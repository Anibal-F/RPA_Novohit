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
            
            # 1. Seleccionar Cuenta Contable PRIMERO (campo obligatorio)
            cuenta_contable = self._get_cuenta_contable(record, config_loader)
            if cuenta_contable:
                success = self._select_cuenta_contable(cuenta_contable)
                if success:
                    logger.info(f"  ✓ Cuenta contable seleccionada: {cuenta_contable}")
                else:
                    logger.error("  ❌ No se pudo seleccionar cuenta contable")
                    return False
            else:
                logger.error("  ❌ No se encontró cuenta contable en configuración")
                return False
            
            # Esperar a que se procese la selección de cuenta
            time.sleep(1)
            
            # 2. Llenar Monto (campo obligatorio)
            monto = record.get('mn_operation') or record.get('mm_operation', '')
            if monto:
                self._fill_monto_asiento(str(monto))
                logger.info(f"  ✓ Monto: {monto}")
            else:
                logger.error("  ❌ No se encontró monto")
                return False
            
            # 3. Seleccionar Naturaleza según configuración del Excel (columna F)
            naturaleza = self._get_naturaleza(record, config_loader)
            success = self._select_naturaleza(naturaleza)
            if success:
                logger.info(f"  ✓ Naturaleza: {naturaleza.capitalize()}")
            else:
                logger.error("  ❌ No se pudo seleccionar naturaleza")
                return False
            
            # Esperar a que se procesen los campos obligatorios
            time.sleep(1)
            
            # 4. Seleccionar Unidad de Negocio (si está disponible)
            unidad_negocio_id = self._get_unidad_negocio_id(config_loader)
            if unidad_negocio_id:
                self._select_unidad_negocio(unidad_negocio_id)
                time.sleep(0.5)
            
            # 5. Tipo de Cambio (1.0000 por defecto)
            tc = record.get('tc_currency', '1.0000')
            self._fill_field_js('tc_currency', tc)
            logger.info(f"  ✓ Tipo Cambio: {tc}")
            
            # 6. Concepto (mismo que el registro principal)
            concepto = record.get('notes', '')
            if concepto:
                self._fill_field_js('observations', concepto[:50])
                logger.info(f"  ✓ Concepto: {concepto[:50]}...")
            
            # Esperar antes de hacer clic en Agregar
            time.sleep(0.5)
            
            # 7. Clic en Agregar
            success = self._click_agregar_asiento()
            if success:
                logger.info("  ✓ Asiento contable registrado")
            else:
                logger.error("  ❌ No se pudo hacer clic en Agregar")
                return False
            
            # Esperar a que se procese
            time.sleep(1.5)
            
            return True
            
        except Exception as e:
            logger.error(f"Error en asiento contable: {e}")
            import traceback
            logger.error(traceback.format_exc())
            return False
    
    def _get_cuenta_contable(self, record: Dict, config_loader) -> Optional[str]:
        """Obtiene la cuenta contable según el tipo de operación."""
        if not config_loader:
            logger.warning("  [DEBUG] No hay config_loader")
            return None
        
        # Obtener el nombre de la operación
        operacion_id = record.get('id_tp_operation')
        operacion_nombre = self._get_operacion_nombre(operacion_id)
        logger.info(f"  [DEBUG] Buscando cuenta contable para: {operacion_nombre} (ID: {operacion_id})")
        
        # Si es DEPOSITO (ID 6), buscar cuenta por unidad de negocio y tipo de transacción
        if operacion_id == '6' or record.get('categoria') == 'deposito':
            unidad_id = record.get('unidad_negocio_id') or config_loader.get_unidad_negocio_id()
            tipo_transaccion = record.get('tipo_transaccion', '')
            logger.info(f"  [DEBUG] Es depósito. Unidad={unidad_id}, Tipo={tipo_transaccion}")
            if unidad_id:
                # Intentar obtener cuenta del Excel según tipo de transacción
                cuenta = config_loader.get_cuenta_deposito_for_unidad(unidad_id, tipo_transaccion)
                if cuenta:
                    logger.info(f"  [DEBUG] Cuenta de depósito encontrada: {cuenta}")
                    return cuenta
                
                # FALLBACK: Usar cuentas por defecto según unidad
                fallback_cuentas = {
                    '2': '11012001.002',
                    '3': '11012002.002'
                }
                if unidad_id in fallback_cuentas:
                    cuenta_fallback = fallback_cuentas[unidad_id]
                    logger.info(f"  [DEBUG] Usando cuenta fallback: {cuenta_fallback}")
                    return cuenta_fallback
                
                logger.warning(f"  [DEBUG] No hay cuenta configurada para unidad {unidad_id}")
        
        # Buscar en configuración general (para comisiones, iva, o fallback de depositos)
        config = config_loader.get_operation_config(operacion_nombre)
        if config:
            logger.info(f"  [DEBUG] Config encontrada: {config}")
            if 'cuenta_contable' in config:
                cuenta = config['cuenta_contable']
                logger.info(f"  [DEBUG] Cuenta contable en config: '{cuenta}'")
                if cuenta and cuenta.strip() and cuenta.lower() != 'nan':
                    return cuenta
                else:
                    logger.warning(f"  [DEBUG] Cuenta contable vacía o inválida: '{cuenta}'")
            else:
                logger.warning(f"  [DEBUG] No hay 'cuenta_contable' en config")
        else:
            logger.warning(f"  [DEBUG] No se encontró config para: {operacion_nombre}")
        
        return None
    
    def _get_naturaleza(self, record: Dict, config_loader) -> str:
        """Obtiene la naturaleza (debito/credito) según el tipo de operación."""
        
        # Obtener el nombre de la operación
        operacion_id = record.get('id_tp_operation')
        operacion_nombre = self._get_operacion_nombre(operacion_id)
        
        # FALLBACK PRIORITARIO: Los depósitos (ID 6) SIEMPRE son crédito
        if operacion_id == '6' or record.get('categoria') == 'deposito':
            logger.info(f"  [DEBUG] Es depósito (ID={operacion_id}), forzando naturaleza: CREDITO")
            return 'credit'
        
        # Para comisiones e IVA, usar configuración del Excel
        if config_loader:
            naturaleza = config_loader.get_naturaleza_for_operation(operacion_nombre)
            if naturaleza:
                resultado = 'credit' if naturaleza == 'credito' else 'debit'
                logger.info(f"  [DEBUG] Naturaleza del Excel para {operacion_nombre}: {resultado}")
                return resultado
        
        # Default para comisiones/iva
        logger.info(f"  [DEBUG] Usando naturaleza por defecto: DEBITO para {operacion_nombre}")
        return 'debit'
    
    def _get_unidad_negocio_id(self, config_loader) -> Optional[str]:
        """Obtiene el ID de unidad de negocio desde la configuración."""
        if not config_loader:
            return None
        return config_loader.get_unidad_negocio_id()
    
    def _select_unidad_negocio(self, unidad_id: str):
        """
        Selecciona la unidad de negocio en el dropdown.
        
        Args:
            unidad_id: ID de la unidad de negocio (ej: '3' para Club Playa)
        """
        try:
            logger.info(f"  Seleccionando unidad de negocio: {unidad_id}")
            
            # Primero verificar cuántas opciones tiene el dropdown
            check_dropdown = self.frame.evaluate("""
                () => {
                    const select = document.querySelector('#id_c_branch');
                    if (!select) return { exists: false, options: 0 };
                    
                    const options = Array.from(select.options);
                    return {
                        exists: true,
                        options: options.length,
                        option_values: options.map(o => ({ value: o.value, text: o.text }))
                    };
                }
            """)
            
            logger.info(f"  Estado dropdown U.Negocio: {check_dropdown}")
            
            if not check_dropdown.get('exists'):
                logger.info("  ℹ️ Dropdown de unidad de negocio no encontrado, continuando...")
                return
            
            options_count = check_dropdown.get('options', 0)
            option_values = check_dropdown.get('option_values', [])
            
            # Si solo hay 1 opción, es "SIN U.Negocio" - continuar sin cambiar
            if options_count <= 1:
                logger.info("  ℹ️ Solo hay 1 opción (SIN U.Negocio), continuando...")
                return
            
            # Verificar si el valor configurado existe en las opciones
            value_exists = any(opt['value'] == unidad_id for opt in option_values)
            
            if not value_exists:
                logger.warning(f"  ⚠️ Unidad de negocio {unidad_id} no encontrada en opciones disponibles")
                logger.info(f"  Opciones disponibles: {[opt['text'] for opt in option_values]}")
                # Usar la primera opción válida (que no sea SIN U.Negocio)
                for opt in option_values:
                    if opt['value'] != '1' and opt['value'] != '':
                        unidad_id = opt['value']
                        logger.info(f"  Usando primera opción válida: {opt['text']} (ID: {unidad_id})")
                        break
            
            # Seleccionar el valor con JavaScript
            result = self.frame.evaluate("""
                (params) => {
                    const select = document.querySelector('#id_c_branch');
                    if (!select) return { success: false, error: 'Select no encontrado' };
                    
                    // Buscar la opción con el valor
                    let optionFound = false;
                    let selectedText = '';
                    
                    for (let i = 0; i < select.options.length; i++) {
                        if (select.options[i].value === params.unidad_id) {
                            select.selectedIndex = i;
                            selectedText = select.options[i].text;
                            optionFound = true;
                            break;
                        }
                    }
                    
                    if (!optionFound) {
                        return { success: false, error: 'Opción no encontrada', searched: params.unidad_id };
                    }
                    
                    // Disparar eventos para que ExtJS detecte el cambio
                    select.dispatchEvent(new Event('change', { bubbles: true }));
                    select.dispatchEvent(new Event('blur', { bubbles: true }));
                    
                    // Intentar disparar evento específico de ExtJS si existe
                    if (typeof Ext !== 'undefined' && Ext.getCmp) {
                        const cmp = Ext.getCmp('id_c_branch');
                        if (cmp && cmp.setValue) {
                            cmp.setValue(params.unidad_id);
                        }
                    }
                    
                    return { success: true, selected: selectedText, value: params.unidad_id };
                }
            """, {'unidad_id': unidad_id})
            
            if result.get('success'):
                logger.info(f"  ✓ Unidad de negocio seleccionada: {result.get('selected')}")
            else:
                logger.warning(f"  ⚠️ No se pudo seleccionar unidad: {result.get('error')}")
            
            time.sleep(0.5)
            
        except Exception as e:
            logger.warning(f"  ⚠️ Error seleccionando unidad de negocio: {e}")
            # No fallar el proceso si esto falla
    
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
    
    def _select_cuenta_contable(self, cuenta: str) -> bool:
        """Selecciona la cuenta contable del dropdown de forma robusta."""
        try:
            logger.info(f"  Seleccionando cuenta contable: {cuenta}")
            
            # La cuenta viene como nombre descriptivo (ej: "IVA acreditable 16%")
            # El dropdown muestra formato: "11180001 - IVA acreditable 16%"
            # Buscamos por el nombre exacto (case insensitive)
            search_text = cuenta.strip().lower()
            
            logger.info(f"  Buscando texto: '{search_text}'")
            
            # Paso 1: Hacer clic en el trigger para abrir el dropdown
            trigger_result = self.frame.evaluate("""() => {
                // Buscar por ID específico
                let trigger = document.querySelector('#ext-gen55');
                if (trigger) {
                    trigger.click();
                    return { success: true, method: 'ext-gen55' };
                }
                // Buscar por clase
                trigger = document.querySelector('.x-form-arrow-trigger');
                if (trigger) {
                    trigger.click();
                    return { success: true, method: 'arrow-trigger' };
                }
                // Buscar junto al input de cuenta
                const cuentaInput = document.querySelector('#cod_op_account_slc');
                if (cuentaInput && cuentaInput.parentElement) {
                    trigger = cuentaInput.parentElement.querySelector('.x-form-trigger');
                    if (trigger) {
                        trigger.click();
                        return { success: true, method: 'parent-trigger' };
                    }
                }
                return { success: false, error: 'Trigger no encontrado' };
            }""")
            
            logger.info(f"  Trigger clic: {trigger_result}")
            
            if not trigger_result.get('success'):
                return False
            
            # Paso 2: Esperar a que el dropdown se abra y cargue
            time.sleep(2)
            
            # Paso 3: Buscar y seleccionar la opción (con reintentos)
            max_attempts = 3
            for attempt in range(max_attempts):
                result = self.frame.evaluate("""(params) => {
                    // Buscar items del dropdown
                    const items = document.querySelectorAll('.x-combo-list-item');
                    
                    if (items.length === 0) {
                        return { success: false, error: 'No hay items en el dropdown', attempt: params.attempt };
                    }
                    
                    // PRIMERO: Buscar coincidencia exacta por texto completo (case insensitive)
                    for (let item of items) {
                        const text = item.textContent || '';
                        const textLower = text.toLowerCase();
                        // Buscar el texto exacto de la cuenta
                        if (textLower.includes(params.search_text)) {
                            item.scrollIntoView({ block: 'center', behavior: 'instant' });
                            item.click();
                            return { success: true, selected: text, method: 'exact_text_match' };
                        }
                    }
                    
                    // SEGUNDO: Si no se encuentra, buscar por palabras clave específicas
                    // Extraer palabras clave del texto de búsqueda
                    const keywords = params.search_text.split(' ').filter(w => w.length > 3);
                    
                    for (let item of items) {
                        const text = item.textContent || '';
                        const textLower = text.toLowerCase();
                        
                        // Verificar si todas las palabras clave están presentes
                        const allKeywordsMatch = keywords.every(kw => textLower.includes(kw));
                        if (allKeywordsMatch && keywords.length > 0) {
                            item.scrollIntoView({ block: 'center', behavior: 'instant' });
                            item.click();
                            return { success: true, selected: text, method: 'keyword_match' };
                        }
                    }
                    
                    return { 
                        success: false, 
                        error: 'Opción no encontrada', 
                        items_count: items.length,
                        search_text: params.search_text,
                        sample_items: Array.from(items).slice(0, 5).map(i => i.textContent),
                        attempt: params.attempt 
                    };
                }""", {'search_text': search_text, 'attempt': attempt + 1})
                
                logger.info(f"  Intento {attempt + 1}: {result}")
                
                if result.get('success'):
                    time.sleep(2)  # Esperar a que se cierre el dropdown y se procese
                    return True
                
                # Si no tuvo éxito, esperar y reintentar
                time.sleep(1.5)
            
            # Si todos los intentos fallaron, reportar error
            logger.error(f"  ❌ No se pudo encontrar la cuenta contable '{cuenta}' después de {max_attempts} intentos")
            
            # Cerrar el dropdown primero (presionar Escape)
            self.frame.evaluate("""() => {
                document.dispatchEvent(new KeyboardEvent('keydown', { key: 'Escape' }));
            }""")
            time.sleep(0.5)
            
            return False
            
        except Exception as e:
            logger.error(f"  ❌ Error seleccionando cuenta contable: {e}")
            import traceback
            logger.error(traceback.format_exc())
            return False
    
    def _fill_monto_asiento(self, monto: str):
        """Llena el campo de monto del asiento contable de forma robusta."""
        try:
            # Usar JavaScript para llenar el campo mn_entry
            result = self.frame.evaluate(f"""
                () => {{
                    // Buscar por name
                    let input = document.querySelector('input[name="mn_entry"]');
                    if (!input) {{
                        // Buscar por id que contenga mn_entry
                        const inputs = document.querySelectorAll('input');
                        for (const inp of inputs) {{
                            if (inp.name && inp.name.includes('mn_entry')) {{
                                input = inp;
                                break;
                            }}
                        }}
                    }}
                    
                    if (input) {{
                        input.value = '{monto}';
                        input.dispatchEvent(new Event('focus', {{ bubbles: true }}));
                        input.dispatchEvent(new Event('input', {{ bubbles: true }}));
                        input.dispatchEvent(new Event('change', {{ bubbles: true }}));
                        input.dispatchEvent(new Event('blur', {{ bubbles: true }}));
                        return {{ success: true, value: input.value }};
                    }}
                    
                    return {{ success: false, error: 'Campo mn_entry no encontrado' }};
                }}
            """)
            
            logger.info(f"  Monto llenado: {result}")
            time.sleep(0.5)
            
        except Exception as e:
            logger.warning(f"  ⚠ Error llenando monto con JS: {e}")
            # Fallback
            try:
                field = self.frame.locator('input[name="mn_entry"]').first
                if field.count() > 0:
                    field.fill(monto)
                    field.blur()
            except:
                pass
    
    def _fill_field_js(self, field_name: str, value: str):
        """Llena un campo del formulario usando JavaScript."""
        try:
            result = self.frame.evaluate(f"""
                () => {{
                    // Buscar por name
                    let input = document.querySelector('input[name="{field_name}"]');
                    if (!input) {{
                        // Buscar por id
                        input = document.querySelector('#{field_name}');
                    }}
                    
                    if (input) {{
                        input.value = '{value}';
                        input.dispatchEvent(new Event('input', {{ bubbles: true }}));
                        input.dispatchEvent(new Event('change', {{ bubbles: true }}));
                        input.dispatchEvent(new Event('blur', {{ bubbles: true }}));
                        return {{ success: true }};
                    }}
                    
                    return {{ success: false }};
                }}
            """)
            time.sleep(0.3)
                
        except Exception as e:
            logger.warning(f"Error llenando campo {field_name}: {e}")
    
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
    
    def _select_naturaleza(self, tipo: str = 'debit') -> bool:
        """Selecciona Débito o Crédito. Retorna True si tuvo éxito."""
        try:
            logger.info(f"  Seleccionando naturaleza: {tipo}")
            
            # Según el HTML de Novohit:
            # - name="is_debit" value="0" -> CRÉDITO
            # - name="is_debit" value="1" -> DÉBITO
            is_debit_value = '0' if tipo == 'credit' else '1'
            
            # Usar JavaScript para seleccionar el radio button
            js_result = self.frame.evaluate("""
                (params) => {
                    const isDebitValue = params.isDebitValue;
                    
                    // Buscar por name="is_debit" y value específico
                    let radio = document.querySelector('input[type="radio"][name="is_debit"][value="' + isDebitValue + '"]');
                    
                    // Si no encontramos, buscar por name que contenga 'debit'
                    if (!radio) {
                        const inputs = document.querySelectorAll('input[type="radio"]');
                        for (let input of inputs) {
                            const name = input.name || '';
                            if (name.includes('debit')) {
                                // Para crédito (is_debit=0), para débito (is_debit=1)
                                if (input.value === isDebitValue) {
                                    radio = input;
                                    break;
                                }
                            }
                        }
                    }
                    
                    // Buscar por texto de label
                    if (!radio) {
                        const labels = document.querySelectorAll('label');
                        for (let label of labels) {
                            const text = label.textContent.toLowerCase();
                            const input = label.querySelector('input[type="radio"]');
                            if (input) {
                                if (isDebitValue === '0' && (text.includes('crédito') || text.includes('credito'))) {
                                    radio = input;
                                    break;
                                }
                                if (isDebitValue === '1' && (text.includes('débito') || text.includes('debito'))) {
                                    radio = input;
                                    break;
                                }
                            }
                        }
                    }
                    
                    if (radio) {
                        radio.checked = true;
                        radio.click();
                        radio.dispatchEvent(new Event('change', { bubbles: true }));
                        radio.dispatchEvent(new Event('click', { bubbles: true }));
                        return { success: true, id: radio.id, name: radio.name, value: radio.value, is_debit: isDebitValue };
                    }
                    
                    return { success: false, error: 'Radio button no encontrado', is_debit: isDebitValue };
                }
            """, {'isDebitValue': is_debit_value})
            
            logger.info(f"  Resultado naturaleza: {js_result}")
            time.sleep(0.5)
            return js_result.get('success', False)
            
        except Exception as e:
            logger.warning(f"  ⚠ Error seleccionando naturaleza: {e}")
            return False
    
    def _click_agregar_asiento(self) -> bool:
        """Clic en el botón Agregar del asiento. Retorna True si tuvo éxito."""
        try:
            logger.info("  Haciendo clic en Agregar asiento...")
            
            # Intentar con JavaScript primero (más confiable)
            js_result = self.frame.evaluate("""
                () => {
                    // Buscar en formularios de asientos
                    const forms = document.forms;
                    for (let form of forms) {
                        if (form.name && (form.name.includes('entries') || form.action.includes('entries'))) {
                            const btn = form.querySelector('input[type="submit"][value="Agregar"]');
                            if (btn) {
                                btn.click();
                                return { success: true, method: 'form-entries' };
                            }
                        }
                    }
                    
                    // Buscar todos los botones Agregar
                    const allBtns = document.querySelectorAll('input[type="submit"][value="Agregar"]');
                    if (allBtns.length > 1) {
                        // El segundo suele ser del asiento
                        allBtns[1].click();
                        return { success: true, method: 'second-button' };
                    } else if (allBtns.length === 1) {
                        allBtns[0].click();
                        return { success: true, method: 'only-button' };
                    }
                    
                    // Buscar por texto en botones
                    const buttons = document.querySelectorAll('button, input[type="submit"]');
                    for (let btn of buttons) {
                        const text = (btn.textContent || btn.value || '').toLowerCase();
                        if (text.includes('agregar')) {
                            btn.click();
                            return { success: true, method: 'text-search' };
                        }
                    }
                    
                    return { success: false, error: 'Botón no encontrado' };
                }
            """)
            
            logger.info(f"  Resultado clic Agregar: {js_result}")
            time.sleep(0.5)
            return js_result.get('success', False)
            
        except Exception as e:
            logger.warning(f"Error clic en Agregar asiento: {e}")
            return False
