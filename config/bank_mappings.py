"""
Mapeos de conceptos bancarios a tipos de operacion de Novohit.

Este archivo contiene los diccionarios de mapeo para cada banco.
Los conceptos se leen de archivos JSON en config/bank_concepts/
"""
import json
from pathlib import Path
from typing import Dict, Optional

# Directorio donde se almacenan los conceptos JSON
CONCEPTS_DIR = Path(__file__).parent / "bank_concepts"

# ============================================================
# CONFIGURACION DE CUENTAS POR BANCO
# ============================================================
BANK_ACCOUNTS = {
    "BBVA": {
        "account_id": "3",
        "nombre": "BANCOMER - MXN",
        "moneda": "MXN",
        "columnas": {
            "fecha": ["FECHA", "FECHA OPERACION", "FECHA OPERACIÓN"],
            "concepto": ["CONCEPTO", "DESCRIPCION", "DESCRIPCIÓN"],
            "referencia": ["REFERENCIA", "REF"],
            "cargo": ["CARGO"],
            "abono": ["ABONO"]
        }
    },
    "BANORTE": {
        "account_id": "4",
        "nombre": "BANORTE - MXN",
        "moneda": "MXN",
        "columnas": {
            "fecha": ["FECHA", "FECHA DE C"],
            "concepto": ["DESCRIPCION", "DESCRIPCIÓN", "DESCRIP"],
            "referencia": ["REFERENCIA"],
            "cargo": ["RETIROS"],
            "abono": ["DEPOSITOS", "DEPÓSITOS"]
        }
    },
    "BANREGIO": {
        "account_id": "2",
        "nombre": "BANREGIO - MXN",
        "moneda": "MXN",
        "columnas": {
            "fecha": ["FECHA"],
            "concepto": ["DESCRIPCION", "DESCRIPCIÓN", "DESCRIP"],
            "referencia": ["REFERENCIA"],
            "cargo": ["CARGO"],
            "abono": ["ABONO"]
        }
    },
}

# ============================================================
# KEYWORDS PARA IDENTIFICAR TIPO DE OPERACION (Modo Automático)
# ============================================================
KEYWORDS = {
    "comision": ["COM", "COMISION", "COMISIÓN", "PROC", "PROCESAMIENTO", "APLICA", "TASA", "SPEI", "DESCUENTO"],
    "iva": ["IVA"],
    "ventas": ["VENTAS", "VTAS", "ABONO", "DEPOSITO", "DEPÓSITO"],
}

# Mapeo de categorías a IDs de operación para modo automático
CATEGORY_TO_OPERATION = {
    "comision": {"id": "7", "nombre": "COMISION"},
    "iva": {"id": "8", "nombre": "IVA POR COMISIONES"},
    "ventas": {"id": None, "nombre": "VENTA"},  # None = No se procesa en este RPA
}


# ============================================================
# FUNCIONES PARA GESTIONAR CONCEPTOS JSON
# ============================================================

def load_bank_mappings(banco: str) -> Dict:
    """
    Carga los mapeos de un banco desde el archivo JSON.
    
    Args:
        banco: Codigo del banco (BBVA, BANORTE, BANREGIO)
        
    Returns:
        Dict con los mapeos del banco
    """
    json_file = CONCEPTS_DIR / f"{banco.upper()}.json"
    
    if json_file.exists():
        try:
            with open(json_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
                return data.get("mappings", {})
        except Exception as e:
            print(f"Error cargando mapeos de {banco}: {e}")
    
    return {}


def save_bank_mappings(banco: str, mappings: Dict, description: str = ""):
    """
    Guarda los mapeos de un banco en el archivo JSON.
    
    Args:
        banco: Codigo del banco (BBVA, BANORTE, BANREGIO)
        mappings: Dict con los mapeos
        description: Descripcion opcional
    """
    json_file = CONCEPTS_DIR / f"{banco.upper()}.json"
    
    data = {
        "bank_name": banco.upper(),
        "description": description or f"Mapeos de conceptos para {banco}",
        "mappings": mappings
    }
    
    try:
        with open(json_file, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
        return True
    except Exception as e:
        print(f"Error guardando mapeos de {banco}: {e}")
        return False


def get_all_banks() -> list:
    """
    Obtiene la lista de todos los bancos disponibles.
    
    Returns:
        Lista de codigos de banco
    """
    banks = []
    for json_file in CONCEPTS_DIR.glob("*.json"):
        banks.append(json_file.stem)
    return sorted(banks)


def add_mapping(banco: str, concepto: str, id_tp_operation: str, 
                tipo_movimiento: str, descripcion: str, categoria: str = "comision"):
    """
    Agrega un nuevo mapeo de concepto para un banco.
    
    Args:
        banco: Codigo del banco
        concepto: Texto del concepto a mapear
        id_tp_operation: ID del tipo de operacion (7=COMISION, 8=IVA)
        tipo_movimiento: 'cargo' o 'abono'
        descripcion: Descripcion para Novohit
        categoria: 'comision' o 'iva'
        
    Returns:
        True si se guardo correctamente
    """
    mappings = load_bank_mappings(banco)
    
    mappings[concepto.upper()] = {
        "id_tp_operation": id_tp_operation,
        "tipo_movimiento": tipo_movimiento,
        "descripcion": descripcion,
        "categoria": categoria
    }
    
    return save_bank_mappings(banco, mappings)


def delete_mapping(banco: str, concepto: str):
    """
    Elimina un mapeo de concepto.
    
    Args:
        banco: Codigo del banco
        concepto: Concepto a eliminar
        
    Returns:
        True si se elimino correctamente
    """
    mappings = load_bank_mappings(banco)
    
    concepto_upper = concepto.upper()
    if concepto_upper in mappings:
        del mappings[concepto_upper]
        return save_bank_mappings(banco, mappings)
    
    return False


# ============================================================
# FUNCIONES DE MAPEO (mantener compatibilidad)
# ============================================================

def _normalize_text(text: str) -> str:
    """Normaliza texto: mayusculas, sin espacios extra, sin tildes."""
    text = text.upper().strip()
    # Quitar tildes
    for char, replacement in [('Á', 'A'), ('É', 'E'), ('Í', 'I'), ('Ó', 'O'), ('Ú', 'U'),
                               ('À', 'A'), ('È', 'E'), ('Ì', 'I'), ('Ò', 'O'), ('Ù', 'U'),
                               ('Ä', 'A'), ('Ë', 'E'), ('Ï', 'I'), ('Ö', 'O'), ('Ü', 'U')]:
        text = text.replace(char, replacement)
    return text


def get_mapping_by_concept(concepto: str, banco: str = "BBVA", strict_mode: bool = True):
    """
    Busca el mapeo para un concepto especifico.
    
    Args:
        concepto: Texto del concepto del estado de cuenta
        banco: Codigo del banco (BBVA, BANORTE, BANREGIO)
        strict_mode: True = Solo diccionario, False = Tambien usar keywords
    
    Returns:
        dict con el mapeo o None si no se encuentra
    """
    # Normalizar concepto (sin tildes)
    concepto_norm = _normalize_text(concepto)
    
    # Cargar mapeos del banco desde JSON
    bank_mapping = load_bank_mappings(banco)
    
    # Buscar la MEJOR coincidencia respetando lo definido en el diccionario
    # Primero: buscar coincidencias al INICIO del concepto (más específicas)
    # Segundo: buscar coincidencias en cualquier parte (por longitud descendente)
    
    sorted_keys = sorted(bank_mapping.keys(), key=len, reverse=True)
    best_match = None
    best_position = float('inf')  # Posición más cercana al inicio
    
    for key in sorted_keys:
        mapping = bank_mapping[key]
        key_norm = _normalize_text(key)
        
        # Buscar la posición donde aparece la clave en el concepto
        pos = concepto_norm.find(key_norm)
        
        if pos != -1:  # Si encontró coincidencia
            # Priorizar: 1) Posición más cercana al inicio, 2) Longitud más larga
            if pos < best_position or (pos == best_position and len(key_norm) > len(_normalize_text(best_match or ''))):
                best_match = key
                best_position = pos
    
    if best_match:
        return bank_mapping[best_match]
    
    # Si no esta en el diccionario y NO estamos en modo estricto, buscar por keywords
    if not strict_mode:
        # Detectar IVA
        if any(kw in concepto_norm for kw in KEYWORDS["iva"]):
            return {
                "id_tp_operation": CATEGORY_TO_OPERATION["iva"]["id"],
                "tipo_movimiento": "cargo",
                "descripcion": concepto,
                "categoria": "iva"
            }
        # Detectar COMISIONES/DESCUENTOS
        elif any(kw in concepto_norm for kw in KEYWORDS["comision"]):
            return {
                "id_tp_operation": CATEGORY_TO_OPERATION["comision"]["id"],
                "tipo_movimiento": "cargo",
                "descripcion": concepto,
                "categoria": "comision"
            }
        # Detectar VENTAS (pero no procesarlas en este RPA, solo identificar)
        elif any(kw in concepto_norm for kw in KEYWORDS["ventas"]):
            return {
                "id_tp_operation": None,
                "tipo_movimiento": "abono",
                "descripcion": concepto,
                "categoria": "venta"
            }
    
    # Si no esta en el diccionario y estamos en modo estricto, NO procesar
    return None


def get_account_id(banco: str) -> str:
    """Obtiene el ID de cuenta para un banco."""
    return BANK_ACCOUNTS.get(banco, {}).get("account_id", "")


def get_bank_columns(banco: str) -> dict:
    """Obtiene la configuracion de columnas para un banco."""
    return BANK_ACCOUNTS.get(banco, {}).get("columnas", {})


def should_process(concepto: str, banco: str = "BBVA", strict_mode: bool = True) -> bool:
    """
    Determina si un concepto debe ser procesado.
    
    Args:
        concepto: Texto del concepto
        banco: Codigo del banco
        strict_mode: True = Solo diccionario, False = Tambien usar keywords
    
    Returns:
        True si debe procesarse, False si no
    """
    mapping = get_mapping_by_concept(concepto, banco, strict_mode)
    
    # Si no hay mapeo, no procesar
    if mapping is None:
        return False
    
    # Si hay mapeo pero no tiene id_tp_operation (ej: ventas en modo automatico), no procesar
    if mapping.get("id_tp_operation") is None:
        return False
    
    # Si hay mapeo con id_tp_operation, procesar
    return True
