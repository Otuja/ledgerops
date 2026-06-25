@echo off
:: ─────────────────────────────────────────────────────────────
:: start_backend.bat — Start the Django API server
:: Run from the hackerthon\ root directory.
:: ─────────────────────────────────────────────────────────────
echo.
echo [LedgerOps] Starting Django backend...
echo.

cd /d "%~dp0croo_backend"

:: Activate the virtual environment
call venv\Scripts\activate.bat

:: Run pending migrations (safe to run on every start)
python manage.py migrate --run-syncdb

:: Start the dev server
python manage.py runserver 0.0.0.0:8000
