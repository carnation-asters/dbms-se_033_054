from flask import Blueprint, render_template, request, redirect, url_for, flash, session
from functools import wraps
from controllers.model import db, Admin, Student, College, User, Major, SeatPreference, Round, StudentAllotment
from datetime import datetime, date
from flask import jsonify, request

main = Blueprint('main', __name__)

# Role-based access control decorator
def role_required(*allowed_roles):
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            if 'user_id' not in session:
                flash('Please log in to access this page.', 'error')
                return redirect(url_for('main.login'))
            
            user_role = session.get('user_role')
            if user_role not in allowed_roles:
                flash('You do not have permission to access this page.', 'error')
                return redirect(url_for('main.login'))
            return f(*args, **kwargs)
        return decorated_function
    return decorator

@main.route('/logout')
def logout():
    session.pop('user_id', None)
    session.pop('user_role', None)
    return redirect(url_for('main.login'))

@main.route('/')
def index():
    return redirect(url_for('main.login'))

@main.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        
        user = db.session.query(User).filter_by(username=username, password=password).first()
        
        if user is not None:
            session['user_id'] = user.id
            session['user_role'] = user.role
            if user.role == 'COLLEGE':
                return redirect(url_for('main.college_dashboard'))
            elif user.role == 'STUDENT':
                return redirect(url_for('main.student_dashboard'))
            else:
                return redirect(url_for('main.admin_dashboard'))
        else:
            flash('User credentials are incorrect. Please try again.', 'error')
            return redirect(url_for('main.login'))
    
    return render_template('login.html')

# Admin routes
@main.route('/admin/dashboard')
@role_required('ADMIN')
def admin_dashboard():
    current_user_id = session.get('user_id')
    admin = Admin.query.get(current_user_id)
    active_round = Round.query.filter_by(is_active=True).first()
    latest_round = Round.query.order_by(Round.round_id.desc()).first()
    return render_template('admin_dashboard.html', admin=admin, active_round=active_round, latest_round=latest_round)

@main.route('/admin/add_round', methods=['POST'])
@role_required('ADMIN')
def add_round():
    start_date = datetime.now()
    try:
        new_round = Round(start_date=start_date, is_active=True)
        db.session.add(new_round)
        db.session.commit()
        flash('New round started successfully!', 'success')
    except Exception as e:
        db.session.rollback()
        flash(f'Error starting new round: {e}', 'danger')
    return redirect(url_for('main.admin_dashboard'))

@main.route('/admin/end_round/<int:round_id>', methods=['POST'])
@role_required('ADMIN')
def end_round(round_id):
    try:
        round_to_update = Round.query.get(round_id)
        if round_to_update and round_to_update.is_active:
            round_to_update.is_active = False
            round_to_update.end_date = datetime.now()
            allocate_seats(round_id)
            db.session.commit()
            flash(f"Round {round_id} has ended and is now inactive.", "success")
        else:
            flash("Round is either not active or does not exist.", "error")
    except Exception as e:
        db.session.rollback()
        flash("An error occurred while trying to end the round.", "error")
        print(e)
    return redirect(url_for('main.admin_dashboard'))

@main.route('/view_students')
@role_required('ADMIN')
def view_students():
    students = Student.query.all()
    return render_template('view_students.html', students=students)

@main.route('/toggle_eligibility/<int:student_id>', methods=['POST'])
@role_required('ADMIN')
def toggle_eligibility(student_id):
    student = Student.query.get_or_404(student_id)
    try:
        student.eligibility_status = not student.eligibility_status
        db.session.commit()
        flash("Eligibility status updated successfully.", "success")
    except Exception as e:
        db.session.rollback()
        flash(f"An error occurred while updating the eligibility status: {str(e)}", "danger")
    return redirect(url_for('main.view_students'))


# College routes
@main.route('/college/dashboard')
@role_required('COLLEGE')
def college_dashboard():
    current_user_id = session.get('user_id')
    user1 = (
        db.session.query(College, User)
        .join(User, User.id == College.id)
        .filter(College.id==current_user_id)
        .all()
    )
    college = College.query.get(current_user_id)
    majors = Major.query.filter_by(college_id=current_user_id).all()
    is_rounds_empty = not db.session.query(Round).first()
    return render_template('college_dashboard.html', users=user1, college=college, majors=majors, is_rounds_empty=is_rounds_empty)

@main.route('/add_major', methods=['GET', 'POST'])
@role_required('COLLEGE')
def add_major():
    current_user_id = session.get('user_id')
    if request.method == 'POST':
        major_name = request.form.get('name')
        seat_count = request.form.get('seat_count', type=int)
        
        if not major_name or seat_count is None:
            flash('Please provide both major name and seat count.', 'danger')
            return redirect(url_for('main.add_major'))

        new_major = Major(name=major_name, seat_count=seat_count, college_id=current_user_id)
        db.session.add(new_major)
        
        try:
            db.session.commit()
            flash('Major added successfully!', 'success')
        except Exception as e:
            db.session.rollback()
            flash('Error adding major. Please ensure the major name is unique.', 'danger')
        return redirect(url_for('main.college_dashboard'))

    college = College.query.get(current_user_id)
    return render_template('add_major.html', college=college)

@main.route('/delete_major/<int:major_id>', methods=['POST'])
@role_required('COLLEGE')
def delete_major(major_id):
    is_rounds_empty = not db.session.query(Round).first()
    if not is_rounds_empty:
        flash("Cannot delete majors while there are active counseling rounds.", "danger")
        return redirect(url_for('main.college_dashboard'))
    
    major = Major.query.get_or_404(major_id)
    try:
        db.session.delete(major)
        db.session.commit()
        flash("Major deleted successfully.", "success")
    except Exception as e:
        db.session.rollback()
        flash(f"An error occurred while deleting the major: {str(e)}", "danger")
    return redirect(url_for('main.college_dashboard'))

@main.route('/edit_major/<int:major_id>', methods=['GET', 'POST'])
@role_required('COLLEGE')
def edit_major(major_id):
    is_rounds_empty = not db.session.query(Round).first()
    if not is_rounds_empty:
        flash("Cannot edit majors while there are active counseling rounds.", "danger")
        return redirect(url_for('main.college_dashboard'))
    
    major = Major.query.get_or_404(major_id)
    if request.method == 'POST':
        major.name = request.form['name']
        major.seat_count = request.form['seat_count']
        try:
            db.session.commit()
            flash("Major updated successfully.", "success")
            return redirect(url_for('main.college_dashboard'))
        except Exception as e:
            db.session.rollback()
            flash(f"An error occurred while updating the major: {str(e)}", "danger")
            return redirect(url_for('main.edit_major', major_id=major_id))
    return render_template('edit_major.html', major=major)

# Student routes
@main.route('/student/dashboard', methods=['GET', 'POST'])
@role_required('STUDENT')
def student_dashboard():
    current_user_id = session.get('user_id')
    student = Student.query.filter_by(id=current_user_id).first()
    active_round = Round.query.filter_by(is_active=True).first()
    college_major_pairs = db.session.query(
        Major.id.label('major_id'),
        Major.name.label('major_name'),
        College.id.label('college_id'),
        College.name.label('college_name')
    ).join(College).all()
    saved_preferences = SeatPreference.query.filter_by(student_id=current_user_id).all()
    seat_allotments = StudentAllotment.query.filter_by(student_id=current_user_id).all()
    
    previous_allotment = (
        StudentAllotment.query
        .filter(StudentAllotment.student_id == current_user_id,
                StudentAllotment.choice.in_(['freeze_and_upgrade', 'reject_and_upgrade']))
        .order_by(StudentAllotment.round_id.desc())
        .first()
    )
    
    if request.method == 'POST':
        try:
            preference1_id = request.form.get('preference1')
            preference2_id = None
            
            if previous_allotment:
                if previous_allotment.choice == 'freeze_and_upgrade':
                    previous_pref = SeatPreference.query.get(previous_allotment.pref_id)
                    if previous_pref:
                        preference2_id = previous_pref.major_id
                elif previous_allotment.choice == 'reject_and_upgrade':
                    preference2_id = request.form.get('preference2')
            else:
                preference2_id = request.form.get('preference2')

            existing_preferences = SeatPreference.query.filter_by(
                student_id=current_user_id, round_id=active_round.round_id
            ).all()
            
            if not existing_preferences:
                preference1 = Major.query.get(preference1_id)
                preference2 = Major.query.get(preference2_id)
                if preference1 and preference2:
                    new_preference1 = SeatPreference(
                        student_id=current_user_id,
                        college_id=preference1.college_id,
                        major_id=preference1.id,
                        preference_order=1,
                        round_id=active_round.round_id
                    )
                    new_preference2 = SeatPreference(
                        student_id=current_user_id,
                        college_id=preference2.college_id,
                        major_id=preference2.id,
                        preference_order=2,
                        round_id=active_round.round_id
                    )
                    db.session.add(new_preference1)
                    db.session.add(new_preference2)
                    db.session.commit()
                    flash('Preferences saved successfully!', 'success')
                else:
                    flash('Invalid preferences selected.', 'danger')
            else:
                flash('Preferences for this round already exist.', 'warning')
        except Exception as e:
            db.session.rollback()
            flash('An error occurred while saving preferences.', 'danger')
        return redirect(url_for('main.student_dashboard'))

    return render_template(
        'student_dashboard.html',
        student=student,
        college_major_pairs=college_major_pairs,
        saved_preferences=saved_preferences,
        active_round=active_round,
        seat_allotments=seat_allotments,
        previous_allotment=previous_allotment
    )

@main.route('/update_choice/<int:allotment_id>', methods=['POST'])
@role_required('STUDENT')
def update_choice(allotment_id):
    choice = request.form.get('choice')
    allotment = StudentAllotment.query.get_or_404(allotment_id)
    major = allotment.preference.major

    if choice == 'accept':
        allotment.status = 'active'
        allotment.student.round_furthering = False
    elif choice == 'freeze_and_upgrade':
        allotment.status = 'active'
        allotment.student.round_furthering = True
    elif choice == 'reject_and_upgrade':
        allotment.status = 'inactive'
        allotment.student.round_furthering = True
        if major.alloted_seat_count > 0:
            major.alloted_seat_count -= 1
            db.session.commit()
    elif choice == 'withdraw':
        allotment.status = 'inactive'
        allotment.student.round_furthering = False
        if major.alloted_seat_count > 0:
            major.alloted_seat_count -= 1
            db.session.commit()

    allotment.choice = choice
    db.session.commit()
    flash('Your choice has been updated successfully!', 'success')
    return redirect(url_for('main.student_dashboard'))

# Public routes
@main.route('/register/student', methods=['GET', 'POST'])
def register_student():
    if request.method == 'POST':
        # Retrieve form data
        username = request.form.get('username')
        email = request.form.get('email')
        password = request.form.get('password')
        name = request.form.get('name')
        address = request.form.get('address')
        rank=request.form.get('rank')
        doc_url=request.form.get('docurl')
        role = 'STUDENT'

        # Debugging output
        print(f"Request method: {request.method}")
        print(f"Creating user with Username: {username}, Email: {email}, Password: {password}, Role: {role},Rank: {rank},Doc_url:{doc_url}")
        print(f"Form data: {request.form}")

        # Validate inputs
        if not username or not email or not password or not name or not address or not rank:
            flash('Please fill in all fields.')
            return redirect(url_for('main.register_student'))

        # Check if the user already exists
        existing_user = db.session.query(User).filter((User.username == username) | (User.email == email)).first()
        if existing_user:
            flash('Username or email already exists. Please choose a different one.')
            return redirect(url_for('main.register_student'))

        # Create a new user in the database
        new_user = User(username=username, email=email, password=password, role=role)
        db.session.add(new_user)

        try:
            db.session.commit()  # Attempt to commit the new user
        except Exception as e:
            db.session.rollback()  # Rollback in case of error
            print(f"Error committing user: {e}")  # Debugging error
            flash('An error occurred while registering. Please try again.')
            return redirect(url_for('main.register_student'))

        # Create a customer entry
        student = Student(id=new_user.id, name=name, address=address,rank=rank,doc_url=doc_url)
        db.session.add(student)

        try:
            db.session.commit()  # Attempt to commit the new customer
        except Exception as e:
            db.session.rollback()  # Rollback in case of error
            print(f"Error committing customer: {e}")  # Debugging error
            flash('An error occurred while creating your profile. Please try again.')
            return redirect(url_for('main.register_student'))

        flash('Registration successful! You can now log in.')
        return redirect(url_for('main.login'))

    return render_template('register_student.html')


@main.route('/register/college', methods=['GET', 'POST'])
def register_college():
    if request.method == 'POST':
        username = request.form.get('username')
        email = request.form.get('email')
        password = request.form.get('password')
        name = request.form.get('name')
        experience = request.form.get('experience')
        desc = request.form.get('desc')
        role = 'COLLEGE'

        # Validate inputs
        if not username or not email or not password or not name or not experience:
            flash('Please fill in all fields.')
            return redirect(url_for('main.register_college'))

        # Check if the user already exists
        existing_user = db.session.query(User).filter_by(username=username).first()
        if existing_user:
            flash('Username already exists. Please choose a different username.')
            return redirect(url_for('main.register_college'))

        # Create a new user in the database
        new_user = User(username=username, email=email, password=password, role=role)
        db.session.add(new_user)
        db.session.commit()

        # Create a service college entry
        college = College(id=new_user.id, name=name,
                                           experience=experience, description=desc)
        db.session.add(college)
        db.session.commit()

        flash('Registration successful! You can now log in.')
        return redirect(url_for('main.login'))

    # Fetch available services for the dropdown

    return render_template('register_college.html')

@main.route('/view_colleges', methods=['GET'])
def view_colleges():
    user = session.get('user_id')
    cur = User.query.filter_by(id=user).first() if user else None
    colleges = College.query.options(db.joinedload(College.majors)).all()
    return render_template('view_colleges.html', colleges=colleges, user=cur)

# Helper function to handle seat allocation logic
def allocate_seats(round_id):
    # Retrieve all students for the given round sorted by rank
    students = Student.query.order_by(Student.rank).all()

    for student in students:
        allocated = False  # Track if the student gets a seat

        # Fetch the previous round allotment for this student
        previous_allotment = StudentAllotment.query.filter_by(
            student_id=student.id,
            status='active'
        ).order_by(StudentAllotment.round_id.desc()).first()

        # Go through each preference in order for this specific round
        preferences = SeatPreference.query.filter_by(
            student_id=student.id, 
            round_id=round_id
        ).order_by(SeatPreference.preference_order).all()

        for idx, preference in enumerate(preferences):
            major = Major.query.filter_by(id=preference.major_id).first()

            # Check if there's an available seat in this major
            if major and major.alloted_seat_count < major.seat_count:
                
                # If previous choice was "freeze and upgrade" and this is the current round's first preference
                if previous_allotment and previous_allotment.choice == 'freeze_and_upgrade':
                    previous_preference = SeatPreference.query.get(previous_allotment.pref_id)
                    previous_major = Major.query.filter_by(id=previous_preference.major_id).first()

                    # If the first preference is available, update both seat counts accordingly
                    if idx == 0:
                        # Increase seat count of new allocation's major (preference 1)
                        major.alloted_seat_count += 1
                        db.session.add(major)

                        # Decrease seat count of previous major (preference 2)
                        if previous_major and previous_major.alloted_seat_count > 0:
                            previous_major.alloted_seat_count -= 1
                            db.session.add(previous_major)

                    # If the second preference is allocated, proceed without changing seat counts
                    elif idx == 1:
                        # Only allocate seat without updating seat counts
                        major.alloted_seat_count += 1
                        db.session.add(major)
                
                # Default logic if previous choice was not "freeze and upgrade"
                else:
                    # Allocate seat to this student for this preference
                    major.alloted_seat_count += 1
                    db.session.add(major)

                # Record the seat allocation in the StudentAllotment table
                allocation = StudentAllotment(
                    student_id=student.id,
                    pref_id=preference.id,
                    round_id=round_id,
                    status='active'
                )
                db.session.add(allocation)

                # Mark the student as allocated
                allocated = True
                break  # Stop further preferences once a seat is allocated

    # Commit all changes to the database
    db.session.commit()
    return "Seat allocation completed for round."




