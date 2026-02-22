"""
blueprints/student/routes.py - Student Blueprint
Handles student-specific routes: dashboard, grades, classes, profile.
"""

from flask import Blueprint, render_template, redirect, url_for, flash, request
from flask_login import login_required, current_user
from models import Student, Class, Enrollment, Grade, Test
from extensions import db, bcrypt
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
    Supports ?year= and ?semester= query params for filtering.
    Defaults to current semester/year if not provided.
    """
    student = current_user.student_profile

    # --- Current config values ---
    current_school_year = Config.get_current_school_year()
    current_semester = Config.get_current_semester()

    # --- Filtering (same pattern as teacher dashboard) ---
    selected_year = request.args.get('year')
    selected_semester = request.args.get('semester')

    if not selected_year or selected_year == 'all':
        selected_year = current_school_year
    if not selected_semester or selected_semester == 'all':
        selected_semester = current_semester

    # --- Build available years from student's enrollment history ---
    from datetime import datetime as dt
    all_enrollments = Enrollment.query.filter_by(
        student_id=student.id
    ).join(Class).with_entities(Class.school_year).distinct().all()

    actual_years = set(row.school_year for row in all_enrollments)
    current_year_num = dt.now().year
    buffer_years = {f"{y}-{y+1}" for y in range(current_year_num - 3, current_year_num + 2)}
    available_years = sorted(list(actual_years | buffer_years), reverse=True)

    # --- Enrolled classes for selected semester/year ---
    enrollments = Enrollment.query.filter_by(
        student_id=student.id
    ).join(Class).filter(
        Class.school_year == selected_year,
        Class.semester == selected_semester
    ).all()

    enrolled_classes = [e.class_ for e in enrollments]

    # Build enrollment lookup dict: class_id -> enrollment
    # This avoids querying the DB inside the template
    enrollment_map = {e.class_id: e for e in enrollments}

    # --- Recent grades (global, not filtered by semester) ---
    recent_grades = Grade.query.filter_by(student_id=student.id)\
        .filter(Grade.final_grade.isnot(None))\
        .join(Test)\
        .join(Class)\
        .order_by(Grade.graded_at.desc())\
        .limit(5)\
        .all()

    # --- Semester GPA (both methods, for selected semester) ---
    semester_gpa_weighted = student.get_semester_gpa(
        selected_year, selected_semester, 'weighted'
    )
    semester_gpa_simple = student.get_semester_gpa(
        selected_year, selected_semester, 'simple'
    )

    # --- Cumulative GPA (always weighted, always global) ---
    cumulative_gpa = student.get_cumulative_gpa('weighted')

    # --- Quick Stats ---

    # Units enrolled this semester
    total_units = sum(cls.effective_units for cls in enrolled_classes)

    # Graded count: subjects with a final_grade in enrollment vs total enrolled
    graded_count = sum(1 for e in enrollments if e.final_grade is not None)
    total_count = len(enrollments)

    # Academic standing from cumulative GPA
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

    return render_template(
        'student/dashboard.html',
        student=student,
        enrolled_classes=enrolled_classes,
        enrollment_map=enrollment_map,
        recent_grades=recent_grades,
        semester_gpa_weighted=semester_gpa_weighted,
        semester_gpa_simple=semester_gpa_simple,
        cumulative_gpa=cumulative_gpa,
        total_units=total_units,
        graded_count=graded_count,
        total_count=total_count,
        academic_standing=academic_standing,
        standing_color=standing_color,
        available_years=available_years,
        selected_year=selected_year,
        selected_semester=selected_semester,
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
    Supports ?year= and ?semester= query params for filtering.
    Defaults to current semester/year if not provided.
    """
    student = current_user.student_profile

    # --- Current config values ---
    current_school_year = Config.get_current_school_year()
    current_semester = Config.get_current_semester()

    # --- Filtering ---
    selected_year = request.args.get('year')
    selected_semester = request.args.get('semester')

    if not selected_year or selected_year == 'all':
        selected_year = current_school_year
    if not selected_semester or selected_semester == 'all':
        selected_semester = current_semester

    # --- Build available years from student enrollment history ---
    from datetime import datetime as dt
    all_enrollments = Enrollment.query.filter_by(
        student_id=student.id
    ).join(Class).with_entities(Class.school_year).distinct().all()

    actual_years = set(row.school_year for row in all_enrollments)
    current_year_num = dt.now().year
    buffer_years = {f"{y}-{y+1}" for y in range(current_year_num - 3, current_year_num + 2)}
    available_years = sorted(list(actual_years | buffer_years), reverse=True)

    # --- Get enrollments for selected semester/year ---
    enrollments = Enrollment.query.filter_by(
        student_id=student.id
    ).join(Class).filter(
        Class.school_year == selected_year,
        Class.semester == selected_semester
    ).all()

    current_classes = [e.class_ for e in enrollments]

    # Build enrollment map: class_id -> enrollment
    enrollment_map = {e.class_id: e for e in enrollments}

    # --- Stats ---
    total_subjects = len(current_classes)
    total_units = sum(cls.effective_units for cls in current_classes)

    # Graded count: enrollments with a final_grade set
    graded_count = sum(1 for e in enrollments if e.final_grade is not None)

    # Academic standing from cumulative GPA
    cumulative_gpa = student.get_cumulative_gpa('weighted')

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

    return render_template(
        'student/my_classes.html',
        student=student,
        current_classes=current_classes,
        enrollment_map=enrollment_map,
        total_subjects=total_subjects,
        total_units=total_units,
        graded_count=graded_count,
        academic_standing=academic_standing,
        standing_color=standing_color,
        available_years=available_years,
        selected_year=selected_year,
        selected_semester=selected_semester,
        current_school_year=current_school_year,
        current_semester=current_semester
    )


@student_bp.route('/grades')
@student_required
def my_grades():
    """
    Renders the My Grades page.
    Shows all enrolled classes for the selected semester as individual
    spreadsheet cards, each mirroring the teacher's grading table.
    Supports ?year= and ?semester= query params for filtering.
    
    ✅ FIXED: Properly structures component data for modal display
    """
    student = current_user.student_profile

    # --- Current config values ---
    current_school_year = Config.get_current_school_year()
    current_semester = Config.get_current_semester()

    # --- Filtering ---
    selected_year = request.args.get('year')
    selected_semester = request.args.get('semester')

    if not selected_year or selected_year == 'all':
        selected_year = current_school_year
    if not selected_semester or selected_semester == 'all':
        selected_semester = current_semester

    # --- Build available years from student enrollment history ---
    from datetime import datetime as dt
    all_enrollments_years = Enrollment.query.filter_by(
        student_id=student.id
    ).join(Class).with_entities(Class.school_year).distinct().all()

    actual_years = set(row.school_year for row in all_enrollments_years)
    current_year_num = dt.now().year
    buffer_years = {f"{y}-{y+1}" for y in range(current_year_num - 3, current_year_num + 2)}
    available_years = sorted(list(actual_years | buffer_years), reverse=True)

    # --- Get enrollments for selected semester/year ---
    enrollments = Enrollment.query.filter_by(
        student_id=student.id
    ).join(Class).filter(
        Class.school_year == selected_year,
        Class.semester == selected_semester
    ).all()

    # --- Build per-class grading data ---
    classes_data = []

    for enrollment in enrollments:
        cls = enrollment.class_

        # Get all tests for this class
        tests = Test.query.filter_by(
            class_id=cls.id
        ).order_by(Test.test_date, Test.created_at).all()

        # ✅ FIX: Get grading formula FIRST
        formula = cls.get_grading_formula()
        formula_components = formula.get('components', []) if formula else []

        # Build component weight lookup: component_name -> weight
        component_weights = {c['name']: c['weight'] for c in formula_components}

        # ✅ FIX: Get student's grades with proper structure
        test_grades = {}
        for test in tests:
            grade = Grade.query.filter_by(
                test_id=test.id,
                student_id=student.id
            ).first()
            
            if grade:
                # Get component scores from the grade
                component_scores = grade.get_component_scores()
                
                test_grades[test.id] = {
                    'grade_obj': grade,  # The actual Grade object
                    'component_scores': component_scores,  # Dict of {component_name: [items]}
                    'final_grade': grade.final_grade,
                    'calculated_percentage': grade.calculated_percentage,
                    'is_overridden': grade.is_overridden,
                    'override_reason': grade.override_reason
                }
            else:
                # No grade yet - still provide empty structure
                test_grades[test.id] = {
                    'grade_obj': None,
                    'component_scores': {},  # Empty dict
                    'final_grade': None,
                    'calculated_percentage': None,
                    'is_overridden': False,
                    'override_reason': None
                }

        classes_data.append({
            'class': cls,
            'enrollment': enrollment,
            'tests': tests,
            'test_grades': test_grades,          # test.id -> grade data dict
            'component_weights': component_weights,  # component_name -> weight %
            'formula_components': formula_components,  # Full formula structure
            'final_grade': enrollment.final_grade
        })

    return render_template(
        'student/my_grades.html',
        student=student,
        classes_data=classes_data,
        available_years=available_years,
        selected_year=selected_year,
        selected_semester=selected_semester,
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

@student_bp.route('/change-password', methods=['POST'])
@student_required
def change_password():
    """
    Change student's password
    """
    from extensions import bcrypt
    
    try:
        current_password = request.form.get('current_password', '').strip()
        new_password = request.form.get('new_password', '').strip()
        confirm_password = request.form.get('confirm_password', '').strip()
        
        # Validation
        if not all([current_password, new_password, confirm_password]):
            flash('All fields are required.', 'error')
            return redirect(url_for('student.profile'))
        
        # Check if new passwords match
        if new_password != confirm_password:
            flash('New passwords do not match.', 'error')
            return redirect(url_for('student.profile'))
        
        # Check password length
        if len(new_password) < 6:
            flash('Password must be at least 6 characters long.', 'error')
            return redirect(url_for('student.profile'))
        
        # Verify current password
        if not bcrypt.check_password_hash(current_user.password, current_password):
            flash('Current password is incorrect.', 'error')
            return redirect(url_for('student.profile'))
        
        # Update password
        current_user.password = bcrypt.generate_password_hash(new_password).decode('utf-8')
        db.session.commit()
        
        flash('✅ Password updated successfully!', 'success')
        return redirect(url_for('student.profile'))
        
    except Exception as e:
        db.session.rollback()
        flash(f'❌ Error updating password: {str(e)}', 'error')
        return redirect(url_for('student.profile'))