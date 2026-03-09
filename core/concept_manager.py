"""
Ventana de gestion de conceptos bancarios para el GUI.
Permite agregar, editar y eliminar conceptos del diccionario.
"""
import tkinter as tk
from tkinter import ttk, messagebox, simpledialog
from typing import Optional

from config.bank_mappings import (
    load_bank_mappings, save_bank_mappings, 
    get_all_banks, add_mapping, delete_mapping,
    CONCEPTS_DIR
)


class ConceptManagerWindow:
    """
    Ventana para gestionar conceptos bancarios.
    """
    
    def __init__(self, parent: tk.Tk):
        self.parent = parent
        self.window = tk.Toplevel(parent)
        self.window.title("Gestionar Conceptos Bancarios")
        self.window.geometry("900x600")
        self.window.minsize(800, 500)
        
        # Variables
        self.current_bank = tk.StringVar(value="BBVA")
        self.mappings = {}
        
        self._create_ui()
        self._load_mappings()
        
        # Centrar ventana
        self.window.transient(parent)
        self.window.grab_set()
        
    def _create_ui(self):
        """Crea la interfaz de usuario."""
        # Frame superior - Seleccion de banco
        top_frame = tk.Frame(self.window, padx=10, pady=10)
        top_frame.pack(fill=tk.X)
        
        tk.Label(top_frame, text="Banco:", font=("Arial", 10, "bold")).pack(side=tk.LEFT, padx=(0, 5))
        
        banks = get_all_banks() or ["BBVA", "BANORTE", "BANREGIO"]
        bank_combo = ttk.Combobox(top_frame, textvariable=self.current_bank, 
                                  values=banks, state="readonly", width=20)
        bank_combo.pack(side=tk.LEFT, padx=(0, 20))
        bank_combo.bind("<<ComboboxSelected>>", lambda e: self._load_mappings())
        
        # Botones de accion
        btn_frame = tk.Frame(top_frame)
        btn_frame.pack(side=tk.RIGHT)
        
        tk.Button(btn_frame, text="+ Agregar Concepto", bg="#2563eb", fg="white",
                  command=self._add_concept, padx=10).pack(side=tk.LEFT, padx=5)
        
        tk.Button(btn_frame, text="🗑 Eliminar", bg="#dc2626", fg="white",
                  command=self._delete_selected, padx=10).pack(side=tk.LEFT, padx=5)
        
        tk.Button(btn_frame, text="💾 Guardar Todo", bg="#16a34a", fg="white",
                  command=self._save_all, padx=10).pack(side=tk.LEFT, padx=5)
        
        # Frame de la tabla
        table_frame = tk.Frame(self.window, padx=10, pady=5)
        table_frame.pack(fill=tk.BOTH, expand=True)
        
        # Treeview para mostrar conceptos
        columns = ("concepto", "categoria", "id_operacion", "descripcion")
        self.tree = ttk.Treeview(table_frame, columns=columns, show="headings", height=20)
        
        # Configurar columnas
        self.tree.heading("concepto", text="Concepto (del banco)")
        self.tree.heading("categoria", text="Categoría")
        self.tree.heading("id_operacion", text="ID Operación")
        self.tree.heading("descripcion", text="Descripción (para Novohit)")
        
        self.tree.column("concepto", width=300)
        self.tree.column("categoria", width=100, anchor="center")
        self.tree.column("id_operacion", width=100, anchor="center")
        self.tree.column("descripcion", width=350)
        
        # Scrollbars
        scrollbar_y = ttk.Scrollbar(table_frame, orient=tk.VERTICAL, command=self.tree.yview)
        scrollbar_x = ttk.Scrollbar(table_frame, orient=tk.HORIZONTAL, command=self.tree.xview)
        self.tree.configure(yscrollcommand=scrollbar_y.set, xscrollcommand=scrollbar_x.set)
        
        self.tree.grid(row=0, column=0, sticky="nsew")
        scrollbar_y.grid(row=0, column=1, sticky="ns")
        scrollbar_x.grid(row=1, column=0, sticky="ew")
        
        table_frame.grid_rowconfigure(0, weight=1)
        table_frame.grid_columnconfigure(0, weight=1)
        
        # Evento doble click para editar
        self.tree.bind("<Double-1>", self._on_double_click)
        
        # Frame inferior - Info
        info_frame = tk.Frame(self.window, padx=10, pady=10, bg="#f3f4f6")
        info_frame.pack(fill=tk.X, side=tk.BOTTOM)
        
        tk.Label(info_frame, text="💡 Doble clic para editar | Los cambios se guardan en archivos JSON",
                 bg="#f3f4f6", fg="#6b7280").pack(side=tk.LEFT)
        
        tk.Button(info_frame, text="Cerrar", command=self.window.destroy,
                  padx=20).pack(side=tk.RIGHT)
        
    def _load_mappings(self):
        """Carga los mapeos del banco seleccionado."""
        # Limpiar tabla
        for item in self.tree.get_children():
            self.tree.delete(item)
        
        # Cargar mapeos
        self.mappings = load_bank_mappings(self.current_bank.get())
        
        # Insertar en tabla
        for concepto, mapping in sorted(self.mappings.items()):
            self.tree.insert("", tk.END, values=(
                concepto,
                mapping.get("categoria", "").upper(),
                mapping.get("id_tp_operation", ""),
                mapping.get("descripcion", "")
            ), tags=(mapping.get("categoria", ""),))
        
        # Colorear filas
        self.tree.tag_configure("comision", background="#dbeafe")  # Azul claro
        self.tree.tag_configure("iva", background="#dcfce7")  # Verde claro
        self.tree.tag_configure("deposito", background="#fef3c7")  # Amarillo claro
        
    def _add_concept(self):
        """Abre dialogo para agregar nuevo concepto."""
        dialog = AddConceptDialog(self.window, self.current_bank.get())
        self.window.wait_window(dialog.top)
        
        if dialog.result:
            self._load_mappings()
            
    def _delete_selected(self):
        """Elimina el concepto seleccionado."""
        selected = self.tree.selection()
        if not selected:
            messagebox.showwarning("Sin seleccion", "Por favor seleccione un concepto para eliminar.")
            return
        
        item = self.tree.item(selected[0])
        concepto = item["values"][0]
        
        if messagebox.askyesno("Confirmar", f"¿Eliminar el concepto '{concepto}'?"):
            if delete_mapping(self.current_bank.get(), concepto):
                self._load_mappings()
                messagebox.showinfo("Exito", "Concepto eliminado correctamente.")
            else:
                messagebox.showerror("Error", "No se pudo eliminar el concepto.")
                
    def _on_double_click(self, event):
        """Maneja el doble clic para editar."""
        item = self.tree.identify_row(event.y)
        if item:
            values = self.tree.item(item, "values")
            concepto = values[0]
            
            dialog = EditConceptDialog(self.window, self.current_bank.get(), 
                                       concepto, self.mappings.get(concepto.upper(), {}))
            self.window.wait_window(dialog.top)
            
            if dialog.result:
                self._load_mappings()
                
    def _save_all(self):
        """Guarda todos los cambios."""
        messagebox.showinfo("Guardado", "Los conceptos se guardan automaticamente.\n\n"
                           "Los archivos JSON estan en:\nconfig/bank_concepts/")


class AddConceptDialog:
    """Dialogo para agregar nuevo concepto."""
    
    def __init__(self, parent, bank):
        self.result = None
        
        self.top = tk.Toplevel(parent)
        self.top.title(f"Agregar Concepto - {bank}")
        self.top.geometry("500x300")
        self.top.transient(parent)
        self.top.grab_set()
        
        self.bank = bank
        
        # Formulario
        tk.Label(self.top, text="Concepto (texto exacto del banco):", anchor="w").pack(fill=tk.X, padx=10, pady=(10, 0))
        self.concepto_var = tk.StringVar()
        tk.Entry(self.top, textvariable=self.concepto_var).pack(fill=tk.X, padx=10, pady=5)
        
        tk.Label(self.top, text="Categoria:", anchor="w").pack(fill=tk.X, padx=10)
        self.categoria_var = tk.StringVar(value="comision")
        self.categoria_combo = ttk.Combobox(self.top, textvariable=self.categoria_var, 
                     values=["comision", "iva", "deposito"], state="readonly")
        self.categoria_combo.pack(fill=tk.X, padx=10, pady=5)
        
        tk.Label(self.top, text="ID Operacion Novohit:", anchor="w").pack(fill=tk.X, padx=10)
        self.id_op_var = tk.StringVar(value="7 (COMISION)")
        self.id_op_combo = ttk.Combobox(self.top, textvariable=self.id_op_var, 
                     values=["6 (DEPOSITO)", "7 (COMISION)", "8 (IVA)"], state="readonly")
        self.id_op_combo.pack(fill=tk.X, padx=10, pady=5)
        
        # Vincular categoria con ID de operacion automaticamente
        self.categoria_var.trace_add('write', self._on_categoria_change)
        
        tk.Label(self.top, text="Descripcion (para Novohit):", anchor="w").pack(fill=tk.X, padx=10)
        self.desc_var = tk.StringVar()
        tk.Entry(self.top, textvariable=self.desc_var).pack(fill=tk.X, padx=10, pady=5)
        
        # Botones
        btn_frame = tk.Frame(self.top)
        btn_frame.pack(fill=tk.X, padx=10, pady=20)
        
        tk.Button(btn_frame, text="Guardar", bg="#16a34a", fg="white",
                  command=self._save).pack(side=tk.RIGHT, padx=5)
        tk.Button(btn_frame, text="Cancelar", command=self.top.destroy).pack(side=tk.RIGHT, padx=5)
        
    def _on_categoria_change(self, *args):
        """Actualiza el ID de operacion segun la categoria seleccionada."""
        categoria = self.categoria_var.get()
        if categoria == "deposito":
            self.id_op_var.set("6 (DEPOSITO)")
        elif categoria == "iva":
            self.id_op_var.set("8 (IVA)")
        else:  # comision
            self.id_op_var.set("7 (COMISION)")
        
    def _save(self):
        """Guarda el nuevo concepto."""
        concepto = self.concepto_var.get().strip()
        if not concepto:
            messagebox.showerror("Error", "El concepto no puede estar vacio.")
            return
        
        categoria = self.categoria_var.get()
        id_op = self.id_op_var.get().split()[0]  # Extraer solo el numero
        descripcion = self.desc_var.get().strip() or concepto
        
        if add_mapping(self.bank, concepto, id_op, "cargo", descripcion, categoria):
            self.result = True
            self.top.destroy()
        else:
            messagebox.showerror("Error", "No se pudo guardar el concepto.")


class EditConceptDialog:
    """Dialogo para editar concepto existente."""
    
    def __init__(self, parent, bank, concepto, mapping):
        self.result = None
        
        self.top = tk.Toplevel(parent)
        self.top.title(f"Editar Concepto - {bank}")
        self.top.geometry("500x300")
        self.top.transient(parent)
        self.top.grab_set()
        
        self.bank = bank
        self.concepto_original = concepto
        
        # Formulario
        tk.Label(self.top, text="Concepto:", anchor="w").pack(fill=tk.X, padx=10, pady=(10, 0))
        self.concepto_var = tk.StringVar(value=concepto)
        tk.Entry(self.top, textvariable=self.concepto_var, state="readonly").pack(fill=tk.X, padx=10, pady=5)
        
        tk.Label(self.top, text="Categoria:", anchor="w").pack(fill=tk.X, padx=10)
        self.categoria_var = tk.StringVar(value=mapping.get("categoria", "comision"))
        self.categoria_combo = ttk.Combobox(self.top, textvariable=self.categoria_var, 
                     values=["comision", "iva", "deposito"], state="readonly")
        self.categoria_combo.pack(fill=tk.X, padx=10, pady=5)
        
        tk.Label(self.top, text="ID Operacion Novohit:", anchor="w").pack(fill=tk.X, padx=10)
        id_op = mapping.get("id_tp_operation", "7")
        # Mapear ID a texto completo
        id_op_map = {"6": "6 (DEPOSITO)", "7": "7 (COMISION)", "8": "8 (IVA)"}
        id_op_text = id_op_map.get(id_op, f"{id_op} (COMISION)")
        self.id_op_var = tk.StringVar(value=id_op_text)
        self.id_op_combo = ttk.Combobox(self.top, textvariable=self.id_op_var, 
                     values=["6 (DEPOSITO)", "7 (COMISION)", "8 (IVA)"], state="readonly")
        self.id_op_combo.pack(fill=tk.X, padx=10, pady=5)
        
        # Vincular categoria con ID de operacion automaticamente
        self.categoria_var.trace_add('write', self._on_categoria_change)
        
        tk.Label(self.top, text="Descripcion (para Novohit):", anchor="w").pack(fill=tk.X, padx=10)
        self.desc_var = tk.StringVar(value=mapping.get("descripcion", ""))
        tk.Entry(self.top, textvariable=self.desc_var).pack(fill=tk.X, padx=10, pady=5)
        
        # Botones
        btn_frame = tk.Frame(self.top)
        btn_frame.pack(fill=tk.X, padx=10, pady=20)
        
        tk.Button(btn_frame, text="Guardar Cambios", bg="#16a34a", fg="white",
                  command=self._save).pack(side=tk.RIGHT, padx=5)
        tk.Button(btn_frame, text="Cancelar", command=self.top.destroy).pack(side=tk.RIGHT, padx=5)
        
    def _on_categoria_change(self, *args):
        """Actualiza el ID de operacion segun la categoria seleccionada."""
        categoria = self.categoria_var.get()
        if categoria == "deposito":
            self.id_op_var.set("6 (DEPOSITO)")
        elif categoria == "iva":
            self.id_op_var.set("8 (IVA)")
        else:  # comision
            self.id_op_var.set("7 (COMISION)")
        
    def _save(self):
        """Guarda los cambios."""
        categoria = self.categoria_var.get()
        id_op = self.id_op_var.get().split()[0]
        descripcion = self.desc_var.get().strip()
        
        # Eliminar el viejo y agregar el nuevo
        delete_mapping(self.bank, self.concepto_original)
        
        if add_mapping(self.bank, self.concepto_original, id_op, "cargo", descripcion, categoria):
            self.result = True
            self.top.destroy()
        else:
            messagebox.showerror("Error", "No se pudo guardar los cambios.")


def open_concept_manager(parent: tk.Tk):
    """
    Funcion de conveniencia para abrir el gestor de conceptos.
    
    Args:
        parent: Ventana padre (tk.Tk)
    """
    ConceptManagerWindow(parent)
