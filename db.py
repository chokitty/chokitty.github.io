import bcrypt
from cs50 import SQL

# Initialize database connection
db = SQL("sqlite:///students.db")

# Fetch all user records
users = db.execute("SELECT id, password FROM students")

# Iterate through each user and update the password
for user in users:
    user_id = user['id']
    unhashed_password = user['password']
    
    # Hash the password using bcrypt
    hashed_password = bcrypt.hashpw(unhashed_password.encode('utf-8'), bcrypt.gensalt())
    
    # Convert hashed_password to a regular string
    hashed_password_str = hashed_password.decode('utf-8')
    
    # Update the database with the hashed password
    db.execute("UPDATE students SET password = :password WHERE id = :id", password=hashed_password_str, id=user_id)

print("Passwords updated successfully!")
