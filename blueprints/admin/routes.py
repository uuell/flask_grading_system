"""
blueprints/admin/routes.py - Admin Blueprint
Backend routes for your gold-themed admin dashboard
"""

from flask import Blueprint, render_template, redirect, url_for, flash, request, make_response
from flask_login import login_required, current_user
from models import User, Student, Teacher
from extensions import db, bcrypt
from config import Config
from sqlalchemy import func
from datetime import datetime
from functools import wraps
import csv
import io

admin_bp = Blueprint('admin', __name__)


def admin_required(f):
    """Ensure only admins can access the route"""
    @wraps(f)
    @login_required
    def decorated_function(*args, **kwargs):
        if current_user.role != 'admin':
            flash('Access denied. Admins only.', 'danger')
            return redirect(url_for('index'))
        return f(*args, **kwargs)
    return decorated_function


@admin_bp.route('/dashboard')
@admin_required
def dashboard():
    """Admin Dashboard - Main page"""
    total_students = Student.query.count()
    total_teachers = Teacher.query.count()
    
    # New users today
    today_start = datetime.utcnow().replace(hour=0, minute=0, second=0, microsecond=0)
    new_today = User.query.filter(User.created_at >= today_start).count()
    
    # Department stats
    students_by_dept = db.session.query(
        Student.department, func.count(Student.id)
    ).group_by(Student.department).all()
    
    departments = []
    for dept_name, student_count in students_by_dept:
        teacher_count = Teacher.query.filter_by(department=dept_name).count()
        departments.append({
            'name': dept_name,
            'student_count': student_count,
            'teacher_count': teacher_count
        })
    
    # Recent users
    recent_users = []
    for student in Student.query.order_by(Student.created_at.desc()).limit(5).all():
        initials = f"{student.first_name[0]}{student.last_name[0]}" if student.last_name else student.first_name[0]
        recent_users.append({
            'name': student.get_full_name(),
            'email': student.user.email,
            'id_number': student.student_number,
            'role': 'Student',
            'initials': initials,
            'date_added': student.created_at.strftime('%b %d, %Y') if student.created_at else 'N/A',
            'status': 'Active'
        })
    
    for teacher in Teacher.query.order_by(Teacher.created_at.desc()).limit(5).all():
        initials = f"{teacher.first_name[0]}{teacher.last_name[0]}" if teacher.last_name else teacher.first_name[0]
        recent_users.append({
            'name': teacher.get_full_name(),
            'email': teacher.user.email,
            'id_number': teacher.employee_number,
            'role': 'Teacher',
            'initials': initials,
            'date_added': teacher.created_at.strftime('%b %d, %Y') if teacher.created_at else 'N/A',
            'status': 'Active'
        })
    
    recent_users.sort(key=lambda x: x['date_added'], reverse=True)
    
    # Department stats for new structure
    dept_stats = {}
    for dept_code in ['CoEng', 'COS', 'COE', 'CIT']:
        dept_stats[dept_code] = Student.query.filter_by(department=dept_code).count()
    
    return render_template(
        'admin/dashboard.html',
        total_students=total_students,
        total_teachers=total_teachers,
        new_today=new_today,
        departments=departments,
        dept_stats=dept_stats,
        recent_users=recent_users[:10]
    )


@admin_bp.route('/register-student', methods=['POST'])
@admin_required
def register_student():
    """Register single student"""
    try:
        full_name = request.form.get('full_name', '').strip()
        student_number = request.form.get('student_number', '').strip()
        email = request.form.get('email', '').strip().lower()
        department = request.form.get('department', '').strip()
        program = request.form.get('program', '').strip()
        year_level = request.form.get('year_level', '').strip()
        section = request.form.get('section', '').strip()
        
        name_parts = full_name.split(' ', 1)
        first_name = name_parts[0]
        last_name = name_parts[1] if len(name_parts) > 1 else ''
        
        if not all([full_name, student_number, email, program]):
            flash('❌ Please fill in all required fields.', 'danger')
            return redirect(url_for('admin.dashboard'))
        
        # Handle password
        password = student_number  # Default to student number
        
        if User.query.filter_by(email=email).first():
            flash('❌ Email already exists.', 'danger')
            return redirect(url_for('admin.dashboard'))
        
        if Student.query.filter_by(student_number=student_number).first():
            flash('❌ Student number already exists.', 'danger')
            return redirect(url_for('admin.dashboard'))
        
        user = User(
            email=email,
            password=bcrypt.generate_password_hash(password).decode('utf-8'),
            role='student'
        )
        db.session.add(user)
        db.session.flush()
        
        student = Student(
            user_id=user.id,
            student_number=student_number,
            first_name=first_name,
            last_name=last_name,
            department=department,
            program=program,
            year_level=year_level,
            section=section if section else None
        )
        db.session.add(student)
        db.session.commit()
        
        pwd_msg = "Student ID" if not request.form.get('password') else "custom password"
        flash(f'✅ Student {full_name} registered! Password: {pwd_msg}', 'success')
        return redirect(url_for('admin.dashboard'))
        
    except Exception as e:
        db.session.rollback()
        flash(f'❌ Error: {str(e)}', 'danger')
        return redirect(url_for('admin.dashboard'))


@admin_bp.route('/register-teacher', methods=['POST'])
@admin_required
def register_teacher():
    """Register single teacher"""
    try:
        full_name = request.form.get('full_name', '').strip()
        employee_number = request.form.get('employee_number', '').strip()
        email = request.form.get('email', '').strip().lower()
        password = request.form.get('password', '').strip()
        confirm_password = request.form.get('confirm_password', '').strip()
        department = request.form.get('department', '').strip()
        
        name_parts = full_name.split(' ', 1)
        first_name = name_parts[0]
        last_name = name_parts[1] if len(name_parts) > 1 else ''
        
        if not all([full_name, employee_number, email, department]):
            flash('❌ Please fill in all required fields.', 'danger')
            return redirect(url_for('admin.dashboard'))
        
        # Handle password
        if password:
            if password != confirm_password:
                flash('❌ Passwords do not match.', 'danger')
                return redirect(url_for('admin.dashboard'))
            if len(password) < 6:
                flash('❌ Password must be at least 6 characters.', 'danger')
                return redirect(url_for('admin.dashboard'))
        else:
            password = employee_number  # Default to employee number
        
        if User.query.filter_by(email=email).first():
            flash('❌ Email already exists.', 'danger')
            return redirect(url_for('admin.dashboard'))
        
        if Teacher.query.filter_by(employee_number=employee_number).first():
            flash('❌ Employee number already exists.', 'danger')
            return redirect(url_for('admin.dashboard'))
        
        user = User(
            email=email,
            password=bcrypt.generate_password_hash(password).decode('utf-8'),
            role='teacher'
        )
        db.session.add(user)
        db.session.flush()
        
        teacher = Teacher(
            user_id=user.id,
            employee_number=employee_number,
            first_name=first_name,
            last_name=last_name,
            department=department
        )
        db.session.add(teacher)
        db.session.commit()
        
        pwd_msg = "Employee ID" if not request.form.get('password') else "custom password"
        flash(f'✅ Teacher {full_name} registered! Password: {pwd_msg}', 'success')
        return redirect(url_for('admin.dashboard'))
        
    except Exception as e:
        db.session.rollback()
        flash(f'❌ Error: {str(e)}', 'danger')
        return redirect(url_for('admin.dashboard'))


@admin_bp.route('/bulk-import-students', methods=['POST'])
@admin_required
def bulk_import_students():
    try:
        if 'csv_file' not in request.files:
            flash('No file uploaded.', 'danger')
            return redirect(url_for('admin.dashboard'))
        
        file = request.files['csv_file']
        if not file or file.filename == '':
            flash('❌ No file selected.', 'danger')
            return redirect(url_for('admin.dashboard'))

        if not file.filename.endswith('.csv'):
            flash('Please upload CSV file.', 'danger')
            return redirect(url_for('admin.dashboard'))
        
        stream = io.StringIO(file.stream.read().decode("UTF8"), newline=None)
        csv_reader = csv.DictReader(stream)
        
        success_count = 0
        error_count = 0
        error_details = []
        
        for row_num, row in enumerate(csv_reader, start=2):
            try:
                # Get data from CSV
                full_name = row.get('Full Name', '').strip()
                student_number = row.get('Student Number', '').strip()
                email = row.get('Email', '').strip().lower()
                department = row.get('Department', '').strip()
                program = row.get('Program', '').strip()
                year_level = row.get('Year Level', '1st Year').strip()  # Default to 1st Year
                section = row.get('Section', '').strip()
                
                # Validation
                if not all([full_name, student_number, email, department, program]):
                    error_count += 1
                    error_details.append(f"Row {row_num}: Missing required fields")
                    continue
                
                # Check existing email
                if User.query.filter_by(email=email).first():
                    error_count += 1
                    error_details.append(f"Row {row_num}: Email {email} already exists")
                    continue
                
                # Check existing student number
                if Student.query.filter_by(student_number=student_number).first():
                    error_count += 1
                    error_details.append(f"Row {row_num}: Student number {student_number} already exists")
                    continue
                
                # Parse name
                name_parts = full_name.split(' ', 1)
                first_name = name_parts[0]
                last_name = name_parts[1] if len(name_parts) > 1 else ''
                
                # Create user account
                user = User(
                    email=email,
                    password=bcrypt.generate_password_hash(student_number).decode('utf-8'),
                    role='student'
                )
                db.session.add(user)
                db.session.flush()
                
                # Create student profile
                student = Student(
                    user_id=user.id,
                    student_number=student_number,
                    first_name=first_name,
                    last_name=last_name,
                    department=department,
                    program=program,
                    year_level=year_level,
                    section=section if section else None
                )
                db.session.add(student)
                success_count += 1
                
            except Exception as e:
                error_count += 1
                error_details.append(f"Row {row_num}: {str(e)}")
                continue
        
        # Commit all successful imports
        db.session.commit()
        
        # Show results
        if success_count > 0:
            flash(f'✅ Successfully imported {success_count} student(s)!', 'success')
        if error_count > 0:
            flash(f'⚠️ {error_count} row(s) had errors.', 'danger')
            for error in error_details[:5]:  # Show first 5 errors
                flash(f'• {error}', 'danger')
        
        return redirect(url_for('admin.dashboard'))
        
    except Exception as e:
        db.session.rollback()
        flash(f'❌ Import failed: {str(e)}', 'danger')
        return redirect(url_for('admin.dashboard'))


@admin_bp.route('/bulk-import-teachers', methods=['POST'])
@admin_required
def bulk_import_teachers():
    try:
        if 'csv_file' not in request.files:
            flash('No file uploaded.', 'danger')
            return redirect(url_for('admin.dashboard'))
        
        file = request.files['csv_file']
        if not file or file.filename == '':
            flash('❌ No file selected.', 'danger')
            return redirect(url_for('admin.dashboard'))
            
        if not file.filename.endswith('.csv'):
            flash('Please upload CSV file.', 'danger')
            return redirect(url_for('admin.dashboard'))
        
        stream = io.StringIO(file.stream.read().decode("UTF8"), newline=None)
        csv_reader = csv.DictReader(stream)
        
        success_count = 0
        error_count = 0
        error_details = []
        
        for row_num, row in enumerate(csv_reader, start=2):
            try:
                full_name = row.get('Full Name', '').strip()
                employee_number = row.get('Employee Number', '').strip()
                email = row.get('Email', '').strip().lower()
                department = row.get('Department', '').strip()
                specialization = row.get('Specialization', '').strip()
                
                if not all([full_name, employee_number, email, department]):
                    error_count += 1
                    error_details.append(f"Row {row_num}: Missing required fields")
                    continue
                
                if User.query.filter_by(email=email).first():
                    error_count += 1
                    error_details.append(f"Row {row_num}: Email {email} already exists")
                    continue
                
                if Teacher.query.filter_by(employee_number=employee_number).first():
                    error_count += 1
                    error_details.append(f"Row {row_num}: Employee number {employee_number} already exists")
                    continue
                
                name_parts = full_name.split(' ', 1)
                user = User(
                    email=email,
                    password=bcrypt.generate_password_hash(employee_number).decode('utf-8'),
                    role='teacher'
                )
                db.session.add(user)
                db.session.flush()
                
                teacher = Teacher(
                    user_id=user.id,
                    employee_number=employee_number,
                    first_name=name_parts[0],
                    last_name=name_parts[1] if len(name_parts) > 1 else '',
                    department=department,
                    specialization=specialization if specialization else None
                )
                db.session.add(teacher)
                success_count += 1
                
            except Exception as e:
                error_count += 1
                error_details.append(f"Row {row_num}: {str(e)}")
                continue
        
        db.session.commit()
        
        if success_count > 0:
            flash(f'✅ Successfully imported {success_count} teacher(s)!', 'success')
        if error_count > 0:
            flash(f'⚠️ {error_count} row(s) had errors.', 'danger')
            for error in error_details[:5]:
                flash(f'• {error}', 'danger')
        
        return redirect(url_for('admin.dashboard'))
        
    except Exception as e:
        db.session.rollback()
        flash(f'❌ Import failed: {str(e)}', 'danger')
        return redirect(url_for('admin.dashboard'))


@admin_bp.route('/download/student-template')
@admin_required
def download_student_template():
    """Download student CSV template"""
    csv_content = "Full Name,Student Number,Email,Department,Program\n"
    csv_content += "Juan Dela Cruz,2024-0001,juan@student.acadify.edu,CoEng,BS Computer Science\n"
    csv_content += "Maria Santos,2024-0002,maria@student.acadify.edu,COS,BS Biology\n"
    
    response = make_response(csv_content)
    response.headers["Content-Disposition"] = "attachment; filename=student_template.csv"
    response.headers["Content-Type"] = "text/csv"
    return response


@admin_bp.route('/download/teacher-template')
@admin_required
def download_teacher_template():
    """Download teacher CSV template"""
    csv_content = "Full Name,Employee Number,Email,Department,Specialization\n"
    csv_content += "Dr. Pedro Reyes,EMP-2024-001,pedro@faculty.acadify.edu,CoEng,Computer Engineering\n"
    csv_content += "Prof. Ana Cruz,EMP-2024-002,ana@faculty.acadify.edu,COS,Biology\n"
    
    response = make_response(csv_content)
    response.headers["Content-Disposition"] = "attachment; filename=teacher_template.csv"
    response.headers["Content-Type"] = "text/csv"
    return response


@admin_bp.route('/user-management')
@admin_required
def user_management():
    """User management page with pagination"""
    import json
    
    # Get page number from query params (default to 1)
    page = request.args.get('page', 1, type=int)
    per_page = 20  # Items per page
    
    # Get filter parameters
    role_filter = request.args.get('role', '')
    dept_filter = request.args.get('department', '')
    search_query = request.args.get('search', '')
    
    # Query students
    student_query = Student.query.order_by(Student.last_name, Student.first_name)
    
    # Query teachers
    teacher_query = Teacher.query.order_by(Teacher.last_name, Teacher.first_name)
    
    # Get all for counts and filters
    all_students = student_query.all()
    all_teachers = teacher_query.all()
    
    # Combine into single user list for pagination
    all_users = []
    
    for student in all_students:
        initials = f"{student.first_name[0]}{student.last_name[0]}" if student.last_name else student.first_name[0]
        all_users.append({
            'user_id': student.user_id,
            'name': student.get_full_name(),
            'email': student.user.email,
            'department': student.department,
            'id_number': student.student_number,
            'role': 'Student',
            'initials': initials,
            'created_date': student.created_at.strftime('%b %d, %Y') if student.created_at else 'N/A',
            'program': student.program
        })
    
    for teacher in all_teachers:
        initials = f"{teacher.first_name[0]}{teacher.last_name[0]}" if teacher.last_name else teacher.first_name[0]
        all_users.append({
            'user_id': teacher.user_id,
            'name': teacher.get_full_name(),
            'email': teacher.user.email,
            'department': teacher.department,
            'id_number': teacher.employee_number,
            'role': 'Teacher',
            'initials': initials,
            'created_date': teacher.created_at.strftime('%b %d, %Y') if teacher.created_at else 'N/A',
            'program': None
        })
    
    # Apply filters
    filtered_users = all_users
    
    if role_filter:
        filtered_users = [u for u in filtered_users if u['role'] == role_filter]
    
    if dept_filter:
        filtered_users = [u for u in filtered_users if u['department'] == dept_filter]
    
    if search_query:
        search_lower = search_query.lower()
        filtered_users = [u for u in filtered_users if 
                         search_lower in u['name'].lower() or 
                         search_lower in u['email'].lower() or 
                         search_lower in u['id_number'].lower()]
    
    # Calculate pagination
    total_users = len(filtered_users)
    total_pages = (total_users + per_page - 1) // per_page  # Ceiling division
    
    # Get users for current page
    start_idx = (page - 1) * per_page
    end_idx = start_idx + per_page
    paginated_users = filtered_users[start_idx:end_idx]
    
    # Get unique departments for filter
    departments = list(set([u['department'] for u in all_users]))
    departments.sort()
    
    # Calculate pagination range
    page_range = []
    if total_pages <= 7:
        page_range = list(range(1, total_pages + 1))
    else:
        if page <= 4:
            page_range = list(range(1, 6)) + ['...', total_pages]
        elif page >= total_pages - 3:
            page_range = [1, '...'] + list(range(total_pages - 4, total_pages + 1))
        else:
            page_range = [1, '...'] + list(range(page - 1, page + 2)) + ['...', total_pages]
    
    return render_template(
        'admin/user_management.html',
        users=paginated_users,
        users_json=json.dumps(paginated_users),
        total_users=total_users,
        departments=departments,
        current_page=page,
        total_pages=total_pages,
        page_range=page_range,
        has_prev=page > 1,
        has_next=page < total_pages,
        per_page=per_page,
        start_idx=start_idx + 1,
        end_idx=min(end_idx, total_users),
        role_filter=role_filter,
        dept_filter=dept_filter,
        search_query=search_query
    )


@admin_bp.route('/delete-user/<int:user_id>', methods=['POST'])
@admin_required
def delete_user(user_id):
    """Delete a user (student or teacher) from the database"""
    try:
        user = User.query.get_or_404(user_id)
        
        # Get user name for flash message
        if user.role == 'student':
            student = Student.query.filter_by(user_id=user_id).first()
            user_name = student.get_full_name() if student else "Student"
        elif user.role == 'teacher':
            teacher = Teacher.query.filter_by(user_id=user_id).first()
            user_name = teacher.get_full_name() if teacher else "Teacher"
        else:
            user_name = "User"
        
        # Delete user (cascades to student/teacher profile)
        db.session.delete(user)
        db.session.commit()
        
        flash(f'✅ {user_name} has been removed from the system.', 'success')
        return redirect(url_for('admin.user_management'))
        
    except Exception as e:
        db.session.rollback()
        flash(f'❌ Error deleting user: {str(e)}', 'danger')
        return redirect(url_for('admin.user_management'))


@admin_bp.route('/reset-password/<int:user_id>', methods=['POST'])
@admin_required
def reset_password(user_id):
    """Reset user password to their ID number"""
    try:
        user = User.query.get_or_404(user_id)
        
        # Generate new password based on user type
        if user.role == 'student':
            student = Student.query.filter_by(user_id=user_id).first()
            if student:
                new_password = student.student_number
                user_name = student.get_full_name()
            else:
                flash('Student not found.', 'danger')
                return redirect(url_for('admin.user_management'))
        elif user.role == 'teacher':
            teacher = Teacher.query.filter_by(user_id=user_id).first()
            if teacher:
                new_password = teacher.employee_number
                user_name = teacher.get_full_name()
            else:
                flash('Teacher not found.', 'danger')
                return redirect(url_for('admin.user_management'))
        else:
            flash('Cannot reset password for this user type.', 'danger')
            return redirect(url_for('admin.user_management'))
        
        # Update password
        user.password = bcrypt.generate_password_hash(new_password).decode('utf-8')
        db.session.commit()
        
        flash(f'✅ Password reset for {user_name}. New password: {new_password}', 'success')
        return redirect(url_for('admin.user_management'))
        
    except Exception as e:
        db.session.rollback()
        flash(f'❌ Error resetting password: {str(e)}', 'danger')
        return redirect(url_for('admin.user_management'))


@admin_bp.route('/export-users-csv')
@admin_required
def export_users_csv():
    """Export all users to CSV"""
    import io
    from flask import Response
    
    # Get all users
    students = Student.query.all()
    teachers = Teacher.query.all()
    
    # Create CSV content
    output = io.StringIO()
    output.write('Name,Email,Role,ID Number,Department,Program,Created Date\n')
    
    for student in students:
        output.write(f'"{student.get_full_name()}",')
        output.write(f'"{student.user.email}",')
        output.write(f'"Student",')
        output.write(f'"{student.student_number}",')
        output.write(f'"{student.department}",')
        output.write(f'"{student.program}",')
        output.write(f'"{student.created_at.strftime("%Y-%m-%d") if student.created_at else "N/A"}"\n')
    
    for teacher in teachers:
        output.write(f'"{teacher.get_full_name()}",')
        output.write(f'"{teacher.user.email}",')
        output.write(f'"Teacher",')
        output.write(f'"{teacher.employee_number}",')
        output.write(f'"{teacher.department}",')
        output.write(f'"N/A",')
        output.write(f'"{teacher.created_at.strftime("%Y-%m-%d") if teacher.created_at else "N/A"}"\n')
    
    # Create response
    response = make_response(output.getvalue())
    response.headers['Content-Disposition'] = 'attachment; filename=acadify_users_export.csv'
    response.headers['Content-Type'] = 'text/csv'
    
    return response


@admin_bp.route('/settings', methods=['GET', 'POST'])
@admin_required
def settings():
    """System settings page with year/semester management"""
    from models import SystemSettings
    
    if request.method == 'POST':
        action = request.form.get('action')
        
        if action == 'update_academic':
            # Update academic year settings
            school_year = request.form.get('school_year', '').strip()
            semester = request.form.get('semester', '').strip()
            
            # Validate school year format
            import re
            if not re.match(r'^\d{4}-\d{4}$', school_year):
                flash('❌ Invalid school year format. Use YYYY-YYYY (e.g., 2024-2025)', 'danger')
                return redirect(url_for('admin.settings'))
            
            # Validate consecutive years
            start_year, end_year = map(int, school_year.split('-'))
            if end_year != start_year + 1:
                flash('❌ School year must be consecutive (e.g., 2024-2025, not 2024-2026)', 'danger')
                return redirect(url_for('admin.settings'))
            
            # Save to database
            SystemSettings.set_setting('current_school_year', school_year, current_user.email)
            SystemSettings.set_setting('current_semester', semester, current_user.email)
            
            flash(f'✅ Academic year updated to {school_year}, {semester}', 'success')
            return redirect(url_for('admin.settings'))
        
        elif action == 'reset_to_auto':
            # Delete settings to revert to auto-calculation
            SystemSettings.delete_setting('current_school_year')
            SystemSettings.delete_setting('current_semester')
            
            flash('✅ Reverted to automatic calculation based on current date', 'success')
            return redirect(url_for('admin.settings'))
    
    # GET request - display settings
    
    # Get current values (either from DB or auto-calculated)
    current_year = Config.get_current_school_year()
    current_semester = Config.get_current_semester()
    
    # Check if values are from database (manual) or auto-calculated
    db_year = SystemSettings.get_setting('current_school_year')
    db_semester = SystemSettings.get_setting('current_semester')
    
    is_manual = db_year is not None and db_semester is not None
    
    # Get auto-calculated values for comparison
    auto_year = Config._auto_calculate_school_year()
    auto_semester = Config._auto_calculate_semester()
    
    # Get last updated info if manual
    last_updated = None
    updated_by = None
    if is_manual:
        year_setting = SystemSettings.query.filter_by(setting_key='current_school_year').first()
        if year_setting:
            last_updated = year_setting.updated_at
            updated_by = year_setting.updated_by
    
    return render_template(
        'admin/settings.html',
        current_year=current_year,
        current_semester=current_semester,
        is_manual=is_manual,
        auto_year=auto_year,
        auto_semester=auto_semester,
        last_updated=last_updated,
        updated_by=updated_by
    )