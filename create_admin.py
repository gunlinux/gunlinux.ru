#!/usr/bin/env python3
"""
CLI tool to create admin users for the blog application.
This version creates a minimal Flask app context to avoid blueprint conflicts.
"""

import sys
import os
import getpass

# Add the project root to the Python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

def create_admin_user(name, password):
    """Create an admin user with minimal app context."""
    # Import only what we need
    from flask import Flask
    from blog.config import config
    from blog.extensions import db
    from blog.user.models import User
    
    # Create a minimal app
    app = Flask(__name__)
    app.config.from_object(config.get('development'))
    
    # Initialize only the database
    db.init_app(app)
    
    with app.app_context():
        # Check if user already exists
        existing_user = db.session.execute(
            db.select(User).where(User.name == name)
        ).scalar_one_or_none()
        
        if existing_user:
            print("User '{}' already exists.".format(name))
            return False
        
        # Create new user
        user = User(name=name)
        user.set_password(password)
        
        # Add to database
        db.session.add(user)
        db.session.commit()
        
        print("Admin user '{}' created successfully.".format(name))
        return True


if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="Create an admin user for the blog.")
    parser.add_argument("name", help="Username for the admin user")
    parser.add_argument("--password", help="Password for the admin user (will prompt if not provided)")
    
    args = parser.parse_args()
    
    # Get password from command line or prompt
    if args.password:
        password = args.password
    else:
        password = getpass.getpass("Password: ")
        confirm_password = getpass.getpass("Confirm Password: ")
        if password != confirm_password:
            print("Passwords do not match.")
            sys.exit(1)
    
    success = create_admin_user(args.name, password)
    sys.exit(0 if success else 1)