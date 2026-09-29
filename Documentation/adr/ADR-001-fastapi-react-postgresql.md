# ADR-001 · FastAPI + React + PostgreSQL en lugar de Streamlit

- **Estado:** aceptada · 2026-09-28 · R-001
- **Cierra:** P-07 de [01-analisis-mvp-a-app-web.md](../01-analisis-mvp-a-app-web.md)

## Contexto

El análisis 01 (§5 y P-07) recomendaba Streamlit por esfuerzo bajo y consideraba FastAPI + React desproporcionado para el alcance. El usuario pidió en R-001 construir la base con FastAPI en capas, React en capas y PostgreSQL 16 en Docker, alineada con las reglas del repositorio (`.claude/rules/`).

## Decisión

- Backend: Python 3.12, FastAPI, Pydantic v2, SQLAlchemy 2 + psycopg 3, arquitectura en capas verificada con import-linter.
- Frontend: React 19 + TypeScript estricto + Vite + Tailwind 4 + React Router, organizado por features.
- Datos: PostgreSQL 16 en contenedor.
- Entorno: Docker Compose con los tres servicios; TDD con pytest, Vitest y Playwright.

## Alternativas descartadas

- **Streamlit** (recomendación de 01): menor esfuerzo, pero sin separación de capas ni contrato de API, y con menos control sobre seguridad y pruebas.
- **Gradio / Hugging Face Spaces:** mismas limitaciones que Streamlit; los Spaces privados requieren cuenta.
- **Ejecutable local (PyInstaller):** sin servidor, pero pesado por scikit-learn y sin interfaz web.

## Consecuencias

- Más código y más infraestructura que Streamlit: el esfuerzo de migración pasa de "bajo – medio" a "medio – alto" (§7 de 01).
- La lógica del notebook deberá vivir en `domain`/`application` del Backend y exponerse por la API; la carga y descarga de Excel pasan a ser endpoints.
- PostgreSQL queda disponible; no se crean tablas hasta que un requerimiento las necesite. *(Actualización 28-09-2026: P-12 se cerró. Los casos de uso de [03](../03-casos-de-uso.md) exigen persistencia: historial acumulativo, listas, modelos versionados, campañas y seguimientos. Con eso la elección de PostgreSQL queda justificada.)*
- Las decisiones de despliegue (P-03) deben considerar un stack de tres contenedores en lugar de `streamlit run`. El despliegue sigue sin confirmarse; ver [04 §3](../04-pendientes-para-iniciar-desarrollo.md).
