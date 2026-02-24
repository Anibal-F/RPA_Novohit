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
        
    def transform_record(self, record: Dict) -> Optional[Dict]:
        """
        Transforma un registro bancario a formato Novohit.
        
        Args:
            record: Diccionario con datos del banco
            
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
        
        # Determinar tipo de operación para nomenclatura
        operacion_nombre = self._get_operacion_nombre(mapping['id_tp_operation'])
        
        # Generar observaciones y clave según configuración
        if self.config_loader:
            notes = self.config_loader.format_observaciones(operacion_nombre, fecha)
            no_document = self.config_loader.format_clave_documento(operacion_nombre, fecha)
        else:
            # Fallback a formato anterior
            notes = f"{mapping['descripcion']} - Ref: {record.get('referencia', '')}"
            no_document = self._generate_document_number(record)
        
        # Construir registro para Novohit
        novohit_record = {
            # Campos del formulario
            'id_bnk_account': self.account_id,
            'id_tp_operation': mapping['id_tp_operation'],
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
        
        logger.info(f"Transformado: {notes[:50]} - ${monto:.2f}")
        
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
        
        for record in records:
            try:
                novohit_record = self.transform_record(record)
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
    
    def _generate_document_number(self, record: Dict) -> str:
        """
        Genera un número de documento único para el registro.
        
        Formato: [BANCO]-[FECHA]-[SECUENCIA]
        """
        fecha = record.get('fecha', datetime.now().strftime("%d%m%Y"))
        fecha_clean = fecha.replace("/", "")
        banco = record.get('banco', 'BNK')[:3]
        referencia = str(record.get('referencia', ''))[-4:]  # Últimos 4 dígitos
        
        return f"{banco}-{fecha_clean}-{referencia}"
    
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
