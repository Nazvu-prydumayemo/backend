# NP-Tennis Backend

A feature-based REST API for the NP-Tennis court booking system, built with FastAPI, SQLAlchemy 2.0, and PostgreSQL.

Manage courts, user accounts, orders, and email notifications -- all served over HTTP to a Textual TUI frontend.

## Features

- **Authentication** -- Register, login with email/password, JWT access + refresh token flow, OAuth2-compatible form login for Swagger UI
- **Password Reset** -- Request a 6-digit reset code via email, verify the code, and set a new password
- **Account Management** -- View profile, update name, change password, delete account (GDPR erasure), export personal data (GDPR right of access)
- **Court Management** -- Create, read, update, delete courts; configure surface type, location, price per hour, and facility (indoor/outdoor)
- **Weekly Schedule** -- Set opening/closing hours per day-of-week for each court; mark days as closed
- **Booking Slots** -- Auto-generated 30-minute intervals from schedule; query available slots for a specific date (up to 7 days ahead)
- **Order Management** -- Book one or more slots in a single all-or-nothing transaction; view order history and details
- **Email Notifications** -- Welcome email on registration, booking confirmation with time ranges, password reset code delivery (via `fastapi-mail`)
- **Booking Reminders** -- APScheduler-based reminder 1 hour before the first slot of an order; recovers pending reminders on server restart
- **Role-Based Access Control** -- Admin role guard for court/schedule management; active user guard for protected endpoints
- **Centralized Logging** -- Structured JSON logging with optional Loki shipping and Grafana dashboards
- **OpenAPI Documentation** -- Auto-generated docs at `/docs` (disabled in production)
- **Dockerized Deployment** -- PostgreSQL, Loki, Grafana, Nginx, and the backend via `docker-compose`

## Prerequisites

- Python **3.11+**
- PostgreSQL **15+** (or Docker for containerized database)
- SMTP server for email features (optional, email features gracefully degrade)

## Installation

### 1. Create a virtual environment

**Windows:**

```bash
py -m venv .venv
```

**Linux/macOS:**

```bash
python3 -m venv .venv
```

### 2. Activate the virtual environment

**Windows (PowerShell):**

```powershell
.venv\Scripts\Activate.ps1
```

**Windows (cmd):**

```cmd
.venv\Scripts\activate
```

**Linux/macOS:**

```bash
source .venv/bin/activate
```

### 3. Install dependencies

```bash
pip install -e ".[dev]"
```

Or using Make:

```bash
make install
```

### 4. Configure environment variables

Copy `.env.example` to `.env` and adjust the values:

```env
APP_NAME="NP-backend"
ENVIRONMENT="dev"

DATABASE_URL="postgresql+asyncpg://postgres:password@localhost:5432/np_db"

SECRET_KEY="change-me-later"
ALGORITHM="HS256"
ACCESS_TOKEN_EXPIRE_MINUTES=30
REFRESH_TOKEN_EXPIRE_DAYS=7

MAIL_SERVER="smtp.gmail.com"
MAIL_PORT=587
MAIL_USERNAME="your-email@gmail.com"
MAIL_PASSWORD="your-app-specific-password"
MAIL_FROM="noreply@example.com"
MAIL_FROM_NAME="NP Backend"
MAIL_TLS=true
MAIL_SSL=false

LOG_LEVEL="INFO"
LOKI_URL=""
LOKI_USER=""
LOKI_PASSWORD=""
```

| Variable                      | Description                                                  |
|-------------------------------|--------------------------------------------------------------|
| `APP_NAME`                    | Application name                                             |
| `ENVIRONMENT`                 | Runtime environment (`dev` / `prod`)                         |
| `DATABASE_URL`                | PostgreSQL async connection string                           |
| `SECRET_KEY`                  | JWT signing secret                                           |
| `ALGORITHM`                   | JWT signing algorithm                                        |
| `ACCESS_TOKEN_EXPIRE_MINUTES` | Access token lifetime (minutes)                              |
| `REFRESH_TOKEN_EXPIRE_DAYS`   | Refresh token lifetime (days)                                |
| `MAIL_*`                      | SMTP server credentials for email sending                    |
| `LOG_LEVEL`                   | Logging level (`DEBUG`, `INFO`, `WARNING`, etc.)             |
| `LOKI_URL`                    | Grafana Loki endpoint (leave empty for console-only logging) |

### 5. Run database migrations

**Create a migration:**

```bash
alembic revision --autogenerate -m "description"
```

Or using Make:

```bash
make migrate msg="description"
```

**Apply migrations:**

```bash
alembic upgrade head
```

Or:

```bash
make upgrade
```

**Rollback last migration:**

```bash
make downgrade
```

### 6. Start the server

**Development (hot-reload):**

```bash
make dev
```

Or manually:

```bash
python -m uvicorn app.main:app --reload
```

**Production:**

```bash
make prod
```

**Docker (full stack with PostgreSQL, Loki, Grafana, Nginx):**

```bash
docker-compose up --build
```

### 7. Verify

- API: `http://localhost:8000/api/v1`
- Swagger docs: `http://localhost:8000/docs`
- Grafana: `http://localhost:3000`

### 8. Code quality & testing

```bash
make lint      # Ruff linter
make format    # Ruff formatter
make type      # Mypy type checking
make test      # Run pytest suite
make clean     # Remove __pycache__ and .pyc files
```

## Project Structure

```
backend/
├── .env.example              # Environment variable template
├── .github/workflows/        # CI/CD pipeline definitions
├── Dockerfile                # Production container image
├── docker-compose.yml        # Full stack orchestration (Postgres, Loki, Grafana, Nginx)
├── docker/                   # Docker config files (nginx, loki, grafana provisioning)
├── Makefile                  # Development task runner
├── pyproject.toml            # Project metadata, dependencies, tooling config
├── alembic.ini               # Alembic migration configuration
├── alembic/                  # Database migration scripts
│   └── versions/
├── app/                      # Application package
│   ├── main.py               # FastAPI app entry point + lifespan
│   ├── api.py                # Router aggregation
│   ├── core/                 # Cross-cutting concerns
│   │   ├── config.py         # Pydantic-settings configuration
│   │   ├── database.py       # DB session dependency
│   │   ├── logging_config.py # Structured JSON logging + Loki handler
│   │   ├── middleware.py     # HTTP request logging middleware
│   │   └── security.py       # Password hashing, JWT, validation
│   ├── db/                   # Database foundation
│   │   ├── base.py           # SQLAlchemy declarative base
│   │   ├── base_all.py       # Meta-import of all models
│   │   └── session.py        # Async engine and session factory
│   └── features/             # Feature modules (feature-based architecture)
│       ├── auth/             # Authentication & authorization
│       │   ├── router.py     # Register, login, refresh, password reset endpoints
│       │   ├── service.py    # Login, registration, token refresh, reset logic
│       │   ├── schemas.py    # Token, LoginRequest, RegisterRequest, etc.
│       │   ├── models.py     # PasswordReset ORM model
│       │   ├── dependencies.py # get_current_user, role guards
│       │   └── openapi.py    # OpenAPI extra schema definitions
│       ├── user/             # User account management
│       │   ├── router.py     # Profile CRUD, password change, GDPR export/delete
│       │   ├── service.py    # User CRUD, export, profile update logic
│       │   ├── schemas.py    # UserRead, UserCreate, ChangePasswordRequest, etc.
│       │   └── models.py     # User and UserRole ORM models
│       ├── court/            # Court and schedule management
│       │   ├── router.py     # Court CRUD, schedule, available slots endpoints
│       │   ├── service.py    # Court and schedule business logic
│       │   ├── schemas.py    # CourtRead, CourtSchedule, BookingSlot schemas
│       │   ├── models.py     # Court, CourtSchedule, BookingSlot ORM models
│       │   └── utils.py      # Slot range generation, overlap detection
│       ├── order/            # Order/booking management
│       │   ├── router.py     # Create order, list orders, get order detail
│       │   ├── service.py    # Order creation with validation, slot formatting
│       │   ├── schemas.py    # OrderCreate, OrderRead, OrderDetailResponse
│       │   └── models.py     # Order ORM model
│       ├── email/            # Email sending service
│       │   ├── service.py    # Send welcome, booking confirmation, reset emails
│       │   └── __init__.py   # EmailService singleton
│       ├── notifications/    # Booking reminders
│       │   ├── service.py    # send_booking_confirmation helper
│       │   └── scheduler.py  # APScheduler reminder scheduling + recovery
│       └── ping/             # Health-check endpoints
│           ├── router.py     # GET /status, GET /status/ping
│           └── schemas.py    # StatusResponse model
├── tests/                    # Test suite
│   ├── conftest.py           # Pytest fixtures
│   ├── test_auth_email.py
│   ├── test_available_courts.py
│   ├── test_court.py
│   └── test_order.py
├── uml/                      # Architecture diagrams
└── build/                    # Build artifacts
```

## Tech Stack

| Layer              | Technology                                                                               |
|--------------------|------------------------------------------------------------------------------------------|
| Framework          | [FastAPI](https://fastapi.tiangolo.com/) >= 0.110                                        |
| ASGI Server        | [uvicorn](https://www.uvicorn.org/) >= 0.27                                              |
| ORM                | [SQLAlchemy](https://www.sqlalchemy.org/) 2.0 (async)                                    |
| Database           | PostgreSQL 15+ via [asyncpg](https://github.com/MagicStack/asyncpg)                      |
| Migrations         | [Alembic](https://alembic.sqlalchemy.org/) >= 1.13                                       |
| Validation         | [Pydantic](https://docs.pydantic.dev/) >= 2.6 + [pydantic-settings](https://docs.pydantic.dev/latest/concepts/pydantic_settings/) |
| Auth               | [PyJWT](https://github.com/jpadilla/pyjwt) >= 2.8 + [passlib](https://passlib.readthedocs.io/) [bcrypt] |
| Email              | [fastapi-mail](https://github.com/sabuhish/fastapi-mail) >= 1.4                          |
| Scheduling         | [APScheduler](https://apscheduler.readthedocs.io/) >= 3.10                               |
| Logging            | Python `logging` + structured JSON + [Grafana Loki](https://grafana.com/oss/loki/)        |
| Linting            | [Ruff](https://docs.astral.sh/ruff/) >= 0.4                                              |
| Type Checking      | [mypy](https://mypy-lang.org/) >= 1.8                                                    |
| Testing            | [pytest](https://docs.pytest.org/) >= 8.0, pytest-asyncio, [httpx](https://www.python-httpx.org/) |
| CI                 | GitHub Actions                                                                           |
| Containerization   | Docker, docker-compose (Postgres + Loki + Grafana + Nginx)                               |

## License

[MIT](LICENSE)
