"""
RPA Novohit - Orquestador Principal

Este script coordina todo el flujo del RPA:
1. Extrae datos del Excel del estado de cuenta
2. Transforma los datos al formato de Novohit
3. Carga los datos en el sistema vía web

Uso:
    python main.py --file "data/input/estado_cuenta.xlsx" [--dry-run]
"""
import argparse
import sys
from pathlib import Path

# Agregar el directorio raíz al path para imports
sys.path.insert(0, str(Path(__file__).parent))

from config import settings
from core.extractor import BankStatementExtractor
from core.transformer import NovohitTransformer
from core.loader import NovohitLoader
from utils.helpers import setup_logging, generate_report


def main():
    """Función principal del RPA."""
    # Parsear argumentos
    parser = argparse.ArgumentParser(description='RPA Novohit - Contabilización Bancaria')
    parser.add_argument('--file', '-f', type=str, required=True,
                        help='Ruta al archivo Excel del estado de cuenta')
    parser.add_argument('--dry-run', '-d', action='store_true',
                        help='Ejecutar sin cargar en Novohit (solo extrae y transforma)')
    parser.add_argument('--headless', action='store_true',
                        help='Ejecutar sin abrir el navegador (modo headless)')
    parser.add_argument('--limit', '-l', type=int, default=None,
                        help='Limitar el número de registros a procesar')
    args = parser.parse_args()
    
    # Configurar logging
    setup_logging(settings.LOG_FILE)
    import logging
    logger = logging.getLogger(__name__)
    
    logger.info("=" * 60)
    logger.info("INICIANDO RPA NOVOHIT - CONTABILIZACIÓN BANCARIA")
    logger.info("=" * 60)
    
    # ===================================================================
    # FASE 1: EXTRACCIÓN
    # ===================================================================
    logger.info("\n📥 FASE 1: EXTRACCIÓN DE DATOS")
    logger.info("-" * 40)
    
    try:
        extractor = BankStatementExtractor(args.file)
        df = extractor.read_excel()
        
        # Obtener resumen inicial
        summary = extractor.get_summary()
        logger.info(f"Banco detectado: {summary['banco']}")
        logger.info(f"Total registros en archivo: {summary['total_registros']}")
        logger.info(f"Total cargos: ${summary['total_cargos']:,.2f}")
        logger.info(f"Total abonos: ${summary['total_abonos']:,.2f}")
        
        # Extraer comisiones e IVA
        records = extractor.extract_commissions_and_iva()
        logger.info(f"Registros de comisiones/IVA encontrados: {len(records)}")
        
        if not records:
            logger.warning("No se encontraron registros para procesar")
            return
            
    except Exception as e:
        logger.error(f"Error en fase de extracción: {e}")
        raise
    
    # ===================================================================
    # FASE 2: TRANSFORMACIÓN
    # ===================================================================
    logger.info("\n🔄 FASE 2: TRANSFORMACIÓN DE DATOS")
    logger.info("-" * 40)
    
    try:
        # Pasar el archivo Excel para cargar configuración
        transformer = NovohitTransformer(
            bank_name=extractor.bank_name,
            excel_file=args.file
        )
        novohit_records = transformer.transform_records(records)
        
        # Validar registros
        valid_records = [r for r in novohit_records if transformer.validate_record(r)]
        logger.info(f"Registros válidos para Novohit: {len(valid_records)}")
        
        # Resumen de transformación
        processing_summary = transformer.get_processing_summary(valid_records)
        logger.info(f"Comisiones: {processing_summary['total_comisiones']} registros, "
                   f"${processing_summary['monto_comisiones']:,.2f}")
        logger.info(f"IVA: {processing_summary['total_iva']} registros, "
                   f"${processing_summary['monto_iva']:,.2f}")
        logger.info(f"Monto total: ${processing_summary['monto_total']:,.2f}")
        
        # Aplicar límite si se especificó
        if args.limit and args.limit > 0:
            valid_records = valid_records[:args.limit]
            logger.info(f"Limitado a {args.limit} registros para procesamiento")
        
    except Exception as e:
        logger.error(f"Error en fase de transformación: {e}")
        raise
    
    # Si es dry-run, terminar aquí
    if args.dry_run:
        logger.info("\n🏁 MODO DRY-RUN: No se cargarán datos en Novohit")
        logger.info(f"Datos preparados (primeros 3 de {len(valid_records)} registros):")
        for i, record in enumerate(valid_records[:3], 1):
            monto = record.get('mn_operation') or record.get('mm_operation') or 'N/A'
            notes = record.get('notes', 'N/A')[:50]
            logger.info(f"  {i}. {notes} - ${monto}")
        return
    
    # ===================================================================
    # FASE 3: CARGA
    # ===================================================================
    logger.info("\n🚀 FASE 3: CARGA EN NOVOHIT")
    logger.info("-" * 40)
    
    try:
        logger.info(f"Iniciando carga de {len(valid_records)} registros...")
        
        with NovohitLoader(headless=args.headless) as loader:
            # Navegar a operaciones bancarias
            loader.navigate_to_bank_operations()
            
            # Verificar que tenemos registros para procesar
            if not valid_records:
                logger.error("No hay registros para procesar")
                results = {'total': 0, 'success': 0, 'failed': 0, 'errors': []}
            else:
                # Procesar registros
                results = loader.process_records(
                    valid_records,
                    delay=settings.DELAY_BETWEEN_OPERATIONS,
                    config_loader=transformer.config_loader if hasattr(transformer, 'config_loader') else None
                )
            
            # Agregar metadata a resultados
            results['summary'] = processing_summary
            results['input_file'] = args.file
            
            # Generar reporte
            report_files = generate_report(results, settings.DATA_OUTPUT_DIR)
            logger.info(f"\n📄 Reporte generado: {report_files[0]}")
            logger.info(f"📄 Resumen generado: {report_files[1]}")
            
            # Estadísticas finales
            logger.info("\n" + "=" * 60)
            logger.info("ESTADÍSTICAS FINALES")
            logger.info("=" * 60)
            logger.info(f"Total procesados: {results['total']}")
            if results['total'] > 0:
                logger.info(f"Exitosos: {results['success']} ({results['success']/results['total']*100:.1f}%)")
                logger.info(f"Fallidos: {results['failed']}")
            else:
                logger.info("Exitosos: 0 (0.0%)")
                logger.info("Fallidos: 0")
            
    except Exception as e:
        logger.error(f"Error en fase de carga: {e}")
        raise
    
    logger.info("\n✅ RPA COMPLETADO EXITOSAMENTE")
    logger.info("=" * 60)


if __name__ == "__main__":
    main()
