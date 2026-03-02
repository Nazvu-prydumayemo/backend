
# FastAPI Backend

Feature-based backend built with FastAPI, SQLAlchemy 2.0 and PostgreSQL (async).

---

## 1. Create virtual environment

```bash
python -m venv .venv
```

## 2. Activate it

**Windows (PowerShell):**

```powershell
.venv\Scripts\Activate.ps1
```

**Windows (cmd):**

```cmd
.venv\Scripts\activate
```

**Linux / macOS:**

```bash
source .venv/bin/activate
```

---

## 3. Install dependencies

```bash
pip install -e ".[dev]"
```

Or using Make:

```bash
make install
```

---

## 4. Setup environment variables

Create a `.env` file:



---

## 5. Run database migrations

```bash
alembic upgrade head
```

Or:

```bash
make upgrade
```

Create a new migration:

```bash
make migrate
```

---

## 6. Start the server

Development:

```bash
make dev
```

Or manually:

```bash
python -m uvicorn app.main:app --reload
```

Production:

```bash
make prod
```

---

API will be available at:

```
http://localhost:8000/api/v1
```

Docs:

```
http://localhost:8000/docs
```

---

## 7. Code Quality

Lint:

```bash
make lint
```

Format:

```bash
make format
```

Type checking:

```bash
make type
```

---

## 8. Run Tests

```bash
make test
```

---

## 9. Clean Cache Files

```bash
make clean
```

---

## Project Structure

```
backend/
│
├── pyproject.toml
├── .env.example
├── Makefile
│
├── app/
│   ├── main.py
│   ├── core/
│   ├── db/
│   ├── features/
│   └── api.py 
│
└── tests/
    ├── auth/
    └── users/
```

---

Backend communicates with the Textual TUI frontend via HTTP API.
