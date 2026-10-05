@echo off
setlocal EnableExtensions EnableDelayedExpansion
rem ============================================================
rem  Build one Python file or a comma-separated list of Python files.
rem
rem  Interactive:
rem    BUILD_bat\_build.bat
rem  Command line:
rem    BUILD_bat\_build.bat src\tool.py
rem    BUILD_bat\_build.bat "src\tool_one.py, src\tool_two.py"
rem ============================================================
chcp 65001 >nul
cd /d "%~dp0.."

rem Activate the project virtual environment.
set "VENV_ACTIVATE=%CD%\.venv\Scripts\activate.bat"
if not exist "%VENV_ACTIVATE%" set "VENV_ACTIVATE=%CD%\venv\Scripts\activate.bat"
if not exist "%VENV_ACTIVATE%" (
    echo [ERROR] Virtual environment not found in .venv or venv.
    goto :err
)
call "%VENV_ACTIVATE%"
if errorlevel 1 (
    echo [ERROR] Failed to activate the virtual environment.
    goto :err
)

call "%~dp0..\bat\_common_build.bat"
if errorlevel 1 goto :err

set "INPUT=%~1"
if not defined INPUT set /p "INPUT=Enter Python file(s), separated by commas: "
if not defined INPUT (
    echo [ERROR] No source files entered.
    goto :err
)

set "REMAINING=!INPUT!"
set /a REQUESTED=0
set /a FAILED=0

:next_file
if not defined REMAINING goto :files_done
for /f "tokens=1,* delims=," %%A in ("!REMAINING!") do (
    set "ITEM=%%A"
    set "REMAINING=%%B"
)
call :trim_item
if not defined ITEM goto :next_file
set /a REQUESTED+=1
call :build_requested "!ITEM!"
if errorlevel 1 set /a FAILED+=1
goto :next_file

:files_done
if !REQUESTED! EQU 0 goto :err
if !FAILED! GTR 0 (
    echo [ERROR] !FAILED! of !REQUESTED! builds failed.
    goto :err
)
echo.
echo Built !REQUESTED! file^(s^) successfully.
goto :success

:trim_item
set "ITEM=!ITEM:"=!"
for /f "tokens=* delims= " %%F in ("!ITEM!") do set "ITEM=%%F"
:trim_item_tail
if defined ITEM if "!ITEM:~-1!"==" " (
    set "ITEM=!ITEM:~0,-1!"
    goto :trim_item_tail
)
exit /b 0

:build_requested
set "SOURCE=%~1"
rem A bare file name resolves to src\NAME.py.
if not exist "!SOURCE!" if exist "src\!SOURCE!" set "SOURCE=src\!SOURCE!"
if not exist "!SOURCE!" (
    echo [ERROR] File not found: !SOURCE!
    exit /b 1
)
if exist "!SOURCE!\" (
    echo [ERROR] Expected a .py file, got a directory: !SOURCE!
    exit /b 1
)
for %%F in ("!SOURCE!") do if /I not "%%~xF"==".py" (
    echo [ERROR] Source file must have the .py extension: %%~fF
    exit /b 1
)
call :build_one "!SOURCE!"
exit /b !errorlevel!

:build_one
set "SOURCE=%~1"
set "NAME=%~n1"

echo.
echo === Building !NAME! ^(source: !SOURCE!^) ===
"%PYTHON%" -m PyInstaller --noconfirm --clean --onefile --name "!NAME!" --paths src --hidden-import functions "!SOURCE!"
if errorlevel 1 (
    echo [ERROR] Build failed: !SOURCE!
    exit /b 1
)

if exist "build\!NAME!" rmdir /s /q "build\!NAME!"
if exist "build" rmdir "build" 2>nul
if exist "!NAME!.spec" del /q "!NAME!.spec"

set "RUNBAT=bat\RUN_!NAME!.bat"
if not exist "!RUNBAT!" goto :write_launcher
set "OVERWRITE="
set /p "OVERWRITE=Launcher exists: !RUNBAT!. Overwrite? (y/N): "
if /I not "!OVERWRITE!"=="y" goto :launcher_done

:write_launcher
>  "!RUNBAT!" echo chcp 65001 ^>nul
>> "!RUNBAT!" echo @echo off
>> "!RUNBAT!" echo cd /d "%%~dp0..\exe"
>> "!RUNBAT!" echo "!NAME!.exe"
echo Generated launcher: !RUNBAT!

:launcher_done
echo Build OK: dist\!NAME!.exe
exit /b 0

:success
echo.
pause
exit /b 0

:err
echo [ERROR] Build failed. See output above.
pause
exit /b 1
