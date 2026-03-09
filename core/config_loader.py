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
            
            # Leer celdas P3 y P4 para credenciales de Novohit
            self._load_credentials()
            
            # Cargar mapeo de cuentas de depósito por unidad de negocio (columnas K, L, M)
            self._load_cuentas_deposito_por_unidad()
            
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
            naturaleza_col = self._find_column(df, ['NATURALEZA', 'NATURALEZA (DEBITO/CREDITO)', 'DEBITO/CREDITO'])
            
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
                    naturaleza = str(row.get(naturaleza_col, '')).strip().lower() if naturaleza_col else ''
                    
                    self.config[operacion] = {
                        'observaciones_template': observaciones_template,
                        'clave_prefix': clave_prefix,
                        'cuenta_contable': cuenta_contable,
                        'naturaleza': naturaleza
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
    
    def _load_credentials(self):
        """Lee usuario y contraseña desde celdas P3 y P4 de la hoja Configuración."""
        try:
            # Leer la hoja sin header para obtener las celdas
            df_raw = pd.read_excel(self.file_path, sheet_name='Configuración', header=None)
            
            # La columna P es la 15 (A=0, B=1, ..., P=15)
            # P3 es fila 2 (0-indexed), columna 15
            # P4 es fila 3 (0-indexed), columna 15
            if len(df_raw) > 2 and len(df_raw.columns) > 15:
                # Leer usuario de P3
                usuario_valor = df_raw.iloc[2, 15]  # P3 = fila 2, columna 15
                usuario_str = str(usuario_valor).strip()
                
                if usuario_str and usuario_str.lower() != 'nan' and usuario_str != '':
                    self.novohit_username = usuario_str
                    logger.info(f"Usuario Novohit configurado (P3): {self.novohit_username}")
                else:
                    self.novohit_username = None
                    logger.info("Celda P3 vacía, se usarán credenciales por defecto")
            else:
                self.novohit_username = None
                logger.info("No se pudo leer celda P3, se usarán credenciales por defecto")
            
            if len(df_raw) > 3 and len(df_raw.columns) > 15:
                # Leer contraseña de P4
                password_valor = df_raw.iloc[3, 15]  # P4 = fila 3, columna 15
                password_str = str(password_valor).strip()
                
                if password_str and password_str.lower() != 'nan' and password_str != '':
                    self.novohit_password = password_str
                    logger.info(f"Contraseña Novohit configurada (P4): ****")
                else:
                    self.novohit_password = None
                    logger.info("Celda P4 vacía, se usarán credenciales por defecto")
            else:
                self.novohit_password = None
                logger.info("No se pudo leer celda P4, se usarán credenciales por defecto")
                
        except Exception as e:
            logger.warning(f"Error leyendo credenciales de P3/P4: {e}")
            self.novohit_username = None
            self.novohit_password = None
    
    def get_credentials(self) -> tuple:
        """
        Obtiene usuario y contraseña de Novohit desde Excel.
        
        Returns:
            Tupla (username, password) o (None, None) si no están configurados
        """
        return (getattr(self, 'novohit_username', None), 
                getattr(self, 'novohit_password', None))
    
    def _load_cuentas_deposito_por_unidad(self):
        """
        Lee el mapeo de cuentas de depósito por unidad de negocio.
        Busca columnas por nombre: ID, Unidad de Negocio, Cuenta Depósitos
        """
        self.cuentas_deposito_por_unidad = {}
        try:
            # Leer la hoja con header para poder buscar por nombre de columna
            df = pd.read_excel(self.file_path, sheet_name='Configuración')
            
            logger.info(f"[DEBUG] Columnas encontradas en Configuración: {list(df.columns)}")
            
            # Buscar columnas por nombre - buscar en TODAS las columnas del DataFrame
            logger.info(f"[DEBUG] Buscando columnas de depósito...")
            
            # Buscar columna ID (puede haber dos: una para operaciones, otra para unidades)
            # La segunda columna ID (la de unidades) suele estar después de "Cuentas" o "Bancos"
            id_cols = [c for c in df.columns if 'ID' in str(c).upper()]
            logger.info(f"[DEBUG] Columnas ID encontradas: {id_cols}")
            
            # Buscar columna de cuenta de depósitos
            cuenta_col = None
            for c in df.columns:
                col_upper = str(c).upper()
                if 'CUENTA' in col_upper and ('DEPOSITO' in col_upper or 'DEPÓSITO' in col_upper):
                    cuenta_col = c
                    break
            
            # Si no encontramos la específica, buscar "Cuenta Depósitos" o similar
            if not cuenta_col:
                cuenta_col = self._find_column(df, ['CUENTA DEPOSITOS', 'CUENTA DEPÓSITOS', 'CUENTAS DEPOSITO'])
            
            # Buscar columna ID que esté cerca de la cuenta de depósitos
            id_col = None
            if cuenta_col:
                # Encontrar el índice de la columna de cuenta
                cuenta_idx = list(df.columns).index(cuenta_col)
                # Buscar columna ID a la izquierda (normalmente 1-2 columnas antes)
                for i in range(cuenta_idx - 1, max(-1, cuenta_idx - 5), -1):
                    if i >= 0 and 'ID' in str(df.columns[i]).upper():
                        id_col = df.columns[i]
                        break
            
            # Si no encontramos, usar la segunda columna ID (la de unidades)
            if not id_col and len(id_cols) >= 2:
                id_col = id_cols[1]  # Segunda columna ID (la primera suele ser para operaciones)
            
            logger.info(f"[DEBUG] Columnas de depósito: ID={id_col}, Cuenta={cuenta_col}")
            
            if not id_col or not cuenta_col:
                logger.warning("[DEBUG] No se encontraron columnas de ID o Cuenta Depósitos")
                return
            
            # Procesar filas
            for idx, row in df.iterrows():
                id_val = row.get(id_col)
                cuenta_val = row.get(cuenta_col)
                
                # Convertir a string y limpiar
                id_str = str(id_val).strip() if pd.notna(id_val) else ''
                cuenta_str = str(cuenta_val).strip() if pd.notna(cuenta_val) else ''
                
                # Solo mostrar debug para filas que tienen datos
                if id_str and id_str.lower() != 'nan':
                    logger.info(f"[DEBUG] Fila {idx}: ID='{id_str}', Cuenta='{cuenta_str}'")
                
                # Validar que tenemos datos válidos
                if id_str and id_str.lower() != 'nan' and cuenta_str and cuenta_str.lower() != 'nan':
                    # Extraer solo el número de ID
                    import re
                    match = re.search(r'\d+', id_str)
                    if match:
                        unidad_id = match.group()
                        self.cuentas_deposito_por_unidad[unidad_id] = cuenta_str
                        logger.info(f"Cuenta depósito cargada: Unidad {unidad_id} -> {cuenta_str}")
            
            if self.cuentas_deposito_por_unidad:
                logger.info(f"Cuentas de depósito por unidad cargadas: {len(self.cuentas_deposito_por_unidad)}")
                for uid, cuenta in self.cuentas_deposito_por_unidad.items():
                    logger.info(f"  - Unidad {uid}: {cuenta}")
            else:
                logger.warning("No se encontraron cuentas de depósito por unidad de negocio")
                
        except Exception as e:
            logger.warning(f"Error cargando cuentas de depósito por unidad: {e}")
            import traceback
            logger.warning(traceback.format_exc())
            self.cuentas_deposito_por_unidad = {}
    
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
    
    def get_cuenta_deposito_for_unidad(self, unidad_id: str) -> Optional[str]:
        """
        Obtiene la cuenta contable de depósitos para una unidad de negocio específica.
        
        Args:
            unidad_id: ID de la unidad de negocio
            
        Returns:
            Cuenta contable de depósitos o None si no está configurada
        """
        if hasattr(self, 'cuentas_deposito_por_unidad') and unidad_id:
            return self.cuentas_deposito_por_unidad.get(str(unidad_id))
        return None
    
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
    
    def get_naturaleza_for_operation(self, operacion: str) -> Optional[str]:
        """
        Obtiene la naturaleza (debito/credito) para una operación específica.
        
        Args:
            operacion: Nombre de la operación (ej: 'COMISION', 'DEPOSITO')
            
        Returns:
            'debito', 'credito' o None si no está configurado
        """
        config = self.get_operation_config(operacion)
        if config and 'naturaleza' in config:
            naturaleza = config['naturaleza'].lower()
            # Normalizar valores
            if 'debit' in naturaleza or 'débit' in naturaleza:
                return 'debito'
            elif 'credit' in naturaleza or 'crédit' in naturaleza:
                return 'credito'
        return None
    
    def format_observaciones(self, operacion: str, fecha: str, tipo_transaccion: str = '') -> str:
        """
        Formatea las observaciones según el template de configuración.
        
        Args:
            operacion: Tipo de operación
            fecha: Fecha en formato DD/MM/YYYY
            tipo_transaccion: Tipo de transacción para depósitos (TDC, TDD, TDC AMEX)
            
        Returns:
            String formateado
        """
        config = self.get_operation_config(operacion)
        
        # Si es DEPOSITO y tenemos tipo de transacción, construir observaciones dinámicas
        if operacion.upper() == 'DEPOSITO' and tipo_transaccion:
            try:
                from datetime import datetime
                dt = datetime.strptime(fecha, '%d/%m/%Y')
                meses = {
                    1: 'ENERO', 2: 'FEBRERO', 3: 'MARZO', 4: 'ABRIL',
                    5: 'MAYO', 6: 'JUNIO', 7: 'JULIO', 8: 'AGOSTO',
                    9: 'SEPTIEMBRE', 10: 'OCTUBRE', 11: 'NOVIEMBRE', 12: 'DICIEMBRE'
                }
                fecha_formateada = f"{dt.day} DE {meses[dt.month]} DEL {dt.year}"
                
                # Usar template del Excel o default "VENTAS"
                template = config.get('observaciones_template', 'VENTAS') if config else 'VENTAS'
                return f"{template} {tipo_transaccion} DEL {fecha_formateada}"
            except Exception as e:
                logging.warning(f"Error formateando fecha para observaciones: {e}")
                template = config.get('observaciones_template', 'VENTAS') if config else 'VENTAS'
                return f"{template} {tipo_transaccion} DEL {fecha}"
        
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
