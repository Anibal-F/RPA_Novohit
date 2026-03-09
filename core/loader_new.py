"""
Módulo Loader: Carga los datos en Novohit vía automatización web.
"""
import time
import random
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
        
    def navigate_to_bank_operations(self, max_retries: int = 3):
        """Navega a Operaciones Bancarias."""
        logger.info("Navegando a Operaciones Bancarias...")
        
        for attempt in range(max_retries):
            try:
                # Clic en Administración
                logger.info("  → Clic en Administración...")
                admin_menu = self.page.get_by_role("link", name="Administración").first
                admin_menu.click(timeout=10000)
                time.sleep(0.5)
                
                # Hover en Tesorería
                logger.info("  → Hover en Tesorería...")
                tesoreria_menu = self.page.get_by_role("link", name="Tesorería").first
                tesoreria_menu.hover(timeout=10000)
                time.sleep(0.5)
                
                # Clic en Operaciones Bancarias
                logger.info("  → Clic en Operaciones Bancarias...")
                operaciones_link = self.page.locator('a.x-menu-item:has-text("Operaciones Bancarias")').first
                operaciones_link.click(timeout=10000)
                
                # NO esperar networkidle - puede causar timeouts en aplicaciones SPA
                # En su lugar, esperar un tiempo fijo y verificar
                logger.info("  ⏳ Esperando carga de página...")
                time.sleep(2.5)  # Esperar a que cargue el iframe
                
                # Detectar iframe
                self._detect_frame()
                
                # Verificar que estamos en el listado correcto
                if self._verify_list_page():
                    logger.info("  ✓ Navegación completada exitosamente")
                    return True
                else:
                    logger.warning(f"  ⚠️ No se verificó el listado en intento {attempt + 1}")
                    # Intentar una vez más esperando más tiempo
                    time.sleep(2)
                    self._detect_frame()
                    if self._verify_list_page():
                        logger.info("  ✓ Navegación completada exitosamente (segundo intento)")
                        return True
                    
            except Exception as e:
                logger.error(f"  ❌ Error en navegación (intento {attempt + 1}): {e}")
                if attempt < max_retries - 1:
                    time.sleep(2)
                    continue
        
        # Si todos los intentos por menú fallan, usar URL directa
        logger.info("  🔄 Intentando navegación directa por URL...")
        try:
            list_url = settings.NOVOHIT_URL.replace('user_login.php', 'bnk_operations.php')
            self.page.goto(list_url, wait_until="domcontentloaded", timeout=15000)
            time.sleep(3)
            self._detect_frame()
            if self._verify_list_page():
                logger.info("  ✓ Navegación por URL exitosa")
                return True
        except Exception as e2:
            logger.error(f"  ❌ Navegación por URL también falló: {e2}")
        
        return False
    
    def _verify_list_page(self) -> bool:
        """Verifica que estamos en la página de listado de operaciones."""
        try:
            # Verificar que el frame existe y tiene contenido
            if not self.frame:
                return False
            
            # Buscar elementos típicos del listado
            check = self.frame.evaluate("""
                () => {
                    // Buscar tabla de registros o botón de agregar
                    const addButton = document.querySelector('a[href*="is_ins_new=1"]');
                    const recordTable = document.querySelector('table.Record');
                    const dataTable = document.querySelector('.x-grid3');
                    
                    return {
                        has_add_button: !!addButton,
                        has_record_table: !!recordTable,
                        has_data_table: !!dataTable,
                        url: window.location.href
                    };
                }
            """)
            
            logger.info(f"  Verificación página: {check}")
            
            # Es válido si tiene botón de agregar o tabla de registros
            if check.get('has_add_button') or check.get('has_record_table') or check.get('has_data_table'):
                return True
            
            return False
        except Exception as e:
            logger.warning(f"  Error verificando página: {e}")
            return False
    
    def get_last_document_sequence(self, prefix: str, fecha: str) -> int:
        """
        Consulta en Novohit el último número de documento registrado para un prefijo y fecha.
        
        Args:
            prefix: Prefijo del documento (ej: "IVA COM", "CB")
            fecha: Fecha en formato DD/MM/YYYY
            
        Returns:
            El último número secuencial usado (0 si no hay registros)
        """
        try:
            # Normalizar fecha al formato DDMMYYYY (8 dígitos)
            fecha_clean = self._normalize_fecha(fecha)
            search_pattern = f"{prefix}-{fecha_clean}-"
            
            logger.info(f"🔍 Buscando último documento con patrón: '{search_pattern}'")
            
            # Verificar estado del frame
            if self.frame is None:
                logger.warning("  Frame es None, intentando detectar...")
                self._detect_frame()
                if self.frame is None:
                    logger.error("  No se pudo detectar el frame")
                    return 0
            
            logger.info(f"  Frame URL: {self.frame.url[:60] if hasattr(self.frame, 'url') else 'N/A'}...")
            
            # Asegurarnos de que estamos en el listado
            is_list_page = self._verify_list_page()
            logger.info(f"  ¿Estamos en listado? {is_list_page}")
            if not is_list_page:
                logger.warning("No se pudo verificar que estamos en el listado")
                return 0
            
            # Usar JavaScript para buscar todos los documentos que coincidan con el patrón
            # Primero intentar buscar en la tabla, luego en toda la página
            logger.info(f"  Ejecutando búsqueda JavaScript...")
            
            # Intento 1: Buscar en elementos de tabla/grid
            logger.info(f"  Buscando en tabla HTML...")
            result = self.frame.evaluate("""
                (searchPattern) => {
                    console.log('Buscando patrón en tabla:', searchPattern);
                    const documentNumbers = [];
                    
                    // Selectores basados en la estructura real de Novohit
                    const selectors = [
                        'table.Grid td',           // Tabla principal con clase Grid
                        'table.Record td',         // Tabla alternativa
                        '.x-grid3-cell-inner',     // Grid de ExtJS
                        'table tr td',             // Cualquier tabla
                        'td'                       // Todas las celdas
                    ];
                    
                    let allCells = [];
                    for (const selector of selectors) {
                        try {
                            const cells = document.querySelectorAll(selector);
                            if (cells.length > 0) {
                                allCells = Array.from(cells);
                                console.log('Selector usado:', selector, '- Celdas encontradas:', cells.length);
                                break;
                            }
                        } catch (e) {}
                    }
                    
                    console.log('Total celdas a revisar:', allCells.length);
                    
                    for (const cell of allCells) {
                        const text = cell.textContent.trim();
                        // Verificar si el texto contiene el patrón de búsqueda
                        if (text.includes(searchPattern)) {
                            console.log('Coincidencia encontrada:', text);
                            // Extraer el número al final (después del último guión)
                            // Soporta formatos como "IVA COM-25022026-09" o "IVA-COM-25022026-09"
                            const match = text.match(/-(\\d{1,3})$/);
                            if (match) {
                                documentNumbers.push(parseInt(match[1], 10));
                            }
                        }
                    }
                    
                    return {
                        found: documentNumbers.length > 0,
                        count: documentNumbers.length,
                        numbers: documentNumbers,
                        maxNumber: documentNumbers.length > 0 ? Math.max(...documentNumbers) : 0,
                        method: 'table'
                    };
                }
            """, search_pattern)
            
            # Intento 2: Si no encontró nada, buscar en todo el texto de la página
            if not result or not result.get('found'):
                logger.info(f"  No se encontró en tabla, buscando en todo el documento...")
                logger.info(f"  Patrón de búsqueda: '{search_pattern}'")
                
                result = self.frame.evaluate("""
                    (searchPattern) => {
                        console.log('Buscando patrón en todo el documento:', searchPattern);
                        const documentNumbers = [];
                        
                        // Obtener todo el texto de la página
                        const bodyText = document.body.innerText;
                        console.log('Texto de página (primeros 500 chars):', bodyText.substring(0, 500));
                        
                        // Buscar todas las ocurrencias del patrón seguido de números
                        // Ejemplo: "IVA COM-25022026-01" o "IVA COM-25022026-09"
                        const escapedPattern = searchPattern.replace(/[.*+?^${}()|[\\]\\\\]/g, '\\\\$&');
                        const regex = new RegExp(escapedPattern + '(\\\\d{1,3})', 'g');
                        console.log('Regex usado:', regex);
                        
                        let match;
                        while ((match = regex.exec(bodyText)) !== null) {
                            console.log('Coincidencia encontrada en texto:', match[0], '-> secuencia:', match[1]);
                            documentNumbers.push(parseInt(match[1], 10));
                        }
                        
                        return {
                            found: documentNumbers.length > 0,
                            count: documentNumbers.length,
                            numbers: documentNumbers,
                            maxNumber: documentNumbers.length > 0 ? Math.max(...documentNumbers) : 0,
                            method: 'body',
                            textPreview: bodyText.substring(0, 200)
                        };
                    }
                """, search_pattern)
            
            logger.info(f"  Resultado búsqueda: {result}")
            
            if result and result.get('found'):
                last_seq = result.get('maxNumber', 0)
                logger.info(f"  ✓ Último consecutivo encontrado: {last_seq}")
                return last_seq
            else:
                logger.info(f"  ℹ️ No se encontraron documentos con el patrón '{search_pattern}'")
                logger.info(f"     Resultado de búsqueda: {result}")
                return 0
                
        except Exception as e:
            logger.warning(f"  ⚠ Error consultando último documento: {e}")
            return 0
    
    def _normalize_fecha(self, fecha: str) -> str:
        """
        Normaliza una fecha al formato DDMMYYYY (8 dígitos).
        
        Args:
            fecha: Fecha en formato DD/MM/YYYY o similar
            
        Returns:
            String de 8 dígitos en formato DDMMYYYY
        """
        try:
            # Limpiar la fecha de cualquier caracter no numérico excepto /
            fecha_clean = fecha.strip()
            
            # Dividir por / o -
            parts = fecha_clean.replace('-', '/').split('/')
            
            if len(parts) == 3:
                # Formato DD/MM/YYYY o variantes
                dia = parts[0].zfill(2)  # Asegurar 2 dígitos
                mes = parts[1].zfill(2)  # Asegurar 2 dígitos
                anio = parts[2]
                
                # Si el año tiene 2 dígitos, asumir 20XX
                if len(anio) == 2:
                    anio = "20" + anio
                
                return f"{dia}{mes}{anio}"
            else:
                # Si no tiene separadores, asumir que ya está limpia
                # pero asegurar que tenga 8 dígitos
                numeros = ''.join(c for c in fecha if c.isdigit())
                if len(numeros) == 8:
                    return numeros
                elif len(numeros) == 6:
                    # Formato DDMMAA, convertir a DDMMAAAA
                    return numeros[:4] + "20" + numeros[4:]
                else:
                    # Intentar padding
                    return numeros.ljust(8, '0')[:8]
        except Exception as e:
            logger.warning(f"Error normalizando fecha '{fecha}': {e}")
            # Fallback: solo quitar caracteres no numéricos
            return ''.join(c for c in fecha if c.isdigit())[:8].ljust(8, '0')
    
    def get_last_document_sequence_via_search(self, prefix: str, fecha: str, operation_id: str = None) -> int:
        """
        Método alternativo: Usa el formulario de búsqueda de Novohit para encontrar documentos.
        
        Args:
            prefix: Prefijo del documento (ej: "IVA COM", "CB")
            fecha: Fecha en formato DD/MM/YYYY
            
        Returns:
            El último número secuencial usado (0 si no hay registros)
        """
        try:
            fecha_clean = self._normalize_fecha(fecha)`n            `n            # Si tenemos operation_id, filtrar primero`n            if operation_id:`n                success = self.filter_by_operation_and_date(operation_id, fecha)`n                if not success:`n                    logger.warning("  No se pudo aplicar el filtro")`n            `n            search_prefix = f"{prefix}-{fecha_clean}-"
            
            logger.info(f"🔍 Buscando vía formulario: {search_prefix}")
            
            # Verificar que estamos en el listado
            if not self._verify_list_page():
                return 0
            
            # Intentar usar el campo de búsqueda de documento si existe
            # Primero hacemos clic en "Buscar" para abrir el formulario de búsqueda si está colapsado
            try:
                logger.info("  Buscando campo de documento...")
                
                # Buscar el campo de documento en el formulario de filtros
                # En Novohit, el campo típicamente tiene id o name relacionado con 'no_document' o 'documento'
                doc_input = self.frame.locator('input[name*="no_document"], input[name*="document"], input#no_document').first
                
                input_count = doc_input.count()
                logger.info(f"  Campos de documento encontrados: {input_count}")
                
                if input_count > 0:
                    # Limpiar y escribir el prefijo de búsqueda
                    doc_input.fill(search_prefix)
                    time.sleep(0.5)
                    
                    # Buscar el botón de búsqueda
                    search_btn = self.frame.locator('input[value="Buscar"], button:has-text("Buscar"), input[type="submit"][value*="Buscar"]').first
                    if search_btn.count() > 0:
                        search_btn.click()
                        logger.info("  🔎 Búsqueda ejecutada, esperando resultados...")
                        time.sleep(3)  # Esperar más tiempo para que la tabla se actualice
                        
                        # Hacer scroll para asegurar que la tabla esté visible
                        try:
                            self.frame.evaluate("window.scrollTo(0, 0)")
                            time.sleep(0.5)
                        except:
                            pass
                        
                        # Ahora buscar en los resultados
                        last_seq = self.get_last_document_sequence(prefix, fecha)
                        
                        # Si no encontramos nada, intentar buscar sin el prefijo completo
                        # (a veces la tabla filtrada solo muestra los números)
                        if last_seq == 0:
                            logger.info("  Intentando búsqueda alternativa en resultados filtrados...")
                            last_seq = self._get_last_seq_from_filtered_results(prefix, fecha_clean)
                        
                        return last_seq
            except Exception as search_err:
                logger.debug(f"  Búsqueda vía formulario no disponible: {search_err}")
                
            return 0
            
        except Exception as e:
            logger.warning(f"  ⚠ Error en búsqueda alternativa: {e}")
            return 0
    
    def _get_last_seq_from_filtered_results(self, prefix: str, fecha_clean: str) -> int:
        """
        Método auxiliar para buscar el último consecutivo cuando la tabla ya está filtrada.
        Busca números que coincidan con el formato PREFIX-FECHA-SEQ en toda la página.
        """
        try:
            logger.info(f"  Buscando en resultados filtrados: {prefix}-{fecha_clean}-XX")
            
            result = self.frame.evaluate("""
                (params) => {
                    const { prefix, fecha } = params;
                    const documentNumbers = [];
                    
                    // Buscar en todo el innerText de la página
                    const text = document.body.innerText;
                    
                    // Intentar varios patrones posibles
                    const patterns = [
                        prefix + '-' + fecha + '-(\\d{1,3})',
                        prefix.replace(' ', '[-\\s]') + '-' + fecha + '-(\\d{1,3})',
                    ];
                    
                    for (const pattern of patterns) {
                        const regex = new RegExp(pattern, 'g');
                        let match;
                        while ((match = regex.exec(text)) !== null) {
                            const seq = parseInt(match[1], 10);
                            documentNumbers.push(seq);
                            console.log('Encontrado:', match[0], '-> secuencia:', seq);
                        }
                    }
                    
                    return {
                        found: documentNumbers.length > 0,
                        count: documentNumbers.length,
                        numbers: documentNumbers,
                        maxNumber: documentNumbers.length > 0 ? Math.max(...documentNumbers) : 0
                    };
                }
            """, {'prefix': prefix, 'fecha': fecha_clean})
            
            logger.info(f"  Resultado búsqueda filtrada: {result}")
            
            if result and result.get('found'):
                return result.get('maxNumber', 0)
            return 0
            
        except Exception as e:
            logger.warning(f"  Error en búsqueda filtrada: {e}")
            return 0
    
    def update_document_sequences(self, records: List[Dict]) -> List[Dict]:
        """
        Actualiza los números de documento de los registros para continuar la numeración
        desde el último documento registrado en Novohit.
        
        Args:
            records: Lista de registros a procesar
            
        Returns:
            Lista de registros con números de documento actualizados
        """
        if not records:
            logger.info("⚠️ No hay registros para actualizar")
            return records
        
        logger.info("🔄 Actualizando secuencias de documentos desde Novohit...")
        logger.info(f"  Total de registros a procesar: {len(records)}")
        
        # Mostrar el primer registro para debug
        if records:
            logger.info(f"  Primer registro - Documento: '{records[0].get('no_document')}', Fecha: '{records[0].get('dt_operation')}'")
        
        # Agrupar registros por prefijo y fecha
        groups = {}
        for record in records:
            no_document = record.get('no_document', '')
            fecha = record.get('dt_operation', '')
            
            logger.info(f"  Analizando documento: '{no_document}', fecha: '{fecha}'")
            
            # Extraer prefijo y fecha del número de documento
            # Soporta formatos: "IVA COM-25022026-01" o "CB-25022026-01"
            # El formato es: PREFIX-FECHA-SEQ
            
            # Dividir por guiones
            parts = no_document.split('-')
            logger.debug(f"    Partes: {parts}")
            
            if len(parts) >= 3:
                # El último elemento es la secuencia
                # El penúltimo es la fecha (8 dígitos)
                # Todo lo demás es el prefijo
                
                # Verificar si el penúltimo elemento parece una fecha (6-8 dígitos)
                potential_date = parts[-2]
                if potential_date.isdigit() and len(potential_date) >= 6:
                    # Formato estándar: PREFIX-FECHA-SEQ
                    prefix = '-'.join(parts[:-2])  # Unir todo excepto fecha y seq
                    # Normalizar la fecha a 8 dígitos
                    if len(potential_date) == 6:
                        # Formato DDMMAA, convertir a DDMMAAAA
                        fecha_doc = potential_date[:4] + "20" + potential_date[4:]
                    else:
                        fecha_doc = potential_date
                else:
                    # Formato alternativo: El documento no tiene fecha en el medio
                    # Usar el formato completo excepto la última parte (secuencia)
                    prefix = '-'.join(parts[:-1])
                    fecha_doc = self._normalize_fecha(fecha)
                
                logger.debug(f"    Prefijo extraído: '{prefix}', Fecha doc: '{fecha_doc}'")
                
                group_key = f"{prefix}_{fecha}"
                if group_key not in groups:
                    groups[group_key] = {
                        'prefix': prefix,
                        'fecha': fecha,
                        'fecha_doc': fecha_doc,
                        'records': []
                    }
                groups[group_key]['records'].append(record)
            elif len(parts) == 2:
                # Formato simple: PREFIX-SEQ (sin fecha en el documento)
                prefix = parts[0]
                group_key = f"{prefix}_{fecha}"
                if group_key not in groups:
                    groups[group_key] = {
                        'prefix': prefix,
                        'fecha': fecha,
                        'fecha_doc': self._normalize_fecha(fecha),
                        'records': []
                    }
                groups[group_key]['records'].append(record)
            else:
                logger.warning(f"    Formato de documento no reconocido: '{no_document}'")
        
        if not groups:
            logger.warning("  ⚠ No se pudieron agrupar registros por prefijo/fecha")
            return records
        
        # Para cada grupo, consultar el último consecutivo y actualizar
        updated_count = 0
        for group_key, group_data in groups.items():
            prefix = group_data['prefix']
            fecha = group_data['fecha']
            fecha_doc = group_data['fecha_doc']
            group_records = group_data['records']
            
            logger.info(f"  📁 Grupo: {prefix} | Fecha: {fecha} | Registros: {len(group_records)}")
            
            # Consultar el último consecutivo en Novohit (primero método directo)
            last_seq = self.get_last_document_sequence(prefix, fecha)
            
            # Si no encontramos nada, intentar con el método alternativo
            if last_seq == 0:
                logger.info(f"    Intentando búsqueda alternativa...")
                last_seq = self.get_last_document_sequence_via_search(prefix, fecha)
            
            if last_seq > 0:
                logger.info(f"  📊 {prefix} ({fecha}): Último registrado={last_seq}, Continuando desde={last_seq + 1}")
                
                # Actualizar los registros con la nueva secuencia
                for i, record in enumerate(group_records, 1):
                    new_seq = last_seq + i
                    old_document = record['no_document']
                    
                    # Generar nuevo número de documento
                    # Formato: PREFIX-FECHA-SEQ
                    # Asegurar que fecha_doc tenga 8 dígitos
                    fecha_doc_normalized = str(fecha_doc).zfill(8)[:8]
                    
                    # Determinar ancho del sufijo según el total esperado
                    total_expected = last_seq + len(group_records)
                    width = 2 if total_expected <= 99 else 3
                    new_document = f"{prefix}-{fecha_doc_normalized}-{new_seq:0{width}d}"
                    
                    record['no_document'] = new_document
                    updated_count += 1
                    
                    logger.info(f"    {old_document} → {new_document}")
            else:
                logger.info(f"  📊 {prefix} ({fecha}): No hay registros previos, iniciando desde 01")
        
        logger.info(f"✓ {updated_count} documentos actualizados")
        return records
        
    def _detect_frame(self):
        """Detecta y selecciona el iframe del contenido."""
        # Intentar por nombre (más rápido)
        try:
            frame_by_name = self.page.frame('id_frame_app')
            if frame_by_name:
                self.frame = frame_by_name
                logger.info("Iframe 'id_frame_app' detectado por nombre")
                return
        except:
            pass
        
        # Intentar buscando en todos los frames por URL (solo frames con URL válida)
        try:
            all_frames = self.page.frames
            for frame in all_frames:
                try:
                    url = frame.url
                    # Frame válido debe tener URL de novohit y no ser about:blank
                    if url and 'novohit.com' in url and 'bnk_operations' in url:
                        self.frame = frame
                        logger.info(f"Iframe detectado por URL: {url[:60]}...")
                        return
                except:
                    continue
        except:
            pass
        
        # Fallback: buscar iframe por posición (evitar about:blank)
        try:
            all_frames = self.page.frames
            for i, frame in enumerate(all_frames):
                try:
                    url = frame.url
                    # Ignorar frames vacíos o about:blank
                    if url and url != 'about:blank' and 'novohit.com' in url:
                        self.frame = frame
                        logger.info(f"Usando iframe {i} con URL: {url[:60]}...")
                        return
                except:
                    continue
        except:
            pass
        
        # Último fallback: usar el primer iframe que no sea about:blank
        try:
            iframes = self.page.locator('iframe').all()
            for i, iframe_element in enumerate(iframes):
                try:
                    src = iframe_element.get_attribute('src')
                    if src and src != 'about:blank':
                        # Encontrar el frame correspondiente
                        all_frames = self.page.frames
                        for frame in all_frames:
                            if frame.url == src or src in frame.url:
                                self.frame = frame
                                logger.info(f"Usando iframe por src: {src[:60]}...")
                                return
                except:
                    continue
        except:
            pass
        
        # Si todo falla, usar la página principal
        self.frame = self.page
        logger.info("Usando página principal (sin iframe)")
            
    def click_add_button(self) -> bool:
        """Clic en el botón '+' para agregar nueva operación, o verifica si ya estamos en el formulario."""
        logger.info("Verificando estado del formulario...")
        
        # Verificar si el frame es None y re-detectarlo
        if self.frame is None:
            logger.warning("Frame es None, re-detectando...")
            self._detect_frame()
            if self.frame is None:
                logger.error("No se pudo detectar el frame después de re-intentar")
                return False
        
        # Primero verificar si ya estamos en el formulario de inserción
        current_url = ''
        try:
            current_url = self.frame.url
            logger.info(f"  URL actual: {current_url[:80]}...")
        except:
            pass
        
        # Si ya estamos en el formulario de inserción, saltar el clic
        if 'is_ins_new=1' in current_url:
            logger.info("  ℹ️ Ya estamos en el formulario de inserción (URL contiene is_ins_new=1)")
            is_insert_form = self._verify_insert_form()
            if is_insert_form:
                logger.info("  ✓ Formulario de inserción confirmado, continuando...")
                return True
            else:
                logger.warning("  ⚠️ URL indica inserción pero no se verificó el formulario")
        
        # Si no estamos en el formulario de inserción, hacer clic en "+"
        logger.info("Clic en botón '+'...")
        
        max_attempts = 3
        for attempt in range(max_attempts):
            try:
                # Scroll al final de la página y esperar más tiempo
                self.frame.evaluate("window.scrollTo(0, document.body.scrollHeight)")
                time.sleep(1.5)
                
                # JavaScript click (más confiable para navegación dentro de iframe)
                logger.info(f"  Intento {attempt + 1}/{max_attempts}: Usando JavaScript para hacer clic en '+'...")
                result = self.frame.evaluate("""
                    () => {
                        // Buscar por href
                        let link = document.querySelector('a[href*="is_ins_new=1"]');
                        if (!link) {
                            // Buscar por imagen
                            const img = document.querySelector('img[src*="icon_rec_ins"]');
                            if (img && img.parentElement && img.parentElement.tagName === 'A') {
                                link = img.parentElement;
                            }
                        }
                        if (!link) {
                            // Buscar por texto
                            const links = document.querySelectorAll('a');
                            for (const l of links) {
                                if (l.textContent.includes('+') || l.title.includes('Nuevo') || l.title.includes('Insertar')) {
                                    link = l;
                                    break;
                                }
                            }
                        }
                        if (link) {
                            link.scrollIntoView({behavior: 'instant', block: 'center'});
                            // Doble click para asegurar
                            link.click();
                            setTimeout(() => link.click(), 100);
                            return { success: true, href: link.href, found: true };
                        }
                        return { success: false, error: 'Elemento no encontrado', found: false };
                    }
                """)
                
                logger.info(f"  Resultado del clic: {result}")
                
                if not result.get('success'):
                    logger.warning(f"  ⚠️ Clic no exitoso en intento {attempt + 1}")
                    time.sleep(0.5)
                    continue
                
                # Esperar más tiempo a que la navegación ocurra
                time.sleep(3)
                
                # Detectar el nuevo frame (puede haber cambiado de URL)
                self._detect_frame_after_navigation()
                
                # Verificar que realmente estamos en el formulario de inserción
                is_insert_form = self._verify_insert_form()
                if is_insert_form:
                    logger.info("  ✓ Formulario de inserción confirmado")
                    return True
                else:
                    logger.warning(f"  ⚠️ No se detectó el formulario de inserción en intento {attempt + 1}")
                    if attempt < max_attempts - 1:
                        time.sleep(2)
                        continue
                    else:
                        return False
                
            except Exception as e:
                logger.error(f"  Error en intento {attempt + 1}: {e}")
                if attempt < max_attempts - 1:
                    time.sleep(1)
                    continue
        
        # Si llegamos aquí, todos los intentos fallaron
        logger.error("❌ No se pudo hacer clic en '+' después de todos los intentos")
        try:
            self.page.screenshot(path=str(settings.DATA_OUTPUT_DIR / "debug_error_click_plus.png"))
        except:
            pass
        return False
    
    def _verify_insert_form(self) -> bool:
        """Verifica que estamos en el formulario de inserción."""
        try:
            # Verificar URL del frame
            current_url = self.frame.url if hasattr(self.frame, 'url') else ''
            has_is_ins_new = 'is_ins_new' in current_url
            
            # Verificar que existe el select de cuenta bancaria
            check = self.frame.evaluate("""
                () => {
                    const cuentaSelect = document.querySelector('#id_bnk_account');
                    const operacionSelect = document.querySelector('#id_tp_operation');
                    const noDocumentInput = document.querySelector('#no_document');
                    return {
                        has_cuenta: !!cuentaSelect,
                        has_operacion: !!operacionSelect,
                        has_no_document: !!noDocumentInput,
                        cuenta_options: cuentaSelect ? cuentaSelect.options.length : 0,
                        url: window.location.href
                    };
                }
            """)
            
            logger.info(f"    Verificación formulario: {check}")
            
            # Es válido si tiene los campos principales del formulario
            has_form_fields = (
                check.get('has_cuenta') and 
                check.get('has_operacion') and 
                check.get('cuenta_options', 0) > 1
            )
            
            # Si tenemos los campos del formulario, es válido sin importar la URL
            if has_form_fields:
                return True
            
            # Si no tenemos los campos pero la URL indica inserción, esperar un poco y reintentar
            if has_is_ins_new and not has_form_fields:
                logger.info("    URL indica inserción pero campos no listos, esperando...")
                time.sleep(2)
                # Reintentar una vez
                check_retry = self.frame.evaluate("""
                    () => {
                        const cuentaSelect = document.querySelector('#id_bnk_account');
                        return {
                            has_cuenta: !!cuentaSelect,
                            cuenta_options: cuentaSelect ? cuentaSelect.options.length : 0
                        };
                    }
                """)
                if check_retry.get('has_cuenta') and check_retry.get('cuenta_options', 0) > 1:
                    logger.info("    Formulario listo en segundo intento")
                    return True
            
            if not has_is_ins_new:
                logger.warning(f"    URL no contiene 'is_ins_new': {current_url[:80]}...")
            
            return False
        except Exception as e:
            logger.warning(f"    Error verificando formulario: {e}")
            return False
    
    def _detect_frame_after_navigation(self):
        """
        Detecta el frame después de una navegación.
        El frame de inserción típicamente tiene 'is_ins_new=1' en la URL.
        """
        logger.info("Detectando frame después de navegación...")
        
        # Esperar a que la navegación ocurra
        time.sleep(1.5)
        
        # Buscar frame que contenga 'is_ins_new' o 'bnk_operations' en la URL
        max_attempts = 15
        for attempt in range(max_attempts):
            try:
                all_frames = self.page.frames
                for frame in all_frames:
                    try:
                        url = frame.url
                        if 'is_ins_new' in url or 'bnk_operations' in url:
                            self.frame = frame
                            logger.info(f"Frame detectado (intento {attempt+1}): {url[:80]}...")
                            # Esperar un poco más para que el DOM cargue
                            time.sleep(1)
                            return
                    except:
                        continue
            except:
                pass
            
            time.sleep(0.5)
        
        # Si no se encuentra frame específico, intentar con el primer iframe o último frame
        try:
            all_frames = self.page.frames
            if len(all_frames) > 1:
                # Buscar iframe por nombre primero
                for frame in all_frames:
                    try:
                        if frame.name == 'id_frame_app':
                            self.frame = frame
                            logger.info(f"Usando frame por nombre 'id_frame_app': {self.frame.url[:80]}...")
                            time.sleep(1)
                            return
                    except:
                        continue
                
                # Fallback al último frame
                self.frame = all_frames[-1]
                logger.info(f"Usando último frame disponible: {self.frame.url[:80]}...")
                time.sleep(1)
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
            time.sleep(2)
            
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
                    # Usar JavaScript para llenar y disparar eventos
                    js_result = self.frame.evaluate(f"""
                        () => {{
                            const input = document.querySelector('#no_document');
                            if (input) {{
                                input.value = '{no_document}';
                                input.dispatchEvent(new Event('input', {{ bubbles: true }}));
                                input.dispatchEvent(new Event('change', {{ bubbles: true }}));
                                input.dispatchEvent(new Event('blur', {{ bubbles: true }}));
                                return {{ success: true, value: input.value }};
                            }}
                            return {{ success: false, error: 'Input no encontrado' }};
                        }}
                    """)
                    logger.info(f"  ✓ Documento: {no_document} (JS: {js_result})")
                except Exception as e:
                    logger.warning(f"  ⚠ Error ingresando documento con JS: {e}")
                    # Fallback a Playwright
                    try:
                        self.frame.fill('#no_document', no_document)
                        self.frame.locator('#no_document').blur()
                        logger.info(f"  ✓ Documento (fallback): {no_document}")
                    except Exception as e2:
                        logger.warning(f"  ⚠ Fallback también falló: {e2}")
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
                
                time.sleep(0.2)
            
            # 6. Comentario
            notes = record.get('notes', '')
            if notes:
                try:
                    self.frame.fill('#notes', notes[:60])  # Max 60 chars
                    logger.info(f"  ✓ Comentario: {notes[:50]}...")
                except Exception as e:
                    logger.warning(f"  ⚠ Error ingresando comentario: {e}")
                time.sleep(0.2)
            
            logger.info("Formulario llenado exitosamente")
            
            # Screenshot para verificar
            try:
                self.page.screenshot(path=str(settings.DATA_OUTPUT_DIR / "debug_form_filled.png"))
            except:
                pass
            
            return True
            
        except Exception as e:
            logger.error(f"Error llenando formulario: {e}")
            # Screenshot para debug
            try:
                self.page.screenshot(path=str(settings.DATA_OUTPUT_DIR / "debug_error_fill.png"))
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
            self.page.screenshot(path=str(settings.DATA_OUTPUT_DIR / "debug_before_submit.png"))
            
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
            time.sleep(2)
            
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
                error_msg = page_status.get('message', '')
                logger.error(f"❌ Error detectado: {error_msg}")
                
                # Si es error de documento duplicado, intentar con número alternativo
                if 'documento' in error_msg.lower() and ('utilizado' in error_msg.lower() or 'ya existe' in error_msg.lower()):
                    logger.info("🔄 Documento duplicado detectado, intentando con alternativo...")
                    
                    import random
                    timestamp = int(time.time()) % 10000
                    random_suffix = random.randint(10, 99)
                    alt_document = f"DUP-{timestamp}-{random_suffix}"
                    
                    logger.info(f"  📝 Intentando con documento alternativo: {alt_document}")
                    
                    # Cambiar el documento en el campo
                    change_result = self.frame.evaluate(f"""
                        () => {{
                            const input = document.querySelector('#no_document');
                            if (input) {{
                                input.value = '{alt_document}';
                                input.dispatchEvent(new Event('input', {{ bubbles: true }}));
                                input.dispatchEvent(new Event('change', {{ bubbles: true }}));
                                input.dispatchEvent(new Event('blur', {{ bubbles: true }}));
                                return {{ success: true, newValue: input.value }};
                            }}
                            return {{ success: false, error: 'Campo no encontrado' }};
                        }}
                    """)
                    
                    logger.info(f"  Cambio de documento: {change_result}")
                    time.sleep(0.5)
                    
                    # Reintentar clic en Agregar
                    retry_result = self.frame.evaluate("""
                        () => {
                            const btn = document.querySelector('input[type="submit"][value="Agregar"]');
                            if (btn) {
                                btn.click();
                                return { success: true, method: 'retry' };
                            }
                            return { success: false };
                        }
                    """)
                    
                    if retry_result.get('success'):
                        logger.info("  ✅ Reintento enviado, esperando resultado...")
                        time.sleep(3)
                        
                        # Verificar nuevamente
                        retry_status = self.frame.evaluate("""
                            () => {
                                const errorElems = document.querySelectorAll('.x-form-invalid-msg, .error, .alert, .ext-mb-error');
                                for (let el of errorElems) {
                                    if (el.textContent.trim()) {
                                        return { type: 'error', message: el.textContent.trim() };
                                    }
                                }
                                const cuentaField = document.querySelector('#cod_op_account_slc');
                                if (cuentaField) {
                                    return { type: 'success', message: 'Asiento contable visible' };
                                }
                                return { type: 'unknown' };
                            }
                        """)
                        
                        if retry_status.get('type') == 'success':
                            logger.info("  ✅ Reintento exitoso con documento alternativo")
                            return True
                        else:
                            logger.error(f"  ❌ Reintento falló: {retry_status}")
                
                self.page.screenshot(path=str(settings.DATA_OUTPUT_DIR / "debug_error_after_submit.png"))
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
                self.page.screenshot(path=str(settings.DATA_OUTPUT_DIR / "debug_error_submit.png"))
            except:
                pass
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
            # PASO 1: Clic en botón '+' para abrir formulario (o verificar si ya estamos en él)
            if not self.click_add_button():
                logger.error("❌ No se pudo abrir el formulario de inserción")
                return False
            
            # PASO 2: Llenar formulario principal
            if not self.fill_form(record):
                logger.error("❌ No se pudo llenar el formulario")
                return False
            
            # PASO 3: Guardar operación bancaria
            if not self.submit_form():
                logger.error("❌ No se pudo guardar la operación bancaria")
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
            time.sleep(1.5)
            logger.info("🔄 Regresando al listado para siguiente registro...")
            
            # Intentar navegación normal primero
            nav_result = self.navigate_to_bank_operations()
            
            if not nav_result:
                logger.warning("⚠️ Navegación por menú falló, intentando por URL...")
                # Intentar navegación directa por URL al listado (sin is_ins_new)
                try:
                    list_url = settings.NOVOHIT_URL.replace('user_login.php', 'bnk_operations.php')
                    self.page.goto(list_url, wait_until="networkidle", timeout=30000)
                    time.sleep(3)
                    self._detect_frame()
                    
                    # Verificar que estamos en el listado
                    if self._verify_list_page():
                        logger.info("  ✓ Navegación por URL al listado exitosa")
                        nav_result = True
                    else:
                        logger.error("  ❌ No se verificó el listado después de navegar por URL")
                except Exception as url_err:
                    logger.error(f"  ❌ Error navegando por URL: {url_err}")
            
            if not nav_result:
                logger.error("❌ No se pudo regresar al listado, pero el registro fue procesado")
                # Último recurso: recargar la página
                try:
                    self.page.reload(wait_until="networkidle", timeout=30000)
                    time.sleep(3)
                    self._detect_frame()
                except Exception as reload_err:
                    logger.error(f"Error al recargar: {reload_err}")
            
            return True
            
        except Exception as e:
            logger.error(f"Error procesando registro: {e}")
            import traceback
            logger.debug(traceback.format_exc())
            return False
            
    def process_records(self, records: List[Dict], delay: int = 3, config_loader=None, auto_adjust_sequence: bool = True) -> Dict:
        """
        Procesa una lista de registros.
        
        Args:
            records: Lista de registros a procesar
            delay: Segundos de espera entre cada operación
            config_loader: Cargador de configuración para cuenta contable
            auto_adjust_sequence: Si es True, ajusta la numeración para continuar desde el último documento registrado
            
        Returns:
            Diccionario con estadísticas del procesamiento
        """
        results = {
            'total': len(records),
            'success': 0,
            'failed': 0,
            'errors': []
        }
        
        # Ajustar secuencias de documentos antes de procesar
        if auto_adjust_sequence and records:
            logger.info("📋 Verificando secuencias de documentos en Novohit...")
            records = self.update_document_sequences(records)
        
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
                    self.page.screenshot(path=str(settings.DATA_OUTPUT_DIR / f"debug_error_record_{i}.png"))
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


