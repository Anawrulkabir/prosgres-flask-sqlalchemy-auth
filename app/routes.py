from flask import request, jsonify, render_template, redirect, url_for, flash
from flask_jwt_extended import create_access_token, jwt_required, get_jwt_identity, get_jwt
from werkzeug.security import generate_password_hash, check_password_hash
from .models import db, User, ResetToken, RevokedToken
from .utils import generate_reset_token, send_reset_email
from datetime import datetime, timedelta
import logging

# Configure logging
logging.basicConfig(level=logging.DEBUG)

def init_routes(app):
    # Web: Signup page
    @app.route('/signup', methods=['GET', 'POST'])
    def signup():
        if request.method == 'POST':
            logging.debug(f"Received signup request with form: {request.form}")
            name = request.form.get('name')
            email = request.form.get('email')
            password = request.form.get('password')

            if not name or not email or not password:
                flash('All fields are required', 'error')
                logging.error("Missing required fields in signup request")
                return render_template('signup.html')

            if User.query.filter_by(email=email).first():
                flash('Email already registered', 'error')
                logging.warning(f"Duplicate email attempted: {email}")
                return render_template('signup.html')

            try:
                hashed_password = generate_password_hash(password, method='pbkdf2:sha256')
                new_user = User(name=name, email=email, password=hashed_password)
                db.session.add(new_user)
                db.session.commit()
                flash('Registration successful! Please sign in.', 'success')
                logging.info(f"User created successfully: {email}")
                return redirect(url_for('signin'))
            except Exception as e:
                db.session.rollback()
                flash(f'Error creating user: {str(e)}', 'error')
                logging.error(f"Error creating user: {str(e)}")
                return render_template('signup.html')
        
        return render_template('signup.html')

    # Web: Sign-in page
    @app.route('/signin', methods=['GET', 'POST'])
    def signin():
        if request.method == 'POST':
            email = request.form.get('email')
            password = request.form.get('password')

            if not email or not password:
                flash('Email and password are required', 'error')
                return render_template('signin.html')

            user = User.query.filter_by(email=email).first()

            if not user or not check_password_hash(user.password, password):
                flash('Invalid email or password', 'error')
                return render_template('signin.html')

            access_token = create_access_token(identity=str(user.id))
            response = redirect(url_for('dashboard'))
            response.set_cookie('access_token', access_token, httponly=True, max_age=3600)
            flash('Sign-in successful!', 'success')
            return response
        
        return render_template('signin.html')

    # Web: Logout
    @app.route('/logout', methods=['POST'])
    @jwt_required()
    def logout():
        jti = get_jwt()['jti']
        try:
            revoked_token = RevokedToken(jti=jti)
            db.session.add(revoked_token)
            db.session.commit()
            logging.info(f"Token revoked: {jti}")
        except Exception as e:
            db.session.rollback()
            logging.error(f"Error revoking token: {str(e)}")
            flash('Error during logout', 'error')
            return redirect(url_for('signin'))
        
        response = redirect(url_for('signin'))
        response.delete_cookie('access_token')
        flash('Logged out successfully', 'success')
        return response

    # Web: Forgot Password
    @app.route('/forgot-password', methods=['GET', 'POST'])
    def forgot_password():
        if request.method == 'POST':
            email = request.form.get('email')
            if not email:
                flash('Email is required', 'error')
                return render_template('forgot_password.html')

            user = User.query.filter_by(email=email).first()
            if not user:
                flash('Email not found', 'error')
                return render_template('forgot_password.html')

            try:
                token = generate_reset_token()
                reset_token = ResetToken(
                    user_id=user.id,
                    token=token,
                    expires_at=datetime.utcnow() + timedelta(hours=1)
                )
                db.session.add(reset_token)
                db.session.commit()

                if send_reset_email(email, token):
                    flash('Password reset email sent', 'success')
                    return redirect(url_for('signin'))
                else:
                    flash('Failed to send reset email', 'error')
                    return render_template('forgot_password.html')
            except Exception as e:
                db.session.rollback()
                flash(f'Error: {str(e)}', 'error')
                logging.error(f"Error in forgot password: {str(e)}")
                return render_template('forgot_password.html')
        
        return render_template('forgot_password.html')

    # Web: Reset Password
    @app.route('/reset-password/<token>', methods=['GET', 'POST'])
    def reset_password(token):
        token_data = ResetToken.query.filter_by(token=token).filter(ResetToken.expires_at > datetime.utcnow()).first()
        if not token_data:
            flash('Invalid or expired token', 'error')
            return redirect(url_for('forgot_password'))

        if request.method == 'POST':
            password = request.form.get('password')
            if not password:
                flash('New password is required', 'error')
                return render_template('reset_password.html', token=token)

            try:
                user = User.query.get(token_data.user_id)
                user.password = generate_password_hash(password, method='pbkdf2:sha256')
                db.session.delete(token_data)
                db.session.commit()
                flash('Password reset successful! Please sign in.', 'success')
                return redirect(url_for('signin'))
            except Exception as e:
                db.session.rollback()
                flash(f'Error: {str(e)}', 'error')
                return render_template('reset_password.html', token=token)
        
        return render_template('reset_password.html', token=token)

    # Web: Dashboard
    @app.route('/dashboard')
    @jwt_required()
    def dashboard():
        current_user_id = get_jwt_identity()
        user = User.query.get(current_user_id)

        if not user:
            flash('User not found', 'error')
            return redirect(url_for('signin'))

        return render_template('dashboard.html', user=user)

    # Web: Public Page
    @app.route('/public')
    def public():
        return render_template('public.html')

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
            return jsonify({'message': 'Invalid credentials'}), 401

        access_token = create_access_token(identity=str(user.id))
        return jsonify({
            'message': 'Sign-in successful',
            'access_token': access_token,
            'user': {'name': user.name, 'email': user.email}
        }), 200

    # API: Logout
    @app.route('/api/logout', methods=['POST'])
    @jwt_required()
    def api_logout():
        jti = get_jwt()['jti']
        try:
            revoked_token = RevokedToken(jti=jti)
            db.session.add(revoked_token)
            db.session.commit()
            logging.info(f"Token revoked: {jti}")
            return jsonify({'message': 'Logout successful. Token revoked.'}), 200
        except Exception as e:
            db.session.rollback()
            logging.error(f"Error revoking token: {str(e)}")
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