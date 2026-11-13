@echo off
chcp 65001 >nul 2>&1
cls

echo.
echo  ███████╗ █████╗ ██████╗  █████╗ ███████╗     █████╗  ██████╗ ███████╗███╗   ██╗████████╗
echo  ██╔════╝██╔══██╗██╔══██╗██╔══██╗╚══███╔╝    ██╔══██╗██╔════╝ ██╔════╝████╗  ██║╚══██╔══╝
echo  █████╗  ███████║██████╔╝███████║  ███╔╝     ███████║██║  ███╗█████╗  ██╔██╗ ██║   ██║   
echo  ██╔══╝  ██╔══██║██╔══██╗██╔══██║ ███╔╝      ██╔══██║██║   ██║██╔══╝  ██║╚██╗██║   ██║   
echo  ██║     ██║  ██║██║  ██║██║  ██║███████╗    ██║  ██║╚██████╔╝███████╗██║ ╚████║   ██║   
echo  ╚═╝     ╚═╝  ╚═╝╚═╝  ╚═╝╚═╝  ╚═╝╚══════╝    ╚═╝  ╚═╝ ╚═════╝ ╚══════╝╚═╝  ╚═══╝   ╚═╝   
echo.
echo  ══════════════════════════════════════════════════════════════════════════════════════════
echo                     Autonomous Terminal AI Agent  ^|  Installer V1.0.0
echo  ══════════════════════════════════════════════════════════════════════════════════════════
echo.

:: Find Python
set PYTHON_EXE=
for %%P in (
    "%LOCALAPPDATA%\Programs\Python\Python313\python.exe"
    "%LOCALAPPDATA%\Programs\Python\Python312\python.exe"
    "%LOCALAPPDATA%\Programs\Python\Python311\python.exe"
    "%LOCALAPPDATA%\Programs\Python\Python310\python.exe"
) do (
    if exist %%P (
        set PYTHON_EXE=%%P
        goto :found_python
    )
)

:: Fallback to PATH python
where python >nul 2>&1
if %errorlevel% == 0 (
    set PYTHON_EXE=python
    goto :found_python
)

echo  [ERROR] Python not found! Please install Python 3.10+ from https://python.org
echo.
pause
exit /b 1

:found_python
echo  [OK]  Python found: %PYTHON_EXE%
echo.

:: Install the package
echo  [>>] Installing Agent Faraz and all dependencies...
echo       This may take a minute on first run.
echo.

%PYTHON_EXE% -m pip install -e "%~dp0." --quiet --no-warn-script-location

if %errorlevel% neq 0 (
    echo.
    echo  [ERROR] Installation failed. Please check your internet connection.
    echo.
    pause
    exit /b 1
)

echo.
echo  [OK]  Installation complete!
echo.

:: Add Scripts to PATH for this session
for /f "delims=" %%i in ('%PYTHON_EXE% -c "import sys, os; print(os.path.join(os.path.dirname(sys.executable), 'Scripts'))"') do set SCRIPTS_DIR=%%i

:: Add to User PATH permanently
powershell -NoProfile -Command ^
    "$current = [Environment]::GetEnvironmentVariable('Path','User'); ^
     if ($current -notlike '*%SCRIPTS_DIR%*') { ^
         [Environment]::SetEnvironmentVariable('Path', $current + ';%SCRIPTS_DIR%', 'User'); ^
         Write-Host '  [OK]  PATH updated permanently.' ^
     } else { ^
         Write-Host '  [OK]  PATH already set.' ^
     }"

echo.
echo  ══════════════════════════════════════════════════════════════════════════════════════════
echo   Agent Faraz is ready! Launch it anytime by typing:
echo.
echo       faraz
echo.
echo   Or run a one-shot command:
echo.
echo       faraz "explain this codebase"
echo.
echo  ══════════════════════════════════════════════════════════════════════════════════════════
echo.
echo  Launching Agent Faraz now...
echo.
timeout /t 2 /nobreak >nul

set PATH=%SCRIPTS_DIR%;%PATH%
%SCRIPTS_DIR%\faraz.exe

pause
