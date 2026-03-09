# Instrucciones para corregir el problema de secuencias

## Problema
El filtro por número de documento no funciona en Novohit. Hay que filtrar por Operación y Fecha.

## Solución

### Paso 1: Agregar nueva función `filter_by_operation_and_date`

Agrega esta función a la clase `NovohitLoader` en `core/loader.py`:

```python
    def filter_by_operation_and_date(self, operation_id: str, fecha: str) -> bool:
        """
        Filtra la tabla de operaciones bancarias por tipo de operacion y fecha.
        """
        try:
            logger.info(f"Filtrando por Operacion ID: {operation_id}, Fecha: {fecha}")
            
            if not self._verify_list_page():
                logger.warning("No estamos en el listado de operaciones")
                return False
            
            # Seleccionar Tipo de Operacion
            try:
                selectors = [
                    'select[name*="operation"]',
                    'select#id_tp_operation', 
                    'select[name*="operacion"]',
                    'select[name*="id_tp_operation"]'
                ]
                
                op_select = None
                for selector in selectors:
                    try:
                        elem = self.frame.locator(selector).first
                        if elem.count() > 0:
                            op_select = elem
                            break
                    except:
                        continue
                
                if op_select and op_select.count() > 0:
                    op_select.select_option(operation_id)
                    logger.info(f"  Operacion seleccionada: {operation_id}")
                    time.sleep(0.5)
            except Exception as e:
                logger.warning(f"  Error seleccionando operacion: {e}")
            
            # Ingresar Fecha
            try:
                fecha_selectors = [
                    'input[name*="fecha"]',
                    'input#dt_operation',
                    'input[name*="dt_operation"]'
                ]
                
                fecha_input = None
                for selector in fecha_selectors:
                    try:
                        elem = self.frame.locator(selector).first
                        if elem.count() > 0:
                            fecha_input = elem
                            break
                    except:
                        continue
                
                if fecha_input and fecha_input.count() > 0:
                    fecha_input.fill(fecha)
                    logger.info(f"  Fecha ingresada: {fecha}")
                    time.sleep(0.5)
            except Exception as e:
                logger.warning(f"  Error ingresando fecha: {e}")
            
            # Clic en Boton Buscar
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
```

### Paso 2: Modificar `get_last_document_sequence_via_search`

Reemplaza la función existente con esta versión:

```python
    def get_last_document_sequence_via_search(self, prefix: str, fecha: str, operation_id: str = None) -> int:
        """
        Filtra por operacion y fecha, luego busca el ultimo consecutivo.
        """
        try:
            fecha_clean = self._normalize_fecha(fecha)
            
            # Si tenemos operation_id, filtrar primero
            if operation_id:
                success = self.filter_by_operation_and_date(operation_id, fecha)
                if not success:
                    logger.warning("  No se pudo aplicar el filtro")
            
            # Buscar en la tabla
            return self.get_last_document_sequence(prefix, fecha)
            
        except Exception as e:
            logger.warning(f"  Error en busqueda: {e}")
            return 0
```

### Paso 3: Modificar la llamada en `update_document_sequences`

Busca esta línea en `update_document_sequences`:
```python
last_seq = self.get_last_document_sequence_via_search(prefix, fecha)
```

Y cámbiala por:
```python
# Obtener operation_id del primer registro del grupo
operation_id = group_records[0].get('id_tp_operation') if group_records else None
last_seq = self.get_last_document_sequence_via_search(prefix, fecha, operation_id)
```

## Verificación

Después de hacer estos cambios:
1. Ejecuta el RPA
2. Deberías ver en el log: "Filtrando por Operacion ID: 8, Fecha: 25/02/2026"
3. Luego: "Operacion seleccionada: 8" y "Fecha ingresada: 25/02/2026"
4. Y finalmente el documento actualizado: "IVA COM-25022026-01 → IVA COM-25022026-10"
