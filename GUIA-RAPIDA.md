# Guía rápida: probar la aplicación en su computadora

Con esta guía la aplicación queda funcionando con **un solo comando**. Solo necesita Docker Desktop: no hace falta instalar Python ni pedir ningún archivo.

> **Los datos son inventados.** Sirven para ver la aplicación funcionando. Las cifras que verá **no son las de la tesis** ni describen al gimnasio.

## Pasos

**1. Instale y abra Docker Desktop.** Descárguelo de <https://www.docker.com/products/docker-desktop/>, ábralo y espere a que indique que está en marcha.

**2. Consiga el proyecto.** Si tiene git:

```bash
git clone https://github.com/CralosMejia/ProyectoMIA.git
cd ProyectoMIA
```

Sin git: en la página del repositorio use **Code → Download ZIP**, descomprímalo y abra una terminal dentro de la carpeta.

**3. Ejecute el comando de su sistema**, desde esa carpeta.

| Sistema | Comando |
|---|---|
| Windows (PowerShell) | `powershell -ExecutionPolicy Bypass -File scripts\levantar-demo.ps1` |
| macOS, Linux o Git Bash | `bash scripts/levantar-demo.sh` |

No tiene que responder nada. Espere el mensaje `Listo. Abra http://localhost:8083 en el navegador.`

**4. Abra <http://localhost:8083>.** La página de Inicio debe indicar que el sistema está listo.

**5. Genere una lista.** Entre en **Lista**, deje la fecha y los días que propone la pantalla, pulse **Generar lista** y después **Descargar Excel**.

## Qué ocurre por dentro

- El comando crea las contraseñas por usted, en el archivo `.env.demo`, que no se sube al repositorio.
- Al arrancar, la aplicación migra los libros de `datos-demo/` a su base de datos y entrena el modelo.
- **La primera vez tarda varios minutos**, porque Docker descarga y construye todo. Las siguientes es casi inmediato.

Para probar la carga de datos, use `Backend/tests/fixtures/plantillas/plantilla_valida.xlsx` en la pantalla **Carga**.

## Parar, volver a levantar y borrar

| Quiero | Comando |
|---|---|
| Parar, sin perder nada | `docker compose -p mtabolic-demo --env-file .env.demo stop` |
| Volver a levantar | El mismo comando del paso 3 |
| Borrar todo el demo | `docker compose -p mtabolic-demo --env-file .env.demo down -v` |

> **Cuidado:** al borrar, escriba siempre `-p mtabolic-demo`. Sin esa parte, `down -v` actúa sobre el proyecto principal y borra su base de datos.

## Si algo falla

| Qué ve | Qué hacer |
|---|---|
| `Docker no esta instalado` o `no esta en marcha` | Instale o abra Docker Desktop, espere a que esté listo y repita el comando |
| `el puerto 8083 ya esta ocupado` (o 8003, 5435) | Cierre el programa que usa ese puerto y repita el comando |
| Docker Desktop no arranca en Windows o la descarga se corta | Compruebe que WSL2 esté instalado (`wsl --install`, y reinicie) y que el antivirus o la VPN no bloqueen a Docker |
| La lista sale vacía | Compare la fecha de hoy con `datos-demo/vigencia.txt`. Si ya pasó, borre el demo y repita el comando: los datos se crean de nuevo con la fecha de hoy. Git los mostrará como modificados, y es lo esperado |
| `tiempo agotado` u otro error | Ejecute el comando de `logs` que muestra el mensaje y revise la última línea con error |
