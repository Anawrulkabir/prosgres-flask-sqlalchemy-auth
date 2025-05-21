# Chapter 1: Building a JWT Authentication System with Flask and PostgreSQL

Welcome to this comprehensive course on building a secure authentication system! In this first chapter, we'll build a JWT-based authentication system from scratch using Flask, PostgreSQL, and SQLAlchemy.

## Table of Contents

- [Introduction](#introduction)
- [Prerequisites](#prerequisites)
- [Project Setup](#project-setup)
- [Flask Application Structure](#flask-application-structure)
- [Database Models](#database-models)
- [Implementing Authentication Routes](#implementing-authentication-routes)
- [Testing with Postman](#testing-with-postman)
- [Dockerizing the Application](#dockerizing-the-application)
- [Running with Docker Compose](#running-with-docker-compose)
- [Conclusion](#conclusion)

## Introduction

Authentication is a crucial component of web applications. In this chapter, we'll implement a JSON Web Token (JWT) based authentication system that provides:

- User registration (signup)
- User login (signin) with JWT token generation
- Protected routes accessible only to authenticated users
- Token refresh mechanism
- Logout functionality
- Password reset capabilities

We'll use Flask for our backend framework, PostgreSQL for our database, and SQLAlchemy as our ORM.

## Prerequisites

Before we start, ensure you have the following installed:

- Python 3.11 or higher
- pip (Python package manager)
- Git
- Docker and Docker Compose
- Postman (for API testing)

## Project Setup

Let's start by setting up our project structure:

```bash
# Create project directory
mkdir flask-jwt-auth
cd flask-jwt-auth

# Create virtual environment
python -m venv venv
source venv/bin/activate  # On Windows, use: venv\Scripts\activate

# Create basic project structure
mkdir -p app migrations assets test
touch app/__init__.py app/models.py app/routes.py app/utils.py
touch migrations/init.sql
touch requirements.txt .env .env.pgAdmin .gitignore README.md
```

Now, let's define our dependencies in `requirements.txt`:

```
Flask
Flask-JWT-Extended
Flask-SQLAlchemy
psycopg2-binary
werkzeug
gunicorn
python-dotenv
```

Install the dependencies:

```bash
pip install -r requirements.txt
```

## Flask Application Structure

Our Flask application will follow a modular structure. Let's start by creating the application factory in `app/__init__.py`:

```python
# filepath: app/__init__.py
from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from flask_jwt_extended import JWTManager
from dotenv import load_dotenv
import os

db = SQLAlchemy()
jwt = JWTManager()
load_dotenv()

def create_app():
    app = Flask(__name__)

    # Configurations
    app.config['SQLALCHEMY_DATABASE_URI'] = os.getenv('DATABASE_URL')
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
    app.config['JWT_SECRET_KEY'] = os.getenv('JWT_SECRET_KEY')
    app.config['SECRET_KEY'] = os.getenv('SECRET_KEY')
    app.config['JWT_ACCESS_TOKEN_EXPIRES'] = 3600  # 1 hour
    app.config['JWT_REFRESH_TOKEN_EXPIRES'] = 604800  # 7 days

    # Initialize extensions
    db.init_app(app)
    jwt.init_app(app)

    # Import and register routes
    from .routes import init_routes
    init_routes(app)

    # Create database tables
    with app.app_context():
        db.create_all()

    # JWT blacklist check
    @jwt.token_in_blocklist_loader
    def check_if_token_revoked(jwt_header, jwt_payload):
        jti = jwt_payload['jti']
        token = RevokedToken.query.filter_by(jti=jti).first()
        return token is not None

    return app

from .models import RevokedToken  # Import here to avoid circular imports
```

Let's create an entry point for our application by creating an `app.py` file in the project root:

```python
# filepath: app.py
from app import create_app

app = create_app()

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5001, debug=True)
```

## Database Models

Now, let's define our database models in `app/models.py`:

```python
# filepath: app/models.py
from . import db
from datetime import datetime

class User(db.Model):
    __tablename__ = 'users'

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password = db.Column(db.String(255), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    def __repr__(self):
        return f'<User {self.email}>'

class ResetToken(db.Model):
    __tablename__ = 'reset_tokens'

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    token = db.Column(db.String(100), unique=True, nullable=False)
    expires_at = db.Column(db.DateTime, nullable=False)
    user = db.relationship('User', backref=db.backref('reset_tokens', lazy=True))

    def __repr__(self):
        return f'<ResetToken {self.token}>'

class RevokedToken(db.Model):
    __tablename__ = 'revoked_tokens'

    id = db.Column(db.Integer, primary_key=True)
    jti = db.Column(db.String(120), unique=True, nullable=False)
    revoked_at = db.Column(db.DateTime, default=datetime.utcnow)

    def __repr__(self):
        return f'<RevokedToken {self.jti}>'

class RefreshToken(db.Model):
    __tablename__ = 'refresh_tokens'

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    token = db.Column(db.String(1000), nullable=False, unique=True)
    expires_at = db.Column(db.DateTime, nullable=False)
    user = db.relationship('User', backref=db.backref('refresh_tokens', lazy=True))

    def __repr__(self):
        return f'<RefreshToken {self.token}>'
```

Let's also create an SQL initialization script in `migrations/init.sql` for our Docker setup:

```sql
-- filepath: migrations/init.sql
CREATE TABLE IF NOT EXISTS users (
    id SERIAL PRIMARY KEY,
    name VARCHAR(100) NOT NULL,
    email VARCHAR(120) UNIQUE NOT NULL,
    password VARCHAR(255) NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS reset_tokens (
    id SERIAL PRIMARY KEY,
    user_id INTEGER REFERENCES users(id) ON DELETE CASCADE,
    token VARCHAR(100) NOT NULL UNIQUE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    expires_at TIMESTAMP NOT NULL
);

CREATE TABLE IF NOT EXISTS revoked_tokens (
    id SERIAL PRIMARY KEY,
    jti VARCHAR(120) NOT NULL UNIQUE,
    revoked_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS refresh_tokens (
    id SERIAL PRIMARY KEY,
    user_id INTEGER REFERENCES users(id) ON DELETE CASCADE,
    token VARCHAR(1000) NOT NULL UNIQUE,
    expires_at TIMESTAMP NOT NULL
);
```

## Implementing Authentication Routes

Now let's implement our authentication routes in `app/routes.py`:

```python
# filepath: app/routes.py
from flask import request, jsonify
from flask_jwt_extended import create_access_token, create_refresh_token, jwt_required, get_jwt_identity, get_jwt
from werkzeug.security import generate_password_hash, check_password_hash
from .models import db, User, ResetToken, RevokedToken, RefreshToken
from .utils import generate_reset_token, send_reset_email
from datetime import datetime, timedelta
import logging

# Configure logging
logging.basicConfig(level=logging.DEBUG)

def init_routes(app):
    # API: Signup
    @app.route('/api/signup', methods=['POST'])
    def api_signup():
        if not request.is_json:
            logging.error("Request must have Content-Type: application/json")
            return jsonify({'message': 'Content-Type must be application/json'}), 415

        try:
            data = request.get_json()
            logging.debug(f"Received API signup request with JSON: {data}")
        except Exception as e:
            logging.error(f"Invalid JSON payload: {str(e)}")
            return jsonify({'message': 'Invalid JSON payload'}), 400

        name = data.get('name')
        email = data.get('email')
        password = data.get('password')

        if not name or not email or not password:
            logging.error("Missing required fields in API signup request")
            return jsonify({'message': 'Missing required fields'}), 400

        if User.query.filter_by(email=email).first():
            logging.warning(f"Duplicate email attempted in API: {email}")
            return jsonify({'message': 'User already exists'}), 400

        try:
            hashed_password = generate_password_hash(password, method='pbkdf2:sha256')
            new_user = User(name=name, email=email, password=hashed_password)
            db.session.add(new_user)
            db.session.commit()
            logging.info(f"User created successfully via API: {email}")
            return jsonify({'message': 'User created successfully'}), 201
        except Exception as e:
            db.session.rollback()
            logging.error(f"Error creating user via API: {str(e)}")
            return jsonify({'message': 'Error creating user', 'error': str(e)}), 500

    # API: Sign-in
    @app.route('/api/signin', methods=['POST'])
    def api_signin():
        if not request.is_json:
            return jsonify({'message': 'Content-Type must be application/json'}), 415

        try:
            data = request.get_json()
        except Exception as e:
            return jsonify({'message': 'Invalid JSON payload'}), 400

        email = data.get('email')
        password = data.get('password')

        if not email or not password:
            return jsonify({'message': 'Missing email or password'}), 400

        user = User.query.filter_by(email=email).first()

        if not user or not check_password_hash(user.password, password):
            logging.warning(f"Invalid sign-in attempt for email: {email}")
            return jsonify({'message': 'Invalid credentials'}), 401

        try:
            access_token = create_access_token(identity=str(user.id))
            refresh_token = create_refresh_token(identity=str(user.id))
            # Store refresh token
            expires = datetime.utcnow() + timedelta(seconds=604800)  # 7 days
            new_refresh_token = RefreshToken(user_id=user.id, token=refresh_token, expires_at=expires)
            db.session.add(new_refresh_token)
            db.session.commit()
            logging.info(f"Sign-in successful for user: {email}")
            return jsonify({
                'message': 'Sign-in successful',
                'access_token': access_token,
                'refresh_token': refresh_token,
                'user': {'name': user.name, 'email': user.email}
            }), 200
        except Exception as e:
            db.session.rollback()
            logging.error(f"Error during sign-in: {str(e)}")
            return jsonify({'message': 'Error during sign-in', 'error': str(e)}), 500

    # API: Refresh Token
    @app.route('/api/refresh', methods=['POST'])
    @jwt_required(refresh=True)
    def api_refresh():
        current_user = get_jwt_identity()
        refresh_jti = get_jwt()['jti']

        try:
            token = RefreshToken.query.filter_by(token=refresh_jti, user_id=int(current_user)).first()
            if not token or token.expires_at <= datetime.utcnow():
                logging.warning(f"Invalid or expired refresh token for user_id: {current_user}")
                return jsonify({'message': 'Invalid or expired refresh token'}), 401

            new_access_token = create_access_token(identity=current_user)
            logging.info(f"Access token refreshed for user_id: {current_user}")
            return jsonify({
                'message': 'Token refreshed successfully',
                'access_token': new_access_token
            }), 200
        except Exception as e:
            logging.error(f"Error refreshing token: {str(e)}")
            return jsonify({'message': 'Error refreshing token', 'error': str(e)}), 500

    # API: Logout
    @app.route('/api/logout', methods=['POST'])
    @jwt_required()
    def api_logout():
        jti = get_jwt()['jti']
        try:
            # Revoke access token
            revoked_token = RevokedToken(jti=jti)
            db.session.add(revoked_token)
            # Revoke refresh token
            refresh_jti = get_jwt()['jti']
            refresh_token = RefreshToken.query.filter_by(token=refresh_jti).first()
            if refresh_token:
                db.session.delete(refresh_token)
            db.session.commit()
            logging.info(f"Logout successful, tokens revoked: {jti}")
            return jsonify({'message': 'Logout successful. Tokens revoked.'}), 200
        except Exception as e:
            db.session.rollback()
            logging.error(f"Error revoking tokens: {str(e)}")
            return jsonify({'message': 'Error during logout', 'error': str(e)}), 500

    # API: Forgot Password
    @app.route('/api/forgot-password', methods=['POST'])
    def api_forgot_password():
        if not request.is_json:
            return jsonify({'message': 'Content-Type must be application/json'}), 415

        try:
            data = request.get_json()
        except Exception as e:
            return jsonify({'message': 'Invalid JSON payload'}), 400

        email = data.get('email')
        if not email:
            return jsonify({'message': 'Email is required'}), 400

        user = User.query.filter_by(email=email).first()
        if not user:
            return jsonify({'message': 'Email not found'}), 404

        try:
            token = generate_reset_token()
            reset_token = ResetToken(
                user_id=user.id,
                token=token,
                expires_at=datetime.utcnow() + timedelta(hours=1)
            )
            db.session.add(reset_token)
            db.session.commit()
            logging.info(f"Password reset token generated for user: {email}")

            if send_reset_email(email, token):
                return jsonify({'message': 'Password reset email sent'}), 200
            else:
                return jsonify({'message': 'Failed to send reset email'}), 500
        except Exception as e:
            db.session.rollback()
            logging.error(f"Error in API forgot password: {str(e)}")
            return jsonify({'message': 'Error processing request', 'error': str(e)}), 500

    # API: Reset Password
    @app.route('/api/reset-password/<token>', methods=['POST'])
    def api_reset_password(token):
        if not request.is_json:
            return jsonify({'message': 'Content-Type must be application/json'}), 415

        try:
            data = request.get_json()
        except Exception as e:
            return jsonify({'message': 'Invalid JSON payload'}), 400

        password = data.get('password')
        if not password:
            return jsonify({'message': 'New password is required'}), 400

        token_data = ResetToken.query.filter_by(token=token).filter(ResetToken.expires_at > datetime.utcnow()).first()
        if not token_data:
            return jsonify({'message': 'Invalid or expired token'}), 400

        try:
            user = User.query.get(token_data.user_id)
            user.password = generate_password_hash(password, method='pbkdf2:sha256')
            db.session.delete(token_data)
            db.session.commit()
            logging.info(f"Password reset successful for user: {user.email}")
            return jsonify({'message': 'Password reset successful'}), 200
        except Exception as e:
            db.session.rollback()
            logging.error(f"Error resetting password: {str(e)}")
            return jsonify({'message': 'Error resetting password', 'error': str(e)}), 500

    # API: Dashboard
    @app.route('/api/dashboard', methods=['GET'])
    @jwt_required()
    def api_dashboard():
        current_user_id = get_jwt_identity()
        user = User.query.get(current_user_id)

        if not user:
            return jsonify({'message': 'User not found'}), 404

        return jsonify({
            'message': f'Welcome {user.name}!',
            'user': {'name': user.name, 'email': user.email}
        }), 200

    # API: Public
    @app.route('/api/public', methods=['GET'])
    def api_public():
        return jsonify({'message': 'This is a public endpoint'}), 200

    # base route
    @app.route('/' , methods=['GET'])
    def base_route():
        return jsonify({'message': 'Welcome to JWT Auth API', 'status': 'online'}), 200
```

Let's implement the utility functions in `app/utils.py`:

```python
# filepath: app/utils.py
import smtplib
import uuid
from email.mime.text import MIMEText

def generate_reset_token():
    return str(uuid.uuid4())

def send_reset_email(email, token):
    try:
        msg = MIMEText(f"Click to reset your password: http://localhost:5000/reset-password/{token}")
        msg['Subject'] = 'Password Reset Request'
        msg['From'] = 'no-reply@flaskapp.com'
        msg['To'] = email

        print(f"Sending reset email to {email} with token {token}")
        return True
    except Exception as e:
        print(f"Email sending failed: {str(e)}")
        return False
```

Create a `.env` file to store our environment variables:

```
DATABASE_URL=postgresql://user:password@db:5432/auth_db
JWT_SECRET_KEY=your-secret-key
SECRET_KEY=your-flask-secret-key
POSTGRES_USER=user
POSTGRES_PASSWORD=password
POSTGRES_DB=auth_db
```

Create a `.env.pgAdmin` file for pgAdmin configuration:

```
PGADMIN_DEFAULT_EMAIL=admin@admin.com
PGADMIN_DEFAULT_PASSWORD=admin
```

Create a `.gitignore` file to exclude sensitive files:

```
# Python specific
__pycache__/
*.py[cod]
*.pyo
*.pyd
*.env
*.venv
*.egg
*.egg-info/
dist/
build/
*.log

# Flask specific
instance/
*.sqlite3

# Environment variables
.env
.env.pgAdmin

# macOS specific
.DS_Store

# Docker specific
docker-compose.override.yml
*.pid

# Logs
logs/
*.log

# Other
*.swp
*.swo
```

## Testing with Postman

Let's create a Postman collection to test our API endpoints. Create a new file called `jwt_auth.postman_collection.json` with the following content:

```json
{
  "info": {
    "_postman_id": "044b382c-e732-4503-9b4d-cceb3193737a",
    "name": "JWT Auth API",
    "schema": "https://schema.getpostman.com/json/collection/v2.1.0/collection.json"
  },
  "item": [
    {
      "name": "Signup API",
      "request": {
        "method": "POST",
        "header": [],
        "body": {
          "mode": "raw",
          "raw": "{\n    \"name\": \"Test User\",\n    \"email\": \"test@example.com\",\n    \"password\": \"password123\"\n}",
          "options": {
            "raw": {
              "language": "json"
            }
          }
        },
        "url": {
          "raw": "http://localhost:5001/api/signup",
          "protocol": "http",
          "host": ["localhost"],
          "port": "5001",
          "path": ["api", "signup"]
        }
      },
      "response": []
    },
    {
      "name": "Signin API",
      "request": {
        "method": "POST",
        "header": [],
        "body": {
          "mode": "raw",
          "raw": "{\n    \"email\" : \"test@example.com\",\n    \"password\" : \"password123\"\n}",
          "options": {
            "raw": {
              "language": "json"
            }
          }
        },
        "url": {
          "raw": "http://localhost:5001/api/signin",
          "protocol": "http",
          "host": ["localhost"],
          "port": "5001",
          "path": ["api", "signin"]
        }
      },
      "response": []
    },
    {
      "name": "Protected Route",
      "request": {
        "method": "GET",
        "header": [
          {
            "key": "Authorization",
            "value": "Bearer {{jwt_token}}",
            "type": "text"
          }
        ],
        "url": {
          "raw": "http://localhost:5001/api/dashboard",
          "protocol": "http",
          "host": ["localhost"],
          "port": "5001",
          "path": ["api", "dashboard"]
        }
      },
      "response": []
    },
    {
      "name": "Forgot Password",
      "request": {
        "method": "POST",
        "header": [],
        "body": {
          "mode": "raw",
          "raw": "{\n    \"email\" : \"test@example.com\"\n}",
          "options": {
            "raw": {
              "language": "json"
            }
          }
        },
        "url": {
          "raw": "http://localhost:5001/api/forgot-password",
          "protocol": "http",
          "host": ["localhost"],
          "port": "5001",
          "path": ["api", "forgot-password"]
        }
      },
      "response": []
    },
    {
      "name": "Logout",
      "request": {
        "method": "POST",
        "header": [
          {
            "key": "Authorization",
            "value": "Bearer {{jwt_token}}",
            "type": "text"
          }
        ],
        "body": {
          "mode": "raw",
          "raw": "{}"
        },
        "url": {
          "raw": "http://localhost:5001/api/logout",
          "protocol": "http",
          "host": ["localhost"],
          "port": "5001",
          "path": ["api", "logout"]
        }
      },
      "response": []
    }
  ]
}
```

Before moving on to Dockerization, let's test our application locally:

```bash
export FLASK_APP=app
export FLASK_ENV=development
flask run --host=0.0.0.0 --port=5001
```

## Dockerizing the Application

Let's create a `Dockerfile` to containerize our Flask application:

```dockerfile
FROM python:3.11-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install -r requirements.txt

COPY . .

ENV FLASK_APP=app
ENV FLASK_ENV=production

EXPOSE 5001

CMD ["gunicorn", "--bind", "0.0.0.0:5001", "app:create_app()"]
```

Build and push the Docker image to Docker Hub (ensure you're logged in to Docker Hub):

```bash
docker build -t yourusername/flask-jwt-auth:latest .
docker push yourusername/flask-jwt-auth:latest
```

## Running with Docker Compose

Let's create a `docker-compose.yml` file to run our application along with PostgreSQL and pgAdmin:

```yaml
version: '3.8'

services:
  app:
    image: yourusername/flask-jwt-auth:latest
    ports:
      - '5001:5001' # Map host port 5001 to container port 5001
    environment:
      - DATABASE_URL=${DATABASE_URL}
      - JWT_SECRET_KEY=${JWT_SECRET_KEY}
      - SECRET_KEY=${SECRET_KEY}
    depends_on:
      db:
        condition: service_healthy
    networks:
      - auth-network

  db:
    image: postgres:13
    environment:
      - POSTGRES_USER=${POSTGRES_USER}
      - POSTGRES_PASSWORD=${POSTGRES_PASSWORD}
      - POSTGRES_DB=${POSTGRES_DB}
    volumes:
      - postgres_data:/var/lib/postgresql/data
      - ./migrations/init.sql:/docker-entrypoint-initdb.d/init.sql
    ports:
      - '5002:5432' # Expose PostgreSQL port to host
    healthcheck:
      test: ['CMD-SHELL', 'pg_isready -U ${POSTGRES_USER} -d ${POSTGRES_DB}']
      interval: 5s
      timeout: 5s
      retries: 5
    networks:
      - auth-network

  pgadmin:
    image: dpage/pgadmin4:latest
    env_file:
      - .env.pgAdmin
    ports:
      - '5050:80' # Expose pgAdmin web interface on port 5050
    depends_on:
      - db
    networks:
      - auth-network

volumes:
  postgres_data:

networks:
  auth-network:
    driver: bridge
```

Run the application using Docker Compose:

```bash
docker-compose up -d
```

Test the application by accessing the following URLs:

- Flask API: http://localhost:5001/api/public
- pgAdmin: http://localhost:5050 (login with admin@admin.com / admin)

## Conclusion

Congratulations! You've built a complete JWT authentication system with Flask and PostgreSQL. In this chapter, you learned:

1. How to structure a Flask application using the application factory pattern
2. How to model database entities with SQLAlchemy
3. How to implement JWT authentication with Flask-JWT-Extended
4. How to handle tokens, including refresh, revocation, and blacklisting
5. How to implement password reset functionality
6. How to dockerize your application and run it with Docker Compose

In the next chapter, we'll deploy our application to AWS, allowing it to be accessed from anywhere.

Use the Postman collection to test all the authentication endpoints:

1. Register a user with the `/api/signup` endpoint
2. Login with the `/api/signin` endpoint to get JWT tokens
3. Access the protected dashboard with the access token
4. Try the password reset flow
5. Logout to revoke the tokens

Great work! You've successfully built a secure Flask authentication system with JWT.
