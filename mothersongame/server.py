import os
import sqlite3
import time
from functools import wraps
from flask import Flask, render_template_string, request, redirect, url_for, session, flash
from werkzeug.security import generate_password_hash, check_password_hash

app = Flask(__name__)
app.secret_key = os.environ.get("SECRET_KEY", "motherson_enterprise_key_2026_prod")

DB_NAME = "motherson_portal.db"

# ==========================================
# 1. DATABASE INIT
# ==========================================
def get_db():
    conn = sqlite3.connect(DB_NAME)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    conn = get_db()
    cursor = conn.cursor()
    
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
    
    # Enforce default system admin credentials
    admin_hash = generate_password_hash("Admin#Motherson2026!")
    cursor.execute("SELECT * FROM users WHERE username = 'admin'")
    if cursor.fetchone():
        cursor.execute("UPDATE users SET password_hash = ?, role = 'admin' WHERE username = 'admin'", (admin_hash,))
    else:
        cursor.execute("INSERT INTO users (username, password_hash, role) VALUES ('admin', ?, 'admin')", (admin_hash,))
    
    cursor.execute("SELECT COUNT(*) FROM questions")
    if cursor.fetchone()[0] == 0:
        cursor.execute('''
            INSERT INTO questions (level, title, description, question, opt_a, opt_b, opt_c, correct_opt, points)
            VALUES (1, 'aPIMS Station Scanner Fault', 
                    'Assembly Line A scanner is unresponsive. Part numbers cannot be registered in the ERP database.',
                    'What is the recommended standard recovery action?',
                    'Reboot main plant electrical cabinet', 
                    'Unplug USB scanner, inspect cable, wait 5s and reconnect', 
                    'Reinstall Windows OS on station', 'B', 100)
        ''')
    
    conn.commit()
    conn.close()

init_db()

# ==========================================
# 2. SECURITY DECORATORS
# ==========================================
def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user' not in session:
            flash("Please sign in to access the system.", "danger")
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated_function

def admin_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user' not in session:
            flash("Authentication required.", "danger")
            return redirect(url_for('login'))
        
        conn = get_db()
        user = conn.execute("SELECT role FROM users WHERE username = ?", (session['user'],)).fetchone()
        conn.close()

        if not user or user['role'] != 'admin':
            flash("ACCESS DENIED: Required administrative rights.", "danger")
            return redirect(url_for('dashboard'))
            
        return f(*args, **kwargs)
    return decorated_function

# ==========================================
# 3. RESPONSIVE MOTHERSON BRAND UI LAYOUT
# ==========================================
HTML_LAYOUT = """
<!DOCTYPE html>
<html lang="en" class="h-full bg-slate-950">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0, maximum-scale=1.0, user-scalable=no">
    <title>Motherson | IT Command Portal</title>
    <!-- Tailwind CSS CDN -->
    <script src="https://cdn.tailwindcss.com"></script>
    <!-- Alpine.js for smooth mobile navigation & UI state -->
    <script defer src="https://cdn.jsdelivr.net/npm/alpinejs@3.x.x/dist/cdn.min.js"></script>
    <script>
      tailwind.config = {
        theme: {
          extend: {
            colors: {
              motherson: {
                red: '#E11D48',
                redhover: '#BE123C',
                blue: '#1E40AF',
                dark: '#0B132B',
                card: '#1E293B',
                border: '#334155'
              }
            }
          }
        }
      }
    </script>
    <style>
      /* Smooth touch scrolling and tap highlight fix */
      * { -webkit-tap-highlight-color: transparent; }
      body { font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif; }
    </style>
</head>
<body class="h-full flex flex-col text-slate-100 bg-slate-950 antialiased selection:bg-motherson-red selection:text-white" x-data="{ mobileMenuOpen: false }">
    
    <!-- TOP NAVIGATION BAR -->
    <nav class="bg-slate-900 border-b border-slate-800 sticky top-0 z-50">
        <div class="max-w-6xl mx-auto px-4 sm:px-6 lg:px-8">
            <div class="flex items-center justify-between h-16">
                
                <!-- Brand Logo & Title -->
                <div class="flex items-center space-x-3">
                    <div class="bg-motherson-red text-white font-black tracking-widest text-lg px-2.5 py-1 rounded shadow-md">
                        MOTHERSON
                    </div>
                    <span class="hidden sm:inline-block text-xs font-semibold uppercase tracking-wider text-slate-400 border-l border-slate-700 pl-3">
                        IT Operations Portal
                    </span>
                </div>

                <!-- Desktop Menu -->
                {% if session.get('user') %}
                <div class="hidden md:flex items-center space-x-4">
                    <span class="text-xs text-slate-400">User: <strong class="text-white font-medium">{{ session['user'] }}</strong></span>
                    {% if session.get('role') == 'admin' %}
                        <a href="/admin" class="bg-amber-600 hover:bg-amber-500 text-white text-xs font-bold px-3 py-2 rounded-lg transition-all shadow">
                            ⚙️ Admin Control
                        </a>
                    {% endif %}
                    <a href="/dashboard" class="bg-slate-800 hover:bg-slate-700 text-slate-200 text-xs font-medium px-3 py-2 rounded-lg transition-all border border-slate-700">
                        Dashboard
                    </a>
                    <a href="/logout" class="bg-motherson-red hover:bg-motherson-redhover text-white text-xs font-bold px-3 py-2 rounded-lg transition-all shadow">
                        Logout
                    </a>
                </div>

                <!-- Mobile Hamburger Button -->
                <div class="md:hidden flex items-center">
                    <button @click="mobileMenuOpen = !mobileMenuOpen" type="button" class="text-slate-300 hover:text-white p-2 rounded-lg bg-slate-800 focus:outline-none border border-slate-700">
                        <svg class="h-6 w-6" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                            <path x-show="!mobileMenuOpen" stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M4 6h16M4 12h16M4 18h16"/>
                            <path x-show="mobileMenuOpen" x-cloak stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M6 18L18 6M6 6l12 12"/>
                        </svg>
                    </button>
                </div>
                {% endif %}
            </div>
        </div>

        <!-- Mobile Dropdown Menu -->
        {% if session.get('user') %}
        <div x-show="mobileMenuOpen" x-cloak 
             x-transition:enter="transition ease-out duration-150"
             x-transition:enter-start="opacity-0 -translate-y-2"
             x-transition:enter-end="opacity-100 translate-y-0"
             x-transition:leave="transition ease-in duration-100"
             x-transition:leave-start="opacity-100 translate-y-0"
             x-transition:leave-end="opacity-0 -translate-y-2"
             class="md:hidden bg-slate-900 border-b border-slate-800 px-4 pt-2 pb-4 space-y-2">
            <div class="px-2 py-1 text-xs text-slate-400 border-b border-slate-800 mb-2">
                Signed in as: <strong class="text-white">{{ session['user'] }}</strong> ({{ session.get('role', 'operator') }})
            </div>
            <a href="/dashboard" class="block w-full text-left px-3 py-2.5 rounded-md text-sm font-medium bg-slate-800 text-white">Dashboard</a>
            {% if session.get('role') == 'admin' %}
                <a href="/admin" class="block w-full text-left px-3 py-2.5 rounded-md text-sm font-medium bg-amber-600 text-white">⚙️ Admin Control Panel</a>
            {% endif %}
            <a href="/logout" class="block w-full text-left px-3 py-2.5 rounded-md text-sm font-medium bg-motherson-red text-white">Logout</a>
        </div>
        {% endif %}
    </nav>

    <!-- MAIN BODY CONTAINER -->
    <main class="flex-grow container mx-auto px-4 sm:px-6 lg:px-8 py-6 max-w-5xl">
        {% with messages = get_flashed_messages(with_categories=true) %}
          {% if messages %}
            {% for category, message in messages %}
              <div class="mb-5 p-4 rounded-xl text-sm font-semibold flex items-center justify-between shadow-lg {% if category == 'danger' %}bg-red-950/90 text-red-200 border border-red-800{% else %}bg-emerald-950/90 text-emerald-200 border border-emerald-800{% endif %}">
                <span>{{ message }}</span>
                <span class="text-xs opacity-60">Dismiss</span>
              </div>
            {% endfor %}
          {% endif %}
        {% endwith %}
        {% block content %}{% endblock %}
    </main>

    <!-- FOOTER -->
    <footer class="bg-slate-900 border-t border-slate-800 py-4 text-center text-xs text-slate-500">
        Motherson Enterprise Systems &copy; 2026 | IT Operational Excellence
    </footer>
</body>
</html>
"""

# ==========================================
# 4. ROUTES
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
            conn.execute("INSERT INTO users (username, password_hash, role) VALUES (?, ?, 'operator')", 
                         (username, hashed_pwd))
            conn.commit()
            flash("Account registered successfully! Please log in.", "success")
            return redirect(url_for('login'))
        except sqlite3.IntegrityError:
            flash("Username / Employee ID already exists.", "danger")
        finally:
            conn.close()

    content = '''
    <div class="max-w-md mx-auto my-8 bg-slate-900 p-6 sm:p-8 rounded-2xl border border-slate-800 shadow-2xl">
        <div class="text-center mb-6">
            <div class="inline-block bg-motherson-red text-white text-xs font-black tracking-widest px-2.5 py-1 rounded mb-3">MOTHERSON</div>
            <h2 class="text-2xl font-bold text-white tracking-tight">Operator Registration</h2>
            <p class="text-xs text-slate-400 mt-1">Create an account to begin IT simulation training</p>
        </div>
        <form method="POST" class="space-y-4">
            <div>
                <label class="block text-xs font-medium text-slate-300 mb-1.5 uppercase tracking-wider">Username / Employee ID</label>
                <input type="text" name="username" required autocomplete="off" 
                       class="w-full bg-slate-950 border border-slate-800 rounded-xl px-4 py-3 text-white placeholder-slate-500 focus:outline-none focus:ring-2 focus:ring-motherson-red focus:border-transparent transition-all">
            </div>
            <div>
                <label class="block text-xs font-medium text-slate-300 mb-1.5 uppercase tracking-wider">Password</label>
                <input type="password" name="password" required 
                       class="w-full bg-slate-950 border border-slate-800 rounded-xl px-4 py-3 text-white placeholder-slate-500 focus:outline-none focus:ring-2 focus:ring-motherson-red focus:border-transparent transition-all">
            </div>
            <button type="submit" class="w-full bg-motherson-red hover:bg-motherson-redhover text-white font-bold py-3.5 rounded-xl shadow-lg transition-all active:scale-[0.98]">
                Register Operator
            </button>
        </form>
        <p class="text-xs text-center text-slate-400 mt-6">
            Already registered? <a href="/login" class="text-blue-400 font-semibold hover:underline">Sign in here</a>
        </p>
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
            flash("Invalid credentials provided.", "danger")
            
    content = '''
    <div class="max-w-md mx-auto my-8 bg-slate-900 p-6 sm:p-8 rounded-2xl border border-slate-800 shadow-2xl">
        <div class="text-center mb-6">
            <div class="inline-block bg-motherson-red text-white text-xs font-black tracking-widest px-2.5 py-1 rounded mb-3">MOTHERSON</div>
            <h2 class="text-2xl font-bold text-white tracking-tight">System Login</h2>
            <p class="text-xs text-slate-400 mt-1">Enter your credentials to access the command portal</p>
        </div>
        <form method="POST" class="space-y-4">
            <div>
                <label class="block text-xs font-medium text-slate-300 mb-1.5 uppercase tracking-wider">Username / Employee ID</label>
                <input type="text" name="username" required autocomplete="off"
                       class="w-full bg-slate-950 border border-slate-800 rounded-xl px-4 py-3 text-white placeholder-slate-500 focus:outline-none focus:ring-2 focus:ring-blue-600 focus:border-transparent transition-all">
            </div>
            <div>
                <label class="block text-xs font-medium text-slate-300 mb-1.5 uppercase tracking-wider">Password</label>
                <input type="password" name="password" required 
                       class="w-full bg-slate-950 border border-slate-800 rounded-xl px-4 py-3 text-white placeholder-slate-500 focus:outline-none focus:ring-2 focus:ring-blue-600 focus:border-transparent transition-all">
            </div>
            <button type="submit" class="w-full bg-blue-700 hover:bg-blue-600 text-white font-bold py-3.5 rounded-xl shadow-lg transition-all active:scale-[0.98]">
                Sign In
            </button>
        </form>
        <div class="mt-6 pt-4 border-t border-slate-800 text-center">
            <p class="text-xs text-slate-400">
                New operator? <a href="/register" class="text-blue-400 font-semibold hover:underline">Create an account</a>
            </p>
        </div>
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
    <div class="grid grid-cols-1 lg:grid-cols-2 gap-6">
        
        <!-- Action Card -->
        <div class="bg-slate-900 p-6 rounded-2xl border border-slate-800 shadow-xl flex flex-col justify-between">
            <div>
                <div class="inline-flex items-center space-x-2 bg-blue-950 text-blue-400 text-xs font-semibold px-3 py-1 rounded-full border border-blue-800/50 mb-3">
                    <span class="w-2 h-2 rounded-full bg-blue-400 animate-pulse"></span>
                    <span>Interactive Training Module</span>
                </div>
                <h3 class="text-xl font-bold text-white mb-2">Plant Incident Response</h3>
                <p class="text-slate-400 text-xs sm:text-sm leading-relaxed mb-6">
                    Diagnose real-time manufacturing IT hardware, network, and scanner faults under time pressure. High scores earn top leaderboard positions.
                </p>
            </div>
            <a href="/start-game" class="block w-full text-center bg-motherson-red hover:bg-motherson-redhover text-white font-bold py-4 rounded-xl shadow-lg transition-all active:scale-[0.98]">
                ▶ Launch Incident Simulation
            </a>
        </div>

        <!-- Leaderboard -->
        <div class="bg-slate-900 p-6 rounded-2xl border border-slate-800 shadow-xl">
            <h3 class="text-lg font-bold text-white mb-4 flex items-center justify-between">
                <span>🏆 Top Operators</span>
                <span class="text-xs text-slate-500 font-normal">Updated Live</span>
            </h3>
            
            <div class="overflow-x-auto">
                <table class="w-full text-left text-xs text-slate-300">
                    <thead class="bg-slate-950 text-slate-400 uppercase tracking-wider">
                        <tr>
                            <th class="p-3 rounded-l-lg">#</th>
                            <th class="p-3">Operator</th>
                            <th class="p-3">Score</th>
                            <th class="p-3 rounded-r-lg">Time</th>
                        </tr>
                    </thead>
                    <tbody class="divide-y divide-slate-800">
                        {% for r in rankings %}
                        <tr class="hover:bg-slate-800/50 transition-colors">
                            <td class="p-3 font-bold text-blue-400">{{ loop.index }}</td>
                            <td class="p-3 font-medium text-white">{{ r['username'] }}</td>
                            <td class="p-3 font-bold text-emerald-400">{{ r['score'] }} pts</td>
                            <td class="p-3 text-slate-400">{{ "%.1f"|format(r['time_seconds']) }}s</td>
                        </tr>
                        {% else %}
                        <tr>
                            <td colspan="4" class="p-4 text-center text-slate-500">No score records registered yet.</td>
                        </tr>
                        {% endfor %}
                    </tbody>
                </table>
            </div>
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
        
        flash(f"Simulation completed! Score: {score} pts in {total_time:.1f} seconds.", "success")
        return redirect(url_for('dashboard'))

    if request.method == 'POST':
        selected = request.form.get('option')
        if selected == question['correct_opt']:
            session['game_score'] = session.get('game_score', 0) + question['points']
            flash(f"Scenario Level {level} Resolved! +{question['points']} pts", "success")
            conn.close()
            return redirect(url_for('play_level', level=level+1))
        else:
            flash("Incorrect diagnostic action! Production line remains halted.", "danger")

    conn.close()
    content = '''
    <div class="max-w-2xl mx-auto bg-slate-900 p-6 sm:p-8 rounded-2xl border border-slate-800 shadow-2xl">
        
        <!-- Header badge -->
        <div class="flex items-center justify-between mb-4">
            <span class="bg-red-950 text-red-400 text-xs font-bold px-3 py-1 rounded-full border border-red-800/60 uppercase tracking-widest">
                INCIDENT LEVEL {{ question['level'] }}
            </span>
            <span class="text-xs font-bold text-emerald-400 bg-emerald-950/60 px-2.5 py-1 rounded border border-emerald-800">
                +{{ question['points'] }} PTS
            </span>
        </div>

        <h2 class="text-xl sm:text-2xl font-bold text-white mb-3 leading-snug">{{ question['title'] }}</h2>
        
        <div class="bg-slate-950 p-4 sm:p-5 rounded-xl border border-slate-800/80 mb-6">
            <p class="text-slate-300 text-xs sm:text-sm leading-relaxed">{{ question['description'] }}</p>
        </div>

        <p class="font-semibold text-slate-100 text-sm sm:text-base mb-4">{{ question['question'] }}</p>

        <!-- Touch-Friendly Options -->
        <form method="POST" class="space-y-3">
            <button type="submit" name="option" value="A" 
                    class="w-full text-left bg-slate-950 hover:bg-blue-900/40 border border-slate-800 hover:border-blue-600 p-4 rounded-xl text-xs sm:text-sm transition-all duration-150 active:scale-[0.99] flex items-start space-x-3">
                <span class="font-bold text-blue-400 bg-blue-950 px-2 py-0.5 rounded border border-blue-800">A</span>
                <span class="text-slate-200 mt-0.5">{{ question['opt_a'] }}</span>
            </button>

            <button type="submit" name="option" value="B" 
                    class="w-full text-left bg-slate-950 hover:bg-blue-900/40 border border-slate-800 hover:border-blue-600 p-4 rounded-xl text-xs sm:text-sm transition-all duration-150 active:scale-[0.99] flex items-start space-x-3">
                <span class="font-bold text-blue-400 bg-blue-950 px-2 py-0.5 rounded border border-blue-800">B</span>
                <span class="text-slate-200 mt-0.5">{{ question['opt_b'] }}</span>
            </button>

            <button type="submit" name="option" value="C" 
                    class="w-full text-left bg-slate-950 hover:bg-blue-900/40 border border-slate-800 hover:border-blue-600 p-4 rounded-xl text-xs sm:text-sm transition-all duration-150 active:scale-[0.99] flex items-start space-x-3">
                <span class="font-bold text-blue-400 bg-blue-950 px-2 py-0.5 rounded border border-blue-800">C</span>
                <span class="text-slate-200 mt-0.5">{{ question['opt_c'] }}</span>
            </button>
        </form>
    </div>
    '''
    return render_template_string(HTML_LAYOUT.replace('{% block content %}{% endblock %}', content), question=question)

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
        flash("New incident scenario successfully published!", "success")

    questions = conn.execute("SELECT * FROM questions ORDER BY level ASC").fetchall()
    users = conn.execute("SELECT id, username, role FROM users").fetchall()
    conn.close()

    content = '''
    <div class="space-y-8">
        
        <!-- Form Section -->
        <div class="bg-slate-900 p-6 rounded-2xl border border-slate-800 shadow-xl">
            <h3 class="text-lg font-bold text-amber-400 mb-4 flex items-center space-x-2">
                <span>⚙️ Add New Incident Scenario</span>
            </h3>
            
            <form method="POST" class="grid grid-cols-1 sm:grid-cols-2 gap-4 text-xs sm:text-sm">
                <div>
                    <label class="block text-slate-400 mb-1">Level Order</label>
                    <input type="number" name="level" required class="w-full bg-slate-950 border border-slate-800 p-3 rounded-xl text-white">
                </div>
                <div>
                    <label class="block text-slate-400 mb-1">Points Value</label>
                    <input type="number" name="points" value="100" required class="w-full bg-slate-950 border border-slate-800 p-3 rounded-xl text-white">
                </div>
                <div class="sm:col-span-2">
                    <label class="block text-slate-400 mb-1">Incident Title</label>
                    <input type="text" name="title" required class="w-full bg-slate-950 border border-slate-800 p-3 rounded-xl text-white">
                </div>
                <div class="sm:col-span-2">
                    <label class="block text-slate-400 mb-1">Description</label>
                    <textarea name="description" required class="w-full bg-slate-950 border border-slate-800 p-3 rounded-xl text-white h-20"></textarea>
                </div>
                <div class="sm:col-span-2">
                    <label class="block text-slate-400 mb-1">Diagnostic Question</label>
                    <input type="text" name="question" required class="w-full bg-slate-950 border border-slate-800 p-3 rounded-xl text-white">
                </div>
                <div>
                    <label class="block text-slate-400 mb-1">Option [A]</label>
                    <input type="text" name="opt_a" required class="w-full bg-slate-950 border border-slate-800 p-3 rounded-xl text-white">
                </div>
                <div>
                    <label class="block text-slate-400 mb-1">Option [B]</label>
                    <input type="text" name="opt_b" required class="w-full bg-slate-950 border border-slate-800 p-3 rounded-xl text-white">
                </div>
                <div>
                    <label class="block text-slate-400 mb-1">Option [C]</label>
                    <input type="text" name="opt_c" required class="w-full bg-slate-950 border border-slate-800 p-3 rounded-xl text-white">
                </div>
                <div>
                    <label class="block text-slate-400 mb-1">Correct Answer Choice</label>
                    <select name="correct_opt" class="w-full bg-slate-950 border border-slate-800 p-3 rounded-xl text-white">
                        <option value="A">A</option>
                        <option value="B">B</option>
                        <option value="C">C</option>
                    </select>
                </div>
                <div class="sm:col-span-2 mt-2">
                    <button type="submit" class="w-full sm:w-auto bg-amber-600 hover:bg-amber-500 text-white font-bold px-6 py-3 rounded-xl shadow-md transition-all active:scale-[0.98]">
                        Publish Scenario
                    </button>
                </div>
            </form>
        </div>

        <!-- Users Management Table -->
        <div class="bg-slate-900 p-6 rounded-2xl border border-slate-800 shadow-xl">
            <h4 class="font-bold text-white mb-4 text-sm sm:text-base">System User Accounts</h4>
            <div class="overflow-x-auto">
                <table class="w-full text-left text-xs text-slate-300">
                    <thead class="bg-slate-950 text-slate-400 uppercase tracking-wider">
                        <tr>
                            <th class="p-3">ID</th>
                            <th class="p-3">Username</th>
                            <th class="p-3">Role</th>
                        </tr>
                    </thead>
                    <tbody class="divide-y divide-slate-800">
                        {% for u in users %}
                        <tr>
                            <td class="p-3">{{ u['id'] }}</td>
                            <td class="p-3 font-bold text-white">{{ u['username'] }}</td>
                            <td class="p-3">
                                <span class="{% if u['role'] == 'admin' %}text-amber-400 bg-amber-950/50 border-amber-800{% else %}text-slate-400 bg-slate-800 border-slate-700{% endif %} border uppercase text-[10px] font-bold px-2 py-0.5 rounded">
                                    {{ u['role'] }}
                                </span>
                            </td>
                        </tr>
                        {% endfor %}
                    </tbody>
                </table>
            </div>
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