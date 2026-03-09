# Script para crear acceso directo de la GUI en el escritorio
$WshShell = New-Object -comObject WScript.Shell

$DesktopPath = [Environment]::GetFolderPath("Desktop")
$BatchPath = Join-Path $PSScriptRoot "Ejecutar_GUI.bat"

# Verificar si existe el icono personalizado
$IconPath = Join-Path $PSScriptRoot "@Gota_Petroil.ico"
if (Test-Path $IconPath) {
    $IconLocation = $IconPath
    Write-Host "[*] Icono personalizado encontrado: @Gota_Petroil.ico" -ForegroundColor Cyan
} else {
    $IconLocation = "$env:SystemRoot\System32\shell32.dll,21"
    Write-Host "[*] Usando icono por defecto del sistema" -ForegroundColor Cyan
}

$Shortcut = $WshShell.CreateShortcut("$DesktopPath\RPA Novohit.lnk")
$Shortcut.TargetPath = $BatchPath
$Shortcut.WorkingDirectory = $PSScriptRoot
$Shortcut.Description = "RPA Novohit - Contabilizacion Bancaria (Interfaz Grafica)"
$Shortcut.IconLocation = $IconLocation
$Shortcut.Save()

Write-Host "[OK] Acceso directo creado exitosamente!" -ForegroundColor Green
Write-Host "   Ubicacion: $DesktopPath\RPA Novohit.lnk" -ForegroundColor Cyan
Write-Host ""
Write-Host "[i] Instrucciones de uso:" -ForegroundColor Yellow
Write-Host "   1. Coloque su archivo Excel en: data\input\" -ForegroundColor White
Write-Host "   2. Doble clic en 'RPA Novohit' en el escritorio" -ForegroundColor White
Write-Host "   3. Seleccione el archivo y haga clic en INICIAR" -ForegroundColor White
Write-Host "   4. No use el mouse/teclado durante el proceso" -ForegroundColor White
Write-Host ""
Pause
