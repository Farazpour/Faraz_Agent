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
echo                       Agent Faraz  ^|  Complete Uninstaller
echo  ══════════════════════════════════════════════════════════════════════════════════════════
echo.

set /p CONFIRM="Are you sure you want to completely uninstall Agent Faraz from your system? (y/N): "
if /i not "%CONFIRM%"=="y" if /i not "%CONFIRM%"=="yes" (
    echo.
    echo Uninstallation cancelled.
    pause
    exit /b 0
)

echo.
echo [1/3] Uninstalling python package 'agent-faraz'...

:: Locate Python
set PYTHON_EXE=
for %%P in (
    "%LOCALAPPDATA%\Programs\Python\Python313\python.exe"
    "%LOCALAPPDATA%\Programs\Python\Python312\python.exe"
    "%LOCALAPPDATA%\Programs\Python\Python311\python.exe"
    "%LOCALAPPDATA%\Programs\Python\Python310\python.exe"
) do (
    if exist %%P (
        set PYTHON_EXE=%%P
        goto :found_py
    )
)

where python >nul 2>&1
if %errorlevel% == 0 (
    set PYTHON_EXE=python
    goto :found_py
)

:found_py
if defined PYTHON_EXE (
    %PYTHON_EXE% -m pip uninstall -y agent-faraz >nul 2>&1
    echo   [OK] Python package uninstalled.
) else (
    echo   [!] Python not detected. Skipping pip uninstall.
)

echo.
echo [2/3] Removing workspace configuration...
if exist "%~dp0.faraz.json" (
    del /f /q "%~dp0.faraz.json" >nul 2>&1
    echo   [OK] Workspace config removed.
)

echo.
echo [3/3] Removing global settings and chat history (~/.agent_faraz)...
set /p DEL_DATA="Do you want to delete all saved API keys, settings, and chat history? (y/N): "
if /i "%DEL_DATA%"=="y" (
    if exist "%USERPROFILE%\.agent_faraz" (
        rmdir /s /q "%USERPROFILE%\.agent_faraz" >nul 2>&1
        echo   [OK] Global configuration and chats removed.
    )
) else (
    echo   [--] Preserved ~/.agent_faraz for future use.
)

echo.
echo  ══════════════════════════════════════════════════════════════════════════════════════════
echo     Agent Faraz has been successfully uninstalled from your system!
echo  ══════════════════════════════════════════════════════════════════════════════════════════
echo.
pause
