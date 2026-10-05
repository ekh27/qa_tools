chcp 65001 >nul
@echo off
cd /d "%~dp0..\exe"
"get_diff_mr.exe"
