from flask import Flask, session, request, render_template, redirect, send_file, after_this_request, make_response
from cs50 import SQL
from flask_session import Session
from werkzeug.utils import secure_filename
from fpdf import FPDF
import os
from datetime import datetime
import redis
import bcrypt
from dotenv import load_dotenv
from io import BytesIO
from urllib.parse import quote_plus


app = Flask(__name__)
load_dotenv()
app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY')

db = SQL("sqlite:///students.db")
subjects = ['thethao', 'vanhoa', 'nghethuat', 'tinhnguyen', 'hocthuat']

app.config["SESSION PERMANENT"] = False
app.config["SESSION_TYPE"] = "redis"
app.config["SESSION_REDIS"] = redis.StrictRedis(host='localhost', port=6379, db=0)
Session(app)



@app.route("/")
def index():
    #create a button for user to go to login site
    return render_template("index.html")

@app.route("/login", methods=["GET", "POST"])
def login():
    ps_message = None
    if request.method == "POST":
        student_id = request.form.get("student_id")
        password = request.form.get("password")

        rows = db.execute("SELECT * FROM students_access WHERE student_id = ?", student_id)
        if len(rows) == 1:
            user = rows[0]
            if bcrypt.checkpw(password.encode('utf-8'), user['password'].encode('utf-8')):
                session['user_id'] = user['student_id']
                session['access_level'] = user['phanquyen']
                if user['default_password']:
                    ps_message = "Your password is still default, you need to change your password first"
                    return render_template("change_password.html", student_id=student_id, ps_message=ps_message)
                else:    
                    return redirect("/home")
            else:
                # Invalid login
                return redirect("/wronglogin")
        else: 
            return redirect("/wronglogin")

    return render_template("login.html")

@app.route("/reset_password", methods = ["GET", "POST"])
def reset_password():
    if "user_id" not in session or session["access_level"] != "IT":
        return redirect("/login")
    if request.method == "POST":    
        student_id = request.form.get("student_id")
        check_exist = db.execute("SELECT * FROM students_access WHERE student_id =?", student_id)
        reset_password = os.environ.get('RESET_PASSWORD')
        hashed_password = bcrypt.hashpw(reset_password.encode('utf-8'), bcrypt.gensalt())
        if len(check_exist) == 1:
            db.execute("UPDATE students_access SET password = ?, default_password = 1 WHERE student_id = ?", hashed_password.decode('utf-8'), student_id)
            message = "Reset password successful"
        else:
            message = "Don't find student"
        return render_template("reset_password.html", message=message)
    return render_template("reset_password.html")

@app.route("/apply_access", methods = ["GET", "POST"])
def apply_access():
    if "user_id" not in session or session["access_level"] != "IT":
        return redirect("/login")
    message = None
    if request.method == "POST":    
        file = request.files["apply_access"]
        filename = secure_filename(file.filename)
        file.save(filename)

        # Check file size (example: limit to 5MB)
        if os.path.getsize(filename) > 5 * 1024 * 1024:
            message = "File size exceeds the limit of 5MB."
            return render_template('submit_activity.html', message=message)
        import openpyxl
        wb = openpyxl.load_workbook(filename)
        sheet = wb.active

        for row in sheet.iter_rows(min_row=2, values_only=True):
            if len(row) == 1:
                student_id = row
                db.execute("UPDATE students_access SET phanquyen = 'DH' WHERE student_id = ?", student_id)
                message = "Đã add lên DH thành công"
            else:
                message = "File chỉ cần 1 cột dữ liệu chứa mã số sinh viên"

    DH_list = db.execute("SELECT student_id, hovaten, phanquyen FROM students_access JOIN students ON students.id = students_access.student_id WHERE phanquyen = 'DH'")
    return render_template("apply_access.html", message=message, DH_list=DH_list)

@app.route("/reset_access", methods = ["GET", "POST"])
def reset_access():
    if "user_id" not in session or session["access_level"] != "IT":
        return redirect("/login")
    message = None
    if request.method == "POST":    
        file = request.files["reset_access"]
        filename = secure_filename(file.filename)
        file.save(filename)

        # Check file size (example: limit to 5MB)
        if os.path.getsize(filename) > 5 * 1024 * 1024:
            message = "File size exceeds the limit of 5MB."
            return render_template('submit_activity.html', message=message)
        import openpyxl
        wb = openpyxl.load_workbook(filename)
        sheet = wb.active

        for row in sheet.iter_rows(min_row=2, values_only=True):
            if len(row) == 1:
                student_id = row
                db.execute("UPDATE students_access SET phanquyen = 'SV' WHERE student_id = ?", student_id)
                message = "Đã chuyển access thành SV thành công"
            else:
                message = "File chỉ cần 1 cột dữ liệu chứa mã số sinh viên"

    DH_list = db.execute("SELECT student_id, hovaten, phanquyen FROM students_access JOIN students ON students.id = students_access.student_id WHERE phanquyen = 'DH'")
    return render_template("reset_access.html", message=message, DH_list=DH_list)

@app.route("/home")
def home():
    if "user_id" not in session:
        return redirect("/login")
    
    user_id = session["user_id"]
    user_info = db.execute("SELECT id, hovaten, birth, nienkhoa FROM students WHERE id = :user_id",
                           user_id=user_id)
    unanswered_questions = db.execute("SELECT COUNT(*) as count FROM questions WHERE answered = 0")[0]["count"]
    return render_template("home.html", user_info=user_info, access_level=session["access_level"], unanswered_questions=unanswered_questions)

@app.route("/wronglogin")
def wronglogin():
    return render_template("wronglogin.html")

@app.route("/temp_activities", methods=["GET", "POST"])
def temp_activities():
    if "user_id" not in session:
        return redirect("/login")
    
    if request.method == "POST":
        from_day_tmp = request.form.get('from_day_tmp')
        to_day_tmp = request.form.get('to_day_tmp')
        session['from_day_tmp'] = from_day_tmp
        session['to_day_tmp'] = to_day_tmp
        return redirect("/activities")

    return render_template("temp_activities.html")

@app.route("/temp_kt_xp", methods=["GET", "POST"])
def temp_kt_xp():
    if "user_id" not in session:
        return redirect("/login")
    
    if request.method == "POST":
        from_day_tmp = request.form.get('from_day_tmp')
        to_day_tmp = request.form.get('to_day_tmp')
        session['from_day_tmp'] = from_day_tmp
        session['to_day_tmp'] = to_day_tmp
        return redirect("/kt_xp")

    return render_template("temp_kt_xp.html")

@app.route("/temp_drl", methods=["GET", "POST"])
def temp_drl():
    if "user_id" not in session:
        return redirect("/login")
    
    if request.method == "POST":
        from_day_tmp = request.form.get('from_day_tmp')
        to_day_tmp = request.form.get('to_day_tmp')
        session['from_day_tmp'] = from_day_tmp
        session['to_day_tmp'] = to_day_tmp
        return redirect("/drl")

    return render_template("temp_drl.html")

@app.route("/activities", methods=["GET", "POST"])
def activities():
    if "user_id" not in session:
        return redirect("/login")
    
    from_day_tmp = session.get('from_day_tmp')
    to_day_tmp = session.get('to_day_tmp')

    user_id = session["user_id"]
    activities = db.execute("""
        SELECT name, time, level, subject, drl
        FROM hoatdong
        JOIN drl_hoatdong ON hoatdong.id = drl_hoatdong.hoatdong_id
        JOIN thamgia ON thamgia.code_hd = drl_hoatdong.code_hd
        JOIN students ON students.id = thamgia.student_id
        WHERE thamgia.student_id = :user_id AND strftime('%Y-%m-%d', substr(time, 7, 4) || '-' || substr(time, 4, 2) || '-' || substr(time, 1, 2)) BETWEEN :from_day AND :to_day
        ORDER BY level, subject
    """, user_id=user_id, from_day=from_day_tmp, to_day=to_day_tmp)
    
    return render_template("activities.html", activities=activities, from_day_tmp=from_day_tmp, to_day_tmp=to_day_tmp)

@app.route("/kt_xp", methods=["GET", "POST"])
def kt_xp():
    if "user_id" not in session:
        return redirect("/login")
    from_day_tmp = session.get('from_day_tmp')
    to_day_tmp = session.get('to_day_tmp')

    user_id = session["user_id"]
    kt_xp = db.execute("SELECT ten_kt_xp, diem_kt_xp, time FROM optional_points WHERE student_id = :user_id AND strftime('%Y-%m-%d', substr(time, 7, 4) || '-' || substr(time, 4, 2) || '-' || substr(time, 1, 2)) BETWEEN :from_day AND :to_day", 
                       user_id=user_id, from_day=from_day_tmp, to_day=to_day_tmp)
    return render_template("kt_xp.html", kt_xp=kt_xp, from_day_tmp=from_day_tmp, to_day_tmp=to_day_tmp)

@app.route("/drl", methods=["GET", "POST"])
def drl():
    if "user_id" not in session:
        return redirect("/login")
    
    from_day_tmp = session.get('from_day_tmp')
    to_day_tmp = session.get('to_day_tmp')

    user_id = session["user_id"]
    activities = db.execute("""
        SELECT subject, level, SUM(drl) as total_points, time
        FROM hoatdong
        JOIN drl_hoatdong ON hoatdong.id = drl_hoatdong.hoatdong_id
        JOIN thamgia ON thamgia.code_hd = drl_hoatdong.code_hd
        JOIN students ON students.id = thamgia.student_id
        WHERE thamgia.student_id = :user_id AND strftime('%Y-%m-%d', substr(time, 7, 4) || '-' || substr(time, 4, 2) || '-' || substr(time, 1, 2)) BETWEEN :from_day AND :to_day
        GROUP BY subject, level
    """, user_id=user_id, from_day=from_day_tmp, to_day=to_day_tmp)

    optional_points = db.execute("SELECT SUM(diem_kt_xp) as optional_points FROM optional_points WHERE student_id = :user_id AND strftime('%Y-%m-%d', substr(time, 7, 4) || '-' || substr(time, 4, 2) || '-' || substr(time, 1, 2)) BETWEEN :from_day AND :to_day", 
                                 user_id=user_id, from_day=from_day_tmp, to_day=to_day_tmp)
    if optional_points[0]["optional_points"] == None:
        optional_points[0]["optional_points"] = 0
    kt_xp = db.execute("SELECT ten_kt_xp, diem_kt_xp, time FROM optional_points WHERE student_id = :user_id", user_id=user_id)

    b = db.execute("""
        SELECT name, time, level, subject, drl
        FROM hoatdong
        JOIN drl_hoatdong ON hoatdong.id = drl_hoatdong.hoatdong_id
        JOIN thamgia ON thamgia.code_hd = drl_hoatdong.code_hd
        JOIN students ON students.id = thamgia.student_id
        WHERE thamgia.student_id = :user_id AND strftime('%Y-%m-%d', substr(time, 7, 4) || '-' || substr(time, 4, 2) || '-' || substr(time, 1, 2)) BETWEEN :from_day AND :to_day
        ORDER BY subject, level
    """, user_id=user_id, from_day=from_day_tmp, to_day=to_day_tmp)
    
    total_points = 45 + optional_points[0]["optional_points"]
    explanations = []
    pfes = []
    for activity in activities:
        if activity["level"] == 'YDS' and activity["total_points"] > 5:
            explanations.append(f"Points for {activity['subject']} from YDS = {activity["total_points"]} exceeded the maximum allowed (5 points) so points for {activity['subject']} from YDS is 5")
            activity["total_points"] = 5
    for subject in subjects:
        a = sum(activity['total_points'] for activity in activities if activity['subject'] == subject)
        if a > 20:
            explanations.append(f"Total points for {activity['subject']} = {a} exceeded the maximum allowed (20 points) so total points for {activity['subject']} is 20.")
            pfes.append({"subject":subject, "points":20})
            total_points += 20
        else:
            pfes.append({"subject":subject, "points":a})
            total_points += a

    return render_template("drl.html", b=b, kt_xp=kt_xp, optional_points=optional_points, pfes=pfes, total_points=total_points, explanations=explanations, from_day=from_day_tmp, to_day=to_day_tmp)

@app.route("/contact_it")
def contact_it():
    return render_template("contact_it.html")

@app.route("/questions", methods=["GET", "POST"])
def questions():
    if "user_id" not in session:
        return redirect("/login")
    success_message = None
    if request.method == "POST":
        question = request.form.get("question")
        user_id = session["user_id"]
        student_info = db.execute("SELECT hovaten, email FROM students JOIN email ON email.student_id = students.id WHERE id = :user_id", user_id=user_id)
        
        db.execute("INSERT INTO questions (id, hovaten, email, question, answered, answered_by) VALUES (:id, :name, :email, :question, 0, 'None')",
                   id=user_id, name=student_info[0]["hovaten"], email=student_info[0]["email"], question=question)
        success_message = "Your question has been submitted successfully."
    
    return render_template("questions.html", success_message=success_message)

@app.route('/change_password', methods=['GET', 'POST'])
def change_password():
    if "user_id" not in session:
        return redirect("/login")
    
    message = None
    if request.method == 'POST':
        student_id = session["user_id"]
        old_password = request.form['old_password']
        new_password = request.form['new_password']

        rows = db.execute("SELECT * FROM students_access WHERE student_id = ?", student_id)
        if len(rows) == 1:
            user = rows[0]
            if bcrypt.checkpw(old_password.encode('utf-8'), user['password'].encode('utf-8')):
                hashed_new_password = bcrypt.hashpw(new_password.encode('utf-8'), bcrypt.gensalt())
                db.execute("UPDATE students_access SET password = :password, default_password = 0 WHERE student_id = :id", password=hashed_new_password.decode('utf-8'), id=student_id)
                message = "Password changed successfully!"
            else:
                message = "Incorrect old password."
                return render_template('change_password.html', message=message, student_id=student_id)

    return render_template('change_password.html', message=message, student_id=session["user_id"])

@app.route("/submit_activity", methods=["GET", "POST"])
def submit_activity():
    if "user_id" not in session or session["access_level"] != "DH":
        return redirect("/login")
    if request.method == "POST":
        
        user_id = session["user_id"]
        submission_time = datetime.now()
        submission_site = "/submit_activity"

        # Get activity information from the form
        activity_id = request.form.get("activity_id")
        # Check if the activity ID already exists in the database
        existing_activity = db.execute("SELECT * FROM hoatdong WHERE id = ?", activity_id)
        if existing_activity:
            message = "Activity ID already exists. Please check again or input another one."
            return render_template("submit_activity.html", message=message)
        activity_name = request.form.get("activity_name")
        activity_level = request.form.get("activity_level")
        activity_subject = request.form.get("activity_subject")
        activity_time = request.form.get("activity_time")
        
        # Get participant information from the form
        roles = request.form.getlist("role[]")
        points = request.form.getlist("points[]")
        codes = request.form.getlist("code[]")
        
        # Get the uploaded file
        file = request.files["file"]
        filename = secure_filename(file.filename)
        file.save(filename)
        
        # Check file size (example: limit to 5MB)
        if os.path.getsize(filename) > 5 * 1024 * 1024:
            message = "File size exceeds the limit of 5MB."
            return render_template('submit_activity.html', message=message)
        import openpyxl
        # Open the .xlsx file and read the data
        wb = openpyxl.load_workbook(filename)
        sheet = wb.active
        student_activity_data = []
        for row in sheet.iter_rows(min_row=2, values_only=True):
            if len(row) == 2:
                student_id, code_hd = row
                student_activity_data.append((student_id, code_hd))
            else:
                false_message = "File excel cần phải có 2 cột dữ liệu"
                return render_template("submit_activity.html", false_message=false_message)
        
        # Insert activity information into the database
        db.execute("INSERT INTO hoatdong (id, name, level, subject, time) VALUES (:id, :name, :level, :subject, :time)",
                   id=activity_id, name=activity_name, level=activity_level, subject=activity_subject, time=activity_time)
        
        # Insert participant information into the database if provided
        if request.form.get("holder_points") and request.form.get("holder_code"):
            db.execute("INSERT INTO drl_hoatdong (hoatdong_id, hinhthucthamgia, drl, code_hd) VALUES (:hoatdong_id, 'TC', :drl, :code_hd)",
                       hoatdong_id=activity_id, drl=request.form.get("holder_points"), code_hd=request.form.get("holder_code"))
        if request.form.get("joiner_points") and request.form.get("joiner_code"):
            db.execute("INSERT INTO drl_hoatdong (hoatdong_id, hinhthucthamgia, drl, code_hd) VALUES (:hoatdong_id, 'TG', :drl, :code_hd)",
                       hoatdong_id=activity_id, drl=request.form.get("joiner_points"), code_hd=request.form.get("joiner_code"))
        if request.form.get("watcher_points") and request.form.get("watcher_code"):
            db.execute("INSERT INTO drl_hoatdong (hoatdong_id, hinhthucthamgia, drl, code_hd) VALUES (:hoatdong_id, 'XE', :drl, :code_hd)",
                       hoatdong_id=activity_id, drl=request.form.get("watcher_points"), code_hd=request.form.get("watcher_code"))
        
        # Insert participant information into the database
        for role, point, code in zip(roles, points, codes):
            db.execute("INSERT INTO drl_hoatdong (hoatdong_id, hinhthucthamgia, drl, code_hd) VALUES (:hoatdong_id, :hinhthucthamgia, :drl, :code_hd)",
                       hoatdong_id=activity_id, hinhthucthamgia=role, drl=point, code_hd=code)
        
        # Insert student activity data into the database
        for student_id, code_hd in student_activity_data:
            db.execute("INSERT INTO thamgia (student_id, code_hd) VALUES (:student_id, :code_hd)",
                       student_id=student_id, code_hd=code_hd)
        
        db.execute("INSERT INTO submission_history (user_id, submission_time, submission_site) VALUES (:user_id, :submission_time, :submission_site)",
                    user_id=user_id, submission_time=submission_time, submission_site=submission_site)

        submit_message="Activity submitted successfully!"
        return render_template("submit_activity.html", submit_message=submit_message)
    
    return render_template("submit_activity.html")

@app.route("/submit_education", methods=["GET", "POST"])
def submit_education():
    if "user_id" not in session or session["access_level"] != "DH":
        return redirect("/login")
    if request.method == "POST":
        user_id = session["user_id"]
        submission_time = datetime.now()
        submission_site = "/submit_education"

        if "edu_file" not in request.files:
            false_submit = "No file part"
            return render_template("submit_education.html", false_submit=false_submit)
        file = request.files["edu_file"]
        if file.filename == "":
            false_submit="No selected file"
            return render_template("submit_education.html", false_submit=false_submit)
        if file:
            filename = secure_filename(file.filename)
            file.save(filename)
            # Check file size (example: limit to 5MB)
            if os.path.getsize(filename) > 5 * 1024 * 1024:
                message = "File size exceeds the limit of 5MB."
                return render_template('submit_activity.html', message=message)
            import openpyxl
            wb = openpyxl.load_workbook(filename)
            sheet = wb.active
            for row in sheet.iter_rows(min_row=2, values_only=True):
                if len(row) == 4:
                    student_id, ten_kt_xp, diem_kt_xp, time = row
                    existing_kt_xp = db.execute("SELECT * FROM optional_points WHERE student_id = :student_id AND ten_kt_xp = :ten_kt_xp",
                               student_id=student_id, ten_kt_xp=ten_kt_xp)
                    if existing_kt_xp:
                        message = "Đã tồn tại loại khen thưởng/xử phạt trong dữ liệu, vui lòng kiểm tra lại hoặc nhập mới"
                        return render_template("submit_education.html", message=message)
                else:
                    false_submit="Invalid file structure. Each row must have 4 columns."
                    return render_template("submit_education.html", false_submit=false_submit)    
                  
            for row in sheet.iter_rows(min_row=2, values_only=True):
                student_id, ten_kt_xp, diem_kt_xp, time = row
                db.execute("INSERT INTO optional_points(student_id, ten_kt_xp, diem_kt_xp, time) VALUES (:student_id, :ten_kt_xp, :diem_kt_xp, :time)",
                           student_id=student_id, ten_kt_xp=ten_kt_xp, diem_kt_xp=diem_kt_xp, time=time)  
                
            db.execute("INSERT INTO submission_history (user_id, submission_time, submission_site) VALUES (:user_id, :submission_time, :submission_site)",
                    user_id=user_id, submission_time=submission_time, submission_site=submission_site)
       
            submitedu_message = "Nhập khen thưởng, xử phạt thành công"
            return render_template("submit_education.html", submitedu_message=submitedu_message)
    
    return render_template("submit_education.html")

@app.route("/submit_students", methods=["GET", "POST"])
def submit_students():
    if "user_id" not in session or session["access_level"] != "DH":
        return redirect("/login")
    
    if request.method == "POST":
        user_id = session["user_id"]
        submission_time = datetime.now()
        submission_site = "/submit_students"

        file = request.files["students_file"]
        filename = secure_filename(file.filename)
        file.save(filename)
        # Check file size (example: limit to 5MB)
        if os.path.getsize(filename) > 5 * 1024 * 1024:
            message = "File size exceeds the limit of 5MB."
            return render_template('submit_activity.html', message=message)
        import openpyxl
        wb = openpyxl.load_workbook(filename)
        sheet = wb.active

        for row in sheet.iter_rows(min_row=2, values_only=True):
            if len(row) == 6:
                id, hovaten, birth, nienkhoa, phanquyen, email = row
                existing_student = db.execute("SELECT * FROM students WHERE id = :id", id=id)
                if existing_student:
                    message = "Có học sinh trong file đã tồn tại trong danh sách sinh viên hiện có, vui lòng kiểm tra lại và nộp lại file khác"
                    return render_template("submit_students.html", message=message)
            else:
                false_submit = "Invalid file structure. Each row must have 6 columns."
                return render_template("submit_students.html", false_submit=false_submit)  
        
        password = "123456"
        for row in sheet.iter_rows(min_row=2, values_only=True):
            id, hovaten, birth, nienkhoa, phanquyen, email = row
            hashed_password = bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt())
            default_password = (password == "123456")
            db.execute("INSERT INTO students(id, hovaten, birth, nienkhoa) VALUES (:id, :hovaten, :birth, :nienkhoa)",
                            id=id, hovaten=hovaten, birth=birth, nienkhoa=nienkhoa)
            db.execute("INSERT INTO students_access(student_id, password, phanquyen, default_password) VALUES (:student_id, :password, :phanquyen, :default_password)",
                       student_id=id, password=hashed_password.decode('utf-8'), phanquyen=phanquyen, default_password=default_password) 
            db.execute("INSERT INTO email(student_id, email) VALUES (:student_id, :email)",
                           student_id=id, email=email)
            
        db.execute("INSERT INTO submission_history (user_id, submission_time, submission_site) VALUES (:user_id, :submission_time, :submission_site)",
                    user_id=user_id, submission_time=submission_time, submission_site=submission_site)

        submitstu_message = "Nhập sinh viên mới thành công"
        return render_template("submit_students.html", submitstu_message=submitstu_message)

    return render_template("submit_students.html")

@app.route("/submit_participants", methods=["GET", "POST"])
def submit_participants():
    if "user_id" not in session or session["access_level"] != "DH":
        return redirect("/login")
    
    if request.method == "POST":
        user_id = session["user_id"]
        submission_time = datetime.now()
        submission_site = "/submit_participants"

        activity_id = request.form.get("activity_id")
        existing_activity = db.execute("SELECT * FROM hoatdong WHERE id = :id", id=activity_id)
        if len(existing_activity) != 1:
            message = "Hoạt động này chưa có hoặc bị nhập dư, vui lòng kiểm tra và nhập lại"
            return render_template("submit_participants.html", message=message)
        
        file = request.files["participants_file"]
        filename = secure_filename(file.filename)
        file.save(filename)
        # Check file size (example: limit to 5MB)
        if os.path.getsize(filename) > 5 * 1024 * 1024:
            message = "File size exceeds the limit of 5MB."
            return render_template('submit_activity.html', message=message)
        import openpyxl
        wb = openpyxl.load_workbook(filename)
        sheet = wb.active

        for row in sheet.iter_rows(min_row=2, values_only=True):
            if len(row) == 2:
                student_id, code_hd = row
                existing_participant = db.execute("SELECT * FROM thamgia WHERE student_id = :student_id AND code_hd = :code_hd",
                                                student_id=student_id, code_hd=code_hd)
                if activity_id not in code_hd:
                    message = "Có sinh viên tham gia không thuộc hoạt động cần thêm, vui lòng kiểm tra lại file"
                    return render_template("submit_participants.html", message=message)
                if existing_participant:
                    message = "Có học sinh tham gia trong file đã tồn tại trong danh sách sinh viên tham gia hiện có, vui lòng kiểm tra lại và nộp lại file khác"
                    return render_template("submit_participants.html", message=message)
            else:
                false_submit = "Invalid file structure. Each row must have 2 columns."
                return render_template("submit_participants.html", false_submit=false_submit)
            
        for row in sheet.iter_rows(min_row=2, values_only=True):
            student_id, code_hd = row
            db.execute("INSERT INTO thamgia(student_id, code_hd) VALUES (:student_id, :code_hd)",
                           student_id=student_id, code_hd=code_hd)

        db.execute("INSERT INTO submission_history (user_id, submission_time, submission_site) VALUES (:user_id, :submission_time, :submission_site)",
                    user_id=user_id, submission_time=submission_time, submission_site=submission_site)

        submitpar_message = "Nhập thêm danh sách sinh viên tham gia thành công"
        return render_template("submit_participants.html", submitpar_message=submitpar_message)
    
    return render_template("/submit_participants.html")

@app.route("/answer_questions", methods=["GET", "POST"])
def answer_questions():
    if "user_id" not in session or session["access_level"] != "DH":
        return redirect("/login")

    if request.method == "POST":
        questions = db.execute("SELECT * FROM questions WHERE answered = 0")
        for question in questions:
            answered_by = request.form.get(f"answered_to_{question['question_id']}")
            answered = request.form.get(f"answered_{question['question_id']}") == "on"
            db.execute("UPDATE questions SET answered_by = :answered_by, answered = :answered WHERE question_id = :question_id",
                       answered_by=answered_by, answered=answered, question_id=question["question_id"])
        questions = db.execute("SELECT * FROM questions WHERE answered = 0")
        answer_message = "Questions updated successfully"
        return render_template("answer_questions.html", questions=questions, answer_message=answer_message)

    questions = db.execute("SELECT * FROM questions WHERE answered = 0")
    return render_template("answer_questions.html", questions=questions)

@app.route("/export_file")
def export_file():
    if "user_id" not in session or session["access_level"] != "DH":
        return redirect("/login")
    return render_template("export_standard.html")

@app.route("/generate_pdf/<int:student_id>")
def generate_pdf(student_id):
    student_info = db.execute("SELECT * FROM students WHERE id = ?", student_id)[0]

    pdf = FPDF()
    pdf.add_page()
    pdf.set_font("Arial", size=12)

    pdf.cell(200, 10, txt=f"Thông tin sinh viên ID: {student_info['id']}", ln=1, align="C")
    pdf.cell(200, 10, txt=f"Họ và tên: {student_info['hovaten']}", ln=1)
    pdf.cell(200, 10, txt=f"Ngày sinh: {student_info['birth']}", ln=1)
    pdf.cell(200, 10, txt=f"Niên khóa: {student_info['nienkhoa']}", ln=1)

    response = make_response(pdf.output(dest='S').encode('latin-1'))
    response.headers["Content-Type"] = "application/pdf"
    response.headers["Content-Disposition"] = f"inline; filename=thong_tin_sinh_vien_{student_id}.pdf"
    return response

@app.route("/export_standard", methods=["POST"])
def export_standard():

    from_day = request.form.get('from_day')
    to_day = request.form.get('to_day')
    school_years = request.form.get('school_years')

    students = db.execute("""
        SELECT students.id, hovaten, birth, nienkhoa
        FROM students
        WHERE nienkhoa = :school_years
    """, school_years=school_years)
    if len(students) == 0:
        message = "Không tìm thấy sinh viên với niên khóa bạn đã nhập, vui lòng kiểm tra lại"
        return render_template("export_standard.html", message=message)
    
    for student in students:
        activities = db.execute("""
            SELECT subject, level, SUM(drl) as total_points, time
            FROM hoatdong
            JOIN drl_hoatdong ON hoatdong.id = drl_hoatdong.hoatdong_id
            JOIN thamgia ON thamgia.code_hd = drl_hoatdong.code_hd
            JOIN students ON students.id = thamgia.student_id
            WHERE thamgia.student_id = :user_id AND strftime('%Y-%m-%d', substr(time, 7, 4) || '-' || substr(time, 4, 2) || '-' || substr(time, 1, 2)) BETWEEN :from_day AND :to_day
            GROUP BY subject, level
        """, user_id=student["id"], from_day=from_day, to_day=to_day)
        
        optional_points = db.execute("SELECT SUM(diem_kt_xp) as optional_points FROM optional_points WHERE student_id = :student_id AND strftime('%Y-%m-%d', substr(time, 7, 4) || '-' || substr(time, 4, 2) || '-' || substr(time, 1, 2)) BETWEEN :from_day AND :to_day",
                                     student_id=student["id"], from_day=from_day, to_day=to_day)
        if optional_points[0]["optional_points"] == None:
            optional_points[0]["optional_points"] = 0

        total_points = 45 + optional_points[0]["optional_points"]
        for activity in activities:
            if activity["level"] == 'YDS' and activity["total_points"] > 5:
                activity["total_points"] = 5
        for subject in subjects:
            a = sum(activity['total_points'] for activity in activities if activity['subject'] == subject)
            if a > 20:
                total_points += 20
            else:
                total_points += a

        student['total_points'] = total_points
    
    pdf = FPDF()
    pdf.add_font('DejaVuSans', '', 'DejaVuSans.ttf', uni=True) # Đăng ký font Unicode
    pdf.add_page()
    pdf.set_font('DejaVuSans', '', 12)

    # Tiêu đề bảng
    pdf.cell(30, 10, "ID", border=1, align='C')
    pdf.cell(70, 10, "Họ và tên", border=1, align='C')
    pdf.cell(30, 10, "Ngày sinh", border=1, align='C')
    pdf.cell(30, 10, "Niên khóa", border=1, align='C')
    pdf.cell(35, 10, "Điểm rèn luyện", border=1, align='C')
    pdf.ln()

    pdf.set_font('DejaVuSans', '', 12)
    for student in students:
        # Dữ liệu sinh viên
        pdf.cell(30, 10, student['id'], border=1)
        pdf.cell(70, 10, student['hovaten'], border=1)
        pdf.cell(30, 10, student['birth'], border=1, align='C')
        pdf.cell(30, 10, student['nienkhoa'], border=1, align='C')
        pdf.cell(35, 10, str(student['total_points']), border=1, align='C')
        pdf.ln()

    buffer = BytesIO()
    pdf.output(buffer)
    pdf_content = buffer.getvalue()
    buffer.close()

    filename = f"Điểm rèn luyện của Khóa Dược {school_years} từ ngày {from_day} đến ngày {to_day}.pdf"
    encoded_filename = quote_plus(filename)
    response = make_response(pdf_content)
    response.headers["Content-Type"] = "application/pdf"
    response.headers["Content-Disposition"] = f"inline; filename*=UTF-8''{encoded_filename}"
    return response

@app.route("/search_selection", methods=["GET", "POST"])
def search_selection():
    if "user_id" not in session or session["access_level"] != "DH":
        return redirect("/login")
    
    if request.method == "POST":
        field = request.form.get("field")
        field_input = request.form.get("field_input")
        student = None
        activities = None
        students = None
        activity = None
        roles = None
        activity_students = None
        if field == "id":
            student = db.execute("SELECT id, hovaten, birth, nienkhoa, email FROM students JOIN email ON email.student_id = students.id WHERE id = :id", id=field_input)
            if len(student) == 0:
                no_found = "Không tìm thấy sinh viên này, vui lòng kiểm tra lại thông tin đã nhập vào"
                return render_template("search_selection.html", no_found=no_found)
            activities = db.execute("""
                                SELECT hoatdong.id as activity_id, name, time, level, subject, hinhthucthamgia, drl
                                FROM hoatdong
                                JOIN drl_hoatdong ON hoatdong.id = drl_hoatdong.hoatdong_id
                                JOIN thamgia ON thamgia.code_hd = drl_hoatdong.code_hd
                                JOIN students ON students.id = thamgia.student_id
                                WHERE thamgia.student_id = :user_id
                                ORDER BY level, subject
                            """, user_id=student[0]["id"])
        elif field == "hovaten":
            students = db.execute("SELECT id, hovaten, birth, nienkhoa, email FROM students JOIN email ON email.student_id = students.id WHERE hovaten = :hovaten", hovaten=field_input)
            if len(students) == 0:
                no_found = "Không tìm thấy sinh viên này, vui lòng kiểm tra lại thông tin đã nhập vào"
                return render_template("search_selection.html", no_found=no_found)
        elif field == "nienkhoa":
            students = db.execute("SELECT id, hovaten, birth, nienkhoa, email FROM students JOIN email ON email.student_id = students.id WHERE nienkhoa = :nienkhoa", nienkhoa=field_input)
            if len(students) == 0:
                no_found = "Không tìm thấy niên khóa này, vui lòng kiểm tra lại thông tin đã nhập hoặc liên hệ IT để kiểm tra"
                return render_template("search_selection.html", no_found=no_found)
        elif field == "activity_id":
            activity = db.execute("SELECT * FROM hoatdong WHERE id = :id", id=field_input)
            if len(activity) == 0:
                no_found = "Không tìm thấy hoạt động với id này, vui lòng kiểm tra lại thông tin đã nhập"
                return render_template("search_selection.html", no_found=no_found)
            roles = db.execute("SELECT hinhthucthamgia, drl, code_hd FROM drl_hoatdong WHERE hoatdong_id = :hoatdong_id", hoatdong_id=field_input)
            activity_students = db.execute("SELECT id, hovaten, birth, nienkhoa, hinhthucthamgia FROM students JOIN thamgia ON thamgia.student_id = students.id JOIN drl_hoatdong ON drl_hoatdong.code_hd = thamgia.code_hd WHERE hoatdong_id = :hoatdong_id",
                                  hoatdong_id=field_input)
        else:
            message = "failure, no field sent"
            return render_template("search_selection.html", message=message)

        return render_template("search_selection.html", activity=activity, activities=activities, roles=roles, student=student, students=students, activity_students=activity_students)
    
    return render_template("search_selection.html")

@app.route("/export_database")
def export_database():
    if "user_id" not in session or session["access_level"] != "DH":
        return redirect("/login")
    return render_template("export_database.html")

@app.route("/students_database")
def students_database():
    if "user_id" not in session or session["access_level"] != "DH":
        return redirect("/login")
    students = db.execute("SELECT id, hovaten, birth, nienkhoa FROM students ORDER BY id")

    pdf = FPDF()
    pdf.add_font('DejaVuSans', '', 'DejaVuSans.ttf', uni=True) # Đăng ký font Unicode
    pdf.add_page()
    pdf.set_font('DejaVuSans', '', 12) # Sử dụng font đã đăng ký

    # Tiêu đề bảng
    pdf.cell(30, 10, "ID", border=1, align='C')
    pdf.cell(70, 10, "Họ và tên", border=1, align='C')
    pdf.cell(30, 10, "Ngày sinh", border=1, align='C')
    pdf.cell(30, 10, "Niên khóa", border=1, align='C')
    pdf.ln()

    for student in students:
        # Dữ liệu sinh viên
        pdf.cell(30, 10, student['id'], border=1)
        pdf.cell(70, 10, student['hovaten'], border=1)
        pdf.cell(30, 10, student['birth'], border=1, align='C')
        pdf.cell(30, 10, student['nienkhoa'], border=1, align='C')
        pdf.ln()

    buffer = BytesIO()
    pdf.output(buffer)
    pdf_content = buffer.getvalue()
    buffer.close()

    filename = "Danh sách tổng sinh viên hiện có trên hệ thống.pdf"
    encoded_filename = quote_plus(filename)
    response = make_response(pdf_content)
    response.headers["Content-Type"] = "application/pdf"
    response.headers["Content-Disposition"] = f"inline; filename*=UTF-8''{encoded_filename}"
    return response

@app.route("/activities_database")
def activities_database():
    if "user_id" not in session or session["access_level"] != "DH":
        return redirect("/login")
    activities = db.execute("SELECT * FROM hoatdong ORDER BY time")

    pdf = FPDF()
    pdf.add_font('DejaVuSans', '', 'DejaVuSans.ttf', uni=True) # Đăng ký font Unicode
    pdf.add_page()
    pdf.set_font('DejaVuSans', '', 12) # Sử dụng font đã đăng ký

    # Tiêu đề bảng
    pdf.cell(30, 10, "ID hoạt động", border=1, align='C')
    pdf.cell(80, 10, "Tên hoạt động", border=1, align='C')
    pdf.cell(10, 10, "Cấp", border=1, align='C')
    pdf.cell(30, 10, "Lĩnh vực", border=1, align='C')
    pdf.cell(30, 10, "Thời gian", border=1, align='C')
    pdf.ln()

    for activity in activities:
        # Dữ liệu sinh viên
        pdf.cell(30, 10, activity['id'], border=1)
        pdf.cell(80, 10, activity['name'], border=1)
        pdf.cell(10, 10, activity['level'], border=1, align='C')
        pdf.cell(30, 10, activity['subject'], border=1, align='C')
        pdf.cell(30, 10, activity["time"], border=1, align='C')
        pdf.ln()

    buffer = BytesIO()
    pdf.output(buffer)
    pdf_content = buffer.getvalue()
    buffer.close()

    filename = "Danh sách tổng hoạt động hiện có trên hệ thống.pdf"
    encoded_filename = quote_plus(filename)
    response = make_response(pdf_content)
    response.headers["Content-Type"] = "application/pdf"
    response.headers["Content-Disposition"] = f"inline; filename*=UTF-8''{encoded_filename}"
    return response

@app.route("/participants_database")
def participants_database():
    if "user_id" not in session or session["access_level"] != "DH":
        return redirect("/login")
    participants = db.execute("SELECT * FROM thamgia ORDER BY code_hd")

    pdf = FPDF()
    pdf.add_font('DejaVuSans', '', 'DejaVuSans.ttf', uni=True) # Đăng ký font Unicode
    pdf.add_page()
    pdf.set_font('DejaVuSans', '', 12) # Sử dụng font đã đăng ký

    # Tiêu đề bảng
    pdf.cell(40, 10, "ID sinh viên", border=1, align='C')
    pdf.cell(50, 10, "Code hoạt động", border=1, align='C')
    pdf.ln()

    for participant in participants:
        # Dữ liệu sinh viên
        pdf.cell(40, 10, participant['student_id'], border=1, align='C')
        pdf.cell(50, 10, participant['code_hd'], border=1, align='C')
        pdf.ln()

    buffer = BytesIO()
    pdf.output(buffer)
    pdf_content = buffer.getvalue()
    buffer.close()

    filename = "Danh sách tổng tham gia hiện có trên hệ thống.pdf"
    encoded_filename = quote_plus(filename)
    response = make_response(pdf_content)
    response.headers["Content-Type"] = "application/pdf"
    response.headers["Content-Disposition"] = f"inline; filename*=UTF-8''{encoded_filename}"
    return response

@app.route("/kt_xp_database")
def kt_xp_database():
    if "user_id" not in session or session["access_level"] != "DH":
        return redirect("/login")
    kt_xp = db.execute("SELECT * FROM optional_points ORDER BY time")

    pdf = FPDF()
    pdf.add_font('DejaVuSans', '', 'DejaVuSans.ttf', uni=True) # Đăng ký font Unicode
    pdf.add_page()
    pdf.set_font('DejaVuSans', '', 12) # Sử dụng font đã đăng ký

    # Tiêu đề bảng
    pdf.cell(30, 10, "ID sinh viên", border=1, align='C')
    pdf.cell(90, 10, "Tên khen thưởng/xử phạt", border=1, align='C')
    pdf.cell(40, 10, "Điểm cộng/trừ", border=1, align='C')
    pdf.cell(30, 10, "Thời gian", border=1, align='C')
    pdf.ln()

    for i in kt_xp:
        # Dữ liệu sinh viên
        pdf.cell(30, 10, i['student_id'], border=1)
        pdf.cell(90, 10, i['ten_kt_xp'], border=1)
        pdf.cell(40, 10, i['diem_kt_xp'], border=1, align='C')
        pdf.cell(30, 10, i['time'], border=1, align='C')
        pdf.ln()

    buffer = BytesIO()
    pdf.output(buffer)
    pdf_content = buffer.getvalue()
    buffer.close()

    filename = "Danh sách tổng khen thưởng/xử phạt hiện có trên hệ thống.pdf"
    encoded_filename = quote_plus(filename)
    response = make_response(pdf_content)
    response.headers["Content-Type"] = "application/pdf"
    response.headers["Content-Disposition"] = f"inline; filename*=UTF-8''{encoded_filename}"
    return response

@app.route("/submission_database")
def submission_database():
    if "user_id" not in session or session["access_level"] != "DH":
        return redirect("/login")
    submissions = db.execute("SELECT * FROM submission_history ORDER BY submission_time")

    pdf = FPDF()
    pdf.add_font('DejaVuSans', '', 'DejaVuSans.ttf', uni=True) # Đăng ký font Unicode
    pdf.add_page()
    pdf.set_font('DejaVuSans', '', 12) # Sử dụng font đã đăng ký

    # Tiêu đề bảng
    pdf.cell(10, 10, "STT", border=1)
    pdf.cell(50, 10, "ID sinh viên thực hiện", border=1)
    pdf.cell(60, 10, "Thời gian nhập", border=1)
    pdf.cell(50, 10, "Địa chỉ nhập", border=1)
    pdf.ln()

    for submission in submissions:
        # Dữ liệu sinh viên
        pdf.cell(10, 10, str(submission['id']), border=1)
        pdf.cell(50, 10, submission['user_id'], border=1)
        pdf.cell(60, 10, submission['submission_time'], border=1)
        pdf.cell(50, 10, submission['submission_site'], border=1)
        pdf.ln()

    buffer = BytesIO()
    pdf.output(buffer)
    pdf_content = buffer.getvalue()
    buffer.close()

    filename = "Lịch sử nhập dữ liệu hiện có trên hệ thống.pdf"
    encoded_filename = quote_plus(filename)
    response = make_response(pdf_content)
    response.headers["Content-Type"] = "application/pdf"
    response.headers["Content-Disposition"] = f"inline; filename*=UTF-8''{encoded_filename}"
    return response

if __name__ == "__main__":
    app.secret_key = os.getenv('FLASK_SECRET_KEY')
    app.run(debug=True)