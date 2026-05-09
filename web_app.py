from flask import Flask, render_template, request
import sqlite3
from datetime import datetime

app = Flask(__name__)
SECRET_TEACHER_PIN = "1234"

def get_db():
    return sqlite3.connect('safari_kid.db')

@app.route('/')
def home():
    return render_template('index.html')

@app.route('/register')
def register_page():
    return render_template('register.html')

@app.route('/roster')
def roster():
    passcode = request.args.get('code')
    if passcode != SECRET_TEACHER_PIN:
        return "<h1>Access Denied</h1><a href='/'>Go Back</a>"

    conn = get_db()
    cursor = conn.cursor()
    today = datetime.now().strftime("%Y-%m-%d")
    
    # Updated query to include Classroom and sort by it
    query = """
        SELECT Students.Name, Students.StudentID, Attendance.TimeIn, Students.Classroom 
        FROM Attendance 
        JOIN Students ON Attendance.StudentID = Students.StudentID 
        WHERE Attendance.Date = ? AND Attendance.TimeOut IS NULL
        ORDER BY Students.Classroom ASC
    """
    cursor.execute(query, (today,))
    rows = cursor.fetchall()
    
    active_students = []
    for row in rows:
        active_students.append({
            'name': row[0], 
            'sid': row[1], 
            'time_in': row[2], 
            'classroom': row[3] # New data point
        })
    
    conn.close()
    return render_template('roster.html', students=active_students)

@app.route('/add_student', methods=['POST'])
def add_student():
    sid = request.form['sid']
    name = request.form['name']
    email = request.form['email']
    classroom = request.form['classroom'] # Capture classroom input
    
    conn = get_db()
    cursor = conn.cursor()
    try:
        # Added Classroom to the SQL INSERT
        cursor.execute("INSERT INTO Students (StudentID, Name, ParentEmail, Classroom) VALUES (?, ?, ?, ?)", 
                       (sid, name, email, classroom))
        conn.commit()
        msg = f"Successfully registered {name} in {classroom}!"
    except:
        msg = "Error: Registration failed."
    finally:
        conn.close()
    return f"<h1>{msg}</h1><br><a href='/'>Go to Check-In</a>"

@app.route('/checkin', methods=['POST'])
def checkin():
    sid = request.form['sid']
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("SELECT Name FROM Students WHERE StudentID=?", (sid,))
    student_data = cursor.fetchone()
    
    if not student_data:
        conn.close()
        return f"<h1>Error: Student ID {sid} not found.</h1><br><a href='/register'>Register them here</a>"
    
    student_name = student_data[0]
    cursor.execute("SELECT LogID FROM Attendance WHERE StudentID=? AND TimeOut IS NULL", (sid,))
    active_session = cursor.fetchone()
    now = datetime.now().strftime("%H:%M:%S")
    
    if active_session:
        cursor.execute("UPDATE Attendance SET TimeOut=? WHERE LogID=?", (now, active_session[0]))
        msg = f"Student {student_name} Checked Out at {now}"
    else:
        cursor.execute("INSERT INTO Attendance (StudentID, Date, TimeIn) VALUES (?, ?, ?)", 
                       (sid, datetime.now().strftime("%Y-%m-%d"), now))
        msg = f"Student {student_name} Checked In at {now}"
    
    conn.commit()
    conn.close()
    return f"<h1>{msg}</h1><p><a href='/billing/{sid}'>View Billing</a> | <a href='/roster?code={SECRET_TEACHER_PIN}'>View Live Roster</a></p><br><a href='/'>Go Back</a>"

@app.route('/billing/<sid>')
def billing(sid):
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("SELECT Name FROM Students WHERE StudentID=?", (sid,))
    student_name = cursor.fetchone()[0]
    cursor.execute("SELECT Date, TimeIn, TimeOut FROM Attendance WHERE StudentID=?", (sid,))
    records = cursor.fetchall()
    total_hours, billing_data, hourly_rate = 0, [], 15.0
    for row in records:
        date, tin, tout = row
        if tout:
            t1, t2 = datetime.strptime(tin, "%H:%M:%S"), datetime.strptime(tout, "%H:%M:%S")
            duration = (t2 - t1).total_seconds() / 3600
            total_hours += duration
            billing_data.append({'date': date, 'duration': round(duration, 2), 'cost': round(duration * hourly_rate, 2)})
    total_bill = round(total_hours * hourly_rate, 2)
    conn.close()
    return render_template('billing.html', name=student_name, logs=billing_data, total=total_bill)

@app.route('/admin/billing')
def admin_billing():
    passcode = request.args.get('code')
    if passcode != SECRET_TEACHER_PIN:
        return "<h1>Access Denied</h1><a href='/'>Go Back</a>"
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("SELECT StudentID, Name FROM Students")
    all_students = cursor.fetchall()
    master_ledger, hourly_rate = [], 15.0
    for student in all_students:
        sid, name = student
        cursor.execute("SELECT TimeIn, TimeOut FROM Attendance WHERE StudentID=?", (sid,))
        logs = cursor.fetchall()
        student_total_hours = 0
        for log in logs:
            tin, tout = log
            if tout:
                t1, t2 = datetime.strptime(tin, "%H:%M:%S"), datetime.strptime(tout, "%H:%M:%S")
                student_total_hours += (t2 - t1).total_seconds() / 3600
        master_ledger.append({'name': name, 'id': sid, 'total_bill': round(student_total_hours * hourly_rate, 2)})
    conn.close()
    return render_template('admin_billing.html', ledger=master_ledger)

if __name__ == '__main__':
    app.run(debug=True)