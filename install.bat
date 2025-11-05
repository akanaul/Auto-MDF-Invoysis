@echo off
:: install.bat — aciona o instalador Python unificado (Windows CMD)
:: Uso: abra o Prompt de Comando na pasta do projeto e execute: install.bat

setlocal

echo Verificando Python...
python --version >nul 2>&1
if %ERRORLEVEL% NEQ 0 (
  echo Python nao encontrado. Instale Python 3.8+ e adicione 'python' ao PATH.
  pause
  exit /b 1
)

echo Iniciando instalacao de dependencias...
python tools\install.py --mode venv --venv-path .venv %*
if %ERRORLEVEL% NEQ 0 (
  echo.
  echo A instalacao encontrou erros. Consulte os logs acima.
  pause
  exit /b 1
)

echo.
echo Instalacao concluida com sucesso!
echo.
echo Para usar, ative o ambiente com:
echo     .\.venv\Scripts\activate.bat
echo.
echo Em seguida execute a GUI com:
echo     python AutoMDF-Start.py
echo.
pause
