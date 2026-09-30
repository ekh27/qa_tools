@echo off
rem ============================================================
rem  Shared helper for RUN_BUILD_*.bat
rem  Resolves Python/PyInstaller and the VATests repo path.
rem  Sets for the caller:
rem    PYTHON  - python.exe to use (with PyInstaller available)
rem    VATEST  - deploy path (where exe get deployed); read from DEPLOY_DIR
rem              in the repo-root settings.env, default .\
rem  Override before calling:
rem    set PY=C:\path\to\python.exe
rem  NOTE: ASCII-only messages to avoid codepage issues in cmd.
rem ============================================================

rem --- Deploy dir: DEPLOY_DIR from repo-root settings.env > default .\ ---
set "VATEST="
if exist "%~dp0..\settings.env" for /f "usebackq tokens=1,* delims==" %%A in ("%~dp0..\settings.env") do (
    if /I "%%A"=="DEPLOY_DIR" set "VATEST=%%B"
)
if not defined VATEST set "VATEST=.\"

rem --- Python auto-detection: env PY > PATH (python/py) > well-known paths ---
set "PYTHON="
if defined PY set "PYTHON=%PY%"
if not defined PYTHON (
    for %%i in (python.exe py.exe) do (
        where %%i >nul 2>nul
        if not errorlevel 1 if not defined PYTHON set "PYTHON=%%i"
    )
)
if not defined PYTHON (
    if exist "%LocalAppData%\Programs\Python\Python312\python.exe" set "PYTHON=%LocalAppData%\Programs\Python\Python312\python.exe"
    if not defined PYTHON if exist "C:\Python312\python.exe" set "PYTHON=C:\Python312\python.exe"
    if not defined PYTHON if exist "C:\Python311\python.exe" set "PYTHON=C:\Python311\python.exe"
)
if not defined PYTHON (
    echo [ERROR] Python not found. Set PY=^<full path to python.exe^> and rerun.
    exit /b 1
)

rem --- PyInstaller must be installed for that Python ---
"%PYTHON%" -m PyInstaller --version >nul 2>&1
if errorlevel 1 (
    echo [ERROR] PyInstaller missing for %PYTHON%.
    echo         Install it with: "%PYTHON%" -m pip install pyinstaller
    exit /b 1
)

echo Python : %PYTHON%
echo VATest : %VATEST%
exit /b 0
