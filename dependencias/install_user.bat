@echo off
:: install_user.bat — aciona o instalador Python unificado em modo --user
:: Uso: abra o Prompt de Comando na pasta do projeto e execute: install_user.bat

setlocal

echo Verificando Python...
python --version >nul 2>&1
if %ERRORLEVEL% NEQ 0 (
  echo Python nao encontrado. Instale Python 3.8+ e adicione 'python' ao PATH.
  pause
  exit /b 1
)

echo Instalando dependencias para o usuario atual...
python ..\tools\install.py --mode user %*
if %ERRORLEVEL% NEQ 0 (
  echo.
  echo A instalacao encontrou erros. Consulte os logs acima.
  pause
  exit /b 1
)

echo.
echo Instalacao concluida com sucesso (escopo --user)!
echo.
echo Agora execute a GUI com:
echo     python AutoMDF-Start.py
echo.
pause
