import os
import sqlite3
import time
from functools import wraps
from flask import Flask, render_template_string, request, redirect, url_for, session, flash
from werkzeug.security import generate_password_hash, check_password_hash

app = Flask(__name__)
# Security: Require a strong secret key from environment
app.secret_key = os.environ.get("SECRET_KEY", "motherson_super_secret_enterprise_key_2026")

DB_NAME = "motherson_portal.db"

# ==========================================
# 1. DATABASE INIT & SECURITY HELPERS
# ==========================================
def get_db():
    conn = sqlite3.connect(DB_NAME)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    conn = get_db()
    cursor = conn.cursor()
    
    # Users table: STRICT ROLE SYSTEM ('operator' by default)
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE NOT NULL,
            password_hash TEXT NOT NULL,
            role TEXT NOT NULL DEFAULT 'operator'
        )
    ''')
    
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS questions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            level INTEGER NOT NULL,
            title TEXT NOT NULL,
            description TEXT NOT NULL,
            question TEXT NOT NULL,
            opt_a TEXT NOT NULL,
            opt_b TEXT NOT NULL,
            opt_c TEXT NOT NULL,
            correct_opt TEXT NOT NULL,
            points INTEGER NOT NULL
        )
    ''')
    
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS scores (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT NOT NULL,
            score INTEGER NOT NULL,
            time_seconds REAL NOT NULL,
            completed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    
    # Seed System Admin (HARDCODED STRONG HASH)
    # Default Admin Password: Admin#Motherson2026!
    admin_hash = generate_password_hash("Admin#Motherson2026!")
    cursor.execute("SELECT * FROM users WHERE username = 'admin'")
    if not cursor.fetchone():
        cursor.execute("INSERT INTO users (username, password_hash, role) VALUES ('admin', ?, 'admin')", (admin_hash,))
    
    # Seed default sample question if empty
    cursor.execute("SELECT COUNT(*) FROM questions")
    if cursor.fetchone()[0] == 0:
        cursor.execute('''
            INSERT INTO questions (level, title, description, question, opt_a, opt_b, opt_c, correct_opt, points)
            VALUES (1, 'aPIMS Station Scanner Fault', 
                    'Assembly Line A scanner is unresponsive. Part numbers cannot be registered.',
                    'What is the recommended standard recovery action?',
                    'Reboot plant power cabinet', 'Unplug USB scanner, wait 5 seconds, reconnect', 'Reinstall OS', 'B', 100)
        ''')
    
    conn.commit()
    conn.close()

init_db()

# ==========================================
# 2. STRICT AUTHENTICATION & ACCESS CONTROL
# ==========================================
def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user' not in session:
            flash("Please log in to access this page.", "danger")
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated_function

def admin_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user' not in session:
            flash("Authentication required.", "danger")
            return redirect(url_for('login'))
        
        # DOUBLE VERIFICATION: Query database to ensure user role has NOT been tampered with
        conn = get_db()
        user = conn.execute("SELECT role FROM users WHERE username = ?", (session['user'],)).fetchone()
        conn.close()

        if not user or user['role'] != 'admin':
            flash("ACCESS DENIED: Administrative privileges required.", "danger")
            return redirect(url_for('dashboard'))
            
        return f(*args, **kwargs)
    return decorated_function

# ==========================================
# 3. HTML / TAILWIND UI TEMPLATE
# ==========================================
HTML_LAYOUT = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <title>Motherson IT Operations</title>
    <script src="https://cdn.tailwindcss.com"></script>
</head>
<body class="bg-slate-900 text-slate-100 font-sans min-h-screen flex flex-col">
    <nav class="bg-slate-800 border-b border-slate-700 px-6 py-4 flex justify-between items-center">
        <div class="flex items-center space-x-3">
            <span class="text-blue-500 text-xl font-bold">MOTHERSON</span>
            <span class="text-slate-400 text-sm">| Secure Command Center</span>
        </div>
        {% if session.get('user') %}
        <div class="flex items-center space-x-4">
            <span class="text-sm text-slate-300">User: <strong class="text-white">{{ session['user'] }}</strong></span>
            {% if session.get('role') == 'admin' %}
                <a href="/admin" class="bg-amber-600 hover:bg-amber-500 text-white text-xs font-bold px-3 py-1.5 rounded">Admin Panel</a>
            {% endif %}
            <a href="/dashboard" class="text-sm text-slate-300 hover:text-white">Dashboard</a>
            <a href="/logout" class="bg-red-600 hover:bg-red-500 text-white text-xs font-bold px-3 py-1.5 rounded">Logout</a>
        </div>
        {% endif %}
    </nav>
    <main class="flex-grow container mx-auto p-6 max-w-5xl">
        {% with messages = get_flashed_messages(with_categories=true) %}
          {% if messages %}
            {% for category, message in messages %}
              <div class="mb-4 p-4 rounded text-sm font-semibold {% if category == 'danger' %}bg-red-900/80 text-red-200 border border-red-700{% else %}bg-emerald-900/80 text-emerald-200 border border-emerald-700{% endif %}">
                {{ message }}
              </div>
            {% endfor %}
          {% endif %}
        {% endwith %}
        {% block content %}{% endblock %}
    </main>
</body>
</html>
"""

# ==========================================
# 4. APPLICATION ROUTES
# ==========================================
@app.route('/')
def index():
    return redirect(url_for('login'))

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form['username'].strip()
        password = request.form['password'].strip()
        
        if not username or not password:
            flash("Username and password are required.", "danger")
            return redirect(url_for('register'))

        hashed_pwd = generate_password_hash(password)
        conn = get_db()
        try:
            # EVERY NEW REGISTERED USER IS STRICTLY AN 'operator'
            conn.execute("INSERT INTO users (username, password_hash, role) VALUES (?, ?, 'operator')", 
                         (username, hashed_pwd))
            conn.commit()
            flash("Account created! Please log in.", "success")
            return redirect(url_for('login'))
        except sqlite3.IntegrityError:
            flash("Username already exists.", "danger")
        finally:
            conn.close()

    content = '''
    <div class="max-w-md mx-auto mt-12 bg-slate-800 p-8 rounded-lg border border-slate-700 shadow-xl">
        <h2 class="text-2xl font-bold text-white text-center mb-2">Create Operator Account</h2>
        <form method="POST" class="mt-6">
            <div class="mb-4">
                <label class="block text-slate-300 text-sm mb-2">Username / Employee ID</label>
                <input type="text" name="username" required class="w-full bg-slate-900 border border-slate-700 rounded px-3 py-2 text-white">
            </div>
            <div class="mb-6">
                <label class="block text-slate-300 text-sm mb-2">Password</label>
                <input type="password" name="password" required class="w-full bg-slate-900 border border-slate-700 rounded px-3 py-2 text-white">
            </div>
            <button type="submit" class="w-full bg-emerald-600 hover:bg-emerald-500 text-white font-bold py-2 rounded">Register Account</button>
        </form>
        <p class="text-xs text-center text-slate-400 mt-4">Already have an account? <a href="/login" class="text-blue-400 hover:underline">Log in here</a></p>
    </div>
    '''
    return render_template_string(HTML_LAYOUT.replace('{% block content %}{% endblock %}', content))

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username'].strip()
        password = request.form['password'].strip()
        
        conn = get_db()
        user = conn.execute("SELECT * FROM users WHERE username = ?", (username,)).fetchone()
        conn.close()
        
        if user and check_password_hash(user['password_hash'], password):
            session['user'] = user['username']
            session['role'] = user['role']
            return redirect(url_for('dashboard'))
        else:
            flash("Invalid credentials.", "danger")
            
    content = '''
    <div class="max-w-md mx-auto mt-12 bg-slate-800 p-8 rounded-lg border border-slate-700 shadow-xl">
        <h2 class="text-2xl font-bold text-white text-center mb-2">System Login</h2>
        <form method="POST" class="mt-6">
            <div class="mb-4">
                <label class="block text-slate-300 text-sm mb-2">Username / Employee ID</label>
                <input type="text" name="username" required class="w-full bg-slate-900 border border-slate-700 rounded px-3 py-2 text-white">
            </div>
            <div class="mb-6">
                <label class="block text-slate-300 text-sm mb-2">Password</label>
                <input type="password" name="password" required class="w-full bg-slate-900 border border-slate-700 rounded px-3 py-2 text-white">
            </div>
            <button type="submit" class="w-full bg-blue-600 hover:bg-blue-500 text-white font-bold py-2 rounded">Login</button>
        </form>
        <p class="text-xs text-center text-slate-400 mt-4">New user? <a href="/register" class="text-blue-400 hover:underline">Create an account</a></p>
    </div>
    '''
    return render_template_string(HTML_LAYOUT.replace('{% block content %}{% endblock %}', content))

@app.route('/dashboard')
@login_required
def dashboard():
    conn = get_db()
    rankings = conn.execute('''
        SELECT username, score, time_seconds, completed_at 
        FROM scores ORDER BY score DESC, time_seconds ASC LIMIT 10
    ''').fetchall()
    conn.close()

    content = '''
    <div class="grid grid-cols-1 md:grid-cols-2 gap-6">
        <div class="bg-slate-800 p-6 rounded-lg border border-slate-700">
            <h3 class="text-xl font-bold text-blue-400 mb-2">Incident Response Protocol</h3>
            <p class="text-slate-300 text-sm mb-6">
                Test your troubleshooting speed across plant systems.
            </p>
            <a href="/start-game" class="inline-block bg-emerald-600 hover:bg-emerald-500 text-white font-bold px-6 py-3 rounded text-center w-full">
                ▶ Start Incident Simulation
            </a>
        </div>
        <div class="bg-slate-800 p-6 rounded-lg border border-slate-700">
            <h3 class="text-xl font-bold text-white mb-4">🏆 Top Operator Rankings</h3>
            <table class="w-full text-left text-sm text-slate-300">
                <thead class="bg-slate-900 text-slate-400">
                    <tr>
                        <th class="p-2">#</th>
                        <th class="p-2">Operator</th>
                        <th class="p-2">Score</th>
                        <th class="p-2">Time</th>
                    </tr>
                </thead>
                <tbody>
                    {% for r in rankings %}
                    <tr class="border-b border-slate-700">
                        <td class="p-2 font-bold text-blue-400">{{ loop.index }}</td>
                        <td class="p-2">{{ r['username'] }}</td>
                        <td class="p-2 font-semibold text-emerald-400">{{ r['score'] }} pts</td>
                        <td class="p-2 text-slate-400">{{ "%.1f"|format(r['time_seconds']) }}s</td>
                    </tr>
                    {% endfor %}
                </tbody>
            </table>
        </div>
    </div>
    '''
    return render_template_string(HTML_LAYOUT.replace('{% block content %}{% endblock %}', content), rankings=rankings)

@app.route('/start-game')
@login_required
def start_game():
    session['game_score'] = 0
    session['game_start_time'] = time.time()
    return redirect(url_for('play_level', level=1))

@app.route('/play/<int:level>', methods=['GET', 'POST'])
@login_required
def play_level(level):
    conn = get_db()
    question = conn.execute("SELECT * FROM questions WHERE level = ?", (level,)).fetchone()
    
    if not question:
        conn.close()
        total_time = time.time() - session.get('game_start_time', time.time())
        score = session.get('game_score', 0)
        
        conn = get_db()
        conn.execute("INSERT INTO scores (username, score, time_seconds) VALUES (?, ?, ?)",
                     (session['user'], score, total_time))
        conn.commit()
        conn.close()
        
        flash(f"Simulation completed! Score: {score} pts in {total_time:.1f}s", "success")
        return redirect(url_for('dashboard'))

    if request.method == 'POST':
        selected = request.form.get('option')
        if selected == question['correct_opt']:
            session['game_score'] = session.get('game_score', 0) + question['points']
            flash(f"Level {level} Resolved! +{question['points']} pts", "success")
            conn.close()
            return redirect(url_for('play_level', level=level+1))
        else:
            flash("Incorrect recovery action! System remains down.", "danger")

    conn.close()
    content = '''
    <div class="max-w-2xl mx-auto bg-slate-800 p-8 rounded-lg border border-slate-700">
        <div class="text-xs font-bold text-blue-400 mb-1">INCIDENT LEVEL {{ question['level'] }}</div>
        <h2 class="text-2xl font-bold text-white mb-4">{{ question['title'] }}</h2>
        <p class="text-slate-300 text-sm mb-6 bg-slate-900 p-4 rounded border border-slate-700">{{ question['description'] }}</p>
        
        <p class="font-semibold text-white mb-4">{{ question['question'] }}</p>
        
        <form method="POST" class="space-y-3">
            <button type="submit" name="option" value="A" class="w-full text-left bg-slate-900 hover:bg-blue-900/50 p-4 rounded border border-slate-700 text-sm">
                [A] {{ question['opt_a'] }}
            </button>
            <button type="submit" name="option" value="B" class="w-full text-left bg-slate-900 hover:bg-blue-900/50 p-4 rounded border border-slate-700 text-sm">
                [B] {{ question['opt_b'] }}
            </button>
            <button type="submit" name="option" value="C" class="w-full text-left bg-slate-900 hover:bg-blue-900/50 p-4 rounded border border-slate-700 text-sm">
                [C] {{ question['opt_c'] }}
            </button>
        </form>
    </div>
    '''
    return render_template_string(HTML_LAYOUT.replace('{% block content %}{% endblock %}', content), question=question)

# ==========================================
# 5. SECURE ADMIN ROUTE (RESTRICTED)
# ==========================================
@app.route('/admin', methods=['GET', 'POST'])
@login_required
@admin_required
def admin_panel():
    conn = get_db()
    if request.method == 'POST':
        level = request.form['level']
        title = request.form['title']
        desc = request.form['description']
        q = request.form['question']
        opt_a = request.form['opt_a']
        opt_b = request.form['opt_b']
        opt_c = request.form['opt_c']
        correct = request.form['correct_opt']
        pts = request.form['points']
        
        conn.execute('''
            INSERT INTO questions (level, title, description, question, opt_a, opt_b, opt_c, correct_opt, points)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (level, title, desc, q, opt_a, opt_b, opt_c, correct, pts))
        conn.commit()
        flash("New incident scenario added to the database!", "success")

    questions = conn.execute("SELECT * FROM questions ORDER BY level ASC").fetchall()
    users = conn.execute("SELECT id, username, role FROM users").fetchall()
    conn.close()

    content = '''
    <div class="space-y-8">
        <div class="bg-slate-800 p-6 rounded-lg border border-slate-700">
            <h3 class="text-xl font-bold text-amber-400 mb-4">⚙️ IT Supervisor Admin Control Panel</h3>
            <form method="POST" class="grid grid-cols-1 md:grid-cols-2 gap-4 text-sm">
                <div>
                    <label class="block text-slate-300 mb-1">Level Order</label>
                    <input type="number" name="level" required class="w-full bg-slate-900 border border-slate-700 p-2 rounded text-white">
                </div>
                <div>
                    <label class="block text-slate-300 mb-1">Points Value</label>
                    <input type="number" name="points" value="100" required class="w-full bg-slate-900 border border-slate-700 p-2 rounded text-white">
                </div>
                <div class="md:col-span-2">
                    <label class="block text-slate-300 mb-1">Incident Title</label>
                    <input type="text" name="title" required class="w-full bg-slate-900 border border-slate-700 p-2 rounded text-white">
                </div>
                <div class="md:col-span-2">
                    <label class="block text-slate-300 mb-1">Incident Description</label>
                    <textarea name="description" required class="w-full bg-slate-900 border border-slate-700 p-2 rounded text-white h-20"></textarea>
                </div>
                <div class="md:col-span-2">
                    <label class="block text-slate-300 mb-1">Diagnostic Question</label>
                    <input type="text" name="question" required class="w-full bg-slate-900 border border-slate-700 p-2 rounded text-white">
                </div>
                <div>
                    <label class="block text-slate-300 mb-1">Option [A]</label>
                    <input type="text" name="opt_a" required class="w-full bg-slate-900 border border-slate-700 p-2 rounded text-white">
                </div>
                <div>
                    <label class="block text-slate-300 mb-1">Option [B]</label>
                    <input type="text" name="opt_b" required class="w-full bg-slate-900 border border-slate-700 p-2 rounded text-white">
                </div>
                <div>
                    <label class="block text-slate-300 mb-1">Option [C]</label>
                    <input type="text" name="opt_c" required class="w-full bg-slate-900 border border-slate-700 p-2 rounded text-white">
                </div>
                <div>
                    <label class="block text-slate-300 mb-1">Correct Choice</label>
                    <select name="correct_opt" class="w-full bg-slate-900 border border-slate-700 p-2 rounded text-white">
                        <option value="A">A</option>
                        <option value="B">B</option>
                        <option value="C">C</option>
                    </select>
                </div>
                <div class="md:col-span-2 mt-2">
                    <button type="submit" class="bg-amber-600 hover:bg-amber-500 text-white font-bold px-4 py-2 rounded">Add Scenario to Live App</button>
                </div>
            </form>
        </div>

        <div class="bg-slate-800 p-6 rounded-lg border border-slate-700">
            <h4 class="font-bold text-white mb-4">Registered Accounts & Roles</h4>
            <table class="w-full text-left text-sm text-slate-300">
                <thead class="bg-slate-900 text-slate-400">
                    <tr>
                        <th class="p-2">ID</th>
                        <th class="p-2">Username</th>
                        <th class="p-2">Role</th>
                    </tr>
                </thead>
                <tbody>
                    {% for u in users %}
                    <tr class="border-b border-slate-700">
                        <td class="p-2">{{ u['id'] }}</td>
                        <td class="p-2 font-bold text-white">{{ u['username'] }}</td>
                        <td class="p-2"><span class="{% if u['role'] == 'admin' %}text-amber-400{% else %}text-slate-400{% endif %} uppercase text-xs font-bold">{{ u['role'] }}</span></td>
                    </tr>
                    {% endfor %}
                </tbody>
            </table>
        </div>
    </div>
    '''
    return render_template_string(HTML_LAYOUT.replace('{% block content %}{% endblock %}', content), questions=questions, users=users)

@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('login'))

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)