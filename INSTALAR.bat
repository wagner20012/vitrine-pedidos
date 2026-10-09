@echo off
setlocal
cd /d "%~dp0"
if not exist "venv\Scripts\python.exe" (
  py -3 -m venv venv
  if errorlevel 1 (
    echo Python 3.12+ nao encontrado.
    pause
    exit /b 1
  )
)
venv\Scripts\python.exe -m pip install -r requirements.txt
venv\Scripts\python.exe manage.py migrate --noinput
venv\Scripts\python.exe manage.py collectstatic --noinput
if not exist ".env" copy /Y ".env.example" ".env" >nul
echo Instalacao concluida.
pause
endlocal
