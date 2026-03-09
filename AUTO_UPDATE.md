# Sistema de Auto-Actualización RPA Novohit

## Descripción
El RPA Novohit ahora incluye un sistema de auto-actualización que permite mantener el software actualizado automáticamente desde el repositorio Git, sin necesidad de descargar y reinstalar manualmente.

## Cómo Funciona

### 1. Verificación Automática al Inicio
Cuando inicias el GUI, el sistema verifica automáticamente si hay actualizaciones disponibles en el repositorio remoto (GitHub).

### 2. Notificación al Usuario
Si hay actualizaciones disponibles, se muestra un diálogo preguntando si deseas actualizar:
- **Sí**: Aplica la actualización y reinicia la aplicación
- **No**: Continúa con la versión actual

### 3. Verificación Manual
También puedes verificar actualizaciones manualmente en cualquier momento usando el botón **"🔄 Verificar Actualizaciones"** en la interfaz principal.

## Requisitos

Para que el sistema de actualización funcione, necesitas:

1. **Git instalado** en el sistema
   - Descargar desde: https://git-scm.com/download/win
   - Durante la instalación, asegúrate de seleccionar "Add to PATH"

2. **Conexión a Internet**
   - El sistema necesita conectar con GitHub para verificar cambios

3. **El proyecto debe ser un repositorio Git**
   - Si instalaste usando `git clone`, ya cumples este requisito
   - Si instalaste por ZIP, necesitas inicializar git:
     ```bash
     git init
     git remote add origin https://github.com/Anibal-F/RPA_Novohit.git
     ```

## Casos Especiales

### Cambios Locales sin Guardar
Si tienes cambios locales que no has commiteado, el sistema **NO** actualizará automáticamente para evitar perder tu trabajo. Verás un mensaje indicando que debes guardar tus cambios primero.

### Sin Git Instalado
Si no tienes Git instalado, el sistema funcionará normalmente pero mostrará un mensaje en el log indicando que no puede verificar actualizaciones.

### Sin Conexión a Internet
Si no hay conexión a internet, el sistema funcionará normalmente con la versión local instalada.

## Flujo de Trabajo para Desarrolladores

Si eres el desarrollador y haces cambios:

1. **Commitea tus cambios**:
   ```bash
   git add .
   git commit -m "Descripción del cambio"
   ```

2. **Sube al repositorio**:
   ```bash
   git push origin master
   ```

3. **Los usuarios recibirán la actualización** automáticamente al iniciar el GUI

## Solución de Problemas

### "Git no está instalado"
Instala Git desde https://git-scm.com/download/win y asegúrate de reiniciar el equipo después.

### "El proyecto no es un repositorio Git"
Si instalaste desde ZIP, inicializa el repositorio:
```bash
cd C:\RPA_Novohit
git init
git remote add origin https://github.com/Anibal-F/RPA_Novohit.git
git pull origin master
```

### Errores de Permisos
Si ves errores de permisos al actualizar, ejecuta el GUI como Administrador o usa el script `Arreglar_Permisos.bat`.

## Ventajas

1. **No más ZIPs**: Los usuarios siempre tendrán la última versión
2. **Historial de cambios**: Se puede ver qué cambió en cada actualización
3. **Rollback**: Si algo falla, se puede volver a una versión anterior con Git
4. **Colaboración**: Varios desarrolladores pueden contribuir fácilmente

## Seguridad

- Las actualizaciones solo se aplican desde el repositorio oficial
- No se pierden datos locales al actualizar
- Se mantiene una copia de seguridad del historial completo
