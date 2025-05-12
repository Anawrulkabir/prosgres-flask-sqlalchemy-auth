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