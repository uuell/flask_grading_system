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
            total_points = sum(g.final_grade * g.test.class_.effective_units for g in grades)
            total_units = sum(g.test.class_.effective_units for g in grades)
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
    
    def calculate_grade(self, class_obj):
        """
        Calculate grade based on class's grading formula
        SUPPORTS BOTH:
        - Option B: Multiple items per component with individual max scores
        - Option A: Single pre-averaged value per component (backward compatibility)
        """
        component_data = self.get_component_scores()
        formula = class_obj.get_grading_formula()
        
        if not component_data or not formula or 'components' not in formula:
            return
        
        total_weighted = 0
        total_weight = 0
        
        for component in formula['components']:
            comp_name = component['name']
            weight = component['weight']
            
            if comp_name not in component_data:
                # Component has no data yet - skip it (incomplete grade is OK)
                continue
            
            items = component_data[comp_name]
            
            # OPTION B: List of items with individual max scores
            if isinstance(items, list):
                if len(items) == 0:
                    # Component exists but has 0 items - skip it (incomplete grade is OK)
                    continue
                
                # Calculate average percentage across all items
                percentages = []
                for item in items:
                    if not isinstance(item, dict):
                        continue
                    
                    score = item.get('score')
                    max_score = item.get('max')
                    
                    # Both score and max are required
                    if score is None or max_score is None or max_score == 0:
                        continue
                    
                    percentage = (score / max_score) * 100
                    percentages.append(percentage)
                
                # Calculate average if we have valid percentages
                if percentages:
                    avg_percentage = sum(percentages) / len(percentages)
                    total_weighted += (avg_percentage * weight / 100)
                    total_weight += weight
            
            # OPTION A: Single value (backward compatibility)
            else:
                max_points = component.get('max_points', 100)
                avg_percentage = (items / max_points) * 100
                total_weighted += (avg_percentage * weight / 100)
                total_weight += weight
        
        # Calculate final grade
        if total_weight > 0:
            self.calculated_percentage = round(total_weighted, 2)
            self.calculated_grade = class_obj.convert_to_ph_grade(
                self.calculated_percentage
            )
            
            # Handle manual override
            if self.is_overridden and self.override_grade:
                self.final_grade = self.override_grade
            else:
                self.final_grade = self.calculated_grade
        else:
            # No components have data yet - grade is incomplete
            self.calculated_percentage = None
            self.calculated_grade = None
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