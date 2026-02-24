"""
Módulo Extractor: Lee y extrae datos de archivos Excel de estados de cuenta.
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
    """
    
    def __init__(self, file_path: str):
        """
        Inicializa el extractor.
        
        Args:
            file_path: Ruta al archivo Excel del estado de cuenta
        """
        self.file_path = Path(file_path)
        self.df = None
        self.bank_name = self._detect_bank()
        
    def _detect_bank(self) -> str:
        """
        Detecta el banco basado en el nombre del archivo.
        
        Returns:
            Código del banco (BBVA, BANORTE, BANREGIO, etc.)
        """
        filename = self.file_path.name.upper()
        if "BBVA" in filename or "BANCOMER" in filename:
            return "BBVA"
        elif "BANORTE" in filename:
            return "BANORTE"
        elif "BANREGIO" in filename:
            return "BANREGIO"
        else:
            logger.warning(f"No se pudo detectar el banco en: {filename}")
            return "UNKNOWN"
    
    def read_excel(self, sheet_name: str = "Edo.Cuenta", header_row: int = None) -> pd.DataFrame:
        """
        Lee el archivo Excel detectando automáticamente la fila de headers.
        
        Args:
            sheet_name: Nombre de la hoja
            header_row: Fila que contiene los headers (0-indexed). Si es None, auto-detecta.
        
        Returns:
            DataFrame con los datos
        """
        try:
            # Primero leer sin headers para detectar la estructura
            df_raw = pd.read_excel(self.file_path, sheet_name=sheet_name, header=None)
            
            logger.info(f"Excel leído: {len(df_raw)} filas x {len(df_raw.columns)} columnas")
            
            # Buscar la fila que contiene "Concepto" o "CONCEPTO"
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
            
            return self.df
            
        except Exception as e:
            logger.error(f"Error leyendo Excel: {e}")
            raise
    
    def _detect_header_row(self, df_raw: pd.DataFrame) -> int:
        """
        Detecta la fila que contiene los headers buscando la palabra 'Concepto'.
        
        Args:
            df_raw: DataFrame leído sin headers
            
        Returns:
            Índice de la fila de headers
        """
        # Buscar en las primeras 10 filas
        for i in range(min(10, len(df_raw))):
            # Convertir toda la fila a string y limpiar
            row_values = []
            for val in df_raw.iloc[i]:
                if pd.isna(val):
                    row_values.append('')
                else:
                    row_values.append(str(val).strip().upper())
            
            # Buscar columnas típicas de estados de cuenta
            if any('CONCEPTO' in val for val in row_values):
                logger.info(f"Header encontrado en fila {i}: {row_values}")
                return i
            if any('FECHA' in val and 'OPER' in val for val in row_values):
                logger.info(f"Header encontrado en fila {i}: {row_values}")
                return i
        
        # Si no se encuentra, usar fila 1 (segunda fila) por defecto
        logger.warning("No se detectó header, usando fila 1 por defecto")
        return 1
    
    def extract_commissions_and_iva(self) -> List[Dict]:
        """
        Extrae solo los movimientos de comisiones e IVA.
        
        Returns:
            Lista de diccionarios con los movimientos filtrados
        """
        if self.df is None:
            raise ValueError("Debe llamar a read_excel primero")
        
        # Normalizar nombres de columnas (quitar espacios, mayúsculas, caracteres especiales)
        original_columns = list(self.df.columns)
        self.df.columns = [str(col).strip().upper().replace('Ó', 'O').replace('Í', 'I') 
                          for col in self.df.columns]
        
        logger.info(f"Columnas normalizadas: {list(self.df.columns)}")
        
        # Buscar la columna de concepto (puede tener variaciones de nombre)
        concepto_col = None
        for col in self.df.columns:
            if 'CONCEPTO' in col or 'DESCRIPCION' in col or 'DESCRIPCIÓN' in col:
                concepto_col = col
                break
        
        if not concepto_col:
            logger.error(f"No se encontró columna de concepto. Columnas disponibles: {list(self.df.columns)}")
            raise KeyError("No se encontró columna de concepto en el Excel")
        
        logger.info(f"Columna de concepto identificada: {concepto_col}")
        
        # Mapeo flexible de columnas
        column_mapping = {}
        
        for col in self.df.columns:
            col_normalized = col.upper().replace('Ó', 'O').replace('Í', 'I')
            
            if any(keyword in col_normalized for keyword in ['FECHA', 'OPERACION', 'OPERACIÓN']):
                if 'FECHA' in col_normalized:
                    column_mapping[col] = 'fecha'
            elif 'CONCEPTO' in col_normalized or 'DESCRIP' in col_normalized:
                column_mapping[col] = 'concepto'
            elif 'REFERENCIA' in col_normalized or 'REF' in col_normalized:
                column_mapping[col] = 'referencia'
            elif 'CARGO' in col_normalized:
                column_mapping[col] = 'cargo'
            elif 'ABONO' in col_normalized:
                column_mapping[col] = 'abono'
        
        logger.info(f"Mapeo de columnas: {column_mapping}")
        
        # Renombrar columnas
        self.df.rename(columns=column_mapping, inplace=True)
        
        # Filtrar solo comisiones e IVA
        from config.bank_mappings import should_process
        
        mask = self.df['concepto'].astype(str).apply(should_process)
        filtered_df = self.df[mask].copy()
        
        logger.info(f"Movimientos filtrados: {len(filtered_df)} de {len(self.df)}")
        
        # Convertir a lista de diccionarios
        records = []
        for _, row in filtered_df.iterrows():
            record = {
                'fecha': self._parse_date(row.get('fecha')),
                'concepto': str(row.get('concepto', '')).strip(),
                'referencia': str(row.get('referencia', '')).strip(),
                'cargo': self._parse_amount(row.get('cargo', 0)),
                'abono': self._parse_amount(row.get('abono', 0)),
                'banco': self.bank_name,
                'fila_excel': int(row.name) + 2  # +2 por header y 0-index
            }
            records.append(record)
        
        return records
    
    def _parse_date(self, date_value) -> str:
        """Parsea la fecha al formato DD/MM/YYYY."""
        if pd.isna(date_value):
            return ""
        
        if isinstance(date_value, datetime):
            return date_value.strftime("%d/%m/%Y")
        elif isinstance(date_value, str):
            # Intentar parsear string
            try:
                dt = datetime.strptime(date_value, "%d/%m/%Y")
                return dt.strftime("%d/%m/%Y")
            except:
                return date_value
        return str(date_value)
    
    def _parse_amount(self, amount) -> float:
        """Parsea el monto a float."""
        if pd.isna(amount):
            return 0.0
        try:
            return float(amount)
        except:
            return 0.0
    
    def get_summary(self) -> Dict:
        """Obtiene un resumen de los datos extraídos."""
        if self.df is None:
            return {}
        
        # Buscar columnas de cargo y abono de forma flexible
        cargo_col = None
        abono_col = None
        
        for col in self.df.columns:
            col_str = str(col).upper()
            if 'CARGO' in col_str:
                cargo_col = col
            elif 'ABONO' in col_str:
                abono_col = col
        
        total_cargos = self.df[cargo_col].sum() if cargo_col else 0
        total_abonos = self.df[abono_col].sum() if abono_col else 0
        
        return {
            'banco': self.bank_name,
            'total_registros': len(self.df),
            'total_cargos': total_cargos,
            'total_abonos': total_abonos,
            'archivo': self.file_path.name
        }


def extract_from_file(file_path: str) -> List[Dict]:
    """
    Función de conveniencia para extraer datos de un archivo.
    
    Args:
        file_path: Ruta al archivo Excel
    
    Returns:
        Lista de movimientos de comisiones e IVA
    """
    extractor = BankStatementExtractor(file_path)
    extractor.read_excel()
    return extractor.extract_commissions_and_iva()
