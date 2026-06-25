@echo off
:: ─────────────────────────────────────────────────────────────
:: start_agent.bat — Start the CROO Agent Worker
:: Run from the hackerthon\ root directory.
:: ─────────────────────────────────────────────────────────────
echo.
echo [LedgerOps] Starting CROO Agent Worker...
echo    Listening for ORDER_PAID, NEGOTIATION_CREATED, etc.
echo    Press Ctrl+C to stop.
echo.

cd /d "%~dp0croo_backend"
call venv\Scripts\activate.bat
python manage.py run_agent
