from controllers.model import User
from controllers.database import db
users=User.query.all()
print(users)