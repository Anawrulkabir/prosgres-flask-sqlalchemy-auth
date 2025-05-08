import unittest
import json
from app import create_app

class AuthTestCase(unittest.TestCase):
    def setUp(self):
        self.app = create_app()
        self.client = self.app.test_client()
        self.user_data = {
            'name': 'Test User',
            'email': 'test@example.com',
            'password': 'securepassword'
        }
        with self.app.app_context():
            from app.models import db
            db.create_all()

    def tearDown(self):
        with self.app.app_context():
            from app.models import db
            db.drop_all()

    def test_web_signup(self):
        response = self.client.post('/signup', data=self.user_data, follow_redirects=True)
        self.assertEqual(response.status_code, 200)
        self.assertIn(b'Registration successful', response.data)

    def test_web_signin(self):
        self.client.post('/signup', data=self.user_data)
        response = self.client.post('/signin', data={
            'email': self.user_data['email'],
            'password': self.user_data['password']
        }, follow_redirects=True)
        self.assertEqual(response.status_code, 200)
        self.assertIn(b'Welcome, Test User!', response.data)

    def test_web_forgot_password(self):
        self.client.post('/signup', data=self.user_data)
        response = self.client.post('/forgot-password', data={'email': self.user_data['email']}, follow_redirects=True)
        self.assertEqual(response.status_code, 200)
        self.assertIn(b'Password reset email sent', response.data)

    def test_api_signup(self):
        response = self.client.post('/api/signup', data=self.user_data)
        self.assertEqual(response.status_code, 201)
        self.assertIn('User created successfully', json.loads(response.data)['message'])

    def test_api_signin(self):
        self.client.post('/api/signup', data=self.user_data)
        response = self.client.post('/api/signin', data={
            'email': self.user_data['email'],
            'password': self.user_data['password']
        })
        self.assertEqual(response.status_code, 200)
        self.assertIn('access_token', json.loads(response.data))

if __name__ == '__main__':
    unittest.main()