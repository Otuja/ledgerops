@echo off
:: ─────────────────────────────────────────────────────────────
:: start_dashboard.bat — Start the React/Vite frontend
:: Run from the hackerthon\ root directory.
:: ─────────────────────────────────────────────────────────────
echo.
echo [LedgerOps] Starting React dashboard...
echo    Dashboard will open at: http://localhost:5173
echo    Press Ctrl+C to stop.
echo.

cd /d "%~dp0croo_dashboard"
npm run dev
