from flask import Flask, render_template, request, redirect, url_for, flash, send_file
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager, UserMixin, login_user, logout_user, login_required, current_user
import pandas as pd
from datetime import date
import pymysql

# Configure PyMySQL to work with SQLAlchemy
pymysql.install_as_MySQLdb()

app = Flask(__name__)
app.config['SECRET_KEY'] = 'secret_key_for_project'

# XAMPP CONNECTION STRING: mysql+pymysql://root:@localhost/database_name
# Updated for Port 3307
app.config['SQLALCHEMY_DATABASE_URI'] = 'mysql+pymysql://root:@127.0.0.1:3307/student_dbms'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db = SQLAlchemy(app)
login_manager = LoginManager(app)
login_manager.login_view = 'login'

# --- DATABASE MODELS ---

class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(50), unique=True, nullable=False)
    password = db.Column(db.String(100), nullable=False)

class Student(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    roll_no = db.Column(db.String(20), unique=True, nullable=False)
    marks = db.Column(db.Float, default=0)
    course = db.Column(db.String(50))
    attendance = db.relationship('Attendance', backref='student', lazy=True)

class Attendance(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    student_id = db.Column(db.Integer, db.ForeignKey('student.id'), nullable=False)
    date = db.Column(db.Date, default=date.today)
    status = db.Column(db.String(10)) # Present / Absent

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

# --- ROUTES ---

@app.route('/')
def login():
    return render_template('login.html')

@app.route('/login', methods=['POST'])
def login_post():
    user = User.query.filter_by(username=request.form.get('username'), 
                                password=request.form.get('password')).first()
    if user:
        login_user(user)
        return redirect(url_for('dashboard'))
    flash('Invalid Login Credentials!')
    return redirect(url_for('login'))

@app.route('/dashboard')
@login_required
def dashboard():
    total_students = Student.query.count()
    avg_marks = db.session.query(db.func.avg(Student.marks)).scalar() or 0
    return render_template('dashboard.html', total=total_students, avg=round(float(avg_marks), 2))

@app.route('/students')
@login_required
def students():
    search = request.args.get('search')
    if search:
        data = Student.query.filter((Student.name.like(f"%{search}%")) | (Student.roll_no == search)).all()
    else:
        data = Student.query.all()
    return render_template('students.html', students=data)

@app.route('/add_student', methods=['GET', 'POST'])
@login_required
def add_student():
    if request.method == 'POST':
        new_s = Student(name=request.form['name'], roll_no=request.form['roll_no'], 
                        marks=float(request.form['marks']), course=request.form['course'])
        db.session.add(new_s)
        db.session.commit()
        return redirect(url_for('students'))
    return render_template('add_student.html')

@app.route('/attendance', methods=['GET', 'POST'])
@login_required
def mark_attendance():
    st_list = Student.query.all()
    today = date.today()
    if request.method == 'POST':
        for s in st_list:
            status = request.form.get(f"status_{s.id}")
            existing = Attendance.query.filter_by(student_id=s.id, date=today).first()
            if existing: existing.status = status
            else: db.session.add(Attendance(student_id=s.id, status=status, date=today))
        db.session.commit()
        flash('Attendance Updated!')
    return render_template('attendance.html', students=st_list, today=today)

@app.route('/export')
@login_required
def export_excel():
    st = Student.query.all()
    df = pd.DataFrame([{"Roll": s.roll_no, "Name": s.name, "Marks": s.marks} for s in st])
    df.to_excel("Student_Report.xlsx", index=False)
    return send_file("Student_Report.xlsx", as_attachment=True)

@app.route('/logout')
def logout():
    logout_user()
    return redirect(url_for('login'))

if __name__ == '__main__':
    with app.app_context():
        db.create_all() # Creates tables in XAMPP
        if not User.query.filter_by(username='admin').first():
            db.session.add(User(username='admin', password='123'))
            db.session.commit()
    app.run(debug=True)