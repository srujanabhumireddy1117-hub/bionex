
import hashlib
import secrets
import sqlite3
import pandas as pd
import streamlit as st
from datetime import datetime

# ---------------- PAGE CONFIG ----------------

st.set_page_config(
    page_title="BioNex",
    page_icon="",
    layout="wide"
)

DB = "bionex.db"


# ---------------- DATABASE ----------------

def connect():
    return sqlite3.connect(DB, check_same_thread=False)


def query(sql, params=()):
    conn = connect()
    try:
        return pd.read_sql_query(sql, conn, params=params)
    finally:
        conn.close()


def execute(sql, params=()):
    conn = connect()
    try:
        cur = conn.cursor()
        cur.execute(sql, params)
        conn.commit()
        return cur.lastrowid
    finally:
        conn.close()


# ---------------- PASSWORD SECURITY ----------------

def hash_password(password, salt=None):
    if salt is None:
        salt = secrets.token_hex(16)

    password_hash = hashlib.pbkdf2_hmac(
        "sha256",
        password.encode("utf-8"),
        salt.encode("utf-8"),
        200000
    ).hex()

    return password_hash, salt


def verify_password(password, stored_hash, salt):
    if not stored_hash or not salt:
        return False

    new_hash, _ = hash_password(password, salt)
    return secrets.compare_digest(new_hash, stored_hash)


# ---------------- DATABASE SETUP ----------------

def setup_database():

    conn = connect()
    cur = conn.cursor()

    cur.execute("""
    CREATE TABLE IF NOT EXISTS requests (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        room TEXT NOT NULL,
        requested_by TEXT NOT NULL,
        item_description TEXT NOT NULL,
        category TEXT NOT NULL,
        priority TEXT NOT NULL,
        status TEXT NOT NULL,
        created_at TEXT NOT NULL
    )
    """)

    cur.execute("""
    CREATE TABLE IF NOT EXISTS waste_records (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        request_id INTEGER NOT NULL,
        category TEXT NOT NULL,
        item_description TEXT NOT NULL,
        room TEXT NOT NULL,
        collected_at TEXT NOT NULL
    )
    """)

    cur.execute("""
    CREATE TABLE IF NOT EXISTS bin_status (
        category TEXT PRIMARY KEY,
        fill_level INTEGER NOT NULL DEFAULT 0
    )
    """)

    cur.execute("""
    CREATE TABLE IF NOT EXISTS robot_status (
        id INTEGER PRIMARY KEY,
        robot_name TEXT,
        status TEXT,
        battery INTEGER,
        location TEXT
    )
    """)

    cur.execute("""
    CREATE TABLE IF NOT EXISTS users (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        username TEXT UNIQUE NOT NULL,
        password_hash TEXT NOT NULL,
        salt TEXT,
        role TEXT NOT NULL,
        active INTEGER DEFAULT 1,
        created_at TEXT NOT NULL
    )
    """)

    # Migration for older databases
    columns = [
        row[1] for row in cur.execute(
            "PRAGMA table_info(users)"
        ).fetchall()
    ]

    if "salt" not in columns:
        cur.execute("ALTER TABLE users ADD COLUMN salt TEXT")

    for category in ["Yellow", "Red", "White", "Blue"]:
        cur.execute(
            "INSERT OR IGNORE INTO bin_status VALUES (?, 0)",
            (category,)
        )

    cur.execute("""
    INSERT OR IGNORE INTO robot_status
    VALUES (1, 'BioNex Robot 01', 'Idle', 100, 'Hospital Block A')
    """)

    conn.commit()
    conn.close()


setup_database()


# ---------------- DESIGN ----------------

st.markdown("""
<style>

.stApp {
    background-color: #f4f7fb;
}

[data-testid="stSidebar"] {
    background-color: #102a43;
}

[data-testid="stSidebar"] * {
    color: white !important;
}

h1, h2, h3 {
    color: #102a43;
}

div[data-testid="stMetric"] {
    background-color: white;
    padding: 15px;
    border-radius: 10px;
    box-shadow: 0 2px 8px rgba(0,0,0,0.05);
}

.stButton > button {
    background-color: #1976d2;
    color: white;
    border-radius: 8px;
    border: none;
    padding: 8px 18px;
}

</style>
""", unsafe_allow_html=True)


# ---------------- LOGIN SYSTEM ----------------

if "logged_in" not in st.session_state:
    st.session_state.logged_in = False

if "role" not in st.session_state:
    st.session_state.role = None

if "username" not in st.session_state:
    st.session_state.username = None


user_count = query(
    "SELECT COUNT(*) AS total FROM users"
).iloc[0]["total"]


if not st.session_state.logged_in:

    st.markdown("""
    <div style="
        background: linear-gradient(120deg,#102a43,#1976d2);
        padding:35px;
        border-radius:15px;
        text-align:center;
        color:white;
    ">
        <h1 style="color:white;">BioNex</h1>
        <h3 style="color:white;">
            Biomedical Waste Management System
        </h3>
        <p>Smart Healthcare Waste Management Platform</p>
        <p>Manage | Segregate | Monitor | Track</p>
    </div>
    """, unsafe_allow_html=True)

    st.write("")
    st.markdown("### Welcome to BioNex")

    st.write(
        "BioNex is a smart biomedical waste management platform "
        "designed to manage biomedical waste requests, segregation, "
        "collection records, smart bin monitoring and waste tracking "
        "in healthcare facilities. It helps healthcare staff organize "
        "waste-management activities and monitor collection information."
    )

    st.divider()

    if user_count == 0:

        st.subheader("Create First Admin Account")

        new_username = st.text_input("Admin Username")
        new_password = st.text_input(
            "Admin Password",
            type="password"
        )
        confirm_password = st.text_input(
            "Confirm Password",
            type="password"
        )

        if st.button("Create Admin", use_container_width=True):

            if not new_username.strip() or not new_password:
                st.error("Enter username and password.")

            elif new_password != confirm_password:
                st.error("Passwords do not match.")

            else:
                password_hash, salt = hash_password(new_password)

                try:
                    execute("""
                        INSERT INTO users
                        (username, password_hash, salt, role, active, created_at)
                        VALUES (?, ?, ?, ?, ?, ?)
                    """, (
                        new_username.strip(),
                        password_hash,
                        salt,
                        "Admin",
                        1,
                        datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                    ))

                    st.success("Admin account created. Please login.")
                    st.rerun()

                except sqlite3.IntegrityError:
                    st.error("Username already exists.")

    else:

        st.markdown("### Login to Continue")

        login_type = st.radio(
            "Select Login Type",
            ["Admin Login", "User / Staff Login"],
            horizontal=True
        )

        username = st.text_input("Username")
        password = st.text_input(
            "Password",
            type="password"
        )

        if st.button("Login", use_container_width=True):

            result = query(
                """
                SELECT username, password_hash, salt, role, active
                FROM users
                WHERE username = ?
                """,
                (username.strip(),)
            )

            if not result.empty:

                user = result.iloc[0]

                correct_role = (
                    (login_type == "Admin Login" and user["role"] == "Admin")
                    or
                    (login_type == "User / Staff Login" and user["role"] == "Staff")
                )

                if (
                    user["active"] == 1
                    and correct_role
                    and verify_password(
                        password,
                        user["password_hash"],
                        user["salt"]
                    )
                ):

                    st.session_state.logged_in = True
                    st.session_state.role = user["role"]
                    st.session_state.username = user["username"]

                    st.rerun()

                else:
                    st.error("Invalid username, password or login type.")

            else:
                st.error("Username not found.")

    st.stop()


# ---------------- LOGOUT ----------------

st.sidebar.title("BioNex")

st.sidebar.write(
    "Logged in as: " + st.session_state.username
)

st.sidebar.write(
    "Role: " + st.session_state.role
)

if st.sidebar.button("Logout"):
    st.session_state.logged_in = False
    st.session_state.role = None
    st.session_state.username = None
    st.rerun()


# ---------------- NAVIGATION ----------------

st.sidebar.divider()
st.sidebar.write("Biomedical Waste Management")

if st.session_state.role == "Admin":

    pages = [
        "Admin Dashboard",
        "Dashboard",
        "Waste Requests",
        "Collection Records",
        "Waste Segregation",
        "Smart Bin Monitoring",
        "Robot Monitoring",
        "Waste Tracking",
        "Reports",
        "Safety Guide"
    ]

else:

    pages = [
        "Dashboard",
        "Waste Requests",
        "Collection Records",
        "Waste Segregation",
        "Smart Bin Monitoring",
        "Waste Tracking",
        "Reports",
        "Safety Guide",
        "AI Assistant"
    ]


page = st.sidebar.radio("Navigation", pages)


# ---------------- ADMIN DASHBOARD ----------------

if page == "Admin Dashboard":

    st.title("BioNex Admin Dashboard")
    st.write("Welcome, Administrator")

    bins = query("SELECT * FROM bin_status")
    users = query("SELECT * FROM users")
    robots = query("SELECT * FROM robot_status")

    staff_count = (
        len(users[users["role"] == "Staff"])
        if not users.empty else 0
    )

    c1, c2, c3, c4 = st.columns(4)

    c1.metric("Registered Users", len(users))
    c2.metric("Staff Accounts", staff_count)
    c3.metric("Total Bins", len(bins))
    c4.metric("Total Robots", len(robots))

    st.subheader("Bin Monitoring")
    st.dataframe(bins, use_container_width=True)

    st.subheader("Robot Status")
    st.dataframe(robots, use_container_width=True)

    st.divider()
    st.subheader("Create Staff Login")

    with st.form("staff_creation_form"):

        staff_username = st.text_input("Staff Username")
        staff_password = st.text_input(
            "Staff Password",
            type="password"
        )
        confirm_staff_password = st.text_input(
            "Confirm Staff Password",
            type="password"
        )

        create_staff = st.form_submit_button("Create Staff Account")

        if create_staff:

            if not staff_username.strip() or not staff_password:
                st.error("Enter staff username and password.")

            elif staff_password != confirm_staff_password:
                st.error("Passwords do not match.")

            else:
                password_hash, salt = hash_password(staff_password)

                try:
                    execute("""
                        INSERT INTO users
                        (username, password_hash, salt, role, active, created_at)
                        VALUES (?, ?, ?, ?, ?, ?)
                    """, (
                        staff_username.strip(),
                        password_hash,
                        salt,
                        "Staff",
                        1,
                        datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                    ))

                    st.success("Staff account created successfully.")
                    st.rerun()

                except sqlite3.IntegrityError:
                    st.error("Username already exists.")


# ---------------- DASHBOARD ----------------

elif page == "Dashboard":

    st.title("BioNex Dashboard")
    st.write("Biomedical Waste Management System")

    requests = query("SELECT * FROM requests")
    records = query("SELECT * FROM waste_records")
    bins = query("SELECT * FROM bin_status")

    pending = (
        int((requests["status"] == "Pending").sum())
        if not requests.empty else 0
    )

    c1, c2, c3, c4 = st.columns(4)

    c1.metric("Total Requests", len(requests))
    c2.metric("Pending Requests", pending)
    c3.metric("Waste Collections", len(records))
    c4.metric("Total Bins", len(bins))

    st.subheader("Waste Collection Summary")

    if not records.empty:
        st.bar_chart(records["category"].value_counts())
    else:
        st.info("No collection records available.")

    st.subheader("Recent Requests")
    st.dataframe(requests.tail(10), use_container_width=True)


# ---------------- WASTE REQUESTS ----------------

elif page == "Waste Requests":

    if st.session_state.role == "Admin":

        # Admin: View-only requests table
        st.title("Waste Request Management")

        data = query(
            "SELECT * FROM requests ORDER BY id DESC"
        )

        if not data.empty:
            st.dataframe(data, use_container_width=True)
        else:
            st.info("No waste requests available.")

    else:

        # Staff: Full request functionality
        st.title("Waste Requests")

        with st.form("request_form"):

            room = st.text_input("Room Number")
            person = st.text_input("Requested By")
            description = st.text_area("Waste Description")

            category = st.selectbox(
                "Waste Category",
                ["Yellow", "Red", "White", "Blue"]
            )

            priority = st.selectbox(
                "Priority",
                ["Low", "Medium", "High", "Emergency"]
            )

            submitted = st.form_submit_button("Create Request")

            if submitted:

                if room.strip() and person.strip() and description.strip():

                    execute("""
                        INSERT INTO requests
                        (room, requested_by, item_description,
                         category, priority, status, created_at)
                        VALUES (?, ?, ?, ?, ?, ?, ?)
                    """, (
                        room,
                        person,
                        description,
                        category,
                        priority,
                        "Pending",
                        datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                    ))

                    st.success("Request created successfully!")
                    st.rerun()

                else:
                    st.error("Please fill all fields.")

        st.subheader("All Requests")

        data = query(
            "SELECT * FROM requests ORDER BY id DESC"
        )

        st.dataframe(data, use_container_width=True)


# ---------------- COLLECTION RECORDS ----------------

elif page == "Collection Records":

    if st.session_state.role == "Admin":

        # Admin: View-only collection table
        st.title("All Records")

        records = query(
            "SELECT * FROM waste_records ORDER BY id DESC"
        )

        if not records.empty:
            st.dataframe(records, use_container_width=True)
        else:
            st.info("No collection records available.")

    else:

        # Staff: Full collection functionality
        st.title("Collection Records")

        requests = query(
            "SELECT id, room, category FROM requests"
        )

        if requests.empty:

            st.warning(
                "Create a waste request before recording collection."
            )

        else:

            with st.form("collection_form"):

                request_id = st.selectbox(
                    "Select Request ID",
                    requests["id"].tolist()
                )

                category = st.selectbox(
                    "Waste Category",
                    ["Yellow", "Red", "White", "Blue"]
                )

                description = st.text_input("Item Description")
                room = st.text_input("Room Number")

                save = st.form_submit_button("Save Collection")

                if save:

                    if description.strip() and room.strip():

                        execute("""
                            INSERT INTO waste_records
                            (request_id, category, item_description,
                             room, collected_at)
                            VALUES (?, ?, ?, ?, ?)
                        """, (
                            request_id,
                            category,
                            description,
                            room,
                            datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                        ))

                        execute(
                            "UPDATE requests SET status='Completed' WHERE id=?",
                            (request_id,)
                        )

                        st.success("Collection record saved!")
                        st.rerun()

                    else:
                        st.error("Enter description and room.")

            records = query(
                "SELECT * FROM waste_records ORDER BY id DESC"
            )

            st.subheader("All Records")
            st.dataframe(records, use_container_width=True)


# ---------------- WASTE SEGREGATION ----------------

elif page == "Waste Segregation":

    st.title("Biomedical Waste Segregation")

    categories = {
        "Yellow": "Human and animal anatomical waste, soiled waste and other specified yellow-category waste.",
        "Red": "Contaminated recyclable plastic waste such as specified tubing, bottles and IV sets.",
        "White": "Specified sharps including needles, blades and scalpels in puncture-proof containers.",
        "Blue": "Specified glassware and metallic implants."
    }

    for name, details in categories.items():

        with st.expander(name + " Category"):
            st.write(details)

    st.warning(
        "Follow the current Biomedical Waste Management Rules "
        "and your hospital's approved segregation SOP."
    )


# ---------------- SMART BIN MONITORING ----------------

elif page == "Smart Bin Monitoring":

    st.title("Smart Bin Monitoring")
    st.caption("Demo simulation. Real sensor data is not connected.")

    bins = query("SELECT * FROM bin_status")

    for _, row in bins.iterrows():

        st.subheader(row["category"] + " Bin")

        level = st.slider(
            row["category"] + " fill level (%)",
            0,
            100,
            int(row["fill_level"]),
            key="bin_" + row["category"]
        )

        if st.session_state.role == "Admin":

            if st.button("Save " + row["category"] + " Bin Level"):

                execute(
                    "UPDATE bin_status SET fill_level=? WHERE category=?",
                    (level, row["category"])
                )

                st.success("Bin level updated.")
                st.rerun()

        if level >= 80:
            st.error("Alert: Bin needs collection.")
        else:
            st.success("Bin level is within demo threshold.")


# ---------------- ROBOT MONITORING ----------------

elif page == "Robot Monitoring":

    st.title("Robot Monitoring")
    st.caption("Demo controls only. No physical robot is connected.")

    robot = query(
        "SELECT * FROM robot_status WHERE id=1"
    )

    if not robot.empty:

        st.metric("Robot", robot.iloc[0]["robot_name"])
        st.metric(
            "Battery",
            str(robot.iloc[0]["battery"]) + "%"
        )

        st.write("Current Status:", robot.iloc[0]["status"])
        st.write("Location:", robot.iloc[0]["location"])

    status = st.selectbox(
        "Demo Robot Status",
        ["Idle", "Moving", "Collecting", "Charging", "Maintenance"]
    )

    battery = st.slider("Demo Battery (%)", 0, 100, 100)

    location = st.text_input(
        "Demo Location",
        "Hospital Block A"
    )

    if st.button("Update Robot Details"):

        execute("""
            UPDATE robot_status
            SET status=?, battery=?, location=?
            WHERE id=1
        """, (status, battery, location))

        st.success("Robot demo details updated.")
        st.rerun()


# ---------------- WASTE TRACKING ----------------

elif page == "Waste Tracking":

    st.title("Waste Tracking")

    stages = [
        "Waste Request",
        "Collection",
        "Segregation",
        "Transportation",
        "Treatment",
        "Final Disposal"
    ]

    st.write("Waste Management Workflow")

    for i, stage in enumerate(stages, 1):
        st.write(str(i) + ". " + stage)

    records = query(
        "SELECT * FROM waste_records ORDER BY id DESC"
    )

    if not records.empty:

        st.subheader("Collected Waste")
        st.dataframe(records, use_container_width=True)

    else:
        st.info("No waste collection data available.")

    st.caption(
        "This is a workflow tracker, not live GPS tracking."
    )


# ---------------- REPORTS ----------------

elif page == "Reports":

    st.title("Reports and Analytics")

    requests = query("SELECT * FROM requests")
    records = query("SELECT * FROM waste_records")

    a, b = st.columns(2)

    a.metric("Total Requests", len(requests))
    b.metric("Total Collections", len(records))

    st.subheader("Request Report")
    st.dataframe(requests, use_container_width=True)

    if not requests.empty:

        st.download_button(
            "Download Requests CSV",
            requests.to_csv(index=False).encode("utf-8"),
            "bionex_requests.csv",
            "text/csv"
        )

    st.subheader("Collection Report")
    st.dataframe(records, use_container_width=True)

    if not records.empty:

        st.download_button(
            "Download Collections CSV",
            records.to_csv(index=False).encode("utf-8"),
            "bionex_collections.csv",
            "text/csv"
        )


# ---------------- AI ASSISTANT ----------------

elif page == "AI Assistant":

    # Only Staff can access this page
    if st.session_state.role != "Staff":
        st.error("Access denied.")
        st.stop()

    st.title("BioNex AI Waste Assistant")

    st.write(
        "Enter a biomedical waste item to get basic "
        "waste segregation guidance."
    )

    waste_item = st.text_input(
        "Enter Waste Item",
        placeholder="Example: Needle, Syringe, Plastic tube"
    )

    if st.button("Get Guidance"):

        item = waste_item.lower().strip()

        if not item:
            st.warning("Please enter a waste item.")

        elif any(word in item for word in
                 ["needle", "syringe", "blade", "scalpel", "sharp"]):

            st.success("Suggested Category: WHITE")
            st.write(
                "Specified sharps should be placed in "
                "puncture-proof, leak-proof and tamper-proof containers."
            )

        elif any(word in item for word in
                 ["plastic", "iv set", "tubing", "catheter"]):

            st.success("Suggested Category: RED")
            st.write(
                "Specified contaminated recyclable plastic waste "
                "belongs in the red category."
            )

        elif any(word in item for word in
                 ["glass", "vial", "bottle", "ampoule"]):

            st.success("Suggested Category: BLUE")
            st.write(
                "Specified glassware belongs in the blue category."
            )

        elif any(word in item for word in
                 ["soiled", "cotton", "dressing", "anatomical"]):

            st.success("Suggested Category: YELLOW")
            st.write(
                "Specified soiled and anatomical waste belongs "
                "in the yellow category."
            )

        else:
            st.warning(
                "Category could not be identified. "
                "Please check your hospital's approved segregation SOP."
            )

    st.caption(
        "This is a rule-based demo assistant, not a validated AI diagnostic system."
    )


# ---------------- SAFETY GUIDE ----------------

elif page == "Safety Guide":

    st.title("Biomedical Waste Safety Guide")

    st.write("1. Segregate waste at the point of generation.")
    st.write("2. Use the correct, labelled colour-coded container.")
    st.write("3. Do not mix different waste categories.")
    st.write("4. Use approved PPE and safe handling procedures.")
    st.write("5. Record collection and handover details.")
    st.write("6. Follow authorized treatment and disposal procedures.")

    st.warning(
        "Always follow current national rules and the hospital's approved SOP. "
        "This prototype is not a substitute for official safety instructions."
    )
