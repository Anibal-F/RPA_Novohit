@echo off
chcp 65001 >nul
title RPA Novohit - Verificacion Pre-Ejecucion
cd /d "%~dp0"

echo ==========================================
echo    VERIFICACION PRE-EJECUCION
echo ==========================================
echo.

set "TODO_OK=1"

REM 1. Verificar Python
echo [*] Verificando Python...
python --version >nul 2>&1
if errorlevel 1 (
    echo [X] Python NO encontrado
    set "TODO_OK=0"
) else (
    for /f "tokens=2" %%a in ('python --version 2^>^&1') do echo [OK] Python %%a
)

REM 2. Verificar dependencias
echo [*] Verificando dependencias...
python -c "import playwright" >nul 2>&1
if errorlevel 1 (
    echo [X] Playwright NO instalado
    set "TODO_OK=0"
) else (
    echo [OK] Playwright instalado
)

python -c "import pandas" >nul 2>&1
if errorlevel 1 (
    echo [X] Pandas NO instalado
    set "TODO_OK=0"
) else (
    echo [OK] Pandas instalado
)

REM 3. Verificar carpetas
echo [*] Verificando carpetas...
if not exist "data\input" (
    echo [X] Carpeta data\input NO existe
    set "TODO_OK=0"
) else (
    echo [OK] Carpeta data\input existe
)

if not exist "data\output" (
    echo [X] Carpeta data\output NO existe
    set "TODO_OK=0"
) else (
    echo [OK] Carpeta data\output existe
)

REM 4. Verificar permisos
echo [*] Verificando permisos...
echo test > "data\output\test_write.txt" 2>nul
if exist "data\output\test_write.txt" (
    del "data\output\test_write.txt"
    echo [OK] Permisos de escritura OK
) else (
    echo [X] Sin permisos de escritura en data\output
    set "TODO_OK=0"
)

REM 5. Verificar archivo Excel
echo [*] Verificando archivos Excel en data\input\...
set "EXCEL_COUNT=0"
for %%f in ("data\input\*.xlsx") do set /a EXCEL_COUNT+=1

if %EXCEL_COUNT% == 0 (
    echo [!] No se encontraron archivos .xlsx en data\input\
) else (
    echo [OK] Encontrados %EXCEL_COUNT% archivo(s) .xlsx
)

REM 6. Verificar Chrome
echo [*] Verificando Google Chrome...
where chrome >nul 2>&1
if errorlevel 1 (
    echo [!] Chrome no esta en el PATH (El RPA usa su propio navegador)
) else (
    echo [OK] Chrome encontrado
)

echo.
echo ==========================================
if %TODO_OK% == 1 (
    echo    [OK] TODO CORRECTO - Listo para ejecutar
    echo ==========================================
    echo.
    echo Puede ejecutar el RPA con:
    echo    Ejecutar_GUI.bat
) else (
    echo    [X] HAY PROBLEMAS - Revise los errores arriba
    echo ==========================================
    echo.
    echo Ejecute INSTALADOR_COMPLETO.bat para corregir
)
echo.
pause
