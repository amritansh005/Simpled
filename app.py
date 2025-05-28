from flask import Flask, request, jsonify, render_template_string, render_template
from flask_cors import CORS
import sqlite3
import os
import re
from datetime import datetime
import openai

app = Flask(__name__)
CORS(app)

# Custom filter to parse JSON string to list
import json
@app.template_filter('json_to_tags')
def json_to_tags_filter(s):
    try:
        tags = json.loads(s)
        if isinstance(tags, list):
            return ['#' + str(tag).strip() for tag in tags if tag]
        return []
    except Exception:
        return []

# Configuration
DATABASE_NAME = 'user_portal.db'
PORT = 5000

def init_database():
    """Initialize the SQLite database with sample data"""
    conn = sqlite3.connect(DATABASE_NAME)
    cursor = conn.cursor()
    
    # Drop tables if they exist (for schema update)
    cursor.execute('DROP TABLE IF EXISTS users')
    cursor.execute('DROP TABLE IF EXISTS attendance')
    cursor.execute('DROP TABLE IF EXISTS notes')
    cursor.execute('DROP TABLE IF EXISTS subjects')
    cursor.execute('DROP TABLE IF EXISTS timetable')
    cursor.execute('DROP TABLE IF EXISTS test_scores')
    cursor.execute('DROP TABLE IF EXISTS notice_board')
    cursor.execute('DROP TABLE IF EXISTS polls')
    cursor.execute('DROP TABLE IF EXISTS poll_participants')
    cursor.execute('DROP TABLE IF EXISTS upcoming_tasks')

    # Create users table
    cursor.execute('''
        CREATE TABLE users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            first_name TEXT NOT NULL,
            last_name TEXT NOT NULL,
            email_address TEXT UNIQUE NOT NULL,
            phone_number TEXT NOT NULL,
            password TEXT NOT NULL,
            registration_date DATETIME DEFAULT CURRENT_TIMESTAMP
        )
    ''')

    # Create attendance table
    cursor.execute('''
        CREATE TABLE attendance (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            attended INTEGER,
            total INTEGER,
            FOREIGN KEY(user_id) REFERENCES users(id)
        )
    ''')

    # Create notes table
    cursor.execute('''
        CREATE TABLE notes (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            note_type TEXT,
            count INTEGER,
            FOREIGN KEY(user_id) REFERENCES users(id)
        )
    ''')

    # Create subjects table
    cursor.execute('''
        CREATE TABLE subjects (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            subject_name TEXT,
            FOREIGN KEY(user_id) REFERENCES users(id)
        )
    ''')

    # Create timetable table
    cursor.execute('''
        CREATE TABLE timetable (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            subject TEXT,
            date TEXT,
            time TEXT,
            status TEXT,
            duration TEXT,
            FOREIGN KEY(user_id) REFERENCES users(id)
        )
    ''')

    # Create test_scores table
    cursor.execute('''
        CREATE TABLE test_scores (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            subject TEXT,
            lesson TEXT,
            score REAL,
            FOREIGN KEY(user_id) REFERENCES users(id)
        )
    ''')

    # Create notice_board table
    cursor.execute('''
        CREATE TABLE notice_board (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            title TEXT,
            image_url TEXT,
            date TEXT,
            FOREIGN KEY(user_id) REFERENCES users(id)
        )
    ''')

    # Create polls table
    cursor.execute('''
        CREATE TABLE polls (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            title TEXT,
            professor TEXT,
            end_time TEXT,
            FOREIGN KEY(user_id) REFERENCES users(id)
        )
    ''')

    # Create poll_participants table
    cursor.execute('''
        CREATE TABLE poll_participants (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            poll_id INTEGER,
            participant_img TEXT,
            FOREIGN KEY(poll_id) REFERENCES polls(id)
        )
    ''')

    # Create upcoming_tasks table
    cursor.execute('''
        CREATE TABLE upcoming_tasks (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            code TEXT,
            title TEXT,
            time TEXT,
            FOREIGN KEY(user_id) REFERENCES users(id)
        )
    ''')

    # Drop score_activity table if it exists (for schema update)
    cursor.execute('DROP TABLE IF EXISTS score_activity')

    # Create score_activity table for subject-wise daily scores
    cursor.execute('''
        CREATE TABLE score_activity (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            subject TEXT,
            date TEXT,
            score INTEGER,
            FOREIGN KEY(user_id) REFERENCES users(id)
        )
    ''')

    # Drop queries table if it exists (for schema update)
    cursor.execute('DROP TABLE IF EXISTS queries')
    # Drop answers table if it exists (for schema update)
    cursor.execute('DROP TABLE IF EXISTS answers')

    # Create queries table for Raise Query submissions
    cursor.execute('''
        CREATE TABLE queries (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            special_mentions TEXT,
            brief TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')

    # Create answers table for teacher answers/comments
    cursor.execute('''
        CREATE TABLE answers (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            query_id INTEGER,
            answer_text TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY(query_id) REFERENCES queries(id)
        )
    ''')

    # Sample user data
    sample_users = [
        ('Alex', 'Johnson', 'alex.johnson@email.com', '+1 555-0101', 'password123'),
        ('Maria', 'Garcia', 'maria.garcia@email.com', '+1 555-0102', 'securepass'),
        ('David', 'Chen', 'david.chen@email.com', '+1 555-0103', 'davidpass'),
        ('Sarah', 'Williams', 'sarah.williams@email.com', '+1 555-0104', 'sarahpw'),
        ('Michael', 'Brown', 'michael.brown@email.com', '+1 555-0105', 'michaelpw'),
        ('Emily', 'Davis', 'emily.davis@email.com', '+1 555-0106', 'emilypw'),
        ('James', 'Miller', 'james.miller@email.com', '+1 555-0107', 'jamespw'),
        ('Lisa', 'Wilson', 'lisa.wilson@email.com', '+1 555-0108', 'lisapw'),
        ('Robert', 'Taylor', 'robert.taylor@email.com', '+1 555-0109', 'robertpw'),
        ('Jennifer', 'Anderson', 'jennifer.anderson@email.com', '+1 555-0110', 'jenniferpw')
    ]
    
    # Insert sample data
    user_ids = []
    for user in sample_users:
        cursor.execute('''
            INSERT OR IGNORE INTO users (first_name, last_name, email_address, phone_number, password) 
            VALUES (?, ?, ?, ?, ?)
        ''', user)
        user_ids.append(cursor.lastrowid if cursor.lastrowid else cursor.execute('SELECT id FROM users WHERE email_address=?', (user[2],)).fetchone()[0])

    # Insert dummy dashboard data for all users
    for idx, user_id in enumerate(user_ids):
        # Attendance (vary attended for each user for realism)
        attended = 254 - idx * 10 if (254 - idx * 10) > 0 else 100 + idx * 5
        total = 300
        cursor.execute('INSERT INTO attendance (user_id, attended, total) VALUES (?, ?, ?)', (user_id, attended, total))

        # Notes (vary counts slightly)
        cursor.execute('INSERT INTO notes (user_id, note_type, count) VALUES (?, ?, ?)', (user_id, "Personalised Notes", 254 - idx * 5))
        cursor.execute('INSERT INTO notes (user_id, note_type, count) VALUES (?, ?, ?)', (user_id, "Subject Planner", 25 + idx))
        cursor.execute('INSERT INTO notes (user_id, note_type, count) VALUES (?, ?, ?)', (user_id, "Notes & PPT", 50 + idx * 2))

        # Subjects (same subjects for all)
        for subject in ["Mathematics", "Physics", "Chemistry", "Economics", "Biology"]:
            cursor.execute('INSERT INTO subjects (user_id, subject_name) VALUES (?, ?)', (user_id, subject))

        # Score Activity (subject-wise daily scores for 14 days, only for Mathematics, Physics, Chemistry)
        import math
        import random
        from datetime import datetime, timedelta
        today = datetime.now()
        days = 14
        for subject in ["Mathematics", "Physics", "Chemistry"]:
            for i in range(days):
                date = (today - timedelta(days=days - i - 1)).strftime('%Y-%m-%d')
                if subject == "Mathematics":
                    score = 60 + int(20 * math.sin(i / 2.0) + 10 * math.cos(i / 3.0) + random.randint(-5, 5))
                elif subject == "Physics":
                    score = 45 + int(30 * math.cos(i / 1.7) + 8 * math.sin(i / 2.5) + random.randint(-8, 8))
                elif subject == "Chemistry":
                    score = 55 + int(18 * math.sin(i / 1.3) - 12 * math.cos(i / 2.2) + random.randint(-10, 10))
                else:
                    score = 50 + random.randint(-10, 10)
                score = max(0, min(100, score))
                cursor.execute('INSERT INTO score_activity (user_id, subject, date, score) VALUES (?, ?, ?, ?)', (user_id, subject, date, score))

        # Timetable (shift dates for each user)
        timetable_data = [
            ("Mathematics", "18-Apr-2022", "10:00 am", "Complete", "50 Minutes"),
            ("Physics", "18-Apr-2022", "11:05 pm", "Complete", "50 Minutes"),
            ("Chemistry", "18-Apr-2022", "02:00 pm", "Complete", "50 Minutes"),
            ("Physics", "19-Apr-2022", "10:00 am", "Pending", "50 Minutes"),
            ("Economics", "19-Apr-2022", "02:00 pm", "Pending", "50 Minutes"),
            ("Physics", "20-Apr-2022", "02:00 pm", "Pending", "50 Minutes"),
            ("Mathematics", "20-Apr-2022", "02:00 pm", "Pending", "50 Minutes"),
        ]
        for row in timetable_data:
            cursor.execute('INSERT INTO timetable (user_id, subject, date, time, status, duration) VALUES (?, ?, ?, ?, ?, ?)', (user_id, *row))

        # Test Scores (vary scores for each user)
        test_scores = [
            (8.5 - idx * 0.2, "Physics", "Lesson 4"),
            (6.0 + idx * 0.3, "Chemistry", "Lesson 2"),
            (7.2 + idx * 0.1, "Maths", "Lesson 2"),
            (9.0 - idx * 0.1, "Economics", "Lesson 2"),
            (8.0 + idx * 0.2, "Biology", "Lesson 2"),
            (8.8 - idx * 0.1, "Biology", "Lesson 6"),
            (6.8 + idx * 0.2, "Biology", "Lesson 5"),
        ]
        for score, subject, lesson in test_scores:
            cursor.execute('INSERT INTO test_scores (user_id, subject, lesson, score) VALUES (?, ?, ?, ?)', (user_id, subject, lesson, round(score, 1)))

        # Notice Board (dummy data)
        notice_data = [
            ("Weekly Maths MCQs & General", "https://images.unsplash.com/photo-1506744038136-46273834b3fb?auto=format&fit=facearea&w=48&h=48", "21 Apr 2022"),
            ("Weekly Physics MCQs", "https://images.unsplash.com/photo-1465101046530-73398c7f28ca?auto=format&fit=facearea&w=48&h=48", "22 Apr 2022"),
            ("Chemistry Quiz-22", "https://images.unsplash.com/photo-1519125323398-675f0ddb6308?auto=format&fit=facearea&w=48&h=48", "22 Apr 2022"),
            ("Biology Special Classes", "https://images.unsplash.com/photo-1462331940025-496dfbfc7564?auto=format&fit=facearea&w=48&h=48", "25 Apr 2022"),
        ]
        for title, img, date in notice_data:
            cursor.execute('INSERT INTO notice_board (user_id, title, image_url, date) VALUES (?, ?, ?, ?)', (user_id, title, img, date))

        # Ongoing Poll (one per user)
        cursor.execute('INSERT INTO polls (user_id, title, professor, end_time) VALUES (?, ?, ?, ?)', (
            user_id, "Maths Extra Class Poll", "Prof. Joshi", "22 Apr 2022, 12:30 pm"
        ))
        poll_id = cursor.lastrowid

        # Poll Participants (dummy avatars)
        poll_participants = [
            "https://randomuser.me/api/portraits/men/31.jpg",
            "https://randomuser.me/api/portraits/women/32.jpg",
            "https://randomuser.me/api/portraits/men/33.jpg",
            "https://randomuser.me/api/portraits/women/34.jpg",
            "https://randomuser.me/api/portraits/men/35.jpg",
        ]
        for img in poll_participants:
            cursor.execute('INSERT INTO poll_participants (poll_id, participant_img) VALUES (?, ?)', (poll_id, img))

        # Upcoming Tasks/Tests (dummy data)
        tasks = [
            ("P", "Metals Purification Methods", "08:30 am, 22 Apr 2022"),
            ("M", "Maths Algorithm", "08:30 am, 22 Apr 2022"),
            ("D", "DNA & RNA Modifications", "08:30 am, 22 Apr 2022"),
            ("F", "Fundamental Physics MCQs", "08:30 am, 22 Apr 2022"),
        ]
        for code, title, time in tasks:
            cursor.execute('INSERT INTO upcoming_tasks (user_id, code, title, time) VALUES (?, ?, ?, ?)', (user_id, code, title, time))

    conn.commit()
    conn.close()
    print(f"✅ Database '{DATABASE_NAME}' initialized successfully!")

def validate_email(email):
    """Validate email format"""
    pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
    return re.match(pattern, email) is not None

def validate_phone(phone):
    """Validate phone number format"""
    pattern = r'^[\+]?[0-9\s\-\(\)]{10,15}$'
    return re.match(pattern, phone) is not None

def validate_name(name):
    """Validate name (letters, spaces, hyphens only)"""
    pattern = r'^[a-zA-Z\s\-\']+$'
    return re.match(pattern, name) is not None

# HTML Template for the login page
LOGIN_TEMPLATE = '''
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>User Portal - Login</title>
    <style>
        * {
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }

        body {
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Oxygen, Ubuntu, Cantarell, sans-serif;
            background: linear-gradient(135deg, #6366f1 0%, #8b5cf6 100%);
            min-height: 100vh;
            display: flex;
            align-items: center;
            justify-content: center;
        }

        .portal-container {
            background: white;
            padding: 2.5rem;
            border-radius: 15px;
            box-shadow: 0 25px 50px rgba(0, 0, 0, 0.1);
            width: 100%;
            max-width: 420px;
        }

        .portal-header {
            text-align: center;
            margin-bottom: 2rem;
        }

        .portal-header h1 {
            color: #1f2937;
            margin-bottom: 0.5rem;
            font-size: 1.8rem;
        }

        .portal-header p {
            color: #6b7280;
            font-size: 0.95rem;
        }

        .input-group {
            margin-bottom: 1.5rem;
        }

        .input-group label {
            display: block;
            margin-bottom: 0.5rem;
            color: #374151;
            font-weight: 500;
        }

        .input-group input {
            width: 100%;
            padding: 0.875rem;
            border: 2px solid #e5e7eb;
            border-radius: 8px;
            font-size: 1rem;
            transition: all 0.3s ease;
        }

        .input-group input:focus {
            outline: none;
            border-color: #6366f1;
            box-shadow: 0 0 0 3px rgba(99, 102, 241, 0.1);
        }

        .submit-btn {
            width: 100%;
            padding: 0.875rem;
            background: linear-gradient(135deg, #6366f1 0%, #8b5cf6 100%);
            color: white;
            border: none;
            border-radius: 8px;
            font-size: 1rem;
            font-weight: 600;
            cursor: pointer;
            transition: all 0.3s ease;
        }

        .submit-btn:hover {
            transform: translateY(-2px);
            box-shadow: 0 10px 25px rgba(99, 102, 241, 0.3);
        }

        .message {
            padding: 0.875rem;
            border-radius: 8px;
            margin-bottom: 1rem;
            display: none;
        }

        .error-msg {
            background: #fef2f2;
            color: #dc2626;
            border: 1px solid #fecaca;
        }

        .success-msg {
            background: #f0fdf4;
            color: #16a34a;
            border: 1px solid #bbf7d0;
        }

        /* Success Modal */
        .modal-backdrop {
            position: fixed;
            top: 0;
            left: 0;
            width: 100%;
            height: 100%;
            background: rgba(0, 0, 0, 0.5);
            display: none;
            justify-content: center;
            align-items: center;
            z-index: 1000;
        }

        .modal-backdrop.active {
            display: flex;
        }

        .success-modal {
            background: white;
            padding: 2.5rem;
            border-radius: 15px;
            box-shadow: 0 25px 50px rgba(0, 0, 0, 0.25);
            text-align: center;
            max-width: 420px;
            width: 90%;
            animation: modalSlide 0.3s ease-out;
        }

        @keyframes modalSlide {
            from {
                transform: translateY(-30px);
                opacity: 0;
            }
            to {
                transform: translateY(0);
                opacity: 1;
            }
        }

        .success-icon {
            width: 70px;
            height: 70px;
            margin: 0 auto 1.5rem;
            background: #10b981;
            border-radius: 50%;
            display: flex;
            align-items: center;
            justify-content: center;
            color: white;
            font-size: 2.5rem;
        }

        .success-modal h3 {
            color: #1f2937;
            margin-bottom: 1rem;
            font-size: 1.4rem;
        }

        .success-modal p {
            color: #6b7280;
            margin-bottom: 2rem;
            line-height: 1.6;
        }

        .continue-btn {
            padding: 0.875rem 2.5rem;
            background: linear-gradient(135deg, #10b981 0%, #059669 100%);
            color: white;
            border: none;
            border-radius: 8px;
            font-size: 1rem;
            font-weight: 600;
            cursor: pointer;
            transition: all 0.3s ease;
        }

        .continue-btn:hover {
            transform: translateY(-2px);
            box-shadow: 0 8px 20px rgba(16, 185, 129, 0.3);
        }

        /* User Details Page */
        .user-details {
            display: none;
            background: white;
            padding: 2.5rem;
            border-radius: 15px;
            box-shadow: 0 25px 50px rgba(0, 0, 0, 0.1);
            width: 100%;
            max-width: 500px;
        }

        .user-details h2 {
            margin-bottom: 2rem;
            color: #1f2937;
            text-align: center;
        }

        .detail-item {
            display: flex;
            justify-content: space-between;
            align-items: center;
            padding: 1rem 0;
            border-bottom: 1px solid #f3f4f6;
        }

        .detail-item:last-child {
            border-bottom: none;
        }

        .detail-label {
            font-weight: 600;
            color: #6b7280;
        }

        .detail-value {
            color: #1f2937;
            font-weight: 500;
        }

        .logout-btn {
            margin-top: 2rem;
            width: 100%;
            padding: 0.75rem;
            background: #ef4444;
            color: white;
            border: none;
            border-radius: 8px;
            cursor: pointer;
            font-weight: 600;
            transition: all 0.3s ease;
        }

        .logout-btn:hover {
            background: #dc2626;
            transform: translateY(-1px);
        }
    </style>
</head>
<body>
    <!-- Login Form -->
    <div class="portal-container" id="loginContainer">
        <div class="portal-header">
            <h1>User Portal</h1>
            <p>Please enter your credentials to access your account</p>
        </div>
        
        <div class="message error-msg" id="errorMessage"></div>
        <div class="message success-msg" id="successMessage"></div>
        
        <form id="userLoginForm">
            <div class="input-group">
                <label for="email">Email Address</label>
                <input type="email" id="email" name="email" required>
            </div>
            
            <div class="input-group">
                <label for="password">Password</label>
                <input type="password" id="password" name="password" required>
            </div>
            
            <button type="submit" class="submit-btn">Access Account</button>
        </form>
    </div>

    <!-- User Details Page -->
    <div class="user-details" id="userDetails">
        <h2>Account Information</h2>
        <div class="detail-item">
            <span class="detail-label">First Name:</span>
            <span class="detail-value" id="userFirstName"></span>
        </div>
        <div class="detail-item">
            <span class="detail-label">Last Name:</span>
            <span class="detail-value" id="userLastName"></span>
        </div>
        <div class="detail-item">
            <span class="detail-label">Email Address:</span>
            <span class="detail-value" id="userEmail"></span>
        </div>
        <div class="detail-item">
            <span class="detail-label">Phone Number:</span>
            <span class="detail-value" id="userPhone"></span>
        </div>
        <button class="logout-btn" onclick="logout()">Sign Out</button>
    </div>

    <!-- Success Modal -->

    <script>
        document.getElementById('userLoginForm').addEventListener('submit', async function(e) {
            e.preventDefault();
            
            const email = document.getElementById('email').value;
            const password = document.getElementById('password').value;
            
            try {
                const response = await fetch('/api/authenticate', {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json',
                    },
                    body: JSON.stringify({ email, password })
                });
                
                const data = await response.json();
                
                if (response.ok) {
                    showUserDetails(data.user);
                } else {
                    showError(data.error || 'Authentication failed');
                }
            } catch (error) {
                showError('Connection error. Please try again.');
            }
        });

        function showUserDetails(user) {
            // Redirect to dashboard after successful login
            window.location.href = "/dashboard";
        }

        function logout() {
            document.getElementById('loginContainer').style.display = 'block';
            document.getElementById('userDetails').style.display = 'none';
            document.getElementById('userLoginForm').reset();
            hideMessages();
        }

        function showError(message) {
            const errorDiv = document.getElementById('errorMessage');
            errorDiv.textContent = message;
            errorDiv.style.display = 'block';
            document.getElementById('successMessage').style.display = 'none';
        }

        function showSuccess(message) {
            const successDiv = document.getElementById('successMessage');
            successDiv.textContent = message;
            successDiv.style.display = 'block';
            document.getElementById('errorMessage').style.display = 'none';
        }

        function hideMessages() {
            document.getElementById('errorMessage').style.display = 'none';
            document.getElementById('successMessage').style.display = 'none';
        }
    </script>
</body>
</html>
'''

# Routes
@app.route('/')
def home():
    """Serve the login page"""
    return render_template_string(LOGIN_TEMPLATE)

@app.route('/dashboard')
def dashboard():
    """Serve the dashboard page with dummy data from the database"""
    conn = sqlite3.connect(DATABASE_NAME)
    cursor = conn.cursor()

    # For demo, use the first user
    cursor.execute('SELECT id, first_name, last_name FROM users ORDER BY id LIMIT 1')
    user = cursor.fetchone()
    user_id = user[0] if user else 1
    user_name = f"{user[1]} {user[2]}" if user else "Student"

    # Attendance
    cursor.execute('SELECT attended, total FROM attendance WHERE user_id=?', (user_id,))
    attendance = cursor.fetchone()
    attendance_data = {'attended': attendance[0], 'total': attendance[1]} if attendance else {'attended': 0, 'total': 0}

    # Notes
    cursor.execute('SELECT note_type, count FROM notes WHERE user_id=?', (user_id,))
    notes = cursor.fetchall()
    notes_data = {row[0]: row[1] for row in notes}

    # Timetable
    cursor.execute('SELECT subject, date, time, status, duration FROM timetable WHERE user_id=? ORDER BY date, time', (user_id,))
    timetable = cursor.fetchall()

    # Test Scores
    cursor.execute('SELECT score, subject, lesson FROM test_scores WHERE user_id=? ORDER BY id', (user_id,))
    test_scores = cursor.fetchall()

    # Notice Board
    cursor.execute('SELECT title, image_url, date FROM notice_board WHERE user_id=? ORDER BY id', (user_id,))
    notice_board = cursor.fetchall()

    # Ongoing Poll (get latest poll for user)
    cursor.execute('SELECT id, title, professor, end_time FROM polls WHERE user_id=? ORDER BY id DESC LIMIT 1', (user_id,))
    poll = cursor.fetchone()
    poll_data = None
    poll_participants = []
    if poll:
        poll_id, poll_title, poll_prof, poll_end = poll
        poll_data = {
            'title': poll_title,
            'professor': poll_prof,
            'end_time': poll_end
        }
        cursor.execute('SELECT participant_img FROM poll_participants WHERE poll_id=?', (poll_id,))
        poll_participants = [row[0] for row in cursor.fetchall()]

    # Fetch subjects in a fixed order
    FIXED_SUBJECT_ORDER = ["Mathematics", "Chemistry", "Physics", "Economics", "Biology"]
    cursor.execute('SELECT subject_name FROM subjects WHERE user_id=?', (user_id,))
    user_subjects = [row[0] for row in cursor.fetchall()]
    # Keep only those in FIXED_SUBJECT_ORDER and preserve order
    ordered_subjects = [subj for subj in FIXED_SUBJECT_ORDER if subj in user_subjects]

    # Upcoming Tasks/Tests
    cursor.execute('SELECT code, title, time FROM upcoming_tasks WHERE user_id=? ORDER BY id', (user_id,))
    upcoming_tasks = cursor.fetchall()

    # Fetch queries for Doubt Forum
    cursor.execute('SELECT id, special_mentions, brief, created_at FROM queries ORDER BY created_at DESC')
    queries = cursor.fetchall()

    # Fetch answers for all queries
    cursor.execute('SELECT query_id, answer_text, created_at FROM answers ORDER BY created_at ASC')
    answers_raw = cursor.fetchall()
    answers = {}
    for query_id, answer_text, created_at in answers_raw:
        answers.setdefault(query_id, []).append({'text': answer_text, 'created_at': created_at})

    conn.close()

    return render_template(
        'dashboard.html',
        user_name=user_name,
        attendance=attendance_data,
        notes=notes_data,
        timetable=timetable,
        test_scores=test_scores,
        notice_board=notice_board,
        poll_data=poll_data,
        poll_participants=poll_participants,
        upcoming_tasks=upcoming_tasks,
        subjects=ordered_subjects,
        queries=queries,
        answers=answers
    )

@app.route('/api/authenticate', methods=['POST'])
def authenticate_user():
    """Authenticate user with email and password"""
    try:
        data = request.get_json()
        email = data.get('email', '').strip().lower()
        password = data.get('password', '').strip()
        
        # Validation
        if not email or not password:
            return jsonify({'error': 'Email address and password are required'}), 400
        
        if not validate_email(email):
            return jsonify({'error': 'Please enter a valid email address'}), 400
        
        # Database query
        conn = sqlite3.connect(DATABASE_NAME)
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT * FROM users 
            WHERE email_address = ? AND password = ?
        ''', (email, password))
        
        user = cursor.fetchone()
        conn.close()
        
        if user:
            user_data = {
                'id': user[0],
                'first_name': user[1],
                'last_name': user[2],
                'email_address': user[3],
                'phone_number': user[4],
                'full_name': f"{user[1]} {user[2]}"
            }
            
            return jsonify({
                'success': True,
                'message': 'Authentication successful',
                'user': user_data
            })
        else:
            # Check if email exists with different password
            conn = sqlite3.connect(DATABASE_NAME)
            cursor = conn.cursor()
            cursor.execute('SELECT email_address FROM users WHERE email_address = ?', (email,))
            email_exists = cursor.fetchone()
            conn.close()
            
            if email_exists:
                return jsonify({'error': 'Password does not match our records for this email'}), 401
            else:
                return jsonify({'error': 'No account found with these credentials'}), 401
                
    except Exception as e:
        return jsonify({'error': 'Server error occurred'}), 500

@app.route('/api/users', methods=['GET'])
def get_all_users():
    """Get all users (for testing/admin purposes)"""
    try:
        conn = sqlite3.connect(DATABASE_NAME)
        cursor = conn.cursor()
        cursor.execute('SELECT * FROM users')
        users = cursor.fetchall()
        conn.close()
        
        user_list = []
        for user in users:
            user_list.append({
                'id': user[0],
                'first_name': user[1],
                'last_name': user[2],
                'email_address': user[3],
                'phone_number': user[4],
                'registration_date': user[5]
            })
        
        return jsonify({'users': user_list})
        
    except Exception as e:
        return jsonify({'error': 'Server error occurred'}), 500

@app.route('/api/users', methods=['POST'])
def create_user():
    """Create a new user account"""
    try:
        data = request.get_json()
        first_name = data.get('first_name', '').strip()
        last_name = data.get('last_name', '').strip()
        email = data.get('email_address', '').strip().lower()
        phone = data.get('phone_number', '').strip()
        password = data.get('password', '').strip()
        
        # Validation
        if not all([first_name, last_name, email, phone, password]):
            return jsonify({'error': 'All fields are required'}), 400
        
        if not validate_name(first_name) or not validate_name(last_name):
            return jsonify({'error': 'Names should only contain letters, spaces, and hyphens'}), 400
        
        if not validate_email(email):
            return jsonify({'error': 'Please enter a valid email address'}), 400
        
        if not validate_phone(phone):
            return jsonify({'error': 'Please enter a valid phone number'}), 400
        
        # Database insertion
        conn = sqlite3.connect(DATABASE_NAME)
        cursor = conn.cursor()
        
        try:
            cursor.execute('''
                INSERT INTO users (first_name, last_name, email_address, phone_number, password) 
                VALUES (?, ?, ?, ?, ?)
            ''', (first_name, last_name, email, phone, password))
            
            user_id = cursor.lastrowid
            conn.commit()
            conn.close()
            
            return jsonify({
                'success': True,
                'message': 'User account created successfully',
                'user': {
                    'id': user_id,
                    'first_name': first_name,
                    'last_name': last_name,
                    'email_address': email,
                    'phone_number': phone,
                    'full_name': f"{first_name} {last_name}"
                }
            }), 201
            
        except sqlite3.IntegrityError:
            conn.close()
            return jsonify({'error': 'An account with this email already exists'}), 400
            
    except Exception as e:
        return jsonify({'error': 'Server error occurred'}), 500

@app.route('/api/users/<int:user_id>', methods=['DELETE'])
def delete_user(user_id):
    """Delete a user account"""
    try:
        conn = sqlite3.connect(DATABASE_NAME)
        cursor = conn.cursor()
        
        cursor.execute('DELETE FROM users WHERE id = ?', (user_id,))
        
        if cursor.rowcount == 0:
            conn.close()
            return jsonify({'error': 'User not found'}), 404
        
        conn.commit()
        conn.close()
        
        return jsonify({'success': True, 'message': 'User account deleted successfully'})
        
    except Exception as e:
        return jsonify({'error': 'Server error occurred'}), 500

@app.route('/api/performance-data', methods=['GET'])
def performance_data():
    """Return subject-wise score activity data for the current user from the database (for Performance tab)"""
    try:
        conn = sqlite3.connect(DATABASE_NAME)
        cursor = conn.cursor()
        # For demo, use the first user (same as dashboard)
        cursor.execute('SELECT id, first_name, last_name FROM users ORDER BY id LIMIT 1')
        user = cursor.fetchone()
        if not user:
            return jsonify({"error": "No user found"}), 404
        user_id, first, last = user
        subjects = ["Mathematics", "Physics", "Chemistry"]
        subject_data = {}
        for subject in subjects:
            cursor.execute('''
                SELECT date, score FROM score_activity
                WHERE user_id=? AND subject=?
                ORDER BY date ASC
                LIMIT 14
            ''', (user_id, subject))
            rows = cursor.fetchall()
            scores = [{"date": row[0], "score": row[1]} for row in rows]
            subject_data[subject] = scores
        conn.close()
        return jsonify({
            "user": f"{first} {last}",
            "subjects": subject_data
        })
    except Exception as e:
        return jsonify({"error": "Failed to fetch performance data"}), 500

# Video Streaming API: Returns random YouTube video links with metadata
import random

YOUTUBE_VIDEOS = [
    {
        "id": "eCZ5IDudt44",
        "title": "Electric Charges and Fields - Physics",
        "subject": "Physics"
    },
    {
        "id": "ESS3w7L7CAU",
        "title": "Arrangement & Application of Resistances",
        "subject": "Physics"
    },
    {
        "id": "NybHckSEQBI",
        "title": "Maths: Lesson 1 - Algebra Basics",
        "subject": "Maths"
    },
    {
        "id": "LwCRRUa8yTU",
        "title": "Maths: Lesson 2 - Linear Equations",
        "subject": "Maths"
    },
    {
        "id": "QX4j_zHAlw8",
        "title": "Chemistry: Lesson 2 - Atomic Structure",
        "subject": "Chemistry"
    }
]

@app.route('/api/videos', methods=['GET'])
def get_random_videos():
    """Return a random list of YouTube video links with metadata"""
    try:
        # Get a random sample of 4 videos for "Upcoming Next"
        upcoming = random.sample(YOUTUBE_VIDEOS, 4)
        # Pick one as the "currently playing" video
        current = random.choice(YOUTUBE_VIDEOS)
        def video_data(video):
            return {
                "id": video["id"],
                "title": video["title"],
                "subject": video["subject"],
                "url": f"https://www.youtube.com/watch?v={video['id']}",
                "thumbnail": f"https://img.youtube.com/vi/{video['id']}/hqdefault.jpg"
            }
        return jsonify({
            "current": video_data(current),
            "upcoming": [video_data(v) for v in upcoming]
        })
    except Exception as e:
        return jsonify({"error": "Failed to fetch videos"}), 500

@app.route('/raise-query')
def raise_query():
    return render_template('raise_query.html')

@app.route('/api/raise-query', methods=['POST'])
def api_raise_query():
    """
    Accepts special mentions (tags) and brief about the query,
    and inserts them into the queries table.
    """
    try:
        data = request.get_json()
        special_mentions = data.get('special_mentions', [])
        brief = data.get('brief', '').strip()
        if not brief:
            return jsonify({'error': 'Brief about your query is required'}), 400
        # Store special_mentions as JSON string
        import json
        special_mentions_json = json.dumps(special_mentions)
        conn = sqlite3.connect(DATABASE_NAME)
        cursor = conn.cursor()
        cursor.execute(
            'INSERT INTO queries (special_mentions, brief) VALUES (?, ?)',
            (special_mentions_json, brief)
        )
        conn.commit()
        conn.close()
        return jsonify({'success': True, 'message': 'Query submitted successfully'})
    except Exception as e:
        return jsonify({'error': 'Failed to submit query'}), 500

# Add Answer API (for teacher comments)
@app.route('/api/add-answer', methods=['POST'])
def add_answer():
    """
    Accepts query_id and answer_text, inserts into answers table.
    """
    try:
        data = request.get_json()
        query_id = data.get('query_id')
        answer_text = data.get('answer', '').strip()
        if not query_id or not answer_text:
            return jsonify({'error': 'Query ID and answer are required'}), 400
        conn = sqlite3.connect(DATABASE_NAME)
        cursor = conn.cursor()
        cursor.execute(
            'INSERT INTO answers (query_id, answer_text) VALUES (?, ?)',
            (query_id, answer_text)
        )
        conn.commit()
        # Fetch created_at for the new answer
        cursor.execute('SELECT created_at FROM answers WHERE id = ?', (cursor.lastrowid,))
        created_at = cursor.fetchone()[0]
        conn.close()
        return jsonify({'success': True, 'answer': answer_text, 'created_at': created_at})
    except Exception as e:
        return jsonify({'error': 'Failed to add answer'}), 500

# Doubt Solver API (OpenAI LLM)
@app.route('/api/doubt-solver', methods=['POST'])
def doubt_solver():
    """Accepts a student's doubt and returns an LLM-generated response using OpenAI API"""
    try:
        data = request.get_json()
        message = data.get('message', '').strip()
        if not message:
            return jsonify({'error': 'No doubt provided'}), 400

        api_key = os.environ.get('OPENAI_API_KEY')
        if not api_key:
            return jsonify({'error': 'OpenAI API key not set in environment'}), 500

        openai.api_key = api_key
        # Call OpenAI Chat API (gpt-3.5-turbo)
        response = openai.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=[
                {"role": "system", "content": "You are a helpful educational assistant. Answer student doubts in a very precise and short manner."},
                {"role": "user", "content": message}
            ],
            max_tokens=512,
            temperature=0.7
        )
        answer = response.choices[0].message.content.strip()
        return jsonify({'response': answer})
    except Exception as e:
        return jsonify({'error': 'Failed to get response from LLM'}), 500

# Error handlers
@app.errorhandler(404)
def not_found(error):
    return jsonify({'error': 'Endpoint not found'}), 404

@app.errorhandler(500)
def internal_error(error):
    return jsonify({'error': 'Internal server error'}), 500

def display_sample_credentials():
    """Display sample login credentials"""
    try:
        conn = sqlite3.connect(DATABASE_NAME)
        cursor = conn.cursor()
        cursor.execute('SELECT first_name, last_name, email_address, phone_number, password FROM users LIMIT 5')
        users = cursor.fetchall()
        conn.close()
        
        if users:
            print('\n📝 Sample login credentials for testing:')
            print('━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━')
            for i, user in enumerate(users, 1):
                print(f'{i}. {user[0]} {user[1]}')
                print(f'   📧 Email: {user[2]}')
                print(f'   🔑 Password: {user[4]}')
                print(f'   📱 Phone: {user[3]}')
                print('━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━')
                
    except Exception as e:
        print(f"Error displaying credentials: {e}")

if __name__ == '__main__':
    print('🚀 Initializing User Portal System...')
    init_database()
    display_sample_credentials()
    print(f'\n🌐 Server starting on http://localhost:{PORT}')
    print('✅ Ready to accept connections!')
    
    app.run(debug=True, host='0.0.0.0', port=PORT)
