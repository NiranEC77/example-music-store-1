from flask import Flask, request, jsonify, session
import sqlite3
import os
import hashlib
import secrets
from functools import wraps

app = Flask(__name__)
app.secret_key = 'users-secret-key-here'

# Configuration
USERS_DB_PATH = os.environ.get('USERS_DB_PATH', 'users.db')

def init_users_db():
    """Initialize the users database with default admin user"""
    with sqlite3.connect(USERS_DB_PATH) as conn:
        c = conn.cursor()
        c.execute('''CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE NOT NULL,
            password_hash TEXT NOT NULL,
            role TEXT NOT NULL DEFAULT 'user',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )''')
        
        # Check if admin user exists, if not create it
        admin_exists = c.execute('SELECT id FROM users WHERE username = ?', ('admin',)).fetchone()
        if not admin_exists:
            # Create admin user with password 'admin'
            admin_password_hash = hashlib.sha256('admin'.encode()).hexdigest()
            c.execute('INSERT INTO users (username, password_hash, role) VALUES (?, ?, ?)', 
                     ('admin', admin_password_hash, 'admin'))
            print("Created default admin user: admin/admin")
        
        conn.commit()

init_users_db()

def hash_password(password):
    """Hash a password using SHA-256"""
    return hashlib.sha256(password.encode()).hexdigest()

def verify_password(password, password_hash):
    """Verify a password against its hash"""
    return hash_password(password) == password_hash

def generate_session_token():
    """Generate a random session token"""
    return secrets.token_hex(32)

@app.route('/api/login', methods=['POST'])
def login():
    """Handle user login"""
    data = request.get_json()
    
    if not data or 'username' not in data or 'password' not in data:
        return jsonify({'error': 'Username and password are required'}), 400
    
    username = data['username']
    password = data['password']
    
    with sqlite3.connect(USERS_DB_PATH) as conn:
        c = conn.cursor()
        user = c.execute('SELECT id, username, password_hash, role FROM users WHERE username = ?', 
                        (username,)).fetchone()
    
    if not user:
        return jsonify({'error': 'Invalid username or password'}), 401
    
    user_id, db_username, password_hash, role = user
    
    if not verify_password(password, password_hash):
        return jsonify({'error': 'Invalid username or password'}), 401
    
    # Generate session token
    session_token = generate_session_token()
    
    # Store session in database (in production, use Redis or similar)
    with sqlite3.connect(USERS_DB_PATH) as conn:
        c = conn.cursor()
        c.execute('''CREATE TABLE IF NOT EXISTS sessions (
            token TEXT PRIMARY KEY,
            user_id INTEGER NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )''')
        c.execute('INSERT INTO sessions (token, user_id) VALUES (?, ?)', (session_token, user_id))
        conn.commit()
    
    return jsonify({
        'success': True,
        'token': session_token,
        'user': {
            'id': user_id,
            'username': db_username,
            'role': role
        }
    })

@app.route('/api/logout', methods=['POST'])
def logout():
    """Handle user logout"""
    data = request.get_json()
    
    if not data or 'token' not in data:
        return jsonify({'error': 'Token is required'}), 400
    
    token = data['token']
    
    with sqlite3.connect(USERS_DB_PATH) as conn:
        c = conn.cursor()
        c.execute('DELETE FROM sessions WHERE token = ?', (token,))
        conn.commit()
    
    return jsonify({'success': True, 'message': 'Logged out successfully'})

@app.route('/api/verify', methods=['POST'])
def verify_token():
    """Verify if a session token is valid"""
    data = request.get_json()
    
    if not data or 'token' not in data:
        return jsonify({'error': 'Token is required'}), 400
    
    token = data['token']
    
    with sqlite3.connect(USERS_DB_PATH) as conn:
        c = conn.cursor()
        session_data = c.execute('''
            SELECT s.user_id, u.username, u.role 
            FROM sessions s 
            JOIN users u ON s.user_id = u.id 
            WHERE s.token = ?
        ''', (token,)).fetchone()
    
    if not session_data:
        return jsonify({'error': 'Invalid or expired token'}), 401
    
    user_id, username, role = session_data
    
    return jsonify({
        'valid': True,
        'user': {
            'id': user_id,
            'username': username,
            'role': role
        }
    })

@app.route('/api/users', methods=['GET'])
def get_users():
    """Get all users (admin only)"""
    data = request.get_json() if request.is_json else {}
    token = data.get('token') or request.args.get('token')
    
    if not token:
        return jsonify({'error': 'Token is required'}), 401
    
    # Verify token and check if user is admin
    with sqlite3.connect(USERS_DB_PATH) as conn:
        c = conn.cursor()
        session_data = c.execute('''
            SELECT s.user_id, u.username, u.role 
            FROM sessions s 
            JOIN users u ON s.user_id = u.id 
            WHERE s.token = ?
        ''', (token,)).fetchone()
    
    if not session_data:
        return jsonify({'error': 'Invalid or expired token'}), 401
    
    user_id, username, role = session_data
    
    if role != 'admin':
        return jsonify({'error': 'Admin access required'}), 403
    
    # Get all users
    with sqlite3.connect(USERS_DB_PATH) as conn:
        c = conn.cursor()
        users = c.execute('SELECT id, username, role, created_at FROM users').fetchall()
    
    return jsonify({
        'users': [
            {
                'id': user[0],
                'username': user[1],
                'role': user[2],
                'created_at': user[3]
            }
            for user in users
        ]
    })

@app.route('/health')
def health():
    """Health check endpoint"""
    return jsonify({'status': 'healthy', 'service': 'users-service'})

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5003, debug=True) 