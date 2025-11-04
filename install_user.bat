@echo off
:: install_user.bat — instala dependências usando a opcao --user do pip (Windows CMD)
:: Uso: abra o Prompt de Comando na pasta do projeto e execute: install_user.bat

echo Verificando Python...
python --version >nul 2>&1
if %ERRORLEVEL% NEQ 0 (
  echo Python nao encontrado. Instale Python 3.8+ e adicione 'python' ao PATH.
  pause
  exit /b 1
)

echo Atualizando pip...
python -m pip install --upgrade pip --quiet

echo Instalando requisitos (escopo --user)...
python -m pip install --user -r requirements.txt --quiet

echo.
echo Instalacao concluida com sucesso (escopo --user)!
echo.
echo Agora execute a GUI com:
echo     python AutoMDF-Start.py
echo.
pause
