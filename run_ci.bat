@echo off
echo 🚀 Starting CI/CD Pipeline Simulation...
echo ----------------------------------------

:: 1. รัน Code Quality Check (flake8)
echo 1. Running Code Quality Check (flake8)...
flake8 . --exclude venv,recipes.db
if errorlevel 1 (
    echo ❌ Code Quality Failed! Fix PEP 8 issues.
    exit /b 1
)
echo ✅ Code Quality Passed.

:: 2. รัน Unit Tests (pytest)
echo 2. Running Unit Tests (pytest)...
pytest test_project.py
if errorlevel 1 (
    echo ❌ Unit Tests Failed! Fix the core logic.
    exit /b 1
)
echo ✅ Unit Tests Passed.

echo ----------------------------------------
echo ✅ CI/CD Pipeline Finished Successfully.
echo    Project is ready for submission.