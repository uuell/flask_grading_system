"""
models.py - Complete Database Models for Acadify
Philippine College Grading System with Customizable Formulas
"""

from extensions import db
from flask_login import UserMixin
from datetime import datetime
from sqlalchemy import func
import json
import os


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
    
    def _get_per_class_ph_grade(self, enrollment):
        """
        Return the Philippine grade (1.0-5.0) for one enrollment.
 
        NEW system (tests have term_tag):
            enrollment.final_grade is set by _update_enrollment_average()
            in teacher routes. It is already a PH grade. Use it directly.
 
        OLD system (tests have no term_tag):
            enrollment.final_grade was never computed (always NULL).
            Fall back to averaging Grade.final_grade values per test —
            those were stored directly as PH grades in the old system.
 
        Returns float or None (None = no grade yet, skip this class for GPA).
        """
        cls = enrollment.class_
 
        # Discriminator: any tagged test means this is a new-system class
        has_tagged = (
            Test.query
            .filter_by(class_id=cls.id)
            .filter(Test.term_tag.isnot(None))
            .first()
        ) is not None
 
        if has_tagged:
            # New system — enrollment.final_grade is the PH grade
            return enrollment.final_grade  # None if not yet computed
 
        else:
            # Old system — average per-test Grade.final_grade values
            old_grades = (
                Grade.query
                .join(Test)
                .filter(
                    Test.class_id        == cls.id,
                    Grade.student_id     == self.id,
                    Grade.final_grade.isnot(None)
                )
                .all()
            )
 
            if not old_grades:
                return None
 
            return round(
                sum(g.final_grade for g in old_grades) / len(old_grades), 2
            )
 
    def get_semester_gpa(self, school_year, semester, calculation_method='weighted'):
        """
        Calculate GPA for a specific semester.
 
        Reads one PH grade per enrolled class (via _get_per_class_ph_grade),
        never raw test scores. Handles both old and new grading systems.
        """
        enrollments = (
            Enrollment.query
            .filter_by(student_id=self.id)
            .join(Class)
            .filter(
                Class.school_year == school_year,
                Class.semester    == semester,
            )
            .all()
        )
 
        if not enrollments:
            return None
 
        # Build (ph_grade, units, is_major) for each class that has a grade
        graded = []
        for e in enrollments:
            ph = self._get_per_class_ph_grade(e)
            if ph is not None:
                graded.append((ph, e.class_.effective_units, e.class_.is_major_subject))
 
        if not graded:
            return None
 
        if calculation_method == 'weighted':
            total_points = sum(ph * units for ph, units, _ in graded)
            total_units  = sum(units      for _,  units, _ in graded)
            return round(total_points / total_units, 2) if total_units > 0 else None
 
        elif calculation_method == 'simple':
            return round(sum(ph for ph, _, _ in graded) / len(graded), 2)
 
        elif calculation_method == 'major_only':
            major = [(ph, units) for ph, units, is_major in graded if is_major]
            if not major:
                return None
            return round(sum(ph for ph, _ in major) / len(major), 2)
 
        return None
 
    def get_cumulative_gpa(self, calculation_method='weighted'):
        """
        Calculate cumulative GPA across all semesters.
 
        Reads one PH grade per enrolled class (via _get_per_class_ph_grade),
        never raw test scores. Handles both old and new grading systems.
        """
        enrollments = Enrollment.query.filter_by(student_id=self.id).all()
 
        if not enrollments:
            return None
 
        # Build (ph_grade, units, is_major) for each class that has a grade
        graded = []
        for e in enrollments:
            ph = self._get_per_class_ph_grade(e)
            if ph is not None:
                graded.append((ph, e.class_.effective_units, e.class_.is_major_subject))
 
        if not graded:
            return None
 
        if calculation_method == 'weighted':
            total_points = sum(ph * units for ph, units, _ in graded)
            total_units  = sum(units      for _,  units, _ in graded)
            return round(total_points / total_units, 2) if total_units > 0 else None
 
        elif calculation_method == 'simple':
            return round(sum(ph for ph, _, _ in graded) / len(graded), 2)
 
        elif calculation_method == 'major_only':
            major = [(ph, units) for ph, units, is_major in graded if is_major]
            if not major:
                return None
            return round(sum(ph for ph, _ in major) / len(major), 2)
 
        return None
 
        """
        Calculate cumulative GPA (all semesters)
        """
        all_grades = self.grades.filter(Grade.final_grade.isnot(None)).all()
        
        if not all_grades:
            return None
        
        if calculation_method == 'weighted':
            total_points = sum(g.final_grade * g.test.class_.effective_units for g in all_grades)
            total_units = sum(g.test.class_.effective_units for g in all_grades)
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
    Class - Specific instance of a subject
    UPDATED: Grading formula no longer requires max_points (for Option B)
    """
    __tablename__ = 'class'
    
    id = db.Column(db.Integer, primary_key=True)
    
    # === SUBJECT INFO ===
    subject_id = db.Column(db.Integer, db.ForeignKey('subject.id'), nullable=True)
    subject_name = db.Column(db.String(200), nullable=True)
    subject_code = db.Column(db.String(20), nullable=True)
    units = db.Column(db.Integer, nullable=True)
    
    # === TEACHER & CLASS DETAILS ===
    teacher_id = db.Column(db.Integer, db.ForeignKey('teacher.id'), nullable=False)
    section = db.Column(db.String(20), nullable=True)
    schedule = db.Column(db.String(100), nullable=True)
    room = db.Column(db.String(50), nullable=True)
    
    # === ACADEMIC PERIOD ===
    school_year = db.Column(db.String(20), nullable=False)
    semester = db.Column(db.String(20), nullable=False)
    
    # === CLASS LIMITS ===
    max_students = db.Column(db.Integer, default=40)
    
    # === GRADING FORMULA ===
    # NEW FORMAT (Option B - max_points optional):
    # {
    #   "components": [
    #     {"name": "Exams", "weight": 30},
    #     {"name": "Quizzes", "weight": 30},
    #     {"name": "Projects", "weight": 40}
    #   ],
    #   "passing_grade": 3.0,
    #   "use_philippine_conversion": true
    # }
    # OLD FORMAT (Option A - still supported):
    # {
    #   "components": [
    #     {"name": "Exams", "weight": 30, "max_points": 100},
    #     {"name": "Quizzes", "weight": 30, "max_points": 100}
    #   ]
    # }
    grading_formula = db.Column(db.Text, nullable=True)
    grade_conversion_table = db.Column(db.Text, nullable=True)
    
    # === PROGRAM/YEAR ===
    department = db.Column(db.String(100), nullable=True)
    program = db.Column(db.String(100), nullable=True)
    year_level = db.Column(db.String(20), nullable=True)
    
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # === RELATIONSHIPS ===
    enrollments = db.relationship('Enrollment', backref='class_', lazy='dynamic', cascade='all, delete-orphan')
    tests = db.relationship('Test', backref='class_', lazy='dynamic', cascade='all, delete-orphan')
    
    # === HELPER PROPERTIES ===
    
    @property
    def effective_subject_name(self):
        """Get subject name from manual input or Subject table"""
        if self.subject_name:
            return self.subject_name
        elif self.subject_id and self.subject:
            return self.subject.name
        return "Unnamed Subject"
    
    @property
    def effective_subject_code(self):
        """Get subject code from manual input or Subject table"""
        if self.subject_code:
            return self.subject_code
        elif self.subject_id and self.subject:
            return self.subject.code
        return "N/A"
    
    @property
    def effective_units(self):
        """Get units from manual input or Subject table"""
        if self.units is not None:
            return self.units
        elif self.subject_id and self.subject:
            return self.subject.units
        return 3  # Default
    
    @property
    def is_major_subject(self):
        """Check if this is a major subject (for GPA calculation)"""
        if self.subject_id and self.subject:
            return self.subject.is_major_subject
        return True
    
    # === GRADING FORMULA METHODS ===
    
    def get_grading_formula(self):
        """
        Parse and return grading formula as dict
        UPDATED: Default formula has no max_points (Option B)
        """
        # Priority 1: Class has its own formula
        if self.grading_formula:
            try:
                return json.loads(self.grading_formula)
            except json.JSONDecodeError:
                pass
        
        # Priority 2: Old class - get from Subject table
        if self.subject_id and self.subject and self.subject.grading_formula:
            try:
                formula = json.loads(self.subject.grading_formula)
                if 'components' in formula:
                    return formula
                return {
                    "components": formula if isinstance(formula, list) else [],
                    "passing_grade": 3.0,
                    "use_philippine_conversion": True
                }
            except (json.JSONDecodeError, AttributeError):
                pass
        
        # Priority 3: Default formula (Option B - no max_points)
        return {
            "components": [
                {"name": "Midterm Exam", "weight": 50},
                {"name": "Final Exam", "weight": 50}
            ],
            "passing_grade": 3.0,
            "use_philippine_conversion": True
        }
    
    def set_grading_formula(self, formula_dict):
        """
        Set grading formula from dict
        UPDATED: max_points is now optional (for Option B)
        Validates that weights total 100%
        """
        if not isinstance(formula_dict, dict):
            raise ValueError("Formula must be a dictionary")
        
        if 'components' not in formula_dict:
            raise ValueError("Formula must have 'components' key")
        
        # Validate each component
        for component in formula_dict['components']:
            if 'name' not in component:
                raise ValueError("Each component must have a 'name'")
            if 'weight' not in component:
                raise ValueError("Each component must have a 'weight'")
            # Note: max_points is optional with Option B
        
        # Validate weights total 100%
        total_weight = sum(c.get('weight', 0) for c in formula_dict['components'])
        if total_weight != 100:
            raise ValueError(f"Component weights must total 100%, got {total_weight}%")
        
        # Ensure required fields
        if 'passing_grade' not in formula_dict:
            formula_dict['passing_grade'] = 3.0
        
        if 'use_philippine_conversion' not in formula_dict:
            formula_dict['use_philippine_conversion'] = True
        
        self.grading_formula = json.dumps(formula_dict)
    
    def validate_formula_weights(self):
        """Check if formula weights total 100%"""
        try:
            formula = self.get_grading_formula()
            if not formula or 'components' not in formula:
                return False
            
            total_weight = sum(c.get('weight', 0) for c in formula['components'])
            return total_weight == 100
        except:
            return False
    
    def has_grading_formula(self):
        """Check if class has a grading formula set"""
        return self.grading_formula is not None or (
            self.subject_id and self.subject and self.subject.grading_formula
        )
    
    def can_edit_formula(self):
        """
        Check if formula can be edited
        Returns True only if no grades have been entered yet
        """
        from models import Grade, Test
        grades_count = Grade.query.join(Test).filter(
            Test.class_id == self.id,
            Grade.final_grade.isnot(None)
        ).count()
        
        return grades_count == 0
    
    def get_grade_conversion_table(self):
        """Get grade conversion table (percentage to PH grade)"""
        if self.grade_conversion_table:
            try:
                return json.loads(self.grade_conversion_table)
            except json.JSONDecodeError:
                pass
        
        # Default Philippine grading scale
        return {
            "97-100": 1.0,
            "94-96": 1.25,
            "91-93": 1.5,
            "88-90": 1.75,
            "85-87": 2.0,
            "82-84": 2.25,
            "79-81": 2.5,
            "76-78": 2.75,
            "75": 3.0,
            "65-74": 4.0,
            "0-64": 5.0
        }
    
    def convert_to_ph_grade(self, percentage):
        """Convert percentage score to Philippine grade"""
        conversion = self.get_grade_conversion_table()
        
        for range_str, grade in conversion.items():
            if '-' in range_str:
                min_score, max_score = map(int, range_str.split('-'))
                if min_score <= percentage <= max_score:
                    return grade
            else:
                if percentage == int(range_str):
                    return grade
        
        return 5.0  # Failed if no match
    
    def __repr__(self):
        section_str = f" - Section {self.section}" if self.section else ""
        return f'<Class {self.effective_subject_code}{section_str} ({self.school_year} {self.semester})>'
    
    def get_enrolled_count(self):
        """Get number of enrolled students"""
        return self.enrollments.filter_by(status='enrolled').count()
    
    def is_full(self):
        """Check if class is at capacity"""
        return self.get_enrolled_count() >= self.max_students
    
    def get_display_name(self):
        """Get full display name of class"""
        code = self.effective_subject_code
        name = self.effective_subject_name
        section = f" - Section {self.section}" if self.section else ""
        return f"{code}: {name}{section}"


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
    Test — A single gradable activity in a class.
 
    METHOD 2 (Activity-Based):
        Every quiz, exam, and project is its own Test row.
        term_tag      → which grading period  ("Prelims", "Midterms", "Finals")
        component_tag → which formula bucket  ("Quizzes", "Exams", "Projects")
 
        Example rows:
            title="Prelim Quiz 1",  term_tag="Prelims",  component_tag="Quizzes"
            title="Prelim Exam",    term_tag="Prelims",  component_tag="Exams"
            title="Midterm Quiz 1", term_tag="Midterms", component_tag="Quizzes"
 
        The grade formula engine groups tests by (term_tag, component_tag),
        averages the scores within each group, applies weights, and produces
        a Philippine grade per term. If any component in the formula has NO
        tagged tests with scores yet, the term grade shows as INC.
 
    BACKWARD COMPATIBLE:
        Old tests with term_tag=None are simply ignored by the new engine.
        They still appear as columns in the grading spreadsheet and can be
        graded manually via final_grade (the old direct-entry path).
    """
 
    __tablename__ = 'test'
 
    id         = db.Column(db.Integer, primary_key=True)
    class_id   = db.Column(db.Integer, db.ForeignKey('class.id'), nullable=False)
    title      = db.Column(db.String(200), nullable=False)
    description = db.Column(db.Text, nullable=True)
    test_date  = db.Column(db.Date, nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
 
    # ── Method 2 tags ──────────────────────────────────────────────────────
    # Nullable so old (untagged) tests keep working without changes.
    term_tag      = db.Column(db.String(50),  nullable=True, index=True)
    component_tag = db.Column(db.String(100), nullable=True)
 
    # Relationships
    grades = db.relationship(
        'Grade', backref='test', lazy='dynamic', cascade='all, delete-orphan'
    )
 
    # ── Helpers ────────────────────────────────────────────────────────────
 
    @property
    def is_tagged(self):
        """True if this test participates in the Method 2 formula engine."""
        return bool(self.term_tag and self.component_tag)
 
    @property
    def display_label(self):
        """
        Short label used in the column header tooltip and student grade view.
        e.g.  "Prelims · Quizzes"
        """
        if self.is_tagged:
            return f"{self.term_tag} · {self.component_tag}"
        return self.title
 
    def __repr__(self):
        tag = f" [{self.term_tag}/{self.component_tag}]" if self.is_tagged else ""
        return f'<Test {self.title}{tag} Class:{self.class_id}>'


class Grade(db.Model):
    """
    Grade - Student scores on tests/assignments
    NOW SUPPORTS: Multiple items per component with individual max scores (Option B)
    BACKWARD COMPATIBLE: Still works with old single-value format (Option A)
    """
    __tablename__ = 'grade'
    
    id = db.Column(db.Integer, primary_key=True)
    test_id = db.Column(db.Integer, db.ForeignKey('test.id'), nullable=False)
    student_id = db.Column(db.Integer, db.ForeignKey('student.id'), nullable=False, index=True)
    
    # Component Scores (JSON format)
    # NEW FORMAT (Option B): {
    #   "Exams": [
    #     {"score": 85, "max": 100, "name": "Prelim Exam", "date": "2024-09-15"},
    #     {"score": 90, "max": 100, "name": "Midterm Exam", "date": "2024-10-20"}
    #   ],
    #   "Quizzes": [
    #     {"score": 20, "max": 25, "name": "Quiz 1", "date": "2024-09-05"}
    #   ]
    # }
    # OLD FORMAT (Option A): {
    #   "Exams": 87.5,
    #   "Quizzes": 85
    # }
    component_scores = db.Column(db.Text, nullable=True)
    raw_score = db.Column(db.Float, nullable=True)
    max_score = db.Column(db.Float, nullable=True)
    
    # Calculated grade (from formula)
    calculated_percentage = db.Column(db.Float, nullable=True)  # Raw percentage (0-100)
    calculated_grade = db.Column(db.Float, nullable=True)  # Converted PH grade (1.0-5.0)
    
    # Manual override
    is_overridden = db.Column(db.Boolean, default=False)
    override_grade = db.Column(db.Float, nullable=True)
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
            try:
                return json.loads(self.component_scores)
            except json.JSONDecodeError:
                return {}
        return {}
    
    def set_component_scores(self, scores_dict):
        """Set component scores from dict"""
        self.component_scores = json.dumps(scores_dict)
        self.updated_at = datetime.utcnow()
    
    def add_component_item(self, component_name, score, max_score, item_name, item_date=None):
        """
        Add a single quiz/exam/task to a component category
        
        Args:
            component_name: e.g., "Quizzes", "Exams"
            score: Student's score (e.g., 20)
            max_score: Maximum possible score (e.g., 25)
            item_name: Name of the item (e.g., "Quiz 1", "Prelim Exam")
            item_date: Date of the item (defaults to now)
        
        Returns:
            dict: The newly added item
        
        Raises:
            ValueError: If validation fails
        """
        # Validation
        if score is None or max_score is None:
            raise ValueError("Score and max_score are required")
        
        if score < 0:
            raise ValueError("Score cannot be negative")
        
        if score > max_score:
            raise ValueError(f"Score ({score}) cannot exceed max score ({max_score})")
        
        if max_score <= 0:
            raise ValueError("Max score must be greater than 0")
        
        if not item_name or not item_name.strip():
            raise ValueError("Item name is required")
        
        # Get current scores
        scores = self.get_component_scores()
        
        # Initialize component as list if it doesn't exist
        if component_name not in scores:
            scores[component_name] = []
        
        # Convert to list if it's old format (single value)
        if not isinstance(scores[component_name], list):
            scores[component_name] = []
        
        # Create new item
        new_item = {
            'score': float(score),
            'max': float(max_score),
            'name': item_name.strip(),
            'date': item_date if item_date else datetime.utcnow().strftime('%Y-%m-%d')
        }
        
        # Add to list
        scores[component_name].append(new_item)
        
        # Save
        self.set_component_scores(scores)
        
        return new_item
    
    def get_component_items(self, component_name):
        """
        Get all items for a specific component
        
        Args:
            component_name: e.g., "Quizzes", "Exams"
        
        Returns:
            list: List of items, empty list if none exist
        """
        scores = self.get_component_scores()
        items = scores.get(component_name, [])
        
        # Handle old format (single value)
        if not isinstance(items, list):
            return []
        
        return items
    
    def update_component_item(self, component_name, item_index, score=None, max_score=None, item_name=None, item_date=None):
        """
        Update a specific quiz/exam/task
        
        Args:
            component_name: e.g., "Quizzes", "Exams"
            item_index: Index of the item to update (0-based)
            score: New score (optional, keeps old if None)
            max_score: New max score (optional, keeps old if None)
            item_name: New name (optional, keeps old if None)
            item_date: New date (optional, keeps old if None)
        
        Returns:
            bool: True if successful, False if item not found
        
        Raises:
            ValueError: If validation fails
        """
        scores = self.get_component_scores()
        
        # Check if component exists and is a list
        if component_name not in scores or not isinstance(scores[component_name], list):
            return False
        
        # Check if index is valid
        if not (0 <= item_index < len(scores[component_name])):
            return False
        
        item = scores[component_name][item_index]
        
        # Update fields if provided
        if score is not None:
            if score < 0:
                raise ValueError("Score cannot be negative")
            item['score'] = float(score)
        
        if max_score is not None:
            if max_score <= 0:
                raise ValueError("Max score must be greater than 0")
            item['max'] = float(max_score)
        
        # Validate score doesn't exceed max after updates
        if item['score'] > item['max']:
            raise ValueError(f"Score ({item['score']}) cannot exceed max score ({item['max']})")
        
        if item_name is not None:
            if not item_name.strip():
                raise ValueError("Item name cannot be empty")
            item['name'] = item_name.strip()
        
        if item_date is not None:
            item['date'] = item_date
        
        # Save
        self.set_component_scores(scores)
        
        return True
    
    def delete_component_item(self, component_name, item_index):
        """
        Delete a specific quiz/exam/task
        
        Args:
            component_name: e.g., "Quizzes", "Exams"
            item_index: Index of the item to delete (0-based)
        
        Returns:
            bool: True if successful, False if item not found
        """
        scores = self.get_component_scores()
        
        # Check if component exists and is a list
        if component_name not in scores or not isinstance(scores[component_name], list):
            return False
        
        # Check if index is valid
        if not (0 <= item_index < len(scores[component_name])):
            return False
        
        # Delete the item
        del scores[component_name][item_index]
        
        # Save
        self.set_component_scores(scores)
        
        return True
    
    def get_component_summary(self, component_name):
        """
        Get summary statistics for a component
        
        Args:
            component_name: e.g., "Quizzes", "Exams"
        
        Returns:
            dict: {
                'item_count': 3,
                'average_percentage': 85.5,
                'total_points': 63,
                'total_max': 75,
                'items': [...]
            }
            Returns None if component doesn't exist or has no items
        """
        items = self.get_component_items(component_name)
        
        if not items:
            return None
        
        percentages = []
        total_points = 0
        total_max = 0
        
        for item in items:
            score = item.get('score', 0)
            max_score = item.get('max', 0)
            
            if max_score > 0:
                percentage = (score / max_score) * 100
                percentages.append(percentage)
                total_points += score
                total_max += max_score
        
        if not percentages:
            return None
        
        return {
            'item_count': len(items),
            'average_percentage': round(sum(percentages) / len(percentages), 2),
            'total_points': total_points,
            'total_max': total_max,
            'items': items
        }
    
    def term_is_complete(self, class_obj, term_tag):
        """
        Check whether every component in the formula has at least one
        tagged test with a score for this term.
    
        Returns (is_complete: bool, missing: list[str])
            is_complete — True only when all components have data
            missing     — list of component names that have no scores yet
    
        Called by calculate_grade_v2() to decide INC vs a real grade.
        """
        from models import Test, Grade
    
        formula = class_obj.get_grading_formula()
        if not formula or 'components' not in formula:
            return False, ['No formula defined']
    
        formula_components = [c['name'] for c in formula['components']]
        missing = []
    
        for comp_name in formula_components:
            # Find all tests for this class, term, component
            tests_in_group = (
                Test.query
                .filter_by(
                    class_id=class_obj.id,
                    term_tag=term_tag,
                    component_tag=comp_name
                )
                .all()
            )
    
            if not tests_in_group:
                # No tests created at all for this component in this term
                missing.append(comp_name)
                continue
    
            # Check if this student has a score in at least one of those tests
            has_score = False
            for t in tests_in_group:
                g = Grade.query.filter_by(
                    test_id=t.id,
                    student_id=self.student_id
                ).first()
                if g and g.final_grade is not None:
                    has_score = True
                    break
    
            if not has_score:
                missing.append(comp_name)
    
        return (len(missing) == 0), missing
 
 
    def calculate_grade_v2(self, class_obj, term_tag):
        """
        Method 2 formula engine.
    
        Groups all tagged tests for (class, term, component), averages the
        scores within each component group, applies formula weights, and
        converts the resulting percentage to a Philippine grade.
    
        Sets:
            self.calculated_percentage  — weighted total (0–100)
            self.calculated_grade       — Philippine grade (1.0–5.0)
            self.final_grade            — same as calculated_grade (or override)
    
        If any formula component has no scores yet, sets everything to None
        (the spreadsheet cell will show "INC").
    
        Returns True if a grade was computed, False if INC.
        """
        from models import Test, Grade
    
        formula = class_obj.get_grading_formula()
        if not formula or 'components' not in formula:
            return False
    
        is_complete, missing = self.term_is_complete(class_obj, term_tag)
        if not is_complete:
            # Not all components have data — show INC
            self.calculated_percentage = None
            self.calculated_grade      = None
            if not self.is_overridden:
                self.final_grade = None
            return False
    
        total_weighted = 0.0
    
        for component in formula['components']:
            comp_name = component['name']
            weight    = component['weight']   # e.g. 40 (meaning 40%)
    
            # All tests for this class / term / component
            tests_in_group = (
                Test.query
                .filter_by(
                    class_id=class_obj.id,
                    term_tag=term_tag,
                    component_tag=comp_name
                )
                .all()
            )
    
            # Collect percentage scores for this student across all tests in group
            percentages = []
            for t in tests_in_group:
                g = Grade.query.filter_by(
                    test_id=t.id,
                    student_id=self.student_id
                ).first()
                if g and g.raw_score is not None and g.max_score is not None and g.max_score > 0:
                    pct = (g.raw_score / g.max_score) * 100
                    percentages.append(pct)
                elif g and g.final_grade is not None:
                    # Fallback: if raw_score not set but final_grade is,
                    # treat final_grade as a pre-converted percentage placeholder.
                    # This handles AI-graded papers where only final_grade is written.
                    # Convert PH grade back to approximate midpoint percentage.
                    # (This branch should rarely be needed.)
                    ph_to_pct = {
                        1.0: 98.5, 1.25: 95.0, 1.5: 92.0, 1.75: 89.0,
                        2.0: 86.0, 2.25: 83.0, 2.5: 80.0, 2.75: 77.0,
                        3.0: 75.0, 4.0: 70.0, 5.0: 50.0
                    }
                    pct = ph_to_pct.get(round(g.final_grade * 4) / 4, 75.0)
                    percentages.append(pct)
    
            if not percentages:
                # Should not happen (term_is_complete already checked), but guard anyway
                self.calculated_percentage = None
                self.calculated_grade      = None
                if not self.is_overridden:
                    self.final_grade = None
                return False
    
            comp_avg = sum(percentages) / len(percentages)
            total_weighted += comp_avg * (weight / 100)
    
        self.calculated_percentage = round(total_weighted, 2)
        self.calculated_grade = class_obj.convert_to_ph_grade(self.calculated_percentage)
    
        if self.is_overridden and self.override_grade:
            self.final_grade = self.override_grade
        else:
            self.final_grade = self.calculated_grade
    
        return True


    def calculate_grade(self, class_obj):
        """
        Unified grade calculation.
    
        If the test this grade belongs to is tagged (Method 2), delegates to
        calculate_grade_v2() which groups all sibling tests by term+component.
    
        If the test is untagged (old Method 1 / direct entry), runs the
        original component_scores logic for backward compatibility.
        """
        # ── Method 2: tagged test ─────────────────────────────────────────────
        if self.test and self.test.is_tagged:
            return self.calculate_grade_v2(class_obj, self.test.term_tag)
    
        # ── Method 1: untagged test (backward compat) ─────────────────────────
        component_data = self.get_component_scores()
        formula = class_obj.get_grading_formula()
    
        if not component_data or not formula or 'components' not in formula:
            return
    
        total_weighted = 0
        total_weight   = 0
    
        for component in formula['components']:
            comp_name = component['name']
            weight    = component['weight']
    
            if comp_name not in component_data:
                continue
    
            items = component_data[comp_name]
    
            if isinstance(items, list):
                if len(items) == 0:
                    continue
                percentages = []
                for item in items:
                    if not isinstance(item, dict):
                        continue
                    score     = item.get('score')
                    max_score = item.get('max')
                    if score is None or max_score is None or max_score == 0:
                        continue
                    percentages.append((score / max_score) * 100)
                if percentages:
                    avg_pct = sum(percentages) / len(percentages)
                    total_weighted += avg_pct * weight / 100
                    total_weight   += weight
            else:
                max_points = component.get('max_points', 100)
                avg_pct    = (items / max_points) * 100
                total_weighted += avg_pct * weight / 100
                total_weight   += weight
    
        if total_weight > 0:
            self.calculated_percentage = round(total_weighted, 2)
            self.calculated_grade = class_obj.convert_to_ph_grade(
                self.calculated_percentage
            )
            if self.is_overridden and self.override_grade:
                self.final_grade = self.override_grade
            else:
                self.final_grade = self.calculated_grade
        else:
            self.calculated_percentage = None
            self.calculated_grade      = None
            if not self.is_overridden:
                self.final_grade = None
    
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

class TestPaperImage(db.Model):
    """
    TestPaperImage — Stores uploaded test paper images from the AI pipeline.
 
    Lifecycle of a record:
        1. 'pending'   → Image uploaded, pipeline running or just finished,
                         not yet assigned to a student.
        2. 'uncertain' → Pipeline ran but OCR name confidence is LOW (<85%).
                         Teacher must manually confirm the suggested student.
        3. 'assigned'  → Teacher has confirmed which student owns this paper.
        4. 'error'     → Pipeline crashed on this specific image. The image
                         file is still saved; teacher can retry or reassign.
 
    Assignment confidence levels (stored in match_confidence):
        >= 85  → HIGH   — auto-suggested, teacher just clicks confirm
        50–84  → MEDIUM — flagged as uncertain, teacher must actively pick
        <  50  → LOW    — treated as unassigned, no suggestion shown
        None   → OCR returned null/garbage, skip fuzzy match entirely
    """
 
    __tablename__ = 'test_paper_image'
 
    id = db.Column(db.Integer, primary_key=True)
 
    # ── Foreign Keys ──────────────────────────────────────────────────────────
    test_id = db.Column(
        db.Integer,
        db.ForeignKey('test.id'),
        nullable=False,
        index=True
    )
    # Null until the professor confirms which student owns this paper
    student_id = db.Column(
        db.Integer,
        db.ForeignKey('student.id'),
        nullable=True,
        index=True
    )
    # Teacher who uploaded the batch
    uploaded_by = db.Column(
        db.Integer,
        db.ForeignKey('teacher.id'),
        nullable=False
    )
 
    # ── File Storage ──────────────────────────────────────────────────────────
    # Relative path from your app's UPLOAD_FOLDER, e.g.:
    #   "test_papers/2025/class_3/test_7/hazel.png"
    image_path = db.Column(db.String(500), nullable=False)
 
    # Original filename as uploaded by the professor
    original_filename = db.Column(db.String(255), nullable=False)
 
    # ── Pipeline / OCR Output (raw from your JSON) ────────────────────────────
    ocr_name  = db.Column(db.String(300), nullable=True)   # raw OCR name field
    ocr_score = db.Column(db.String(50),  nullable=True)   # e.g. "23/100"
    ocr_label = db.Column(db.String(500), nullable=True)   # exam label/title
    ocr_raw_json = db.Column(db.Text,     nullable=True)   # full JSON blob from pipeline
 
    # ── Matching / Assignment ─────────────────────────────────────────────────
    # 0–100 fuzzy match score. None = OCR returned null/garbage.
    match_confidence = db.Column(db.Float, nullable=True)
 
    # Best-guess student_id from fuzzy matching (before teacher confirms).
    # This is the SUGGESTION. student_id above is the CONFIRMED assignment.
    suggested_student_id = db.Column(
        db.Integer,
        db.ForeignKey('student.id'),
        nullable=True
    )
 
    # ── Status ────────────────────────────────────────────────────────────────
    # 'pending' | 'uncertain' | 'assigned' | 'error'
    status = db.Column(db.String(20), nullable=False, default='pending', index=True)
 
    # Human-readable error message if status == 'error'
    error_message = db.Column(db.Text, nullable=True)
 
    # ── Timestamps ────────────────────────────────────────────────────────────
    uploaded_at  = db.Column(db.DateTime, default=datetime.utcnow)
    assigned_at  = db.Column(db.DateTime, nullable=True)   # when teacher confirmed
    processed_at = db.Column(db.DateTime, nullable=True)   # when pipeline finished
 
    # ── Relationships ─────────────────────────────────────────────────────────
    test              = db.relationship('Test',    backref='paper_images',    foreign_keys=[test_id])
    student           = db.relationship('Student', backref='paper_images',    foreign_keys=[student_id])
    suggested_student = db.relationship('Student', foreign_keys=[suggested_student_id])
    uploader          = db.relationship('Teacher', backref='uploaded_papers', foreign_keys=[uploaded_by])
 
    # ── Helpers ───────────────────────────────────────────────────────────────
 
    @property
    def confidence_tier(self):
        """
        Returns a human-readable tier based on match_confidence.
        Used by the template to decide which UI badge/colour to show.
        """
        if self.match_confidence is None:
            return 'none'          # OCR returned null/garbage
        if self.match_confidence >= 85:
            return 'high'          # green  — auto-suggest, professor confirms
        if self.match_confidence >= 50:
            return 'medium'        # yellow — uncertain, professor must pick
        return 'low'               # red    — no useful guess, treat as unassigned
 
    @property
    def display_status(self):
        """Friendly label for the UI."""
        return {
            'pending':   '⏳ Pending Review',
            'uncertain': '⚠️ Uncertain — Verify',
            'assigned':  '✅ Assigned',
            'error':     '❌ Pipeline Error',
        }.get(self.status, self.status)
 
    def assign_to_student(self, student_id):
        """
        Confirm assignment to a student.
        Call this when the teacher clicks 'Confirm' or picks from the dropdown.
        Raises ValueError if student_id is already assigned to another image
        in the same test (duplicate-assignment guard).
        """
        # Duplicate guard — one paper per student per test
        existing = TestPaperImage.query.filter(
            TestPaperImage.test_id    == self.test_id,
            TestPaperImage.student_id == student_id,
            TestPaperImage.id         != self.id,         # not this record itself
            TestPaperImage.status     == 'assigned'
        ).first()
 
        if existing:
            raise ValueError(
                f"Student ID {student_id} already has an assigned paper "
                f"for this test (image ID {existing.id}: {existing.original_filename})."
            )
 
        self.student_id  = student_id
        self.status      = 'assigned'
        self.assigned_at = datetime.utcnow()
 
    def mark_error(self, message):
        """Mark this image as failed during pipeline processing."""
        self.status        = 'error'
        self.error_message = message
        self.processed_at  = datetime.utcnow()
 
    def mark_processed(self, ocr_name, ocr_score, ocr_label, raw_json,
                       suggested_student_id=None, match_confidence=None):
        """
        Call this after the pipeline finishes for this image.
        Sets OCR fields and determines initial status automatically.
        """
        self.ocr_name             = ocr_name
        self.ocr_score            = ocr_score
        self.ocr_label            = ocr_label
        self.ocr_raw_json         = raw_json
        self.suggested_student_id = suggested_student_id
        self.match_confidence     = match_confidence
        self.processed_at         = datetime.utcnow()
 
        # Auto-set status from confidence tier
        tier = self.confidence_tier
        if tier == 'high':
            self.status = 'pending'     # still needs teacher confirm, but pre-filled
        elif tier in ('medium', 'low', 'none'):
            self.status = 'uncertain'   # explicitly flag for manual review
 
    def get_image_url(self):
        """
        Returns the URL path for serving the image.
        Assumes Flask serves uploaded files under /uploads/<image_path>.
        Adjust the prefix to match your app.config['UPLOAD_FOLDER'] setup.
        """
        return f"/uploads/{self.image_path}"
 
    def __repr__(self):
        return (
            f"<TestPaperImage id={self.id} file='{self.original_filename}' "
            f"status='{self.status}' confidence={self.match_confidence}>"
        )


class SystemSettings(db.Model):
    """
    System-wide settings stored in database
    Allows admin to override auto-calculated values
    """
    __tablename__ = 'system_settings'
    
    id = db.Column(db.Integer, primary_key=True)
    setting_key = db.Column(db.String(100), unique=True, nullable=False, index=True)
    setting_value = db.Column(db.String(200), nullable=False)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    updated_by = db.Column(db.String(100), nullable=True)  # Email of admin who updated
    
    def __repr__(self):
        return f'<SystemSettings {self.setting_key}={self.setting_value}>'
    
    @staticmethod
    def get_setting(key, default=None):
        """
        Get a setting value from database
        Returns None if not found
        """
        setting = SystemSettings.query.filter_by(setting_key=key).first()
        return setting.setting_value if setting else default
    
    @staticmethod
    def set_setting(key, value, updated_by=None):
        """
        Set a setting value in database
        Creates new setting if doesn't exist
        """
        setting = SystemSettings.query.filter_by(setting_key=key).first()
        if setting:
            setting.setting_value = value
            setting.updated_at = datetime.utcnow()
            setting.updated_by = updated_by
        else:
            setting = SystemSettings(
                setting_key=key,
                setting_value=value,
                updated_by=updated_by
            )
            db.session.add(setting)
        db.session.commit()
        return setting
    
    @staticmethod
    def delete_setting(key):
        """Delete a setting (revert to auto-calculation)"""
        setting = SystemSettings.query.filter_by(setting_key=key).first()
        if setting:
            db.session.delete(setting)
            db.session.commit()
            return True
        return False