@echo off
setlocal
cd /d "%~dp0"
title Vitrine - Servidor

if not exist "venv\Scripts\python.exe" (
  echo [1/4] Criando ambiente virtual...
  py -3 -m venv venv
  if errorlevel 1 (
    echo.
    echo ERRO: Python 3 nao foi encontrado.
    echo Instale Python 3.12 ou superior e marque "Add Python to PATH".
    pause
    exit /b 1
  )
)

echo [2/4] Configurando ambiente...
if not exist ".env" (
  copy /Y ".env.example" ".env" >nul
)

venv\Scripts\python.exe -c "from pathlib import Path; import secrets; p=Path('.env'); s=p.read_text(encoding='utf-8'); s=s.replace('SECRET_KEY=', 'SECRET_KEY='+secrets.token_urlsafe(50), 1); p.write_text(s, encoding='utf-8') if 'SECRET_KEY=' in s and 'SECRET_KEY=django-' not in s and 'SECRET_KEY=' in s else None"

echo [3/4] Instalando/verificando dependencias...
venv\Scripts\python.exe -m pip install -r requirements.txt
if errorlevel 1 (
  echo.
  echo ERRO ao instalar dependencias.
  pause
  exit /b 1
)

echo [4/4] Preparando banco de dados e arquivos...
venv\Scripts\python.exe manage.py migrate --noinput
if errorlevel 1 (
  echo.
  echo ERRO nas migracoes do banco.
  pause
  exit /b 1
)
venv\Scripts\python.exe manage.py collectstatic --noinput >nul


echo [5/5] Iniciando a loja...
start "" http://127.0.0.1:8000/
venv\Scripts\python.exe manage.py runserver 127.0.0.1:8000

endlocal
