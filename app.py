import sqlite3
from datetime import datetime

# --- DATABASE SETUP ---
conn = sqlite3.connect('safari_kid.db')
cursor = conn.cursor()

# Create tables
cursor.execute('''CREATE TABLE IF NOT EXISTS Students 
                  (StudentID TEXT PRIMARY KEY, Name TEXT, ParentEmail TEXT)''')

# Added "Hours" column to track duration for billing
cursor.execute('''CREATE TABLE IF NOT EXISTS Attendance 
                  (LogID INTEGER PRIMARY KEY AUTOINCREMENT, StudentID TEXT, 
                   Date TEXT, TimeIn TEXT, TimeOut TEXT, Hours REAL,
                   FOREIGN KEY(StudentID) REFERENCES Students(StudentID))''')
conn.commit()

# --- SYSTEM FUNCTIONS ---

def register_student():
    """Process 2.0: Registering a new student"""
    print("\n--- New Student Registration ---")
    sid = input("Enter New Student ID: ")
    name = input("Enter Student Name: ")
    email = input("Enter Parent Email: ")
    try:
        cursor.execute("INSERT INTO Students VALUES (?, ?, ?)", (sid, name, email))
        conn.commit()
        print(f"Registration successful for {name}!")
    except sqlite3.IntegrityError:
        print("Error: That Student ID already exists.")

def check_in():
    """Process 1.0: Capture Check-In and Process 3.0: Send Alert"""
    print("\n--- Student Check-In ---")
    sid = input("Scan or Enter Student ID: ")
    cursor.execute("SELECT Name, ParentEmail FROM Students WHERE StudentID=?", (sid,))
    student = cursor.fetchone()
    
    if student:
        name, email = student
        now = datetime.now()
        cursor.execute("INSERT INTO Attendance (StudentID, Date, TimeIn) VALUES (?, ?, ?)", 
                       (sid, now.strftime("%Y-%m-%d"), now.strftime("%H:%M:%S")))
        conn.commit()
        print(f"Check-in Success: {name} at {now.strftime('%H:%M:%S')}")
        print(f">>> ALERT: Notification sent to {email}")
    else:
        print("Error: Student ID not found.")

def check_out():
    """Update existing log with TimeOut and calculate duration"""
    print("\n--- Student Check-Out ---")
    sid = input("Scan or Enter Student ID: ")
    
    # Find the most recent check-in for this student that doesn't have a check-out yet
    cursor.execute('''SELECT LogID, TimeIn FROM Attendance 
                      WHERE StudentID=? AND TimeOut IS NULL 
                      ORDER BY LogID DESC LIMIT 1''', (sid,))
    record = cursor.fetchone()
    
    if record:
        log_id, time_in = record
        now = datetime.now()
        time_out = now.strftime("%H:%M:%S")
        
        # Calculate duration in hours
        fmt = "%H:%M:%S"
        duration = datetime.strptime(time_out, fmt) - datetime.strptime(time_in, fmt)
        hours = round(duration.total_seconds() / 3600, 2)
        
        cursor.execute("UPDATE Attendance SET TimeOut=?, Hours=? WHERE LogID=?", 
                       (time_out, hours, log_id))
        conn.commit()
        print(f"Check-out Success! Duration: {hours} hours.")
    else:
        print("Error: No active check-in found for this ID.")

def billing_report():
    """Process 4.0: Weekly/Monthly Billing Report"""
    print("\n--- Weekly/Monthly Billing Summary ---")
    print("Format: [Student Name] | [Total Hours] | [Estimated Charge]")
    
    # Sum up all hours for each student
    cursor.execute('''SELECT Students.Name, SUM(Attendance.Hours) 
                      FROM Attendance 
                      JOIN Students ON Attendance.StudentID = Students.StudentID
                      WHERE Attendance.Hours IS NOT NULL
                      GROUP BY Students.StudentID''')
    rows = cursor.fetchall()
    
    rate_per_hour = 25  # Example hourly rate for Burlington facility
    
    if not rows:
        print("No billing data available for this period.")
    for row in rows:
        name, total_hours = row
        total_charge = total_hours * rate_per_hour
        print(f"{name.ljust(15)} | {str(total_hours).ljust(11)} | ${total_charge:,.2f}")

# --- MAIN MENU ---

def main():
    while True:
        print("\n--- SAFARI KID BURLINGTON: ATTENDANCE & BILLING ---")
        print("1. Student Check-In")
        print("2. Student Check-Out")
        print("3. Register New Student")
        print("4. View Billing Report (Weekly/Monthly)")
        print("5. Exit")
        
        choice = input("\nSelect an option: ")
        if choice == '1': check_in()
        elif choice == '2': check_out()
        elif choice == '3': register_student()
        elif choice == '4': billing_report()
        elif choice == '5': break

if __name__ == "__main__":
    main()