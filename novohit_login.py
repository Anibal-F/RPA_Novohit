"""
Script de automatización para login en Novohit ERP - Grupo Petroil
Modo DEBUG: Navegador visible para inspeccionar el flujo
"""
import os
from pathlib import Path
from dotenv import load_dotenv
from playwright.sync_api import sync_playwright, expect

# Cargar variables de entorno
env_path = Path(__file__).parent / ".env.Novohit"
load_dotenv(dotenv_path=env_path)

# Configuración desde .env
NOVOHIT_URL = os.getenv("NOVOHIT_URL")
NOVOHIT_USERNAME = os.getenv("NOVOHIT_USERNAME")
NOVOHIT_PASSWORD = os.getenv("NOVOHIT_PASSWORD")
NOVOHIT_USER_SELECTOR = os.getenv("NOVOHIT_USER_SELECTOR", "#s_username")
NOVOHIT_PASS_SELECTOR = os.getenv("NOVOHIT_PASS_SELECTOR", "#s_passwd")
NOVOHIT_LOGIN_SELECTOR = os.getenv("NOVOHIT_LOGIN_SELECTOR", "#btn-login")


def login_novohit():
    """
    Abre el navegador en modo visible y realiza el login en Novohit.
    Se mantiene abierto para debugging del flujo post-login.
    """
    # Validar que existan credenciales
    if not NOVOHIT_USERNAME or not NOVOHIT_PASSWORD:
        print("❌ Error: NOVOHIT_USERNAME y NOVOHIT_PASSWORD deben estar configurados en .env.Novohit")
        return

    with sync_playwright() as p:
        # Lanzar navegador en modo visible (headed) para debugging
        browser = p.chromium.launch(
            headless=False,  # Modo visible para debug
            slow_mo=100,     # Retardo entre acciones para visualizar mejor
            args=['--start-maximized']
        )
        
        context = browser.new_context(
            viewport={'width': 1920, 'height': 1080},
            record_video_dir="./videos"  # Grabar video del flujo
        )
        
        page = context.new_page()
        
        print(f"🌐 Navegando a: {NOVOHIT_URL}")
        page.goto(NOVOHIT_URL, wait_until="networkidle")
        
        # Esperar a que el formulario esté cargado
        print("⏳ Esperando formulario de login...")
        page.wait_for_selector(NOVOHIT_USER_SELECTOR, state="visible")
        
        # Completar usuario
        print(f"👤 Ingresando usuario: {NOVOHIT_USERNAME}")
        page.fill(NOVOHIT_USER_SELECTOR, NOVOHIT_USERNAME)
        
        # Completar contraseña
        print("🔒 Ingresando contraseña...")
        page.fill(NOVOHIT_PASS_SELECTOR, NOVOHIT_PASSWORD)
        
        # Click en botón login
        print("🔘 Clic en botón Login...")
        page.click(NOVOHIT_LOGIN_SELECTOR)
        
        # Esperar navegación post-login
        print("⏳ Esperando carga post-login...")
        page.wait_for_load_state("networkidle")
        
        # Verificar si el login fue exitoso (ajustar según la URL o elemento específico)
        current_url = page.url
        print(f"✅ Login completado. URL actual: {current_url}")
        
        # ===================================================================
        # NAVEGACIÓN POST-LOGIN: Administración → Tesorería → Operaciones Bancarias
        # ===================================================================
        print("\n📂 Navegando al menú Administración → Tesorería → Operaciones Bancarias...")
        
        # Screenshot para debug inicial
        page.screenshot(path="./debug_01_post_login.png")
        
        # 1. Clic en "Administración" (menú principal)
        print("   → Clic en Administración...")
        admin_menu = page.get_by_role("link", name="Administración").first
        admin_menu.click()
        page.wait_for_timeout(800)  # Esperar animación del menú
        page.screenshot(path="./debug_02_admin_open.png")
        
        # 2. Hover sobre "Tesorería" para mostrar su submenú flotante
        print("   → Hover en Tesorería (para abrir submenú)...")
        tesoreria_menu = page.get_by_role("link", name="Tesorería").first
        tesoreria_menu.hover()
        page.wait_for_timeout(800)  # Esperar a que aparezca el submenú
        page.screenshot(path="./debug_03_tesoreria_hover.png")
        
        # 3. Buscar y clic en "Operaciones Bancarias" en el submenú visible
        print("   → Buscando Operaciones Bancarias...")
        
        # Intentar múltiples selectores para mayor robustez
        operaciones_link = None
        
        # Opción 1: Por texto exacto
        try:
            operaciones_link = page.locator("a.x-menu-item:has-text('Operaciones Bancarias')").filter(
                visible=True
            ).first
            if operaciones_link.count() > 0:
                print("      ✓ Encontrado por texto")
        except:
            pass
        
        # Opción 2: Por href si el primero falla
        if not operaciones_link or operaciones_link.count() == 0:
            try:
                operaciones_link = page.locator('a[href*="bnk_operations.php"]').filter(
                    visible=True
                ).first
                if operaciones_link.count() > 0:
                    print("      ✓ Encontrado por href")
            except:
                pass
        
        # Opción 3: Buscar en cualquier menú visible
        if not operaciones_link or operaciones_link.count() == 0:
            try:
                operaciones_link = page.get_by_role("link", name="Operaciones Bancarias").filter(
                    visible=True
                ).first
                if operaciones_link.count() > 0:
                    print("      ✓ Encontrado por role")
            except:
                pass
        
        if operaciones_link and operaciones_link.count() > 0:
            print("   → Clic en Operaciones Bancarias...")
            operaciones_link.click()
        else:
            print("   ⚠️ No se encontró el enlace, intentando clic por coordenadas...")
            # Fallback: clic relativo al menú de Tesorería
            tesoreria_menu.click()
            page.wait_for_timeout(500)
        
        # Esperar navegación
        page.wait_for_load_state("networkidle")
        page.wait_for_timeout(1000)
        page.screenshot(path="./debug_04_operaciones_loaded.png")
        print(f"✅ Página actual: {page.url}")
        
        # ===================================================================
        # SCROLL HASTA ABAJO Y CLIC EN BOTÓN "+" (Insertar)
        # ===================================================================
        print("\n📜 Detectando iframes...")
        
        # Buscar todos los iframes en la página
        iframes = page.locator('iframe').all()
        print(f"   Iframes encontrados: {len(iframes)}")
        
        # El contenido probablemente está en el iframe llamado 'id_frame_app'
        frame = None
        try:
            frame = page.frame('id_frame_app')
            if frame:
                print("   ✓ Encontrado iframe 'id_frame_app'")
        except:
            pass
        
        # Si no, buscar el primer iframe con src
        if not frame and len(iframes) > 0:
            for i, iframe in enumerate(iframes):
                src = iframe.get_attribute('src')
                print(f"   Iframe [{i}] src={src}")
                if src and 'bnk_operations' in src:
                    import re
                    frame = page.frame({ 'url': re.compile(r'bnk_operations') })
                    print(f"   ✓ Usando iframe con bnk_operations")
                    break
        
        # Si aún no hay frame, intentar con el primer iframe
        if not frame and len(iframes) > 0:
            # Obtener el src del primer iframe
            first_src = iframes[0].get_attribute('src')
            if first_src:
                frame = page.frame({ 'url': first_src })
                print(f"   ✓ Usando primer iframe con src: {first_src}")
        
        # Si no hay iframe, usar la página principal
        if not frame:
            print("   ⚠️ No se encontró iframe, usando página principal")
            frame = page
        
        # Ahora trabajar con el frame
        print("\n📜 Haciendo scroll hasta abajo en el frame...")
        frame.evaluate("window.scrollTo(0, document.body.scrollHeight)")
        page.wait_for_timeout(1000)
        
        # Screenshot de la página principal
        page.screenshot(path="./debug_05_scrolled.png")
        
        # DEBUG: Buscar enlaces en el frame
        print("🔍 DEBUG: Buscando enlaces con 'is_ins_new' en el frame...")
        try:
            links = frame.locator('a[href*="is_ins_new"]').all()
            print(f"   Enlaces encontrados con 'is_ins_new': {len(links)}")
            for i, link in enumerate(links[:5]):
                try:
                    href = link.get_attribute('href')
                    visible = link.is_visible()
                    print(f"   [{i}] href={href}, visible={visible}")
                except:
                    pass
        except Exception as e:
            print(f"   Error buscando enlaces: {e}")
        
        # DEBUG: Buscar imágenes con icon_rec_ins
        print("🔍 DEBUG: Buscando imágenes 'icon_rec_ins.gif'...")
        try:
            images = frame.locator('img[src*="icon_rec_ins"]').all()
            print(f"   Imágenes 'icon_rec_ins' encontradas: {len(images)}")
            for i, img in enumerate(images):
                try:
                    src = img.get_attribute('src')
                    alt = img.get_attribute('alt')
                    visible = img.is_visible()
                    print(f"   [{i}] src={src}, alt={alt}, visible={visible}")
                except:
                    pass
        except Exception as e:
            print(f"   Error buscando imágenes: {e}")
        
        # Intentar clic en el botón "+"
        print("\n🔘 Intentando clic en botón '+'...")
        
        clic_exitoso = False
        
        # Estrategia 1: Clic directo en el enlace con is_ins_new=1
        try:
            print("   → Estrategia 1: Clic en enlace href con is_ins_new=1...")
            btn = frame.locator('a[href*="is_ins_new=1"]').first
            if btn.count() > 0:
                print("      ✓ Botón encontrado, haciendo clic...")
                btn.scroll_into_view_if_needed(timeout=5000)
                btn.click(timeout=5000)
                print("      ✓ Clic realizado")
                clic_exitoso = True
            else:
                print("      ✗ No se encontró el botón con is_ins_new=1")
        except Exception as e:
            print(f"      ✗ Error: {e}")
        
        # Estrategia 2: Buscar por la imagen icon_rec_ins
        if not clic_exitoso:
            try:
                print("   → Estrategia 2: Clic en imagen icon_rec_ins...")
                img = frame.locator('img[src*="icon_rec_ins"]').first
                if img.count() > 0:
                    print("      ✓ Imagen encontrada, haciendo clic...")
                    img.scroll_into_view_if_needed(timeout=5000)
                    img.click(timeout=5000)
                    print("      ✓ Clic realizado")
                    clic_exitoso = True
                else:
                    print("      ✗ No se encontró la imagen")
            except Exception as e:
                print(f"      ✗ Error: {e}")
        
        # Estrategia 3: JavaScript directo en el frame
        if not clic_exitoso:
            try:
                print("   → Estrategia 3: JavaScript click...")
                result = frame.evaluate("""
                    () => {
                        const link = document.querySelector('a[href*="is_ins_new=1"]');
                        if (link) {
                            link.scrollIntoView({behavior: 'instant', block: 'center'});
                            link.click();
                            return 'Clicked: ' + link.href;
                        }
                        const img = document.querySelector('img[src*="icon_rec_ins"]');
                        if (img && img.parentElement) {
                            img.parentElement.scrollIntoView({behavior: 'instant', block: 'center'});
                            img.parentElement.click();
                            return 'Clicked via parent: ' + img.parentElement.href;
                        }
                        return 'Not found';
                    }
                """)
                print(f"      Resultado: {result}")
                clic_exitoso = True
            except Exception as e:
                print(f"      ✗ Error: {e}")
        
        if clic_exitoso:
            page.wait_for_timeout(2000)
            print("   ✓ Esperando carga después del clic...")
        else:
            print("   ⚠️ No se pudo hacer clic en el botón")
        
        page.screenshot(path="./debug_06_final.png")
        print(f"\n✅ URL página: {page.url}")
        try:
            print(f"✅ URL frame: {frame.url}")
        except:
            pass
        
        # ===================================================================
        # MODO DEBUG - Inspección del flujo
        # ===================================================================
        print("\n" + "="*60)
        print("🔍 MODO DEBUG ACTIVO")
        print("="*60)
        print("Navegador listo para inspección.")
        print("Presiona ENTER en esta consola para cerrar el navegador...")
        print("="*60 + "\n")
        
        input()  # Espera input del usuario
        
        # Cerrar
        context.close()
        browser.close()
        print("👋 Navegador cerrado.")


if __name__ == "__main__":
    try:
        login_novohit()
    except KeyboardInterrupt:
        print("\n⚠️  Script interrumpido por el usuario.")
    except Exception as e:
        print(f"\n❌ Error durante la ejecución: {e}")
        raise
