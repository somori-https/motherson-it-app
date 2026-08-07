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

DB_NAME = "motherson_portal.db"

# =========================================================================
# EMBEDDED MOTHERSON SVG LOGO
# =========================================================================
MOTHERSON_LOGO_SVG = """
<svg class="h-8 w-auto" viewBox="0 0 320 50" fill="none" xmlns="http://www.w3.org/2000/svg">
    <rect width="320" height="50" rx="4" fill="#000000"/>
    <path d="M12 10H22L30 30L38 10H48V40H40V20L32 38H28L20 20V40H12V10Z" fill="#E11D48"/>
    <text x="56" y="34" font-family="-apple-system, BlinkMacSystemFont, Arial, sans-serif" font-weight="900" font-size="24" fill="#FFFFFF" letter-spacing="2.5">MOTHERSON</text>
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
# 1. DATABASE INITIALIZATION & SEEDING (20+ Questions Per Room)
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
    
    # Enforce default admin account
    admin_hash = generate_password_hash("Admin#Motherson2026!")
    cursor.execute("SELECT * FROM users WHERE username = 'admin'")
    if cursor.fetchone():
        cursor.execute("UPDATE users SET password_hash = ?, role = 'admin' WHERE username = 'admin'", (admin_hash,))
    else:
        cursor.execute("INSERT INTO users (username, password_hash, role, department, plant_location) VALUES ('admin', ?, 'admin', 'IT & Digital Infrastructure', 'Global HQ & IT Center')", (admin_hash,))
    
    # Check if questions exist; if not, seed 20+ questions per room
    cursor.execute("SELECT COUNT(*) FROM questions")
    if cursor.fetchone()[0] == 0:
        seed_questions(cursor)
    
    conn.commit()
    conn.close()

def seed_questions(cursor):
    """Seeds 20 high-quality operational questions for each of the 5 enterprise rooms (100 total)."""
    
    base_questions = {
        1: [ # Room 1: Hardware & Workstation
            ("aPIMS Scanner Unresponsive", "Line A scanner stops sending barcode telemetry.", "Recommended first step?", "Reboot plant power cabinet", "Unplug USB, inspect pin connector, reconnect", "Reinstall OS", "B"),
            ("Thermal Barcode Printer Smudging", "Labels on line 3 are illegible.", "How to resolve smudging?", "Increase feed speed", "Clean thermal printhead with isopropyl alcohol swab", "Replace network cable", "B"),
            ("Workstation Blue Screen (BSOD)", "Assembly terminal crashes repeatedly.", "Correct initial action?", "Log incident ticket with RAM dump codes", "Sledgehammer terminal", "Ignore and skip parts", "A"),
            ("Touchscreen Calibration Drift", "Operator clicks button A, screen clicks B.", "Solution?", "Run Windows Touch Calibration Utility", "Replace monitor cable", "Reboot switch", "A"),
            ("RFID Reader Offline", "Pallet gate 2 RFID fails to ping.", "Primary check?", "Verify PoE ethernet link lights on reader port", "Check plant air pressure", "Call HR", "A"),
            ("Handheld Terminal Battery Draining", "Scanners die after 1 hour.", "Correct protocol?", "Charge on 24V dock, replace degraded Li-Ion cell", "Wrap in foil", "Leave plugged into PC", "A"),
            ("Label Printer Paper Jam", "Zebra printer flashing red error LED.", "Safe clearing procedure?", "Open housing latch, clear ribbon path, press Feed", "Use metal screwdriver to pry paper", "Force pull paper", "A"),
            ("Kiosk Monitor Flickering", "QC inspection screen blinks continuously.", "Troubleshooting order?", "Check DisplayPort cable seat, replace cable, test GPU", "Replace desk", "Upgrade RAM", "A"),
            ("Scale Telemetry Disconnected", "Weight sensor sending zero values.", "Next step?", "Verify RS232-to-USB serial driver state", "Recalibrate line speed", "Restart SAP server", "A"),
            ("Workstation Overheating", "Dust accumulation causing CPU throttling.", "Action required?", "Schedule compressed air blowout during maintenance window", "Pour water on chassis", "Lower ambient light", "A"),
            ("USB Dongle Unrecognized", "CAD license key missing error.", "Correct response?", "Reinsert into dedicated rear USB port, check device manager", "Format local drive", "Buy new license", "A"),
            ("Wireless Barcode Scanner Disconnects", "Scanner loses Bluetooth base link.", "Fix?", "Dock scanner in cradle to re-pair RF channel", "Power down workstation", "Replace barcode label", "A"),
            ("Line Workstation No Power", "Operator hits power button, zero response.", "Check?", "Verify UPS battery outlet switch & AC power cable", "Replace Ethernet cable", "Call electrician", "A"),
            ("Smart Card Reader Lockout", "Badge login fails for all operators.", "Resolution?", "Restart SmartCard service in Windows Services", "Re-issue all employee badges", "Disable login", "A"),
            ("Industrial Mouse Trackball Stuck", "Oily residue locking cursor.", "Action?", "Disassemble optical ring and clean trackball bearings", "Oil the trackball", "Replace motherboard", "A"),
            ("Audio Alarm Horn Silence", "Fault warning horn not sounding.", "Check?", "Test 12V relay output module on station PLC", "Mute volume slider", "Change speaker wire", "A"),
            ("Dual Monitor Orientation Flipped", "QC workstation screen display inverted.", "Quick key shortcut?", "Press Ctrl + Alt + Up Arrow", "Turn monitor upside down", "Reinstall graphics driver", "A"),
            ("High Density Barcode Reader Failure", "2D Matrix code on harness not reading.", "Fix?", "Clean camera lens glass and check LED ring lighting", "Increase barcode size manually", "Skip scanning", "A"),
            ("POS Terminal Keyboard Lockup", "Keypad unresponsive during inventory intake.", "Action?", "Unplug PS/2 or USB plug, check for bent pins", "Replace SSD", "Log out user", "A"),
            ("Workstation BIOS Clock Reset", "Time reverts to 2000 on power off.", "Fix?", "Replace CR2032 CMOS coin battery on motherboard", "Change time zone every boot", "Reinstall OS", "A")
        ],
        2: [ # Room 2: Automation & aPIMS
            ("aPIMS Line Stoppage Alert", "Line 4 conveyor stops automatically.", "Action?", "Inspect PLC error stack in aPIMS supervisor console", "Force conveyor start button", "Bypass safety light curtain", "A"),
            ("Screw Torque Telemetry Fault", "Torque gun value not writing to database.", "Check?", "Verify Modbus TCP driver connection status", "Tighten screw manually", "Turn off torque tool", "A"),
            ("PLC Communication Loss", "Siemens S7 PLC shows red SF error.", "Step 1?", "Check Industrial Ethernet cable to Profinet switch", "Power cycle whole plant", "Delete PLC program", "A"),
            ("Vision Inspection Camera Fail", "Optical camera rejecting 100% good parts.", "Correction?", "Clean lens cover, recalibrate strobe illumination LED", "Lower quality threshold to 0%", "Turn off camera", "A"),
            ("aPIMS License Expiration Alert", "System warning appears across terminals.", "Resolution?", "Notify IT Admin to upload valid corporate SLA license file", "Change PC clock back 2 years", "Ignore prompt", "A"),
            ("Conveyor Sensor Misalignment", "Photoelectric eye missing box trigger.", "Fix?", "Align reflector bracket and wipe optical sensor lens", "Increase conveyor speed", "Disable sensor in code", "A"),
            ("Robotic Arm Axis Interlock", "Robot station halted due to safety trigger.", "Protocol?", "Clear safety zone, reset emergency circuit, resume job", "Push robot manually", "Bypass interlock switch", "A"),
            ("aPIMS Database Queue Overflow", "Local station buffering 500 scans offline.", "Fix?", "Check network gateway ping to central SQL cluster", "Clear local buffer manually", "Reboot PC", "A"),
            ("Pneumatic Valve Solenoid Fault", "Part ejector arm fails to extend.", "Check?", "Test 24V DC signal output on PLC digital module", "Increase plant main air to 200 PSI", "Hit valve with hammer", "A"),
            ("Temperature Sensor Out-of-Bounds", "Soldering station reading 999C error.", "Cause?", "Thermocouple wire broken or disconnected", "Soldering iron too hot", "aPIMS code glitch", "A"),
            ("HMI Touch Panel Frozen", "Operator screen frozen on station 12.", "Recovery?", "Soft reboot HMI via maintenance key switch", "Smash screen glass", "Cut power wire", "A"),
            ("Barcode Verifier Grade Drop", "Grade drops from A to F on harness label.", "Fix?", "Clean focal glass and check label print DPI setting", "Change verifier software", "Override grade in DB", "A"),
            ("aPIMS Shift Report Sync Failure", "End-of-shift metrics not exporting.", "Action?", "Run manual sync retry script via supervisor dashboard", "Delete shift records", "Re-enter data in Excel", "A"),
            ("Safety Light Curtain Muting Error", "Part entry triggers instant E-Stop.", "Check?", "Check muting sensor alignment timing", "Turn off light curtain", "Speed up part entry", "A"),
            ("VFD Motor Drive Overcurrent", "Conveyor motor tripping fault code F0001.", "Action?", "Inspect conveyor belt jam before resetting VFD drive", "Increase circuit breaker rating", "Force motor spin", "A"),
            ("Part Positioning Laser Drift", "Laser line offset by 5mm.", "Correction?", "Adjust optical mounting rig using calibration target", "Change part specifications", "Ignore deviation", "A"),
            ("aPIMS User Access Denied", "New operator badge fails at station 4.", "Fix?", "Add operator employee ID to aPIMS Active Directory group", "Share admin password", "Bypass station authorization", "A"),
            ("Proximity Switch Inductive Fault", "Metal carrier presence not detected.", "Check?", "Verify sensing distance (gap < 2mm) and metallic dust buildup", "Replace carrier", "Bypass PLC input", "A"),
            ("Automated Guided Vehicle (AGV) Lost", "AGV stopped in main aisle with path fault.", "Action?", "Clean floor optical tape or LiDAR dome lens", "Push AGV into wall", "Turn off LiDAR", "A"),
            ("aPIMS Real-time OEE Drop", "Dashboard showing unexpected 0% availability.", "Check?", "Verify shift pattern calendar settings in server", "Call vendor", "Close dashboard", "A")
        ],
        3: [ # Room 3: Cybersecurity
            ("Suspicious Phishing Email Received", "Email asking for password reset with urgent tag.", "Correct response?", "Report email using Outlook Report Phishing button", "Click link to verify", "Forward to all coworkers", "A"),
            ("Unknown USB Drive Found in Parking Lot", "Flash drive labeled 'Executive Bonuses'.", "Action?", "Hand over immediately to IT Security team", "Plug into workstation", "Plug into personal laptop", "A"),
            ("Unusual Pop-up Threat Warning", "Screen claims 'PC Infected - Call Number'.", "Correct procedure?", "Disconnect network cable & alert IT Helpdesk", "Call phone number", "Pay ransom", "A"),
            ("Ransomware File Extension Change", "Files suddenly changing to .locked extension.", "Emergency step?", "Unplug network cable immediately to stop spread", "Restart computer", "Email hacker", "A"),
            ("Tailgating Security Violation", "Unbadged stranger following you into server room.", "Action?", "Politely stop them and request security escort check", "Hold door open", "Give them your badge", "A"),
            ("Password Policy Requirements", "Creating new corporate network password.", "Best practice?", "Use 14+ characters mixing letters, numbers, symbols", "Use 'Password123'", "Write on sticky note", "A"),
            ("Unauthorized Wireless Access Point", "Rogue Wi-Fi hotspot named 'Motherson_Guest_Free'.", "Action?", "Do not connect; report rogue SSID to Network IT", "Connect corporate laptop", "Stream video", "A"),
            ("Shared Credential Security Hazard", "Co-worker asks to borrow your SAP login.", "Response?", "Refuse and direct them to IT for their own account", "Give password", "Write password down", "A"),
            ("MFA Verification Prompt Unexpected", "Receiving Microsoft Authenticator prompt at 2 AM.", "Action?", "Deny prompt immediately and change password", "Approve request", "Ignore forever", "A"),
            ("Clean Desk Policy Violation", "Confidential wiring schematics left on desk overnight.", "Requirement?", "Lock sensitive documents in safe before leaving", "Leave on desk", "Throw in standard trash", "A"),
            ("Webcam Light On Randomly", "Laptop camera LED turns on unexpectedly.", "Action?", "Close browser tabs & report suspected malware to IT", "Cover with tape only", "Ignore", "A"),
            ("Social Engineering Phone Call", "Caller claims to be 'IT Support' asking for password.", "Action?", "Hang up and verify caller identity via official directory", "Provide password", "Give credit card", "A"),
            ("Public Wi-Fi Laptop Usage", "Working from airport or hotel on company laptop.", "Mandatory tool?", "Connect to Motherson Corporate Secure VPN first", "Use open Wi-Fi without VPN", "Disable firewall", "A"),
            ("Software Download Request", "Downloading unauthorized file converter from web.", "Policy?", "Only download approved software via Corporate Portal", "Download crack file", "Disable antivirus", "A"),
            ("Sensitive Data Disposal", "Discarding old printed customer schematics.", "Correct disposal?", "Deposit in locked Cross-Cut Shredding Bins", "Throw in recycle bin", "Burn at home", "A"),
            ("Outdated Operating System Prompt", "Windows update reboot popup appears.", "Action?", "Save work and allow system update installation", "Postpone indefinitely", "Disable Windows Update", "A"),
            ("Badge Sharing Policy", "Employee forgot badge at home.", "Correct process?", "Obtain temporary visitor/employee pass from Security", "Borrow colleague badge", "Force open turnstile", "A"),
            ("Unauthorized Remote Desktop Tool", "Employee installed AnyDesk without permission.", "Risk?", "Security violation; remove and use IT-approved tool", "Keep using it", "Share ID online", "A"),
            ("Database Export Security Protocol", "Exporting 50,000 customer records to CSV.", "Requirement?", "Manager approval & strict file encryption mandatory", "Upload to personal Google Drive", "Send via WhatsApp", "A"),
            ("Locked Screen Requirement", "Stepping away from workstation for 2 minutes.", "Shortcut?", "Press Windows Key + L to lock terminal", "Leave screen open", "Turn off monitor only", "A")
        ],
        4: [ # Room 4: Network & Infrastructure
            ("IP Address Conflict Error", "Windows alert: 'Another IP conflict exists'.", "Cause?", "Two devices assigned identical static IP addresses", "Bad cable", "Server fire", "A"),
            ("Fiber Optic Link Loss", "Core switch fiber trunk LED off.", "Action?", "Inspect fiber patch cord for bends and test with OTDR", "Splice fiber with scissors", "Reboot core router", "A"),
            ("Industrial Wi-Fi Deadzone", "Forklifts lose connection in Bay 4.", "Solution?", "Perform RF site survey and adjust Access Point power", "Add home router", "Tell driver to drive slower", "A"),
            ("Network Switch Loop", "All switch LEDs blinking rapidly, network down.", "Cause?", "Broadcast storm caused by redundant unmanaged cable loop", "Virus attack", "Power outage", "A"),
            ("VLAN Isolation Issue", "Plant PC cannot ping SAP server.", "Check?", "Verify switch port is configured in correct VLAN", "Replace PC CPU", "Change PC hostname", "A"),
            ("PoE Camera Losing Power", "IP Security camera cycling on/off.", "Fix?", "Check PoE wattage budget on switch port", "Replace camera glass", "Reboot DNS server", "A"),
            ("DHCP Scope Exhaustion", "New laptops receiving 169.254.x.x IP.", "Cause?", "DHCP server pool ran out of available leases", "ISP internet line down", "Bad password", "A"),
            ("High Latency / Packet Loss", "Ping times jump from 2ms to 1500ms.", "Troubleshooting tool?", "Run traceroute and ping -t to locate bottleneck switch", "Format C: drive", "Restart computer", "A"),
            ("Firewall Rule Blocking Port 8080", "aPIMS web console unreachable.", "Fix?", "Create inbound rule allowing TCP 8080 on firewall", "Disable entire firewall permanently", "Change PC MAC address", "A"),
            ("Patch Panel Port Damage", "Ethernet plug clip broken in wall jack.", "Fix?", "Re-terminate keystone jack with punchdown tool", "Tape cable to wall", "Glue connector inside", "A"),
            ("DNS Resolution Failure", "Can ping 8.8.8.8 but cannot open web links.", "Diagnosis?", "DNS server unreachable or misconfigured", "Network card destroyed", "No power", "A"),
            ("Gigabit Speed Dropped to 100Mbps", "PC speed test shows exactly 90Mbps.", "Cause?", "Damaged ethernet cable pin or 4-core cable limitation", "Hard drive too full", "Monitor refresh rate", "A"),
            ("SFP Transceiver Failure", "Fiber module in switch slot 1 not lit.", "Action?", "Reseat SFP optic or replace with spare transceiver", "Blow air into fiber slot", "Reinstall OS", "A"),
            ("Wireless Controller Offline", "All 30 Access Points dropping clients.", "Check?", "Verify central Wireless LAN Controller (WLC) service", "Replace all APs", "Disable Wi-Fi", "A"),
            ("Unshielded Cable Noise Interference", "Cable running next to 480V motor throwing errors.", "Fix?", "Replace with Shielded Twisted Pair (STP) Cat6A cable", "Wrap with electrical tape", "Ignore errors", "A"),
            ("VPN Tunnel Disconnected", "Remote plant site lost connection to HQ.", "First check?", "Verify public IP ping gateway and IPSec phase 1 log", "Reinstall Windows", "Replace router box", "A"),
            ("Subnet Mask Misconfiguration", "192.168.1.50 cannot talk to 192.168.1.200.", "Cause?", "Subnet mask set to 255.255.255.192 instead of /24", "Router destroyed", "Duplicate MAC address", "A"),
            ("Network Rack Temperature High", "Switch cabinet alarm sounding at 55°C.", "Action?", "Inspect rack ventilation fans and air filter intake", "Open rack and leave it", "Turn off rack", "A"),
            ("MAC Address Filtering Rejection", "New industrial PC rejected by switch.", "Fix?", "Whitelist new PC MAC address in switch port security", "Change IP address", "Reboot switch", "A"),
            ("Load Balancer Traffic Imbalance", "Server 1 at 100% CPU, Server 2 at 0%.", "Fix?", "Rebalance algorithm in F5/NGINX config", "Delete Server 1", "Add more RAM", "A")
        ],
        5: [ # Room 5: ERP & SAP
            ("SAP Transaction MIGO Error", "Goods movement blocked with material lock.", "Cause?", "Another user holds active lock on material record", "Database deleted", "Printer offline", "A"),
            ("Barcode Scanner Extra Character Bug", "Scanned barcode adds unwanted enter key.", "Fix?", "Reconfigure scanner suffix barcode settings", "Edit SAP source code", "Type barcode manually", "A"),
            ("Out of Memory Error during SAP Export", "Exporting 100k lines crashes client.", "Solution?", "Export in background job mode or narrow date filter", "Buy new monitor", "Increase screen resolution", "A"),
            ("Purchase Order Release Block", "PO stuck in 'Awaiting Approval' status.", "Action?", "Check release strategy workflow hierarchy in SAP", "Override DB table", "Delete PO", "A"),
            ("Inventory Discrepancy Fault", "System shows 100 units, physical shelf has 80.", "Protocol?", "Perform cycle count posting and trigger variance audit", "Adjust DB manually", "Hide 20 parts", "A"),
            ("SAP GUI Disconnect Timeout", "User idle for 15 minutes gets kicked off.", "Reason?", "Standard security idle session auto-logoff policy", "Server crash", "Network destroyed", "A"),
            ("Duplicate Material Number Warning", "Creating new part throws error.", "Fix?", "Search existing material index before creating new ID", "Add random letter to ID", "Ignore error", "A"),
            ("Batch Number Tracking Expiry", "Raw material batch expired in system.", "Action?", "Quarantine physical batch and re-test via Quality module", "Change expiry date", "Use batch anyway", "A"),
            ("Shipping Manifest EDI Failure", "Automated EDI file rejected by logistics partner.", "Check?", "Inspect XML payload structure for missing tax/VAT tags", "Call truck driver", "Delete shipment", "A"),
            ("Printer Destination Unknown in SAP", "SAP print job disappears without error.", "Check?", "Verify SAP SPAD spool device server assignment", "Buy new printer", "Reboot SAP server", "A"),
            ("Billing Document Lock Error", "Invoice cannot be created due to block.", "Cause?", "Delivery document not marked as Goods Issued", "Credit card expired", "SAP GUI out of date", "A"),
            ("SAP User Password Locked", "3 incorrect attempts locks account.", "Fix?", "Self-service unlock portal or IT Helpdesk ticket", "Create new account", "Log in as colleague", "A"),
            ("Production Order Confirmation Fail", "Cannot backflush components.", "Cause?", "Insufficient raw material stock balance in storage location", "Workstation offline", "Scanner broken", "A"),
            ("Vendor Master Record Incomplete", "Cannot issue payment to supplier.", "Fix?", "Complete IBAN/SWIFT and Tax ID fields in vendor master", "Pay with cash", "Delete vendor", "A"),
            ("SAP Logon Pad Server List Missing", "SAP GUI opens with empty connection list.", "Fix?", "Restore SAPUILandscape.xml file from network share", "Reinstall Windows", "Format hard drive", "A"),
            ("Valuation Class Misconfiguration", "Financial posting fails during goods receipt.", "Action?", "Update G/L account mapping in MM-FI integration table", "Ignore financial error", "Delete G/L account", "A"),
            ("Serialized Part Number Double Allocation", "Serial #10023 already exists.", "Fix?", "Scan unique serial number from physical part tag", "Override serial number", "Delete original part", "A"),
            ("MRP Run Job Failed", "Material Requirements Planning crashed overnight.", "Check?", "Inspect background job spool log in transaction SM37", "Run MRP manually on 1 item", "Delete job", "A"),
            ("Custom Z-Transaction Dump", "Custom Motherson transaction throws ABAP dump.", "Action?", "Log ticket with ABAP development team with ST22 log", "Restart PC", "Use standard transaction", "A"),
            ("Customer Master Credit Limit Exceeded", "Sales order blocked automatically.", "Fix?", "Finance team review & credit limit increase approval", "Bypass credit check", "Cancel order", "A")
        ]
    }

    for room_id, q_list in base_questions.items():
        for idx, item in enumerate(q_list, start=1):
            cursor.execute('''
                INSERT INTO questions (room_id, level, title, description, question, opt_a, opt_b, opt_c, correct_opt, points)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (room_id, idx, item[0], item[1], item[2], item[3], item[4], item[5], item[6], 100))

# =========================================================================
# 2. DYNAMIC API & PROCEDURAL QUESTION GENERATOR
# =========================================================================
def fetch_dynamic_api_questions(amount=10):
    """
    Fetches dynamic computer science/IT questions from an open public API.
    Falls back gracefully to dynamic procedural scenario generation if offline.
    """
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
    
    # Fallback to dynamic procedural generation if external API is unreachable
    return generate_procedural_questions(amount)

def generate_procedural_questions(count=10):
    """Generates procedural infinite variations of plant incidents."""
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
# 4. MASTER HTML & TAILWIND UI LAYOUT
# =========================================================================
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
      
      .bg-radial-gradient {
        position: fixed;
        top: 0;
        left: 0;
        width: 100%;
        height: 100%;
        background: radial-gradient(circle at center, #18181b 0%, #000000 100%);
        z-index: -1;
      }
    </style>
</head>
<body class="h-full flex flex-col text-white bg-black antialiased selection:bg-brand-red selection:text-white" x-data="{ mobileMenuOpen: false }">
    
    <div class="bg-radial-gradient"></div>

    <!-- TOP NAVIGATION BAR -->
    <nav class="bg-black/90 backdrop-blur-md border-b border-brand-red/50 sticky top-0 z-50">
        <div class="max-w-6xl mx-auto px-4 sm:px-6 lg:px-8">
            <div class="flex items-center justify-between h-16">
                
                <!-- Brand Official Logo -->
                <div class="flex items-center space-x-3">
                    <a href="/dashboard" class="flex items-center bg-black p-1 rounded border border-zinc-800 hover:border-brand-red transition-colors">
                        ''' + MOTHERSON_LOGO_SVG + '''
                    </a>
                    <span class="hidden sm:inline-block text-xs font-semibold uppercase tracking-widest text-zinc-400 border-l border-zinc-800 pl-3">
                        Enterprise Command Portal
                    </span>
                </div>

                <!-- Desktop Menu -->
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

    <!-- MAIN CONTAINER -->
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

    <!-- FOOTER -->
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
            <div class="inline-block bg-black p-2 rounded-lg border border-zinc-800 shadow-lg mb-3">
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
    return render_template_string(HTML_LAYOUT.replace('{% block content %}{% endblock %}', content), departments=DEPARTMENTS, plants=PLANT_LOCATIONS)

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
            <div class="inline-block bg-black p-2 rounded-lg border border-zinc-800 shadow-lg mb-3">
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
    rankings = conn.execute('''
        SELECT username, department, plant_location, score, time_seconds, completed_at 
        FROM scores ORDER BY score DESC, time_seconds ASC LIMIT 10
    ''').fetchall()
    
    # User high score query
    user_best = conn.execute('''
        SELECT MAX(score) as best_score FROM scores WHERE username = ?
    ''', (session['user'],)).fetchone()
    conn.close()

    content = '''
    <div class="space-y-8">
        
        <!-- Employee Profile Header -->
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

        <!-- Room Selection Grid -->
        <div>
            <div class="flex items-center justify-between mb-4">
                <h3 class="text-lg font-bold text-white">🏭 Operational Training Rooms</h3>
                <span class="text-xs text-zinc-400">20+ Scenarios Per Module</span>
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

                <!-- Dynamic API Challenge Room -->
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

        <!-- Global Leaderboard -->
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

    # Store full list of questions in session
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
        # Quiz Complete!
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
            flash(f"Incorrect option selected. Systems require standard response protocols.", "danger")
            
        session['quiz_index'] = idx + 1
        return redirect(url_for('play_quiz'))

    total_q = len(quiz)
    progress_pct = int(((idx) / total_q) * 100)

    content = '''
    <div class="max-w-2xl mx-auto bg-zinc-950/90 backdrop-blur-md p-6 sm:p-8 rounded-xl border border-brand-red/50 shadow-2xl">
        
        <!-- Progress bar -->
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
        flash("New incident scenario published to database!", "success")

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
    app.run(host='0.0.0.0', port=5000, debug=True)