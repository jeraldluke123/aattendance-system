import streamlit as st
import pandas as pd
import qrcode
from datetime import datetime
import sqlite3
from io import BytesIO
import base64
import uuid

# Page config
st.set_page_config(
    page_title="🎓 Smart Attendance System",
    page_icon="🎓",
    layout="wide"
)

# Styling
st.markdown("""
<style>
    .main-header {
        background: linear-gradient(90deg, #667eea 0%, #764ba2 100%);
        padding: 2rem;
        border-radius: 15px;
        color: white;
        text-align: center;
        margin-bottom: 2rem;
    }
    .success-alert {
        background: #d4edda;
        border: 1px solid #c3e6cb;
        color: #155724;
        padding: 1rem;
        border-radius: 8px;
        margin: 1rem 0;
    }
</style>
""", unsafe_allow_html=True)

# Database setup
@st.cache_resource
def init_db():
    conn = sqlite3.connect('attendance.db', check_same_thread=False)
    c = conn.cursor()
    
    c.execute('''CREATE TABLE IF NOT EXISTS students
                 (id INTEGER PRIMARY KEY, name TEXT, reg_no TEXT UNIQUE, 
                  department TEXT, parent_phone TEXT, barcode TEXT UNIQUE)''')
    
    c.execute('''CREATE TABLE IF NOT EXISTS attendance
                 (id INTEGER PRIMARY KEY, student_id INTEGER, 
                  date TEXT, time TEXT, status TEXT)''')
    
    conn.commit()
    return conn

def generate_qr(data):
    qr = qrcode.QRCode(version=1, box_size=10, border=5)
    qr.add_data(data)
    qr.make(fit=True)
    
    img = qr.make_image(fill_color="black", back_color="white")
    buf = BytesIO()
    img.save(buf, format='PNG')
    buf.seek(0)
    return base64.b64encode(buf.getvalue()).decode()

def main():
    conn = init_db()
    
    # Header
    st.markdown("""
    <div class="main-header">
        <h1>🎓 Smart Attendance Management System</h1>
        <p>✨ Real-time QR Scanning • Professional Reports • Mobile Responsive</p>
    </div>
    """, unsafe_allow_html=True)
    
    # Sidebar
    st.sidebar.title("🎯 Navigation")
    page = st.sidebar.selectbox("Choose Action", [
        "📊 Dashboard", 
        "👨‍🎓 Register Student", 
        "📷 QR Scanner", 
        "📈 Reports"
    ])
    
    if page == "📊 Dashboard":
        show_dashboard(conn)
    elif page == "👨‍🎓 Register Student":
        register_student(conn)
    elif page == "📷 QR Scanner":
        qr_scanner(conn)
    elif page == "📈 Reports":
        show_reports(conn)

def show_dashboard(conn):
    st.header("📊 Dashboard")
    
    c = conn.cursor()
    total_students = c.execute("SELECT COUNT(*) FROM students").fetchone()[0]
    today = datetime.now().strftime('%Y-%m-%d')
    today_attendance = c.execute("SELECT COUNT(*) FROM attendance WHERE date=?", (today,)).fetchone()[0]
    
    col1, col2, col3 = st.columns(3)
    with col1:
        st.metric("👨‍🎓 Total Students", total_students)
    with col2:
        st.metric("✅ Today's Attendance", today_attendance)
    with col3:
        if total_students > 0:
            rate = (today_attendance / total_students) * 100
            st.metric("📊 Attendance Rate", f"{rate:.1f}%")
        else:
            st.metric("📊 Attendance Rate", "0%")
    
    st.subheader("📋 Recent Records")
    recent = pd.read_sql("""
        SELECT s.name, s.reg_no, a.date, a.time, a.status 
        FROM attendance a 
        JOIN students s ON a.student_id = s.id 
        ORDER BY a.date DESC, a.time DESC 
        LIMIT 10
    """, conn)
    
    if not recent.empty:
        st.dataframe(recent, use_container_width=True)
    else:
        st.info("📊 No records yet. Start by registering students!")

def register_student(conn):
    st.header("👨‍🎓 Register Student")
    
    with st.form("student_form"):
        col1, col2 = st.columns(2)
        
        with col1:
            name = st.text_input("👤 Student Name")
            reg_no = st.text_input("🆔 Registration Number")
        
        with col2:
            department = st.selectbox("🏢 Department", [
                "Computer Science", "Electronics", "Mechanical", 
                "Civil", "Electrical"
            ])
            parent_phone = st.text_input("📱 Parent Phone")
        
        if st.form_submit_button("✅ Register"):
            if name and reg_no and department and parent_phone:
                try:
                    barcode = str(uuid.uuid4())[:8].upper()
                    c = conn.cursor()
                    c.execute("INSERT INTO students (name, reg_no, department, parent_phone, barcode) VALUES (?, ?, ?, ?, ?)",
                             (name, reg_no, department, parent_phone, barcode))
                    conn.commit()
                    
                    st.markdown(f"""
                    <div class="success-alert">
                        <h3>✅ Registration Successful!</h3>
                        <p><strong>{name}</strong> registered successfully!</p>
                        <p><strong>Barcode:</strong> {barcode}</p>
                    </div>
                    """, unsafe_allow_html=True)
                    
                    # Show QR code
                    qr_code = generate_qr(barcode)
                    
                    col1, col2 = st.columns(2)
                    with col1:
                        st.subheader("📱 QR Code")
                        st.image(f"data:image/png;base64,{qr_code}", width=250)
                    
                    with col2:
                        st.subheader("📋 Details")
                        st.write(f"**Name:** {name}")
                        st.write(f"**Reg No:** {reg_no}")
                        st.write(f"**Department:** {department}")
                        st.write(f"**Barcode:** `{barcode}`")
                    
                    st.download_button(
                        "⬇️ Download QR Code",
                        base64.b64decode(qr_code),
                        f"{name}_QR.png"
                    )
                    
                except Exception as e:
                    st.error(f"❌ Error: {e}")
            else:
                st.error("❌ Please fill all fields!")

def qr_scanner(conn):
    st.header("📷 QR Scanner")
    
    st.info("📱 Use phone camera to scan QR code, then paste the text here:")
    
    scanned_code = st.text_input("🔍 QR Code Data:")
    
    if st.button("✅ Mark Attendance") and scanned_code:
        c = conn.cursor()
        student = c.execute("SELECT * FROM students WHERE barcode=?", (scanned_code,)).fetchone()
        
        if student:
            today = datetime.now().strftime('%Y-%m-%d')
            existing = c.execute("SELECT * FROM attendance WHERE student_id=? AND date=?", (student[0], today)).fetchone()
            
            if existing:
                st.warning(f"⚠️ {student[1]} already marked today!")
            else:
                current_time = datetime.now().strftime('%H:%M:%S')
                status = 'present' if datetime.now().hour <= 9 else 'late'
                
                c.execute("INSERT INTO attendance (student_id, date, time, status) VALUES (?, ?, ?, ?)",
                         (student[0], today, current_time, status))
                conn.commit()
                
                st.success(f"✅ Attendance marked for {student[1]}")
                st.balloons()
                
                col1, col2 = st.columns(2)
                with col1:
                    st.write(f"**Student:** {student[1]}")
                    st.write(f"**Status:** {status.upper()}")
                with col2:
                    st.write(f"**Time:** {current_time}")
                    st.write(f"**Date:** {today}")
        else:
            st.error("❌ Invalid QR code!")

def show_reports(conn):
    st.header("📈 Reports")
    
    all_data = pd.read_sql("""
        SELECT s.name, s.reg_no, a.date, a.time, a.status 
        FROM attendance a 
        JOIN students s ON a.student_id = s.id 
        ORDER BY a.date DESC
    """, conn)
    
    if not all_data.empty:
        st.subheader("📊 Statistics")
        
        col1, col2, col3 = st.columns(3)
        with col1:
            st.metric("📋 Total Records", len(all_data))
        with col2:
            present = len(all_data[all_data['status'] == 'present'])
            st.metric("🟢 Present", present)
        with col3:
            late = len(all_data[all_data['status'] == 'late'])
            st.metric("🟡 Late", late)
        
        st.subheader("📋 All Records")
        st.dataframe(all_data, use_container_width=True)
        
        csv = all_data.to_csv(index=False)
        st.download_button("📥 Download CSV", csv, "attendance_report.csv")
    else:
        st.info("📊 No data yet!")

if __name__ == "__main__":
    main()
