# Roll Call and Private Voting

A FastAPI web application for class attendance and private group voting. Professors can create classes, enroll students, take attendance, and schedule single-choice votes. Students can cast one private vote; professors see totals but never individual choices.

## Demo professor login

- Email: `professor@rollcall.local`
- Password: `Professor123!`

The account is created automatically when the application starts in development mode. It is disabled when `APP_ENV=production`.

## Run locally

Requirements: Python 3.11 or newer.

### Windows PowerShell

```powershell
py -3.11 -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -e .
python -m uvicorn app.main:app --reload
```

### macOS or Linux

```bash
python3.11 -m venv .venv
source .venv/bin/activate
python -m pip install -e .
python -m uvicorn app.main:app --reload
```

Open [http://127.0.0.1:8000](http://127.0.0.1:8000) and sign in with the professor credentials above. API documentation is available at [http://127.0.0.1:8000/docs](http://127.0.0.1:8000/docs).

The default configuration uses a local SQLite database named `attendance.db`.

## Run with Docker

```bash
docker compose up --build
```

Then open [http://127.0.0.1:8000](http://127.0.0.1:8000).

## Use the voting feature

1. Sign in as the demo professor.
2. Create a class from the left sidebar.
3. Create student accounts and add their email addresses to the class.
4. Open the class's **Voting** tab.
5. Enter the question, opening and closing times, and at least two options.
6. Students sign in and submit one private vote from their dashboard.

## Tests

After installing the development dependencies:

```bash
python -m pip install -e ".[dev]"
python -m pytest -q
```

## Production note

Set `APP_ENV=production` and provide strong, different values for `JWT_SECRET` and `CODE_SECRET`. The application refuses to start in production with the built-in development secrets, and the demo professor account is not created there.
