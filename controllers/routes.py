from flask import Blueprint, render_template, request, redirect, url_for, flash, session
from controllers.model import db, Admin, Student, College, User, Major, SeatPreference, Round, StudentAllotment
from datetime import datetime,date
from flask import jsonify, request

main = Blueprint('main', __name__)

@main.route('/logout')
def logout():
    session.pop('user_id', None)  # Adjust the key based on your session management
    return redirect(url_for('main.login'))  # Redirect to login page after logout

@main.route('/')
def index():
    return redirect(url_for('main.login')) 

from flask import flash, redirect, render_template, request, session, url_for
# Ensure you import the necessary libraries at the top

@main.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        print(f"Creating user with Username: {username}, Password: {password}")
        
        # Query for the user
        user = db.session.query(User).filter_by(username=username, password=password).first()
        print(user)
        
        # Check if user exists
        if user is not None:  # Correct way to check if the user is found
            session['user_id'] = user.id
            session['user_role'] = user.role
            if user.role == 'COLLEGE':
                return redirect(url_for('main.college_dashboard'))
            elif user.role == 'STUDENT':
                return redirect(url_for('main.student_dashboard'))
            else:
                return redirect(url_for('main.admin_dashboard'))
        else:
            # Set a flash message for failed login attempt
            flash('User credentials are incorrect. Please try again.', 'error')
            return redirect(url_for('main.login'))  # Redirect to login page to show the message
    
    return render_template('login.html')


# Route for registration page
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
        role = 'STUDENT'

        # Debugging output
        print(f"Request method: {request.method}")
        print(f"Creating user with Username: {username}, Email: {email}, Password: {password}, Role: {role},Rank: {rank}")
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
        student = Student(id=new_user.id, name=name, address=address,rank=rank)
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
        doc_url = request.form.get('doc_url')
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
                                           experience=experience, doc_url=doc_url, description=desc)
        db.session.add(college)
        db.session.commit()

        flash('Registration successful! You can now log in.')
        return redirect(url_for('main.login'))

    # Fetch available services for the dropdown

    return render_template('register_college.html')





@main.route('/admin/dashboard')
def admin_dashboard():
    # Query the database for professionals who are not approved
    current_user_id = session.get('user_id')
    admin = Admin.query.get(current_user_id)
  
    # Query to get the current active round, if any
    active_round = Round.query.filter_by(is_active=True).first()
    latest_round = Round.query.order_by(Round.round_id.desc()).first()

    return render_template('admin_dashboard.html',admin=admin,active_round=active_round,
                           latest_round=latest_round)



@main.route('/admin/add_round', methods=['POST'])
def add_round():
    start_date = datetime.now() 
    
    try:

        # Create a new round
        new_round = Round(start_date=start_date, is_active=True)

        # Add and commit the new round to the database
        db.session.add(new_round)
        db.session.commit()

        flash('New round started successfully!', 'success')
    except Exception as e:
        db.session.rollback()
        flash(f'Error starting new round: {e}', 'danger')

    return redirect(url_for('main.admin_dashboard'))


@main.route('/admin/end_round/<int:round_id>', methods=['POST'])
def end_round(round_id):
    try:
        # Retrieve the round by ID
        round_to_update = Round.query.get(round_id)
        
        # Check if the round exists and is currently active
        if round_to_update and round_to_update.is_active:
            # Set the round as inactive and update the end date
            round_to_update.is_active = False
            round_to_update.end_date = datetime.now()  # Update end_date to the current date/time
            allocate_seats(round_id)


            # Commit the change to the database
            db.session.commit()
            
            flash(f"Round {round_id} has ended and is now inactive.", "success")
        else:
            flash("Round is either not active or does not exist.", "error")
    except Exception as e:
        db.session.rollback()  # Roll back if there's an error
        flash("An error occurred while trying to end the round.", "error")
        print(e)  # Optional: for debugging purposes
        

    return redirect(url_for('main.admin_dashboard'))


@main.route('/unblock_user', methods=['POST'])
def unblock_user():
    user_id = request.form['user_id']
    # Logic to unblock the user in the database
    user = User.query.get(user_id)
    if user:
        user.is_active = True
        db.session.commit()
    return redirect(url_for('main.admin_dashboard'))


@main.route('/college/dashboard')
def college_dashboard():
    current_user_id = session.get('user_id')  # Get the current user's ID from the session
    
    user1 = (
        db.session.query(College, User)
        .join(User, User.id == College.id)  # Join with User
        .filter(College.id==current_user_id)  # Case-insensitive search
        .all()
    )
    print(user1)
    college = College.query.get(current_user_id)
    print(college)
    majors = Major.query.filter_by(college_id=current_user_id).all() 
    print(majors)
    
    return render_template('college_dashboard.html', users=user1,college=college, majors=majors)  # Pass the full user object to the template

#add major
@main.route('/add_major', methods=['GET', 'POST'])
def add_major():
    current_user_id = session.get('user_id')  # Get the current user ID from the session

    if request.method == 'POST':
        # Retrieve the form data
        major_name = request.form.get('name')  # Get the major name
        seat_count = request.form.get('seat_count', type=int)  # Get the seat count as an integer

        # Debugging print statements to check the values
        print(f'Major Name: {major_name}, Seat Count: {seat_count}, College ID: {current_user_id}')

        # Check for missing values
        if not major_name or seat_count is None:
            flash('Please provide both major name and seat count.', 'danger')
            return redirect(url_for('main.add_major'))  # Redirect back to the form if validation fails

        # Create and save the new major associated with the current college
        new_major = Major(name=major_name, seat_count=seat_count, college_id=current_user_id)
        db.session.add(new_major)

        try:
            db.session.commit()  # Commit the transaction
            flash('Major added successfully!', 'success')  # Flash a success message
        except IntegrityError:
            db.session.rollback()  # Rollback the session in case of an error
            flash('Error adding major. Please ensure the major name is unique.', 'danger')

        return redirect(url_for('main.college_dashboard'))  # Redirect to the dashboard

    # If the request is a GET, render the add major page
    college = College.query.get(current_user_id)  # Get the current college object
    return render_template('add_major.html', college=college)  # Pass the college object to the template


@main.route('/student/dashboard', methods=['GET', 'POST'])
def student_dashboard():
    current_user_id = session.get('user_id')
    student = Student.query.filter_by(id=current_user_id).first()

    # Fetch the current active round
    active_round = Round.query.filter_by(is_active=True).first()

    # Fetch all college-major pairs
    college_major_pairs = db.session.query(
        Major.id.label('major_id'),
        Major.name.label('major_name'),
        College.id.label('college_id'),
        College.name.label('college_name')
    ).join(College).all()

    # Fetch saved seat preferences for the student
    saved_preferences = SeatPreference.query.filter_by(student_id=current_user_id).all()

    # Fetch seat allotments for all rounds for the student
    seat_allotments = StudentAllotment.query.filter_by(student_id=current_user_id).all()

    if request.method == 'POST':
        preference1_id = request.form.get('preference1')
        preference2_id = request.form.get('preference2')

        # Retrieve preferences and create new SeatPreference entries
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
            return redirect(url_for('main.student_dashboard'))

    return render_template(
        'student_dashboard.html',
        student=student,
        college_major_pairs=college_major_pairs,
        saved_preferences=saved_preferences,
        active_round=active_round,
        seat_allotments=seat_allotments
    )

@main.route('/view_colleges', methods=['GET'])
def view_colleges():
    colleges = College.query.options(db.joinedload(College.majors)).all()  # Fetch all colleges with their majors
    return render_template('view_colleges.html', colleges=colleges)


# Helper function to handle seat allocation logic
def allocate_seats(round_id):
    # Retrieve all students for the given round sorted by rank
    students = Student.query.order_by(Student.rank).all()

    for student in students:
        allocated = False  # Track if the student gets a seat

        # Go through each preference in order for this specific round
        preferences = SeatPreference.query.filter_by(student_id=student.id, round_id=round_id).order_by(SeatPreference.preference_order).all()

        for preference in preferences:
            major = Major.query.filter_by(id=preference.major_id).first()

            # Check if there's an available seat in this major
            if major and major.alloted_seat_count < major.seat_count:
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


@main.route('/update_choice/<int:allotment_id>', methods=['POST'])
def update_choice(allotment_id):
    choice = request.form.get('choice')
    allotment = StudentAllotment.query.get_or_404(allotment_id)

    if choice == 'accept':
        allotment.status = 'active'
        allotment.student.round_furthering = False
    elif choice == 'freeze_and_upgrade':
        allotment.status = 'active'
        allotment.student.round_furthering = True
    elif choice == 'reject_and_upgrade':
        allotment.status = 'inactive'
        allotment.student.round_furthering = True
    elif choice == 'withdraw':
        allotment.status = 'inactive'
        allotment.student.round_furthering = False

    allotment.choice = choice
    db.session.commit()
    flash('Your choice has been updated successfully!', 'success')
    return redirect(url_for('main.student_dashboard'))




