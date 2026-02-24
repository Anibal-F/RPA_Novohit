"""
Módulo para manejar el registro de asientos contables después de la operación bancaria.
Este es el segundo paso del flujo donde se registra la contabilización.
"""
import time
import logging
from typing import Dict, Optional

logger = logging.getLogger(__name__)


class AccountingEntryHandler:
    """
    Maneja el registro del asiento contable (segundo paso del flujo).
    """
    
    def __init__(self, frame, page):
        self.frame = frame
        self.page = page
        
    def fill_accounting_entry(self, record: Dict, config_loader=None) -> bool:
        """
        Llena el formulario de asiento contable después de guardar la operación bancaria.
        
        Args:
            record: Datos del registro
            config_loader: Cargador de configuración para obtener cuenta contable
            
        Returns:
            True si se completó exitosamente
        """
        try:
            logger.info("\n📊 PROCESANDO ASIENTO CONTABLE...")
            
            # Esperar a que aparezca el formulario de asiento contable
            time.sleep(2)
            
            # 1. Seleccionar Cuenta Contable
            cuenta_contable = self._get_cuenta_contable(record, config_loader)
            if cuenta_contable:
                self._select_cuenta_contable(cuenta_contable)
                logger.info(f"  ✓ Cuenta contable seleccionada: {cuenta_contable}")
            
            # 2. Llenar Monto (usar el mismo)
            monto = record.get('mn_operation') or record.get('mm_operation', '')
            if monto:
                self._fill_field('mn_entry', str(monto))
                logger.info(f"  ✓ Monto: {monto}")
            
            # 3. Tipo de Cambio (1.0000 por defecto)
            tc = record.get('tc_currency', '1.0000')
            self._fill_field('tc_currency', tc)
            logger.info(f"  ✓ Tipo Cambio: {tc}")
            
            # 4. Naturaleza - Débito (radio button)
            self._select_naturaleza('debit')
            logger.info("  ✓ Naturaleza: Débito")
            
            # 5. Concepto (mismo que el registro principal)
            concepto = record.get('notes', '')
            if concepto:
                self._fill_field('observations', concepto[:50])
                logger.info(f"  ✓ Concepto: {concepto[:50]}...")
            
            # 6. Clic en Agregar
            time.sleep(0.5)
            self._click_agregar_asiento()
            logger.info("  ✓ Asiento contable registrado")
            
            # Esperar a que se procese
            time.sleep(2)
            
            return True
            
        except Exception as e:
            logger.error(f"Error en asiento contable: {e}")
            return False
    
    def _get_cuenta_contable(self, record: Dict, config_loader) -> Optional[str]:
        """Obtiene la cuenta contable según el tipo de operación."""
        if not config_loader:
            return None
        
        # Obtener el nombre de la operación
        operacion_id = record.get('id_tp_operation')
        operacion_nombre = self._get_operacion_nombre(operacion_id)
        
        # Buscar en configuración
        config = config_loader.get_operation_config(operacion_nombre)
        if config and 'cuenta_contable' in config:
            return config['cuenta_contable']
        
        return None
    
    def _get_operacion_nombre(self, id_tp_operation: str) -> str:
        """Convierte ID de operación a nombre."""
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
        return operaciones.get(id_tp_operation, '')
    
    def _select_cuenta_contable(self, cuenta: str):
        """Selecciona la cuenta contable del dropdown usando el método estándar de ExtJS."""
        try:
            logger.info(f"  Seleccionando cuenta contable: {cuenta}")
            
            # Extraer el número de cuenta (ej: "11180001" de "IVA acreditable 16% - 11180001")
            cuenta_numero = cuenta.split('-')[-1].strip() if '-' in cuenta else cuenta
            search_term = 'iva' if 'iva' in cuenta.lower() else 'comision'
            
            # MÉTODO 1: Abrir dropdown y seleccionar opción (más confiable)
            logger.info(f"  Usando método dropdown para: {cuenta_numero}")
            
            # Hacer clic en el trigger para abrir el dropdown
            trigger_clicked = self.frame.evaluate("""() => {
                // Buscar el trigger por ID específico
                let trigger = document.querySelector('#ext-gen55');
                if (trigger) {
                    trigger.click();
                    return { success: true, method: 'ext-gen55' };
                }
                // Fallback: buscar por clase
                trigger = document.querySelector('.x-form-arrow-trigger');
                if (trigger) {
                    trigger.click();
                    return { success: true, method: 'arrow-trigger' };
                }
                return { success: false, error: 'Trigger no encontrado' };
            }""")
            
            logger.info(f"  Click en trigger: {trigger_clicked}")
            
            if trigger_clicked.get('success'):
                time.sleep(2)  # Esperar a que abra el dropdown
                
                # Seleccionar la opción
                result = self.frame.evaluate("""(params) => {
                    const items = document.querySelectorAll('.x-combo-list-item');
                    
                    // Buscar coincidencia exacta por número de cuenta
                    for (let item of items) {
                        const text = item.textContent || '';
                        if (text.includes(params.cuenta_numero)) {
                            item.scrollIntoView({ block: 'nearest' });
                            item.click();
                            return { success: true, selected: text, method: 'exact' };
                        }
                    }
                    
                    // Fallback: buscar por término parcial
                    for (let item of items) {
                        const text = item.textContent || '';
                        if (text.toLowerCase().includes(params.search_term)) {
                            item.scrollIntoView({ block: 'nearest' });
                            item.click();
                            return { success: true, selected: text, method: 'fallback' };
                        }
                    }
                    
                    return { success: false, items: items.length, searched: params.cuenta_numero };
                }""", {'cuenta_numero': cuenta_numero, 'search_term': search_term})
                
                logger.info(f"  Resultado selección dropdown: {result}")
                
                if result.get('success'):
                    logger.info(f"  ✓ Cuenta seleccionada: {result.get('selected')}")
                    time.sleep(0.5)
                    return
            
            # MÉTODO 2: Escribir directamente (fallback)
            logger.info("  Intentando método directo...")
            try:
                cuenta_field = self.frame.locator('#cod_op_account_slc').first
                if cuenta_field.count() > 0:
                    cuenta_field.click()
                    time.sleep(0.3)
                    cuenta_field.fill(cuenta_numero)
                    cuenta_field.press('Tab')
                    logger.info(f"  ✓ Cuenta ingresada directamente: {cuenta_numero}")
                    time.sleep(0.5)
                    return
            except Exception as e:
                logger.debug(f"  Método directo falló: {e}")
            
            # MÉTODO 3: Forzar valor vía JavaScript
            logger.info("  Usando método JavaScript...")
            self.frame.evaluate("""(params) => {
                const input = document.querySelector('#cod_op_account_slc');
                const hidden = document.querySelector('input[name="cod_op_account_slc"]');
                
                if (input) {
                    input.value = params.valor;
                    input.dispatchEvent(new Event('change', { bubbles: true }));
                }
                if (hidden) {
                    hidden.value = params.valor;
                }
                
                // Intentar disparar evento de ExtJS si existe
                if (input && input.getAttribute('data-store')) {
                    const store = Ext.getCmp && Ext.getCmp(input.id);
                    if (store && store.setValue) {
                        store.setValue(params.valor);
                    }
                }
            }""", {'valor': cuenta_numero})
            
            logger.info(f"  ✓ Valor forzado vía JS: {cuenta_numero}")
            time.sleep(0.5)
            
        except Exception as e:
            logger.warning(f"  ⚠ Error seleccionando cuenta contable: {e}")
    
    def _fill_field(self, field_name: str, value: str):
        """Llena un campo del formulario."""
        try:
            # Intentar por name
            field = self.frame.locator(f'input[name="{field_name}"]').first
            if field.count() > 0:
                field.fill(value)
                return
            
            # Intentar por id
            field = self.frame.locator(f'#{field_name}').first
            if field.count() > 0:
                field.fill(value)
                return
                
        except Exception as e:
            logger.warning(f"Error llenando campo {field_name}: {e}")
    
    def _select_naturaleza(self, tipo: str = 'debit'):
        """Selecciona Débito o Crédito."""
        try:
            logger.info(f"  Seleccionando naturaleza: {tipo}")
            
            # Usar JavaScript con argumentos para evitar problemas con comillas
            js_script = """
                (params) => {
                    const tipo = params.tipo;
                    
                    // Buscar por value
                    let radio = document.querySelector('input[type="radio"][value="' + tipo + '"]');
                    
                    // Si no, buscar por texto cercano
                    if (!radio) {
                        const labels = document.querySelectorAll('label');
                        for (let label of labels) {
                            const text = label.textContent.toLowerCase();
                            if (text.includes('débito') || text.includes('debit')) {
                                const input = label.querySelector('input[type="radio"]');
                                if (input) {
                                    radio = input;
                                    break;
                                }
                            }
                        }
                    }
                    
                    // Buscar en inputs sin atributo value pero con name
                    if (!radio) {
                        const inputs = document.querySelectorAll('input[type="radio"]');
                        for (let input of inputs) {
                            const name = input.name || '';
                            const id = input.id || '';
                            if (name.includes('debit') || id.includes('debit') || name.includes('natur')) {
                                radio = input;
                                break;
                            }
                        }
                    }
                    
                    if (radio) {
                        radio.checked = true;
                        radio.click();
                        radio.dispatchEvent(new Event('change', { bubbles: true }));
                        return { success: true, id: radio.id, name: radio.name };
                    }
                    
                    return { success: false, error: 'Radio button no encontrado' };
                }
            """
            js_result = self.frame.evaluate(js_script, {'tipo': tipo})
            logger.info(f"  Resultado naturaleza: {js_result}")
            
        except Exception as e:
            logger.warning(f"  ⚠ Error seleccionando naturaleza: {e}")
    
    def _click_agregar_asiento(self):
        """Clic en el botón Agregar del asiento."""
        try:
            # Buscar el botón Agregar (hay varios, buscar el del formulario de asientos)
            btns = self.frame.locator('input[type="submit"][value="Agregar"]').all()
            if len(btns) > 1:
                # Usar el segundo (el primero es del formulario principal)
                btns[1].click()
            else:
                # JavaScript como fallback
                self.frame.evaluate("""
                    () => {
                        const forms = document.forms;
                        for (let form of forms) {
                            if (form.name.includes('entries') || form.action.includes('entries')) {
                                const btn = form.querySelector('input[value="Agregar"]');
                                if (btn) {
                                    btn.click();
                                    return true;
                                }
                            }
                        }
                        return false;
                    }
                """)
        except Exception as e:
            logger.warning(f"Error clic en Agregar asiento: {e}")
