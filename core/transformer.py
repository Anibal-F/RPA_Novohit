"""
Módulo Transformer: Transforma y valida los datos para Novohit.
"""
from typing import List, Dict, Optional
from datetime import datetime
import logging

from config.bank_mappings import get_mapping_by_concept, get_account_id
from core.config_loader import ExcelConfigLoader

logger = logging.getLogger(__name__)


class NovohitTransformer:
    """
    Transforma los datos del banco al formato requerido por Novohit.
    """
    
    def __init__(self, bank_name: str = "BBVA", excel_file: str = None):
        self.bank_name = bank_name
        self._fallback_account_id = get_account_id(bank_name)
        self.config_loader = None
        
        # Cargar configuración desde Excel si se proporciona
        if excel_file:
            try:
                self.config_loader = ExcelConfigLoader(excel_file)
                self.config_loader.load_config()
                logger.info(f"Configuración cargada desde: {excel_file}")
            except Exception as e:
                logger.warning(f"No se pudo cargar configuración: {e}")
    
    @property
    def account_id(self) -> str:
        """
        Obtiene el ID de cuenta bancaria.
        Prioridad: 1) Configuración Excel (C1), 2) Mapeo por defecto
        """
        if self.config_loader:
            config_account = self.config_loader.get_bank_account_id()
            if config_account:
                return config_account
        return self._fallback_account_id
        
    def _extract_tipo_transaccion(self, concepto: str) -> str:
        """
        Extrae el tipo de transacción del concepto (TDC, TDD, TDC AMEX).
        
        Para Banregio: busca "TDC", "TDD", "TDC AMEX" en el concepto
        Para BBVA: busca "VENTAS DEBIDO" (TDD), "VENTAS CREDITO" (TDC), 
                   "VENTA INTL. AMEX" o "VENTA NAL. AMEX" (TDC AMEX)
        
        Args:
            concepto: Texto del concepto del estado de cuenta
            
        Returns:
            Tipo de transacción (TDC, TDD, TDC AMEX) o string vacío
        """
        concepto_upper = concepto.upper()
        
        if self.bank_name.upper() == 'BANREGIO':
            # Banregio: buscar TDC AMEX primero (más específico que solo TDC)
            if 'TDC AMEX' in concepto_upper or 'AMEX' in concepto_upper:
                return 'TDC AMEX'
            elif 'TDD' in concepto_upper:
                return 'TDD'
            elif 'TDC' in concepto_upper:
                return 'TDC'
                
        elif self.bank_name.upper() == 'BBVA':
            # BBVA: detectar según patrones específicos
            # VENTA INTL. AMEX o VENTA NAL. AMEX
            if 'AMEX' in concepto_upper:
                return 'TDC AMEX'
            # VENTAS DEBITO / VENTAS DEBIDO
            elif 'DEBITO' in concepto_upper or 'DEBIDO' in concepto_upper:
                return 'TDD'
            # VENTAS CREDITO / VENTAS TDC INTER
            elif 'CREDITO' in concepto_upper or 'TDC' in concepto_upper:
                return 'TDC'
        
        return ''
    
    def _get_tipo_transaccion_suffix(self, tipo_transaccion: str) -> str:
        """
        Obtiene el sufijo para el documento según el tipo de transacción.
        
        Args:
            tipo_transaccion: Tipo de transacción (TDC, TDD, TDC AMEX)
            
        Returns:
            Sufijo para el documento (DC, DD, DCA) o string vacío
        """
        suffix_map = {
            'TDC': 'DC',
            'TDD': 'DD',
            'TDC AMEX': 'DCA'
        }
        return suffix_map.get(tipo_transaccion, '')
        
    def transform_record(self, record: Dict, index: int = 0, doc_counter: Dict = None, type_date_counts: Dict = None) -> Optional[Dict]:
        """
        Transforma un registro bancario a formato Novohit.
        
        Args:
            record: Diccionario con datos del banco
            index: Índice del registro para generar documento único
            doc_counter: Contador de documentos por tipo (para seguimiento)
            type_date_counts: Conteo total de registros por tipo y fecha
            
        Returns:
            Diccionario con datos formateados para Novohit o None si no es válido
        """
        concepto = record.get('concepto', '')
        
        # Obtener mapeo del concepto
        mapping = get_mapping_by_concept(concepto, self.bank_name)
        
        if not mapping:
            logger.warning(f"No se encontró mapeo para: {concepto}")
            return None
        
        # Determinar monto (cargo o abono)
        cargo = record.get('cargo', 0) if record.get('cargo') else 0
        abono = record.get('abono', 0) if record.get('abono') else 0
        monto = cargo if cargo > 0 else abono
        
        if monto <= 0:
            logger.warning(f"Monto inválido para: {concepto} (cargo={cargo}, abono={abono})")
            return None
        
        # Obtener fecha
        fecha = record.get('fecha', datetime.now().strftime("%d/%m/%Y"))
        fecha_clean = fecha.replace('/', '')
        
        # Determinar tipo de operación para nomenclatura
        operacion_id = mapping['id_tp_operation']
        operacion_nombre = self._get_operacion_nombre(operacion_id)
        
        # Crear clave para el contador (tipo + fecha)
        counter_key = f"{operacion_id}_{fecha_clean}"
        
        # Incrementar contador para este tipo/fecha
        if doc_counter is None:
            doc_counter = {}
        if counter_key not in doc_counter:
            doc_counter[counter_key] = 0
        doc_counter[counter_key] += 1
        
        # Obtener el número secuencial actual y el total
        current_seq = doc_counter[counter_key]
        total_count = type_date_counts.get(counter_key, 1) if type_date_counts else 1
        
        # Extraer tipo de transacción para depósitos (TDC, TDD, TDC AMEX)
        # Detectar primero el tipo de transaccion basado en el concepto
        tipo_transaccion = self._extract_tipo_transaccion(concepto)
        categoria = mapping.get('categoria', '')
        
        # Si detectamos tipo_transaccion, es un deposito sin importar el mapeo
        es_deposito = (operacion_id == '6' or categoria == 'deposito' or tipo_transaccion != '')
        
        logger.info(f"  [DEBUG] Concepto: {concepto[:50]}, operacion_id: {operacion_id}, categoria: {categoria}, tipo_transaccion: {tipo_transaccion}, es_deposito: {es_deposito}")
        
        # Generar observaciones y clave según configuración
        if self.config_loader:
            # Para depósitos, pasar el tipo de transacción para observaciones dinámicas
            if es_deposito:
                notes = self.config_loader.format_observaciones(
                    operacion_nombre, fecha, tipo_transaccion=tipo_transaccion
                )
            else:
                notes = self.config_loader.format_observaciones(operacion_nombre, fecha)
            # Generar documento con sufijo secuencial (01, 02, etc.)
            # Para depósitos, pasar tipo_transaccion para generar clave dinámica
            if es_deposito:
                no_document = self._generate_sequential_document(
                    operacion_nombre, fecha, current_seq, total_count, tipo_transaccion
                )
            else:
                no_document = self._generate_sequential_document(
                    operacion_nombre, fecha, current_seq, total_count
                )
        else:
            # Fallback a formato anterior
            if es_deposito:
                # Observaciones dinámicas para depósitos (Banregio y BBVA)
                if tipo_transaccion:
                    notes = f"VENTAS {tipo_transaccion} DEL {fecha}"
                else:
                    notes = f"Deposito Bancario del dia: {fecha}"
            else:
                notes = f"{mapping['descripcion']} - Ref: {record.get('referencia', '')}"
            no_document = self._generate_document_number(record, index, doc_counter)
        
        # Construir registro para Novohit
        novohit_record = {
            # Campos del formulario
            'id_bnk_account': self.account_id,
            'id_tp_operation': operacion_id,
            'dt_operation': fecha,
            'no_document': no_document,
            'mn_operation': f"{monto:.2f}",
            'notes': notes,
            
            # Metadatos para tracking
            'banco': record.get('banco', ''),
            'concepto_original': concepto,
            'referencia': record.get('referencia', ''),
            'monto': monto,
            'categoria': mapping['categoria'],
            'fila_excel': record.get('fila_excel', 0)
        }
        
        logger.info(f"Transformado: {notes[:50]} - Doc: {no_document} (${monto:.2f}) [{current_seq}/{total_count}]")
        
        return novohit_record
    
    def transform_records(self, records: List[Dict]) -> List[Dict]:
        """
        Transforma una lista de registros.
        
        Args:
            records: Lista de registros bancarios
            
        Returns:
            Lista de registros transformados para Novohit
        """
        transformed = []
        
        # PASO 1: Contar registros por tipo de operación y fecha
        # Esto nos permite saber cuántos documentos de cada tipo tenemos
        type_date_counts = {}
        for record in records:
            concepto = record.get('concepto', '')
            fecha = record.get('fecha', '')
            
            # Obtener mapeo para determinar el tipo de operación
            mapping = get_mapping_by_concept(concepto, self.bank_name)
            if not mapping:
                continue
            
            # Crear clave única por tipo de operación y fecha
            operacion_id = mapping['id_tp_operation']
            fecha_clean = fecha.replace('/', '')
            key = f"{operacion_id}_{fecha_clean}"
            
            if key not in type_date_counts:
                type_date_counts[key] = 0
            type_date_counts[key] += 1
        
        # Log del conteo
        logger.info("Conteo de registros por tipo y fecha:")
        for key, count in type_date_counts.items():
            logger.info(f"  {key}: {count} registros")
        
        # PASO 2: Transformar registros con contador secuencial por tipo/fecha
        doc_counter = {}  # Contador por clave (tipo + fecha)
        
        for idx, record in enumerate(records):
            try:
                novohit_record = self.transform_record(record, idx, doc_counter, type_date_counts)
                if novohit_record:
                    transformed.append(novohit_record)
            except Exception as e:
                logger.error(f"Error transformando registro: {e}")
                continue
        
        logger.info(f"Registros transformados: {len(transformed)} de {len(records)}")
        return transformed
    
    def _get_operacion_nombre(self, id_tp_operation: str) -> str:
        """
        Obtiene el nombre de la operación según su ID.
        
        Args:
            id_tp_operation: ID del tipo de operación
            
        Returns:
            Nombre legible de la operación
        """
        operaciones = {
            '1': 'CHEQUES',
            '6': 'DEPOSITO',
            '7': 'COMISION',
            '8': 'IVA POR COMISIONES',
            '11': 'TRANSFER. SALIDA',
            '14': 'CARGO A CTA. CHEQUES',
            '15': 'INTERESES',
            '17': 'DEPTO COBRANZA',
            '20': 'TRANSF. ELECT.PAGO PROV.',
            '22': 'DEPTO OPERACION',
            '24': 'DEPTO x RESERVA',
        }
        return operaciones.get(id_tp_operation, 'OPERACION')
    
    def _generate_document_number(self, record: Dict, index: int = 0, doc_counter: Dict = None) -> str:
        """
        Genera un número de documento único para el registro (fallback).
        
        Formato: [PREFIX]-[FECHA]-[SECUENCIA_UNICA]
        """
        fecha = record.get('fecha', datetime.now().strftime("%d%m%Y"))
        fecha_clean = fecha.replace("/", "")
        
        # Determinar prefijo según tipo de operación
        concepto = record.get('concepto', '').lower()
        if 'iva' in concepto:
            prefix = "IVA"
        elif 'comision' in concepto:
            prefix = "COM"
        else:
            prefix = record.get('banco', 'BNK')[:3].upper()
        
        # Generar secuencia única usando timestamp + índice
        import time
        timestamp = int(time.time()) % 10000  # Últimos 4 dígitos del timestamp
        unique_seq = f"{timestamp:04d}-{index+1:02d}"
        
        # Alternativa: usar contador por tipo si está disponible
        if doc_counter is not None:
            if prefix not in doc_counter:
                doc_counter[prefix] = 0
            doc_counter[prefix] += 1
            unique_seq = f"{doc_counter[prefix]:03d}"
        
        return f"{prefix}-{fecha_clean}-{unique_seq}"
    
    def _generate_sequential_document(self, operacion_nombre: str, fecha: str, current_seq: int, 
                                        total_count: int, tipo_transaccion: str = '') -> str:
        """
        Genera un número de documento con sufijo secuencial.
        
        Formato: [PREFIX]-[FECHA]-[SECUENCIA]
        Ejemplo: CB-23022026-01, CB-23022026-02, ..., CB-23022026-15
        
        Para DEPOSITOS con tipo de transacción:
        Formato: [PREFIX][TIPO_SUFIJO]-[FECHA]-[SECUENCIA]
        Ejemplo: TDC-05032026-01, TDD-05032026-01, TDCA-05032026-01
        
        Args:
            operacion_nombre: Nombre de la operación (ej: 'COMISION')
            fecha: Fecha en formato DD/MM/YYYY
            current_seq: Número secuencial actual (1-based)
            total_count: Total de registros de este tipo/fecha
            tipo_transaccion: Tipo de transacción para depósitos (TDC, TDD, TDC AMEX)
            
        Returns:
            String con el número de documento formateado
        """
        # Obtener configuración para el prefijo
        config = None
        if self.config_loader:
            config = self.config_loader.get_operation_config(operacion_nombre)
        
        # Determinar prefijo
        if config and config.get('clave_prefix'):
            prefix = config['clave_prefix'].replace('-', '')
        else:
            # Fallback: usar prefijo basado en el nombre de operación
            operacion_upper = operacion_nombre.upper()
            if 'IVA' in operacion_upper:
                prefix = "IVA COM"
            elif 'COMISION' in operacion_upper:
                prefix = "CB"
            else:
                prefix = "DOC"
        
        # Si tenemos tipo de transacción (TDC/TDD/TDCA), agregar sufijo al prefijo
        logger.info(f"  [DEBUG] Generando documento: operacion={operacion_nombre}, prefix={prefix}, tipo_transaccion={tipo_transaccion}")
        if tipo_transaccion:
            tipo_suffix = self._get_tipo_transaccion_suffix(tipo_transaccion)
            logger.info(f"  [DEBUG] Sufijo generado: {tipo_suffix}")
            if tipo_suffix:
                prefix = f"{prefix}{tipo_suffix}"
        
        # Limpiar fecha
        fecha_clean = fecha.replace('/', '').replace('-', '')
        
        # Determinar ancho del sufijo según el total (2 dígitos para <=99, 3 para más)
        width = 2 if total_count <= 99 else 3
        seq_str = f"{current_seq:0{width}d}"
        
        return f"{prefix}-{fecha_clean}-{seq_str}"
    
    def validate_record(self, record: Dict) -> bool:
        """
        Valida que un registro tenga todos los campos requeridos.
        
        Args:
            record: Registro a validar
            
        Returns:
            True si es válido, False en caso contrario
        """
        required_fields = ['id_bnk_account', 'id_tp_operation', 'dt_operation', 
                          'no_document', 'mn_operation']
        
        for field in required_fields:
            if not record.get(field):
                logger.warning(f"Campo requerido faltante: {field}")
                return False
        
        # Validar que el monto sea numérico
        monto_val = record.get('mn_operation') or record.get('mm_operation')
        try:
            float(monto_val or 0)
        except:
            logger.warning(f"Monto no numérico: {monto_val}")
            return False
        
        return True
    
    def get_processing_summary(self, records: List[Dict]) -> Dict:
        """
        Genera un resumen del procesamiento.
        """
        total_registros = len(records)
        
        # Contar por categoría
        comisiones = [r for r in records if r.get('categoria') == 'comision']
        ivas = [r for r in records if r.get('categoria') == 'iva']
        
        total_comisiones = sum(float(r.get('monto', 0)) for r in comisiones)
        total_iva = sum(float(r.get('monto', 0)) for r in ivas)
        
        return {
            'total_registros': total_registros,
            'total_comisiones': len(comisiones),
            'total_iva': len(ivas),
            'monto_comisiones': total_comisiones,
            'monto_iva': total_iva,
            'monto_total': total_comisiones + total_iva,
            'banco': self.bank_name
        }
