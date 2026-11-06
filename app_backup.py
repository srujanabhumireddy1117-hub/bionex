import hashlib
import secrets
import streamlit as st
import sqlite3
import pandas as pd
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
    background: #f4f7fb;
}
[data-testid="stSidebar"] {
    background: #102a43;
}
[data-testid="stSidebar"] * {
    color: white !important;
}
h1, h2, h3 {
    color: #102a43;
}
div[data-testid="stMetric"] {
    background: white;
    padding: 15px;
    border-radius: 10px;
}
</style>
""", unsafe_allow_html=True)

# ---------------- SIDEBAR ----------------
st.sidebar.title("BioNex")
st.sidebar.write("Biomedical Waste Management")

page = st.sidebar.radio(
    "Navigation",
    [
        "Dashboard",
        "Waste Requests",
        "Collection Records",
        "Waste Segregation",
        "Smart Bin Monitoring",
        "Robot Monitoring",
        "Waste Tracking",
        "AI Assistant",
        "Reports",
        "Safety Guide"
    ]
)

# ---------------- DASHBOARD ----------------
if page == "Dashboard":
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
    st.title("Waste Request Management")

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
                    room, person, description,
                    category, priority, "Pending",
                    datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                ))
                st.success("Request created successfully!")
                st.rerun()
            else:
                st.error("Please fill all fields.")

    st.subheader("All Requests")
    data = query("SELECT * FROM requests ORDER BY id DESC")
    st.dataframe(data, use_container_width=True)

    if not data.empty:
        request_id = st.selectbox(
            "Select Request ID",
            data["id"].tolist()
        )

        new_status = st.selectbox(
            "Update Status",
            ["Pending", "Approved", "Rejected", "In Progress", "Completed"]
        )

        if st.button("Update Request"):
            execute(
                "UPDATE requests SET status=? WHERE id=?",
                (new_status, request_id)
            )
            st.success("Request status updated.")
            st.rerun()

# ---------------- COLLECTION RECORDS ----------------
elif page == "Collection Records":
    st.title("Waste Collection Records")

    requests = query(
        "SELECT id, room, category FROM requests"
    )

    if requests.empty:
        st.warning("Create a waste request before recording collection.")
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
                        request_id, category, description,
                        room, datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                    ))

                    execute(
                        "UPDATE requests SET status='Completed' WHERE id=?",
                        (request_id,)
                    )

                    st.success("Collection record saved!")
                    st.rerun()
                else:
                    st.error("Enter description and room.")

    records = query("SELECT * FROM waste_records ORDER BY id DESC")
    st.subheader("All Collection Records")
    st.dataframe(records, use_container_width=True)

# ---------------- SEGREGATION ----------------
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
            0, 100, int(row["fill_level"]),
            key="bin_" + row["category"]
        )

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

    robot = query("SELECT * FROM robot_status WHERE id=1")

    if not robot.empty:
        st.metric("Robot", robot.iloc[0]["robot_name"])
        st.metric("Battery", str(robot.iloc[0]["battery"]) + "%")
        st.write("Current Status:", robot.iloc[0]["status"])
        st.write("Location:", robot.iloc[0]["location"])

    status = st.selectbox(
        "Demo Robot Status",
        ["Idle", "Moving", "Collecting", "Charging", "Maintenance"]
    )

    battery = st.slider("Demo Battery (%)", 0, 100, 100)
    location = st.text_input("Demo Location", "Hospital Block A")

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

    records = query("SELECT * FROM waste_records ORDER BY id DESC")
    if not records.empty:
        st.subheader("Collected Waste")
        st.dataframe(records, use_container_width=True)
    else:
        st.info("No waste collection data available.")

    st.caption(
        "This is a workflow tracker, not live GPS tracking."
    )

# ---------------- AI ASSISTANT ----------------
elif page == "AI Assistant":
    st.title("BioNex Waste Assistant")
    st.write("Basic rule-based demo assistant.")

    question = st.text_input(
        "Enter a waste item or category"
    )

    if st.button("Get Guidance"):
        if question.strip():
            q = question.lower()

            if "needle" in q or "syringe" in q or "blade" in q:
                st.info("Specified sharps generally belong in the White category.")
            elif "plastic" in q or "iv set" in q or "tubing" in q:
                st.info("Specified contaminated recyclable plastics generally belong in the Red category.")
            elif "glass" in q or "vial" in q:
                st.info("Specified glassware generally belongs in the Blue category.")
            elif "soiled" in q or "anatomical" in q:
                st.info("Specified soiled and anatomical waste generally belongs in the Yellow category.")
            else:
                st.warning(
                    "Cannot confidently classify this item. "
                    "Check your hospital SOP and ask the authorized waste officer."
                )

            st.caption(
                "Demo guidance only. Verify every item against current rules and approved hospital SOP."
            )
        else:
            st.warning("Enter an item first.")

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

