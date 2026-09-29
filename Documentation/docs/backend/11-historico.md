# Backend · 11 · Histórico (lectura, limpieza, ciclos y etiquetas)

Creado en R-003 (día 2 del [cronograma](../../05-cronograma-semana.md)). Porta al backend la lógica del notebook `Notebookes/MVP.ipynb` (secciones 2.4–5.5) que usa CU-03 ([03 §6](../../03-casos-de-uso.md)). La composición con los repositorios dentro de la migración atómica al arrancar es del día 3 (D3-BE-04, [ADR-004](../../adr/ADR-004-migracion-datos-al-arrancar.md)); los endpoints siguen en `501`.

## Flujo

`LectorLibrosExcel` (infraestructura, pandas) → `FilaCruda` con valores crudos → `limpiar` (dominio: conversión, normalización, identidad) → `RegistroHistorico` → `fecha_corte` + `clasificar` + `etiquetar` (dominio) → `ResultadoProcesamiento` con `InformeHistorico`. Lo orquesta `ProcesarHistorico(lector).ejecutar(rutas)` sin persistir.

## Dominio — `app/domain/historico/` (solo librería estándar)

| Módulo | Contenido |
|---|---|
| `conversiones.py` | `convertir_fecha` sin pandas: `datetime`/`date`, ISO, `d/m/aaaa` día primero, año de 2 dígitos → 2000+, serial Excel (1899-12-30) solo en 20000..60000, separador doble (`dd//mm/aaaa`) solo entre la 1.ª y la 2.ª parte; `bool` no es número. `convertir_monto` → `Decimal` (primer número tras cambiar coma por punto; `float` vía `str`). `normalizar_texto_encabezado`. |
| `normalizacion.py` | `es_fila_util`, `normalizar_nombre` (sin tildes, `A-Z` y espacio simple), `normalizar_cedula` (≥ 9 dígitos o `None`), `normalizar_plan` (6 categorías de `Plan`, reglas y orden del notebook, incluida la duración cuando el campo trae una forma de pago; `"PROMO VERANO"` → `ANUAL` por la subcadena `ANO`, como el notebook), `normalizar_forma_pago`. |
| `identidad.py` | `identidad_de`: `C:<cédula>` o `N:<nombre normalizado>`. |
| `registro.py` | `FilaCruda`, `RegistroHistorico` (montos `Decimal`, fechas `date`, `referencia` = año/hoja/fila), `limpiar(filas) -> ResultadoLimpieza` con conteos. Sin identidad utilizable: nombre normalizado de menos de 5 caracteres contando espacios (como el notebook) y sin cédula válida → se descarta y se cuenta. Sin fecha de inicio → `inicio_aproximado` y `fecha_actividad` = primer día del mes de la hoja. Duplicados exactos se conservan. `repr` sin datos personales. |
| `ciclos.py` | `fecha_corte` (último día del mes máximo de las hojas), `MotivoCiclo`, `clasificar` (orden del notebook: sin vencimiento, fuera de rango < 2024-12-01, posterior al corte, pase diario, duración fuera de 22..400, ventana incompleta), `etiquetar` (renovación = otra membresía no `DIARIO` del mismo socio con actividad en `[T, T+30]`, ambos inclusive). Caso del tutor: vence el 20 del último mes → `PENDIENTE`. |
| `errores.py` | `LibroSinAnioError`, `HojaSinEncabezadoError` (`DomainError`, mensajes con libro y hoja, sin datos de celdas). |

## Aplicación — `app/application/historial/`

- `ports.py`: `LectorHistorico`, `SocioRepository.insertar_en_bloque` (ids en el orden de entrada), `MembresiaRepository.insertar_en_bloque`, `CargaRepository.crear`, como `Protocol` `runtime_checkable`; DTOs `NuevoSocio`, `NuevaMembresia` (`socio_id: int`), `NuevaCarga` (`fecha_carga` con zona o `ValueError`). **El llamante es dueño de la transacción:** los repositorios nunca hacen `commit` ni `rollback`.
- `procesar_historico.py`: `ProcesarHistorico` → `registros`, `ciclos`, `fecha_corte` e `InformeHistorico` (solo conteos: filas, ciclos por estado y motivo, evaluables, no renovó, renovó, prevalencia `Decimal`, rango de vencimientos); serializable a `dict` sin nombres ni cédulas.

## Infraestructura

- `infrastructure/historico/lector_libros.py` (`LectorLibrosExcel`) y `alias_columnas.py` (`MESES`, `ALIAS_COLUMNAS` del notebook): año desde el nombre del archivo; solo hojas cuyo nombre es un mes (las demás se reportan como omitidas); encabezado = primera de las 10 primeras filas con `CEDULA` y `NOMBRE`; columnas por alias (subcadena); `header=None`, `dtype=object`; `NaN`/`NaT` → `None`; las cédulas nunca se leen como `float`. Único lugar con pandas (ADR-002).
- `infrastructure/persistence/repositories/historial.py`: `SqlAlchemy{Socio,Membresia,Carga}Repository(session, clock)`; `insert` masivo con lista de parámetros, `RETURNING id` ordenado para socios, `created_at`/`updated_at` del `Clock`, `referencia_origen` JSONB. Prueba: 1 carga + 1.000 socios + 3.000 membresías en una transacción; tras `rollback` las tablas quedan vacías; < 5 s.
- Monto negativo en el libro → `monto_cobrado = None` y se cuenta (la BD exige `>= 0`): **desviación del notebook**, que lo conserva.

## Datos sintéticos y verificación

- `Backend/tests/fixtures/`: generador determinista, 2 libros y 5 plantillas sin datos reales, `esperado.py`. Validados ejecutando el código real del notebook sobre ellos: 39 filas leídas, 25 útiles, 14 socios, 15 evaluables, prevalencia 0,6.
- `Backend/scripts/verificar_historico.py <carpeta>`: compara con las cifras del notebook (uso en `Backend/README.md`).

## Conciliación con el notebook (libros reales, local)

| Cifra | Notebook | App |
|---|---|---|
| Filas útiles / con identidad / socios | 2.771 / 2.748 / 1.410 | igual |
| Fecha de corte | 2026-08-31 | igual |
| `EVALUABLE` (no renovó / renovó) | 1.564 (1.098 / 466) | igual |
| `VENCIMIENTO_POSTERIOR_AL_CORTE` / `VENTANA_INCOMPLETA` / `DURACION_IMPLAUSIBLE` / `PASE_DIARIO` | 160 / 96 / 49 / 16 | igual |
| `SIN_VENCIMIENTO` | 855 | **857** |
| `FECHA_FUERA_DE_RANGO` | 8 | **6** |

**Diferencias conocidas** (registradas en `DIFERENCIAS_CONOCIDAS` del script): 2 celdas basura en la fecha de vencimiento (un entero de 4 dígitos y el texto `dd/`) que pandas 3 convierte en los años 1114 y 1; la app no las interpreta como fecha y las deja sin vencimiento. Ambos ciclos quedan excluidos igual: sin efecto en evaluables ni etiquetas. Decisión: no replicar esa conversión de pandas, que podría convertir basura como `2026` en una fecha válida.

Corregido con TDD durante la conciliación: fechas con separador doble (`dd//mm/aaaa`) que antes se perdían; los evaluables pasaron de 1.562 a 1.564.

**pandas:** se mantiene 3.0.6. El notebook se ejecutó con pandas 3 (con 2.x su propia lógica no da 855/8); la app da las mismas cifras con 2.3.3 porque su conversión de fechas no usa pandas.

## Pendiente

- Conectar `ProcesarHistorico` con los repositorios en la migración atómica al arrancar (día 3, D3-BE-04).
- `mypy` sobre `tests/`: stubs de `openpyxl`, `generar_fixtures.py:836` y un `type: ignore` sin uso en `test_procesar_historico.py:33`.
