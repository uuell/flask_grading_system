"""
blueprints/student/routes.py - Student Blueprint
Handles student-specific routes: dashboard, grades, classes, profile.
"""

from flask import Blueprint, render_template, redirect, url_for, flash
from flask_login import login_required, current_user
from models import Student, Class, Enrollment, Grade, Test
from config import Config

# Initialize the blueprint for student-related routes
student_bp = Blueprint('student', __name__)


# Decorator to check if current user is a student
def student_required(f):
    """
    Decorator to ensure only students can access the route
    """
    from functools import wraps
    
    @wraps(f)
    @login_required
    def decorated_function(*args, **kwargs):
        if current_user.role != 'student':
            flash('Access denied. Students only.', 'danger')
            return redirect(url_for('index'))
        return f(*args, **kwargs)
    return decorated_function


@student_bp.route('/dashboard')
@student_required
def dashboard():
    """
    Renders the Student Dashboard page.
    Main landing page showing academic overview, enrolled classes, and recent grades.
    """
    # Get student profile
    student = current_user.student_profile
    
    # Get current semester info from config
    current_school_year = Config.get_current_school_year()
    current_semester = Config.get_current_semester()
    
    # Get enrolled classes for current semester
    enrolled_classes = Class.query.join(Enrollment).filter(
        Enrollment.student_id == student.id,
        Class.school_year == current_school_year,
        Class.semester == current_semester
    ).all()
    
    # Get recent grades (last 5)
    recent_grades = Grade.query.filter_by(student_id=student.id)\
        .filter(Grade.final_grade.isnot(None))\
        .order_by(Grade.graded_at.desc())\
        .limit(5)\
        .all()
    
    # Calculate GPA with all three methods
    semester_gpa = student.get_semester_gpa(
        current_school_year, current_semester, 'weighted'
    )
    semester_gpa_simple = student.get_semester_gpa(
        current_school_year, current_semester, 'simple'
    )
    semester_gpa_major = student.get_semester_gpa(
        current_school_year, current_semester, 'major_only'
    )
    
    cumulative_gpa = student.get_cumulative_gpa('weighted')
    cumulative_gpa_simple = student.get_cumulative_gpa('simple')
    cumulative_gpa_major = student.get_cumulative_gpa('major_only')
    
    # Calculate total units enrolled
    total_units = sum(cls.effective_units for cls in enrolled_classes)
    
    # Placeholder values for now (you can calculate these later)
    total_units_completed = None
    total_program_units = None
    passing_rate = None
    
    return render_template(
        'student/dashboard.html',
        student=student,
        enrolled_classes=enrolled_classes,
        recent_grades=recent_grades,
        semester_gpa=semester_gpa,
        semester_gpa_simple=semester_gpa_simple,
        semester_gpa_major=semester_gpa_major,
        cumulative_gpa=cumulative_gpa,
        cumulative_gpa_simple=cumulative_gpa_simple,
        cumulative_gpa_major=cumulative_gpa_major,
        total_units=total_units,
        total_units_completed=total_units_completed,
        total_program_units=total_program_units,
        passing_rate=passing_rate,
        current_school_year=current_school_year,
        current_semester=current_semester
    )


@student_bp.route('/profile')
@student_required
def profile():
    """
    Renders the Profile page.
    Shows student information and allows profile updates.
    """
    student = current_user.student_profile
    
    # Calculate some profile stats
    current_school_year = Config.get_current_school_year()
    current_semester = Config.get_current_semester()
    
    # Get cumulative GPA
    cumulative_gpa = student.get_cumulative_gpa('weighted')
    
    # Check academic standing based on GPA
    if cumulative_gpa:
        if cumulative_gpa <= 1.75:
            academic_standing = "Dean's Lister"
            standing_color = "var(--success-green)"
        elif cumulative_gpa <= 2.5:
            academic_standing = "Good Standing"
            standing_color = "var(--success-green)"
        elif cumulative_gpa <= 3.0:
            academic_standing = "Satisfactory"
            standing_color = "var(--text-main)"
        else:
            academic_standing = "Probation"
            standing_color = "var(--danger-red)"
    else:
        academic_standing = "Good Standing"
        standing_color = "var(--text-main)"
    
    # Get total completed units (all enrollments with grades)
    completed_enrollments = Enrollment.query.filter_by(
        student_id=student.id,
        status='completed'
    ).all()
    total_completed_units = sum(e.class_.effective_units for e in completed_enrollments if e.final_grade and e.final_grade <= 3.0)
    
    # Get current enrollments
    current_enrollments = Enrollment.query.filter_by(
        student_id=student.id,
        status='enrolled'
    ).join(Class).filter(
        Class.school_year == current_school_year,
        Class.semester == current_semester
    ).count()
    
    # Determine student type (Regular vs Irregular)
    student_type = "Regular Student" if student.section else "Irregular Student"
    
    # Check if Dean's Lister
    is_deans_lister = cumulative_gpa and cumulative_gpa <= 1.75
    
    return render_template(
        'student/profile.html',
        student=student,
        cumulative_gpa=cumulative_gpa,
        academic_standing=academic_standing,
        standing_color=standing_color,
        total_completed_units=total_completed_units,
        current_enrollments=current_enrollments,
        student_type=student_type,
        is_deans_lister=is_deans_lister,
        current_school_year=current_school_year,
        current_semester=current_semester
    )


@student_bp.route('/classes')
@student_required
def my_classes():
    """
    Renders the 'My Classes' page.
    Shows all enrolled classes with details (current and past semesters).
    """
    student = current_user.student_profile
    
    # Get current semester classes
    current_school_year = Config.get_current_school_year()
    current_semester = Config.get_current_semester()
    
    current_classes = Class.query.join(Enrollment).filter(
        Enrollment.student_id == student.id,
        Class.school_year == current_school_year,
        Class.semester == current_semester,
        Enrollment.status == 'enrolled'
    ).all()
    
    # Calculate stats
    total_subjects = len(current_classes)
    total_units = sum(cls.effective_units for cls in current_classes)
    lab_hours = sum(cls.effective_units * 1.5 for cls in current_classes if cls.subject and ('Lab' in cls.subject.name or cls.subject.code.endswith('L')))
    
    # Check for schedule conflicts (simplified - checks if any two classes overlap)
    has_conflicts = False  # You can implement conflict detection logic later
    
    return render_template(
        'student/my_classes.html',
        student=student,
        current_classes=current_classes,
        total_subjects=total_subjects,
        total_units=total_units,
        lab_hours=lab_hours,
        has_conflicts=has_conflicts,
        current_school_year=current_school_year,
        current_semester=current_semester
    )


@student_bp.route('/grades')
@student_required
def my_grades():
    """
    Renders the academic records and grades page.
    Shows detailed grade breakdown per subject.
    """
    student = current_user.student_profile
    
    # Get all grades grouped by class
    current_school_year = Config.get_current_school_year()
    current_semester = Config.get_current_semester()
    
    # Get all enrolled classes for current semester with their grades
    current_classes_with_grades = []
    
    enrollments = Enrollment.query.filter_by(
        student_id=student.id
    ).join(Class).filter(
        Class.school_year == current_school_year,
        Class.semester == current_semester
    ).all()
    
    for enrollment in enrollments:
        cls = enrollment.class_
        
        # Get all grades for this class
        grades_for_class = Grade.query.filter_by(
            student_id=student.id
        ).join(Test).filter(
            Test.class_id == cls.id
        ).all()
        
        # Calculate midterm and finals (example logic - adjust as needed)
        midterm_grade = None
        finals_grade = None
        
        for grade in grades_for_class:
            if 'midterm' in grade.test.title.lower():
                midterm_grade = grade.final_grade
            elif 'final' in grade.test.title.lower():
                finals_grade = grade.final_grade
        
        current_classes_with_grades.append({
            'class': cls,
            'enrollment': enrollment,
            'midterm': midterm_grade,
            'finals': finals_grade,
            'semester_grade': enrollment.final_grade,
            'all_grades': grades_for_class
        })
    
    # Calculate semester GPA
    semester_gpa = student.get_semester_gpa(
        current_school_year, current_semester, 'weighted'
    )
    
    # Calculate cumulative GPA
    cumulative_gpa = student.get_cumulative_gpa('weighted')
    
    # Determine academic rank (simplified)
    if cumulative_gpa:
        if cumulative_gpa <= 1.5:
            academic_rank = 'A'
        elif cumulative_gpa <= 2.0:
            academic_rank = 'B'
        elif cumulative_gpa <= 2.5:
            academic_rank = 'C'
        else:
            academic_rank = 'D'
    else:
        academic_rank = 'N/A'
    
    # Count passed subjects
    passed_count = sum(1 for item in current_classes_with_grades 
                      if item['semester_grade'] and item['semester_grade'] <= 3.0)
    total_count = len(current_classes_with_grades)
    
    return render_template(
        'student/my_grades.html',
        student=student,
        current_classes_with_grades=current_classes_with_grades,
        semester_gpa=semester_gpa,
        cumulative_gpa=cumulative_gpa,
        academic_rank=academic_rank,
        passed_count=passed_count,
        total_count=total_count,
        current_school_year=current_school_year,
        current_semester=current_semester
    )


@student_bp.route('/gpa-calculator')
@student_required
def gpa_calculator():
    """
    Renders the interactive GPA calculation tool.
    Allows students to toggle between different GPA calculation methods.
    Pre-loads their current enrolled classes for easy calculation.
    """
    student = current_user.student_profile
    
    current_school_year = Config.get_current_school_year()
    current_semester = Config.get_current_semester()
    
    # Get enrolled classes with current grades
    enrolled_classes_data = []
    
    enrollments = Enrollment.query.filter_by(
        student_id=student.id
    ).join(Class).filter(
        Class.school_year == current_school_year,
        Class.semester == current_semester,
        Enrollment.status == 'enrolled'
    ).all()
    
    for enrollment in enrollments:
        cls = enrollment.class_
        enrolled_classes_data.append({
            'subject_name': cls.effective_subject_name,
            'subject_code': cls.effective_subject_code,
            'units': cls.effective_units,
            'current_grade': enrollment.final_grade if enrollment.final_grade else None
        })
    
    # Calculate GPA with all three methods
    semester_gpa_weighted = student.get_semester_gpa(
        current_school_year, current_semester, 'weighted'
    )
    semester_gpa_simple = student.get_semester_gpa(
        current_school_year, current_semester, 'simple'
    )
    semester_gpa_major = student.get_semester_gpa(
        current_school_year, current_semester, 'major_only'
    )
    
    cumulative_gpa_weighted = student.get_cumulative_gpa('weighted')
    cumulative_gpa_simple = student.get_cumulative_gpa('simple')
    cumulative_gpa_major = student.get_cumulative_gpa('major_only')
    
    # Get all grades for reference
    all_grades = Grade.query.filter_by(student_id=student.id)\
        .filter(Grade.final_grade.isnot(None))\
        .all()
    
    return render_template(
        'student/gpa_calculator.html',
        student=student,
        enrolled_classes_data=enrolled_classes_data,
        semester_gpa_weighted=semester_gpa_weighted,
        semester_gpa_simple=semester_gpa_simple,
        semester_gpa_major=semester_gpa_major,
        cumulative_gpa_weighted=cumulative_gpa_weighted,
        cumulative_gpa_simple=cumulative_gpa_simple,
        cumulative_gpa_major=cumulative_gpa_major,
        all_grades=all_grades,
        current_school_year=current_school_year,
        current_semester=current_semester
    )