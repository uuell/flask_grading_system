"""
seed_db.py - Standalone Database Seeder for Acadify
Run this locally to create all tables and seed an admin user in Render's PostgreSQL.

Usage:
    python seed_db.py
"""

import os
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker, DeclarativeBase
from sqlalchemy import (
    Column, Integer, String, Boolean, Float, Text, DateTime, Date,
    ForeignKey, UniqueConstraint
)
from sqlalchemy.orm import relationship
from datetime import datetime
from bcrypt import hashpw, gensalt
import json


# ============================================================
# CONFIGURE YOUR RENDER EXTERNAL DATABASE URL HERE
# ============================================================
DATABASE_URL = "postgresql://acadify_db_user:sVaRBptc0Vob3Mcrz0QiYQ1EGVAqInaB@dpg-d6dvkkdm5p6s73fh4o50-a.singapore-postgres.render.com/acadify_db"
# Example:
# DATABASE_URL = "postgresql://acadify_user:abc123@dpg-xxxx.singapore-postgres.render.com/acadify"

# Fix Render's postgres:// prefix if needed
if DATABASE_URL.startswith("postgres://"):
    DATABASE_URL = DATABASE_URL.replace("postgres://", "postgresql://", 1)


# ============================================================
# ADMIN USER CREDENTIALS
# ============================================================
ADMIN_EMAIL    = "admin@acadify.com"
ADMIN_PASSWORD = "AcadifyStrongPassword"  # Change if you want


# ============================================================
# DATABASE MODELS (mirrors models.py exactly)
# ============================================================

class Base(DeclarativeBase):
    pass


class User(Base):
    __tablename__ = 'user'

    id         = Column(Integer, primary_key=True)
    email      = Column(String(120), unique=True, nullable=False, index=True)
    password   = Column(String(255), nullable=False)
    role       = Column(String(20), nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)

    student_profile = relationship('Student', back_populates='user', uselist=False, cascade='all, delete-orphan')
    teacher_profile = relationship('Teacher', back_populates='user', uselist=False, cascade='all, delete-orphan')


class Student(Base):
    __tablename__ = 'student'

    id             = Column(Integer, primary_key=True)
    user_id        = Column(Integer, ForeignKey('user.id'), nullable=False, unique=True)
    student_number = Column(String(50), unique=True, nullable=False, index=True)
    first_name     = Column(String(100), nullable=False)
    last_name      = Column(String(100), nullable=False)
    department     = Column(String(100), nullable=False)
    program        = Column(String(100), nullable=False)
    year_level     = Column(String(20), nullable=False)
    section        = Column(String(20), nullable=True)
    created_at     = Column(DateTime, default=datetime.utcnow)

    user        = relationship('User', back_populates='student_profile')
    enrollments = relationship('Enrollment', back_populates='student', cascade='all, delete-orphan')
    grades      = relationship('Grade', back_populates='student', cascade='all, delete-orphan')


class Teacher(Base):
    __tablename__ = 'teacher'

    id              = Column(Integer, primary_key=True)
    user_id         = Column(Integer, ForeignKey('user.id'), nullable=False, unique=True)
    employee_number = Column(String(50), unique=True, nullable=False, index=True)
    first_name      = Column(String(100), nullable=False)
    last_name       = Column(String(100), nullable=False)
    department      = Column(String(100), nullable=False)
    specialization  = Column(String(200), nullable=True)
    created_at      = Column(DateTime, default=datetime.utcnow)

    user    = relationship('User', back_populates='teacher_profile')
    classes = relationship('Class', back_populates='teacher')


class Subject(Base):
    __tablename__ = 'subject'

    id               = Column(Integer, primary_key=True)
    code             = Column(String(20), unique=True, nullable=False, index=True)
    name             = Column(String(200), nullable=False)
    description      = Column(Text, nullable=True)
    units            = Column(Integer, nullable=False, default=3)
    is_major_subject = Column(Boolean, default=True)
    grading_formula  = Column(Text, nullable=True)
    grade_conversion = Column(Text, nullable=True)
    created_at       = Column(DateTime, default=datetime.utcnow)

    classes = relationship('Class', back_populates='subject')


class Class(Base):
    __tablename__ = 'class'

    id                   = Column(Integer, primary_key=True)
    subject_id           = Column(Integer, ForeignKey('subject.id'), nullable=True)
    subject_name         = Column(String(200), nullable=True)
    subject_code         = Column(String(20), nullable=True)
    units                = Column(Integer, nullable=True)
    teacher_id           = Column(Integer, ForeignKey('teacher.id'), nullable=False)
    section              = Column(String(20), nullable=True)
    schedule             = Column(String(100), nullable=True)
    room                 = Column(String(50), nullable=True)
    school_year          = Column(String(20), nullable=False)
    semester             = Column(String(20), nullable=False)
    max_students         = Column(Integer, default=40)
    grading_formula      = Column(Text, nullable=True)
    grade_conversion_table = Column(Text, nullable=True)
    department           = Column(String(100), nullable=True)
    program              = Column(String(100), nullable=True)
    year_level           = Column(String(20), nullable=True)
    created_at           = Column(DateTime, default=datetime.utcnow)

    subject     = relationship('Subject', back_populates='classes')
    teacher     = relationship('Teacher', back_populates='classes')
    enrollments = relationship('Enrollment', back_populates='class_', cascade='all, delete-orphan')
    tests       = relationship('Test', back_populates='class_', cascade='all, delete-orphan')


class Enrollment(Base):
    __tablename__ = 'enrollment'

    id              = Column(Integer, primary_key=True)
    student_id      = Column(Integer, ForeignKey('student.id'), nullable=False, index=True)
    class_id        = Column(Integer, ForeignKey('class.id'), nullable=False, index=True)
    enrollment_date = Column(DateTime, default=datetime.utcnow)
    status          = Column(String(20), default='enrolled')
    final_grade     = Column(Float, nullable=True)

    student = relationship('Student', back_populates='enrollments')
    class_  = relationship('Class', back_populates='enrollments')


class Test(Base):
    __tablename__ = 'test'

    id          = Column(Integer, primary_key=True)
    class_id    = Column(Integer, ForeignKey('class.id'), nullable=False)
    title       = Column(String(200), nullable=False)
    description = Column(Text, nullable=True)
    test_date   = Column(Date, nullable=True)
    created_at  = Column(DateTime, default=datetime.utcnow)

    class_  = relationship('Class', back_populates='tests')
    grades  = relationship('Grade', back_populates='test', cascade='all, delete-orphan')


class Grade(Base):
    __tablename__ = 'grade'

    id                   = Column(Integer, primary_key=True)
    test_id              = Column(Integer, ForeignKey('test.id'), nullable=False)
    student_id           = Column(Integer, ForeignKey('student.id'), nullable=False, index=True)
    component_scores     = Column(Text, nullable=True)
    calculated_percentage = Column(Float, nullable=True)
    calculated_grade     = Column(Float, nullable=True)
    is_overridden        = Column(Boolean, default=False)
    override_grade       = Column(Float, nullable=True)
    override_reason      = Column(Text, nullable=True)
    final_grade          = Column(Float, nullable=True)
    graded_by            = Column(Integer, ForeignKey('teacher.id'), nullable=True)
    graded_at            = Column(DateTime, nullable=True)
    created_at           = Column(DateTime, default=datetime.utcnow)
    updated_at           = Column(DateTime, default=datetime.utcnow)

    test    = relationship('Test', back_populates='grades')
    student = relationship('Student', back_populates='grades')


class SystemSettings(Base):
    __tablename__ = 'system_settings'

    id            = Column(Integer, primary_key=True)
    setting_key   = Column(String(100), unique=True, nullable=False, index=True)
    setting_value = Column(String(200), nullable=False)
    updated_at    = Column(DateTime, default=datetime.utcnow)
    updated_by    = Column(String(100), nullable=True)


# ============================================================
# MAIN - Create tables and seed admin
# ============================================================

def main():
    print("🔌 Connecting to database...")
    engine = create_engine(DATABASE_URL, echo=False)

    print("📦 Creating all tables...")
    Base.metadata.create_all(engine)
    print("✅ All tables created!")

    Session = sessionmaker(bind=engine)
    session = Session()

    try:
        # Check if admin already exists
        existing = session.query(User).filter_by(email=ADMIN_EMAIL).first()
        if existing:
            print(f"⚠️  Admin user '{ADMIN_EMAIL}' already exists. Skipping.")
        else:
            print("👤 Creating admin user...")
            hashed_pw = hashpw(ADMIN_PASSWORD.encode('utf-8'), gensalt()).decode('utf-8')

            admin = User(
                email=ADMIN_EMAIL,
                password=hashed_pw,
                role='admin',
                created_at=datetime.utcnow()
            )
            session.add(admin)
            session.commit()
            print(f"✅ Admin user created!")
            print(f"   Email:    {ADMIN_EMAIL}")
            print(f"   Password: {ADMIN_PASSWORD}")
            print(f"   Role:     admin")

    except Exception as e:
        session.rollback()
        print(f"❌ Error: {e}")
        raise
    finally:
        session.close()

    print("\n🎉 Done! Your Render database is ready.")


if __name__ == '__main__':
    main()