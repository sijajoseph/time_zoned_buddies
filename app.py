from flask import Flask, render_template, request, jsonify, session
import pytz
from datetime import datetime
import sqlite3
import hashlib

app = Flask(__name__)
app.secret_key = 'your-secret-key-change-this'

# Initialize database
def init_db():
    conn = sqlite3.connect('users.db')
    conn.execute('''
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE NOT NULL,
            email TEXT UNIQUE NOT NULL,
            timezone TEXT NOT NULL,
            bio TEXT,
            activities TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    conn.commit()
    conn.close()

@app.before_first_request
def setup_database():
    init_db()

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/api/register', methods=['POST'])
def register():
    data = request.get_json()
    
    try:
        conn = sqlite3.connect('users.db')
        cursor = conn.cursor()
        
        # Check if user exists
        cursor.execute('SELECT id FROM users WHERE email = ?', (data['email'],))
        if cursor.fetchone():
            return jsonify({'error': 'Email already registered'}), 400
        
        # Insert new user
        cursor.execute('''
            INSERT INTO users (username, email, timezone, bio, activities)
            VALUES (?, ?, ?, ?, ?)
        ''', (data['username'], data['email'], data['timezone'], 
              data.get('bio', ''), ','.join(data.get('activities', []))))
        
        user_id = cursor.lastrowid
        conn.commit()
        conn.close()
        
        session['user_id'] = user_id
        session['username'] = data['username']
        session['timezone'] = data['timezone']
        
        return jsonify({'message': 'Registration successful', 'user_id': user_id}), 201
    
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/find-matches')
def find_matches():
    if 'user_id' not in session:
        return jsonify({'error': 'Not logged in'}), 401
    
    try:
        conn = sqlite3.connect('users.db')
        cursor = conn.cursor()
        
        # Get current user's timezone
        user_tz = session['timezone']
        time_range = int(request.args.get('time_range', 3))
        
        # Get all other users
        cursor.execute('SELECT * FROM users WHERE id != ?', (session['user_id'],))
        users = cursor.fetchall()
        conn.close()
        
        compatible_users = []
        
        for user in users:
            user_dict = {
                'id': user[0],
                'username': user[1],
                'email': user[2],
                'timezone': user[3],
                'bio': user[4] or 'No bio available',
                'activities': user[5].split(',') if user[5] else []
            }
            
            # Calculate time difference
            time_diff = calculate_time_difference(user_tz, user_dict['timezone'])
            if abs(time_diff) <= time_range:
                user_dict['time_difference'] = time_diff
                user_dict['current_time'] = get_current_time(user_dict['timezone'])
                compatible_users.append(user_dict)
        
        return jsonify({'matches': compatible_users})
    
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/timezones')
def get_timezones():
    common_timezones = [
        'US/Pacific', 'US/Mountain', 'US/Central', 'US/Eastern',
        'Europe/London', 'Europe/Paris', 'Europe/Berlin', 'Europe/Moscow',
        'Asia/Tokyo', 'Asia/Shanghai', 'Asia/Kolkata', 'Asia/Dubai',
        'Australia/Sydney', 'Australia/Melbourne'
    ]
    
    timezone_data = []
    for tz_name in common_timezones:
        tz = pytz.timezone(tz_name)
        current_time = datetime.now(tz)
        timezone_data.append({
            'name': tz_name,
            'display_name': tz_name.replace('_', ' '),
            'current_time': current_time.strftime('%H:%M'),
            'utc_offset': current_time.strftime('%z')
        })
    
    return jsonify({'timezones': timezone_data})

def calculate_time_difference(tz1, tz2):
    try:
        timezone1 = pytz.timezone(tz1)
        timezone2 = pytz.timezone(tz2)
        now = datetime.now(pytz.UTC)
        time1 = now.astimezone(timezone1)
        time2 = now.astimezone(timezone2)
        diff = (time1.utcoffset() - time2.utcoffset()).total_seconds() / 3600
        return round(diff, 1)
    except:
        return 0

def get_current_time(timezone_name):
    try:
        tz = pytz.timezone(timezone_name)
        current_time = datetime.now(tz)
        return current_time.strftime('%H:%M')
    except:
        return 'Unknown'

@app.route('/logout')
def logout():
    session.clear()
    return jsonify({'message': 'Logged out'}), 200

if __name__ == '__main__':
    app.run(debug=True)
