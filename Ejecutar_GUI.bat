@echo off
chcp 65001 >nul
title RPA Novohit - Interfaz Grafica
cd /d "%~dp0"

echo ==========================================
echo    RPA NOVOHIT - Interfaz Grafica
echo ==========================================
echo.

REM Verificar Python
python --version >nul 2>&1
if errorlevel 1 (
    echo [!] Python no encontrado. Por favor instale Python 3.10+
    pause
    exit /b 1
)

echo [*] Iniciando interfaz grafica...
python gui.py
