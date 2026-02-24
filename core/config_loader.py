"""
Módulo Config Loader: Lee configuración desde hoja "Configuración" del Excel.
"""
import pandas as pd
from pathlib import Path
from typing import Dict, Optional
import logging

logger = logging.getLogger(__name__)


class ExcelConfigLoader:
    """
    Carga configuración de nomenclaturas desde la hoja 'Configuración' del Excel.
    """
    
    def __init__(self, file_path: str):
        self.file_path = Path(file_path)
        self.config = {}
        
    def __init__(self, file_path: str):
        self.file_path = Path(file_path)
        self.config = {}
        self.bank_account_id = None  # ID de cuenta bancaria desde celda C1
        
    def load_config(self) -> Dict:
        """
        Lee la hoja 'Configuración' del Excel.
        
        Returns:
            Diccionario con la configuración por tipo de operación
        """
        try:
            # Leer primero la celda C1 para obtener la cuenta bancaria
            self._load_bank_account()
            
            # Intentar leer la hoja Configuración (desde fila 2 para omitir header de cuenta)
            df = pd.read_excel(self.file_path, sheet_name='Configuración', header=1)
            logger.info(f"Configuración cargada: {len(df)} operaciones")
            
            # Normalizar columnas
            df.columns = [str(col).strip().upper() for col in df.columns]
            
            # Buscar columnas (pueden tener variaciones)
            operacion_col = self._find_column(df, ['OPERACIÓN', 'OPERACION', 'OPERACIÓN'])
            observaciones_col = self._find_column(df, ['OBSERVACIONES', 'OBSERVACION'])
            clave_col = self._find_column(df, ['CLAVE DOCUMENTO', 'CLAVE', 'DOCUMENTO'])
            cuenta_col = self._find_column(df, ['CUENTA CONTABLE', 'CUENTA', 'CONTABLE'])
            
            if not operacion_col:
                logger.warning("No se encontró columna de operación en Configuración")
                return {}
            
            # Construir diccionario de configuración
            for _, row in df.iterrows():
                try:
                    operacion = str(row.get(operacion_col, '')).strip().upper()
                    if not operacion or operacion == 'NAN':
                        continue
                    
                    observaciones_template = str(row.get(observaciones_col, '')).strip() if observaciones_col else ''
                    clave_prefix = str(row.get(clave_col, '')).strip() if clave_col else ''
                    cuenta_contable = str(row.get(cuenta_col, '')).strip() if cuenta_col else ''
                    
                    self.config[operacion] = {
                        'observaciones_template': observaciones_template,
                        'clave_prefix': clave_prefix,
                        'cuenta_contable': cuenta_contable
                    }
                    
                except Exception as e:
                    logger.warning(f"Error procesando fila de configuración: {e}")
                    continue
            
            logger.info(f"Configuración procesada: {len(self.config)} operaciones")
            for op, cfg in self.config.items():
                cuenta = cfg.get('cuenta_contable', 'N/A')
                logger.info(f"  - {op}: clave={cfg['clave_prefix']}, cuenta={cuenta[:30] if cuenta else 'N/A'}, obs={cfg['observaciones_template'][:30]}...")
            
            return self.config
            
        except Exception as e:
            logger.warning(f"No se pudo cargar configuración desde Excel: {e}")
            return {}
    
    def _find_column(self, df: pd.DataFrame, possible_names: list) -> Optional[str]:
        """Busca una columna por posibles nombres."""
        for col in df.columns:
            col_upper = str(col).upper().strip()
            for name in possible_names:
                if name.upper() in col_upper:
                    return col
        return None
    
    def _load_bank_account(self):
        """Lee el ID de cuenta bancaria desde la celda D1 de la hoja Configuración."""
        try:
            # Leer la hoja sin header para obtener la celda D1
            df_raw = pd.read_excel(self.file_path, sheet_name='Configuración', header=None)
            
            # La celda D1 está en fila 0, columna 3 (índice 3)
            if len(df_raw) > 0 and len(df_raw.columns) > 3:
                cuenta_valor = df_raw.iloc[0, 3]  # D1 = fila 0, columna 3
                cuenta_str = str(cuenta_valor).strip()
                
                # Validar que sea un número
                if cuenta_str and cuenta_str.lower() != 'nan' and cuenta_str != '':
                    # Extraer solo el valor numérico
                    import re
                    match = re.search(r'\d+', cuenta_str)
                    if match:
                        self.bank_account_id = match.group()
                        logger.info(f"ID de cuenta bancaria configurado (D1): {self.bank_account_id}")
                    else:
                        self.bank_account_id = cuenta_str
                        logger.info(f"ID de cuenta bancaria configurado (D1): {self.bank_account_id}")
                else:
                    logger.warning("Celda D1 vacía, usando cuenta por defecto")
            else:
                logger.warning("No se pudo leer celda D1, usando cuenta por defecto")
                
        except Exception as e:
            logger.warning(f"Error leyendo cuenta bancaria de D1: {e}")
    
    def get_bank_account_id(self) -> Optional[str]:
        """
        Obtiene el ID de cuenta bancaria configurado en C1.
        
        Returns:
            ID de cuenta bancaria o None si no está configurado
        """
        return self.bank_account_id
    
    def get_operation_config(self, operacion: str) -> Optional[Dict]:
        """
        Obtiene configuración para una operación específica.
        
        Args:
            operacion: Nombre de la operación (ej: 'COMISION', 'IVA POR COMISIONES')
            
        Returns:
            Dict con observaciones_template y clave_prefix, o None
        """
        operacion_norm = operacion.upper().strip()
        
        # Buscar coincidencia exacta
        if operacion_norm in self.config:
            return self.config[operacion_norm]
        
        # Buscar coincidencia parcial
        for key in self.config.keys():
            if operacion_norm in key or key in operacion_norm:
                return self.config[key]
        
        return None
    
    def format_observaciones(self, operacion: str, fecha: str) -> str:
        """
        Formatea las observaciones según el template de configuración.
        
        Args:
            operacion: Tipo de operación
            fecha: Fecha en formato DD/MM/YYYY
            
        Returns:
            String formateado
        """
        config = self.get_operation_config(operacion)
        
        if not config:
            # Fallback: usar formato genérico
            return f"{operacion} del día {fecha}"
        
        template = config.get('observaciones_template', '')
        
        # Reemplazar placeholders
        observaciones = template.replace('[FECHA]', fecha)
        observaciones = observaciones.replace(' del día:', f' del día {fecha}')
        
        return observaciones
    
    def format_clave_documento(self, operacion: str, fecha: str) -> str:
        """
        Formatea la clave de documento según configuración.
        
        Args:
            operacion: Tipo de operación
            fecha: Fecha en formato DD/MM/YYYY
            
        Returns:
            String formateado (ej: "CB-23022026")
        """
        config = self.get_operation_config(operacion)
        
        prefix = 'DOC'  # Default
        if config:
            prefix = config.get('clave_prefix', 'DOC').replace('-', '')
        
        # Limpiar fecha
        fecha_clean = fecha.replace('/', '').replace('-', '')
        
        return f"{prefix}-{fecha_clean}"


# Función de conveniencia
def load_config_from_excel(file_path: str) -> ExcelConfigLoader:
    """Carga configuración desde archivo Excel."""
    loader = ExcelConfigLoader(file_path)
    loader.load_config()
    return loader
