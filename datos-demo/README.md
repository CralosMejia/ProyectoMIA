# Datos de demostración

**Todo lo que hay en esta carpeta es inventado.** Ningún socio existe: los nombres llevan la palabra `Demo`, las cédulas empiezan por `0999` (no corresponden a una persona), los celulares por `0900` y los correos terminan en `@example.com`.

Estos archivos **no derivan de los libros reales** de Mtabolic. El programa que los crea no abre ningún archivo: los precios y las probabilidades están escritos a mano en su código. Por eso las cifras que se ven con estos datos **no son las de la tesis** ni describen al gimnasio.

## Qué contiene

| Archivo | Qué es |
|---|---|
| `Control Gym <año> demo.xlsx` | Un libro por año, con una hoja por mes y una fila por membresía, con el mismo formato que usa el gimnasio |
| `vigencia.txt` | La última fecha en que una lista a 31 días sigue teniendo socios |

Sirven para que quien clona el proyecto pueda levantar la aplicación sin ningún archivo confidencial: con ellos se migra el histórico, se entrena el modelo y se genera una lista. Cómo hacerlo está en [`GUIA-RAPIDA.md`](../GUIA-RAPIDA.md).

## Por qué hay una fecha de vigencia

Una lista muestra las membresías que vencen desde hoy, así que unos datos fijos envejecen. Consulte la fecha en `vigencia.txt`. Si ya pasó y aún no había levantado el demo en ese equipo, el comando `levantar-demo` crea estos archivos de nuevo con la fecha de hoy, sin que tenga que hacer nada. En ese caso git los mostrará como modificados: es lo esperado.

## Cómo regenerarlos a mano

Desde la carpeta `Backend/`, con el entorno de desarrollo o solo con `openpyxl` instalado:

```bash
python scripts/generar_dataset_demo.py --fecha-base 2026-11-02 --salida ../datos-demo
```

La misma fecha produce siempre los mismos archivos, byte a byte. No los edite a mano: cualquier cambio se pierde al regenerar.
