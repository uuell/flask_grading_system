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
ADMIN_PASSWORD = "AcadifyStrongPassword"  # Change this before running!


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

    id                     = Column(Integer, primary_key=True)
    # Subject info — can be linked to Subject table OR entered manually
    subject_id             = Column(Integer, ForeignKey('subject.id'), nullable=True)
    subject_name           = Column(String(200), nullable=True)
    subject_code           = Column(String(20),  nullable=True)
    units                  = Column(Integer,      nullable=True)
    # Teacher & class details
    teacher_id             = Column(Integer, ForeignKey('teacher.id'), nullable=False)
    section                = Column(String(20),  nullable=True)
    schedule               = Column(String(100), nullable=True)
    room                   = Column(String(50),  nullable=True)
    # Academic period
    school_year            = Column(String(20), nullable=False)
    semester               = Column(String(20), nullable=False)
    # Class limits
    max_students           = Column(Integer, default=40)
    # Grading
    grading_formula        = Column(Text, nullable=True)
    grade_conversion_table = Column(Text, nullable=True)
    # Program / year
    department             = Column(String(100), nullable=True)
    program                = Column(String(100), nullable=True)
    year_level             = Column(String(20),  nullable=True)

    created_at = Column(DateTime, default=datetime.utcnow)

    subject     = relationship('Subject',    back_populates='classes')
    teacher     = relationship('Teacher',    back_populates='classes')
    enrollments = relationship('Enrollment', back_populates='class_', cascade='all, delete-orphan')
    tests       = relationship('Test',       back_populates='class_', cascade='all, delete-orphan')


class Enrollment(Base):
    __tablename__ = 'enrollment'

    id              = Column(Integer, primary_key=True)
    student_id      = Column(Integer, ForeignKey('student.id'), nullable=False, index=True)
    class_id        = Column(Integer, ForeignKey('class.id'),   nullable=False, index=True)
    enrollment_date = Column(DateTime, default=datetime.utcnow)
    status          = Column(String(20), default='enrolled')   # enrolled | dropped | completed
    final_grade     = Column(Float, nullable=True)

    student = relationship('Student', back_populates='enrollments')
    class_  = relationship('Class',   back_populates='enrollments')


class Test(Base):
    """
    A single gradable activity in a class.

    Method 2 (Activity-Based) fields:
        term_tag      → which grading period  ("Prelims", "Midterms", "Finals")
        component_tag → which formula bucket  ("Quizzes", "Exams", "Projects")

    Old (untagged) tests have term_tag = NULL and are handled by the
    legacy component_scores path in Grade.calculate_grade().
    """
    __tablename__ = 'test'

    id            = Column(Integer, primary_key=True)
    class_id      = Column(Integer, ForeignKey('class.id'), nullable=False)
    title         = Column(String(200), nullable=False)
    description   = Column(Text, nullable=True)
    test_date     = Column(Date, nullable=True)
    created_at    = Column(DateTime, default=datetime.utcnow)

    # Method 2 tags (nullable → backward-compatible with old untagged tests)
    term_tag      = Column(String(50),  nullable=True, index=True)
    component_tag = Column(String(100), nullable=True)

    class_  = relationship('Class', back_populates='tests')
    grades  = relationship('Grade', back_populates='test', cascade='all, delete-orphan')


class Grade(Base):
    """
    Student score on a single Test.

    Supports both the old component_scores JSON path (Method 1 / untagged tests)
    and the new raw_score / max_score path used by Method 2 tagged tests.
    """
    __tablename__ = 'grade'

    id                    = Column(Integer, primary_key=True)
    test_id               = Column(Integer, ForeignKey('test.id'),    nullable=False)
    student_id            = Column(Integer, ForeignKey('student.id'), nullable=False, index=True)

    # Method 1 (legacy) — per-component JSON scores
    component_scores      = Column(Text,  nullable=True)

    # Method 2 — raw numeric score for a single tagged test activity
    raw_score             = Column(Float, nullable=True)
    max_score             = Column(Float, nullable=True)

    # Calculated results
    calculated_percentage = Column(Float, nullable=True)   # 0–100
    calculated_grade      = Column(Float, nullable=True)   # PH grade 1.0–5.0

    # Manual override
    is_overridden         = Column(Boolean, default=False)
    override_grade        = Column(Float, nullable=True)
    override_reason       = Column(Text,  nullable=True)

    # Final grade (calculated or overridden)
    final_grade           = Column(Float, nullable=True)

    # Metadata
    graded_by             = Column(Integer, ForeignKey('teacher.id'), nullable=True)
    graded_at             = Column(DateTime, nullable=True)
    created_at            = Column(DateTime, default=datetime.utcnow)
    updated_at            = Column(DateTime, default=datetime.utcnow)

    test    = relationship('Test',    back_populates='grades')
    student = relationship('Student', back_populates='grades')


class TestPaperImage(Base):
    """
    Stores uploaded test paper images from the AI grading pipeline.

    Status lifecycle:
        pending   → uploaded, pipeline running / just finished, not yet assigned
        uncertain → OCR name confidence is LOW (<85%); teacher must confirm
        assigned  → teacher confirmed which student owns this paper
        error     → pipeline crashed on this image; teacher can retry/reassign
    """
    __tablename__ = 'test_paper_image'

    id = Column(Integer, primary_key=True)

    # Foreign keys
    test_id    = Column(Integer, ForeignKey('test.id'),    nullable=False, index=True)
    student_id = Column(Integer, ForeignKey('student.id'), nullable=True,  index=True)   # confirmed
    uploaded_by = Column(Integer, ForeignKey('teacher.id'), nullable=False)

    # File storage
    image_path        = Column(String(500), nullable=False)
    original_filename = Column(String(255), nullable=False)

    # Pipeline / OCR output
    ocr_name     = Column(String(300), nullable=True)
    ocr_score    = Column(String(50),  nullable=True)   # e.g. "23/100"
    ocr_label    = Column(String(500), nullable=True)
    ocr_raw_json = Column(Text,        nullable=True)   # full JSON blob from pipeline

    # Matching / assignment
    match_confidence     = Column(Float,   nullable=True)          # 0–100 fuzzy score
    suggested_student_id = Column(Integer, ForeignKey('student.id'), nullable=True)  # pre-confirmed guess

    # Status
    status        = Column(String(20), nullable=False, default='pending', index=True)
    error_message = Column(Text, nullable=True)

    # Timestamps
    uploaded_at  = Column(DateTime, default=datetime.utcnow)
    assigned_at  = Column(DateTime, nullable=True)
    processed_at = Column(DateTime, nullable=True)

    # Relationships
    test              = relationship('Test',    foreign_keys=[test_id])
    student           = relationship('Student', foreign_keys=[student_id])
    suggested_student = relationship('Student', foreign_keys=[suggested_student_id])
    uploader          = relationship('Teacher', foreign_keys=[uploaded_by])


class SystemSettings(Base):
    __tablename__ = 'system_settings'

    id            = Column(Integer, primary_key=True)
    setting_key   = Column(String(100), unique=True, nullable=False, index=True)
    setting_value = Column(String(200), nullable=False)
    updated_at    = Column(DateTime, default=datetime.utcnow)
    updated_by    = Column(String(100), nullable=True)


# ============================================================
# MAIN - Create / migrate tables and seed admin
# ============================================================

def main():
    print("🔌 Connecting to database...")
    engine = create_engine(DATABASE_URL, echo=False)

    print("📦 Creating / updating all tables...")
    Base.metadata.create_all(engine)   # create_all is safe to re-run — it skips existing tables
    print("✅ All tables created or already exist!")

    # ── Add new columns to existing tables if they are missing ──────────────
    # SQLAlchemy's create_all() won't ALTER existing tables, so we do it manually.
    migrations = [
        # Test table — Method 2 tags
        ("ALTER TABLE test ADD COLUMN IF NOT EXISTS term_tag      VARCHAR(50)",),
        ("ALTER TABLE test ADD COLUMN IF NOT EXISTS component_tag VARCHAR(100)",),

        # Grade table — raw score fields for Method 2
        ("ALTER TABLE grade ADD COLUMN IF NOT EXISTS raw_score  FLOAT",),
        ("ALTER TABLE grade ADD COLUMN IF NOT EXISTS max_score  FLOAT",),
        ("ALTER TABLE grade ADD COLUMN IF NOT EXISTS updated_at TIMESTAMP",),

        # Class table — new optional fields
        ("ALTER TABLE class ADD COLUMN IF NOT EXISTS subject_name           VARCHAR(200)",),
        ("ALTER TABLE class ADD COLUMN IF NOT EXISTS subject_code           VARCHAR(20)",),
        ("ALTER TABLE class ADD COLUMN IF NOT EXISTS units                  INTEGER",),
        ("ALTER TABLE class ADD COLUMN IF NOT EXISTS grade_conversion_table TEXT",),
        ("ALTER TABLE class ADD COLUMN IF NOT EXISTS department             VARCHAR(100)",),
        ("ALTER TABLE class ADD COLUMN IF NOT EXISTS program                VARCHAR(100)",),
        ("ALTER TABLE class ADD COLUMN IF NOT EXISTS year_level             VARCHAR(20)",),

        # Make class.subject_id nullable (was NOT NULL in the old schema)
        # PostgreSQL: DROP NOT NULL is safe if column already is nullable
        ("ALTER TABLE class ALTER COLUMN subject_id DROP NOT NULL",),
    ]

    with engine.connect() as conn:
        for (sql,) in migrations:
            try:
                conn.execute(text(sql))
                conn.commit()
                print(f"  ✔ {sql.strip()[:80]}")
            except Exception as e:
                conn.rollback()
                # Column may already exist with a different error — just warn
                print(f"  ⚠  Skipped (probably already applied): {e!s:.120}")

    print("✅ Schema migrations complete!")

    # ── Seed admin user ─────────────────────────────────────────────────────
    Session = sessionmaker(bind=engine)
    session = Session()

    try:
        existing = session.query(User).filter_by(email=ADMIN_EMAIL).first()
        if existing:
            print(f"\n⚠️  Admin user '{ADMIN_EMAIL}' already exists. Skipping.")
        else:
            print("\n👤 Creating admin user...")
            hashed_pw = hashpw(ADMIN_PASSWORD.encode('utf-8'), gensalt()).decode('utf-8')

            admin = User(
                email=ADMIN_EMAIL,
                password=hashed_pw,
                role='admin',
                created_at=datetime.utcnow()
            )
            session.add(admin)
            session.commit()
            print("✅ Admin user created!")
            print(f"   Email:    {ADMIN_EMAIL}")
            print(f"   Password: {ADMIN_PASSWORD}")
            print(f"   Role:     admin")

    except Exception as e:
        session.rollback()
        print(f"❌ Error creating admin: {e}")
        raise
    finally:
        session.close()

    print("\n🎉 Done! Your Render database is ready.")


if __name__ == '__main__':
    main()