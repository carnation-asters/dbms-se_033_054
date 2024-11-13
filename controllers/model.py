from controllers.database import db
from datetime import datetime, date
from sqlalchemy import event, DDL

# Base User model, which both Customer and ServiceProfessional will inherit
class User(db.Model):
    __tablename__ = 'users'
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(50), unique=True, nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password = db.Column(db.String(100), nullable=False)
    role = db.Column(db.String(15), nullable=False)
    is_active = db.Column(db.Boolean, default=True)

class Admin(User):
    __tablename__ = 'admin'
    id = db.Column(db.Integer, db.ForeignKey('users.id'), primary_key=True)

# College model
class College(db.Model):
    __tablename__ = 'colleges'
    id = db.Column(db.Integer, db.ForeignKey('users.id'), primary_key=True)
    name = db.Column(db.String(50), nullable=False)
    experience = db.Column(db.Integer, nullable=False)
    description = db.Column(db.Text)

# Student model
class Student(db.Model):
    __tablename__ = 'students'
    id = db.Column(db.Integer, db.ForeignKey('users.id'), primary_key=True)
    name = db.Column(db.String(50), nullable=False)
    address = db.Column(db.String(200), nullable=True)
    doc_url = db.Column(db.String(200), nullable=True)
    eligibility_status = db.Column(db.Boolean, default=False)
    rank = db.Column(db.Integer, nullable=False)
    round_furthering = db.Column(db.Boolean, default=True)
    
    # Relationship with SeatPreference
    seat_preferences = db.relationship('SeatPreference', back_populates='student')

# Major model
class Major(db.Model):
    __tablename__ = 'majors'
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    college_id = db.Column(db.Integer, db.ForeignKey('colleges.id'), nullable=False)
    name = db.Column(db.String(50), nullable=False)
    seat_count = db.Column(db.Integer, nullable=False, default=0)
    alloted_seat_count = db.Column(db.Integer, nullable=False, default=0)

    college = db.relationship('College', backref=db.backref('majors', cascade='all, delete-orphan'))

# Student seat preference model
class SeatPreference(db.Model):
    __tablename__ = 'seat_preferences'
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    round_id = db.Column(db.Integer, db.ForeignKey('rounds.round_id'), nullable=False)
    student_id = db.Column(db.Integer, db.ForeignKey('students.id'), nullable=False)
    college_id = db.Column(db.Integer, db.ForeignKey('colleges.id'), nullable=False)
    major_id = db.Column(db.Integer, db.ForeignKey('majors.id'), nullable=False)
    preference_order = db.Column(db.Integer, nullable=False)

    # Define relationships
    student = db.relationship('Student', back_populates='seat_preferences')
    college = db.relationship('College', backref=db.backref('seat_preferences', lazy=True))
    major = db.relationship('Major', backref=db.backref('seat_preferences', lazy=True))
    round = db.relationship('Round', backref=db.backref('seat_preferences', lazy=True))

class Round(db.Model):
    __tablename__ = 'rounds'
    
    round_id = db.Column(db.Integer, primary_key=True)
    start_date = db.Column(db.Date, nullable=False)
    end_date = db.Column(db.Date, nullable=True)
    is_active = db.Column(db.Boolean, nullable=False, default=False)

    # Relationship to link Round with StudentAllotment
    student_allotments = db.relationship('StudentAllotment', back_populates='round')

class StudentAllotment(db.Model):
    __tablename__ = 'student_allotments'
    
    id = db.Column(db.Integer, primary_key=True)
    student_id = db.Column(db.Integer, db.ForeignKey('students.id'), nullable=False)
    pref_id = db.Column(db.Integer, db.ForeignKey('seat_preferences.id'), nullable=False)
    round_id = db.Column(db.Integer, db.ForeignKey('rounds.round_id'), nullable=False)
    status = db.Column(db.String(10), nullable=False)   # "active" or "no"
    choice = db.Column(db.String(100))

    # Relationships
    round = db.relationship('Round', back_populates='student_allotments')
    student = db.relationship('Student', backref='student_allotments')
    preference = db.relationship('SeatPreference', backref='student_allotments')
