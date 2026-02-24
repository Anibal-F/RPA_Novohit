"""
Funciones auxiliares para el RPA.
"""
import logging
import json
from pathlib import Path
from datetime import datetime
from typing import Dict, Any


def setup_logging(log_file: Path = None):
    """
    Configura el logging del RPA.
    
    Args:
        log_file: Ruta al archivo de log
    """
    handlers = [logging.StreamHandler()]
    
    if log_file:
        log_file.parent.mkdir(parents=True, exist_ok=True)
        handlers.append(logging.FileHandler(log_file, encoding='utf-8'))
    
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=handlers
    )


def save_json(data: Any, file_path: Path, indent: int = 2):
    """
    Guarda datos en formato JSON.
    
    Args:
        data: Datos a guardar
        file_path: Ruta del archivo
        indent: Indentación para formato pretty
    """
    file_path.parent.mkdir(parents=True, exist_ok=True)
    with open(file_path, 'w', encoding='utf-8') as f:
        json.dump(data, f, indent=indent, ensure_ascii=False, default=str)


def load_json(file_path: Path) -> Any:
    """
    Carga datos desde un archivo JSON.
    
    Args:
        file_path: Ruta del archivo
        
    Returns:
        Datos cargados
    """
    with open(file_path, 'r', encoding='utf-8') as f:
        return json.load(f)


def generate_report(results: Dict, output_dir: Path):
    """
    Genera un reporte del procesamiento.
    
    Args:
        results: Resultados del procesamiento
        output_dir: Directorio de salida
    """
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    report_file = output_dir / f"report_{timestamp}.json"
    
    save_json(results, report_file)
    
    # También generar resumen en texto
    summary_file = output_dir / f"summary_{timestamp}.txt"
    with open(summary_file, 'w', encoding='utf-8') as f:
        f.write("=" * 60 + "\n")
        f.write("REPORTE DE PROCESAMIENTO - RPA NOVOHIT\n")
        f.write("=" * 60 + "\n\n")
        f.write(f"Fecha: {datetime.now().strftime('%d/%m/%Y %H:%M:%S')}\n")
        f.write(f"Total registros: {results.get('total', 0)}\n")
        f.write(f"Exitosos: {results.get('success', 0)}\n")
        f.write(f"Fallidos: {results.get('failed', 0)}\n")
        f.write(f"Tasa de éxito: {results.get('success', 0) / max(results.get('total', 1), 1) * 100:.2f}%\n")
        
        if results.get('summary'):
            f.write("\n--- Resumen por Banco ---\n")
            for key, value in results['summary'].items():
                f.write(f"{key}: {value}\n")
        
        if results.get('errors'):
            f.write("\n--- Errores ---\n")
            for error in results['errors']:
                f.write(f"Registro {error.get('index', 'N/A')}: {error.get('error', 'Desconocido')}\n")
    
    return report_file, summary_file


def format_currency(amount: float) -> str:
    """Formatea un monto como moneda mexicana."""
    return f"${amount:,.2f}"


def parse_date(date_str: str, input_format: str = "%d/%m/%Y", output_format: str = "%Y-%m-%d") -> str:
    """
    Parsea y reformatea una fecha.
    
    Args:
        date_str: Fecha en string
        input_format: Formato de entrada
        output_format: Formato de salida
        
    Returns:
        Fecha reformateada
    """
    try:
        dt = datetime.strptime(date_str, input_format)
        return dt.strftime(output_format)
    except:
        return date_str
