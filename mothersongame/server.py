import os
import sqlite3
import time
import json
import random
import urllib.request
from functools import wraps
from flask import Flask, render_template_string, request, redirect, url_for, session, flash
from werkzeug.security import generate_password_hash, check_password_hash

app = Flask(__name__)
app.secret_key = os.environ.get("SECRET_KEY", "motherson_enterprise_global_2026_key")

# Database path suitable for Render persistent/local execution
DB_NAME = os.path.join(os.path.dirname(__file__), "motherson_portal.db")

# =========================================================================
# OFFICIAL MOTHERSON SVG LOGO (High-contrast, pure inline code)
# =========================================================================
MOTHERSON_LOGO_SVG = """
<svg class="h-8 w-auto" viewBox="0 0 340 60" fill="none" xmlns="http://www.w3.org/2000/svg">
    <rect width="340" height="60" rx="6" fill="#FFFFFF"/>
    <g transform="translate(12, 10)">
        <path d="M0 40 V0 L12 24 L24 0 V40 H16 V16 L12 24 L8 16 V40 H0 Z" fill="#E11D48"/>
        <path d="M18 40 V15 L26 31 L34 15 V40 H28 V24 L26 28 L24 24 V40 H18 Z" fill="#E11D48" opacity="0.85"/>
    </g>
    <text x="62" y="41" font-family="-apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Helvetica, Arial, sans-serif" font-weight="900" font-size="28" fill="#000000" letter-spacing="3">MOTHERSON</text>
</svg>
"""

DEPARTMENTS = [
    "IT & Digital Infrastructure",
    "Plant Operations & Assembly",
    "Quality Control & Assurance",
    "Supply Chain & Logistics",
    "Engineering & Automation",
    "Human Resources & Admin",
    "Finance & Procurement"
]

PLANT_LOCATIONS = [
    "Plant A - Main Assembly",
    "Plant B - Wiring Harness Unit",
    "Plant C - Polymers & Modules",
    "Global HQ & IT Center"
]

ROOMS = [
    {
        "id": 1,
        "code": "IT-101",
        "name": "🖥️ Hardware & Workstation Support",
        "description": "Troubleshoot thermal printers, handheld scanners, PC terminals, and workstation peripherals.",
        "icon": "🖥️"
    },
    {
        "id": 2,
        "code": "AUTO-202",
        "name": "⚙️ Plant Automation & aPIMS",
        "description": "Manage manufacturing execution systems, line sensors, PLC interfaces, and assembly station software.",
        "icon": "⚙️"
    },
    {
        "id": 3,
        "code": "SEC-303",
        "name": "🔒 Cybersecurity & Incident Protocols",
        "description": "Identify phishing threats, unauthorized hardware, credential leaks, and ransomware containment.",
        "icon": "🔒"
    },
    {
        "id": 4,
        "code": "NET-404",
        "name": "🌐 Network Infrastructure & Wi-Fi",
        "description": "Diagnose industrial switch faults, VLAN isolation, IP conflicts, and wireless access point issues.",
        "icon": "🌐"
    },
    {
        "id": 5,
        "code": "ERP-505",
        "name": "📊 SAP, ERP & Supply Chain Systems",
        "description": "Resolve barcode registration errors, inventory database lockups, and shipping manifest sync faults.",
        "icon": "📊"
    }
]

# =========================================================================
# 1. DATABASE INITIALIZATION & SEEDING
# =========================================================================
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
            role TEXT NOT NULL DEFAULT 'operator',
            department TEXT NOT NULL DEFAULT 'Plant Operations & Assembly',
            plant_location TEXT NOT NULL DEFAULT 'Plant A - Main Assembly'
        )
    ''')
    
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS questions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            room_id INTEGER NOT NULL,
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
            department TEXT NOT NULL,
            plant_location TEXT NOT NULL,
            room_id INTEGER NOT NULL,
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
        cursor.execute("INSERT INTO users (username, password_hash, role, department, plant_location) VALUES ('admin', ?, 'admin', 'IT & Digital Infrastructure', 'Global HQ & IT Center')", (admin_hash,))
    
    cursor.execute("SELECT COUNT(*) FROM questions")
    if cursor.fetchone()[0] == 0:
        seed_questions(cursor)
    
    conn.commit()
    conn.close()

def seed_questions(cursor):
    base_questions = {
        1: [
            ("aPIMS Scanner Unresponsive", "Line A scanner stops sending barcode telemetry.", "Recommended first step?", "Reboot plant power cabinet", "Unplug USB, inspect pin connector, reconnect", "Reinstall OS", "B"),
            ("Thermal Barcode Printer Smudging", "Labels on line 3 are illegible.", "How to resolve smudging?", "Increase feed speed", "Clean thermal printhead with isopropyl alcohol swab", "Replace network cable", "B"),
            ("Workstation Blue Screen (BSOD)", "Assembly terminal crashes repeatedly.", "Correct initial action?", "Log incident ticket with RAM dump codes", "Sledgehammer terminal", "Ignore and skip parts", "A"),
            ("Touchscreen Calibration Drift", "Operator clicks button A, screen clicks B.", "Solution?", "Run Windows Touch Calibration Utility", "Replace monitor cable", "Reboot switch", "A"),
            ("RFID Reader Offline", "Pallet gate 2 RFID fails to ping.", "Primary check?", "Verify PoE ethernet link lights on reader port", "Check plant air pressure", "Call HR", "A")
        ],
        2: [
            ("aPIMS Line Stoppage Alert", "Line 4 conveyor stops automatically.", "Action?", "Inspect PLC error stack in aPIMS supervisor console", "Force conveyor start button", "Bypass safety light curtain", "A"),
            ("Screw Torque Telemetry Fault", "Torque gun value not writing to database.", "Check?", "Verify Modbus TCP driver connection status", "Tighten screw manually", "Turn off torque tool", "A"),
            ("PLC Communication Loss", "Siemens S7 PLC shows red SF error.", "Step 1?", "Check Industrial Ethernet cable to Profinet switch", "Power cycle whole plant", "Delete PLC program", "A")
        ],
        3: [
            ("Suspicious Phishing Email Received", "Email asking for password reset with urgent tag.", "Correct response?", "Report email using Outlook Report Phishing button", "Click link to verify", "Forward to all coworkers", "A"),
            ("Unknown USB Drive Found in Parking Lot", "Flash drive labeled 'Executive Bonuses'.", "Action?", "Hand over immediately to IT Security team", "Plug into workstation", "Plug into personal laptop", "A")
        ],
        4: [
            ("IP Address Conflict Error", "Windows alert: 'Another IP conflict exists'.", "Cause?", "Two devices assigned identical static IP addresses", "Bad cable", "Server fire", "A"),
            ("Fiber Optic Link Loss", "Core switch fiber trunk LED off.", "Action?", "Inspect fiber patch cord for bends and test with OTDR", "Splice fiber with scissors", "Reboot core router", "A")
        ],
        5: [
            ("SAP Transaction MIGO Error", "Goods movement blocked with material lock.", "Cause?", "Another user holds active lock on material record", "Database deleted", "Printer offline", "A"),
            ("Barcode Scanner Extra Character Bug", "Scanned barcode adds unwanted enter key.", "Fix?", "Reconfigure scanner suffix barcode settings", "Edit SAP source code", "Type barcode manually", "A")
        ]
    }

    for room_id, q_list in base_questions.items():
        for idx, item in enumerate(q_list, start=1):
            cursor.execute('''
                INSERT INTO questions (room_id, level, title, description, question, opt_a, opt_b, opt_c, correct_opt, points)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (room_id, idx, item[0], item[1], item[2], item[3], item[4], item[5], item[6], 100))

init_db()

# =========================================================================
# 2. DYNAMIC API QUESTION GENERATOR
# =========================================================================
def fetch_dynamic_api_questions(amount=10):
    url = f"https://opentdb.com/api.php?amount={amount}&category=18&type=multiple"
    try:
        req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
        with urllib.request.urlopen(req, timeout=3) as response:
            if response.status == 200:
                data = json.loads(response.read().decode())
                if data.get("response_code") == 0 and data.get("results"):
                    dynamic_list = []
                    for idx, res in enumerate(data["results"], start=1):
                        q_text = res["question"].replace("&quot;", '"').replace("&#039;", "'")
                        correct = res["correct_answer"].replace("&quot;", '"').replace("&#039;", "'")
                        incorrects = [i.replace("&quot;", '"').replace("&#039;", "'") for i in res["incorrect_answers"]]
                        
                        opts = [correct] + incorrects[:2]
                        random.shuffle(opts)
                        
                        correct_letter = "A" if opts[0] == correct else ("B" if opts[1] == correct else "C")
                        
                        dynamic_list.append({
                            "id": 9000 + idx,
                            "level": idx,
                            "title": f"🌐 Dynamic IT Incident #{idx}",
                            "description": "Real-time external API dynamic security/technical scenario challenge.",
                            "question": q_text,
                            "opt_a": opts[0],
                            "opt_b": opts[1],
                            "opt_c": opts[2],
                            "correct_opt": correct_letter,
                            "points": 150
                        })
                    return dynamic_list
    except Exception:
        pass
    
    return generate_procedural_questions(amount)

def generate_procedural_questions(count=10):
    generated = []
    lines = ["Assembly Line Alpha", "Harness Bay Delta", "Polymers Unit 3", "Logistics Gate 9"]
    errors = ["ERR_NET_TIMEOUT_104", "FAIL_SENSOR_MISALIGN_90", "SQL_LOCK_DEADLOCK_02", "AUTH_TOKEN_EXPIRED"]
    
    for i in range(1, count + 1):
        line = random.choice(lines)
        err = random.choice(errors)
        ip = f"10.0.{random.randint(1, 20)}.{random.randint(10, 250)}"
        
        generated.append({
            "id": 8000 + i,
            "level": i,
            "title": f"🤖 Dynamic Scenario #{i}: Fault on {line}",
            "description": f"Terminal on IP address {ip} reported error code [{err}]. Production line affected.",
            "question": "What is the recommended standard recovery protocol?",
            "opt_a": f"Inspect network connection on {ip} and verify port configuration.",
            "opt_b": "Power down main plant electrical distribution panel.",
            "opt_c": "Ignore error alert and manually override safety interlocks.",
            "correct_opt": "A",
            "points": 150
        })
    return generated

# =========================================================================
# 3. SECURITY HELPERS
# =========================================================================
def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user' not in session:
            flash("Please sign in to access the enterprise portal.", "danger")
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
            flash("ACCESS DENIED: Required IT Administrator rights.", "danger")
            return redirect(url_for('dashboard'))
            
        return f(*args, **kwargs)
    return decorated_function

# =========================================================================
# 4. MASTER HTML TEMPLATE
# =========================================================================
HTML_LAYOUT = """
<!DOCTYPE html>
<html lang="en" class="h-full bg-black">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0, maximum-scale=1.0, user-scalable=no">
    <title>Motherson | IT Command Portal</title>
    <script src="https://cdn.tailwindcss.com"></script>
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
      .bg-radial-gradient {
        position: fixed;
        top: 0; left: 0; width: 100%; height: 100%;
        background: radial-gradient(circle at center, #18181b 0%, #000000 100%);
        z-index: -1;
      }
    </style>
</head>
<body class="h-full flex flex-col text-white bg-black antialiased selection:bg-brand-red selection:text-white" x-data="{ mobileMenuOpen: false }">
    <div class="bg-radial-gradient"></div>

    <nav class="bg-black/90 backdrop-blur-md border-b border-brand-red/50 sticky top-0 z-50">
        <div class="max-w-6xl mx-auto px-4 sm:px-6 lg:px-8">
            <div class="flex items-center justify-between h-16">
                <div class="flex items-center space-x-3">
                    <a href="/dashboard" class="flex items-center p-1 rounded transition-colors">
                        ''' + MOTHERSON_LOGO_SVG + '''
                    </a>
                    <span class="hidden sm:inline-block text-xs font-semibold uppercase tracking-widest text-zinc-400 border-l border-zinc-800 pl-3">
                        Enterprise Command Portal
                    </span>
                </div>

                {% if session.get('user') %}
                <div class="hidden md:flex items-center space-x-4">
                    <div class="text-right">
                        <div class="text-xs text-white font-bold">{{ session['user'] }}</div>
                        <div class="text-[10px] text-zinc-400">{{ session.get('department', 'Plant Operations') }}</div>
                    </div>
                    {% if session.get('role') == 'admin' %}
                        <a href="/admin" class="bg-white text-black font-extrabold text-xs px-3 py-2 rounded shadow hover:bg-zinc-200 transition-all">
                            ⚙️ Admin Control
                        </a>
                    {% endif %}
                    <a href="/dashboard" class="bg-zinc-900 border border-zinc-800 hover:border-zinc-600 text-white text-xs font-medium px-3 py-2 rounded transition-all">
                        Dashboard
                    </a>
                    <a href="/logout" class="bg-brand-red hover:bg-brand-hover text-white text-xs font-bold px-3 py-2 rounded shadow transition-all">
                        Logout
                    </a>
                </div>

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

        {% if session.get('user') %}
        <div x-show="mobileMenuOpen" x-cloak class="md:hidden bg-black/95 border-b border-brand-red px-4 pt-2 pb-4 space-y-2">
            <div class="px-2 py-1 text-xs text-zinc-400 border-b border-zinc-800 mb-2">
                User: <strong class="text-white">{{ session['user'] }}</strong> ({{ session.get('department') }})
            </div>
            <a href="/dashboard" class="block w-full text-left px-3 py-2.5 rounded text-sm font-medium bg-zinc-900 text-white">Dashboard</a>
            {% if session.get('role') == 'admin' %}
                <a href="/admin" class="block w-full text-left px-3 py-2.5 rounded text-sm font-medium bg-white text-black font-extrabold">⚙️ Admin Control Panel</a>
            {% endif %}
            <a href="/logout" class="block w-full text-left px-3 py-2.5 rounded text-sm font-medium bg-brand-red text-white">Logout</a>
        </div>
        {% endif %}
    </nav>

    <main class="flex-grow container mx-auto px-4 sm:px-6 lg:px-8 py-6 max-w-6xl">
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

    <footer class="bg-black/90 border-t border-zinc-900 py-4 text-center text-xs text-zinc-500 flex flex-col items-center justify-center space-y-2">
        <div>MOTHERSON ENTERPRISE SYSTEMS &copy; 2026 | Global Employee Learning Portal</div>
    </footer>
</body>
</html>
"""

# =========================================================================
# 5. ROUTES
# =========================================================================
@app.route('/')
def index():
    return redirect(url_for('login'))

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form['username'].strip()
        password = request.form['password'].strip()
        department = request.form.get('department', DEPARTMENTS[1])
        plant_location = request.form.get('plant_location', PLANT_LOCATIONS[0])
        
        if not username or not password:
            flash("Username and password are required.", "danger")
            return redirect(url_for('register'))

        hashed_pwd = generate_password_hash(password)
        conn = get_db()
        try:
            conn.execute('''
                INSERT INTO users (username, password_hash, role, department, plant_location) 
                VALUES (?, ?, 'operator', ?, ?)
            ''', (username, hashed_pwd, department, plant_location))
            conn.commit()
            flash("Account registered successfully! Please sign in.", "success")
            return redirect(url_for('login'))
        except sqlite3.IntegrityError:
            flash("Username / Employee ID already exists.", "danger")
        finally:
            conn.close()

    content = '''
    <div class="max-w-md mx-auto my-6 bg-zinc-950/90 backdrop-blur-md p-6 sm:p-8 rounded-xl border border-brand-red/50 shadow-2xl">
        <div class="text-center mb-6">
            <div class="inline-block p-1 rounded-lg mb-3">
                ''' + MOTHERSON_LOGO_SVG + '''
            </div>
            <h2 class="text-2xl font-bold text-white tracking-tight">Employee Registration</h2>
            <p class="text-xs text-zinc-400 mt-1">Register your profile across enterprise departments</p>
        </div>
        <form method="POST" class="space-y-4">
            <div>
                <label class="block text-xs font-medium text-zinc-300 mb-1.5 uppercase tracking-wider">Username / Employee ID</label>
                <input type="text" name="username" required autocomplete="off" 
                       class="w-full bg-black border border-zinc-800 rounded px-4 py-3 text-white focus:outline-none focus:border-brand-red transition-all">
            </div>
            <div>
                <label class="block text-xs font-medium text-zinc-300 mb-1.5 uppercase tracking-wider">Department</label>
                <select name="department" class="w-full bg-black border border-zinc-800 rounded px-4 py-3 text-white focus:outline-none focus:border-brand-red transition-all">
                    {% for dept in departments %}
                        <option value="{{ dept }}">{{ dept }}</option>
                    {% endfor %}
                </select>
            </div>
            <div>
                <label class="block text-xs font-medium text-zinc-300 mb-1.5 uppercase tracking-wider">Plant / Office Facility</label>
                <select name="plant_location" class="w-full bg-black border border-zinc-800 rounded px-4 py-3 text-white focus:outline-none focus:border-brand-red transition-all">
                    {% for plant in plants %}
                        <option value="{{ plant }}">{{ plant }}</option>
                    {% endfor %}
                </select>
            </div>
            <div>
                <label class="block text-xs font-medium text-zinc-300 mb-1.5 uppercase tracking-wider">Password</label>
                <input type="password" name="password" required 
                       class="w-full bg-black border border-zinc-800 rounded px-4 py-3 text-white focus:outline-none focus:border-brand-red transition-all">
            </div>
            <button type="submit" class="w-full bg-brand-red hover:bg-brand-hover text-white font-bold py-3.5 rounded shadow-lg transition-all active:scale-[0.98]">
                Register Profile
            </button>
        </form>
        <p class="text-xs text-center text-zinc-400 mt-6">
            Already registered? <a href="/login" class="text-white font-bold hover:underline">Sign in here</a>
        </p>
    </div>
    '''
    return render_template_string(
        HTML_LAYOUT.replace('{% block content %}{% endblock %}', content), 
        departments=DEPARTMENTS, 
        plants=PLANT_LOCATIONS
    )

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
            session['department'] = user['department']
            session['plant_location'] = user['plant_location']
            return redirect(url_for('dashboard'))
        else:
            flash("Invalid login credentials.", "danger")
            
    content = '''
    <div class="max-w-md mx-auto my-8 bg-zinc-950/90 backdrop-blur-md p-6 sm:p-8 rounded-xl border border-brand-red/50 shadow-2xl">
        <div class="text-center mb-6">
            <div class="inline-block p-1 rounded-lg mb-3">
                ''' + MOTHERSON_LOGO_SVG + '''
            </div>
            <h2 class="text-2xl font-bold text-white tracking-tight">System Login</h2>
            <p class="text-xs text-zinc-400 mt-1">Access operational command & simulation center</p>
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
                New employee? <a href="/register" class="text-brand-red font-bold hover:underline">Create an account</a>
            </p>
        </div>
    </div>
    '''
    return render_template_string(HTML_LAYOUT.replace('{% block content %}{% endblock %}', content))

@app.route('/dashboard')
@login_required
def dashboard():
    conn = get_db()
    
    # Group by username so each employee only appears ONCE with their highest score
    rankings = conn.execute('''
        SELECT username, department, plant_location, MAX(score) as score, MIN(time_seconds) as time_seconds, MAX(completed_at) as completed_at 
        FROM scores 
        GROUP BY username 
        ORDER BY score DESC, time_seconds ASC 
        LIMIT 10
    ''').fetchall()
    
    user_best = conn.execute('''
        SELECT MAX(score) as best_score FROM scores WHERE username = ?
    ''', (session['user'],)).fetchone()
    conn.close()

    content = '''
    <div class="space-y-8">
        <div class="bg-zinc-950/90 backdrop-blur-md p-6 rounded-xl border border-zinc-800 shadow-xl flex flex-col md:flex-row items-start md:items-center justify-between gap-4">
            <div>
                <div class="text-xs text-brand-red font-bold uppercase tracking-wider mb-1">Employee Operational Profile</div>
                <h2 class="text-2xl font-bold text-white">{{ session['user'] }}</h2>
                <div class="text-xs text-zinc-400 mt-1 flex flex-wrap gap-2">
                    <span class="bg-zinc-900 px-2.5 py-1 rounded border border-zinc-800">🏢 {{ session.get('department') }}</span>
                    <span class="bg-zinc-900 px-2.5 py-1 rounded border border-zinc-800">📍 {{ session.get('plant_location') }}</span>
                </div>
            </div>
            <div class="bg-black p-4 rounded-xl border border-zinc-800 text-center min-w-[140px]">
                <div class="text-[10px] text-zinc-500 uppercase font-bold tracking-wider">Personal High Score</div>
                <div class="text-2xl font-black text-white mt-0.5">{{ user_best['best_score'] or 0 }} <span class="text-xs font-normal text-zinc-400">PTS</span></div>
            </div>
        </div>

        <div>
            <div class="flex items-center justify-between mb-4">
                <h3 class="text-lg font-bold text-white">🏭 Operational Training Rooms</h3>
            </div>
            
            <div class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
                {% for room in rooms %}
                <div class="bg-zinc-950/90 backdrop-blur-md p-6 rounded-xl border border-zinc-800 hover:border-brand-red/60 transition-all shadow-xl flex flex-col justify-between group">
                    <div>
                        <div class="flex items-center justify-between mb-3">
                            <span class="bg-brand-red text-white text-[10px] font-black px-2.5 py-1 rounded uppercase tracking-widest">
                                {{ room['code'] }}
                            </span>
                            <span class="text-2xl">{{ room['icon'] }}</span>
                        </div>
                        <h4 class="text-base font-bold text-white mb-2 group-hover:text-brand-red transition-colors">{{ room['name'] }}</h4>
                        <p class="text-xs text-zinc-400 leading-relaxed mb-6">{{ room['description'] }}</p>
                    </div>
                    
                    <a href="/start-room/{{ room['id'] }}" 
                       class="block w-full text-center bg-zinc-900 hover:bg-brand-red text-white text-xs font-bold py-3 rounded transition-all border border-zinc-800 hover:border-brand-red shadow">
                        Enter Module & Start
                    </a>
                </div>
                {% endfor %}

                <div class="bg-zinc-950/90 backdrop-blur-md p-6 rounded-xl border border-brand-red/50 shadow-xl flex flex-col justify-between group">
                    <div>
                        <div class="flex items-center justify-between mb-3">
                            <span class="bg-white text-black text-[10px] font-black px-2.5 py-1 rounded uppercase tracking-widest">
                                API-DYNAMIC
                            </span>
                            <span class="text-2xl">⚡</span>
                        </div>
                        <h4 class="text-base font-bold text-white mb-2 group-hover:text-brand-red transition-colors">🌐 Live API Dynamic Challenge</h4>
                        <p class="text-xs text-zinc-400 leading-relaxed mb-6">Generates real-time random IT scenarios fetched dynamically via external APIs.</p>
                    </div>
                    
                    <a href="/start-dynamic-room" 
                       class="block w-full text-center bg-brand-red hover:bg-brand-hover text-white text-xs font-bold py-3 rounded transition-all shadow">
                        ⚡ Launch API Dynamic Quiz
                    </a>
                </div>
            </div>
        </div>

        <div class="bg-zinc-950/90 backdrop-blur-md p-6 rounded-xl border border-zinc-800 shadow-xl">
            <h3 class="text-lg font-bold text-white mb-4 flex items-center justify-between border-b border-zinc-800 pb-2">
                <span>🏆 Enterprise Rankings</span>
                <span class="text-xs text-brand-red font-bold">ALL DEPARTMENTS</span>
            </h3>
            
            <div class="overflow-x-auto">
                <table class="w-full text-left text-xs text-zinc-300">
                    <thead class="bg-black text-zinc-400 uppercase tracking-wider">
                        <tr>
                            <th class="p-3">#</th>
                            <th class="p-3">Employee</th>
                            <th class="p-3">Department</th>
                            <th class="p-3">Plant Facility</th>
                            <th class="p-3">Score</th>
                            <th class="p-3">Time</th>
                        </tr>
                    </thead>
                    <tbody class="divide-y divide-zinc-900">
                        {% for r in rankings %}
                        <tr class="hover:bg-zinc-900/50">
                            <td class="p-3 font-bold text-brand-red">{{ loop.index }}</td>
                            <td class="p-3 font-bold text-white">{{ r['username'] }}</td>
                            <td class="p-3 text-zinc-400">{{ r['department'] }}</td>
                            <td class="p-3 text-zinc-400">{{ r['plant_location'] }}</td>
                            <td class="p-3 font-bold text-white bg-zinc-900/80 px-2 py-1 rounded">{{ r['score'] }} pts</td>
                            <td class="p-3 text-zinc-400">{{ "%.1f"|format(r['time_seconds']) }}s</td>
                        </tr>
                        {% else %}
                        <tr>
                            <td colspan="6" class="p-4 text-center text-zinc-500">No score records registered yet.</td>
                        </tr>
                        {% endfor %}
                    </tbody>
                </table>
            </div>
        </div>
    </div>
    '''
    return render_template_string(HTML_LAYOUT.replace('{% block content %}{% endblock %}', content), rooms=ROOMS, rankings=rankings, user_best=user_best)

@app.route('/start-room/<int:room_id>')
@login_required
def start_room(room_id):
    conn = get_db()
    questions = conn.execute("SELECT * FROM questions WHERE room_id = ? ORDER BY level ASC", (room_id,)).fetchall()
    conn.close()
    
    if not questions:
        flash("No questions found in this room.", "danger")
        return redirect(url_for('dashboard'))

    session['active_quiz'] = [dict(q) for q in questions]
    session['quiz_index'] = 0
    session['quiz_score'] = 0
    session['quiz_room_id'] = room_id
    session['quiz_start_time'] = time.time()
    
    return redirect(url_for('play_quiz'))

@app.route('/start-dynamic-room')
@login_required
def start_dynamic_room():
    dynamic_qs = fetch_dynamic_api_questions(amount=10)
    session['active_quiz'] = dynamic_qs
    session['quiz_index'] = 0
    session['quiz_score'] = 0
    session['quiz_room_id'] = 999
    session['quiz_start_time'] = time.time()
    
    flash("Generated 10 real-time dynamic questions via API!", "success")
    return redirect(url_for('play_quiz'))

@app.route('/play-quiz', methods=['GET', 'POST'])
@login_required
def play_quiz():
    quiz = session.get('active_quiz', [])
    idx = session.get('quiz_index', 0)
    
    if not quiz or idx >= len(quiz):
        total_time = time.time() - session.get('quiz_start_time', time.time())
        final_score = session.get('quiz_score', 0)
        room_id = session.get('quiz_room_id', 1)
        
        conn = get_db()
        conn.execute('''
            INSERT INTO scores (username, department, plant_location, room_id, score, time_seconds)
            VALUES (?, ?, ?, ?, ?, ?)
        ''', (session['user'], session.get('department', 'General'), session.get('plant_location', 'Main Facility'), room_id, final_score, total_time))
        conn.commit()
        conn.close()
        
        session.pop('active_quiz', None)
        flash(f"Module Complete! Score: {final_score} PTS in {total_time:.1f}s.", "success")
        return redirect(url_for('dashboard'))

    question = quiz[idx]

    if request.method == 'POST':
        selected = request.form.get('option')
        if selected == question['correct_opt']:
            session['quiz_score'] = session.get('quiz_score', 0) + question['points']
            flash(f"Question {idx + 1} Correct! +{question['points']} PTS", "success")
        else:
            flash("Incorrect option selected.", "danger")
            
        session['quiz_index'] = idx + 1
        return redirect(url_for('play_quiz'))

    total_q = len(quiz)
    progress_pct = int(((idx) / total_q) * 100)

    content = '''
    <div class="max-w-2xl mx-auto bg-zinc-950/90 backdrop-blur-md p-6 sm:p-8 rounded-xl border border-brand-red/50 shadow-2xl">
        <div class="mb-6">
            <div class="flex justify-between text-xs text-zinc-400 mb-2">
                <span>QUESTION {{ idx + 1 }} OF {{ total_q }}</span>
                <span>PROGRESS: {{ progress_pct }}%</span>
            </div>
            <div class="w-full bg-zinc-900 h-2 rounded-full overflow-hidden border border-zinc-800">
                <div class="bg-brand-red h-full transition-all duration-300" style="width: {{ progress_pct }}%;"></div>
            </div>
        </div>

        <div class="flex items-center justify-between mb-4">
            <span class="bg-brand-red text-white text-xs font-bold px-3 py-1 rounded uppercase tracking-widest">
                {{ question['title'] }}
            </span>
            <span class="text-xs font-bold text-black bg-white px-2.5 py-1 rounded">
                +{{ question['points'] }} PTS
            </span>
        </div>

        <div class="bg-black/80 p-4 sm:p-5 rounded border border-zinc-800 mb-6">
            <p class="text-zinc-300 text-xs sm:text-sm leading-relaxed">{{ question['description'] }}</p>
        </div>

        <p class="font-semibold text-white text-sm sm:text-base mb-6">{{ question['question'] }}</p>

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
    return render_template_string(HTML_LAYOUT.replace('{% block content %}{% endblock %}', content), question=question, idx=idx, total_q=total_q, progress_pct=progress_pct)

@app.route('/admin', methods=['GET', 'POST'])
@login_required
@admin_required
def admin_panel():
    conn = get_db()
    if request.method == 'POST':
        room_id = request.form['room_id']
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
            INSERT INTO questions (room_id, level, title, description, question, opt_a, opt_b, opt_c, correct_opt, points)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (room_id, level, title, desc, q, opt_a, opt_b, opt_c, correct, pts))
        conn.commit()
        flash("New incident scenario published!", "success")

    users = conn.execute("SELECT id, username, role, department, plant_location FROM users").fetchall()
    q_count = conn.execute("SELECT COUNT(*) FROM questions").fetchone()[0]
    conn.close()

    content = '''
    <div class="space-y-8">
        <div class="bg-zinc-950/90 backdrop-blur-md p-6 rounded-xl border border-brand-red/50 shadow-xl">
            <h3 class="text-lg font-bold text-white mb-4 flex items-center justify-between border-b border-zinc-800 pb-2">
                <span>⚙️ Create Custom Operational Scenario</span>
                <span class="text-xs text-brand-red font-bold">TOTAL SCENARIOS: {{ q_count }}</span>
            </h3>
            
            <form method="POST" class="grid grid-cols-1 sm:grid-cols-2 gap-4 text-xs sm:text-sm">
                <div>
                    <label class="block text-zinc-400 mb-1">Target Room / Module</label>
                    <select name="room_id" class="w-full bg-black border border-zinc-800 p-3 rounded text-white focus:border-brand-red">
                        {% for r in rooms %}
                            <option value="{{ r['id'] }}">{{ r['name'] }}</option>
                        {% endfor %}
                    </select>
                </div>
                <div>
                    <label class="block text-zinc-400 mb-1">Level Order</label>
                    <input type="number" name="level" value="1" required class="w-full bg-black border border-zinc-800 p-3 rounded text-white focus:border-brand-red">
                </div>
                <div>
                    <label class="block text-zinc-400 mb-1">Points Value</label>
                    <input type="number" name="points" value="100" required class="w-full bg-black border border-zinc-800 p-3 rounded text-white focus:border-brand-red">
                </div>
                <div>
                    <label class="block text-zinc-400 mb-1">Correct Answer Choice</label>
                    <select name="correct_opt" class="w-full bg-black border border-zinc-800 p-3 rounded text-white focus:border-brand-red">
                        <option value="A">Option A</option>
                        <option value="B">Option B</option>
                        <option value="C">Option C</option>
                    </select>
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
                <div class="sm:col-span-2">
                    <label class="block text-zinc-400 mb-1">Option [C]</label>
                    <input type="text" name="opt_c" required class="w-full bg-black border border-zinc-800 p-3 rounded text-white focus:border-brand-red">
                </div>
                <div class="sm:col-span-2 mt-2">
                    <button type="submit" class="bg-white hover:bg-zinc-200 text-black font-extrabold px-6 py-3 rounded shadow transition-all active:scale-[0.98]">
                        Publish Scenario
                    </button>
                </div>
            </form>
        </div>

        <div class="bg-zinc-950/90 backdrop-blur-md p-6 rounded-xl border border-zinc-800 shadow-xl">
            <h4 class="font-bold text-white mb-4 text-sm sm:text-base">Registered System Accounts</h4>
            <div class="overflow-x-auto">
                <table class="w-full text-left text-xs text-zinc-300">
                    <thead class="bg-black text-zinc-400 uppercase tracking-wider">
                        <tr>
                            <th class="p-3">ID</th>
                            <th class="p-3">Username</th>
                            <th class="p-3">Department</th>
                            <th class="p-3">Plant Facility</th>
                            <th class="p-3">Role</th>
                        </tr>
                    </thead>
                    <tbody class="divide-y divide-zinc-900">
                        {% for u in users %}
                        <tr>
                            <td class="p-3">{{ u['id'] }}</td>
                            <td class="p-3 font-bold text-white">{{ u['username'] }}</td>
                            <td class="p-3 text-zinc-400">{{ u['department'] }}</td>
                            <td class="p-3 text-zinc-400">{{ u['plant_location'] }}</td>
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
    return render_template_string(HTML_LAYOUT.replace('{% block content %}{% endblock %}', content), users=users, rooms=ROOMS, q_count=q_count)

@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('login'))

if __name__ == '__main__':
    port = int(os.environ.get("PORT", 5000))
    app.run(host='0.0.0.0', port=port, debug=False)