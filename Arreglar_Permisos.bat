@echo off
chcp 65001 >nul
title RPA Novohit - Arreglar Permisos
cd /d "%~dp0"

echo ==========================================
echo    ARREGLANDO PERMISOS
echo ==========================================
echo.

echo [*] Creando carpetas necesarias...

REM Crear carpetas con permisos abiertos
if not exist "data" mkdir "data"
if not exist "data\input" mkdir "data\input"
if not exist "data\output" mkdir "data\output"
if not exist "data\debug" mkdir "data\debug"

echo [*] Aplicando permisos...

REM Dar permisos completos al usuario actual
icacls "data" /grant "%username%":F /T >nul 2>&1
icacls "data\input" /grant "%username%":F /T >nul 2>&1
icacls "data\output" /grant "%username%":F /T >nul 2>&1
icacls "data\debug" /grant "%username%":F /T >nul 2>&1

echo [*] Verificando...

REM Verificar que se pueden escribir archivos
echo test > "data\output\test.txt" 2>nul
if exist "data\output\test.txt" (
    del "data\output\test.txt"
    echo [OK] Permisos corregidos exitosamente!
) else (
    echo [X] No se pudieron corregir los permisos
    echo.
    echo [i] SOLUCION ALTERNATIVA:
    echo    1. Corte la carpeta RPA_Novohit
    echo    2. Peguela en C:\ (directamente en el disco)
    echo    3. Ejecute desde: C:\RPA_Novohit\
    echo.
    pause
    exit /b 1
)

echo.
echo ==========================================
echo    [OK] PERMISOS ARREGLADOS
echo ==========================================
echo.
pause
