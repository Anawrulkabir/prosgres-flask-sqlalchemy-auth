# Flask JWT Auth

A simple Flask app with JWT authentication, PostgreSQL database, and pgAdmin for management.

## Architecture

```
Flask App <--> PostgreSQL <--> pgAdmin
  (Port 5001)    (Port 5002)    (Port 5050)
```

- **Flask App**: Serves API for signup, signin, etc.
- **PostgreSQL**: Stores user data in `auth_db`.
- **pgAdmin**: Web GUI for database management.

---

## Prerequisites

- Docker
- Docker Compose

---

## Setup

1. **Clone Repository**:

   ```bash
   git clone https://github.com/Anawrulkabir/prosgres-flask-sqlalchemy-auth.git
   cd prosgres-flask-sqlalchemy-auth
   ```

2. **Run Application**:

   ```bash
   docker-compose up -d
   ```

3. **Initialize Database**:
   ```bash
   docker-compose exec app python init-schema.py
   ```

---

## Ports

- **5001**: Flask API - [http://localhost:5001/api/signup](http://localhost:5001/api/signup)
- **5002**: PostgreSQL - Connect via:
  ```bash
  psql -h localhost -U user -d auth_db -p 5002
  ```
- **5050**: pgAdmin GUI - [http://localhost:5050](http://localhost:5050)  
  Login: `admin@admin.com` / `admin`

---

## API Routes

| Method | Route                         | Description                |
| ------ | ----------------------------- | -------------------------- |
| POST   | `/api/signup`                 | Create a new user.         |
| POST   | `/api/signin`                 | Sign in and get JWT token. |
| GET    | `/api/dashboard`              | View user dashboard (JWT). |
| POST   | `/api/logout`                 | Log out (JWT).             |
| POST   | `/api/forgot-password`        | Request password reset.    |
| POST   | `/api/reset-password/<token>` | Reset password with token. |

### Example: Signup

```bash
curl -X POST http://localhost:5001/api/signup \
-H "Content-Type: application/json" \
-d '{"name":"testuser","email":"test@example.com","password":"test123"}'
```

---

## Database Access

### pgAdmin

- **URL**: [http://localhost:5050](http://localhost:5050)
- **Login**: `admin@admin.com` / `admin`
- **Add Server**:
  - Host: `db` or `localhost`
  - Port: `5432` or `5002`
  - Database: `auth_db`
  - User: `user`
  - Password: `password`

### psql

```bash
psql -h localhost -U user -d auth_db -p 5002
```

---

## Troubleshooting

- **No database in pgAdmin**:

  - Refresh: `Schemas > public > Tables`.
  - Re-add server with correct host/port.

- **Check logs**:

  ```bash
  docker-compose logs app
  ```

- **Stop Application**:
  ```bash
  docker-compose down
  ```
