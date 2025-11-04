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

set VENV_DIR=.venv

echo Criando ambiente virtual...
if not exist %VENV_DIR% (
  python -m venv %VENV_DIR%
  echo Ambiente virtual criado em .\%VENV_DIR%
) else (
  echo Ambiente virtual ja existe em .\%VENV_DIR% - pulando criacao
)

echo Atualizando ferramentas basicas do pip...
call .\%VENV_DIR%\Scripts\python.exe -m pip install --upgrade pip setuptools wheel

echo Instalando dependencias do projeto (obrigatorias e recomendadas)...
call .\%VENV_DIR%\Scripts\python.exe -m pip install --upgrade -r requirements.txt

echo.
echo Instalacao concluida com sucesso!
echo.
echo Para usar, ative o ambiente com:
echo     .\%VENV_DIR%\Scripts\activate.bat
echo.
echo Entao execute a GUI com:
echo     python AutoMDF-Start.py
echo.
pause
