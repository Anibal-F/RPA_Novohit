"""
GUI para RPA Novohit - Interfaz gráfica de usuario
"""
import tkinter as tk
from tkinter import ttk, filedialog, messagebox, scrolledtext
import threading
import os
import sys
from pathlib import Path
from datetime import datetime

# Agregar el directorio raíz al path
sys.path.insert(0, str(Path(__file__).parent))

from core.extractor import BankStatementExtractor
from core.transformer import NovohitTransformer
from core.loader import NovohitLoader
from core.concept_manager import open_concept_manager
from config import settings


class ScrollableFrame(ttk.Frame):
    """Frame que soporta scroll vertical y se adapta horizontalmente"""
    def __init__(self, container, *args, **kwargs):
        super().__init__(container, *args, **kwargs)
        
        # Crear canvas y scrollbar
        self.canvas = tk.Canvas(self, highlightthickness=0)
        self.scrollbar = ttk.Scrollbar(self, orient="vertical", command=self.canvas.yview)
        self.scrollable_frame = ttk.Frame(self.canvas, padding="20")
        
        # Crear ventana en el canvas que se redimensione horizontalmente
        self.canvas_window = self.canvas.create_window((0, 0), window=self.scrollable_frame, anchor="nw", tags="frame")
        
        # Configurar scrollregion cuando cambie el tamaño del frame
        self.scrollable_frame.bind(
            "<Configure>",
            self._on_frame_configure
        )
        
        # Configurar ancho del canvas cuando cambie el tamaño del contenedor
        self.bind("<Configure>", self._on_canvas_configure)
        
        self.canvas.configure(yscrollcommand=self.scrollbar.set)
        
        # Empaquetar
        self.canvas.pack(side="left", fill="both", expand=True)
        self.scrollbar.pack(side="right", fill="y")
        
        # Bind mousewheel
        self.bind_mousewheel()
        
    def _on_frame_configure(self, event=None):
        """Actualizar scrollregion cuando cambia el frame interior"""
        self.canvas.configure(scrollregion=self.canvas.bbox("all"))
        
    def _on_canvas_configure(self, event):
        """Redimensionar el frame interior al ancho del canvas"""
        canvas_width = event.width
        self.canvas.itemconfig(self.canvas_window, width=canvas_width)
        
    def bind_mousewheel(self):
        """Configurar scroll con rueda del mouse"""
        def _on_mousewheel(event):
            self.canvas.yview_scroll(int(-1*(event.delta/120)), "units")
        self.canvas.bind_all("<MouseWheel>", _on_mousewheel)


class RPAGUI:
    def __init__(self, root):
        self.root = root
        self.root.title("RPA Novohit - Contabilización Bancaria")
        self.root.geometry("900x700")
        self.root.minsize(800, 600)
        self.root.resizable(True, True)
        
        # Variables
        self.file_path = tk.StringVar(value="data/input/estado_cuenta.xlsx")
        self.strict_mode = tk.BooleanVar(value=True)
        self.is_running = False
        self.thread = None
        self.total_records = 0
        self.current_record = 0
        self.success_count = 0
        self.failed_count = 0
        
        # Estilos
        self.setup_styles()
        
        # Crear widgets
        self.create_widgets()
        
        # Log inicial
        self.log("RPA Novohit iniciado")
        self.log(f"Versión: 1.0")
        self.log("")
        
    def setup_styles(self):
        """Configurar estilos personalizados"""
        style = ttk.Style()
        
        # Colores
        self.primary_color = '#2563eb'
        self.success_color = '#16a34a'
        self.warning_color = '#f59e0b'
        self.danger_color = '#dc2626'
        self.bg_color = '#f3f4f6'
        
    def create_widgets(self):
        """Crear todos los widgets de la interfaz"""
        # Frame scrollable principal
        scroll_frame = ScrollableFrame(self.root)
        scroll_frame.pack(fill="both", expand=True)
        
        # Obtener el frame interno donde colocar todo
        main_frame = scroll_frame.scrollable_frame
        
        # Configurar grid del frame interno
        main_frame.columnconfigure(1, weight=1)
        
        # ========== TÍTULO ==========
        title_label = ttk.Label(
            main_frame,
            text="🏦 RPA Novohit - Contabilización Bancaria",
            font=('Segoe UI', 18, 'bold')
        )
        title_label.grid(row=0, column=0, columnspan=3, pady=(0, 20))
        
        # ========== SECCIÓN DE ARCHIVO ==========
        file_frame = ttk.LabelFrame(main_frame, text="📁 Archivo de Entrada", padding="10")
        file_frame.grid(row=1, column=0, columnspan=3, sticky=(tk.W, tk.E), pady=(0, 10))
        file_frame.columnconfigure(0, weight=1)
        
        self.file_entry = ttk.Entry(
            file_frame,
            textvariable=self.file_path,
            font=('Segoe UI', 10),
            state='readonly'
        )
        self.file_entry.grid(row=0, column=0, sticky=(tk.W, tk.E), padx=(0, 10))
        
        browse_btn = ttk.Button(
            file_frame,
            text="📂 Examinar...",
            command=self.browse_file
        )
        browse_btn.grid(row=0, column=1)
        
        # ========== OPCIONES DE PROCESAMIENTO ==========
        options_frame = ttk.LabelFrame(main_frame, text="⚙️ Modo de Procesamiento", padding="10")
        options_frame.grid(row=2, column=0, columnspan=3, sticky=(tk.W, tk.E), pady=(0, 10))
        
        # Variable para el texto dinámico
        self.mode_text = tk.StringVar()
        self._update_mode_text()
        
        # Checkbox para modo estricto
        self.strict_checkbox = ttk.Checkbutton(
            options_frame,
            text="Modo Estricto: Solo procesar conceptos definidos en el diccionario",
            variable=self.strict_mode,
            command=self._update_mode_text
        )
        self.strict_checkbox.grid(row=0, column=0, sticky=tk.W)
        
        # Label dinámico
        self.mode_label = ttk.Label(
            options_frame,
            textvariable=self.mode_text,
            font=('Segoe UI', 9, 'italic'),
            foreground='#2563eb'
        )
        self.mode_label.grid(row=1, column=0, sticky=tk.W, pady=(5, 0))
        
        # Tooltip
        tooltip_label = ttk.Label(
            options_frame,
            text="💡 Modo Automático: Detecta COMISIONES, IVA, DESCUENTOS | Excluye: VENTAS, ABONOS, DEPÓSITOS",
            font=('Segoe UI', 8),
            foreground='#6b7280'
        )
        tooltip_label.grid(row=2, column=0, sticky=tk.W, pady=(5, 0))
        
        # ========== ESTADÍSTICAS ==========
        stats_frame = ttk.LabelFrame(main_frame, text="📊 Estadísticas", padding="15")
        stats_frame.grid(row=3, column=0, columnspan=3, sticky=(tk.W, tk.E), pady=(0, 15))
        
        for i in range(4):
            stats_frame.columnconfigure(i, weight=1)
        
        self.stat_total_label = self.create_stat_card(stats_frame, "Total Registros", "0", 0)
        self.stat_current_label = self.create_stat_card(stats_frame, "Procesando", "-", 1)
        self.stat_success_label = self.create_stat_card(stats_frame, "✓ Exitosos", "0", 2)
        self.stat_failed_label = self.create_stat_card(stats_frame, "✗ Fallidos", "0", 3)
        
        ttk.Separator(stats_frame, orient='horizontal').grid(row=1, column=0, columnspan=4, sticky=(tk.W, tk.E), pady=10)
        
        ttk.Label(stats_frame, text="Monto Total Comisiones:", font=('Segoe UI', 10)).grid(row=2, column=0, sticky=tk.W)
        self.monto_comisiones_label = ttk.Label(stats_frame, text="$0.00", font=('Segoe UI', 10, 'bold'))
        self.monto_comisiones_label.grid(row=2, column=1, sticky=tk.W)
        
        ttk.Label(stats_frame, text="Monto Total IVA:", font=('Segoe UI', 10)).grid(row=2, column=2, sticky=tk.W)
        self.monto_iva_label = ttk.Label(stats_frame, text="$0.00", font=('Segoe UI', 10, 'bold'))
        self.monto_iva_label.grid(row=2, column=3, sticky=tk.W)
        
        # ========== PROGRESO ==========
        progress_frame = ttk.LabelFrame(main_frame, text="⏳ Progreso", padding="10")
        progress_frame.grid(row=4, column=0, columnspan=3, sticky=(tk.W, tk.E), pady=(0, 15))
        progress_frame.columnconfigure(0, weight=1)
        
        self.progress_var = tk.DoubleVar(value=0)
        self.progress_bar = ttk.Progressbar(
            progress_frame,
            variable=self.progress_var,
            maximum=100,
            mode='determinate',
            length=400
        )
        self.progress_bar.grid(row=0, column=0, sticky=(tk.W, tk.E), padx=(0, 10))
        
        self.progress_label = ttk.Label(progress_frame, text="0%", font=('Segoe UI', 10, 'bold'))
        self.progress_label.grid(row=0, column=1)
        
        self.status_label = ttk.Label(
            progress_frame,
            text="Listo para iniciar",
            font=('Segoe UI', 9),
            foreground='#6b7280'
        )
        self.status_label.grid(row=1, column=0, columnspan=2, sticky=tk.W, pady=(5, 0))
        
        # ========== BOTONES ==========
        buttons_frame = ttk.Frame(main_frame)
        buttons_frame.grid(row=5, column=0, columnspan=3, pady=(0, 15))
        
        # Botón INICIAR (tk.Button para mejor control de colores)
        self.start_btn = tk.Button(
            buttons_frame,
            text="▶ INICIAR PROCESO",
            command=self.start_process,
            bg='#22c55e',
            fg='white',
            activebackground='#16a34a',
            activeforeground='white',
            font=('Segoe UI', 10, 'bold'),
            width=20,
            cursor='hand2',
            relief=tk.FLAT,
            padx=10,
            pady=5
        )
        self.start_btn.pack(side=tk.LEFT, padx=(0, 10))
        
        # Botón DETENER
        self.stop_btn = tk.Button(
            buttons_frame,
            text="⏹ DETENER",
            command=self.stop_process,
            bg='#ef4444',
            fg='white',
            disabledforeground='white',
            activebackground='#dc2626',
            activeforeground='white',
            font=('Segoe UI', 10, 'bold'),
            width=15,
            state='disabled',
            cursor='hand2',
            relief=tk.FLAT,
            padx=10,
            pady=5
        )
        self.stop_btn.pack(side=tk.LEFT, padx=(0, 10))
        
        # Botones secundarios (ttk.Button)
        ttk.Button(
            buttons_frame,
            text="📂 Abrir Carpeta de Reportes",
            command=self.open_output_folder,
            width=25
        ).pack(side=tk.LEFT, padx=(0, 10))
        
        ttk.Button(
            buttons_frame,
            text="⚙️ Gestionar Conceptos",
            command=lambda: open_concept_manager(self.root),
            width=20
        ).pack(side=tk.LEFT)
        
        # ========== LOG ==========
        log_frame = ttk.LabelFrame(main_frame, text="📝 Registro de Actividad", padding="10")
        log_frame.grid(row=6, column=0, columnspan=3, sticky=(tk.W, tk.E), pady=(0, 10))
        log_frame.columnconfigure(0, weight=1)
        
        self.log_text = scrolledtext.ScrolledText(
            log_frame,
            wrap=tk.WORD,
            font=('Consolas', 9),
            height=12,
            state='disabled',
            bg='#1e1e1e',
            fg='#d4d4d4',
            insertbackground='white'
        )
        self.log_text.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        
        # Configurar tags para colores en el log
        self.log_text.tag_configure('success', foreground='#4ade80')
        self.log_text.tag_configure('error', foreground='#f87171')
        self.log_text.tag_configure('warning', foreground='#fbbf24')
        self.log_text.tag_configure('info', foreground='#60a5fa')
        
        # Footer
        footer = ttk.Label(
            main_frame,
            text="RPA Novohit v1.0 | Desarrollado por Aníbal Fuentes | Procesos 2026",
            font=('Segoe UI', 8),
            foreground='#9ca3af'
        )
        footer.grid(row=7, column=0, columnspan=3, pady=(10, 0))
    
    def create_stat_card(self, parent, title, value, column):
        """Crear una tarjeta de estadística"""
        frame = ttk.Frame(parent)
        frame.grid(row=0, column=column, padx=10, pady=5)
        
        ttk.Label(frame, text=title, font=('Segoe UI', 10)).pack()
        label = ttk.Label(frame, text=value, font=('Segoe UI', 24, 'bold'))
        label.pack()
        
        return label
    
    def browse_file(self):
        """Abrir diálogo para seleccionar archivo"""
        filename = filedialog.askopenfilename(
            title="Seleccionar archivo de estado de cuenta",
            filetypes=[
                ("Archivos Excel", "*.xlsx"),
                ("Archivos Excel 97-2003", "*.xls"),
                ("Todos los archivos", "*.*")
            ],
            initialdir="data/input" if os.path.exists("data/input") else "."
        )
        if filename:
            self.file_path.set(filename)
            self.log(f"Archivo seleccionado: {filename}")
    
    def _update_mode_text(self):
        """Actualiza el texto descriptivo según el modo"""
        if self.strict_mode.get():
            self.mode_text.set("🎯 Solo se procesarán conceptos definidos explícitamente en el diccionario")
        else:
            self.mode_text.set("🤖 Detección automática: Comisiones, IVA, Descuentos | Excluye: Ventas, Abonos")
    
    def log(self, message, tag=None):
        """Agregar mensaje al log"""
        timestamp = datetime.now().strftime("%H:%M:%S")
        self.log_text.configure(state='normal')
        self.log_text.insert(tk.END, f"[{timestamp}] {message}\n", tag)
        self.log_text.see(tk.END)
        self.log_text.configure(state='disabled')
    
    def update_stats(self, current=None, success=None, failed=None, total=None):
        """Actualizar estadísticas"""
        if total is not None:
            self.stat_total_label.config(text=str(total))
        if current is not None:
            self.stat_current_label.config(text=str(current))
        if success is not None:
            self.stat_success_label.config(text=str(success))
        if failed is not None:
            self.stat_failed_label.config(text=str(failed))
        
        self.root.update_idletasks()
    
    def update_progress(self, value, status_text=None):
        """Actualizar barra de progreso"""
        self.progress_var.set(value)
        self.progress_label.config(text=f"{int(value)}%")
        if status_text:
            self.status_label.config(text=status_text)
        self.root.update_idletasks()
    
    def update_status(self, text, color=None):
        """Actualizar texto de estado"""
        self.status_label.config(text=text)
        if color:
            self.status_label.config(foreground=color)
        self.root.update_idletasks()
    
    def open_output_folder(self):
        """Abrir carpeta de reportes"""
        output_dir = Path("data/output")
        if output_dir.exists():
            if sys.platform == 'win32':
                os.startfile(output_dir)
            else:
                import subprocess
                subprocess.call(['open', output_dir])
        else:
            messagebox.showwarning("Carpeta no encontrada", "La carpeta de reportes no existe aún.")
    
    def start_process(self):
        """Iniciar procesamiento"""
        if not os.path.exists(self.file_path.get()):
            messagebox.showerror(
                "Error",
                f"No se encontró el archivo:\n{self.file_path.get()}"
            )
            return
        
        self.is_running = True
        self.start_btn.config(state='disabled')
        self.stop_btn.config(state='normal')
        
        # Limpiar log anterior
        self.log_text.configure(state='normal')
        self.log_text.delete(1.0, tk.END)
        self.log_text.configure(state='disabled')
        
        self.thread = threading.Thread(target=self.run_rpa, daemon=True)
        self.thread.start()
    
    def stop_process(self):
        """Detener procesamiento"""
        self.is_running = False
        self.update_status("Proceso detenido por el usuario", self.warning_color)
        self.log("⚠️ Proceso detenido por el usuario", 'warning')
    
    def run_rpa(self):
        """Ejecutar el RPA en segundo plano"""
        try:
            self.update_status("Cargando configuración...", self.primary_color)
            self.log("⚙️ Cargando configuración...")
            
            from core.config_loader import ExcelConfigLoader
            config_loader = ExcelConfigLoader(self.file_path.get())
            config_loader.load_config()
            
            bank_name = config_loader.get_bank_name()
            if bank_name:
                self.log(f"✓ Banco configurado en Excel (B1): {bank_name}")
            else:
                self.log("ℹ️ No se configuró banco en Excel (B1), detectando por nombre de archivo...")
            
            modo_texto = "ESTRICTO" if self.strict_mode.get() else "AUTOMÁTICO"
            self.log(f"🔧 Modo de procesamiento: {modo_texto}")
            
            self.update_status("Extrayendo datos del Excel...", self.primary_color)
            self.log("📥 Extrayendo datos del Excel...")
            
            extractor = BankStatementExtractor(
                self.file_path.get(), 
                bank_name=bank_name, 
                strict_mode=self.strict_mode.get()
            )
            df = extractor.read_excel()
            records = extractor.extract_commissions_and_iva()
            
            if not records:
                self.log("⚠️ No se encontraron registros para procesar")
                self.update_status("Sin registros para procesar", self.warning_color)
                return
            
            summary = extractor.get_summary()
            self.log(f"📊 Banco: {summary['banco']}")
            self.log(f"📊 Total registros: {summary['total_registros']}")
            self.log(f"📊 Total cargos: ${summary['total_cargos']:,.2f}")
            self.log(f"📊 Total abonos: ${summary['total_abonos']:,.2f}")
            self.log(f"📊 Registros de comisiones/IVA: {len(records)}")
            self.log("")
            
            self.update_stats(total=len(records))
            
            self.update_status("Transformando datos...", self.primary_color)
            self.log("🔄 Transformando datos...")
            
            transformer = NovohitTransformer(
                bank_name=extractor.bank_name,
                excel_file=self.file_path.get()
            )
            novohit_records = transformer.transform_records(records)
            valid_records = [r for r in novohit_records if transformer.validate_record(r)]
            
            processing_summary = transformer.get_processing_summary(valid_records)
            self.monto_comisiones_label.config(text=f"${processing_summary['monto_comisiones']:,.2f}")
            self.monto_iva_label.config(text=f"${processing_summary['monto_iva']:,.2f}")
            
            self.log(f"✓ Registros válidos: {len(valid_records)}")
            self.log(f"✓ Comisiones: {processing_summary['total_comisiones']} registros, ${processing_summary['monto_comisiones']:,.2f}")
            self.log(f"✓ IVA: {processing_summary['total_iva']} registros, ${processing_summary['monto_iva']:,.2f}")
            self.log("")
            
            self.update_status("Cargando en Novohit...", self.primary_color)
            self.log("🚀 Cargando datos en Novohit...")
            self.log("")
            self.log("=" * 50)
            self.log("⚠️  INSTRUCCIONES IMPORTANTES:")
            self.log("   1. NO cierre la ventana del navegador")
            self.log("   2. NO mueva el mouse")
            self.log("   3. NO use el teclado")
            self.log("   4. NO haga clic en ninguna parte")
            self.log("   5. Espere hasta que termine completamente")
            self.log("=" * 50)
            self.log("")
            
            # Procesar con NovohitLoader
            with NovohitLoader(headless=False) as loader:
                self.log("✓ Sesión iniciada correctamente", 'success')
                self.log("")
                
                # Navegar a Operaciones Bancarias
                self.log("🧭 Navegando a Operaciones Bancarias...")
                if not loader.navigate_to_bank_operations():
                    self.log("❌ Error: No se pudo navegar a Operaciones Bancarias", 'error')
                    self.update_status("Error de navegación", self.danger_color)
                    return
                self.log("✓ Navegación completada", 'success')
                self.log("")
                
                # Ajustar secuencias de documentos para continuar desde el último registrado
                self.log("🔍 Verificando últimos consecutivos registrados en Novohit...")
                valid_records = loader.update_document_sequences(valid_records)
                self.log("")
                
                total = len(valid_records)
                for idx, record in enumerate(valid_records, 1):
                    if not self.is_running:
                        break
                    
                    self.current_record = idx
                    self.update_stats(current=idx)
                    self.update_progress((idx / total) * 100, f"Procesando registro {idx}/{total}")
                    
                    doc_num = record.get('no_document', 'N/A')
                    self.log(f"[{idx}/{total}] {record.get('notes', 'Sin descripción')[:50]}... - ${float(record.get('monto', 0)):,.2f} [Doc: {doc_num}]")
                    
                    success = loader.process_record(record, transformer.config_loader)
                    
                    if success:
                        self.success_count += 1
                        self.update_stats(success=self.success_count)
                        self.log(f"  ✅ Registro {idx} procesado exitosamente", 'success')
                    else:
                        self.failed_count += 1
                        self.update_stats(failed=self.failed_count)
                        self.log(f"  ❌ Error en registro {idx}", 'error')
                    
                    self.log("")
                
                self.update_progress(100, "Proceso completado")
                
                self.log("=" * 50)
                self.log("📊 RESUMEN FINAL:")
                self.log(f"   Total registros: {total}")
                self.log(f"   ✅ Exitosos: {self.success_count}", 'success')
                self.log(f"   ❌ Fallidos: {self.failed_count}", 'error')
                self.log(f"   📁 Reportes guardados en: data/output/", 'info')
                self.log("=" * 50)
                
                self.update_status("Proceso completado", self.success_color)
                
        except Exception as e:
            self.log(f"❌ Error: {str(e)}", 'error')
            self.update_status(f"Error: {str(e)}", self.danger_color)
            import traceback
            self.log(traceback.format_exc(), 'error')
        
        finally:
            self.is_running = False
            self.start_btn.config(state='normal')
            self.stop_btn.config(state='disabled')


def main():
    """Función principal"""
    root = tk.Tk()
    app = RPAGUI(root)
    root.mainloop()


if __name__ == "__main__":
    main()
