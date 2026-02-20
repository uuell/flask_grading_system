"""
blueprints/teacher/routes.py - Teacher Blueprint COMPLETE & FIXED
Handles teacher-specific routes: dashboard, classes, grading, roster management.
This version fixes the routing errors while preserving all existing functionality.
"""

import json
from flask import Blueprint, render_template, redirect, url_for, flash, request, jsonify
from flask_login import login_required, current_user
from models import Teacher, Class, Enrollment, Student, Subject, Grade, Test
from extensions import db, bcrypt
from config import Config
from sqlalchemy import func
from datetime import datetime, timedelta
from config import Config

# Initialize the blueprint for teacher-related routes
teacher_bp = Blueprint('teacher', __name__)


# Decorator to check if current user is a teacher
def teacher_required(f):
    """
    Decorator to ensure only teachers can access the route
    """
    from functools import wraps
    
    @wraps(f)
    @login_required
    def decorated_function(*args, **kwargs):
        if current_user.role != 'teacher':
            flash('Access denied. Teachers only.', 'danger')
            return redirect(url_for('index'))
        return f(*args, **kwargs)
    return decorated_function


@teacher_bp.route('/dashboard')
@teacher_required
def dashboard():
    """
    Renders the Teacher Dashboard page with year and semester selection support.
    """
    teacher = current_user.teacher_profile
    
    # Get current values from config
    current_school_year = Config.get_current_school_year()
    current_semester = Config.get_current_semester()
    
    # ✅ Get filters from query parameters
    selected_year = request.args.get('year')
    selected_semester = request.args.get('semester')
    
    # ✅ FIX: Default to current semester if no filter or "all" selected
    if not selected_year or selected_year == 'all':
        selected_year = current_school_year
    
    if not selected_semester or selected_semester == 'all':
        selected_semester = current_semester
    
    # Get ALL classes for this teacher (to build year list)
    all_classes = Class.query.filter_by(teacher_id=teacher.id).all()
    
    # Build available years list
    from datetime import datetime
    actual_years = set([cls.school_year for cls in all_classes])
    current_year_num = datetime.now().year
    buffer_years = {f"{y}-{y+1}" for y in range(current_year_num-5, current_year_num+3)}
    available_years = sorted(list(actual_years | buffer_years), reverse=True)
    
    # ✅ Build query with filters - ALWAYS filter by selected year/semester
    query = Class.query.filter_by(
        teacher_id=teacher.id,
        school_year=selected_year,
        semester=selected_semester
    )
    
    # Execute query
    classes = query.all()
    
    # ✅ Calculate total students for FILTERED classes
    total_students = db.session.query(func.count(func.distinct(Enrollment.student_id)))\
        .join(Class).filter(
            Class.teacher_id == teacher.id,
            Class.school_year == selected_year,
            Class.semester == selected_semester,
            Enrollment.status == 'enrolled'
        ).scalar() or 0
    
    # Calculate weekly schedule for FILTERED classes
    weekly_schedule = {
        'Monday': 0, 'Tuesday': 0, 'Wednesday': 0,
        'Thursday': 0, 'Friday': 0, 'Saturday': 0
    }
    
    for cls in classes:
        if cls.schedule:
            schedule_upper = cls.schedule.upper()
            if 'M' in schedule_upper and 'Monday' not in schedule_upper:
                weekly_schedule['Monday'] += 1
            if 'T' in schedule_upper and 'TH' not in schedule_upper:
                weekly_schedule['Tuesday'] += 1
            if 'W' in schedule_upper:
                weekly_schedule['Wednesday'] += 1
            if 'TH' in schedule_upper or 'R' in schedule_upper:
                weekly_schedule['Thursday'] += 1
            if 'F' in schedule_upper:
                weekly_schedule['Friday'] += 1
            if 'S' in schedule_upper or 'SAT' in schedule_upper:
                weekly_schedule['Saturday'] += 1
    
    # Get classes with stats for FILTERED classes
    classes_with_stats = []
    for cls in classes:
        student_count = Enrollment.query.filter_by(
            class_id=cls.id,
            status='enrolled'
        ).count()
        
        tests = Test.query.filter_by(class_id=cls.id).all()
        ungraded_count = 0
        
        for test in tests:
            enrolled_students = Enrollment.query.filter_by(
                class_id=cls.id,
                status='enrolled'
            ).count()
            
            graded_students = Grade.query.filter_by(
                test_id=test.id
            ).filter(Grade.final_grade.isnot(None)).count()
            
            ungraded_count += (enrolled_students - graded_students)
        
        # Create display dict
        class_display = {
            'id': cls.id,
            'name': cls.effective_subject_name,
            'code': cls.effective_subject_code,
            'section': cls.section
        }
        
        classes_with_stats.append({
            'class': class_display,
            'student_count': student_count,
            'ungraded_count': ungraded_count
        })
    
    return render_template(
        'teacher/dashboard.html',
        teacher=teacher,
        classes_with_stats=classes_with_stats,
        total_students=total_students,
        total_classes=len(classes),
        weekly_schedule=weekly_schedule,
        current_school_year=current_school_year,
        current_semester=current_semester,
        selected_year=selected_year,          # ✅ Pass actual selected value
        selected_semester=selected_semester,  # ✅ Pass actual selected value
        available_years=available_years
    )

@teacher_bp.route('/classes')
@teacher_required
def classes():
    teacher = current_user.teacher_profile
    
    current_school_year = Config.get_current_school_year()
    current_semester = Config.get_current_semester()
    
    # Get filters from query parameters
    selected_year = request.args.get('year')
    selected_semester = request.args.get('semester')
    
    # Build query
    query = Class.query.filter_by(teacher_id=teacher.id)
    
    # Apply year filter
    if selected_year and selected_year != 'all':
        query = query.filter_by(school_year=selected_year)
    
    # Apply semester filter
    if selected_semester and selected_semester != 'all':
        query = query.filter_by(semester=selected_semester)
    
    # Execute query
    teacher_classes = query.order_by(
        Class.school_year.desc(),
        Class.semester
    ).all()
    
    # Build available years list for dropdown
    all_years = sorted(
        list(set([cls.school_year for cls in Class.query.filter_by(teacher_id=teacher.id).all()])),
        reverse=True
    )
    available_years = all_years  # Show all years with classes
    
    # Get class details with enrollment info and grading progress
    classes_data = []
    for cls in teacher_classes:
        enrollment_count = Enrollment.query.filter_by(
            class_id=cls.id,
            status='enrolled'
        ).count()
        
        # Calculate grading completion percentage
        tests = Test.query.filter_by(class_id=cls.id).all()
        total_possible_grades = enrollment_count * len(tests) if tests else 0
        
        if total_possible_grades > 0:
            graded_count = 0
            for test in tests:
                graded_count += Grade.query.filter_by(
                    test_id=test.id
                ).filter(Grade.final_grade.isnot(None)).count()
            
            grading_percentage = (graded_count / total_possible_grades * 100)
        else:
            grading_percentage = 0
        
        # Create display dict
        class_display = {
            'id': cls.id,
            'name': cls.effective_subject_name,
            'code': cls.effective_subject_code,
            'units': cls.effective_units,
            'section': cls.section,
            'schedule': cls.schedule,
            'room': cls.room,
            'semester': cls.semester,
            'school_year': cls.school_year,
            'max_students': cls.max_students,
            'has_formula': cls.has_grading_formula(),
            'can_edit_formula': cls.can_edit_formula()
        }
        
        classes_data.append({
            'class': class_display,
            'enrollment_count': enrollment_count,
            'capacity_percentage': (enrollment_count / cls.max_students * 100) if cls.max_students else 0,
            'grading_percentage': grading_percentage
        })
    
    # Get all students for the roster builder
    all_students = Student.query.order_by(Student.last_name, Student.first_name).all()
    students_json = [{
        'id': s.id,
        'first_name': s.first_name,
        'last_name': s.last_name,
        'student_number': s.student_number,
        'program': s.program
    } for s in all_students]
    
    return render_template(
        'teacher/classes.html',
        teacher=teacher,
        classes_data=classes_data,
        all_students=students_json,
        current_school_year=current_school_year,
        current_semester=current_semester,
        available_years=available_years,
        selected_year=selected_year or 'all',  # Pass selected filters back
        selected_semester=selected_semester or 'all'
    )


@teacher_bp.route('/classes/create', methods=['POST'])
@teacher_required
def create_class():
    """
    Create a new class with manual subject input and grading formula.
    """
    teacher = current_user.teacher_profile
    
    try:
        # === GET MANUAL SUBJECT INPUT ===
        subject_name = request.form.get('subject_name', '').strip()
        subject_code = request.form.get('subject_code', '').strip()
        units = request.form.get('units', type=int)
        
        # === GET CLASS DETAILS ===
        section = request.form.get('section', '').strip()
        room = request.form.get('room', '').strip()
        schedule = request.form.get('schedule', '').strip()
        school_year = request.form.get('school_year', '').strip()
        semester = request.form.get('semester', '').strip()
        max_students = request.form.get('max_students', type=int, default=40)
        
        # === GET GRADING FORMULA ===
        grading_formula_json = request.form.get('grading_formula', '').strip()
        passing_grade = request.form.get('passing_grade', type=float, default=3.0)
        
        # === GET STUDENT IDS ===
        student_ids_str = request.form.get('student_ids', '')
        
        # === VALIDATE REQUIRED FIELDS ===
        if not subject_name:
            flash('Subject name is required.', 'error')
            return redirect(url_for('teacher.classes'))
        
        if not units or units < 1:
            flash('Units must be at least 1.', 'error')
            return redirect(url_for('teacher.classes'))
        
        if not section or not school_year or not semester:
            flash('Section, school year, and semester are required.', 'error')
            return redirect(url_for('teacher.classes'))
        
        # === VALIDATE GRADING FORMULA ===
        if not grading_formula_json:
            flash('Grading formula is required.', 'error')
            return redirect(url_for('teacher.classes'))
        
        try:
            formula = json.loads(grading_formula_json)
            
            # Validate structure
            if 'components' not in formula or not isinstance(formula['components'], list):
                raise ValueError("Invalid formula structure")
            
            if len(formula['components']) < 1:
                raise ValueError("At least one component is required")
            
            # Validate weights total 100%
            total_weight = sum(c.get('weight', 0) for c in formula['components'])
            if total_weight != 100:
                raise ValueError(f"Component weights must total 100%, got {total_weight}%")
            
            # Validate all components have names
            for comp in formula['components']:
                if not comp.get('name') or comp['name'].strip() == '':
                    raise ValueError("All components must have a name")
                if comp.get('weight', 0) < 0 or comp.get('weight', 0) > 100:
                    raise ValueError("Component weights must be between 0 and 100")
                if comp.get('max_points', 0) < 1:
                    raise ValueError("Max points must be at least 1")
            
        except json.JSONDecodeError:
            flash('Invalid grading formula format.', 'error')
            return redirect(url_for('teacher.classes'))
        except ValueError as e:
            flash(f'Grading formula error: {str(e)}', 'error')
            return redirect(url_for('teacher.classes'))
        
        # === CREATE THE CLASS ===
        new_class = Class(
            teacher_id=teacher.id,
            
            # Manual subject input (NEW)
            subject_name=subject_name,
            subject_code=subject_code or None,
            units=units,
            
            # Class details
            section=section,
            room=room or None,
            schedule=schedule or None,
            school_year=school_year,
            semester=semester,
            max_students=max_students,
            
            # Grading formula (NEW)
            grading_formula=grading_formula_json
        )
        
        db.session.add(new_class)
        db.session.flush()  # Get the class ID
        
        # === ENROLL SELECTED STUDENTS ===
        if student_ids_str:
            student_ids = [int(id) for id in student_ids_str.split(',') if id.strip()]
            
            for student_id in student_ids:
                enrollment = Enrollment(
                    student_id=student_id,
                    class_id=new_class.id,
                    status='enrolled'
                )
                db.session.add(enrollment)
        
        db.session.commit()
        
        # Success message
        display_name = f"{subject_code} - {subject_name}" if subject_code else subject_name
        flash(f'Class "{display_name} (Section {section})" created successfully!', 'success')
        
    except Exception as e:
        db.session.rollback()
        flash(f'Error creating class: {str(e)}', 'error')
        print(f"Error creating class: {str(e)}")  # For debugging
        import traceback
        traceback.print_exc()
    
    return redirect(url_for('teacher.classes'))


@teacher_bp.route('/classes/delete', methods=['POST'])
@teacher_required
def delete_class():
    """
    Delete a class and all associated enrollments.
    """
    teacher = current_user.teacher_profile
    class_id = request.form.get('class_id', type=int)
    
    # Verify the class belongs to this teacher
    cls = Class.query.filter_by(
        id=class_id,
        teacher_id=teacher.id
    ).first()
    
    if not cls:
        flash('Class not found or access denied.', 'error')
        return redirect(url_for('teacher.classes'))
    
    try:
        class_name = f"{cls.subject.name} - Section {cls.section}"
        
        # Delete the class (cascades to enrollments, tests, and grades)
        db.session.delete(cls)
        db.session.commit()
        
        flash(f'Class "{class_name}" deleted successfully.', 'success')
        
    except Exception as e:
        db.session.rollback()
        flash(f'Error deleting class: {str(e)}', 'error')
    
    return redirect(url_for('teacher.classes'))


@teacher_bp.route('/classes/<int:class_id>')
@teacher_required
def class_detail(class_id):
    """
    Renders the Class Detail page showing roster and class information.
    """
    teacher = current_user.teacher_profile
    
    # Get class and verify it belongs to this teacher
    cls = Class.query.filter_by(
        id=class_id,
        teacher_id=teacher.id
    ).first_or_404()
    
    # Get enrolled students
    enrollments = Enrollment.query.filter_by(
        class_id=class_id,
        status='enrolled'
    ).join(Student).order_by(Student.last_name, Student.first_name).all()
    
    # Get students with their current grades
    students_with_grades = []
    for enrollment in enrollments:
        student = enrollment.student
        
        # Get all grades for this student in this class
        grades = Grade.query.join(Test).filter(
            Test.class_id == class_id,
            Grade.student_id == student.id,
            Grade.final_grade.isnot(None)
        ).all()
        
        # Calculate average grade
        if grades:
            avg_grade = sum(g.final_grade for g in grades) / len(grades)
        else:
            avg_grade = None
        
        students_with_grades.append({
            'student': student,
            'enrollment': enrollment,
            'avg_grade': avg_grade,
            'grade_count': len(grades)
        })
    
    return render_template(
        'teacher/class_detail.html',
        teacher=teacher,
        class_obj=cls,
        students_with_grades=students_with_grades
    )


@teacher_bp.route('/classes/<int:class_id>/formula', methods=['GET'])
@teacher_required
def view_formula(class_id):
    """
    API endpoint to get grading formula for a class
    Used when editing an existing class
    """
    teacher = current_user.teacher_profile
    
    # Verify class belongs to this teacher
    cls = Class.query.filter_by(
        id=class_id,
        teacher_id=teacher.id
    ).first_or_404()
    
    formula = cls.get_grading_formula()
    
    return jsonify({
        'success': True,
        'formula': formula,
        'can_edit': cls.can_edit_formula()
    })


@teacher_bp.route('/classes/<int:class_id>/formula', methods=['POST'])
@teacher_required
def update_formula(class_id):
    """
    API endpoint to update grading formula for a class
    Only allowed if no grades have been entered yet
    """
    teacher = current_user.teacher_profile
    
    # Verify class belongs to this teacher
    cls = Class.query.filter_by(
        id=class_id,
        teacher_id=teacher.id
    ).first_or_404()
    
    # Check if formula can be edited
    if not cls.can_edit_formula():
        return jsonify({
            'success': False,
            'error': 'Cannot edit formula after grades have been entered'
        }), 403
    
    try:
        formula_json = request.json.get('formula')
        
        # Validate and set formula
        cls.set_grading_formula(formula_json)
        db.session.commit()
        
        return jsonify({
            'success': True,
            'message': 'Formula updated successfully'
        })
        
    except ValueError as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 400
    except Exception as e:
        db.session.rollback()
        return jsonify({
            'success': False,
            'error': 'An error occurred while updating the formula'
        }), 500


@teacher_bp.route('/grading')
@teacher_required
def grading():
    """
    Renders the Grading page with year and semester filters (backend filtering).
    Excel-like interface for entering and managing grades.
    """
    teacher = current_user.teacher_profile
    
    current_school_year = Config.get_current_school_year()
    current_semester = Config.get_current_semester()
    
    # ✅ Get filters from query parameters (like classes page)
    selected_year = request.args.get('year')
    selected_semester = request.args.get('semester')
    
    # Build query
    query = Class.query.filter_by(teacher_id=teacher.id)
    
    # ✅ Apply year filter (backend)
    if selected_year and selected_year != 'all':
        query = query.filter_by(school_year=selected_year)
    
    # ✅ Apply semester filter (backend)
    if selected_semester and selected_semester != 'all':
        query = query.filter_by(semester=selected_semester)
    
    # Execute query
    classes = query.order_by(
        Class.school_year.desc(),
        Class.semester
    ).all()
    
    # Build available years list for dropdown (all years with classes)
    all_teacher_classes = Class.query.filter_by(teacher_id=teacher.id).all()
    available_years = sorted(
        list(set([cls.school_year for cls in all_teacher_classes])),
        reverse=True
    )
    
    # Get selected class (from query parameter or first filtered class)
    selected_class_id = request.args.get('class_id', type=int)
    
    if selected_class_id:
        selected_class = Class.query.filter_by(
            id=selected_class_id,
            teacher_id=teacher.id
        ).first()
    else:
        selected_class = classes[0] if classes else None
    
    grading_data = None
    
    if selected_class:
        # Get all students enrolled in this class
        enrollments = Enrollment.query.filter_by(
            class_id=selected_class.id,
            status='enrolled'
        ).join(Student).order_by(Student.last_name, Student.first_name).all()
        
        # Get all tests for this class
        tests = Test.query.filter_by(
            class_id=selected_class.id
        ).order_by(Test.test_date).all()
        
        # Build grading matrix
        students_data = []
        for enrollment in enrollments:
            student = enrollment.student
            
            # Get grades for each test
            test_grades = {}
            for test in tests:
                grade = Grade.query.filter_by(
                    test_id=test.id,
                    student_id=student.id
                ).first()
                
                test_grades[test.id] = grade.final_grade if grade else None
            
            students_data.append({
                'student': student,
                'enrollment': enrollment,
                'test_grades': test_grades
            })
        
        grading_data = {
            'students': students_data,
            'tests': tests
        }
    
    return render_template(
        'teacher/grading.html',
        teacher=teacher,
        classes=classes,
        selected_class=selected_class,
        grading_data=grading_data,
        current_school_year=current_school_year,
        current_semester=current_semester,
        available_years=available_years,
        selected_year=selected_year or 'all',      # ✅ Pass back to template
        selected_semester=selected_semester or 'all'  # ✅ Pass back to template
    )


@teacher_bp.route('/grading/update', methods=['POST'])
@teacher_required
def update_grade():
    """
    API endpoint to update a single grade.
    Used by the Excel-like grading interface.
    """
    teacher = current_user.teacher_profile
    
    # Get data from request
    student_id = request.form.get('student_id', type=int)
    test_id = request.form.get('test_id', type=int)
    grade_value = request.form.get('grade', type=float)
    
    # Verify the test belongs to a class taught by this teacher
    test = Test.query.join(Class).filter(
        Test.id == test_id,
        Class.teacher_id == teacher.id
    ).first_or_404()
    
    # Get or create grade record
    grade = Grade.query.filter_by(
        test_id=test_id,
        student_id=student_id
    ).first()
    
    if not grade:
        grade = Grade(
            test_id=test_id,
            student_id=student_id,
            graded_by=teacher.id
        )
        db.session.add(grade)
    
    # Update grade
    grade.final_grade = grade_value
    grade.calculated_grade = grade_value
    grade.graded_by = teacher.id
    grade.graded_at = datetime.utcnow()
    
    db.session.commit()
    
    # Update enrollment final grade (average)
    enrollment = Enrollment.query.filter_by(
        student_id=student_id,
        class_id=test.class_id
    ).first()
    
    if enrollment:
        all_grades = Grade.query.join(Test).filter(
            Test.class_id == test.class_id,
            Grade.student_id == student_id,
            Grade.final_grade.isnot(None)
        ).all()
        
        if all_grades:
            avg_grade = sum(g.final_grade for g in all_grades) / len(all_grades)
            enrollment.final_grade = round(avg_grade, 2)
            db.session.commit()
    
    return jsonify({'success': True, 'grade': grade_value})


# FIX FOR ERROR: "Could not build url for endpoint 'teacher.create_test'"
@teacher_bp.route('/grading/create-test', methods=['POST'])
@teacher_required
def create_test():
    """
    Create a new test/quiz for a class.
    FIX: This route was missing, causing the BuildError
    """
    teacher = current_user.teacher_profile
    
    try:
        class_id = request.form.get('class_id', type=int)
        title = request.form.get('title', '').strip()
        
        if not class_id or not title:
            flash('Class and title are required.', 'error')
            return redirect(url_for('teacher.grading'))
        
        # Verify class belongs to this teacher
        cls = Class.query.filter_by(
            id=class_id,
            teacher_id=teacher.id
        ).first()
        
        if not cls:
            flash('Class not found or access denied.', 'error')
            return redirect(url_for('teacher.grading'))
        
        # Create test
        new_test = Test(
            class_id=class_id,
            title=title,
            test_date=datetime.utcnow().date()
        )
        
        db.session.add(new_test)
        db.session.commit()
        
        flash(f'Test "{title}" created successfully!', 'success')
        return redirect(url_for('teacher.grading', class_id=class_id))
        
    except Exception as e:
        db.session.rollback()
        flash(f'Error creating test: {str(e)}', 'error')
        return redirect(url_for('teacher.grading'))


@teacher_bp.route('/grading/delete-test', methods=['POST'])
@teacher_required
def delete_test():
    """
    Delete a test and all associated grades.
    """
    teacher = current_user.teacher_profile
    
    try:
        test_id = request.form.get('test_id', type=int)
        
        # Verify test belongs to a class taught by this teacher
        test = Test.query.join(Class).filter(
            Test.id == test_id,
            Class.teacher_id == teacher.id
        ).first()
        
        if not test:
            flash('Test not found or access denied.', 'error')
            return redirect(url_for('teacher.grading'))
        
        class_id = test.class_id
        test_title = test.title
        
        # Delete test (cascades to grades)
        db.session.delete(test)
        db.session.commit()
        
        flash(f'Test "{test_title}" deleted successfully.', 'success')
        return redirect(url_for('teacher.grading', class_id=class_id))
        
    except Exception as e:
        db.session.rollback()
        flash(f'Error deleting test: {str(e)}', 'error')
        return redirect(url_for('teacher.grading'))


# FIX FOR ERROR: "'dict object' has no attribute 'overall_average'"
@teacher_bp.route('/analytics')
@teacher_required
def analytics():
    """
    Renders the Analytics page with comprehensive statistics.
    FIX: Added 'overall_average' key to analytics_data dictionary
    """
    teacher = current_user.teacher_profile
    
    current_school_year = Config.get_current_school_year()
    current_semester = Config.get_current_semester()
    
    # Get all classes for this semester
    classes = Class.query.filter_by(
        teacher_id=teacher.id,
        school_year=current_school_year,
        semester=current_semester
    ).all()
    
    # Calculate total students
    total_students = db.session.query(func.count(func.distinct(Enrollment.student_id)))\
        .join(Class).filter(
            Class.teacher_id == teacher.id,
            Class.school_year == current_school_year,
            Class.semester == current_semester,
            Enrollment.status == 'enrolled'
        ).scalar() or 0
    
    # Calculate new students this semester
    new_students = max(0, total_students - 120)  # Placeholder logic
    
    # Get all grades for this semester
    all_grades = Grade.query.join(Test).join(Class).filter(
        Class.teacher_id == teacher.id,
        Class.school_year == current_school_year,
        Class.semester == current_semester,
        Grade.final_grade.isnot(None)
    ).all()
    
    # Calculate average grade
    if all_grades:
        avg_class_grade = sum(g.final_grade for g in all_grades) / len(all_grades)
    else:
        avg_class_grade = 0.0
    
    # Calculate passing rate
    graded_students = len(all_grades)
    passed_students = sum(1 for g in all_grades if g.final_grade <= 3.0)
    passing_rate = round((passed_students / graded_students * 100) if graded_students > 0 else 0)
    
    # Grade distribution
    grade_distribution = {
        '1.0-1.5': 0,
        '1.75-2.0': 0,
        '2.25-2.5': 0,
        '2.75-3.0': 0,
        '4.0-5.0': 0
    }
    
    for grade in all_grades:
        g = grade.final_grade
        if 1.0 <= g <= 1.5:
            grade_distribution['1.0-1.5'] += 1
        elif 1.75 <= g <= 2.0:
            grade_distribution['1.75-2.0'] += 1
        elif 2.25 <= g <= 2.5:
            grade_distribution['2.25-2.5'] += 1
        elif 2.75 <= g <= 3.0:
            grade_distribution['2.75-3.0'] += 1
        else:
            grade_distribution['4.0-5.0'] += 1
    
    # Class performance breakdown
    class_performance = []
    for cls in classes:
        enrollments = Enrollment.query.filter_by(
            class_id=cls.id,
            status='enrolled'
        ).all()
        
        student_count = len(enrollments)
        
        # Get average grade for this class
        class_grades = Grade.query.join(Test).filter(
            Test.class_id == cls.id,
            Grade.final_grade.isnot(None)
        ).all()
        
        if class_grades:
            avg_grade = sum(g.final_grade for g in class_grades) / len(class_grades)
        else:
            avg_grade = None
        
        class_performance.append({
            'class': cls,
            'student_count': student_count,
            'avg_grade': avg_grade
        })
    
    # Total tests
    total_tests = Test.query.join(Class).filter(
        Class.teacher_id == teacher.id,
        Class.school_year == current_school_year,
        Class.semester == current_semester
    ).count()
    
    # Grading completion
    total_gradable = 0
    graded_count = 0
    
    for cls in classes:
        enrollment_count = Enrollment.query.filter_by(
            class_id=cls.id,
            status='enrolled'
        ).count()
        
        test_count = Test.query.filter_by(class_id=cls.id).count()
        total_gradable += enrollment_count * test_count
        
        graded_count += Grade.query.join(Test).filter(
            Test.class_id == cls.id,
            Grade.final_grade.isnot(None)
        ).count()
    
    completion_rate = round((graded_count / total_gradable * 100) if total_gradable > 0 else 0)
    ungraded_count = total_gradable - graded_count
    
    # Total units
    total_units = sum(cls.units for cls in classes)
    
    # FIX: Added 'overall_average' key - this was causing the error
    analytics_data = {
        'total_students': total_students,
        'new_students': new_students,
        'avg_class_grade': avg_class_grade,
        'overall_average': avg_class_grade,  # ← FIX: This key was missing
        'grade_trend': 0.15,  # Placeholder
        'passing_rate': passing_rate,
        'passed_students': passed_students,
        'graded_students': graded_students,
        'completion_rate': completion_rate,
        'graded_count': graded_count,
        'total_gradable': total_gradable,
        'grade_distribution': grade_distribution,
        'class_performance': class_performance,
        'total_tests': total_tests,
        'avg_tests_per_class': round(total_tests / len(classes), 1) if classes else 0,
        'ungraded_count': ungraded_count,
        'total_classes': len(classes),
        'total_units': total_units
    }
    
    return render_template(
        'teacher/analytics.html',
        teacher=teacher,
        classes=classes,
        analytics=analytics_data,  # Now includes 'overall_average'
        current_school_year=current_school_year,
        current_semester=current_semester
    )


@teacher_bp.route('/profile')
@teacher_required
def profile():
    """
    Renders the Teacher Profile page.
    Shows teacher information and allows profile updates.
    """
    teacher = current_user.teacher_profile
    
    # Get teaching stats
    total_classes = Class.query.filter_by(teacher_id=teacher.id).count()

    current_students = db.session.query(func.count(func.distinct(Enrollment.student_id)))\
        .join(Class).filter(
            Class.teacher_id == teacher.id,
            Class.school_year == Config.get_current_school_year(),
            Class.semester == Config.get_current_semester(),
            Enrollment.status == 'enrolled'
        ).scalar() or 0
    
    # Total grades given
    total_grades_given = Grade.query.join(Test).join(Class).filter(
        Class.teacher_id == teacher.id,
        Grade.final_grade.isnot(None)
    ).count()
    
    # Calculate years teaching (based on account creation)
    years_teaching = max(1, (datetime.utcnow() - teacher.created_at).days // 365) if teacher.created_at else 1
    
    # Recent activity
    recent_grades = Grade.query.join(Test).join(Class).filter(
        Class.teacher_id == teacher.id,
        Grade.graded_at.isnot(None)
    ).order_by(Grade.graded_at.desc()).limit(10).all()
    
    recent_activities = []
    for grade in recent_grades:
        time_diff = datetime.utcnow() - grade.graded_at
        
        if time_diff < timedelta(minutes=60):
            time_ago = f"{time_diff.seconds // 60} minutes ago"
        elif time_diff < timedelta(hours=24):
            time_ago = f"{time_diff.seconds // 3600} hours ago"
        else:
            time_ago = f"{time_diff.days} days ago"
        
        recent_activities.append({
            'description': f"Graded {grade.student.get_full_name()} in {grade.test.class_.effective_subject_code}",
            'time_ago': time_ago
        })
            
    # If no recent grading activity, show placeholder
    if not recent_activities:
        recent_activities = [
            {'description': 'No recent grading activity', 'time_ago': 'Start grading to see activity here'}
        ]
    
    stats = {
        'total_classes': total_classes,
        'current_students': current_students,
        'total_grades_given': total_grades_given,
        'years_teaching': years_teaching
    }
    
    return render_template(
        'teacher/profile.html',
        teacher=teacher,
        stats=stats,
        recent_activities=recent_activities
    )

@teacher_bp.route('/change-password', methods=['POST'])
@teacher_required
def change_password():
    """Change teacher's password"""
    try:
        current_password = request.form.get('current_password', '').strip()
        new_password = request.form.get('new_password', '').strip()
        confirm_password = request.form.get('confirm_password', '').strip()
        
        # Validation
        if not all([current_password, new_password, confirm_password]):
            flash('All fields are required.', 'error')
            return redirect(url_for('teacher.profile'))
        
        # Check if new passwords match
        if new_password != confirm_password:
            flash('New passwords do not match.', 'error')
            return redirect(url_for('teacher.profile'))
        
        # Check password length
        if len(new_password) < 6:
            flash('Password must be at least 6 characters long.', 'error')
            return redirect(url_for('teacher.profile'))
        
        # Verify current password
        if not bcrypt.check_password_hash(current_user.password, current_password):
            flash('Current password is incorrect.', 'error')
            return redirect(url_for('teacher.profile'))
        
        # Update password
        current_user.password = bcrypt.generate_password_hash(new_password).decode('utf-8')
        db.session.commit()
        
        flash('✅ Password updated successfully!', 'success')
        return redirect(url_for('teacher.profile'))
        
    except Exception as e:
        db.session.rollback()
        flash(f'❌ Error updating password: {str(e)}', 'error')
        return redirect(url_for('teacher.profile'))


"""
NEW ROUTES TO ADD TO blueprints/teacher/routes.py
Add these routes to your existing routes.py file
"""

@teacher_bp.route('/grading/components', methods=['GET'])
@teacher_required
def get_components():
    """
    API endpoint to get component scores for a student/test
    """
    teacher = current_user.teacher_profile
    
    student_id = request.args.get('student_id', type=int)
    test_id = request.args.get('test_id', type=int)
    
    # Verify test belongs to teacher's class
    test = Test.query.join(Class).filter(
        Test.id == test_id,
        Class.teacher_id == teacher.id
    ).first_or_404()
    
    # Get existing grade
    grade = Grade.query.filter_by(
        test_id=test_id,
        student_id=student_id
    ).first()
    
    if grade:
        components = grade.get_component_scores()
    else:
        components = {}
    
    return jsonify({
        'success': True,
        'components': components
    })


@teacher_bp.route('/grading/update-components', methods=['POST'])
@teacher_required
def update_components():
    """
    API endpoint to save component scores (Option B)
    Automatically calculates final grade
    """
    teacher = current_user.teacher_profile
    
    try:
        data = request.get_json()
        student_id = data.get('student_id')
        test_id = data.get('test_id')
        components = data.get('components', {})
        
        # Verify test belongs to teacher's class
        test = Test.query.join(Class).filter(
            Test.id == test_id,
            Class.teacher_id == teacher.id
        ).first_or_404()
        
        # Get or create grade
        grade = Grade.query.filter_by(
            test_id=test_id,
            student_id=student_id
        ).first()
        
        if not grade:
            grade = Grade(
                test_id=test_id,
                student_id=student_id,
                graded_by=teacher.id
            )
            db.session.add(grade)
        
        # Save component scores
        grade.set_component_scores(components)
        
        # Calculate final grade using Option B logic
        grade.calculate_grade(test.class_)
        
        grade.graded_by = teacher.id
        grade.graded_at = datetime.utcnow()
        
        db.session.commit()
        
        # Update enrollment final grade (average of all tests)
        update_enrollment_average(student_id, test.class_id)
        
        return jsonify({
            'success': True,
            'final_grade': grade.final_grade,
            'calculated_percentage': grade.calculated_percentage
        })
        
    except Exception as e:
        db.session.rollback()
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@teacher_bp.route('/grading/student-average', methods=['GET'])
@teacher_required
def get_student_average():
    """
    API endpoint to get updated student average for a class
    """
    teacher = current_user.teacher_profile
    
    student_id = request.args.get('student_id', type=int)
    class_id = request.args.get('class_id', type=int)
    
    # Verify class belongs to teacher
    cls = Class.query.filter_by(
        id=class_id,
        teacher_id=teacher.id
    ).first_or_404()
    
    # Get enrollment
    enrollment = Enrollment.query.filter_by(
        student_id=student_id,
        class_id=class_id
    ).first()
    
    if not enrollment:
        return jsonify({
            'success': False,
            'error': 'Enrollment not found'
        }), 404
    
    # Calculate average from all tests
    average = calculate_class_average(student_id, class_id)
    
    # Update enrollment
    enrollment.final_grade = average
    db.session.commit()
    
    return jsonify({
        'success': True,
        'average': average
    })


def calculate_class_average(student_id, class_id):
    """
    Helper function to calculate student's average grade for a class
    """
    # Get all grades for this student in this class
    all_grades = Grade.query.join(Test).filter(
        Test.class_id == class_id,
        Grade.student_id == student_id,
        Grade.final_grade.isnot(None)
    ).all()
    
    if not all_grades:
        return None
    
    # Simple average of all test grades
    total = sum(g.final_grade for g in all_grades)
    return round(total / len(all_grades), 2)


def update_enrollment_average(student_id, class_id):
    """
    Helper function to update enrollment average after grade change
    """
    enrollment = Enrollment.query.filter_by(
        student_id=student_id,
        class_id=class_id
    ).first()
    
    if enrollment:
        average = calculate_class_average(student_id, class_id)
        enrollment.final_grade = average
        db.session.commit()