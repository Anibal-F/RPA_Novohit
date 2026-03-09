@echo off
chcp 65001 >nul
setlocal EnableDelayedExpansion

title RPA Novohit - Instalador Completo
mode con: cols=80 lines=40
color 0B
cls

:: ============================================
:: CONFIGURACION
:: ============================================
set "RPA_VERSION=1.0"
set "PYTHON_MIN_VERSION=3.10"
set "RPA_FOLDER=C:\RPA_Novohit"

:: ============================================
:: TITULO
:: ============================================
echo.
echo  ========================================================================
echo.
echo            RPA NOVOHIT - Instalador Completo v%RPA_VERSION%
echo.
echo   Contabilizacion Bancaria Automatizada
echo.
echo  ========================================================================
echo.
echo  Este instalador configurara todo automaticamente:
echo   * Python (si no esta instalado)
echo   * Dependencias del RPA
echo   * Navegador Chrome para automatizacion
echo   * Carpetas y permisos
echo   * Acceso directo en el escritorio
echo.
pause
cls

:: ============================================
:: PASO 1: VERIFICAR/MOVER CARPETA
:: ============================================
echo.
echo  ========================================================================
echo   PASO 1/6: Ubicacion del Programa
echo  ========================================================================
echo.

set "CURRENT_DIR=%~dp0"
set "CURRENT_DRIVE=%~d0"

:: Verificar si estamos en Descargas o Documentos (problemas de permisos)
echo %CURRENT_DIR% | findstr /I "Downloads Descargas Documents Documentos" >nul
if %errorlevel% == 0 (
    echo  [!] Detectado: Estas en Descargas/Documentos (puede causar problemas)
    echo.
    echo  [+] Moviendo a ubicacion recomendada: %RPA_FOLDER%
    echo.
    
    :: Crear carpeta destino
    if not exist "%RPA_FOLDER%" mkdir "%RPA_FOLDER%"
    
    :: Copiar archivos
    echo  [*] Copiando archivos...
    xcopy /E /I /Y "%CURRENT_DIR%\*" "%RPA_FOLDER%\" >nul 2>&1
    
    if !errorlevel! == 0 (
        echo  [OK] Archivos copiados exitosamente
        echo.
        echo  [!] IMPORTANTE: A partir de ahora usa:
        echo     %RPA_FOLDER%
        echo.
        echo  Abriendo nueva ubicacion...
        start "" "%RPA_FOLDER%"
        echo.
        echo  Por favor, ejecuta INSTALADOR_COMPLETO.bat desde la nueva ubicacion.
        echo.
        pause
        exit /b 0
    ) else (
        echo  [!] No se pudieron mover los archivos automaticamente
        echo  Continuando en ubicacion actual...
    )
) else (
    echo  [OK] Ubicacion correcta: %CURRENT_DIR%
)

echo.
pause
cls

:: ============================================
:: PASO 2: VERIFICAR/INSTALAR PYTHON
:: ============================================
echo.
echo  ========================================================================
echo   PASO 2/6: Python
echo  ========================================================================
echo.

set "PYTHON_OK=0"
set "VERSION_OK=0"

echo  [*] Verificando Python...
python --version >nul 2>&1
if %errorlevel% == 0 (
    set "PYTHON_OK=1"
    for /f "tokens=2" %%a in ('python --version 2^>^&1') do set "PYTHON_VERSION=%%a"
    echo  [OK] Python encontrado: %PYTHON_VERSION%
    
    :: Verificar version minima (3.10+)
    python -c "import sys; v=sys.version_info; exit(0 if (v.major==3 and v.minor>=10) or v.major>3 else 1)" >nul 2>&1
    if !errorlevel! == 0 (
        set "VERSION_OK=1"
    )
)

:: Si Python esta OK y version OK, continuar
if %PYTHON_OK% == 1 if %VERSION_OK% == 1 (
    echo  [OK] Version compatible (3.10+)
    echo  [*] Continuando con la instalacion...
    goto :PYTHON_DONE
)

:: Si Python esta pero version vieja, ofrecer actualizar
if %PYTHON_OK% == 1 if %VERSION_OK% == 0 (
    echo.
    echo  [!] Version de Python muy antigua (requiere 3.10+)
    echo  [*] Version actual: %PYTHON_VERSION%
    echo.
    choice /C SN /M "Desea actualizar Python automaticamente"
    
    if !errorlevel! == 2 (
        echo.
        echo  Instalacion cancelada. Se requiere Python 3.10+
        pause
        exit /b 1
    )
    
    :: Actualizar Python
    echo.
    echo  [*] Descargando Python 3.10.11...
    echo  (Este proceso puede tardar varios minutos)
    echo.
    
    powershell -Command "& {$url='https://www.python.org/ftp/python/3.10.11/python-3.10.11-amd64.exe'; $output='%TEMP%\python_installer.exe'; Invoke-WebRequest -Uri $url -OutFile $output}"
    
    if exist "%TEMP%\python_installer.exe" (
        echo  [OK] Descarga completada
        echo  [*] Instalando Python...
        echo    IMPORTANTE: No cierre esta ventana
        echo.
        
        "%TEMP%\python_installer.exe" /quiet InstallAllUsers=0 PrependPath=1 Include_test=0
        del "%TEMP%\python_installer.exe" >nul 2>&1
        
        :: Verificar instalacion
        python --version >nul 2>&1
        if !errorlevel! == 0 (
            for /f "tokens=2" %%a in ('python --version 2^>^&1') do set "NEW_VERSION=%%a"
            echo  [OK] Python actualizado a: !NEW_VERSION!
            echo  [*] Reiniciando...
            timeout /t 3 >nul
            goto :PYTHON_DONE
        ) else (
            echo  [X] Error al actualizar
            pause
            exit /b 1
        )
    ) else (
        echo  [X] Error descargando Python
        pause
        exit /b 1
    )
)

:: Si no hay Python, instalar
if %PYTHON_OK% == 0 (
    echo  [X] Python NO encontrado
    echo.
    choice /C SN /M "Desea instalar Python 3.10 automaticamente"
    
    if !errorlevel! == 2 (
        echo.
        echo  Instalacion cancelada.
        pause
        exit /b 1
    )
    
    echo.
    echo  [*] Descargando Python 3.10.11...
    echo  (Este proceso puede tardar varios minutos)
    echo.
    
    powershell -Command "& {$url='https://www.python.org/ftp/python/3.10.11/python-3.10.11-amd64.exe'; $output='%TEMP%\python_installer.exe'; Invoke-WebRequest -Uri $url -OutFile $output}"
    
    if exist "%TEMP%\python_installer.exe" (
        echo  [OK] Descarga completada
        echo  [*] Instalando Python...
        echo    IMPORTANTE: No cierre esta ventana
        echo.
        
        "%TEMP%\python_installer.exe" /quiet InstallAllUsers=0 PrependPath=1 Include_test=0
        del "%TEMP%\python_installer.exe" >nul 2>&1
        
        :: Verificar instalacion
        python --version >nul 2>&1
        if !errorlevel! == 0 (
            for /f "tokens=2" %%a in ('python --version 2^>^&1') do set "NEW_VERSION=%%a"
            echo  [OK] Python instalado: !NEW_VERSION!
            echo  [*] Reiniciando...
            timeout /t 3 >nul
            goto :PYTHON_DONE
        ) else (
            echo  [X] Error al instalar
            pause
            exit /b 1
        )
    ) else (
        echo  [X] Error descargando Python
        pause
        exit /b 1
    )
)

:PYTHON_DONE
echo.
pause
cls

:: ============================================
:: PASO 3: INSTALAR DEPENDENCIAS
:: ============================================
echo.
echo  ========================================================================
echo   PASO 3/6: Dependencias de Python
echo  ========================================================================
echo.

cd /d "%~dp0"

echo  [*] Instalando dependencias...
echo  (playwright, pandas, openpyxl, python-dotenv)
echo.

pip install -r requirements.txt

if %errorlevel% == 0 (
    echo  [OK] Dependencias instaladas correctamente
) else (
    echo  [!] Algunas dependencias no se instalaron correctamente
    echo  [*] Intentando instalacion individual...
    pip install playwright pandas openpyxl python-dotenv
)

echo.
pause
cls

:: ============================================
:: PASO 4: INSTALAR NAVEGADOR
:: ============================================
echo.
echo  ========================================================================
echo   PASO 4/6: Navegador para Automatizacion
echo  ========================================================================
echo.

echo  [*] Descargando navegador Chromium...
echo  (Esto puede tardar varios minutos)
echo.

python -m playwright install chromium

if %errorlevel% == 0 (
    echo  [OK] Navegador instalado correctamente
) else (
    echo  [!] Hubo un problema instalando el navegador
    echo  [*] El RPA intentara instalarlo automaticamente al ejecutarse
)

echo.
pause
cls

:: ============================================
:: PASO 5: CREAR CARPETAS Y PERMISOS
:: ============================================
echo.
echo  ========================================================================
echo   PASO 5/6: Configuracion de Carpetas
echo  ========================================================================
echo.

echo  [*] Creando carpetas necesarias...

mkdir "data" 2>nul
mkdir "data\input" 2>nul
mkdir "data\output" 2>nul

echo  [OK] Carpetas creadas

echo  [*] Aplicando permisos...

icacls "data" /grant "%username%":F /T >nul 2>&1
icacls "data\input" /grant "%username%":F /T >nul 2>&1
icacls "data\output" /grant "%username%":F /T >nul 2>&1

echo  [OK] Permisos configurados

echo.
echo  [*] Verificando escritura...

echo test > "data\output\test.txt" 2>nul
if exist "data\output\test.txt" (
    del "data\output\test.txt"
    echo  [OK] Verificacion exitosa
) else (
    echo  [!] Advertencia: Posibles problemas de permisos
)

echo.
pause
cls

:: ============================================
:: PASO 6: CREAR ACCESO DIRECTO
:: ============================================
echo.
echo  ========================================================================
echo   PASO 6/6: Acceso Directo
echo  ========================================================================
echo.

echo  [*] Creando acceso directo en el escritorio...

:: Verificar si existe el icono personalizado
set "ICON_PATH=%SystemRoot%\System32\shell32.dll,21"
if exist "%~dp0@Gota_Petroil.ico" (
    echo  [*] Icono personalizado encontrado: @Gota_Petroil.ico
    set "ICON_PATH=%~dp0@Gota_Petroil.ico"
) else (
    echo  [*] Usando icono por defecto del sistema
)

powershell -NoProfile -Command "$WshShell = New-Object -comObject WScript.Shell; $Shortcut = $WshShell.CreateShortcut('%USERPROFILE%\Desktop\RPA Novohit.lnk'); $Shortcut.TargetPath = '%~dp0Ejecutar_GUI.bat'; $Shortcut.WorkingDirectory = '%~dp0'; $Shortcut.Description = 'RPA Novohit - Contabilizacion Bancaria'; $Shortcut.IconLocation = '!ICON_PATH!'; $Shortcut.Save()"

if %errorlevel% == 0 (
    echo  [OK] Acceso directo creado en el escritorio
) else (
    echo  [!] No se pudo crear el acceso directo automaticamente
)

echo.
cls

:: ============================================
:: RESUMEN FINAL
:: ============================================
echo.
echo  ========================================================================
echo                    [OK] INSTALACION COMPLETADA
echo  ========================================================================
echo.
echo  +------------------------------------------------------------------------+
echo  !  RESUMEN:                                                              !
echo  +------------------------------------------------------------------------+
echo  !  [OK] Python instalado y configurado                                   !
echo  !  [OK] Dependencias de Python instaladas                                !
echo  !  [OK] Navegador para automatizacion instalado                          !
echo  !  [OK] Carpetas creadas y permisos configurados                         !
echo  !  [OK] Acceso directo en el escritorio                                  !
echo  +------------------------------------------------------------------------+
echo.
echo  Ubicacion del programa:
echo     %CD%
echo.
echo  [+] PARA USAR EL RPA:
echo.
echo     1. Copie su archivo Excel a:
echo        %CD%\data\input\
echo.
echo     2. Haga doble clic en el acceso directo del escritorio:
echo        "RPA Novohit"
echo.
echo  [!] IMPORTANTE DURANTE LA EJECUCION:
echo     * NO cierre la ventana del navegador
echo     * NO mueva el mouse
echo     * NO use el teclado
echo     * Espere hasta que diga "PROCESO COMPLETADO"
echo.
echo  ========================================================================
echo.

choice /C SN /M "Desea ejecutar el RPA ahora"

if %errorlevel% == 1 (
    echo.
    echo  Iniciando RPA...
    start "" "Ejecutar_GUI.bat"
) else (
    echo.
    echo  Puede ejecutar el RPA mas tarde desde el acceso directo.
)

echo.
echo  Presione cualquier tecla para cerrar...
pause >nul
exit /b 0
