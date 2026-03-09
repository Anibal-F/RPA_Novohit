"""
Módulo Updater: Verifica y aplica actualizaciones automáticas desde Git.
"""
import subprocess
import os
import sys
from pathlib import Path
import logging

logger = logging.getLogger(__name__)


class AutoUpdater:
    """
    Maneja la verificación y aplicación de actualizaciones desde Git.
    """
    
    def __init__(self, project_path: str = None):
        self.project_path = Path(project_path) if project_path else Path(__file__).parent.parent
        self.git_available = self._check_git_available()
        
    def _check_git_available(self) -> bool:
        """Verifica si Git está disponible en el sistema."""
        try:
            result = subprocess.run(
                ['git', '--version'],
                capture_output=True,
                text=True,
                timeout=5
            )
            return result.returncode == 0
        except (subprocess.SubprocessError, FileNotFoundError):
            return False
    
    def is_git_repository(self) -> bool:
        """Verifica si el proyecto es un repositorio Git."""
        try:
            result = subprocess.run(
                ['git', 'rev-parse', '--git-dir'],
                cwd=self.project_path,
                capture_output=True,
                text=True,
                timeout=5
            )
            return result.returncode == 0
        except subprocess.SubprocessError:
            return False
    
    def has_internet_connection(self) -> bool:
        """Verifica si hay conexión a internet."""
        import socket
        try:
            # Intenta conectar a GitHub
            socket.create_connection(("github.com", 443), timeout=5)
            return True
        except OSError:
            return False
    
    def has_local_changes(self) -> bool:
        """Verifica si hay cambios locales sin commit."""
        try:
            result = subprocess.run(
                ['git', 'status', '--porcelain'],
                cwd=self.project_path,
                capture_output=True,
                text=True,
                timeout=5
            )
            # Si hay salida, hay cambios sin commit
            return bool(result.stdout.strip())
        except subprocess.SubprocessError:
            return False
    
    def check_for_updates(self) -> dict:
        """
        Verifica si hay actualizaciones disponibles.
        
        Returns:
            dict con información sobre el estado de las actualizaciones
        """
        result = {
            'success': False,
            'has_updates': False,
            'message': '',
            'details': ''
        }
        
        # Verificar prerequisitos
        if not self.git_available:
            result['message'] = 'Git no está instalado o no está en el PATH'
            return result
        
        if not self.is_git_repository():
            result['message'] = 'El proyecto no es un repositorio Git'
            return result
        
        if not self.has_internet_connection():
            result['message'] = 'No hay conexión a internet'
            return result
        
        try:
            # Fetch para obtener los últimos cambios del remoto
            logger.info("Verificando actualizaciones en el repositorio...")
            fetch_result = subprocess.run(
                ['git', 'fetch', 'origin'],
                cwd=self.project_path,
                capture_output=True,
                text=True,
                timeout=30
            )
            
            if fetch_result.returncode != 0:
                result['message'] = 'Error al obtener información del servidor'
                result['details'] = fetch_result.stderr
                return result
            
            # Verificar si hay cambios locales sin commit
            if self.has_local_changes():
                result['message'] = 'Hay cambios locales sin guardar'
                result['details'] = 'No se puede actualizar automáticamente porque hay cambios locales. Por favor guarde sus cambios primero.'
                return result
            
            # Verificar si la rama local está detrás del remoto
            status_result = subprocess.run(
                ['git', 'status', '-uno'],
                cwd=self.project_path,
                capture_output=True,
                text=True,
                timeout=5
            )
            
            if "Your branch is behind" in status_result.stdout:
                result['success'] = True
                result['has_updates'] = True
                result['message'] = 'Hay actualizaciones disponibles'
                
                # Obtener información de los commits pendientes
                log_result = subprocess.run(
                    ['git', 'log', 'HEAD..origin/master', '--oneline'],
                    cwd=self.project_path,
                    capture_output=True,
                    text=True,
                    timeout=5
                )
                if log_result.returncode == 0 and log_result.stdout:
                    result['details'] = f"Commits pendientes:\n{log_result.stdout}"
                
            elif "Your branch is up to date" in status_result.stdout:
                result['success'] = True
                result['has_updates'] = False
                result['message'] = 'El proyecto está actualizado'
            else:
                # Intentar con 'main' si 'master' no funcionó
                log_result = subprocess.run(
                    ['git', 'log', 'HEAD..origin/main', '--oneline'],
                    cwd=self.project_path,
                    capture_output=True,
                    text=True,
                    timeout=5
                )
                if log_result.returncode == 0 and log_result.stdout.strip():
                    result['success'] = True
                    result['has_updates'] = True
                    result['message'] = 'Hay actualizaciones disponibles (rama main)'
                    result['details'] = f"Commits pendientes:\n{log_result.stdout}"
                else:
                    result['success'] = True
                    result['has_updates'] = False
                    result['message'] = 'El proyecto está actualizado'
            
            return result
            
        except subprocess.TimeoutExpired:
            result['message'] = 'Tiempo de espera agotado al verificar actualizaciones'
            return result
        except subprocess.SubprocessError as e:
            result['message'] = f'Error al verificar actualizaciones: {str(e)}'
            return result
    
    def apply_updates(self) -> dict:
        """
        Aplica las actualizaciones haciendo pull.
        
        Returns:
            dict con el resultado de la operación
        """
        result = {
            'success': False,
            'message': '',
            'details': ''
        }
        
        try:
            logger.info("Aplicando actualizaciones...")
            
            # Primero intentar con master
            pull_result = subprocess.run(
                ['git', 'pull', 'origin', 'master'],
                cwd=self.project_path,
                capture_output=True,
                text=True,
                timeout=60
            )
            
            # Si falla, intentar con main
            if pull_result.returncode != 0 and "main" in pull_result.stderr:
                pull_result = subprocess.run(
                    ['git', 'pull', 'origin', 'main'],
                    cwd=self.project_path,
                    capture_output=True,
                    text=True,
                    timeout=60
                )
            
            if pull_result.returncode == 0:
                result['success'] = True
                result['message'] = 'Actualización completada exitosamente'
                result['details'] = pull_result.stdout
                logger.info("Actualización aplicada correctamente")
            else:
                result['message'] = 'Error al aplicar actualizaciones'
                result['details'] = pull_result.stderr
                logger.error(f"Error en pull: {pull_result.stderr}")
            
            return result
            
        except subprocess.TimeoutExpired:
            result['message'] = 'Tiempo de espera agotado al aplicar actualizaciones'
            return result
        except subprocess.SubprocessError as e:
            result['message'] = f'Error al aplicar actualizaciones: {str(e)}'
            return result
    
    def get_current_version(self) -> str:
        """Obtiene la versión actual (último commit)."""
        try:
            result = subprocess.run(
                ['git', 'log', '-1', '--oneline'],
                cwd=self.project_path,
                capture_output=True,
                text=True,
                timeout=5
            )
            if result.returncode == 0:
                return result.stdout.strip()
            return "Versión desconocida"
        except:
            return "Versión desconocida"


def check_and_update(show_ui_callback=None) -> dict:
    """
    Función de conveniencia para verificar y aplicar actualizaciones.
    
    Args:
        show_ui_callback: Función opcional para mostrar mensajes en la UI
        
    Returns:
        dict con el resultado de la operación
    """
    updater = AutoUpdater()
    
    # Verificar si hay actualizaciones
    check_result = updater.check_for_updates()
    
    if not check_result['success']:
        if show_ui_callback:
            show_ui_callback(f"⚠️ {check_result['message']}", 'warning')
        return check_result
    
    if not check_result['has_updates']:
        if show_ui_callback:
            show_ui_callback(f"✅ {check_result['message']}", 'info')
        return check_result
    
    # Hay actualizaciones disponibles
    if show_ui_callback:
        show_ui_callback(f"📦 {check_result['message']}\n{check_result.get('details', '')}", 'info')
    
    # Aplicar actualizaciones
    update_result = updater.apply_updates()
    
    if update_result['success']:
        if show_ui_callback:
            show_ui_callback(f"✅ {update_result['message']}\n{update_result.get('details', '')}", 'success')
    else:
        if show_ui_callback:
            show_ui_callback(f"❌ {update_result['message']}\n{update_result.get('details', '')}", 'error')
    
    return update_result


if __name__ == "__main__":
    # Prueba del módulo
    logging.basicConfig(level=logging.INFO)
    result = check_and_update()
    print(f"Resultado: {result}")
