@echo off
title Urban Data Explorer

set "PROJECT_DIR=%~dp0"
set "FRONTEND_DIR=%PROJECT_DIR%frontend"
set "BACKEND_DIR=%PROJECT_DIR%frontend\api"

echo === Urban Data Explorer ===

if not exist "%BACKEND_DIR%\main.py" (
    echo Erreur : main.py introuvable dans %BACKEND_DIR%
    pause
    exit /b
)

if not exist "%FRONTEND_DIR%\index.html" (
    echo Erreur : index.html introuvable dans %FRONTEND_DIR%
    pause
    exit /b
)

cd /d "%BACKEND_DIR%"

if not exist ".venv" (
    echo Creation environnement virtuel backend...
    py -m venv .venv
)

call ".venv\Scripts\activate.bat"

if exist requirements.txt (
    echo Installation requirements.txt...
    pip install -r requirements.txt
) else (
    echo Installation dependances FastAPI minimales...
    pip install fastapi uvicorn pymongo python-dotenv
)

if not exist ".env" (
    (
        echo MONGODB_URI=REMPLACE_PAR_TON_URI_MONGODB_ATLAS
        echo MONGODB_DB=urban_explorer
        echo MONGODB_COLLECTION=scores
    ) > .env

    echo.
    echo Fichier .env cree ici :
    echo %BACKEND_DIR%\.env
    echo.
    echo Remplace MONGODB_URI puis relance mongo.bat.
    pause
    exit /b
)

start "Urban API FastAPI" cmd /k "cd /d ""%BACKEND_DIR%"" && call "".venv\Scripts\activate.bat"" && py -m uvicorn main:app --reload --host 127.0.0.1 --port 8000"

start "Urban Frontend" cmd /k "cd /d ""%FRONTEND_DIR%"" && echo Frontend servi depuis: ""%FRONTEND_DIR%"" && py -m http.server 5500 --bind 127.0.0.1"

echo.
echo API      : http://localhost:8000/health
echo Frontend : http://localhost:5500/index.html
echo.

timeout /t 3 >nul
start http://localhost:5500

pause