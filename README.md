# Flask JWT Authentication System

A secure and scalable JWT authentication system built with Flask, PostgreSQL, and pgAdmin.

## Table of Contents

- [JWT Authentication](#jwt-authentication)
- [Project Architecture](#project-architecture)
- [Getting Started](#getting-started)
  - [Prerequisites](#prerequisites)
  - [Setup](#setup)
- [Service Access](#service-access)
- [API Documentation](#api-documentation)
  - [Authentication Flow](#authentication-flow)
  - [API Examples](#examples)
- [Database Management](#database-management)
- [Development](#development)
- [Testing with Postman](#testing-with-postman)
- [Troubleshooting](#troubleshooting)
- [License](#license)
- [Author](#author)

## JWT Authentication

![JWT Architecture](assets/image1.svg)

JSON Web Tokens (JWT) is an open standard (RFC 7519) that defines a compact and self-contained way for securely transmitting information between parties as a JSON object. JWTs are commonly used for authentication and information exchange in web applications.

### How JWT Works

1. **User Authentication**: User logs in with credentials
2. **Token Generation**: Server validates credentials and issues a signed JWT
3. **Token Storage**: Client stores the token (browser storage, mobile keychain)
4. **Protected Requests**: Client includes the token in request headers
5. **Token Verification**: Server validates the token signature before processing requests

JWTs consist of three parts separated by dots (`.`):

- **Header**: Identifies the algorithm used to sign the token
- **Payload**: Contains claims (statements about the user and metadata)
- **Signature**: Ensures the token hasn't been altered

This implementation uses both access tokens (short-lived) and refresh tokens (long-lived) for enhanced security.

## Project Architecture

![Project Architecture](assets/image2.svg)

### Components

- **Flask App**: REST API with JWT authentication, user management, and password reset functionality
- **PostgreSQL**: Relational database storing user data and tokens
- **pgAdmin**: Web-based administration tool for PostgreSQL database management

## Getting Started

### Prerequisites

- Docker
- Docker Compose

### Setup

1. **Clone Repository**:

   ```bash
   git clone https://github.com/Anawrulkabir/prosgres-flask-sqlalchemy-auth.git
   cd prosgres-flask-sqlalchemy-auth
   ```

2. **Configure Environment Variables**:

   Create a `.env` file with the following variables:

   ```properties
   DATABASE_URL=postgresql://user:password@db:5432/auth_db
   JWT_SECRET_KEY=your-secure-jwt-key
   SECRET_KEY=your-secure-flask-key
   POSTGRES_USER=user
   POSTGRES_PASSWORD=password
   POSTGRES_DB=auth_db
   ```

   For pgAdmin, create a `.env.pgAdmin` file:

   ```properties
   PGADMIN_DEFAULT_EMAIL=admin@admin.com
   PGADMIN_DEFAULT_PASSWORD=admin
   ```

3. **Run Application**:

   ```bash
   docker-compose up -d
   ```

4. **Initialize Database**:

   ```bash
   docker-compose exec app python init-schema.py
   ```

5. **Verify Services**:
   - Flask API: [http://localhost:5001/api/public](http://localhost:5001/api/public)
   - pgAdmin: [http://localhost:5050](http://localhost:5050)

## Service Access

- **Flask API** - Port 5001: [http://localhost:5001](http://localhost:5001)
- **PostgreSQL** - Port 5002: Connect via:
  ```bash
  psql -h localhost -U user -d auth_db -p 5002
  ```
- **pgAdmin** - Port 5050: [http://localhost:5050](http://localhost:5050)  
  Login: `admin@admin.com` / `admin`

## API Documentation

| Method | Endpoint | Description | Auth Required |
| --- | --- | --- | --- |
| POST | `/api/signup` | Register a new user | No |
| POST | `/api/signin` | Sign in and get JWT tokens | No |
| POST | `/api/refresh` | Refresh access token | Refresh Token |
| GET | `/api/dashboard` | Access protected dashboard | Access Token |
| POST | `/api/logout` | Revoke tokens | Access Token |
| POST | `/api/forgot-password` | Request password reset | No |
| POST | `/api/reset-password/<token>` | Reset password with token | No |
| GET | `/api/public` | Public endpoint example | No |
| GET | `/` | Public endpoint example | No |

### Authentication Flow

1. Register a user with `/api/signup`
2. Sign in with `/api/signin` to receive access and refresh tokens
3. Use access token in Authorization header: `Bearer <access_token>`
4. When access token expires, use refresh token with `/api/refresh`
5. Log out with `/api/logout` to revoke tokens

### Examples

#### Register a User

```bash
curl -X POST http://localhost:5001/api/signup \
-H "Content-Type: application/json" \
-d '{"name":"John Doe","email":"john@example.com","password":"SecurePass123"}'
```

#### Sign In

```bash
curl -X POST http://localhost:5001/api/signin \
-H "Content-Type: application/json" \
-d '{"email":"john@example.com","password":"SecurePass123"}'
```

#### Access Protected Route

```bash
curl -X GET http://localhost:5001/api/dashboard \
-H "Authorization: Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9..."
```

#### Refresh Token

```bash
curl -X POST http://localhost:5001/api/refresh \
-H "Authorization: Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9..."
```

## Database Management

### pgAdmin Connection

1. Open [http://localhost:5050](http://localhost:5050)
2. Log in with `admin@admin.com` / `admin`
3. Add a new server:
   - Name: `PostgreSQL`
   - Connection tab:
     - Host: `db` (when connected within Docker network) or `localhost` (external)
     - Port: `5432` (internal) or `5002` (external)
     - Database: `auth_db`
     - Username: `user`
     - Password: `password`

### Database Schema

The application uses the following tables:

- **users**: User account information
- **refresh_tokens**: Long-lived tokens for generating new access tokens
- **revoked_tokens**: Blacklisted tokens that have been logged out
- **reset_tokens**: Temporary tokens for password reset

## Development

### Testing the API

A Postman collection (`jwt_auth.postman_collection.json`) is included for testing the API endpoints.

### Run Tests

```bash
docker-compose exec app python -m pytest
```

### Building a New Docker Image

```bash
docker build -t your-username/flask-jwt-auth:latest .
docker push your-username/flask-jwt-auth:latest
```

## Troubleshooting

- **Database Connection Issues**:

  ```bash
  docker-compose exec db psql -U user -d auth_db -c "SELECT 1"
  ```

- **Check Container Logs**:

  ```bash
  docker-compose logs app
  docker-compose logs db
  ```

- **Reset All Containers and Data**:

  ```bash
  docker-compose down -v
  docker-compose up -d
  ```

- **No Tables in pgAdmin**:
  - Refresh the browser
  - Navigate to: Servers > PostgreSQL > Databases > auth_db > Schemas > public > Tables
  - Right-click and refresh

## Testing with Postman

This repository includes a Postman collection `jwt_auth.postman_collection.json` that you can use to quickly test all API endpoints.

### Import the Collection

1. Open Postman
2. Click on "Import" button in the top-left corner
3. Select "File" and choose `jwt_auth.postman_collection.json` from the project directory
4. Click "Import"

### Test Endpoints

The collection includes ready-to-use requests for:

- User signup
- User signin
- Accessing protected routes
- Password reset flow
- Logging out

### Usage Tips

1. **Execute in Order**: Start with signup, then signin to get your tokens
2. **Auth Token**: After signin, the access token is automatically used for protected routes
3. **Test Environment**: All requests are configured for `localhost:5001`

### Example Workflow

1. Run the "Signup API" request with your credentials
2. Run the "Signin API" request to get your tokens
3. The "Protected Route" request should now work with the token
4. Use "Logout" to invalidate your token

The collection includes example data, but you can modify request bodies as needed.

## License

MIT

## Author

Created by Anawrul Kabir
