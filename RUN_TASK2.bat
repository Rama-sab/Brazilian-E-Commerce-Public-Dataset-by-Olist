@echo off
setlocal
cd /d "%~dp0"

set "TASK2_PYTHON=%CD%\.venv\Scripts\python.exe"
if not exist "%TASK2_PYTHON%" set "TASK2_PYTHON=python"
set "PATH=%CD%\.venv\Scripts;%PATH%"

"%TASK2_PYTHON%" tools\execute_task2_notebooks.py %*
exit /b %ERRORLEVEL%
