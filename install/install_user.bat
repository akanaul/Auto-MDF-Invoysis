@echo off
:: install\install_user.bat — instalacao das dependencias em modo --user
:: Uso: execute este arquivo a partir da pasta install ou via Explorer.

setlocal

set "INSTALL_DIR=%~dp0"
for %%I in ("%INSTALL_DIR%..") do set "PROJECT_ROOT=%%~fI"

pushd "%PROJECT_ROOT%" >nul 2>&1

for /f "delims=" %%I in ('powershell -NoProfile -ExecutionPolicy Bypass -File "%INSTALL_DIR%find_python.ps1"') do set "PYTHON_PATH=%%I"

if not defined PYTHON_PATH (
  echo Nao foi possivel localizar Python 3.10 ou superior automaticamente.
  echo Verifique a instalacao do Python ou ajuste o caminho manualmente.
  popd >nul 2>&1
  pause
  exit /b 1
)

echo Encontrado Python em: %PYTHON_PATH%
echo Instalando dependencias no escopo do usuario atual...

"%PYTHON_PATH%" "%INSTALL_DIR%install.py" --mode user %*
set "EXIT_CODE=%ERRORLEVEL%"

if not "%EXIT_CODE%"=="0" (
  echo.
  echo A instalacao encontrou erros. Consulte os logs exibidos acima.
  popd >nul 2>&1
  pause
  exit /b %EXIT_CODE%
)

echo.
echo Instalacao concluida com sucesso para o usuario atual!
echo.
echo Agora execute a GUI com:
echo     python AutoMDF-Start.py
echo.

popd >nul 2>&1
pause
exit /b 0
