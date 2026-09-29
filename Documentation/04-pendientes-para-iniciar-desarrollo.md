# 04 · Decisiones y pendientes para iniciar el desarrollo

**Fecha:** 28 de septiembre de 2026 · **Revisión 3**: decisiones D-01 a D-18 confirmadas por el usuario  
**Base:** [01 · Análisis](01-analisis-mvp-a-app-web.md), [03 · Casos de uso](03-casos-de-uso.md) (v4), `plantillas/` y el estado del repositorio.  
**Uso:** lista viva. Cuando cambie una decisión, se actualiza aquí y en `03`.

---

## 1. Decisiones de contexto

| Fecha | Decisión | Dónde queda |
|---|---|---|
| 28-09-2026 | Stack FastAPI + React + PostgreSQL 16 en Docker. | [ADR-001](adr/ADR-001-fastapi-react-postgresql.md) |
| 28-09-2026 | El histórico 2025–2026 se migra **una sola vez**; después, la carga paulatina es **solo con la plantilla oficial**. | `03` · CU-03, CU-01 |
| 28-09-2026 | Datos históricos: `plantillas/Control Gym 2025 (1).xlsx` y `plantillas/Control Gym 2026 (2).xlsx`. | `03` · CU-03 |
| 28-09-2026 | **Todo el proyecto (CU-00 a CU-12) se entrega en una semana**, con alcance simplificado. | `03` §1.1 y §20 · §6 de este documento |
| 28-09-2026 | El sistema funciona en **un solo PC** de Mtabolic, con Docker Compose, y se usa desde ese equipo. | `03` RT-15 · §3 de este documento |

De las preguntas de `01`: P-01, P-02, P-05, P-06, P-08, P-11 y P-12 ya estaban cerradas. P-03 (dónde se instala) queda cerrada con "un solo PC", P-04 con D-08, P-09 con D-07 y P-10 con D-11.

---

## 2. Decisiones D-01 a D-18 (confirmadas el 28-09-2026)

| ID | Tema | Decisión | Efecto en `03` |
|---|---|---|---|
| D-01 | Cómo se ejecuta la migración única | **(b) Automática:** el backend la inicia al arrancar si la base no tiene membresías ni una migración registrada. Corre en segundo plano, con un bloqueo en la base para que no se ejecute dos veces. El **esquema** lo sigue creando Alembic en un servicio aparte que corre antes del backend. | CU-03 (disparador y flujo), RT-14 |
| D-02 | Si falla el entrenamiento del modelo v1 | **(a) Se revierte todo:** datos y modelo en una sola transacción. La base queda vacía y se reintenta en el siguiente arranque. | CU-03 (RN-03.2) |
| D-03 | Enlace de un socio histórico sin cédula | **(b) Automático** si el nombre normalizado coincide exactamente, el socio histórico no tiene cédula y no hay homónimos. Los casos ambiguos se informan en el resumen de la carga. | CU-01 (RN-01.9) |
| D-04 | Clave de duplicado | Identidad del socio + fecha de inicio + fecha de vencimiento + plan. En la migración se conservan los duplicados exactos del histórico, como en el notebook. | CU-01 (RN-01.8), CU-03 |
| D-05 | Reentrenamiento programado con el PC apagado | **No se recupera la fecha perdida.** Si el PC no estuvo encendido en la fecha programada, al arrancar no se reentrena: se registra `OMITIDO` y la próxima fecha pasa a ser 6 meses después. | CU-02 ("Política de fechas perdidas") |
| D-06 | Ejecución manual | **Sí**, con un comando documentado (`docker compose exec backend python -m app.cli reentrenar`; el nombre final se fija al implementar y se documenta en `Backend/README.md`). | CU-02 ("Comando manual") |
| D-07 | Criterios de reentrenamiento | Al menos 150 ciclos nuevos evaluables; al menos 60 % de membresías nuevas con fecha de vencimiento; al menos 20 casos por clase; y el modelo nuevo **no puede tener peor PR-AUC** que el vigente en los últimos 3 meses con resultado conocido. | CU-02 |
| D-08 | Fecha de generación de la lista | Fecha actual del reloj, editable, con advertencia si la última carga tiene más de 30 días. | CU-04 |
| D-09 | Máximo de filas por archivo | 500 filas. | CU-01 |
| D-10 | Umbrales de riesgo | Percentiles de los scores sobre los últimos 3 meses con resultado conocido: 20 % ALTO, 30 % MEDIO, 50 % BAJO. Se recalculan en cada entrenamiento. | CU-05 |
| D-11 | Variables `inicio_aproximado` y `mes_vencimiento` | **Como en el notebook**: se mantienen y se calculan igual. | CU-02 (RN-02.7), CU-03 (RN-03.3) |
| D-12 | Estados del registro | **Como en el notebook**: no se usan en la etiqueta ni en la lista; se guardan como dato informativo. | CU-01 (RN-01.7), CU-04 |
| D-13 | Asistencias | **Como en el notebook**: se guardan, pero no entran al modelo. | CU-01 |
| D-14 | Validación de la cédula | 10 dígitos con dígito verificador. Se acepta un pasaporte (alfanumérico de 5 a 20 caracteres) si Observaciones contiene `PASAPORTE`. | CU-01 |
| D-15 | Correcciones a la plantilla | **Ninguna.** La exclusión de ciclos (fecha mínima razonable, duración implausible, sin vencimiento) sigue las reglas del notebook. La hoja `Catalogos` tiene un error de presentación: `TRANSFERENCIA` y `TARJETA_DATAFAST` aparecen como equivalencias de plan. Es solo cosmético, porque el sistema no lee esa hoja. | CU-01 (RN-01.5) |
| D-16 | Detalles de gestión y dashboard | **No hacen falta reglas adicionales**: hay un solo PC y un solo punto de uso, así que no se tratan conflictos entre usuarios simultáneos. Se mantienen las reglas mínimas que el formulario necesita para funcionar (`03` CU-08 a CU-11). | CU-08 a CU-11 sin cambios |
| D-17 | Campañas iniciales | **No se conocen todavía.** Se cargan campañas de ejemplo, marcadas como tales, hasta que Mtabolic entregue las reales. | CU-06 (RN-06.4) |
| D-18 | Quién registró una gestión | Campo de texto opcional "Responsable". | CU-08, CU-10 |

---

## 3. Instalación en un solo PC: qué implica

Con la instalación en un solo PC, la mayoría de las dudas de despliegue quedan resueltas. Lo que falta tener en cuenta:

1. **Acceso (CU-00):** por defecto solo se permite `127.0.0.1`. Los puertos se publican solo en `127.0.0.1`, como ya hace `compose.yaml`. No hace falta HTTPS dentro del propio equipo.
2. **Arranque automático:** Docker Desktop debe iniciarse con Windows y los servicios deben tener `restart: unless-stopped`. Si no, después de reiniciar el PC el sistema no está disponible.
3. **Reentrenamiento:** como las fechas perdidas no se recuperan (D-05), el modelo puede pasar mucho tiempo sin actualizarse si el PC suele estar apagado. El comando manual es la vía de respaldo.
4. **Respaldos:** después de la migración, la base es la **única fuente de verdad**. Si el disco del PC falla, se pierde todo. Hace falta un respaldo periódico (`pg_dump`) copiado **fuera del PC** (disco externo o nube) y una restauración probada al menos una vez.
5. **Libros históricos:** se montan como volumen de solo lectura para la migración. Después se pueden retirar de la carpeta.
6. **Ley Orgánica de Protección de Datos Personales:** falta definir quién es el responsable del tratamiento en Mtabolic, el plazo de conservación y cómo se atiende una solicitud de eliminación. Como no se borra físicamente, hace falta un proceso de anonimización. Esto no bloquea la entrega, pero debe quedar mencionado en el informe.
7. **Recursos:** 2 GB de RAM libres y 2 núcleos alcanzan para PostgreSQL, el backend (con entrenamiento) y el frontend.

---

## 4. Repositorio y datos: acciones inmediatas

1. **Riesgo real ahora mismo:** el repositorio raíz es git y los libros `plantillas/Control Gym 2025 (1).xlsx` y `plantillas/Control Gym 2026 (2).xlsx` están **sin seguimiento, pero no ignorados**. Un `git add .` subiría datos personales reales. Hay que añadir `plantillas/Control Gym*.xlsx` a `.gitignore`.
2. Los notebooks están en `Notebookes/`. Revisé sus salidas: no contienen cédulas, correos ni celulares.
3. Las imágenes Docker se construyen desde `Backend/` y `Frontend/`, así que los libros no entran en ellas. Llegan por volumen (D-01).
4. **Datos para pruebas:** no se pueden usar los reales en el repositorio. Hace falta un conjunto pequeño, **sintético**, con la estructura de los libros históricos (varias hojas mensuales, encabezado en filas distintas y nombres de columna cambiantes) para probar CU-03, y archivos de plantilla válidos e inválidos para probar CU-01. La verificación contra las cifras del notebook (2.771 / 2.748 / 1.410) se hace **solo en local**, con los libros reales y fuera de la suite versionada.

---

## 5. Configuración del proyecto antes de `/req`

| # | Ajuste | Estado |
|---|---|---|
| 1 | `.claude/CLAUDE.md`: completar los marcadores de la plantilla (`{{PROYECTO}}`, `{{DESCRIPCION_UNA_LINEA}}`, `{{INVARIANTE_PROPIA_DEL_DOMINIO}}`) y reemplazar las invariantes de usuarios con sesión ("el dueño del dato sale del token") por las de este sistema (sin login, acceso por IP). | Hecho (R-002, DOC-1) |
| 2 | `.claude/rules/database.md` exige `user_id NOT NULL` en toda tabla. | **No aplica en este caso** (decisión del usuario). Se deja anotado en `CLAUDE.md` para que los agentes no lo exijan. |
| 3 | Crear `Documentation/DEVELOPMENT_GUIDELINES.md` con el alcance y lo que queda fuera (`03` §19 y §20), porque `CLAUDE.md` lo cita. | Hecho: [DEVELOPMENT_GUIDELINES](DEVELOPMENT_GUIDELINES.md) |
| 4 | **ADR-002 · El modelo de ML vive en infraestructura**, detrás de un puerto (por ejemplo `PredictorModel`). pandas y scikit-learn no entran en el dominio; la lógica de ciclos T−30 y T+30 puede quedar en dominio como código puro. | **Confirmado** · [ADR-002](adr/ADR-002-ml-en-infraestructura.md) |
| 5 | **ADR-003 · Reentrenamiento y versionado de modelos**: planificador dentro del backend sin recuperar fechas perdidas, comando manual, comparación contra el vigente, modelos guardados en la base. | [ADR-003](adr/ADR-003-reentrenamiento-y-versionado.md) |
| 6 | **ADR-004 · Migración de datos al arrancar**: excepción explícita a la regla "nada automático al arrancar". Solo aplica a datos, nunca al esquema; corre en segundo plano, con bloqueo y de forma atómica. | [ADR-004](adr/ADR-004-migracion-datos-al-arrancar.md) |
| 7 | Montos: se guardan como `Decimal` y el modelo trabaja con `float`. Dejar escrito que la conversión en ese punto está permitida. | Hecho: [DEVELOPMENT_GUIDELINES](DEVELOPMENT_GUIDELINES.md) §Excepciones |

---

## 6. Plan de la entrega de una semana

### Condiciones sin las que el plan no se cumple

1. Decisiones cerradas (hecho: §2).
2. **Proceso de agentes aligerado:** TDD completo solo en CU-03 y en las reglas T−30/T+30 y de etiqueta. En el resto, pruebas mínimas de los criterios de aceptación de `03`, y una sola revisión de seguridad al final.
3. Instalación en el PC local con Docker Compose.
4. Siete días a tiempo completo, o dos personas en paralelo (backend y frontend).

### Plan por día (resumen)

| Día | Trabajo | Casos de uso | Resultado verificable |
|---|---|---|---|
| 1 | Ajustes de §4 y §5; esquema de la base con Alembic y servicio de migraciones en Compose. | — | `docker compose up` crea todas las tablas antes de arrancar el backend. |
| 2 | Lectura y limpieza del histórico, identidad, ciclos y etiquetas. | CU-03 (lógica) | Con los libros reales, en local: 2.771 / 2.748 / 1.410 y los ciclos evaluables del notebook. |
| 3 | Entrenamiento v1, umbrales, guardado atómico al arrancar; generación de la lista y Excel en el backend. | CU-03 (completo), CU-04, CU-05, CU-12 | Arranque en limpio → modelo v1; lista al 31-08-2026 igual a la del notebook. |
| 4 | Carga por plantilla (validación, vista previa, duplicados, enlace con el histórico). Pantallas de carga, lista y descarga. | CU-01, CU-04, CU-12 | Carga y lista de punta a punta en el navegador. |
| 5 | Campañas (con las de ejemplo) y formulario de gestión, en backend y frontend. | CU-06, CU-07, CU-08, CU-10 | Asignar y cerrar una gestión desde la lista. |
| 6 | Alertas, dashboard, reentrenamiento (programado, `OMITIDO`, comparación y comando) y restricción por IP. | CU-09, CU-11, CU-02, CU-00 | Pruebas con reloj simulado; `403` desde una IP no autorizada. |
| 7 | Escenario de demostración (`03` §21), revisión de seguridad única, corrección de errores, instalación limpia en el PC y documentación final. | Todos | Demostración ensayada. |

El cronograma detallado por día, con tareas de base de datos, backend y frontend, está en [05 · Cronograma](05-cronograma-semana.md).

### Riesgos del plan

| Riesgo | Señal temprana | Qué se recorta primero |
|---|---|---|
| La migración no reproduce las cifras del notebook | Al final del día 2 no cuadran los conteos | Se documenta la diferencia y se sigue; no más de medio día extra. |
| La migración atómica al arrancar es lenta o bloquea el arranque | El backend tarda más de 1 minuto en responder `/health` | Se asegura que corra en segundo plano; si no alcanza el tiempo, se deja en primer plano con un tiempo de espera mayor en el healthcheck. |
| El día 5 o 6 se atrasa | CU-08/CU-10 sin terminar al cierre del día 5 | En este orden: el gráfico del embudo (queda como tabla), la tabla por campaña del dashboard y la comparación contra el modelo vigente en CU-02. |
| Mtabolic no entrega campañas reales | — (ya se sabe) | Campañas de ejemplo (D-17). |
