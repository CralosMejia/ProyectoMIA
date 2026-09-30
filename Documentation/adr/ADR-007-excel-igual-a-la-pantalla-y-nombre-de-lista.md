# ADR-007 · Excel igual a la pantalla y nombre editable de la lista

- **Estado:** aceptada · 2026-09-29 · R-008 (petición del usuario tras el Día 4)
- **Origen:** revisión de la lista y del Excel por el usuario; [03 §15 CU-12](../03-casos-de-uso.md)
- **Se aparta de:** R-005 (e) "el Excel conserva score y aportes" ([ADR-006](ADR-006-lista-desde-hoy-y-cedula-en-lugar-de-correo.md), solo en lo relativo al Excel), R-006 "el celular se mantiene en el Excel" y las hojas `top_K` / `cartera_completa` / `resumen` de CU-12; amplía el contrato y el esquema de listas de R-004

## Contexto

El Excel mostraba columnas técnicas (score, aportes, monto, celular) y hojas con nombres internos, distintas de lo que el personal ve en pantalla. Además, las listas solo se distinguían por la fecha, lo que no basta cuando se generan varias el mismo día o para campañas concretas.

## Decisión

1. **Excel = tabla de la pantalla.** Hojas `Socios prioritarios a contactar`, `Otros socios por vencer` y `Resumen` (términos llanos, sin modelo, umbrales, Top K ni score). Columnas: Prioridad, Nombre, Cédula, Plan, Vence el, Días para vencer, Nivel de riesgo, Motivos principales (sin aporte). Sin celular, score ni monto. Se mantienen RN-12.1..12.3 (memoria, neutralización de fórmulas, bytes deterministas).
2. **La API no cambia para los ítems:** `PrediccionDTO` conserva `celular`, `score` y `monto_cobrado`.
3. **Nombre de la lista:** `listas_priorizadas.nombre TEXT NOT NULL` con `CHECK` 1..80 (migración `0006`, rellena las listas existentes). `POST /listas` acepta `nombre` opcional (recortado, 1..80, sin caracteres de control; inválido → `400`); por defecto `"Lista del <d> <mmm> <aaaa>"` con la fecha de la lista, mismo formato en dominio, migración y frontend. `ListaPriorizadaDTO` y `ListaResumenDTO` devuelven `nombre`. Sin unicidad; no se edita después (RN-04.5).

## Alternativas descartadas

- **Mantener score y aportes en el Excel** (R-005 (e)): el usuario no los usa y confunden al personal.
- **Mantener el celular solo en el Excel** (R-006): el usuario prefirió que el Excel sea idéntico a la pantalla; el dato sigue disponible en la API.
- **Nombre calculado solo en el frontend:** no se vería en el Excel ni sería el mismo en todas las pantallas.
- **Nombre único o editable tras generar:** innecesario y contrario a la inmutabilidad de la lista.

## Consecuencias

- El personal no tiene el celular en el Excel; si lo necesita, habrá que reintroducirlo con otra decisión.
- `nombre` es un campo requerido en las respuestas: clientes y dobles de prueba lo deben incluir.
- Detalle: [12 §Excel](../docs/backend/12-modelo-y-listas.md), [09](../docs/backend/09-esquema-base-de-datos.md), [API_CONTRACT](../docs/API_CONTRACT.md), [frontend/01](../docs/frontend/01-arquitectura.md).
