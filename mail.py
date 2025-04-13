CLIENT_ID = os.environ.get('OUTLOOK_CLIENT_ID')
CLIENT_SECRET = os.environ.get('OUTLOOK_CLIENT_SECRET')
TENANT_ID = 'common'
REDIRECT_URI = 'http://localhost:5000/oauth2callback-outlook'

GRAPH_API_ENDPOINT = 'https://graph.microsoft.com/v1.0'
MAIL_SEND_ENDPOINT = f'{GRAPH_API_ENDPOINT}/me/sendMail'
AUTHORITY = f'https://login.microsoftonline.com/{TENANT_ID}'
SCOPES = ['Mail.Send']

def update_password(user_id, new_password_hash, db):
    db.execute("UPDATE temp_user SET password = :password, reset_token = NULL, reset_token_expiration = NULL WHERE student_id = :id", password=new_password_hash, id=user_id)
class ResetPasswordForm(FlaskForm):
    email = StringField('Địa chỉ Email', validators=[DataRequired(), Email()])
    submit_request = SubmitField('Gửi yêu cầu đặt lại mật khẩu')
class NewPasswordForm(FlaskForm):
    password = PasswordField('Mật khẩu mới', validators=[DataRequired()])
    confirm_password = PasswordField('Xác nhận mật khẩu',
                                     validators=[DataRequired(), EqualTo('password', message='Mật khẩu phải trùng khớp.')])
    submit_password = SubmitField('Đặt lại mật khẩu')
@app.route('/outlook/login')
def outlook_login():
    auth_app = msal.PublicClientApplication(
        CLIENT_ID,
        authority=AUTHORITY,
    )
    auth_url = auth_app.get_authorization_request_url(
        scopes=SCOPES,
        redirect_uri=REDIRECT_URI  # Thêm redirect_uri ở đây
    )
    return redirect(auth_url)

@app.route('/oauth2callback-outlook')
def outlook_callback():
    code = request.args.get('code')
    if code:
        auth_app = msal.PublicClientApplication(
            CLIENT_ID,
            authority=AUTHORITY
        )
        try:
            print(f"Authorization code nhận được: {code}")
            result = auth_app.acquire_token_by_authorization_code(
                code,
                scopes=SCOPES,
                redirect_uri=REDIRECT_URI,
                client_secret=CLIENT_SECRET
            )
            print(f"Result from acquire_token: {result}")
            if 'access_token' in result:
                session['outlook_token'] = result['access_token']
                # Sau khi lấy token thành công, bạn có thể gửi email ngay
                recipient_email = session.pop('reset_email_recipient', None)
                reset_token = session.pop('reset_token', None)
                if recipient_email and reset_token:
                    email_result = send_outlook_email(recipient_email, 'Yêu cầu đặt lại mật khẩu', f'''Để đặt lại mật khẩu của bạn, vui lòng nhấp vào liên kết sau:\n{url_for('reset_token', token=reset_token, _external=True)}\n\nNếu bạn không yêu cầu đặt lại mật khẩu này, hãy bỏ qua email này và mật khẩu của bạn sẽ không thay đổi.''')
                    flash(email_result, 'info' if "thành công" in email_result else 'danger')
                    return redirect(url_for('login')) # Chuyển hướng về trang đăng nhập sau khi gửi email
                else:
                    flash('Có lỗi xảy ra trong quá trình đặt lại mật khẩu.', 'danger')
                    return redirect(url_for('login'))
            else:
                return f'Lỗi khi lấy access token: {result.get("error")}, {result.get("error_description")}'
        except Exception as e:
            print(f"Lỗi trong quá trình lấy token: {e}")
            return f'Lỗi trong quá trình lấy token: {e}'
    else:
        return 'Mã ủy quyền không được tìm thấy.'

def send_outlook_email(recipient_email, subject, body):
    token = session.get('outlook_token')
    if not token:
        return 'Bạn chưa ủy quyền hoặc token đã hết hạn. Vui lòng <a href="/outlook/login">đăng nhập Outlook</a> trước khi gửi email.'

    headers = {
        'Authorization': f'Bearer {token}',
        'Content-Type': 'application/json'
    }
    payload = {
        'message': {
            'subject': subject,
            'body': {
                'contentType': 'Text',
                'content': body
            },
            'toRecipients': [
                {
                    'emailAddress': {
                        'address': recipient_email
                    }
                }
            ]
        },
        'saveToSentItems': 'true'
    }

    try:
        response = requests.post(MAIL_SEND_ENDPOINT, headers=headers, json=payload)
        if response.status_code == 202:
            return 'Email đặt lại mật khẩu đã được gửi thành công!'
        else:
            return f'Lỗi khi gửi email: {response.status_code} - {response.text}'
    except requests.exceptions.RequestException as e:
        return f'Lỗi kết nối khi gửi email: {e}'

@app.route("/reset_request", methods=['GET', 'POST'])
def reset_request_form():
    form = ResetPasswordForm()
    if form.validate_on_submit():
        email = form.email.data
        user = db.execute("SELECT * FROM email WHERE email = ?", email)
        if len(user) == 1:
            user_id = user[0]['student_id']
            token = generate_reset_token(user_id)
            session['reset_email_recipient'] = user[0]['email']
            session['reset_token'] = token
            return redirect(url_for('outlook_login'))
        else:
            flash('Không tìm thấy tài khoản với địa chỉ email này.', 'danger')
    return render_template('reset_request.html', title='Reset Password', form=form)

@app.route("/reset_token/<token>", methods=['GET', 'POST'])
def reset_token(token):
    user_id = verify_reset_token(token)
    if not user_id:
        flash('Token đặt lại mật khẩu không hợp lệ hoặc đã hết hạn.', 'warning')
        return redirect(url_for('reset_request'))
    form = NewPasswordForm()
    if form.validate_on_submit():
        password = form.password.data
        hashed_password = bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt())
        db.execute("UPDATE temp_user SET password = ?, reset_token = NULL, reset_token_expiration = NULL WHERE student_id = ?", hashed_password.decode('utf-8'), user_id)
        flash('Mật khẩu của bạn đã được cập nhật thành công! Bạn có thể đăng nhập ngay bây giờ.', 'success')
        return redirect(url_for('login'))
    return render_template('reset_token.html', title='Đặt lại mật khẩu', form=form)

# --- Các hàm hỗ trợ (bạn cần tự viết) ---

def generate_reset_token(user_id):
    token = secrets.token_urlsafe(16)
    expiration = datetime.utcnow() + timedelta(seconds=1800)
    db.execute("UPDATE temp_user SET reset_token = ?, reset_token_expiration = ? WHERE student_id = ?", token, expiration, user_id)
    return token

def verify_reset_token(token):
    user_data = db.execute("SELECT student_id FROM temp_user WHERE reset_token = ? AND reset_token_expiration > ?", token, datetime.utcnow())
    if len(user_data) == 1:
        return user_data[0]['id']
    return None