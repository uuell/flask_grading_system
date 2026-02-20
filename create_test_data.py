"""
create_test_data.py - Populate Database with Test Data
Run this script to create sample teachers, students, classes, and grades for testing.

Usage: python create_test_data.py
"""

from app import create_app
from extensions import db, bcrypt
from models import User, Student, Teacher, Subject, Class, Enrollment, Test, Grade
from datetime import datetime, date, timedelta
import random

def create_test_data():
    """Create comprehensive test data for the Acadify system"""
    
    app = create_app('development')
    
    with app.app_context():
        print("🗑️  Clearing existing data...")
        # Clear existing data (be careful with this in production!)
        Grade.query.delete()
        Test.query.delete()
        Enrollment.query.delete()
        Class.query.delete()
        Subject.query.delete()
        Student.query.delete()
        Teacher.query.delete()
        User.query.delete()
        db.session.commit()
        
        print("👨‍🏫 Creating Teachers...")
        # Create teacher users
        teacher_users_data = [
            {
                'email': 'prof.santos@acadify.edu',
                'password': 'teacher123',
                'first_name': 'Maria',
                'last_name': 'Santos',
                'employee_number': 'T-2024-001',
                'department': 'College of Engineering',
                'specialization': 'Computer Science'
            },
            {
                'email': 'prof.mendoza@acadify.edu',
                'password': 'teacher123',
                'first_name': 'Antonio',
                'last_name': 'Mendoza',
                'employee_number': 'T-2024-002',
                'department': 'College of Engineering',
                'specialization': 'Data Science'
            },
            {
                'email': 'prof.garcia@acadify.edu',
                'password': 'teacher123',
                'first_name': 'Elena',
                'last_name': 'Garcia',
                'employee_number': 'T-2024-003',
                'department': 'College of Engineering',
                'specialization': 'Software Engineering'
            }
        ]
        
        teachers = []
        for data in teacher_users_data:
            # Create user account
            user = User(
                email=data['email'],
                password=bcrypt.generate_password_hash(data['password']).decode('utf-8'),
                role='teacher'
            )
            db.session.add(user)
            db.session.flush()
            
            # Create teacher profile
            teacher = Teacher(
                user_id=user.id,
                employee_number=data['employee_number'],
                first_name=data['first_name'],
                last_name=data['last_name'],
                department=data['department'],
                specialization=data['specialization']
            )
            db.session.add(teacher)
            teachers.append(teacher)
        
        db.session.commit()
        print(f"   ✅ Created {len(teachers)} teachers")
        
        print("👨‍🎓 Creating Students...")
        # Create student users
        student_first_names = ['Juan', 'Maria', 'Pedro', 'Ana', 'Jose', 'Sofia', 'Miguel', 'Isabella', 'Carlos', 'Lucia',
                              'Diego', 'Valentina', 'Luis', 'Carmen', 'Roberto', 'Elena', 'Fernando', 'Paula', 'Ricardo', 'Beatriz']
        student_last_names = ['Dela Cruz', 'Santos', 'Reyes', 'Garcia', 'Lopez', 'Martinez', 'Gonzales', 'Rodriguez', 'Hernandez', 'Perez']
        
        students = []
        for i in range(30):  # Create 30 students
            first_name = random.choice(student_first_names)
            last_name = random.choice(student_last_names)
            
            # Create user account
            user = User(
                email=f'student{i+1}@acadify.edu',
                password=bcrypt.generate_password_hash('student123').decode('utf-8'),
                role='student'
            )
            db.session.add(user)
            db.session.flush()
            
            # Create student profile
            student = Student(
                user_id=user.id,
                student_number=f'2024-{str(i+1).zfill(5)}',
                first_name=first_name,
                last_name=last_name,
                department='College of Engineering',
                program='BS Computer Science',
                year_level=random.choice(['1st Year', '2nd Year', '3rd Year', '4th Year']),
                section=random.choice(['A', 'B', 'C', None])
            )
            db.session.add(student)
            students.append(student)
        
        db.session.commit()
        print(f"   ✅ Created {len(students)} students")
        
        print("📚 Creating Subjects...")
        # Create subjects
        subjects_data = [
            {'code': 'CS101', 'name': 'Introduction to Computing', 'units': 3, 'is_major': True},
            {'code': 'CS201', 'name': 'Data Structures & Algorithms', 'units': 3, 'is_major': True},
            {'code': 'CS202', 'name': 'Object-Oriented Programming', 'units': 3, 'is_major': True},
            {'code': 'CS205', 'name': 'Discrete Mathematics', 'units': 3, 'is_major': True},
            {'code': 'CS301', 'name': 'Database Systems', 'units': 3, 'is_major': True},
            {'code': 'CS401', 'name': 'Software Engineering', 'units': 3, 'is_major': True},
            {'code': 'MATH101', 'name': 'Calculus I', 'units': 3, 'is_major': False},
            {'code': 'PE101', 'name': 'Physical Education 1', 'units': 2, 'is_major': False}
        ]
        
        subjects = []
        for data in subjects_data:
            subject = Subject(
                code=data['code'],
                name=data['name'],
                units=data['units'],
                is_major_subject=data['is_major']
            )
            db.session.add(subject)
            subjects.append(subject)
        
        db.session.commit()
        print(f"   ✅ Created {len(subjects)} subjects")
        
        print("🏫 Creating Classes...")
        # Create classes for the main teacher (Prof. Mendoza - index 1)
        main_teacher = teachers[1]  # Prof. Mendoza
        
        classes_data = [
            {
                'subject': subjects[1],  # CS201 - Data Structures
                'section': 'A',
                'schedule': 'MWF 9:00-10:30',
                'room': 'Room 301'
            },
            {
                'subject': subjects[2],  # CS202 - OOP
                'section': 'B',
                'schedule': 'TTh 10:00-11:30',
                'room': 'Room 302'
            },
            {
                'subject': subjects[0],  # CS101 - Intro to Computing
                'section': 'A',
                'schedule': 'MWF 13:00-14:30',
                'room': 'Room 205'
            },
            {
                'subject': subjects[4],  # CS301 - Database Systems
                'section': 'C',
                'schedule': 'TTh 14:00-15:30',
                'room': 'Room 401'
            },
            {
                'subject': subjects[5],  # CS401 - Software Engineering
                'section': 'A',
                'schedule': 'MWF 15:00-16:30',
                'room': 'Room 402'
            },
            {
                'subject': subjects[3],  # CS205 - Discrete Math
                'section': 'B',
                'schedule': 'TTh 8:00-9:30',
                'room': 'Room 303'
            }
        ]
        
        classes = []
        for data in classes_data:
            cls = Class(
                teacher_id=main_teacher.id,
                subject_id=data['subject'].id,
                section=data['section'],
                schedule=data['schedule'],
                room=data['room'],
                school_year='2024-2025',
                semester='1st Semester',
                max_students=40
            )
            db.session.add(cls)
            classes.append(cls)
        
        db.session.commit()
        print(f"   ✅ Created {len(classes)} classes")
        
        print("📝 Enrolling Students in Classes...")
        # Enroll students in classes (random enrollment)
        enrollments = []
        for cls in classes:
            # Randomly select 20-35 students per class
            num_students = random.randint(20, 35)
            enrolled_students = random.sample(students, num_students)
            
            for student in enrolled_students:
                enrollment = Enrollment(
                    student_id=student.id,
                    class_id=cls.id,
                    status='enrolled'
                )
                db.session.add(enrollment)
                enrollments.append(enrollment)
        
        db.session.commit()
        print(f"   ✅ Created {len(enrollments)} enrollments")
        
        print("📋 Creating Tests/Assignments...")
        # Create tests for each class
        test_types = ['Quiz 1', 'Quiz 2', 'Midterm Exam', 'Quiz 3', 'Final Exam', 'Project']
        
        tests = []
        for cls in classes:
            for i, test_name in enumerate(test_types):
                test = Test(
                    class_id=cls.id,
                    title=test_name,
                    description=f'{test_name} for {cls.subject.name}',
                    test_date=date.today() - timedelta(days=random.randint(1, 60))
                )
                db.session.add(test)
                tests.append(test)
        
        db.session.commit()
        print(f"   ✅ Created {len(tests)} tests")
        
        print("✅ Creating Grades...")
        # Create grades for students (random grades)
        grades = []
        for test in tests:
            # Get enrolled students for this test's class
            class_enrollments = Enrollment.query.filter_by(
                class_id=test.class_id,
                status='enrolled'
            ).all()
            
            # Randomly decide how many students have been graded (60-100%)
            num_graded = int(len(class_enrollments) * random.uniform(0.6, 1.0))
            graded_students = random.sample(class_enrollments, num_graded)
            
            for enrollment in graded_students:
                # Generate realistic grades (1.0 - 3.0 mostly, some 4.0, rare 5.0)
                grade_pool = [1.0, 1.25, 1.5, 1.75, 2.0, 2.25, 2.5, 2.75, 3.0] * 10 + [4.0] * 2 + [5.0]
                final_grade = random.choice(grade_pool)
                
                grade = Grade(
                    test_id=test.id,
                    student_id=enrollment.student_id,
                    calculated_percentage=random.uniform(75, 100),
                    calculated_grade=final_grade,
                    final_grade=final_grade,
                    graded_by=main_teacher.id,
                    graded_at=datetime.utcnow() - timedelta(days=random.randint(1, 30))
                )
                db.session.add(grade)
                grades.append(grade)
        
        db.session.commit()
        print(f"   ✅ Created {len(grades)} grades")
        
        print("\n" + "="*60)
        print("🎉 TEST DATA CREATION COMPLETE!")
        print("="*60)
        print("\n📋 LOGIN CREDENTIALS:\n")
        print("👨‍🏫 TEACHER LOGIN:")
        print("   Email: prof.mendoza@acadify.edu")
        print("   Password: teacher123")
        print("   (Has 6 classes with enrolled students and grades)")
        print()
        print("👨‍🎓 STUDENT LOGIN (example):")
        print("   Student Number: 2024-00001")
        print("   Password: student123")
        print()
        print("📊 DATABASE SUMMARY:")
        print(f"   Teachers: {len(teachers)}")
        print(f"   Students: {len(students)}")
        print(f"   Subjects: {len(subjects)}")
        print(f"   Classes: {len(classes)}")
        print(f"   Enrollments: {len(enrollments)}")
        print(f"   Tests: {len(tests)}")
        print(f"   Grades: {len(grades)}")
        print("\n" + "="*60)
        print("🚀 You can now run the Flask app and test the system!")
        print("   Run: python app.py")
        print("="*60 + "\n")

if __name__ == '__main__':
    create_test_data()