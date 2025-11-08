@echo off
REM Start SLD Design Electrical Automation System

echo ============================================
echo  SLD Design - Electrical Automation System
echo ============================================
echo.
echo Starting Streamlit application...
echo.
echo The application will open in your default web browser.
echo If it doesn't open automatically, navigate to:
echo    http://localhost:8501
echo.
echo Press Ctrl+C to stop the application.
echo ============================================
echo.

streamlit run src\app.py

pause
