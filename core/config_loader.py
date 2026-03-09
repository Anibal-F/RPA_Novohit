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
            # Leer primero la celda B1 para obtener el nombre del banco
            self._load_bank_name()
            
            # Leer celda D1 para obtener la cuenta bancaria
            self._load_bank_account()
            
            # Leer celda L1 para obtener unidad de negocio
            self._load_unidad_negocio()
            
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
    
    def _load_bank_name(self):
        """Lee el nombre del banco desde la celda B1 de la hoja Configuración."""
        try:
            # Leer la hoja sin header para obtener la celda B1
            df_raw = pd.read_excel(self.file_path, sheet_name='Configuración', header=None)
            
            # La celda B1 está en fila 0, columna 1 (índice 1, ya que A=0, B=1)
            if len(df_raw) > 0 and len(df_raw.columns) > 1:
                banco_valor = df_raw.iloc[0, 1]  # B1 = fila 0, columna 1
                banco_str = str(banco_valor).strip().upper()
                
                # Mapeo de nombres comunes a códigos de banco
                bank_mapping = {
                    'BBVA': 'BBVA',
                    'BANCOMER': 'BBVA',
                    'BANORTE': 'BANORTE',
                    'IXE': 'BANORTE',
                    'BANREGIO': 'BANREGIO',
                }
                
                if banco_str and banco_str.lower() != 'nan' and banco_str != '':
                    # Buscar coincidencia en el mapeo
                    for key, value in bank_mapping.items():
                        if key in banco_str:
                            self.bank_name = value
                            logger.info(f"Banco configurado (B1): {self.bank_name} (desde: {banco_str})")
                            return
                    
                    # Si no hay coincidencia, usar el valor directo si es válido
                    if banco_str in ['BBVA', 'BANORTE', 'BANREGIO']:
                        self.bank_name = banco_str
                        logger.info(f"Banco configurado (B1): {self.bank_name}")
                    else:
                        logger.warning(f"Banco en B1 no reconocido: {banco_str}")
                else:
                    logger.info("Celda B1 vacía, se detectará banco por nombre de archivo")
            else:
                logger.info("No se pudo leer celda B1, se detectará banco por nombre de archivo")
                
        except Exception as e:
            logger.warning(f"Error leyendo nombre de banco de B1: {e}")
    
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
    
    def _load_unidad_negocio(self):
        """Lee el ID de unidad de negocio desde la celda L1 de la hoja Configuración."""
        try:
            # Leer la hoja sin header para obtener la celda L1
            df_raw = pd.read_excel(self.file_path, sheet_name='Configuración', header=None)
            
            # La celda L1 está en fila 0, columna 11 (índice 11, ya que A=0, B=1, ..., L=11)
            if len(df_raw) > 0 and len(df_raw.columns) > 11:
                unidad_valor = df_raw.iloc[0, 11]  # L1 = fila 0, columna 11
                unidad_str = str(unidad_valor).strip()
                
                # Validar que sea un número
                if unidad_str and unidad_str.lower() != 'nan' and unidad_str != '':
                    # Extraer solo el valor numérico
                    import re
                    match = re.search(r'\d+', unidad_str)
                    if match:
                        self.unidad_negocio_id = match.group()
                        logger.info(f"ID de unidad de negocio configurado (L1): {self.unidad_negocio_id}")
                    else:
                        self.unidad_negocio_id = unidad_str
                        logger.info(f"ID de unidad de negocio configurado (L1): {self.unidad_negocio_id}")
                else:
                    logger.info("Celda L1 vacía, se usará selección automática de unidad de negocio")
            else:
                logger.info("No se pudo leer celda L1, se usará selección automática")
                
        except Exception as e:
            logger.warning(f"Error leyendo unidad de negocio de L1: {e}")
    
    def get_bank_name(self) -> Optional[str]:
        """
        Obtiene el nombre del banco configurado en C1.
        
        Returns:
            Nombre del banco (BBVA, BANORTE, BANREGIO) o None si no está configurado
        """
        return self.bank_name
    
    def get_bank_account_id(self) -> Optional[str]:
        """
        Obtiene el ID de cuenta bancaria configurado en D1.
        
        Returns:
            ID de cuenta bancaria o None si no está configurado
        """
        return self.bank_account_id
    
    def get_unidad_negocio_id(self) -> Optional[str]:
        """
        Obtiene el ID de unidad de negocio configurado en L1.
        
        Returns:
            ID de unidad de negocio o None si no está configurado
        """
        return self.unidad_negocio_id
    
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
    
    def format_clave_documento(self, operacion: str, fecha: str, index: int = 0, doc_counter: Dict = None) -> str:
        """
        Formatea la clave de documento según configuración con secuencia única.
        
        Args:
            operacion: Tipo de operación
            fecha: Fecha en formato DD/MM/YYYY
            index: Índice del registro
            doc_counter: Contador de documentos por tipo
            
        Returns:
            String formateado (ej: "CB-23022026-001")
        """
        config = self.get_operation_config(operacion)
        
        prefix = 'DOC'  # Default
        if config:
            prefix = config.get('clave_prefix', 'DOC').replace('-', '')
        
        # Limpiar fecha
        fecha_clean = fecha.replace('/', '').replace('-', '')
        
        # Generar secuencia única
        if doc_counter is not None:
            if prefix not in doc_counter:
                doc_counter[prefix] = 0
            doc_counter[prefix] += 1
            unique_seq = f"{doc_counter[prefix]:03d}"
        else:
            # Fallback: usar timestamp + índice
            import time
            timestamp = int(time.time()) % 10000
            unique_seq = f"{timestamp:04d}-{index+1:02d}"
        
        return f"{prefix}-{fecha_clean}-{unique_seq}"


# Función de conveniencia
def load_config_from_excel(file_path: str) -> ExcelConfigLoader:
    """Carga configuración desde archivo Excel."""
    loader = ExcelConfigLoader(file_path)
    loader.load_config()
    return loader
