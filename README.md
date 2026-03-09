# 🚀 RPA Novohit - Contabilización Bancaria

## 📋 Índice
1. [Instalación](#instalación)
2. [Uso](#uso)
3. [Checklist Pre-Ejecución](#checklist-pre-ejecución)
4. [Solución de Problemas](#solución-de-problemas)
5. [Consideraciones Importantes](#consideraciones-importantes)

---

## Instalación

### Requisitos Mínimos
- Windows 10 o 11
- 4 GB RAM
- 2 GB espacio libre
- Conexión a internet (para descargar componentes)

### Instalación en 1 Paso

1. **Descomprima** el archivo `RPA_Novohit.zip` en cualquier lugar
2. **Haga doble clic** en: `INSTALADOR_COMPLETO.bat`
3. **Siga las instrucciones** en pantalla
4. **¡Listo!** El instalador hará todo automáticamente:
   - ✅ Verifica/Instala Python
   - ✅ Instala dependencias
   - ✅ Descarga navegador
   - ✅ Configura carpetas y permisos
   - ✅ Crea acceso directo en el escritorio

> **Nota:** Si está en Descargas/Documentos, el instalador moverá automáticamente a `C:\RPA_Novohit`

---

## Uso

### Primera Vez

1. **Copie su archivo Excel** a:
   ```
   C:\RPA_Novohit\data\input\
   ```

2. **Haga doble clic** en el acceso directo del escritorio: **"RPA Novohit"**

3. **En la ventana que aparece:**
   - Seleccione el archivo Excel (o use el predeterminado)
   - Haga clic en **"INICIAR PROCESO"**

4. **¡IMPORTANTE! Durante la ejecución:**
   - ❌ NO cierre el navegador que se abre
   - ❌ NO mueva el mouse
   - ❌ NO use el teclado
   - ❌ NO haga clic en ninguna parte
   - ✅ Espere hasta "PROCESO COMPLETADO"

### Uso Posterior
Simplemente haga doble clic en el acceso directo del escritorio y siga los pasos 3-4.

---

## Checklist Pre-Ejecución

Antes de cada ejecución, verifique:

- [ ] **Cerrar Chrome completamente**
  - Cerrar todas las pestañas
  - Cerrar desde la barra de tareas
  - Verificar en Administrador de tareas (Ctrl+Shift+Esc) que no haya chrome.exe

- [ ] **Verificar archivo Excel**
  - Colocado en: `data/input/`
  - Formato correcto (hojas "Edo.Cuenta" y "Configuración")

- [ ] **Cerrar otras aplicaciones**
  - Outlook, Word, Excel (excepto el del RPA)
  - Teams, Slack, etc.
  - Juegos, videos, etc.

### Durante la Ejecución (MUY IMPORTANTE)

- [ ] **NO tocar el mouse**
- [ ] **NO tocar el teclado**
- [ ] **NO hacer clic en ninguna ventana**
- [ ] **NO cerrar el navegador que abre el RPA**
- [ ] **NO minimizar el navegador**
- [ ] Dejar que la PC trabaje sola

### Post-ejecución

- [ ] Revisar resumen en la GUI
- [ ] Verificar reportes en `data/output/`
- [ ] Revisar si hubo errores en el log

**Tiempo estimado:** ~30 segundos por registro  
**Para 10 registros:** ~5 minutos  
**Para 100 registros:** ~45 minutos

**⚠️ NO DEJE LA PC EN SUSPENSIÓN DURANTE LA EJECUCIÓN**

---

## Solución de Problemas

### "Windows protegió su PC" (SmartScreen)

**Causa:** Windows bloquea archivos descargados  
**Solución:**
1. Clic en "Más información"
2. Clic en "Ejecutar de todos modos"

### "Acceso denegado" o "Permission denied"

**Causa:** Windows bloquea la carpeta Descargas/Documentos  
**Solución:**
1. Mueva la carpeta `RPA_Novohit` a `C:\` (directamente)
2. Ejecute desde `C:\RPA_Novohit\`
3. O ejecute `Arreglar_Permisos.bat` como Administrador

### "Python no encontrado" después de instalar

**Causa:** Python no se agregó al PATH  
**Solución:**
1. Cierre y vuelva a abrir la ventana de comandos
2. O reinicie la computadora

### "No se pudo instalar Python automáticamente"

**Solución:**
1. Vaya a: https://www.python.org/downloads/
2. Descargue Python 3.10 o superior
3. ⚠️ **IMPORTANTE:** Marque "Add Python to PATH"
4. Instale y vuelva a ejecutar el instalador del RPA

### El navegador no abre o se cierra solo

**Causa:** Chrome está abierto o hay interferencia  
**Solución:**
1. Cierre completamente Google Chrome (todas las ventanas)
2. Verifique en el Administrador de tareas que no haya chrome.exe
3. Vuelva a ejecutar el RPA

### Error: "Target page, context or browser has been closed"

**Causa:** El navegador se cerró o el usuario hizo clic en él  
**Solución:**
1. Cierre el RPA
2. Cierre Chrome completamente (Ctrl+Shift+Esc → finalizar chrome.exe)
3. Vuelva a iniciar el RPA
4. **NO haga clic en el navegador durante la ejecución**

### El navegador se abre pero no hace nada

**Causa:** El sistema Novohit está lento o el RPA perdió el foco  
**Solución:**
1. Deje que espere hasta 2 minutos
2. Si sigue congelado, cierre y reinicie

### Error: "No module named 'playwright'"

**Causa:** No se instalaron las dependencias  
**Solución:**
```cmd
cd C:\RPA_Novohit
pip install -r requirements.txt
python -m playwright install chromium
```

---

## Consideraciones Importantes

### Estructura del Archivo Excel

El archivo Excel debe tener:

1. **Hoja "Edo.Cuenta"** con los movimientos bancarios
2. **Hoja "Configuración"** con:
   - Celda D1: ID de la cuenta bancaria
   - Celda L1: ID de unidad de negocio (opcional)
   - Mapeo de operaciones y cuentas contables

### Formato de la hoja "Edo.Cuenta":

| FECHA OPERACIÓN | CONCEPTO | REFERENCIA | CARGO | ABONO |
|-----------------|----------|------------|-------|-------|
| 23/02/2026 | IVA POR COMISIONES | ... | 0.47 | |
| 23/02/2026 | COMISION BANCARIA | ... | 2.94 | |

### Configuración de Credenciales

Antes de usar por primera vez, configure el archivo `.env.Novohit`:

```env
NOVOHIT_URL=https://grupopetroil.novohit.com/ccgen/user_login.php
NOVOHIT_USERNAME=TU_USUARIO
NOVOHIT_PASSWORD=TU_PASSWORD
```

**Para editar:**
1. Clic derecho en `.env.Novohit` → Abrir con → Bloc de notas
2. Modifique usuario y contraseña
3. Guardar (Ctrl+G)

### Rendimiento Esperado

- **Velocidad:** ~25-30 segundos por registro
- **Tiempo estimado:**
  - 10 registros = ~5 minutos
  - 100 registros = ~45 minutos
  - 648 registros = ~5 horas

**NO deje la PC en suspensión durante la ejecución**

### Consejos

1. **Pruebe primero con pocos registros:**
   - Modifique el archivo `gui.py`
   - Busque `limit=` y ponga `--limit 3` para probar con 3 registros

2. **Ejecute fuera de horario pico:**
   - El sistema Novohit es más rápido en la mañana (8-10am) o tarde (6-8pm)

3. **No deje la PC en suspensión:**
   - Configure para que la pantalla no se apague
   - Panel de control → Opciones de energía → Nunca suspender

4. **Si falla en el primer registro:**
   - Probablemente las credenciales están mal
   - Verifique el archivo `.env.Novohit`

---

## 📁 Estructura de Archivos

```
C:\RPA_Novohit\
├── 📄 INSTALADOR_COMPLETO.bat     ← Instalador (ejecutar primero)
├── 📄 Ejecutar_GUI.bat            ← Ejecutar el RPA
├── 📄 Arreglar_Permisos.bat       ← Fix permisos (si hay problemas)
├── 📄 Verificar_Pre_Ejecucion.bat ← Verificar antes de usar
├── 📄 README.md                   ← Este archivo
├── 📄 gui.py                      ← Interfaz gráfica
├── 📄 main.py                     ← Programa principal
├── 📁 core\                       ← Código del RPA
├── 📁 config\                     ← Configuraciones
├── 📁 data\
│   ├── 📁 input\                  ← Coloque aquí su Excel
│   │   └── estado_cuenta.xlsx
│   └── 📁 output\                 ← Reportes generados aquí
│       ├── report_*.json
│       ├── summary_*.txt
│       └── rpa_novohit.log
└── 📄 .env.Novohit                ← Credenciales (configurar)
```

---

## 🆘 Soporte

Si tiene problemas persistentes:

1. Revise el archivo de log: `data\output\rpa_novohit.log`
2. Tome captura de pantalla del error
3. Contacte al administrador con:
   - Versión de Windows
   - Mensaje de error exacto
   - Archivo de log

---

**Versión:** 1.0  
**Fecha:** Febrero 2026

**Recomendación:** La primera vez, pruebe con pocos registros (10-20) para verificar que todo funciona correctamente.
