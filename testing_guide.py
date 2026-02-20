"""
PHASE 1 TESTING GUIDE - Grade Model with Option B
Complete usage examples and test scenarios
"""

from models import Grade, Class, Student, Teacher, Test
from extensions import db
from datetime import datetime

# ============================================================================
# EXAMPLE 1: Adding Individual Quiz/Exam Items (Option B - New Way)
# ============================================================================

def example_add_grades_option_b():
    """
    Teacher adds grades throughout the semester using Option B
    Each quiz/exam is tracked individually with its own max score
    """
    
    # Get a student and their test/class
    student = Student.query.first()
    test = Test.query.first()
    class_obj = test.class_
    
    # Create or get the grade entry for this student
    grade = Grade.query.filter_by(
        student_id=student.id,
        test_id=test.id
    ).first()
    
    if not grade:
        grade = Grade(student_id=student.id, test_id=test.id)
        db.session.add(grade)
    
    # Week 2: Add Quiz 1
    try:
        grade.add_component_item(
            component_name="Quizzes",
            score=20,
            max_score=25,
            item_name="Quiz 1",
            item_date="2024-09-05"
        )
        print("✓ Quiz 1 added: 20/25")
    except ValueError as e:
        print(f"✗ Error: {e}")
    
    # Week 5: Add Quiz 2 (different max score)
    try:
        grade.add_component_item(
            component_name="Quizzes",
            score=25,
            max_score=30,
            item_name="Quiz 2",
            item_date="2024-09-25"
        )
        print("✓ Quiz 2 added: 25/30")
    except ValueError as e:
        print(f"✗ Error: {e}")
    
    # Week 8: Add Quiz 3
    try:
        grade.add_component_item(
            component_name="Quizzes",
            score=18,
            max_score=20,
            item_name="Quiz 3",
            item_date="2024-10-10"
        )
        print("✓ Quiz 3 added: 18/20")
    except ValueError as e:
        print(f"✗ Error: {e}")
    
    # Midterm: Add Prelim Exam
    try:
        grade.add_component_item(
            component_name="Exams",
            score=85,
            max_score=100,
            item_name="Prelim Exam",
            item_date="2024-09-15"
        )
        print("✓ Prelim Exam added: 85/100")
    except ValueError as e:
        print(f"✗ Error: {e}")
    
    # Add Midterm Exam
    try:
        grade.add_component_item(
            component_name="Exams",
            score=90,
            max_score=100,
            item_name="Midterm Exam",
            item_date="2024-10-20"
        )
        print("✓ Midterm Exam added: 90/100")
    except ValueError as e:
        print(f"✗ Error: {e}")
    
    # Finals: Add Final Exam
    try:
        grade.add_component_item(
            component_name="Exams",
            score=88,
            max_score=100,
            item_name="Final Exam",
            item_date="2024-12-10"
        )
        print("✓ Final Exam added: 88/100")
    except ValueError as e:
        print(f"✗ Error: {e}")
    
    # Add Performance Tasks
    try:
        grade.add_component_item(
            component_name="Performance Task",
            score=40,
            max_score=50,
            item_name="Task 1",
            item_date="2024-10-01"
        )
        print("✓ Task 1 added: 40/50")
    except ValueError as e:
        print(f"✗ Error: {e}")
    
    try:
        grade.add_component_item(
            component_name="Performance Task",
            score=28,
            max_score=30,
            item_name="Task 2",
            item_date="2024-11-05"
        )
        print("✓ Task 2 added: 28/30")
    except ValueError as e:
        print(f"✗ Error: {e}")
    
    # Add Project
    try:
        grade.add_component_item(
            component_name="Project",
            score=92,
            max_score=100,
            item_name="Final Project",
            item_date="2024-12-05"
        )
        print("✓ Final Project added: 92/100")
    except ValueError as e:
        print(f"✗ Error: {e}")
    
    # Calculate final grade
    grade.calculate_grade(class_obj)
    
    db.session.commit()
    
    print(f"\n--- CALCULATION RESULTS ---")
    print(f"Calculated Percentage: {grade.calculated_percentage}%")
    print(f"Calculated PH Grade: {grade.calculated_grade}")
    print(f"Final Grade: {grade.final_grade}")


# ============================================================================
# EXAMPLE 2: Viewing Component Summaries
# ============================================================================

def example_view_component_summary():
    """
    View detailed breakdown of each component
    """
    grade = Grade.query.first()
    
    print("\n=== GRADE BREAKDOWN ===\n")
    
    # Get all components from the class formula
    class_obj = grade.test.class_
    formula = class_obj.get_grading_formula()
    
    for component in formula['components']:
        comp_name = component['name']
        weight = component['weight']
        
        summary = grade.get_component_summary(comp_name)
        
        if summary:
            print(f"{comp_name} ({weight}%)")
            print(f"  Items: {summary['item_count']}")
            print(f"  Average: {summary['average_percentage']:.2f}%")
            print(f"  Total: {summary['total_points']}/{summary['total_max']}")
            print(f"  Contribution: {summary['average_percentage'] * weight / 100:.2f} points")
            
            # Show individual items
            for i, item in enumerate(summary['items']):
                percentage = (item['score'] / item['max']) * 100
                print(f"    {i+1}. {item['name']}: {item['score']}/{item['max']} ({percentage:.1f}%) - {item['date']}")
            print()
        else:
            print(f"{comp_name} ({weight}%)")
            print(f"  No items yet\n")


# ============================================================================
# EXAMPLE 3: Updating an Existing Item
# ============================================================================

def example_update_item():
    """
    Teacher corrects a grade entry
    """
    grade = Grade.query.first()
    
    print("\n=== BEFORE UPDATE ===")
    items = grade.get_component_items("Quizzes")
    print(f"Quiz 2: {items[1]['score']}/{items[1]['max']}")
    
    # Update Quiz 2 score
    try:
        success = grade.update_component_item(
            component_name="Quizzes",
            item_index=1,  # Quiz 2 (0-based index)
            score=28,      # Changed from 25 to 28
            max_score=30   # Keep the same
        )
        
        if success:
            print("\n=== AFTER UPDATE ===")
            items = grade.get_component_items("Quizzes")
            print(f"Quiz 2: {items[1]['score']}/{items[1]['max']}")
            
            # Recalculate grade
            grade.calculate_grade(grade.test.class_)
            db.session.commit()
            
            print(f"New Final Grade: {grade.final_grade}")
        else:
            print("✗ Update failed - item not found")
            
    except ValueError as e:
        print(f"✗ Validation error: {e}")


# ============================================================================
# EXAMPLE 4: Deleting an Item
# ============================================================================

def example_delete_item():
    """
    Teacher removes a quiz (e.g., pop quiz that was too hard)
    """
    grade = Grade.query.first()
    
    print("\n=== BEFORE DELETE ===")
    items = grade.get_component_items("Quizzes")
    print(f"Quiz count: {len(items)}")
    for i, item in enumerate(items):
        print(f"  {i}. {item['name']}: {item['score']}/{item['max']}")
    
    # Delete Quiz 3
    success = grade.delete_component_item(
        component_name="Quizzes",
        item_index=2  # Quiz 3 (0-based index)
    )
    
    if success:
        print("\n=== AFTER DELETE ===")
        items = grade.get_component_items("Quizzes")
        print(f"Quiz count: {len(items)}")
        for i, item in enumerate(items):
            print(f"  {i}. {item['name']}: {item['score']}/{item['max']}")
        
        # Recalculate grade
        grade.calculate_grade(grade.test.class_)
        db.session.commit()
        
        print(f"New Final Grade: {grade.final_grade}")
    else:
        print("✗ Delete failed - item not found")


# ============================================================================
# EXAMPLE 5: Backward Compatibility (Old Format Still Works)
# ============================================================================

def example_backward_compatibility():
    """
    Old grades with single values still calculate correctly
    """
    student = Student.query.first()
    test = Test.query.first()
    
    # Create a grade with OLD FORMAT (Option A)
    grade = Grade(student_id=student.id, test_id=test.id)
    
    # Old way: Single pre-averaged values
    old_format_scores = {
        "Quizzes": 85.83,
        "Exams": 87.67,
        "Performance Task": 87.78,
        "Project": 92
    }
    
    grade.set_component_scores(old_format_scores)
    grade.calculate_grade(test.class_)
    
    print("\n=== OLD FORMAT (Option A) ===")
    print(f"Component Scores: {grade.get_component_scores()}")
    print(f"Calculated Grade: {grade.calculated_grade}")
    print(f"✓ Old format still works!")


# ============================================================================
# EXAMPLE 6: Validation Tests
# ============================================================================

def example_validation_tests():
    """
    Test all validation rules
    """
    grade = Grade.query.first()
    class_obj = grade.test.class_
    
    print("\n=== VALIDATION TESTS ===\n")
    
    # Test 1: Negative score
    try:
        grade.add_component_item("Quizzes", -5, 100, "Test Quiz")
        print("✗ FAIL: Negative score should be rejected")
    except ValueError as e:
        print(f"✓ PASS: Negative score rejected - {e}")
    
    # Test 2: Score exceeds max
    try:
        grade.add_component_item("Quizzes", 110, 100, "Test Quiz")
        print("✗ FAIL: Score > max should be rejected")
    except ValueError as e:
        print(f"✓ PASS: Score > max rejected - {e}")
    
    # Test 3: Max score is 0
    try:
        grade.add_component_item("Quizzes", 50, 0, "Test Quiz")
        print("✗ FAIL: Max score = 0 should be rejected")
    except ValueError as e:
        print(f"✓ PASS: Max = 0 rejected - {e}")
    
    # Test 4: Empty item name
    try:
        grade.add_component_item("Quizzes", 50, 100, "")
        print("✗ FAIL: Empty name should be rejected")
    except ValueError as e:
        print(f"✓ PASS: Empty name rejected - {e}")
    
    # Test 5: Missing required fields
    try:
        grade.add_component_item("Quizzes", None, 100, "Test Quiz")
        print("✗ FAIL: None score should be rejected")
    except ValueError as e:
        print(f"✓ PASS: None score rejected - {e}")
    
    print("\n✓ All validation tests passed!")


# ============================================================================
# EXAMPLE 7: Incomplete Grades (Components with 0 items)
# ============================================================================

def example_incomplete_grade():
    """
    Grade calculation with missing components (Option A behavior)
    System calculates based only on components with data
    """
    student = Student.query.first()
    test = Test.query.first()
    class_obj = test.class_
    
    # Create new grade
    grade = Grade(student_id=student.id, test_id=test.id)
    db.session.add(grade)
    
    # Only add Quizzes and Exams, skip Performance Task and Project
    grade.add_component_item("Quizzes", 20, 25, "Quiz 1", "2024-09-05")
    grade.add_component_item("Exams", 85, 100, "Prelim", "2024-09-15")
    
    # Calculate (should skip empty components)
    grade.calculate_grade(class_obj)
    
    print("\n=== INCOMPLETE GRADE ===")
    print(f"Quizzes: Added ✓")
    print(f"Exams: Added ✓")
    print(f"Performance Task: Missing (skipped)")
    print(f"Project: Missing (skipped)")
    print(f"\nCalculated Percentage: {grade.calculated_percentage}")
    print(f"Calculated Grade: {grade.calculated_grade}")
    print(f"Note: Grade calculated from available components only")
    
    db.session.rollback()  # Don't save this test


# ============================================================================
# EXAMPLE 8: Complete Workflow
# ============================================================================

def example_complete_workflow():
    """
    Complete semester workflow from setup to final grade
    """
    print("\n=== COMPLETE SEMESTER WORKFLOW ===\n")
    
    # STEP 1: Create class with grading formula
    print("STEP 1: Teacher creates class")
    # (This happens in Phase 2 UI, but here's the data structure)
    formula = {
        "components": [
            {"name": "Exams", "weight": 30},
            {"name": "Quizzes", "weight": 30},
            {"name": "Performance Task", "weight": 20},
            {"name": "Project", "weight": 20}
        ],
        "passing_grade": 3.0,
        "use_philippine_conversion": True
    }
    print(f"Formula: {formula}")
    
    # STEP 2: Throughout semester, add grades
    print("\nSTEP 2: Teacher adds grades throughout semester")
    
    student = Student.query.first()
    test = Test.query.first()
    grade = Grade(student_id=student.id, test_id=test.id)
    db.session.add(grade)
    
    # Week 2
    grade.add_component_item("Quizzes", 20, 25, "Quiz 1", "2024-09-05")
    print("Week 2: Quiz 1 added")
    
    # Week 5
    grade.add_component_item("Quizzes", 25, 30, "Quiz 2", "2024-09-25")
    print("Week 5: Quiz 2 added")
    
    # Week 8
    grade.add_component_item("Exams", 85, 100, "Prelim", "2024-09-15")
    print("Week 8: Prelim Exam added")
    
    # Week 12
    grade.add_component_item("Quizzes", 18, 20, "Quiz 3", "2024-10-10")
    grade.add_component_item("Exams", 90, 100, "Midterm", "2024-10-20")
    print("Week 12: Quiz 3 and Midterm added")
    
    # Week 15
    grade.add_component_item("Performance Task", 40, 50, "Task 1", "2024-10-01")
    grade.add_component_item("Performance Task", 28, 30, "Task 2", "2024-11-05")
    print("Week 15: Performance Tasks added")
    
    # Finals Week
    grade.add_component_item("Exams", 88, 100, "Final", "2024-12-10")
    grade.add_component_item("Project", 92, 100, "Final Project", "2024-12-05")
    print("Finals Week: Final Exam and Project added")
    
    # STEP 3: Calculate final grade
    print("\nSTEP 3: Calculate final grade")
    grade.calculate_grade(test.class_)
    
    print(f"\nFINAL RESULTS:")
    print(f"Calculated Percentage: {grade.calculated_percentage}%")
    print(f"PH Grade: {grade.calculated_grade}")
    print(f"Status: {'PASSED' if grade.final_grade <= 3.0 else 'FAILED'}")
    
    db.session.rollback()  # Don't save this test


# ============================================================================
# RUN ALL EXAMPLES
# ============================================================================

if __name__ == "__main__":
    print("=" * 60)
    print("PHASE 1: GRADE MODEL TESTING GUIDE")
    print("=" * 60)
    
    # Uncomment the examples you want to run:
    
    # example_add_grades_option_b()
    # example_view_component_summary()
    # example_update_item()
    # example_delete_item()
    # example_backward_compatibility()
    # example_validation_tests()
    # example_incomplete_grade()
    # example_complete_workflow()
    
    print("\n" + "=" * 60)
    print("Testing complete!")
    print("=" * 60)