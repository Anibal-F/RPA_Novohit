# Bancos Soportados - RPA Novohit

El RPA soporta actualmente 3 bancos. El banco se puede configurar de DOS maneras:

### Opción 1: Configuración en Excel (RECOMENDADO)
En la hoja `Configuración`, celda **B1**, seleccione el nombre del banco:
- `BBVA`
- `Banregio`
- `Banorte`

### Opción 2: Detección por nombre de archivo
El archivo debe contener el nombre del banco:
- `estado_cuenta_BBVA.xlsx`
- `BANORTE_febrero_2026.xlsx`
- `BANREGIO_enero.xlsx`

**Prioridad:** La configuración en Excel (B1) tiene prioridad sobre el nombre del archivo.

---

## Estructura de la hoja "Configuración"

| Celda | Contenido | Ejemplo | Descripción |
|-------|-----------|---------|-------------|
| **B1** | Nombre del banco | `BBVA`, `Banregio`, `Banorte` | Para detectar estructura del banco |
| **C1** | Número de cuenta | `4364010644192320` | Referencia visual (no usado por el RPA) |
| **D1** | ID de cuenta Novohit | `3`, `4`, `5` | ID para registrar en Novohit |
| **L1** | Unidad de negocio | `1` | ID de unidad de negocio (opcional) |

---

## BBVA (Bancomer)

### Configuración en Excel (Celda B1)
Seleccione en la celda B1:
- `BBVA`
- `BANCOMER`

### Estructura esperada
- Hoja: `Edo.Cuenta`
- Columnas: Fecha, Concepto, Referencia, Cargo, Abono

### Conceptos mapeados
| Concepto en Excel | Tipo en Novohit |
|-------------------|-----------------|
| P./PROC.COMUNICACION GPRS | COMISION |
| COM VTAS TDC INTER | COMISION |
| APLICA TASA DESCUENTO | COMISION |
| IVA PAGO/PROC.COMU GPRS | IVA POR COMISIONES |
| IVA COM VTAS TDC INTER | IVA POR COMISIONES |
| IVA TASA DE DESC | IVA POR COMISIONES |

---

## Banregio

### Configuración en Excel (Celda B1)
Seleccione en la celda B1:
- `Banregio`

### Nombre de archivo (alternativo)
- `estado_cuenta_BANREGIO.xlsx`
- `BANREGIO_febrero_2026.xlsx`

### Estructura esperada
- Hoja: `Edo.Cuenta`
- Columnas: Fecha, Descripcion, Referencia, Cargo, Abono, Saldo

### Conceptos mapeados
| Concepto en Excel | Tipo en Novohit |
|-------------------|-----------------|
| Comision Transferencia - envio ; (SPEI; banca por internet) | COMISION |
| Comision SPEI | COMISION |
| IVA de Comision Transferencia - envio ; (SPEI; banca por internet) | IVA POR COMISIONES |
| IVA Comision | IVA POR COMISIONES |

**Nota:** El sistema detecta automaticamente keywords como "COMISION", "IVA", "SPEI" en el concepto.

---

## Banorte

### Configuración en Excel (Celda B1)
Seleccione en la celda B1:
- `Banorte`
- `IXE` (también detectado como Banorte)

### Nombre de archivo (alternativo)
- `estado_cuenta_BANORTE.xlsx`
- `BANORTE_febrero_2026.xlsx`

### Estructura esperada
- Hoja: `Edo.Cuenta`
- Columnas: Fecha, Descripcion, Referencia, Depositos, Retiros

### Nota importante
En Banorte:
- La columna `Depositos` = Abonos (entradas de dinero)
- La columna `Retiros` = Cargos (salidas de dinero, incluye comisiones)

El RPA detecta automaticamente estas columnas y las trata correctamente.

### Conceptos mapeados
Por el momento Banorte usa el sistema de deteccion por keywords:
- Si el concepto contiene "COMISION" o "COM" -> COMISION
- Si el concepto contiene "IVA" -> IVA POR COMISIONES

---

## Instrucciones de Uso

### Paso 1: Configurar el banco (IMPORTANTE)
En la hoja `Configuración`, celda **B1**, seleccione el nombre del banco desde el dropdown:
```
BBVA     -> seleccione: BBVA
Banorte  -> seleccione: Banorte
Banregio -> seleccione: Banregio
```

### Paso 2: Seleccionar Modo de Procesamiento
En la interfaz del RPA, debajo del selector de archivo, encontrará el checkbox:

**✓ Modo Estricto** (recomendado para Banregio)
- Solo procesa conceptos definidos explicitamente en el diccionario
- Use este modo si solo quiere ciertos conceptos específicos (ej: solo SPEI)

**Modo Automático** (recomendado para BBVA/Banorte)
- Detecta automaticamente: COMISIONES, IVA, DESCUENTOS
- Excluye automaticamente: VENTAS, ABONOS, DEPÓSITOS
- Use este modo si quiere procesar todas las comisiones del banco

### Paso 3: Pegar datos
Copie el contenido del estado de cuenta del banco a la hoja `Edo.Cuenta` del archivo `estado_cuenta.xlsx`.

### Paso 4: Verificar
El RPA detectara automaticamente el banco al iniciar y mostrara un resumen:
```
✓ Banco configurado en Excel (B1): Banregio
🔧 Modo de procesamiento: ESTRICTO (solo conceptos del diccionario)
```

---

## Gestionar Conceptos (NUEVO)

Desde la interfaz gráfica puede agregar, editar o eliminar conceptos del diccionario:

### Abrir Gestor de Conceptos
1. En la ventana principal del RPA, haga clic en el botón **"⚙️ Gestionar Conceptos"**
2. Seleccione el banco del dropdown
3. Vea, agregue, edite o elimine conceptos

### Agregar nuevo concepto
1. Haga clic en **"+ Agregar Concepto"**
2. Complete los campos:
   - **Concepto**: Texto exacto que aparece en el estado de cuenta
   - **Categoría**: Comision o IVA
   - **ID Operación**: 7 (Comision) o 8 (IVA)
   - **Descripción**: Texto que aparecerá en Novohit
3. Haga clic en **Guardar**

### Editar concepto existente
- Haga doble clic sobre cualquier concepto en la tabla para editarlo

### Notas importantes
- Los conceptos se guardan en archivos JSON en `config/bank_concepts/`
- Los cambios son permanentes y afectan a todas las ejecuciones futuras
- Si un concepto no está en el diccionario, el RPA intentará detectarlo automáticamente por keywords

---

## Solucion de Problemas

### "No se detecto el banco"
**Solución 1 (Recomendada):** Configure el banco en la hoja `Configuración`, celda B1:
- Seleccione `BBVA`, `Banorte` o `Banregio` desde el dropdown

**Solución 2:** Asegurese de que el nombre del archivo contenga el nombre del banco.

### "Banco configurado no reconocido"
Verifique que en la celda B1 seleccionó exactamente:
- `BBVA` o `BANCOMER`
- `Banorte` o `IXE`
- `Banregio`

### "No se encontro columna de concepto"
Verifique que los headers esten en la hoja `Edo.Cuenta`. El RPA buscara automaticamente la fila con los headers según el banco configurado.

### Los montos no coinciden
- **Banorte**: Asegurese de que las comisiones aparezcan en la columna `Retiros`
- **BBVA/Banregio**: Asegurese de que las comisiones aparezcan en la columna `Cargo`

### Diferencia entre Modo Estricto y Automático

| Característica | Modo Estricto | Modo Automático |
|----------------|---------------|-----------------|
| **Conceptos procesados** | Solo los del diccionario | COMISIONES, IVA, DESCUENTOS |
| **Configuración** | Requiere definir conceptos | Funciona sin configuración |
| **Precisión** | Alta (control total) | Media (puede detectar extras) |
| **Recomendado para** | Banregio (solo SPEI) | BBVA/Banorte (todas las comisiones) |

**¿Cuál usar?**
- Use **Modo Estricto** si quiere control exacto de qué conceptos procesar
- Use **Modo Automático** si quiere procesar todas las comisiones/IVA del banco

---

## Configuracion de Cuentas

Las cuentas bancarias se configuran en la hoja `Configuracion`, celda **D1**:

| Banco | ID Cuenta en Novohit (D1) |
|-------|---------------------------|
| BBVA | 3 (BANCOMER - MXN) |
| Banorte | 4 (BANORTE - MXN) |
| Banregio | 2 (BANREGIO - MXN) |

Para usar una cuenta diferente, simplemente cambie el valor en la celda D1.
