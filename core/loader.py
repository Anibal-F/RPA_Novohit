"""
Módulo Loader: Carga los datos en Novohit vía automatización web.
"""
import time
import logging
from typing import List, Dict, Optional
from playwright.sync_api import sync_playwright, Frame, Page

from config import settings
from core.accounting_entry import AccountingEntryHandler

logger = logging.getLogger(__name__)


class NovohitLoader:
    """
    Automatiza la carga de operaciones bancarias en Novohit.
    """
    
    def __init__(self, headless: bool = False):
        self.headless = headless
        self.browser = None
        self.context = None
        self.page = None
        self.frame = None  # El iframe donde está el contenido
        
    def __enter__(self):
        """Context manager entry."""
        self.start_browser()
        return self
        
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit."""
        self.close()
        
    def start_browser(self):
        """Inicia el navegador y hace login."""
        logger.info("Iniciando navegador...")
        
        playwright = sync_playwright().start()
        self.playwright = playwright
        
        self.browser = playwright.chromium.launch(
            headless=self.headless,
            slow_mo=100,
            args=['--start-maximized']
        )
        
        self.context = self.browser.new_context(
            viewport={'width': 1920, 'height': 1080}
        )
        
        self.page = self.context.new_page()
        
        # Login
        self._login()
        
    def _login(self):
        """Realiza el login en Novohit."""
        logger.info("Realizando login...")
        
        self.page.goto(settings.NOVOHIT_URL, wait_until="networkidle")
        
        # Esperar formulario
        self.page.wait_for_selector(settings.NOVOHIT_USER_SELECTOR, state="visible")
        
        # Completar credenciales
        self.page.fill(settings.NOVOHIT_USER_SELECTOR, settings.NOVOHIT_USERNAME)
        self.page.fill(settings.NOVOHIT_PASS_SELECTOR, settings.NOVOHIT_PASSWORD)
        
        # Login
        self.page.click(settings.NOVOHIT_LOGIN_SELECTOR)
        self.page.wait_for_load_state("networkidle")
        
        logger.info("Login exitoso")
        
    def navigate_to_bank_operations(self, max_retries: int = 3) -> bool:
        """Navega a Operaciones Bancarias."""
        logger.info("Navegando a Operaciones Bancarias...")
        
        for attempt in range(max_retries):
            try:
                logger.info(f"  Intento {attempt + 1}/{max_retries}")
                
                # Clic en Administración
                admin_menu = self.page.get_by_role("link", name="Administración").first
                admin_menu.click(timeout=10000)
                time.sleep(0.5)
                
                # Hover en Tesorería
                tesoreria_menu = self.page.get_by_role("link", name="Tesorería").first
                tesoreria_menu.hover(timeout=10000)
                time.sleep(0.5)
                
                # Clic en Operaciones Bancarias
                operaciones_link = self.page.locator('a.x-menu-item:has-text("Operaciones Bancarias")').first
                operaciones_link.click(timeout=10000)
                time.sleep(2)  # Esperar carga
                
                # Detectar iframe
                self._detect_frame()
                
                # Verificar que estamos en el listado
                if self._verify_list_page():
                    logger.info("✓ Navegación completada exitosamente")
                    return True
                else:
                    logger.warning(f"  No se verificó el listado en intento {attempt + 1}")
                    
            except Exception as e:
                logger.error(f"  Error en intento {attempt + 1}: {e}")
                time.sleep(2)
                continue
        
        # Si todos los intentos fallan, intentar navegación directa por URL
        logger.info("Intentando navegación directa por URL...")
        try:
            list_url = settings.NOVOHIT_URL.replace('user_login.php', 'bnk_operations.php')
            self.page.goto(list_url, wait_until="domcontentloaded", timeout=15000)
            time.sleep(3)
            self._detect_frame()
            
            if self._verify_list_page():
                logger.info("✓ Navegación por URL exitosa")
                return True
        except Exception as e2:
            logger.error(f"  Navegación por URL también falló: {e2}")
        
        logger.error("❌ No se pudo navegar a Operaciones Bancarias")
        return False
        
    def _detect_frame(self):
        """Detecta y selecciona el iframe del contenido."""
        # Intentar por nombre
        try:
            frame_by_name = self.page.frame('id_frame_app')
            if frame_by_name:
                self.frame = frame_by_name
                logger.info("Iframe 'id_frame_app' detectado por nombre")
                return
        except:
            pass
        
        # Intentar buscando en todos los frames por URL
        try:
            all_frames = self.page.frames
            for frame in all_frames:
                try:
                    url = frame.url
                    if 'bnk_operations' in url or 'ccgen' in url:
                        self.frame = frame
                        logger.info(f"Iframe detectado por URL: {url[:60]}...")
                        return
                except:
                    continue
        except:
            pass
        
        # Fallback: primer iframe
        iframes = self.page.locator('iframe').all()
        if len(iframes) > 0:
            try:
                src = iframes[0].get_attribute('src')
                # Usar el frame por posición
                all_frames = self.page.frames
                if len(all_frames) > 1:
                    self.frame = all_frames[1]  # frames[0] es main, frames[1] es el primer iframe
                    logger.info(f"Usando iframe en posición 1, src: {src}")
                    return
            except:
                pass
        
        # Si todo falla, usar la página principal
        self.frame = self.page
        logger.info("Usando página principal (sin iframe)")
    
    def _verify_list_page(self) -> bool:
        """Verifica que estamos en la página de listado de operaciones."""
        try:
            if not self.frame:
                return False
            
            check = self.frame.evaluate("""
                () => {
                    const addButton = document.querySelector('a[href*="is_ins_new=1"]');
                    const recordTable = document.querySelector('table.Record');
                    const gridTable = document.querySelector('table.Grid');
                    const dataTable = document.querySelector('.x-grid3');
                    
                    return {
                        has_add_button: !!addButton,
                        has_record_table: !!recordTable,
                        has_grid_table: !!gridTable,
                        has_data_table: !!dataTable
                    };
                }
            """)
            
            return (check.get('has_add_button') or 
                    check.get('has_record_table') or 
                    check.get('has_grid_table') or 
                    check.get('has_data_table'))
            
        except Exception as e:
            logger.warning(f"Error verificando página: {e}")
            return False
            
    def click_add_button(self) -> bool:
        """Clic en el botón '+' para agregar nueva operación."""
        logger.info("Clic en botón '+'...")
        
        try:
            # Scroll al final de la página
            self.frame.evaluate("window.scrollTo(0, document.body.scrollHeight)")
            time.sleep(0.8)
            
            # Guardar URL actual del frame para detectar cambio
            old_frame_url = None
            try:
                old_frame_url = self.frame.url
            except:
                pass
            
            # JavaScript click (más confiable para navegación dentro de iframe)
            logger.info("Usando JavaScript para hacer clic en '+'...")
            result = self.frame.evaluate("""
                () => {
                    const link = document.querySelector('a[href*="is_ins_new=1"]');
                    if (link) {
                        link.scrollIntoView({behavior: 'instant', block: 'center'});
                        link.click();
                        return { success: true, href: link.href };
                    }
                    const img = document.querySelector('img[src*="icon_rec_ins"]');
                    if (img && img.parentElement && img.parentElement.tagName === 'A') {
                        img.parentElement.scrollIntoView({behavior: 'instant', block: 'center'});
                        img.parentElement.click();
                        return { success: true, href: img.parentElement.href };
                    }
                    return { success: false, error: 'Elemento no encontrado' };
                }
            """)
            
            logger.info(f"Resultado del clic: {result}")
            
            # Esperar a que la navegación ocurra (hasta 5 segundos)
            time.sleep(2)
            
            # Detectar el nuevo frame (puede haber cambiado de URL)
            self._detect_frame_after_navigation()
            
            logger.info("Formulario de inserción abierto")
            return True
            
        except Exception as e:
            logger.error(f"Error haciendo clic en botón '+': {e}")
            # Screenshot para debug
            try:
                self.page.screenshot(path="./debug_error_click_plus.png")
            except:
                pass
            return False
    
    def _detect_frame_after_navigation(self):
        """
        Detecta el frame después de una navegación.
        El frame de inserción típicamente tiene 'is_ins_new=1' en la URL.
        """
        logger.info("Detectando frame después de navegación...")
        
        # Esperar un poco para que la navegación ocurra
        time.sleep(1)
        
        # Buscar frame que contenga 'is_ins_new' en la URL
        max_attempts = 10
        for attempt in range(max_attempts):
            try:
                all_frames = self.page.frames
                for frame in all_frames:
                    try:
                        url = frame.url
                        if 'is_ins_new' in url or 'bnk_operations' in url:
                            self.frame = frame
                            logger.info(f"Frame detectado (intento {attempt+1}): {url[:80]}...")
                            return
                    except:
                        continue
            except:
                pass
            
            time.sleep(0.5)
        
        # Si no se encuentra, intentar con el último frame disponible
        try:
            all_frames = self.page.frames
            if len(all_frames) > 1:
                self.frame = all_frames[-1]  # Último frame
                logger.info(f"Usando último frame disponible: {self.frame.url[:80]}...")
                return
        except:
            pass
        
        logger.warning("No se pudo detectar el frame específico, usando página principal")
        self.frame = self.page
            
    def fill_form(self, record: Dict) -> bool:
        """
        Llena el formulario de operación bancaria.
        
        Args:
            record: Diccionario con los datos a ingresar
            
        Returns:
            True si se llenó correctamente, False en caso contrario
        """
        try:
            logger.info(f"Llenando formulario para: {record.get('notes', '')[:50]}...")
            
            # Esperar a que el formulario esté listo y los dropdowns carguen
            logger.info("  Esperando a que el formulario cargue...")
            time.sleep(3)
            
            # Verificar que tenemos el frame correcto
            logger.info(f"Frame actual URL: {self.frame.url[:80] if hasattr(self.frame, 'url') else 'N/A'}...")
            
            # 1. Seleccionar Cuenta (dropdown) - con retry
            cuenta_id = record.get('id_bnk_account')
            if cuenta_id:
                cuenta_seleccionada = False
                for intento in range(3):
                    try:
                        logger.info(f"  Intentando seleccionar cuenta (intento {intento + 1})...")
                        
                        # Verificar si el select tiene opciones con JavaScript
                        js_check = self.frame.evaluate("""() => {
                            const select = document.querySelector('#id_bnk_account');
                            if (!select) return { error: 'Select no encontrado' };
                            return { 
                                found: true, 
                                options: select.options.length,
                                has_value: Array.from(select.options).some(o => o.value === '3')
                            };
                        }""")
                        logger.info(f"  Estado del dropdown: {js_check}")
                        
                        if js_check.get('options', 0) > 1:
                            # Intentar seleccionar con JavaScript (más confiable)
                            js_result = self.frame.evaluate("""(params) => {
                                const select = document.querySelector('#id_bnk_account');
                                if (!select) return { error: 'Select no encontrado' };
                                
                                // Buscar la opción con el valor correcto
                                let optionFound = false;
                                for (let i = 0; i < select.options.length; i++) {
                                    if (select.options[i].value === params.cuenta_id) {
                                        select.selectedIndex = i;
                                        optionFound = true;
                                        break;
                                    }
                                }
                                
                                if (!optionFound) {
                                    return { error: 'Opción no encontrada', value: params.cuenta_id };
                                }
                                
                                // Disparar eventos
                                select.dispatchEvent(new Event('change', { bubbles: true }));
                                select.dispatchEvent(new Event('blur', { bubbles: true }));
                                
                                return { success: true, selected: select.value };
                            }""", {'cuenta_id': cuenta_id})
                            
                            if js_result.get('success'):
                                logger.info(f"  ✓ Cuenta seleccionada: {cuenta_id}")
                                cuenta_seleccionada = True
                                break
                            else:
                                logger.warning(f"  JS error: {js_result}")
                        
                        # Si no hay opciones, esperar y reintentar
                        logger.info(f"  Dropdown no listo, esperando...")
                        time.sleep(2)
                        
                    except Exception as e:
                        logger.warning(f"  Error intento {intento + 1}: {e}")
                        time.sleep(2)
                
                if not cuenta_seleccionada:
                    logger.error(f"  ❌ No se pudo seleccionar la cuenta después de 3 intentos")
                    return False
                
                time.sleep(0.5)
            
            # 2. Seleccionar Operación (dropdown)
            operacion_id = record.get('id_tp_operation')
            if operacion_id:
                try:
                    self.frame.select_option('#id_tp_operation', operacion_id)
                    logger.info(f"  ✓ Operación seleccionada: {operacion_id}")
                except Exception as e:
                    logger.warning(f"  ⚠ Error seleccionando operación: {e}")
                time.sleep(0.5)
            
            # 3. Fecha - usar JavaScript para llenar el campo
            fecha = record.get('dt_operation')
            if fecha:
                try:
                    self.frame.evaluate(f"""
                        () => {{
                            const fechaInput = document.querySelector('#dt_operation');
                            if (fechaInput) {{
                                fechaInput.value = '{fecha}';
                                fechaInput.dispatchEvent(new Event('change'));
                            }}
                        }}
                    """)
                    logger.info(f"  ✓ Fecha ingresada: {fecha}")
                except Exception as e:
                    logger.warning(f"  ⚠ Error ingresando fecha: {e}")
                time.sleep(0.3)
            
            # 4. Número de Documento
            no_document = record.get('no_document')
            if no_document:
                try:
                    self.frame.fill('#no_document', no_document)
                    logger.info(f"  ✓ Documento: {no_document}")
                except Exception as e:
                    logger.warning(f"  ⚠ Error ingresando documento: {e}")
                time.sleep(0.3)
            
            # 5. Monto - con múltiples intentos y eventos
            monto = record.get('mn_operation') or record.get('mm_operation')
            if monto:
                monto_str = str(monto).replace(',', '.')  # Asegurar punto decimal
                try:
                    # DEBUG: Listar todos los inputs del formulario
                    inputs_debug = self.frame.evaluate("""
                        () => {
                            const inputs = document.querySelectorAll('input');
                            return Array.from(inputs).map(i => ({
                                id: i.id,
                                name: i.name,
                                type: i.type,
                                value: i.value
                            })).filter(i => i.id || i.name);
                        }
                    """)
                    logger.info(f"  DEBUG - Inputs encontrados: {len(inputs_debug)}")
                    for inp in inputs_debug[:10]:  # Mostrar primeros 10
                        logger.info(f"    Input: id={inp['id']}, name={inp['name']}, value={inp['value']}")
                    
                    # Buscar input que contenga 'monto', 'mn_' o 'mm_' en su id/name
                    monto_input_info = None
                    for inp in inputs_debug:
                        if 'monto' in (inp['id'] or '').lower() or 'monto' in (inp['name'] or '').lower():
                            monto_input_info = inp
                            break
                        if 'mn_' in (inp['id'] or '').lower() or 'mn_' in (inp['name'] or '').lower():
                            monto_input_info = inp
                            break
                        if 'mm_' in (inp['id'] or '').lower() or 'mm_' in (inp['name'] or '').lower():
                            monto_input_info = inp
                            break
                    
                    if monto_input_info:
                        logger.info(f"  Input de monto identificado: id={monto_input_info['id']}, name={monto_input_info['name']}")
                        
                        # Usar el selector correcto
                        selector = f"input[id='{monto_input_info['id']}']" if monto_input_info['id'] else f"input[name='{monto_input_info['name']}']"
                        
                        # Intentar con Playwright
                        try:
                            input_elem = self.frame.locator(selector).first
                            input_elem.fill(monto_str)
                            input_elem.blur()
                            logger.info(f"  ✓ Monto llenado con Playwright: {monto_str}")
                        except:
                            # Fallback a JavaScript con el selector correcto
                            # Escapar el selector para JavaScript
                            selector_js = selector.replace('"', '\\"')
                            js_fill = self.frame.evaluate(f"""
                                () => {{
                                    const input = document.querySelector("{selector_js}");
                                    if (input) {{
                                        input.value = '{monto_str}';
                                        input.dispatchEvent(new Event('input', {{ bubbles: true }}));
                                        input.dispatchEvent(new Event('change', {{ bubbles: true }}));
                                        input.dispatchEvent(new Event('blur', {{ bubbles: true }}));
                                        return {{ success: true, value: input.value }};
                                    }}
                                    return {{ success: false }};
                                }}
                            """)
                            logger.info(f"  ✓ Monto llenado con JS: {monto_str}, resultado={js_fill}")
                    else:
                        logger.error("  ❌ No se encontró input de monto en el formulario")
                        
                except Exception as e:
                    logger.warning(f"  ⚠ Error ingresando monto: {e}")
                    import traceback
                    logger.debug(traceback.format_exc())
                
                time.sleep(0.3)
            
            # 6. Comentario
            notes = record.get('notes', '')
            if notes:
                try:
                    self.frame.fill('#notes', notes[:60])  # Max 60 chars
                    logger.info(f"  ✓ Comentario: {notes[:50]}...")
                except Exception as e:
                    logger.warning(f"  ⚠ Error ingresando comentario: {e}")
                time.sleep(0.3)
            
            logger.info("Formulario llenado exitosamente")
            
            # Screenshot para verificar
            try:
                self.page.screenshot(path="./debug_form_filled.png")
            except:
                pass
            
            return True
            
        except Exception as e:
            logger.error(f"Error llenando formulario: {e}")
            # Screenshot para debug
            try:
                self.page.screenshot(path="./debug_error_fill.png")
            except:
                pass
            return False
            
    def submit_form(self) -> bool:
        """
        Presiona el botón 'Agregar' para guardar la operación.
        
        Returns:
            True si se guardó exitosamente
        """
        try:
            logger.info("Guardando operación...")
            
            # Screenshot antes de intentar guardar
            self.page.screenshot(path="./debug_before_submit.png")
            
            # Intentar JavaScript primero (más confiable para este tipo de formularios)
            js_result = self.frame.evaluate("""
                () => {
                    // Buscar botón Agregar por múltiples criterios
                    let btn = document.querySelector('button[type="submit"]');
                    if (!btn) btn = document.querySelector('input[type="submit"][value="Agregar"]');
                    if (!btn) btn = document.querySelector('button:contains("Agregar")');
                    if (!btn) {
                        const buttons = document.querySelectorAll('button, input[type="submit"]');
                        for (let b of buttons) {
                            if (b.textContent && b.textContent.includes('Agregar')) {
                                btn = b;
                                break;
                            }
                            if (b.value && b.value.includes('Agregar')) {
                                btn = b;
                                break;
                            }
                        }
                    }
                    
                    if (btn) {
                        btn.scrollIntoView({behavior: 'instant', block: 'center'});
                        btn.click();
                        return { success: true, element: btn.tagName + (btn.value ? ':' + btn.value : '') };
                    }
                    
                    return { success: false, error: 'Botón no encontrado' };
                }
            """)
            
            logger.info(f"Resultado JS click en Agregar: {js_result}")
            
            # Si JS no funcionó, intentar con Playwright
            if not js_result or not js_result.get('success'):
                logger.info("Intentando click con Playwright...")
                
                # Buscar por varios selectores
                btn_selectors = [
                    'button[type="submit"]',
                    'input[type="submit"][value="Agregar"]',
                    'button:has-text("Agregar")',
                    'input[value="Agregar"]'
                ]
                
                for selector in btn_selectors:
                    try:
                        btn = self.frame.locator(selector).first
                        if btn.count() > 0:
                            btn.click(timeout=5000)
                            logger.info(f"Click exitoso con selector: {selector}")
                            break
                    except:
                        continue
            
            # Esperar a que se procese
            time.sleep(3)
            
            # Verificar estado después de guardar
            current_url = self.frame.url if hasattr(self.frame, 'url') else 'unknown'
            logger.info(f"URL después de guardar: {current_url}")
            
            # Verificar si hay mensajes de error o si apareció el formulario de asientos
            page_status = self.frame.evaluate("""
                () => {
                    // Buscar mensajes de error
                    const errorElems = document.querySelectorAll('.x-form-invalid-msg, .error, .alert, .ext-mb-error');
                    for (let el of errorElems) {
                        if (el.textContent.trim()) {
                            return { type: 'error', message: el.textContent.trim() };
                        }
                    }
                    
                    // Verificar si apareció el formulario de asientos (éxito)
                    const cuentaField = document.querySelector('#cod_op_account_slc');
                    const montoField = document.querySelector('input[name="mn_entry"]');
                    const asientoForm = document.querySelector('form[name*="entries"]');
                    
                    if (cuentaField || montoField || asientoForm) {
                        return { type: 'success', message: 'Formulario de asiento contable visible' };
                    }
                    
                    // Verificar tabla de asientos
                    const recordTable = document.querySelector('table.Record');
                    if (recordTable) {
                        const dataRows = recordTable.querySelectorAll('tr[class*="Row"]');
                        if (dataRows.length > 0) {
                            return { type: 'success', message: 'Asientos registrados en tabla' };
                        }
                    }
                    
                    return { type: 'unknown', message: 'Estado no determinado' };
                }
            """)
            
            logger.info(f"Estado de la página: {page_status}")
            
            if page_status and page_status.get('type') == 'error':
                logger.error(f"❌ Error detectado: {page_status['message']}")
                self.page.screenshot(path="./debug_error_after_submit.png")
                return False
            
            if page_status and page_status.get('type') == 'success':
                logger.info(f"✅ {page_status['message']}")
                return True
            
            # Si no se pudo determinar, asumir éxito si no hay errores obvios
            logger.info("⚠️ Estado incierto, pero continuando...")
            return True
            
        except Exception as e:
            logger.error(f"Error guardando operación: {e}")
            import traceback
            logger.debug(traceback.format_exc())
            # Screenshot para debug
            try:
                self.page.screenshot(path="./debug_error_submit.png")
            except:
                pass
            return False
    
    def filter_by_operation_and_date(self, operation_id: str, fecha: str, account_id: str = None) -> bool:
        """
        Filtra la tabla de operaciones bancarias por cuenta, operacion y fecha.
        """
        try:
            logger.info(f"Filtrando por Cuenta: {account_id}, Operacion: {operation_id}, Fecha: {fecha}")
            
            if not self._verify_list_page():
                logger.warning("No estamos en el listado de operaciones")
                return False
            
            # 1. Seleccionar Cuenta Bancaria (si se proporciona)
            if account_id:
                try:
                    # Selector especifico del HTML de Novohit
                    cuenta_select = self.frame.locator('select[name="s_id_bnk_account"]').first
                    
                    if cuenta_select.count() > 0:
                        cuenta_select.select_option(account_id)
                        logger.info(f"  Cuenta seleccionada: {account_id}")
                        time.sleep(0.5)
                    else:
                        logger.warning("  No se encontro el dropdown de cuenta (s_id_bnk_account)")
                except Exception as e:
                    logger.warning(f"  Error seleccionando cuenta: {e}")
            
            # 2. Seleccionar Tipo de Operacion
            try:
                # El select de operacion esta en la misma fila que cuenta
                # Buscamos por el label "Operacion" cercano
                op_select = self.frame.locator('select[name*="tp_operation"], select[name*="operation"]').first
                
                if op_select.count() > 0:
                    op_select.select_option(operation_id)
                    logger.info(f"  Operacion seleccionada: {operation_id}")
                    time.sleep(0.5)
                else:
                    logger.warning("  No se encontro el dropdown de operacion")
            except Exception as e:
                logger.warning(f"  Error seleccionando operacion: {e}")
            
            # 3. Ingresar Fecha usando el datepicker de jQuery UI
            try:
                logger.info("  Abriendo datepicker...")
                
                # Hacer clic en el icono del calendario (ui-datepicker-trigger)
                calendar_trigger = self.frame.locator('img.ui-datepicker-trigger').first
                if calendar_trigger.count() > 0:
                    calendar_trigger.click()
                    logger.info("    Calendario abierto")
                    time.sleep(0.8)  # Esperar a que el calendario se renderice
                    
                    # Extraer día, mes y año de la fecha (DD/MM/YYYY)
                    dia_str = fecha.split('/')[0].lstrip('0')  # Eliminar ceros a la izquierda
                    mes_str = fecha.split('/')[1].lstrip('0')
                    anio_str = fecha.split('/')[2]
                    
                    # Intentar hacer clic en el día específico del calendario
                    # Selector basado en el HTML: td con data-handler="selectDay" que contenga el número
                    day_clicked = False
                    try:
                        # Buscar el día en el calendario visible
                        # Los días tienen estructura: <td data-handler="selectDay" data-event="click" ...><a href="#">5</a></td>
                        day_locator = self.frame.locator(f'td[data-handler="selectDay"] a:has-text("{dia_str}")').first
                        
                        # Verificar si el día está visible en el calendario actual
                        if day_locator.count() > 0 and day_locator.is_visible():
                            day_locator.click()
                            logger.info(f"    Dia {dia_str} seleccionado en el calendario")
                            day_clicked = True
                            time.sleep(0.3)
                        else:
                            # Intentar buscar en los td directamente (algunos calendarios no usan <a>)
                            day_cells = self.frame.locator(f'td[data-handler="selectDay"]').all()
                            for cell in day_cells:
                                if cell.is_visible():
                                    text = cell.inner_text().strip()
                                    if text == dia_str:
                                        cell.click()
                                        logger.info(f"    Dia {dia_str} seleccionado en celda")
                                        day_clicked = True
                                        time.sleep(0.3)
                                        break
                    except Exception as click_err:
                        logger.warning(f"    No se pudo hacer clic en el dia: {click_err}")
                    
                    # Si no se pudo hacer clic en el día, usar JavaScript como fallback
                    if not day_clicked:
                        logger.info("    Usando metodo JavaScript para establecer fecha...")
                        js_result = self.frame.evaluate(f"""
                            () => {{
                                try {{
                                    // Intentar usar el datepicker de jQuery si existe
                                    if (typeof $ !== 'undefined' && $.datepicker) {{
                                        // Encontrar el input asociado al datepicker
                                        const inputs = document.querySelectorAll('input[name*="dt_operation"]');
                                        for (const input of inputs) {{
                                            if ($(input).datepicker) {{
                                                $(input).datepicker('setDate', '{fecha}');
                                                $(input).trigger('change');
                                                return {{ success: true, method: 'jquery' }};
                                            }}
                                        }}
                                    }}
                                    
                                    // Fallback: establecer valor directo en los campos
                                    const hiddenInput = document.querySelector('input[name="s_dt_operation"]');
                                    const calInput = document.querySelector('input[name="s_dt_operation_cal"]');
                                    
                                    const parts = '{fecha}'.split('/');
                                    const fechaISO = parts[2] + '-' + parts[1] + '-' + parts[0];
                                    
                                    if (hiddenInput) {{
                                        hiddenInput.value = fechaISO;
                                        hiddenInput.dispatchEvent(new Event('change', {{ bubbles: true }}));
                                    }}
                                    
                                    if (calInput) {{
                                        calInput.value = '{fecha}';
                                        calInput.dispatchEvent(new Event('change', {{ bubbles: true }}));
                                    }}
                                    
                                    // Cerrar el datepicker si esta abierto
                                    const datepickerDiv = document.querySelector('#ui-datepicker-div');
                                    if (datepickerDiv) {{
                                        datepickerDiv.style.display = 'none';
                                    }}
                                    
                                    return {{ success: true, method: 'direct' }};
                                }} catch (e) {{
                                    return {{ success: false, error: e.message }};
                                }}
                            }}
                        """)
                        
                        if js_result and js_result.get('success'):
                            logger.info(f"  Fecha establecida: {fecha} (metodo: {js_result.get('method')})")
                        else:
                            logger.warning(f"  No se pudo establecer fecha: {js_result}")
                    else:
                        logger.info(f"  Fecha establecida: {fecha} (metodo: click en calendario)")
                    
                    time.sleep(0.3)
                else:
                    logger.warning("  No se encontro el icono del calendario")
                    
            except Exception as e:
                logger.warning(f"  Error ingresando fecha: {e}")
            
            # 4. Clic en Boton Buscar
            try:
                search_btn = self.frame.locator('input[value="Buscar"]').first
                if search_btn.count() > 0:
                    search_btn.click()
                    logger.info("  Filtro aplicado, esperando resultados...")
                    time.sleep(3)
                    return True
            except Exception as e:
                logger.warning(f"  Error clic en Buscar: {e}")
            
            return False
            
        except Exception as e:
            logger.warning(f"  Error filtrando tabla: {e}")
            return False
    
    def _click_nuevo_button(self) -> bool:
        """
        Hace clic en el botón 'Nuevo' para limpiar el formulario después de registrar.
        """
        try:
            logger.info("🔄 Clic en botón 'Nuevo' para siguiente registro...")
            
            # Intentar por name/value con JavaScript
            js_result = self.frame.evaluate("""
                () => {
                    // Buscar por value
                    let btn = document.querySelector('input[value="Nuevo"]');
                    if (!btn) btn = document.querySelector('input[name="Button_New"]');
                    if (!btn) btn = document.querySelector('input.Button[value="Nuevo"]');
                    
                    if (btn) {
                        btn.click();
                        return { success: true, method: 'value/name', element: btn.outerHTML.substring(0, 50) };
                    }
                    
                    // Fallback: buscar por texto visible
                    const buttons = document.querySelectorAll('input[type="submit"], input[type="button"], button');
                    for (let b of buttons) {
                        const val = b.value || b.textContent || '';
                        if (val.toLowerCase().includes('nuevo')) {
                            b.click();
                            return { success: true, method: 'text_search', value: val };
                        }
                    }
                    
                    return { success: false, error: 'Botón Nuevo no encontrado' };
                }
            """)
            
            logger.info(f"  Resultado clic en Nuevo: {js_result}")
            
            if js_result.get('success'):
                logger.info("  ✓ Formulario listo para siguiente registro")
                return True
            else:
                logger.warning(f"  ⚠ No se encontró botón Nuevo: {js_result.get('error')}")
                return False
                
        except Exception as e:
            logger.warning(f"  ⚠ Error clic en Nuevo: {e}")
            return False
    
    def _normalize_fecha(self, fecha: str) -> str:
        """Normaliza una fecha al formato DDMMYYYY (8 digitos)."""
        try:
            fecha_clean = fecha.strip()
            parts = fecha_clean.replace('-', '/').split('/')
            
            if len(parts) == 3:
                dia = parts[0].zfill(2)
                mes = parts[1].zfill(2)
                anio = parts[2]
                if len(anio) == 2:
                    anio = "20" + anio
                return f"{dia}{mes}{anio}"
            else:
                numeros = ''.join(c for c in fecha if c.isdigit())
                if len(numeros) == 8:
                    return numeros
                elif len(numeros) == 6:
                    return numeros[:4] + "20" + numeros[4:]
                else:
                    return numeros.ljust(8, '0')[:8]
        except Exception as e:
            logger.warning(f"Error normalizando fecha '{fecha}': {e}")
            return ''.join(c for c in fecha if c.isdigit())[:8].ljust(8, '0')
    
    def get_last_document_sequence(self, prefix: str, fecha: str) -> int:
        """Consulta en Novohit el ultimo numero de documento registrado."""
        try:
            fecha_clean = self._normalize_fecha(fecha)
            search_pattern = f"{prefix}-{fecha_clean}-"
            
            logger.info(f"Buscando documentos con patron: '{search_pattern}'")
            
            if self.frame is None:
                self._detect_frame()
                if self.frame is None:
                    return 0
            
            if not self._verify_list_page():
                return 0
            
            # Buscar en la tabla
            result = self.frame.evaluate("""
                (searchPattern) => {
                    const documentNumbers = [];
                    const selectors = ['table.Grid td', 'table.Record td', 'td'];
                    
                    let allCells = [];
                    for (const selector of selectors) {
                        const cells = document.querySelectorAll(selector);
                        if (cells.length > 0) {
                            allCells = Array.from(cells);
                            break;
                        }
                    }
                    
                    for (const cell of allCells) {
                        const text = cell.textContent.trim();
                        if (text.includes(searchPattern)) {
                            const match = text.match(/-(\\d{1,3})$/);
                            if (match) {
                                documentNumbers.push(parseInt(match[1], 10));
                            }
                        }
                    }
                    
                    return {
                        found: documentNumbers.length > 0,
                        maxNumber: documentNumbers.length > 0 ? Math.max(...documentNumbers) : 0
                    };
                }
            """, search_pattern)
            
            if result and result.get('found'):
                return result.get('maxNumber', 0)
            return 0
            
        except Exception as e:
            logger.warning(f"Error consultando documento: {e}")
            return 0
    
    def get_last_document_sequence_via_search(self, prefix: str, fecha: str, operation_id: str = None, account_id: str = None) -> int:
        """Filtra por cuenta, operacion y fecha, luego busca el ultimo consecutivo."""
        try:
            # Si tenemos operation_id, filtrar primero
            if operation_id:
                success = self.filter_by_operation_and_date(operation_id, fecha, account_id)
                if not success:
                    logger.warning("No se pudo aplicar el filtro")
            
            # Buscar en la tabla
            return self.get_last_document_sequence(prefix, fecha)
            
        except Exception as e:
            logger.warning(f"Error en busqueda: {e}")
            return 0
    
    def update_document_sequences(self, records: List[Dict]) -> List[Dict]:
        """Actualiza los numeros de documento para continuar la numeracion."""
        if not records:
            return records
        
        logger.info("Actualizando secuencias de documentos desde Novohit...")
        
        # Agrupar registros por prefijo, fecha, operacion y cuenta
        groups = {}
        for record in records:
            no_document = record.get('no_document', '')
            fecha = record.get('dt_operation', '')
            operation_id = record.get('id_tp_operation', '')
            account_id = record.get('id_bnk_account', '')
            
            parts = no_document.split('-')
            if len(parts) >= 3:
                potential_date = parts[-2]
                if potential_date.isdigit() and len(potential_date) >= 6:
                    prefix = '-'.join(parts[:-2])
                    if len(potential_date) == 6:
                        fecha_doc = potential_date[:4] + "20" + potential_date[4:]
                    else:
                        fecha_doc = potential_date
                else:
                    prefix = '-'.join(parts[:-1])
                    fecha_doc = self._normalize_fecha(fecha)
                
                group_key = f"{prefix}_{fecha}_{operation_id}_{account_id}"
                if group_key not in groups:
                    groups[group_key] = {
                        'prefix': prefix,
                        'fecha': fecha,
                        'fecha_doc': fecha_doc,
                        'operation_id': operation_id,
                        'account_id': account_id,
                        'records': []
                    }
                groups[group_key]['records'].append(record)
        
        # Para cada grupo, consultar el ultimo consecutivo
        updated_count = 0
        for group_key, group_data in groups.items():
            prefix = group_data['prefix']
            fecha = group_data['fecha']
            fecha_doc = group_data['fecha_doc']
            operation_id = group_data['operation_id']
            account_id = group_data['account_id']
            group_records = group_data['records']
            
            logger.info(f"Grupo: {prefix} | Fecha: {fecha} | Operacion: {operation_id} | Cuenta: {account_id}")
            
            last_seq = self.get_last_document_sequence_via_search(prefix, fecha, operation_id, account_id)
            
            if last_seq > 0:
                logger.info(f"  Ultimo registrado: {last_seq}, Continuando desde: {last_seq + 1}")
                
                for i, record in enumerate(group_records, 1):
                    new_seq = last_seq + i
                    old_document = record['no_document']
                    fecha_doc_normalized = str(fecha_doc).zfill(8)[:8]
                    total_expected = last_seq + len(group_records)
                    width = 2 if total_expected <= 99 else 3
                    new_document = f"{prefix}-{fecha_doc_normalized}-{new_seq:0{width}d}"
                    
                    record['no_document'] = new_document
                    updated_count += 1
                    
                    logger.info(f"  {old_document} -> {new_document}")
            else:
                logger.info(f"  No hay registros previos, iniciando desde 01")
        
        logger.info(f"{updated_count} documentos actualizados")
        return records
            
    def process_record(self, record: Dict, config_loader=None) -> bool:
        """
        Procesa un registro completo: clic en +, llena, guarda y registra asiento contable.
        
        Args:
            record: Diccionario con los datos
            config_loader: Cargador de configuración para cuenta contable
            
        Returns:
            True si se procesó exitosamente
        """
        try:
            # PASO 1: Clic en botón '+' para abrir formulario
            if not self.click_add_button():
                return False
            
            # PASO 2: Llenar formulario principal
            if not self.fill_form(record):
                return False
            
            # PASO 3: Guardar operación bancaria
            if not self.submit_form():
                return False
            
            # PASO 4: Registrar asiento contable (segundo paso)
            logger.info("\n📋 Registrando asiento contable...")
            accounting_handler = AccountingEntryHandler(self.frame, self.page)
            accounting_result = accounting_handler.fill_accounting_entry(record, config_loader)
            
            if accounting_result:
                logger.info("✅ Asiento contable registrado exitosamente")
            else:
                logger.warning("⚠️ No se pudo registrar el asiento contable")
            
            # PASO 5: Navegar de nuevo al módulo para el siguiente registro
            # (El botón "Nuevo" borra el registro, así que reiniciamos el flujo completo)
            time.sleep(2)
            logger.info("🔄 Regresando al listado para siguiente registro...")
            self.navigate_to_bank_operations()
            
            return True
            
        except Exception as e:
            logger.error(f"Error procesando registro: {e}")
            return False
            
    def process_records(self, records: List[Dict], delay: int = 3, config_loader=None, auto_adjust_sequence: bool = True) -> Dict:
        """
        Procesa una lista de registros.
        
        Args:
            records: Lista de registros a procesar
            delay: Segundos de espera entre cada operación
            config_loader: Cargador de configuración para cuenta contable
            auto_adjust_sequence: Si es True, ajusta la numeración desde el último documento registrado
            
        Returns:
            Diccionario con estadísticas del procesamiento
        """
        # Ajustar secuencias de documentos antes de procesar
        if auto_adjust_sequence and records:
            logger.info("Verificando secuencias de documentos en Novohit...")
            records = self.update_document_sequences(records)
        
        results = {
            'total': len(records),
            'success': 0,
            'failed': 0,
            'errors': []
        }
        
        for i, record in enumerate(records, 1):
            logger.info(f"\n{'='*60}")
            logger.info(f"PROCESANDO REGISTRO {i}/{len(records)}")
            logger.info(f"{'='*60}")
            logger.info(f"Concepto: {record.get('notes', 'N/A')[:60]}...")
            monto = record.get('mn_operation') or record.get('mm_operation', 'N/A')
            logger.info(f"Monto: ${monto}")
            
            success = self.process_record(record, config_loader)
            
            if success:
                results['success'] += 1
                logger.info(f"✅ Registro {i} PROCESADO EXITOSAMENTE")
            else:
                results['failed'] += 1
                results['errors'].append({
                    'index': i,
                    'record': record,
                    'error': 'Error procesando registro'
                })
                logger.error(f"❌ ERROR en registro {i}")
                
                # Screenshot del error
                try:
                    self.page.screenshot(path=f"./debug_error_record_{i}.png")
                except:
                    pass
            
            # Pausa entre operaciones
            if i < len(records):
                logger.info(f"⏳ Esperando {delay} segundos...")
                time.sleep(delay)
        
        return results
        
    def close(self):
        """Cierra el navegador."""
        if self.context:
            self.context.close()
        if self.browser:
            self.browser.close()
        if hasattr(self, 'playwright'):
            self.playwright.stop()
        logger.info("Navegador cerrado")
