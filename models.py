"""
models.py - Complete Database Models for Acadify
Philippine College Grading System with Customizable Formulas
"""

from extensions import db
from flask_login import UserMixin
from datetime import datetime
from sqlalchemy import func
import json


class User(UserMixin, db.Model):
    """
    Base User Model - Authentication for all users
    """
    __tablename__ = 'user'
    
    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(120), unique=True, nullable=False, index=True)
    password = db.Column(db.String(255), nullable=False)
    role = db.Column(db.String(20), nullable=False)  # 'admin', 'teacher', 'student'
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Relationships
    student_profile = db.relationship('Student', backref='user', uselist=False, cascade='all, delete-orphan')
    teacher_profile = db.relationship('Teacher', backref='user', uselist=False, cascade='all, delete-orphan')
    
    def __repr__(self):
        return f'<User {self.email} ({self.role})>'
    
    def is_admin(self):
        return self.role == 'admin'
    
    def is_teacher(self):
        return self.role == 'teacher'
    
    def is_student(self):
        return self.role == 'student'


class Student(db.Model):
    """
    Student Profile - Extended student information
    """
    __tablename__ = 'student'
    
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False, unique=True)
    
    # Basic Information
    student_number = db.Column(db.String(50), unique=True, nullable=False, index=True)
    first_name = db.Column(db.String(100), nullable=False)
    last_name = db.Column(db.String(100), nullable=False)
    
    # Academic Information
    department = db.Column(db.String(100), nullable=False)  # "College of Engineering"
    program = db.Column(db.String(100), nullable=False)  # "BS Computer Science"
    year_level = db.Column(db.String(20), nullable=False)  # "1st Year", "2nd Year", etc.
    section = db.Column(db.String(20), nullable=True)  # "A", "B", "C" (null for irregular)
    
    # Timestamps
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Relationships
    enrollments = db.relationship('Enrollment', backref='student', lazy='dynamic', cascade='all, delete-orphan')
    grades = db.relationship('Grade', backref='student', lazy='dynamic', cascade='all, delete-orphan')
    
    def __repr__(self):
        return f'<Student {self.student_number} - {self.get_full_name()}>'
    
    def get_full_name(self):
        """Return full name"""
        return f"{self.first_name} {self.last_name}"
    
    def get_semester_gpa(self, school_year, semester, calculation_method='weighted'):
        """
        Calculate GPA for a specific semester
        
        Args:
            school_year: e.g., "2024-2025"
            semester: e.g., "1st Semester"
            calculation_method: 'weighted', 'simple', or 'major_only'
        
        Returns:
            float: GPA value
        """
        # Get all grades for this semester
        grades = self.grades.join(Grade.test).join(Test.class_).filter(
            Class.school_year == school_year,
            Class.semester == semester,
            Grade.final_grade.isnot(None)
        ).all()
        
        if not grades:
            return None
        
        if calculation_method == 'weighted':
            # Weighted by units
            total_points = sum(g.final_grade * g.test.class_.units for g in grades)
            total_units = sum(g.test.class_.units for g in grades)
            return round(total_points / total_units, 2) if total_units > 0 else None
        
        elif calculation_method == 'simple':
            # Simple average (no weighting)
            total = sum(g.final_grade for g in grades)
            return round(total / len(grades), 2)
        
        elif calculation_method == 'major_only':
            # Only major subjects (non-PE, non-elective)
            major_grades = [g for g in grades if g.test.class_.is_major_subject]
            if not major_grades:
                return None
            total = sum(g.final_grade for g in major_grades)
            return round(total / len(major_grades), 2)
        
        return None
    
    def get_cumulative_gpa(self, calculation_method='weighted'):
        """
        Calculate cumulative GPA (all semesters)
        """
        all_grades = self.grades.filter(Grade.final_grade.isnot(None)).all()
        
        if not all_grades:
            return None
        
        if calculation_method == 'weighted':
            total_points = sum(g.final_grade * g.test.class_.units for g in all_grades)
            total_units = sum(g.test.class_.units for g in all_grades)
            return round(total_points / total_units, 2) if total_units > 0 else None
        
        elif calculation_method == 'simple':
            total = sum(g.final_grade for g in all_grades)
            return round(total / len(all_grades), 2)
        
        elif calculation_method == 'major_only':
            major_grades = [g for g in all_grades if g.test.class_.is_major_subject]
            if not major_grades:
                return None
            total = sum(g.final_grade for g in major_grades)
            return round(total / len(major_grades), 2)
        
        return None


class Teacher(db.Model):
    """
    Teacher Profile - Extended teacher information
    """
    __tablename__ = 'teacher'
    
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False, unique=True)
    
    # Basic Information
    employee_number = db.Column(db.String(50), unique=True, nullable=False, index=True)
    first_name = db.Column(db.String(100), nullable=False)
    last_name = db.Column(db.String(100), nullable=False)
    
    # Professional Information
    department = db.Column(db.String(100), nullable=False)
    specialization = db.Column(db.String(200), nullable=True)
    
    # Timestamps
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Relationships
    classes = db.relationship('Class', backref='teacher', lazy='dynamic')
    
    def __repr__(self):
        return f'<Teacher {self.employee_number} - {self.get_full_name()}>'
    
    def get_full_name(self):
        """Return full name"""
        return f"{self.first_name} {self.last_name}"


class Subject(db.Model):
    """
    Subject/Course Master List
    Defines grading formula per subject (applies to all sections)
    """
    __tablename__ = 'subject'
    
    id = db.Column(db.Integer, primary_key=True)
    code = db.Column(db.String(20), unique=True, nullable=False, index=True)  # "MATH101"
    name = db.Column(db.String(200), nullable=False)  # "Mathematics 101"
    description = db.Column(db.Text, nullable=True)
    units = db.Column(db.Integer, nullable=False, default=3)
    is_major_subject = db.Column(db.Boolean, default=True)  # For GPA calculation filtering
    
    # Grading Formula (JSON format)
    # Example: [
    #   {"component": "Quizzes", "weight": 20, "max_points": 100},
    #   {"component": "Midterm", "weight": 30, "max_points": 100},
    #   {"component": "Final", "weight": 30, "max_points": 100},
    #   {"component": "Projects", "weight": 20, "max_points": 100}
    # ]
    grading_formula = db.Column(db.Text, nullable=True)  # JSON string
    
    # Grade Conversion Table (Percentage to PH Grade)
    # Standard: 97-100=1.0, 94-96=1.25, 91-93=1.5, etc.
    grade_conversion = db.Column(db.Text, nullable=True)  # JSON string
    
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Relationships
    classes = db.relationship('Class', backref='subject', lazy='dynamic')
    
    def __repr__(self):
        return f'<Subject {self.code} - {self.name}>'
    
    def get_grading_formula(self):
        """Parse and return grading formula as list"""
        if self.grading_formula:
            return json.loads(self.grading_formula)
        return []
    
    def set_grading_formula(self, formula_list):
        """Set grading formula from list"""
        self.grading_formula = json.dumps(formula_list)
    
    def get_grade_conversion(self):
        """Parse and return grade conversion table"""
        if self.grade_conversion:
            return json.loads(self.grade_conversion)
        # Default PH grading scale
        return {
            "97-100": 1.0, "94-96": 1.25, "91-93": 1.5, "88-90": 1.75,
            "85-87": 2.0, "82-84": 2.25, "79-81": 2.5, "76-78": 2.75,
            "75": 3.0, "65-74": 4.0, "0-64": 5.0
        }
    
    def convert_to_ph_grade(self, percentage):
        """
        Convert percentage score to Philippine grade
        
        Args:
            percentage: Score as percentage (0-100)
        
        Returns:
            float: PH grade (1.0 - 5.0)
        """
        conversion = self.get_grade_conversion()
        
        for range_str, grade in conversion.items():
            if '-' in range_str:
                min_score, max_score = map(int, range_str.split('-'))
                if min_score <= percentage <= max_score:
                    return grade
            else:
                if percentage == int(range_str):
                    return grade
        
        return 5.0  # Failed if no match


class Class(db.Model):
    """
    Class - Specific instance of a subject (with section, schedule, semester)
    """
    __tablename__ = 'class'
    
    id = db.Column(db.Integer, primary_key=True)
    subject_id = db.Column(db.Integer, db.ForeignKey('subject.id'), nullable=False)
    teacher_id = db.Column(db.Integer, db.ForeignKey('teacher.id'), nullable=False)
    
    # Class Details
    section = db.Column(db.String(20), nullable=True)  # "A", "B", or null for irregular
    schedule = db.Column(db.String(100), nullable=True)  # "MWF 9:00-10:30"
    room = db.Column(db.String(50), nullable=True)  # "Room 301"
    
    # Academic Period
    school_year = db.Column(db.String(20), nullable=False)  # "2024-2025"
    semester = db.Column(db.String(20), nullable=False)  # "1st Semester", "2nd Semester", "Summer"
    
    # Class Limits
    max_students = db.Column(db.Integer, default=50)
    
    # Program/Year for section-based enrollment
    department = db.Column(db.String(100), nullable=True)  # "College of Engineering"
    program = db.Column(db.String(100), nullable=True)  # "BS Computer Science"
    year_level = db.Column(db.String(20), nullable=True)  # "1st Year"
    
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Relationships
    enrollments = db.relationship('Enrollment', backref='class_', lazy='dynamic', cascade='all, delete-orphan')
    tests = db.relationship('Test', backref='class_', lazy='dynamic', cascade='all, delete-orphan')
    
    # Convenience property to access units from subject
    @property
    def units(self):
        return self.subject.units
    
    @property
    def is_major_subject(self):
        return self.subject.is_major_subject
    
    def __repr__(self):
        section_str = f" - Section {self.section}" if self.section else ""
        return f'<Class {self.subject.code}{section_str} ({self.school_year} {self.semester})>'
    
    def get_enrolled_count(self):
        """Get number of enrolled students"""
        return self.enrollments.filter_by(status='enrolled').count()
    
    def is_full(self):
        """Check if class is at capacity"""
        return self.get_enrolled_count() >= self.max_students


class Enrollment(db.Model):
    """
    Enrollment - Links students to classes (many-to-many relationship)
    """
    __tablename__ = 'enrollment'
    
    id = db.Column(db.Integer, primary_key=True)
    student_id = db.Column(db.Integer, db.ForeignKey('student.id'), nullable=False, index=True)
    class_id = db.Column(db.Integer, db.ForeignKey('class.id'), nullable=False, index=True)
    
    enrollment_date = db.Column(db.DateTime, default=datetime.utcnow)
    status = db.Column(db.String(20), default='enrolled')  # 'enrolled', 'dropped', 'completed'
    
    # Final grade for this class (computed at end of semester)
    final_grade = db.Column(db.Float, nullable=True)
    
    def __repr__(self):
        return f'<Enrollment Student:{self.student_id} Class:{self.class_id} ({self.status})>'


class Test(db.Model):
    """
    Test/Assignment - Created by teachers (placeholder for OCR integration)
    """
    __tablename__ = 'test'
    
    id = db.Column(db.Integer, primary_key=True)
    class_id = db.Column(db.Integer, db.ForeignKey('class.id'), nullable=False)
    
    title = db.Column(db.String(200), nullable=False)
    description = db.Column(db.Text, nullable=True)
    test_date = db.Column(db.Date, nullable=True)
    
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Relationships
    grades = db.relationship('Grade', backref='test', lazy='dynamic', cascade='all, delete-orphan')
    
    def __repr__(self):
        return f'<Test {self.title} - Class:{self.class_id}>'


class Grade(db.Model):
    """
    Grade - Student scores on tests/assignments
    Stores individual component scores and final calculated grade
    """
    __tablename__ = 'grade'
    
    id = db.Column(db.Integer, primary_key=True)
    test_id = db.Column(db.Integer, db.ForeignKey('test.id'), nullable=False)
    student_id = db.Column(db.Integer, db.ForeignKey('student.id'), nullable=False, index=True)
    
    # Component Scores (JSON format matching subject's grading formula)
    # Example: {
    #   "Quizzes": 85,
    #   "Midterm": 90,
    #   "Final": 88,
    #   "Projects": 92
    # }
    component_scores = db.Column(db.Text, nullable=True)  # JSON string
    
    # Calculated grade (from formula)
    calculated_percentage = db.Column(db.Float, nullable=True)  # Raw percentage (0-100)
    calculated_grade = db.Column(db.Float, nullable=True)  # Converted PH grade (1.0-5.0)
    
    # Manual override
    is_overridden = db.Column(db.Boolean, default=False)
    override_grade = db.Column(db.Float, nullable=True)  # Manual PH grade
    override_reason = db.Column(db.Text, nullable=True)
    
    # Final grade (either calculated or overridden)
    final_grade = db.Column(db.Float, nullable=True)
    
    # Metadata
    graded_by = db.Column(db.Integer, db.ForeignKey('teacher.id'), nullable=True)
    graded_at = db.Column(db.DateTime, nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    def __repr__(self):
        return f'<Grade Student:{self.student_id} Test:{self.test_id} Grade:{self.final_grade}>'
    
    def get_component_scores(self):
        """Parse and return component scores as dict"""
        if self.component_scores:
            return json.loads(self.component_scores)
        return {}
    
    def set_component_scores(self, scores_dict):
        """Set component scores from dict"""
        self.component_scores = json.dumps(scores_dict)
    
    def calculate_grade(self, subject):
        """
        Calculate grade based on subject's formula
        
        Args:
            subject: Subject instance with grading formula
        """
        scores = self.get_component_scores()
        formula = subject.get_grading_formula()
        
        if not scores or not formula:
            return
        
        # Calculate weighted percentage
        total_weighted = 0
        total_weight = 0
        
        for component in formula:
            comp_name = component['component']
            weight = component['weight']
            max_points = component['max_points']
            
            if comp_name in scores:
                score = scores[comp_name]
                # Convert to percentage and apply weight
                percentage = (score / max_points) * 100
                total_weighted += (percentage * weight / 100)
                total_weight += weight
        
        if total_weight > 0:
            self.calculated_percentage = round(total_weighted, 2)
            self.calculated_grade = subject.convert_to_ph_grade(self.calculated_percentage)
            
            # Set final grade (use override if exists, otherwise calculated)
            if self.is_overridden and self.override_grade:
                self.final_grade = self.override_grade
            else:
                self.final_grade = self.calculated_grade
    
    def set_override(self, grade, reason, teacher_id):
        """
        Manually override the calculated grade
        
        Args:
            grade: Override PH grade (1.0-5.0)
            reason: Reason for override
            teacher_id: Teacher who made the override
        """
        self.is_overridden = True
        self.override_grade = grade
        self.override_reason = reason
        self.final_grade = grade
        self.graded_by = teacher_id
        self.graded_at = datetime.utcnow()
    
    def remove_override(self):
        """Remove manual override and use calculated grade"""
        self.is_overridden = False
        self.override_grade = None
        self.override_reason = None
        self.final_grade = self.calculated_grade