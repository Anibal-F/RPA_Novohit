"""
Mapeos de conceptos bancarios a tipos de operación de Novohit.

Este archivo contiene los diccionarios de mapeo para cada banco.
Los conceptos del estado de cuenta se mapean a:
- Tipo de operación en Novohit (id_tp_operation)
- Descripción/comentario
- Tipo de movimiento (cargo/abono)
"""

# Mapeo para BBVA (Basado en la imagen compartida)
BBVA_MAPPINGS = {
    # Comisiones - Tipo de Operación: COMISION (value="7")
    "P./PROC.COMUNICACION GPRS": {
        "id_tp_operation": "7",
        "tipo_movimiento": "cargo",
        "descripcion": "COMISION PROCESAMIENTO GPRS",
        "categoria": "comision"
    },
    "COM VTAS TDC INTER": {
        "id_tp_operation": "7",
        "tipo_movimiento": "cargo", 
        "descripcion": "COMISION VENTAS TDC INTERNACIONAL",
        "categoria": "comision"
    },
    "APLICA TASA DESCUENTO": {
        "id_tp_operation": "7",
        "tipo_movimiento": "cargo",
        "descripcion": "APLICACION TASA DESCUENTO",
        "categoria": "comision"
    },
    
    # IVA - Tipo de Operación: IVA POR COMISIONES (value="8")
    "IVA PAGO/PROC.COMU GPRS": {
        "id_tp_operation": "8",
        "tipo_movimiento": "cargo",
        "descripcion": "IVA COMISION GPRS",
        "categoria": "iva"
    },
    "IVA COM VTAS TDC INTER": {
        "id_tp_operation": "8",
        "tipo_movimiento": "cargo",
        "descripcion": "IVA COMISION VENTAS TDC",
        "categoria": "iva"
    },
    "IVA TASA DE DESC": {
        "id_tp_operation": "8",
        "tipo_movimiento": "cargo",
        "descripcion": "IVA TASA DESCUENTO",
        "categoria": "iva"
    },
    
    # Ventas - NO se contabilizan como comisiones (para referencia)
    "VENTAS DEBITO": {
        "id_tp_operation": None,  # No se registra en este RPA
        "tipo_movimiento": "abono",
        "descripcion": "VENTAS TARJETA DEBITO",
        "categoria": "venta"
    },
    "VENTAS CREDITO": {
        "id_tp_operation": None,
        "tipo_movimiento": "abono",
        "descripcion": "VENTAS TARJETA CREDITO",
        "categoria": "venta"
    },
    "VENTAS TDC INTER": {
        "id_tp_operation": None,
        "tipo_movimiento": "abono",
        "descripcion": "VENTAS TDC INTERNACIONAL",
        "categoria": "venta"
    },
}

# Mapeo de bancos a cuentas en Novohit
BANK_ACCOUNTS = {
    "BBVA": {
        "account_id": "3",  # BANCOMER - MXN - 0122511124
        "nombre": "BANCOMER - MXN",
        "moneda": "MXN"
    },
    "BANORTE": {
        "account_id": "4",  # BANORTE - MXN - 1284217944
        "nombre": "BANORTE - MXN",
        "moneda": "MXN"
    },
    "BANREGIO": {
        "account_id": "2",  # BANREGIO - MXN - 114977800019
        "nombre": "BANREGIO - MXN",
        "moneda": "MXN"
    },
}

# Keywords para identificar tipo de operación por concepto
KEYWORDS = {
    "comision": ["COM", "COMISION", "PROC", "PROCESAMIENTO", "APLICA", "TASA"],
    "iva": ["IVA"],
    "ventas": ["VENTAS", "VTAS"],
}


def get_mapping_by_concept(concepto: str, banco: str = "BBVA"):
    """
    Busca el mapeo para un concepto específico.
    
    Args:
        concepto: Texto del concepto del estado de cuenta
        banco: Código del banco (BBVA, BANORTE, etc.)
    
    Returns:
        dict con el mapeo o None si no se encuentra
    """
    # Normalizar concepto (mayúsculas, sin espacios extra)
    concepto_norm = concepto.upper().strip()
    
    # Buscar coincidencia exacta primero
    if banco == "BBVA":
        for key, mapping in BBVA_MAPPINGS.items():
            if key.upper() in concepto_norm or concepto_norm in key.upper():
                return mapping
    
    # Si no hay coincidencia exacta, buscar por keywords
    if any(kw in concepto_norm for kw in KEYWORDS["iva"]):
        return {
            "id_tp_operation": "8",
            "tipo_movimiento": "cargo",
            "descripcion": concepto,
            "categoria": "iva"
        }
    elif any(kw in concepto_norm for kw in KEYWORDS["comision"]):
        return {
            "id_tp_operation": "7",
            "tipo_movimiento": "cargo",
            "descripcion": concepto,
            "categoria": "comision"
        }
    
    return None


def get_account_id(banco: str) -> str:
    """Obtiene el ID de cuenta para un banco."""
    return BANK_ACCOUNTS.get(banco, {}).get("account_id", "")


def should_process(concepto: str) -> bool:
    """
    Determina si un concepto debe ser procesado (comisión o IVA).
    
    Returns:
        True si es comisión o IVA, False si es venta u otro
    """
    concepto_norm = concepto.upper()
    return (
        any(kw in concepto_norm for kw in KEYWORDS["iva"]) or
        any(kw in concepto_norm for kw in KEYWORDS["comision"])
    )
