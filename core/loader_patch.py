"""
Funciones adicionales para core/loader.py
Estas funciones deben agregarse a la clase NovohitLoader en core/loader.py
"""

    def filter_by_operation_and_date(self, operation_id: str, fecha: str) -> bool:
        """
        Filtra la tabla de operaciones bancarias por tipo de operacion y fecha.
        
        Args:
            operation_id: ID del tipo de operacion (ej: "8" para IVA POR COMISIONES)
            fecha: Fecha en formato DD/MM/YYYY
            
        Returns:
            True si se aplico el filtro correctamente
        """
        try:
            logger.info(f"Filtrando por Operacion ID: {operation_id}, Fecha: {fecha}")
            
            # Verificar que estamos en el listado
            if not self._verify_list_page():
                logger.warning("No estamos en el listado de operaciones")
                return False
            
            # 1. Seleccionar Tipo de Operacion en el dropdown
            try:
                # Buscar el select de operacion - varios selectores posibles
                selectors = [
                    'select[name*="operation"]',
                    'select#id_tp_operation', 
                    'select[name*="operacion"]',
                    'select[name*="id_tp_operation"]',
                    'select[name*="tp_operation"]'
                ]
                
                op_select = None
                for selector in selectors:
                    try:
                        elem = self.frame.locator(selector).first
                        if elem.count() > 0:
                            op_select = elem
                            logger.info(f"  Dropdown de operacion encontrado: {selector}")
                            break
                    except:
                        continue
                
                if op_select and op_select.count() > 0:
                    op_select.select_option(operation_id)
                    logger.info(f"  Operacion seleccionada: {operation_id}")
                    time.sleep(0.5)
                else:
                    logger.warning("  No se encontro el dropdown de operacion")
            except Exception as e:
                logger.warning(f"  Error seleccionando operacion: {e}")
            
            # 2. Ingresar Fecha
            try:
                # Buscar el campo de fecha - varios selectores posibles
                fecha_selectors = [
                    'input[name*="fecha"]',
                    'input#dt_operation',
                    'input[name*="date"]',
                    'input[name*="dt_operation"]'
                ]
                
                fecha_input = None
                for selector in fecha_selectors:
                    try:
                        elem = self.frame.locator(selector).first
                        if elem.count() > 0:
                            fecha_input = elem
                            logger.info(f"  Campo de fecha encontrado: {selector}")
                            break
                    except:
                        continue
                
                if fecha_input and fecha_input.count() > 0:
                    fecha_input.fill(fecha)
                    logger.info(f"  Fecha ingresada: {fecha}")
                    time.sleep(0.5)
                else:
                    logger.warning("  No se encontro el campo de fecha")
            except Exception as e:
                logger.warning(f"  Error ingresando fecha: {e}")
            
            # 3. Clic en Boton Buscar
            try:
                search_btn = self.frame.locator('input[value="Buscar"], button:has-text("Buscar"), input[type="submit"][value*="Buscar"]').first
                if search_btn.count() > 0:
                    search_btn.click()
                    logger.info("  Filtro aplicado, esperando resultados...")
                    time.sleep(3)  # Esperar a que la tabla se actualice
                    
                    # Verificar que la tabla se actualizo
                    try:
                        self.frame.evaluate("window.scrollTo(0, 0)")
                        time.sleep(0.5)
                    except:
                        pass
                    
                    return True
                else:
                    logger.warning("  No se encontro el boton Buscar")
            except Exception as e:
                logger.warning(f"  Error clic en Buscar: {e}")
            
            return False
            
        except Exception as e:
            logger.warning(f"  Error filtrando tabla: {e}")
            return False


# Luego modificar la funcion update_document_sequences para usar operation_id:
# En el loop de grupos, cambiar:
#     last_seq = self.get_last_document_sequence_via_search(prefix, fecha)
# Por:
#     operation_id = group_records[0].get('id_tp_operation')
#     last_seq = self.get_last_document_sequence_via_search(prefix, fecha, operation_id)
