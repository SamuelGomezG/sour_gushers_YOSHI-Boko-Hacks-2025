from werkzeug.security import generate_password_hash, check_password_hash
from extensions import db
from sqlalchemy import text

class User(db.Model):
    __tablename__ = "users"
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(150), unique=True, nullable=False)
    password_hash = db.Column(db.String(200), nullable=False)
    
    def set_password(self, password):
        """Hashes password and stores it."""
        self.password_hash = generate_password_hash(password)
        
    def check_password(self, password) -> bool:
        """Compares hashed password to user-provided password."""
        return check_password_hash(self.password_hash, password)
    
    @property
    def is_admin(self):
        """
        Check if the user is an admin by querying the admin_credentials table.
        This avoids defining a new model for the admin_credentials table
        which is already defined elsewhere in the application.
        """
        # Use raw SQL query to check if user_id exists in admin_credentials table
        sql = text("SELECT 1 FROM admin_credentials WHERE user_id = :user_id LIMIT 1")
        result = db.session.execute(sql, {"user_id": self.id})
        return result.scalar() is not None
        
    def __repr__(self):
        return f"<User {self.username}>"