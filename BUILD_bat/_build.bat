@echo off
rem ============================================================
rem  Universal build: compiles a .py tool into dist\<name>.exe.
rem  You enter the .py file (a bare name resolves to src\NAME.py);
rem  imports are resolved from src\ (functions etc.).
rem  After a successful build:
rem    - cleans PyInstaller residuals (build\<name>, generated .spec, empty build\)
rem    - generates bat\RUN_<name>.bat launcher (analogy: RUN_run_pipeline_with_config).
rem  BUILD\ moved to repo root; cd / run root handled here.
rem  NOTE: ASCII-only to avoid codepage/UTF-8 issues in cmd.
rem ============================================================
chcp 65001 >nul
call "%~dp0..\bat\_common_build.bat"
if errorlevel 1 goto :err
cd /d "%~dp0.."

set /p INPUT="Enter source file (.py): "
if not defined INPUT goto :err

rem Extract the tool name from the entered filename.
for %%F in ("%INPUT%") do set "NAME=%%~nF"

rem Sources live in src\; a bare filename maps to src\NAME.py.
if not exist "%INPUT%" (
    if exist "src\%INPUT%" set "INPUT=src\%INPUT%"
)
if not exist "%INPUT%" (
    echo [ERROR] File not found: %INPUT%
    goto :err
)

echo === Building %NAME% (source: %INPUT%) ===
"%PYTHON%" -m PyInstaller --noconfirm --clean --onefile --name "%NAME%" --paths src --hidden-import functions "%INPUT%"
if errorlevel 1 goto :err

echo.
echo Build OK: dist\%NAME%.exe

rem ============================================================
rem  Post-build: clean PyInstaller residuals and make a launcher.
rem ============================================================

rem --- 1. Clean residual files (build\<NAME>, generated .spec, empty build\) ---
if exist "build\%NAME%" (
    echo Cleaning build\%NAME% ...
    rmdir /s /q "build\%NAME%"
)
if exist "build" rmdir "build" 2>nul
rem PyInstaller writes a NAME.spec at repo root - it's a build residual, remove it.
if exist "%NAME%.spec" (
    echo Cleaning %NAME%.spec ...
    del /q "%NAME%.spec"
)

rem --- 2. Generate RUN_<NAME>.bat launcher (analogy: bat\RUN_run_pipeline_with_config.bat) ---
set "RUNBAT=bat\RUN_%NAME%.bat"
if not exist "%RUNBAT%" goto :gen_launcher
set /p OVERW="Launcher already exists: %RUNBAT%. Overwrite? (y/N): "
if /I not "%OVERW%"=="y" goto :after_launcher
:gen_launcher
>  "%RUNBAT%" echo chcp 65001
>> "%RUNBAT%" echo @echo off
>> "%RUNBAT%" echo cd %%~dp0..\exe
>> "%RUNBAT%" echo "%NAME%.exe"
echo Generated launcher: %RUNBAT%
:after_launcher

pause
exit /b 0

:err
echo [ERROR] Build failed. See output above.
pause
exit /b 1
