@echo off
REM cross_calls.bat — Windows launcher for run_cross_calls.py
REM Ensures UTF-8 output and activates the venv automatically.
REM Usage:  cross_calls.bat [--round A|B|C|all] [--delay N] [--dry-run] [--summary]
REM Example: cross_calls.bat --round A --delay 60

setlocal
set PYTHONIOENCODING=utf-8

REM Activate the virtual environment
call "%~dp0venv\Scripts\activate.bat"

REM Forward all CLI arguments to the orchestrator script
python "%~dp0run_cross_calls.py" %*

endlocal
