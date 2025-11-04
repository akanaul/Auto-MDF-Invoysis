@echo off
:: install.bat — cria um virtualenv e instala dependências (Windows CMD)
:: Uso: abra o Prompt de Comando na pasta do projeto e execute: install.bat

echo Verificando Python...
python --version >nul 2>&1
if %ERRORLEVEL% NEQ 0 (
  echo Python nao encontrado. Instale Python 3.8+ e adicione 'python' ao PATH.
  pause
  exit /b 1
)

echo Criando virtual environment...
if not exist venv (
  python -m venv venv
  echo Virtual environment criado em .\venv
) else (
  echo Virtual environment ja existe em .\venv - pulando criacao
)

echo Atualizando pip e instalando requisitos...
call .\venv\Scripts\python.exe -m pip install --upgrade pip --quiet
call .\venv\Scripts\python.exe -m pip install -r requirements.txt --quiet

echo.
echo Instalacao concluida com sucesso!
echo.
echo Para usar, ative o venv com:
echo     .\venv\Scripts\activate.bat
echo.
echo Entao execute a GUI com:
echo     python AutoMDF-Start.py
echo.
pause
