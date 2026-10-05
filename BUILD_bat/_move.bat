@echo off
rem ============================================================
rem  move: deploy a built exe to PROD.
rem
rem  Target base dir (DEPLOY_DIR) is read from <repo>\src\settings.env
rem  (key DEPLOY_DIR). If it is missing/empty - asked interactively.
rem  Before the move the script prints FROM/TO and asks confirmation.
rem
rem  Python/PyInstaller are NOT required for moving binaries, so the
rem  shared _common_build.bat is not used here.
rem  NOTE: ASCII-only to avoid codepage issues in cmd.
rem ============================================================
chcp 65001 >nul
cd /d "%~dp0.."

rem --- Deploy dir: DEPLOY_DIR from src\settings.env > fallback: ask ---
set "VATEST="
set "SETTINGS_FILE=%~dp0..\src\settings.env"
if exist "%SETTINGS_FILE%" (
    rem ASCII/UTF-8: settings.env is KEY=VALUE; take the FIRST line with key DEPLOY_DIR.
    for /f "usebackq tokens=1,* delims==" %%A in ("%SETTINGS_FILE%") do (
        if /I "%%A"=="DEPLOY_DIR" set "VATEST=%%B"
    )
    if not defined VATEST (
        echo [WARN] Key DEPLOY_DIR not found in %SETTINGS_FILE%
    )
) else (
    echo [WARN] %SETTINGS_FILE% not found
)

if not defined VATEST (
    set /p "VATEST=Enter deploy base dir (full path, e.g. C:\VanessaTests\VAtest): "
)
if not defined VATEST (
    echo [ERROR] Deploy dir not set.
    goto :err
)
echo Deploy base dir: %VATEST%

set /p "FILE=Enter full path to the file to deploy: "
if not defined FILE goto :err
if not exist "%FILE%" (
    echo [ERROR] File not found: %FILE%
    goto :err
)

for %%F in ("%FILE%") do set "FILENAME=%%~nxF"

rem --- Confirmation: show FROM/TO before deploying ---
echo.
echo Will deploy:
echo   FROM: %FILE%
echo   TO  : %VATEST%%FILENAME%
echo.
set /p "CONFIRM=Proceed? (y/n): "
if /I not "%CONFIRM%"=="y" (
    echo Deploy cancelled.
    goto :err
)

echo === moving %FILE% to %VATEST% ===
move /Y "%FILE%" "%VATEST%" >nul
if errorlevel 1 goto :err

rem ============================================================
rem  The exe reads settings from its OWN directory at runtime, so
rem  deploy carries runtime files (settings.env, default pipeline
rem  variables) alongside the moved exe. Single source of truth in
rem  the repo: src\settings.env (live config; repo keeps only the
rem  settings.env.example template). A settings.env next to the
rem  source file being deployed takes precedence.
rem ============================================================

rem --- settings.env ---
rem settings.env.example is ONLY a template - never used as a source for deploy.
set "SRC_SETTINGS=src\settings.env"
if exist "%~dp1settings.env" set "SRC_SETTINGS=%~dp1settings.env"

if exist "%SRC_SETTINGS%" (
    copy /Y "%SRC_SETTINGS%" "%VATEST%settings.env" >nul
    if errorlevel 1 goto :err
    echo settings.env OK: %VATEST%settings.env  ^(from %SRC_SETTINGS%^)
) else (
    echo [ERROR] settings.env not found (src\settings.env); deploy aborted so PROD is not left without config.
    goto :err
)

rem --- run_pipeline_default_variables.json (expected next to the exe) ---
set "SRC_VARS=src\run_pipeline_default_variables.json"
if exist "%~dp1run_pipeline_default_variables.json" set "SRC_VARS=%~dp1run_pipeline_default_variables.json"

if exist "%SRC_VARS%" (
    copy /Y "%SRC_VARS%" "%VATEST%run_pipeline_default_variables.json" >nul
    if errorlevel 1 goto :err
    echo run_pipeline_default_variables.json OK  ^(from %SRC_VARS%^)
)

echo.
echo move OK: %VATEST%%FILENAME%
pause
exit /b 0

:err
echo [ERROR] move failed. See output above.
pause
exit /b 1
