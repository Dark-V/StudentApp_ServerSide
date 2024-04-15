from flask import Flask, render_template, request, jsonify, session
from werkzeug.security import generate_password_hash, check_password_hash
from FlaskWebStudentApp import app
from functools import wraps
import sqlite3
from dateutil.parser import parse
import pandas as pd


conn = sqlite3.connect('test.db', check_same_thread=False)
c = conn.cursor()

#import logging
#logging.basicConfig(filename="log.log",level=logging.DEBUG)

def require_login(roles):
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            cur = conn.cursor()  # Create a new cursor
            user_id = session.get('user_id')
            if not user_id:
                return jsonify({'message': 'Please log in first'}), 401
            cur.execute("SELECT * FROM user WHERE id=?", (user_id,))
            user = cur.fetchone()
            if user[3] not in roles:  # 3 is roles
                return jsonify({'message': 'Unauthorized'}), 403
            return f(*args, **kwargs)
        return decorated_function
    return decorator

def get_logged_in_user():
    user_id = session.get('user_id')
    if not user_id:
        return None
    cur = conn.cursor()  # Create a new cursor
    cur.execute("SELECT * FROM user WHERE id=?", (user_id,))
    user = cur.fetchone()
    return user

@app.route('/auth/login', methods=['GET'])
def login_backend():
    username = request.args.get('username')
    password = request.args.get('password')
    
    c.execute("SELECT * FROM user WHERE username=?", (username,))
    user = c.fetchone()
    if not user or not check_password_hash(user[2], password):
        return jsonify({'message': 'Invalid username or password'}), 401
   
    session['user_id'] = user[0]
    session['role'] = user[3]
    return jsonify({'message': 'Logged in successfully', 'role': user[3]})

@app.route('/auth/register', methods=['GET'])
@require_login(["admin"])
def register():
    username = request.args.get('username')
    password = request.args.get('password')
    id_ = request.args.get('id')

    # Check if username already exists
    c.execute("SELECT * FROM user WHERE username = ?", (username,))
    if c.fetchone() is not None:
        return jsonify({'error':"username_already_exists", 'message': 'Username already exists'})

    hashed_password = generate_password_hash(password, method='scrypt')
    c.execute("INSERT INTO user (id, username, password) VALUES (?, ?, ?)", (id_, username, hashed_password))
    conn.commit()
    return jsonify({'message': 'Registered successfully'})

@app.route('/student/edit', methods=['POST'])
def edit_student_data1():
    # Get the JSON data from the request
    data = request.get_json()
    print(data)

    # Check if username already exists
    c.execute("SELECT * FROM user WHERE username = ?", (data['login'],))
    if c.fetchone() is not None:
        return jsonify({'error':"username_already_exists", 'message': 'Username already exists'})
    conn.commit()

    # Hash the password
    hashed_password = generate_password_hash(data['password'], method='scrypt')

    user_id = data["id"]
    
    # Prepare the SQL query for the Student table
    sql_student = """
    UPDATE Student
    SET family = ?, name = ?, second_name = ?, gender = ?, Groups_number = ?, specialty = ?, department = ?, img = ?
    WHERE id = ?
    """
    
    # Execute the SQL query for the Student table
    c.execute(sql_student, (data['Family'], data['Name'], data['SecondName'], data['Gender'], data['GroupNumber'], data['Specialty'], data['Department'], data['Img'], user_id))
    conn.commit()

    c.execute('''
        INSERT OR REPLACE INTO user (id, username, password) 
        VALUES ((SELECT id FROM user WHERE username = ?), ?, ?)
    ''', (data['login'], data['login'], hashed_password))
    conn.commit()
    
    # Return a success message
    return jsonify({'message': 'student data was changed'})

@app.route('/student/add', methods=['POST'])
def add_student_data():
    # Get the JSON data from the request
    data = request.get_json()

    # Check if username already exists
    c.execute("SELECT * FROM user WHERE username = ?", (data['login'],))
    if c.fetchone() is not None:
        return jsonify({'error':"username_already_exists", 'message': 'Username already exists'},400)

    # Hash the password
    hashed_password = generate_password_hash(data['password'], method='scrypt')

    # Prepare the SQL query for the Student table
    sql_student = """
    INSERT INTO Student (family, name, second_name, gender, Groups_number, specialty, department, img)
    VALUES (?, ?, ?, ?, ?, ?, ?, ?)
    """
    
    # Execute the SQL query for the Student table
    c.execute(sql_student, (data['Family'], data['Name'], data['SecondName'], data['Gender'], data['GroupNumber'], data['Specialty'], data['Department'], data['Img']))
    conn.commit()

    # Get the last inserted id
    last_id = c.lastrowid
   

    c.execute('''
        INSERT INTO user (id, username, password) 
        VALUES (?, ?, ?)
    ''', (last_id, data['login'], hashed_password))
    conn.commit()
    
    # Return a success message
    return jsonify({'message': 'student data was added'})

@app.route('/student/remove/<int:id>', methods=['DELETE'])
def remove_student(id):
    # Prepare the SQL query
    sql = "DELETE FROM Student WHERE id = ?"
    
    # Execute the SQL query
    c.execute(sql, (id,))
    
    # Commit the changes
    conn.commit()
    
    # Check if any row is deleted
    if c.rowcount:
        return jsonify({'message': 'Student removed successfully'})
    else:
        return jsonify({'message': 'No student found with the given id'}), 404

@app.route('/auth/permission', methods=['GET'])
@require_login(["admin"])
def change_role():
    user_id = request.args.get('id')
    new_role = request.args.get('role')

    try:
        c.execute("UPDATE user SET role = ? WHERE id = ?", (new_role, user_id))
        conn.commit()
        return jsonify({"message": "Success. Role updated."}), 200
    except sqlite3.Error as e:
        return jsonify({'error':"cant_update_role", 'message': e}), 500

@app.route('/auth/raw_sql', methods=['GET'])
@require_login(["admin"])
def sql():
    sql = request.args.get('sql')

    try:
        c.execute(sql)
        conn.commit()
        return jsonify({"message": "Success. Sql was used."}), 200
    except sqlite3.Error as e:
        return jsonify({'error':"custom_sql_error", 'message': e}), 500

@app.route('/auth/logout', methods=['GET'])
@require_login(["student", "teacher", "admin"])
def logout():
    session.pop('user_id', None)
    return jsonify({'message': 'Logged out successfully'})

@app.route('/get_info', methods=['GET'])
@require_login(["student", "teacher", "admin"])
def get_info():
    user_id = session.get('user_id')
    
    c.execute("SELECT * FROM Student WHERE id=?", (user_id,))
    student = c.fetchone()
    return jsonify({
        'id': student[0],
        'name': student[1] + " " + student[2]+ " " + student[3],
        'specialty': student[5],
        'groups_number': student[6],
        'department': student[7],
        'role': session.get('role')
    })

@app.route('/get_grades', methods=['GET'])
@require_login(["student", "teacher", "admin"])
def get_grades():
    user_id = session.get('user_id')
    role = session.get('role')
    
    if role in ['teacher', 'admin']:
        user_id = request.args.get('id', default=user_id, type=int)

    c.execute("""
        SELECT Grade.id, Grade.date, Grade.score, Student.name, Discipline.name, Teacher.name 
        FROM Grade 
        INNER JOIN Student ON Grade.student_id = Student.id
        INNER JOIN Discipline ON Grade.discipline_id = Discipline.id
        INNER JOIN Teacher ON Discipline.teacher_id = Teacher.id
        WHERE Student.id = ?
        ORDER BY Grade.date      
    """, (user_id,))
    grades_data = c.fetchall()
    
    grades = [{
        "id": grade_data[0],
        "date": grade_data[1],
        "mark": grade_data[2],
        "student_name": grade_data[3],
        "discipline_id": grade_data[4]
    } for grade_data in grades_data]

    return jsonify(grades)

@app.route('/grade/add', methods=['POST'])
@require_login(["admin", "teacher"])  # assuming only admin and teacher can add grades
def add_grade():
    # Extract information from the request
    date = int(parse(request.json.get('date')).timestamp())
    score = request.json.get('score')
    student_id = request.json.get('student_id')
    discipline_id = request.json.get('discipline_id')

    # Check if all necessary information is provided
    if not all([date, score, student_id, discipline_id]):
        return jsonify({'message': 'Missing information'}), 400

    # Insert the new grade into the Grade table
    c.execute("INSERT INTO Grade (date, score, student_id, discipline_id) VALUES (?, ?, ?, ?)",
              (date, score, student_id, discipline_id))
    conn.commit()

    return jsonify({'message': 'Grade added successfully'})

@app.route('/grade/delete', methods=['GET'])
@require_login(["admin", "teacher"])  # assuming only admin and teacher can delete grades
def delete_grade():
    # Extract the id from the request
    grade_id = request.args.get('id')

    # Check if id is provided
    if not grade_id:
        return jsonify({'message': 'Missing grade id'}), 400

    # Delete the grade from the Grade table
    c.execute("DELETE FROM Grade WHERE id = ?", (grade_id,))
    conn.commit()

    return jsonify({'message': 'Grade deleted successfully'})

@app.route('/get_dates', methods=['GET'])
@require_login(["student", "teacher", "admin"])
def get_dates():
    user_id = session.get('user_id')
    role = session.get('role')
        
    if role in ['teacher', 'admin']:
        user_id = request.args.get('id', default=user_id, type=int)
        
    # Fetch dates from the database
    c.execute("SELECT id,date,status FROM Attendance WHERE student_id=?", (user_id,))
    dates = c.fetchall()

    dates = [{
        "id": date[0],
        "date": date[1],
        "status": date[2],
    } for date in dates]
    
    return jsonify(dates)

@app.route('/date/delete', methods=['GET'])
@require_login(["admin", "teacher"])  # assuming only admin and teacher can delete dates
def delete_date():
    # Extract the id from the request
    date_id = request.args.get('id')

    # Check if id is provided
    if not date_id:
        return jsonify({'message': 'Missing date id'}), 400

    # Delete the date from the Attendance table
    c.execute("DELETE FROM Attendance WHERE id = ?", (date_id,))
    conn.commit()

    return jsonify({'message': 'Date deleted successfully'})

@app.route('/date/add', methods=['POST'])
@require_login(["admin", "teacher"])  # assuming only admin and teacher can add dates
def add_date():
    date = int(parse(request.json.get('date')).timestamp())
    status = request.json.get('status')
    student_id = request.json.get('student_id')

    # Check if all necessary information is provided
    if not all([date, status, student_id]):
        return jsonify({'message': 'Missing information'}), 400

    # Insert the new date into the Attendance table
    c.execute("INSERT INTO Attendance (date, status, student_id) VALUES (?, ?, ?)",
              (date, status, student_id))
    conn.commit()

    return jsonify({'message': 'Date added successfully'})

@app.route('/student/get', methods=['GET'])
@require_login(["admin", "teacher"])  # assuming these roles can get student data
def get_students1():
    groupId = request.args.get('groupId')
    
    if groupId:
        # If groupId is provided, select only students from this group
        c.execute("SELECT id, family, name, second_name FROM Student WHERE Groups_number = ?", (groupId,))
    else:
        # If no groupId is provided, select all students
        c.execute("SELECT id, family, name, second_name FROM Student")
    
    students = c.fetchall()

    # Return the student data
    return jsonify({'students': [{'id': student[0], 'name': f"{student[1]} {student[2]} {student[3]}"} for student in students]})

@app.route('/student/getAll', methods=['GET'])
@require_login(["admin"])  # assuming these roles can get student data
def get_studentsAll():
    # Get all students from the Student table
    c.execute("SELECT * FROM Student")
    conn.commit()
    students = c.fetchall()

    # Convert the student data to a list of dictionaries
    students_dict = [dict(id=s[0], family=s[1], name=s[2], second_name=s[3], gender=s[4], Groups_number=s[5], specialty=s[6], department=s[7]) for s in students]

    # Return the student data
    return jsonify(students_dict)

@app.route('/groups/get', methods=['GET'])
@require_login(["admin", "teacher"])  # assuming these roles can get group data
def get_groups():
    # Get all groups from the Groups table
    c.execute("SELECT id, name FROM Groups")
    groups = c.fetchall()

    # Return the group data
    return jsonify({'groups': [{'id': group[0], 'name': group[1]} for group in groups]})

@app.route('/discipline/get', methods=['GET'])
@require_login(["admin", "teacher"])  # assuming only admin and teacher can get discipline data
def get_disciplines():
    cur = conn.cursor()  # Create a new cursor
    cur.execute("SELECT id, name FROM Discipline")
    disciplines = cur.fetchall()

    # Return the discipline data
    return jsonify({'disciplines': [{'id': discipline[0], 'name': discipline[1]} for discipline in disciplines]})

@app.route('/discipline/getAll', methods=['GET'])
@require_login(["admin", "teacher"])  # assuming only admin and teacher can get discipline data
def get_disciplinesAll():
    cur = conn.cursor()  # Create a new cursor
    cur.execute("SELECT * FROM Groups")
    disciplines = cur.fetchall()
    
    return jsonify({'disciplines': [{'id': discipline[0], 'name': discipline[1],'specialty': discipline[2], 'department': discipline[3]} for discipline in disciplines]})
 
@app.route('/report', methods=['GET'])
def generate_report():
    # Convert the semester start and end dates to timestamps
    start_date = request.args.get('from')
    end_date = request.args.get('to')
    report_type = request.args.get('type')
    
    student_id = request.args.get('studentId')
    group_name = request.args.get('group_id')
   
    start_timestamp = int(parse(start_date).timestamp())
    end_timestamp = int(parse(end_date).timestamp())

    if report_type == 't':
        c.execute("""
            SELECT Student.family || ' ' || Student.name || ' ' || Student.second_name AS full_name, Discipline.name, Grade.score
            FROM Grade
            INNER JOIN Student ON Grade.student_id = Student.id
            INNER JOIN Discipline ON Grade.discipline_id = Discipline.id
            WHERE Grade.date BETWEEN ? AND ? AND Student.Groups_number = ?
        """, (start_timestamp, end_timestamp, group_name))
    elif report_type == 's':
        c.execute("""
            SELECT Groups.name, Discipline.name, Grade.score
            FROM Grade
            INNER JOIN Student ON Grade.student_id = Student.id
            INNER JOIN Groups ON Student.Groups_number = Groups.id
            INNER JOIN Discipline ON Grade.discipline_id = Discipline.id
            WHERE Grade.date BETWEEN ? AND ? AND Groups.id = ?
        """, (start_timestamp, end_timestamp, group_name))
    elif report_type == 'student':
        c.execute("""
            SELECT Student.family || ' ' || Student.name || ' ' || Student.second_name AS full_name, Discipline.name, Grade.score
            FROM Grade
            INNER JOIN Student ON Grade.student_id = Student.id
            INNER JOIN Discipline ON Grade.discipline_id = Discipline.id
            WHERE Grade.date BETWEEN ? AND ? AND Student.id = ?
        """, (start_timestamp, end_timestamp, student_id))
    else:
        return jsonify({'error': 'Invalid report type'}), 400
    rows = c.fetchall()

    df = pd.DataFrame(rows, columns=['Name', 'Discipline', 'Score'])
    
    # Convert the 'Score' column to numeric
    df['Score'] = pd.to_numeric(df['Score'], errors='coerce')
    
    report = df.groupby(['Name', 'Discipline']).agg(['mean', 'median', lambda x: x.mode()[0] if len(x) > 0 else None, 'var']).reset_index().values.tolist()
    
    # Replace NaN with 0
    report = [[0 if pd.isna(val) else val for val in row] for row in report]
    return jsonify({'report': [{'name': row[0], 'discipline': row[1], 'average_score': row[2], 'median': row[3], 'mode': row[4], 'variance': row[5]} for row in report]})