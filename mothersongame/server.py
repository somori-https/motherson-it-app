import os
import sqlite3
import time
from functools import wraps
from flask import Flask, render_template_string, request, redirect, url_for, session, flash
from werkzeug.security import generate_password_hash, check_password_hash

app = Flask(__name__)
app.secret_key = os.environ.get("SECRET_KEY", "motherson_logo_red_black_white_2026")

DB_NAME = "motherson_portal.db"

# Official Motherson Logo URL (Crisp Transparent PNG)
MOTHERSON_LOGO_URL = "https://upload.wikimedia.org/wikipedia/commons/thumb/8/87/Motherson_Group_logo.svg/512px-Motherson_Group_logo.svg.png"

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
                    'Assembly Line A scanner is unresponsive. Part numbers cannot be registered in the plant system.',
                    'What is the recommended standard recovery action?',
                    'Reboot main plant power grid', 
                    'Unplug USB scanner, inspect cable, wait 5 seconds and reconnect', 
                    'Reinstall Windows OS on station', 'B', 100)
        ''')
    
    conn.commit()
    conn.close()

init_db()

# ==========================================
# 2. SECURITY HELPERS
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
            flash("ACCESS DENIED: Administrative rights required.", "danger")
            return redirect(url_for('dashboard'))
            
        return f(*args, **kwargs)
    return decorated_function

# ==========================================
# 3. RED, WHITE & BLACK LAYOUT WITH LOGO & VIDEO
# ==========================================
HTML_LAYOUT = """
<!DOCTYPE html>
<html lang="en" class="h-full bg-black">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0, maximum-scale=1.0, user-scalable=no">
    <title>Motherson | IT Command Portal</title>
    <!-- Tailwind CSS CDN -->
    <script src="https://cdn.tailwindcss.com"></script>
    <!-- Alpine.js -->
    <script defer src="https://cdn.jsdelivr.net/npm/alpinejs@3.x.x/dist/cdn.min.js"></script>
    <script>
      tailwind.config = {
        theme: {
          extend: {
            colors: {
              brand: {
                red: '#E11D48',
                hover: '#BE123C',
                dark: '#0A0A0A',
                card: '#121212',
                border: '#262626'
              }
            }
          }
        }
      }
    </script>
    <style>
      * { -webkit-tap-highlight-color: transparent; }
      body { font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif; }
      
      .video-bg-container {
        position: fixed;
        top: 0;
        left: 0;
        width: 100%;
        height: 100%;
        z-index: -2;
        overflow: hidden;
      }
      .video-bg-container video {
        min-width: 100%;
        min-height: 100%;
        width: auto;
        height: auto;
        position: absolute;
        top: 50%;
        left: 50%;
        transform: translate(-50%, -50%);
        object-fit: cover;
      }
      .video-overlay {
        position: fixed;
        top: 0;
        left: 0;
        width: 100%;
        height: 100%;
        background: rgba(0, 0, 0, 0.85);
        z-index: -1;
      }
    </style>
</head>
<body class="h-full flex flex-col text-white bg-black antialiased selection:bg-brand-red selection:text-white" x-data="{ mobileMenuOpen: false }">
    
    <!-- BACKGROUND VIDEO -->
    <div class="video-bg-container">
        <video autoplay loop muted playsinline poster="https://images.unsplash.com/photo-1518770660439-4636190af475?q=80&w=1920">
            <source src="https://assets.mixkit.co/videos/preview/mixkit-circuit-board-loop-video-40348-large.mp4" type="video/mp4">
        </video>
    </div>
    <div class="video-overlay"></div>

    <!-- TOP NAVIGATION BAR -->
    <nav class="bg-black/90 backdrop-blur-md border-b border-brand-red/50 sticky top-0 z-50">
        <div class="max-w-6xl mx-auto px-4 sm:px-6 lg:px-8">
            <div class="flex items-center justify-between h-16">
                
                <!-- Brand Official Logo -->
                <div class="flex items-center space-x-3">
                    <a href="/dashboard" class="flex items-center bg-white/95 px-3 py-1.5 rounded shadow-lg hover:bg-white transition-colors">
                        <img src="https://upload.wikimedia.org/wikipedia/commons/thumb/8/87/Motherson_Group_logo.svg/512px-Motherson_Group_logo.svg.png" 
                             alt="Motherson Logo" 
                             class="h-6 sm:h-7 w-auto object-contain">
                    </a>
                    <span class="hidden sm:inline-block text-xs font-semibold uppercase tracking-widest text-zinc-400 border-l border-zinc-800 pl-3">
                        Enterprise Command Portal
                    </span>
                </div>

                <!-- Desktop Menu -->
                {% if session.get('user') %}
                <div class="hidden md:flex items-center space-x-4">
                    <span class="text-xs text-zinc-400">User: <strong class="text-white font-medium">{{ session['user'] }}</strong></span>
                    {% if session.get('role') == 'admin' %}
                        <a href="/admin" class="bg-white text-black font-extrabold text-xs px-3 py-2 rounded shadow hover:bg-zinc-200 transition-all">
                            ⚙️ Admin Panel
                        </a>
                    {% endif %}
                    <a href="/dashboard" class="bg-zinc-900 border border-zinc-800 hover:border-zinc-600 text-white text-xs font-medium px-3 py-2 rounded transition-all">
                        Dashboard
                    </a>
                    <a href="/logout" class="bg-brand-red hover:bg-brand-hover text-white text-xs font-bold px-3 py-2 rounded shadow transition-all">
                        Logout
                    </a>
                </div>

                <!-- Mobile Menu Button -->
                <div class="md:hidden flex items-center">
                    <button @click="mobileMenuOpen = !mobileMenuOpen" type="button" class="text-white p-2 rounded bg-zinc-900 border border-zinc-800 focus:outline-none">
                        <svg class="h-6 w-6" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                            <path x-show="!mobileMenuOpen" stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M4 6h16M4 12h16M4 18h16"/>
                            <path x-show="mobileMenuOpen" x-cloak stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M6 18L18 6M6 6l12 12"/>
                        </svg>
                    </button>
                </div>
                {% endif %}
            </div>
        </div>

        <!-- Mobile Drawer -->
        {% if session.get('user') %}
        <div x-show="mobileMenuOpen" x-cloak 
             x-transition:enter="transition ease-out duration-150"
             x-transition:enter-start="opacity-0 -translate-y-2"
             x-transition:enter-end="opacity-100 translate-y-0"
             class="md:hidden bg-black/95 border-b border-brand-red px-4 pt-2 pb-4 space-y-2">
            <div class="px-2 py-1 text-xs text-zinc-400 border-b border-zinc-800 mb-2">
                Signed in as: <strong class="text-white">{{ session['user'] }}</strong>
            </div>
            <a href="/dashboard" class="block w-full text-left px-3 py-2.5 rounded text-sm font-medium bg-zinc-900 text-white">Dashboard</a>
            {% if session.get('role') == 'admin' %}
                <a href="/admin" class="block w-full text-left px-3 py-2.5 rounded text-sm font-medium bg-white text-black font-extrabold">⚙️ Admin Control Panel</a>
            {% endif %}
            <a href="/logout" class="block w-full text-left px-3 py-2.5 rounded text-sm font-medium bg-brand-red text-white">Logout</a>
        </div>
        {% endif %}
    </nav>

    <!-- MAIN CONTAINER -->
    <main class="flex-grow container mx-auto px-4 sm:px-6 lg:px-8 py-6 max-w-5xl">
        {% with messages = get_flashed_messages(with_categories=true) %}
          {% if messages %}
            {% for category, message in messages %}
              <div class="mb-5 p-4 rounded-lg text-sm font-semibold flex items-center justify-between shadow-2xl {% if category == 'danger' %}bg-brand-red text-white border border-red-500{% else %}bg-white text-black border border-zinc-300{% endif %}">
                <span>{{ message }}</span>
              </div>
            {% endfor %}
          {% endif %}
        {% endwith %}
        {% block content %}{% endblock %}
    </main>

    <!-- FOOTER -->
    <footer class="bg-black/90 border-t border-zinc-900 py-4 text-center text-xs text-zinc-500 flex flex-col items-center justify-center space-y-2">
        <img src="https://upload.wikimedia.org/wikipedia/commons/thumb/8/87/Motherson_Group_logo.svg/512px-Motherson_Group_logo.svg.png" 
             alt="Motherson Logo" class="h-4 w-auto grayscale opacity-40 hover:opacity-100 transition-opacity">
        <div>MOTHERSON ENTERPRISE &copy; 2026 | Red & White Corporate System</div>
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
            flash("Username and password required.", "danger")
            return redirect(url_for('register'))

        hashed_pwd = generate_password_hash(password)
        conn = get_db()
        try:
            conn.execute("INSERT INTO users (username, password_hash, role) VALUES (?, ?, 'operator')", 
                         (username, hashed_pwd))
            conn.commit()
            flash("Account registered! Please sign in.", "success")
            return redirect(url_for('login'))
        except sqlite3.IntegrityError:
            flash("Username / Employee ID already exists.", "danger")
        finally:
            conn.close()

    content = '''
    <div class="max-w-md mx-auto my-8 bg-zinc-950/90 backdrop-blur-md p-6 sm:p-8 rounded-xl border border-brand-red/50 shadow-2xl">
        <div class="text-center mb-6">
            <div class="inline-block bg-white p-2.5 rounded shadow-lg mb-4">
                <img src="https://upload.wikimedia.org/wikipedia/commons/thumb/8/87/Motherson_Group_logo.svg/512px-Motherson_Group_logo.svg.png" 
                     alt="Motherson Logo" class="h-8 w-auto mx-auto object-contain">
            </div>
            <h2 class="text-2xl font-bold text-white tracking-tight">Operator Registration</h2>
            <p class="text-xs text-zinc-400 mt-1">Join the enterprise simulation platform</p>
        </div>
        <form method="POST" class="space-y-4">
            <div>
                <label class="block text-xs font-medium text-zinc-300 mb-1.5 uppercase tracking-wider">Username / Employee ID</label>
                <input type="text" name="username" required autocomplete="off" 
                       class="w-full bg-black border border-zinc-800 rounded px-4 py-3 text-white focus:outline-none focus:border-brand-red transition-all">
            </div>
            <div>
                <label class="block text-xs font-medium text-zinc-300 mb-1.5 uppercase tracking-wider">Password</label>
                <input type="password" name="password" required 
                       class="w-full bg-black border border-zinc-800 rounded px-4 py-3 text-white focus:outline-none focus:border-brand-red transition-all">
            </div>
            <button type="submit" class="w-full bg-brand-red hover:bg-brand-hover text-white font-bold py-3.5 rounded shadow-lg transition-all active:scale-[0.98]">
                Register Account
            </button>
        </form>
        <p class="text-xs text-center text-zinc-400 mt-6">
            Already registered? <a href="/login" class="text-white font-bold hover:underline">Sign in here</a>
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
            flash("Invalid credentials.", "danger")
            
    content = '''
    <div class="max-w-md mx-auto my-8 bg-zinc-950/90 backdrop-blur-md p-6 sm:p-8 rounded-xl border border-brand-red/50 shadow-2xl">
        <div class="text-center mb-6">
            <div class="inline-block bg-white p-2.5 rounded shadow-lg mb-4">
                <img src="https://upload.wikimedia.org/wikipedia/commons/thumb/8/87/Motherson_Group_logo.svg/512px-Motherson_Group_logo.svg.png" 
                     alt="Motherson Logo" class="h-8 w-auto mx-auto object-contain">
            </div>
            <h2 class="text-2xl font-bold text-white tracking-tight">System Login</h2>
            <p class="text-xs text-zinc-400 mt-1">Access secure operations command portal</p>
        </div>
        <form method="POST" class="space-y-4">
            <div>
                <label class="block text-xs font-medium text-zinc-300 mb-1.5 uppercase tracking-wider">Username / Employee ID</label>
                <input type="text" name="username" required autocomplete="off"
                       class="w-full bg-black border border-zinc-800 rounded px-4 py-3 text-white focus:outline-none focus:border-brand-red transition-all">
            </div>
            <div>
                <label class="block text-xs font-medium text-zinc-300 mb-1.5 uppercase tracking-wider">Password</label>
                <input type="password" name="password" required 
                       class="w-full bg-black border border-zinc-800 rounded px-4 py-3 text-white focus:outline-none focus:border-brand-red transition-all">
            </div>
            <button type="submit" class="w-full bg-white hover:bg-zinc-200 text-black font-extrabold py-3.5 rounded shadow-lg transition-all active:scale-[0.98]">
                Sign In
            </button>
        </form>
        <div class="mt-6 pt-4 border-t border-zinc-900 text-center">
            <p class="text-xs text-zinc-400">
                New user? <a href="/register" class="text-brand-red font-bold hover:underline">Create an account</a>
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
        
        <div class="bg-zinc-950/90 backdrop-blur-md p-6 rounded-xl border border-brand-red/40 shadow-xl flex flex-col justify-between">
            <div>
                <div class="inline-flex items-center space-x-2 bg-brand-red/20 text-brand-red text-xs font-bold px-3 py-1 rounded-full border border-brand-red/40 mb-3">
                    <span class="w-2 h-2 rounded-full bg-brand-red animate-ping"></span>
                    <span>System Simulation Active</span>
                </div>
                <h3 class="text-xl font-bold text-white mb-2">Plant Incident Simulation</h3>
                <p class="text-zinc-400 text-xs sm:text-sm leading-relaxed mb-6">
                    Diagnose industrial hardware, line halts, and network failures in real time. Fast resolutions earn top leaderboard placement.
                </p>
            </div>
            <a href="/start-game" class="block w-full text-center bg-brand-red hover:bg-brand-hover text-white font-bold py-4 rounded shadow-lg transition-all active:scale-[0.98]">
                ▶ Launch Simulation
            </a>
        </div>

        <div class="bg-zinc-950/90 backdrop-blur-md p-6 rounded-xl border border-zinc-800 shadow-xl">
            <h3 class="text-lg font-bold text-white mb-4 flex items-center justify-between border-b border-zinc-800 pb-2">
                <span>🏆 Top Operators</span>
                <span class="text-xs text-brand-red font-bold">LIVE RANKINGS</span>
            </h3>
            
            <div class="overflow-x-auto">
                <table class="w-full text-left text-xs text-zinc-300">
                    <thead class="bg-black text-zinc-400 uppercase tracking-wider">
                        <tr>
                            <th class="p-3">#</th>
                            <th class="p-3">Operator</th>
                            <th class="p-3">Score</th>
                            <th class="p-3">Time</th>
                        </tr>
                    </thead>
                    <tbody class="divide-y divide-zinc-900">
                        {% for r in rankings %}
                        <tr class="hover:bg-zinc-900/50">
                            <td class="p-3 font-bold text-brand-red">{{ loop.index }}</td>
                            <td class="p-3 font-medium text-white">{{ r['username'] }}</td>
                            <td class="p-3 font-bold text-white bg-zinc-900/80 px-2 py-1 rounded">{{ r['score'] }} pts</td>
                            <td class="p-3 text-zinc-400">{{ "%.1f"|format(r['time_seconds']) }}s</td>
                        </tr>
                        {% else %}
                        <tr>
                            <td colspan="4" class="p-4 text-center text-zinc-500">No records published yet.</td>
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
        
        flash(f"Simulation complete! Final Score: {score} pts in {total_time:.1f}s.", "success")
        return redirect(url_for('dashboard'))

    if request.method == 'POST':
        selected = request.form.get('option')
        if selected == question['correct_opt']:
            session['game_score'] = session.get('game_score', 0) + question['points']
            flash(f"Incident Level {level} Resolved! +{question['points']} pts", "success")
            conn.close()
            return redirect(url_for('play_level', level=level+1))
        else:
            flash("Incorrect response! Line output remains offline.", "danger")

    conn.close()
    content = '''
    <div class="max-w-2xl mx-auto bg-zinc-950/90 backdrop-blur-md p-6 sm:p-8 rounded-xl border border-brand-red/50 shadow-2xl">
        
        <div class="flex items-center justify-between mb-4">
            <span class="bg-brand-red text-white text-xs font-bold px-3 py-1 rounded uppercase tracking-widest">
                LEVEL {{ question['level'] }}
            </span>
            <span class="text-xs font-bold text-black bg-white px-2.5 py-1 rounded">
                +{{ question['points'] }} PTS
            </span>
        </div>

        <h2 class="text-xl sm:text-2xl font-bold text-white mb-3">{{ question['title'] }}</h2>
        
        <div class="bg-black/80 p-4 sm:p-5 rounded border border-zinc-800 mb-6">
            <p class="text-zinc-300 text-xs sm:text-sm leading-relaxed">{{ question['description'] }}</p>
        </div>

        <p class="font-semibold text-white text-sm sm:text-base mb-4">{{ question['question'] }}</p>

        <form method="POST" class="space-y-3">
            <button type="submit" name="option" value="A" 
                    class="w-full text-left bg-black hover:bg-zinc-900 border border-zinc-800 hover:border-brand-red p-4 rounded text-xs sm:text-sm transition-all flex items-start space-x-3 active:scale-[0.99]">
                <span class="font-bold text-white bg-brand-red px-2 py-0.5 rounded">A</span>
                <span class="text-zinc-200 mt-0.5">{{ question['opt_a'] }}</span>
            </button>

            <button type="submit" name="option" value="B" 
                    class="w-full text-left bg-black hover:bg-zinc-900 border border-zinc-800 hover:border-brand-red p-4 rounded text-xs sm:text-sm transition-all flex items-start space-x-3 active:scale-[0.99]">
                <span class="font-bold text-white bg-brand-red px-2 py-0.5 rounded">B</span>
                <span class="text-zinc-200 mt-0.5">{{ question['opt_b'] }}</span>
            </button>

            <button type="submit" name="option" value="C" 
                    class="w-full text-left bg-black hover:bg-zinc-900 border border-zinc-800 hover:border-brand-red p-4 rounded text-xs sm:text-sm transition-all flex items-start space-x-3 active:scale-[0.99]">
                <span class="font-bold text-white bg-brand-red px-2 py-0.5 rounded">C</span>
                <span class="text-zinc-200 mt-0.5">{{ question['opt_c'] }}</span>
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
        flash("New scenario published to system!", "success")

    questions = conn.execute("SELECT * FROM questions ORDER BY level ASC").fetchall()
    users = conn.execute("SELECT id, username, role FROM users").fetchall()
    conn.close()

    content = '''
    <div class="space-y-8">
        
        <div class="bg-zinc-950/90 backdrop-blur-md p-6 rounded-xl border border-brand-red/50 shadow-xl">
            <h3 class="text-lg font-bold text-white mb-4 flex items-center space-x-2 border-b border-zinc-800 pb-2">
                <span>⚙️ Create New Incident Scenario</span>
            </h3>
            
            <form method="POST" class="grid grid-cols-1 sm:grid-cols-2 gap-4 text-xs sm:text-sm">
                <div>
                    <label class="block text-zinc-400 mb-1">Level Order</label>
                    <input type="number" name="level" required class="w-full bg-black border border-zinc-800 p-3 rounded text-white focus:border-brand-red">
                </div>
                <div>
                    <label class="block text-zinc-400 mb-1">Points Value</label>
                    <input type="number" name="points" value="100" required class="w-full bg-black border border-zinc-800 p-3 rounded text-white focus:border-brand-red">
                </div>
                <div class="sm:col-span-2">
                    <label class="block text-zinc-400 mb-1">Incident Title</label>
                    <input type="text" name="title" required class="w-full bg-black border border-zinc-800 p-3 rounded text-white focus:border-brand-red">
                </div>
                <div class="sm:col-span-2">
                    <label class="block text-zinc-400 mb-1">Description</label>
                    <textarea name="description" required class="w-full bg-black border border-zinc-800 p-3 rounded text-white h-20 focus:border-brand-red"></textarea>
                </div>
                <div class="sm:col-span-2">
                    <label class="block text-zinc-400 mb-1">Diagnostic Question</label>
                    <input type="text" name="question" required class="w-full bg-black border border-zinc-800 p-3 rounded text-white focus:border-brand-red">
                </div>
                <div>
                    <label class="block text-zinc-400 mb-1">Option [A]</label>
                    <input type="text" name="opt_a" required class="w-full bg-black border border-zinc-800 p-3 rounded text-white focus:border-brand-red">
                </div>
                <div>
                    <label class="block text-zinc-400 mb-1">Option [B]</label>
                    <input type="text" name="opt_b" required class="w-full bg-black border border-zinc-800 p-3 rounded text-white focus:border-brand-red">
                </div>
                <div>
                    <label class="block text-zinc-400 mb-1">Option [C]</label>
                    <input type="text" name="opt_c" required class="w-full bg-black border border-zinc-800 p-3 rounded text-white focus:border-brand-red">
                </div>
                <div>
                    <label class="block text-zinc-400 mb-1">Correct Choice</label>
                    <select name="correct_opt" class="w-full bg-black border border-zinc-800 p-3 rounded text-white focus:border-brand-red">
                        <option value="A">A</option>
                        <option value="B">B</option>
                        <option value="C">C</option>
                    </select>
                </div>
                <div class="sm:col-span-2 mt-2">
                    <button type="submit" class="bg-white hover:bg-zinc-200 text-black font-extrabold px-6 py-3 rounded shadow transition-all active:scale-[0.98]">
                        Publish Scenario
                    </button>
                </div>
            </form>
        </div>

        <div class="bg-zinc-950/90 backdrop-blur-md p-6 rounded-xl border border-zinc-800 shadow-xl">
            <h4 class="font-bold text-white mb-4 text-sm sm:text-base">System User Accounts</h4>
            <div class="overflow-x-auto">
                <table class="w-full text-left text-xs text-zinc-300">
                    <thead class="bg-black text-zinc-400 uppercase tracking-wider">
                        <tr>
                            <th class="p-3">ID</th>
                            <th class="p-3">Username</th>
                            <th class="p-3">Role</th>
                        </tr>
                    </thead>
                    <tbody class="divide-y divide-zinc-900">
                        {% for u in users %}
                        <tr>
                            <td class="p-3">{{ u['id'] }}</td>
                            <td class="p-3 font-bold text-white">{{ u['username'] }}</td>
                            <td class="p-3">
                                <span class="{% if u['role'] == 'admin' %}text-black bg-white{% else %}text-zinc-400 bg-zinc-900{% endif %} uppercase text-[10px] font-extrabold px-2 py-0.5 rounded">
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