from flask import Flask
from controllers.database import db
from controllers.routes import main as main_routes
from sqlalchemy import text
from controllers.model import User,Admin
app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///household_services_2519.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.register_blueprint(main_routes)
app.secret_key ='54project'
db.init_app(app)

with app.app_context():
    db.create_all()  # Create database tables

    def insert_admin(username, password, role, email):
        try:
            # Ensure role is set to 'ADMIN' for the admin user
            if role != 'ADMIN':
                print("Invalid role for admin user. Set role to 'ADMIN'.")
                return

            # Create a new Admin instance
            new_admin = Admin(username=username, password=password, role=role, email=email)
            db.session.add(new_admin)  # Add the admin user to the session
            db.session.commit()  # Commit to save changes
            print("Admin inserted successfully")
        except Exception as e:
            db.session.rollback()  # Rollback in case of error
            print(f"Error inserting admin: {e}")

        # Insert a new user
    insert_admin('taylor', 'taylor', 'ADMIN', 'taylor@gmail.com')
    insert_admin('scoups', 'scoups', 'ADMIN', 'scoups@gmail.com')
# Register blueprints
#app.register_blueprint(main_routes)

if __name__ == '__main__':
    app.run(debug=True)

