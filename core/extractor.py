"""
Modulo Extractor: Lee y extrae datos de archivos Excel de estados de cuenta.
Soporta multiples bancos: BBVA, Banorte, Banregio
"""
import pandas as pd
from pathlib import Path
from typing import List, Dict, Optional
from datetime import datetime
import logging

logger = logging.getLogger(__name__)


class BankStatementExtractor:
    """
    Extrae movimientos de comisiones e IVA de estados de cuenta bancarios.
    Soporta BBVA, Banorte y Banregio.
    """
    
    def __init__(self, file_path: str, bank_name: str = None, strict_mode: bool = True):
        """
        Inicializa el extractor.
        
        Args:
            file_path: Ruta al archivo Excel del estado de cuenta
            bank_name: Nombre del banco (BBVA, BANORTE, BANREGIO). Si es None, se detecta automáticamente.
            strict_mode: True = Solo conceptos del diccionario, False = Usar keywords automáticas
        """
        self.file_path = Path(file_path)
        self.df = None
        # Prioridad: 1) Parámetro explícito, 2) Detección por nombre de archivo, 3) Default BBVA
        self.bank_name = bank_name.upper() if bank_name else self._detect_bank()
        self.strict_mode = strict_mode
        self.column_mapping = {}  # Mapeo de columnas detectado
        
    def _detect_bank(self) -> str:
        """
        Detecta el banco basado en el nombre del archivo.
        
        Returns:
            Codigo del banco (BBVA, BANORTE, BANREGIO, etc.)
        """
        filename = self.file_path.name.upper()
        if "BBVA" in filename or "BANCOMER" in filename:
            return "BBVA"
        elif "BANORTE" in filename:
            return "BANORTE"
        elif "BANREGIO" in filename:
            return "BANREGIO"
        else:
            logger.warning(f"No se pudo detectar el banco en: {filename}. Usando BBVA por defecto.")
            return "BBVA"
    
    def read_excel(self, sheet_name: str = "Edo.Cuenta", header_row: int = None) -> pd.DataFrame:
        """
        Lee el archivo Excel detectando automaticamente la fila de headers.
        
        Args:
            sheet_name: Nombre de la hoja
            header_row: Fila que contiene los headers (0-indexed). Si es None, auto-detecta.
        
        Returns:
            DataFrame con los datos
        """
        try:
            # Primero leer sin headers para detectar la estructura
            df_raw = pd.read_excel(self.file_path, sheet_name=sheet_name, header=None)
            
            logger.info(f"Excel leido: {len(df_raw)} filas x {len(df_raw.columns)} columnas")
            
            # Buscar la fila que contiene los headers
            if header_row is None:
                header_row = self._detect_header_row(df_raw)
                logger.info(f"Fila de headers detectada: {header_row}")
            
            # Leer nuevamente con el header correcto
            self.df = pd.read_excel(
                self.file_path,
                sheet_name=sheet_name,
                header=header_row
            )
            
            logger.info(f"Excel procesado: {len(self.df)} filas")
            logger.info(f"Columnas detectadas: {list(self.df.columns)}")
            
            # Detectar mapeo de columnas segun el banco
            self._detect_column_mapping()
            
            return self.df
            
        except Exception as e:
            logger.error(f"Error leyendo Excel: {e}")
            raise
    
    def _detect_header_row(self, df_raw: pd.DataFrame) -> int:
        """
        Detecta la fila que contiene los headers buscando palabras clave.
        
        Args:
            df_raw: DataFrame leido sin headers
            
        Returns:
            Indice de la fila de headers
        """
        from config.bank_mappings import get_bank_columns
        
        # Obtener posibles nombres de columnas para este banco
        bank_columns = get_bank_columns(self.bank_name)
        possible_headers = []
        for cols in bank_columns.values():
            possible_headers.extend([c.upper() for c in cols])
        
        # Buscar en las primeras 15 filas
        for i in range(min(15, len(df_raw))):
            row_values = []
            for val in df_raw.iloc[i]:
                if pd.isna(val):
                    row_values.append('')
                else:
                    row_values.append(str(val).strip().upper())
            
            # Contar cuantas palabras clave coinciden
            matches = sum(1 for header in possible_headers if any(header in val for val in row_values))
            
            # Si encontramos al menos 2 coincidencias, es probable que sea el header
            if matches >= 2:
                logger.info(f"Header encontrado en fila {i}: {row_values}")
                return i
            
            # Fallback: buscar columnas tipicas
            if any('CONCEPTO' in val or 'DESCRIP' in val for val in row_values):
                logger.info(f"Header encontrado en fila {i} (por CONCEPTO/DESCRIPCION): {row_values}")
                return i
            if any('FECHA' in val for val in row_values) and any('CARGO' in val or 'RETIRO' in val or 'DEPOSITO' in val for val in row_values):
                logger.info(f"Header encontrado en fila {i} (por FECHA y CARGO/RETIRO): {row_values}")
                return i
        
        # Si no se encuentra, usar fila 1 (segunda fila) por defecto
        logger.warning("No se detecto header, usando fila 1 por defecto")
        return 1
    
    def _detect_column_mapping(self):
        """
        Detecta el mapeo de columnas segun el banco.
        Crea un diccionario que mapea nombres estandar a nombres reales del Excel.
        """
        from config.bank_mappings import get_bank_columns
        
        bank_columns = get_bank_columns(self.bank_name)
        df_columns = [str(col).strip().upper() for col in self.df.columns]
        
        self.column_mapping = {}
        
        for standard_name, possible_names in bank_columns.items():
            for col_idx, col_name in enumerate(df_columns):
                # Limpiar nombre de columna (quitar acentos)
                col_clean = col_name.replace('Ó', 'O').replace('Í', 'I').replace('Á', 'A').replace('É', 'E').replace('Ú', 'U')
                
                for possible in possible_names:
                    possible_clean = possible.upper().replace('Ó', 'O').replace('Í', 'I').replace('Á', 'A').replace('É', 'E').replace('Ú', 'U')
                    
                    if possible_clean in col_clean or col_clean in possible_clean:
                        # Guardar el nombre original de la columna
                        original_col = self.df.columns[col_idx]
                        self.column_mapping[standard_name] = original_col
                        logger.info(f"Columna mapeada: {standard_name} -> {original_col}")
                        break
        
        # Verificar que tenemos las columnas esenciales
        essential = ['fecha', 'concepto', 'cargo']
        missing = [col for col in essential if col not in self.column_mapping]
        
        if missing:
            logger.warning(f"Columnas no encontradas: {missing}")
            logger.warning(f"Columnas disponibles: {list(self.df.columns)}")
    
    def extract_commissions_and_iva(self) -> List[Dict]:
        """
        Extrae solo los movimientos de comisiones e IVA.
        
        Returns:
            Lista de diccionarios con los movimientos filtrados
        """
        if self.df is None:
            raise ValueError("Debe llamar a read_excel primero")
        
        # Verificar que tenemos el mapeo de columnas
        if not self.column_mapping:
            self._detect_column_mapping()
        
        # Obtener nombre real de la columna de concepto
        concepto_col = self.column_mapping.get('concepto')
        if not concepto_col:
            raise KeyError(f"No se encontro columna de concepto. Mapeo: {self.column_mapping}")
        
        logger.info(f"Columna de concepto: {concepto_col}")
        
        # Filtrar solo comisiones e IVA
        from config.bank_mappings import should_process
        
        # Convertir conceptos a string y aplicar filtro (pasando el banco y modo estricto)
        conceptos_str = self.df[concepto_col].astype(str)
        mask = conceptos_str.apply(lambda x: should_process(x, self.bank_name, self.strict_mode))
        filtered_df = self.df[mask].copy()
        
        logger.info(f"Movimientos filtrados: {len(filtered_df)} de {len(self.df)}")
        
        # Convertir a lista de diccionarios
        records = []
        for _, row in filtered_df.iterrows():
            record = self._row_to_record(row)
            if record:
                records.append(record)
        
        return records
    
    def _row_to_record(self, row) -> Optional[Dict]:
        """
        Convierte una fila del DataFrame a un diccionario estandarizado.
        
        Args:
            row: Fila del DataFrame
            
        Returns:
            Diccionario con los datos normalizados o None si hay error
        """
        try:
            # Obtener valores usando el mapeo de columnas
            fecha_col = self.column_mapping.get('fecha')
            concepto_col = self.column_mapping.get('concepto')
            referencia_col = self.column_mapping.get('referencia')
            cargo_col = self.column_mapping.get('cargo')
            abono_col = self.column_mapping.get('abono')
            
            fecha = row.get(fecha_col) if fecha_col else None
            concepto = str(row.get(concepto_col, '')).strip() if concepto_col else ''
            referencia = str(row.get(referencia_col, '')).strip() if referencia_col else ''
            
            # Parsear montos
            cargo = self._parse_amount(row.get(cargo_col)) if cargo_col else 0.0
            abono = self._parse_amount(row.get(abono_col)) if abono_col else 0.0
            
            # Para Banorte: los cargos estan en la columna RETIROS (positivos)
            # Para otros bancos: los cargos pueden ser negativos
            if self.bank_name == "BANORTE":
                # En Banorte, RETIROS ya son positivos para comisiones
                pass
            
            return {
                'fecha': self._parse_date(fecha),
                'concepto': concepto,
                'referencia': referencia,
                'cargo': cargo,
                'abono': abono,
                'banco': self.bank_name,
                'fila_excel': int(row.name) + 2  # +2 por header y 0-index
            }
            
        except Exception as e:
            logger.error(f"Error procesando fila: {e}")
            return None
    
    def _parse_date(self, date_value) -> str:
        """Parsea la fecha al formato DD/MM/YYYY."""
        if pd.isna(date_value):
            return ""
        
        # Si es número (serial de Excel), convertir a datetime
        if isinstance(date_value, (int, float)):
            try:
                # Excel cuenta días desde 1899-12-30 (con un ajuste por el año bisiesto 1900)
                from datetime import timedelta
                excel_epoch = datetime(1899, 12, 30)
                dt = excel_epoch + timedelta(days=int(date_value))
                return dt.strftime("%d/%m/%Y")
            except:
                return str(date_value)
        
        if isinstance(date_value, datetime):
            return date_value.strftime("%d/%m/%Y")
        elif isinstance(date_value, str):
            # Intentar varios formatos
            formats = ["%d/%m/%Y", "%d-%m-%Y", "%Y/%m/%d", "%Y-%m-%d", "%m/%d/%Y"]
            for fmt in formats:
                try:
                    dt = datetime.strptime(date_value.strip(), fmt)
                    return dt.strftime("%d/%m/%Y")
                except:
                    continue
            return date_value
        return str(date_value)
    
    def _parse_amount(self, amount) -> float:
        """Parsea el monto a float, manejando formatos de diferentes bancos."""
        if pd.isna(amount):
            return 0.0
        
        if isinstance(amount, (int, float)):
            return float(amount)
        
        if isinstance(amount, str):
            # Limpiar formato: quitar $, comas, espacios
            cleaned = amount.replace('$', '').replace(',', '').replace(' ', '').strip()
            try:
                return float(cleaned)
            except:
                return 0.0
        
        return 0.0
    
    def get_summary(self) -> Dict:
        """Obtiene un resumen de los datos extraidos."""
        if self.df is None:
            return {}
        
        # Obtener columnas mapeadas
        cargo_col = self.column_mapping.get('cargo')
        abono_col = self.column_mapping.get('abono')
        
        total_cargos = 0
        total_abonos = 0
        
        if cargo_col and cargo_col in self.df.columns:
            total_cargos = self.df[cargo_col].apply(self._parse_amount).sum()
        
        if abono_col and abono_col in self.df.columns:
            total_abonos = self.df[abono_col].apply(self._parse_amount).sum()
        
        return {
            'banco': self.bank_name,
            'total_registros': len(self.df),
            'total_cargos': total_cargos,
            'total_abonos': total_abonos,
            'archivo': self.file_path.name,
            'columnas_mapeadas': self.column_mapping
        }


def extract_from_file(file_path: str) -> List[Dict]:
    """
    Funcion de conveniencia para extraer datos de un archivo.
    
    Args:
        file_path: Ruta al archivo Excel
    
    Returns:
        Lista de movimientos de comisiones e IVA
    """
    extractor = BankStatementExtractor(file_path)
    extractor.read_excel()
    return extractor.extract_commissions_and_iva()


def detect_bank_from_file(file_path: str) -> str:
    """
    Detecta el banco a partir del nombre del archivo.
    
    Args:
        file_path: Ruta al archivo Excel
        
    Returns:
        Codigo del banco (BBVA, BANORTE, BANREGIO)
    """
    filename = Path(file_path).name.upper()
    if "BBVA" in filename or "BANCOMER" in filename:
        return "BBVA"
    elif "BANORTE" in filename:
        return "BANORTE"
    elif "BANREGIO" in filename:
        return "BANREGIO"
    return "BBVA"  # Default
