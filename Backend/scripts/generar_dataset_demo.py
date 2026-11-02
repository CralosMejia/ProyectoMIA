"""Generador determinista del dataset sintetico del demo (R-019).

Produce, en ``--salida``, un libro ``Control Gym <anio> demo.xlsx`` por anio (hojas mensuales
desde ENERO 2025 hasta el ultimo mes cerrado antes de ``--fecha-base``) y ``vigencia.txt``, la
ultima fecha en que una lista a 31 dias sigue teniendo socios.

**Todo es inventado:** el script no abre ningun archivo, no ajusta nada a los datos reales y sus
precios y probabilidades estan escritos a mano. Nombres con la marca ``Demo``, cedulas
``0999NNNNNN`` (tercer digito 9: no corresponde a una persona natural), celulares
``0900NNNNNN``, correos ``socioNNNN@example.com`` y transacciones ``DEMO-NNNNN``.

Por que siguen saliendo listas (definicion (d) de R-019): cada mes entra el mismo cupo de socios
y un tercio compra plan anual, repartido por los dias del mes. Asi los ultimos 12 meses dejan
vencimientos hasta casi un anio despues del corte.

Determinista: cada decision sale de un hash de la semilla y de la clave de la decision (sin
``random``: el resultado no depende de la version de Python), la fecha llega solo por
``--fecha-base`` y los metadatos del libro y del zip estan fijos. Una fecha base posterior
conserva las hojas ya cerradas y agrega las nuevas.

Solo necesita la libreria estandar y ``openpyxl``: el comando del demo lo ejecuta en un
contenedor sin el backend. Uso (desde ``Backend/``):
``python scripts/generar_dataset_demo.py --fecha-base 2026-11-02 --salida ../datos-demo``.
"""

import argparse
import calendar
import hashlib
import io
import re
import sys
import zipfile
from collections.abc import Iterator, Sequence
from dataclasses import dataclass
from datetime import date, timedelta
from decimal import Decimal
from pathlib import Path

from openpyxl import Workbook

SEMILLA = "mtabolic-demo-1"
AUTOR = "generar_dataset_demo"
PRIMER_MES = date(2025, 1, 1)
# Antes de esta fecha no hay ciclos suficientes para las garantias del dataset.
FECHA_BASE_MINIMA = date(2026, 11, 2)
HORIZONTE_LISTA = 31

SOCIOS_NUEVOS_POR_MES = 40
MENSUAL = "MENSUAL"
TRIMESTRAL = "TRIMESTRAL"
SEMESTRAL = "SEMESTRAL"
ANUAL = "ANUAL"
DURACION_DIAS = {MENSUAL: 30, TRIMESTRAL: 90, SEMESTRAL: 180, ANUAL: 365}
PRECIO = {
    MENSUAL: Decimal("42.00"),
    TRIMESTRAL: Decimal("115.00"),
    SEMESTRAL: Decimal("215.00"),
    ANUAL: Decimal("395.00"),
}
PLAN_ALTERNATIVO = {
    MENSUAL: TRIMESTRAL,
    TRIMESTRAL: MENSUAL,
    SEMESTRAL: TRIMESTRAL,
    ANUAL: SEMESTRAL,
}
FORMAS_PAGO = ("EFECTIVO", "TRANSFERENCIA", "TARJETA DATAFAST")
FACTOR_PROMOCION = Decimal("0.85")
CENTAVOS = Decimal("0.01")

# Probabilidades en tanto por mil: enteros, sin coma flotante.
RENOVACION_BASE = {MENSUAL: 350, TRIMESTRAL: 400, SEMESTRAL: 450, ANUAL: 500}
RENOVACION_POR_CICLO = 110
MAX_CICLOS_CON_EFECTO = 4
RENOVACION_MENOS_POR_PROMOCION = 150
PROMOCION = 250
MISMO_PLAN = 750
REINGRESO = 200

DIAS_HASTA_RENOVAR = 21  # 0..20: siempre dentro de la ventana [T, T+30]
DIAS_MINIMOS_REINGRESO = 45  # fuera de la ventana: el ciclo cuenta como no renovado
DIAS_EXTRA_REINGRESO = 76

ESTADO_NUEVO = "NUEVO"
ESTADO_RENOVACION = "RENOVACION"
ESTADO_REINGRESO = "REINGRESO"

NOMBRES = (
    "Lucia",
    "Mateo",
    "Camila",
    "Diego",
    "Sofia",
    "Tomas",
    "Valentina",
    "Joaquin",
    "Isabella",
    "Martin",
    "Emilia",
    "Samuel",
    "Renata",
    "Jose",
    "Ana",
    "Bruno",
    "Carla",
    "Dario",
    "Elena",
    "Felipe",
    "Gabriela",
    "Hugo",
    "Ines",
    "Julian",
)
# Ningun apellido contiene TOTAL, SUMA ni MONTO: la limpieza descartaria la fila.
APELLIDOS = (
    "Andrade",
    "Benitez",
    "Castillo",
    "Cevallos",
    "Guerrero",
    "Naranjo",
    "Ortiz",
    "Paredes",
    "Ponce",
    "Rivas",
    "Salazar",
    "Villacis",
    "Aguirre",
    "Mena",
    "Rojas",
    "Vega",
    "Luna",
    "Soto",
    "Paz",
    "Reyes",
    "Molina",
    "Tapia",
    "Zambrano",
    "Herrera",
)

MESES = (
    "ENERO",
    "FEBRERO",
    "MARZO",
    "ABRIL",
    "MAYO",
    "JUNIO",
    "JULIO",
    "AGOSTO",
    "SEPTIEMBRE",
    "OCTUBRE",
    "NOVIEMBRE",
    "DICIEMBRE",
)
# Formato de las hojas recientes de los libros (solo titulos de columna).
ENCABEZADO: tuple[str | None, ...] = (
    None,
    "STATUS",
    "FACTURA",
    "NOMBRES Y APELLIDOS",
    "CEDULA",
    "CELULAR",
    "CORREO",
    "TIPO DE PLAN",
    "FECHA INICIO",
    "FECHA FIN",
    "TIPO PAGO",
    "No TRANSACCION",
    "No LOTE T/C",
    "MONTO FACTURAR",
    "MONTO A COBRAR",
    "NUTRIC",
)

_FORMATO_FECHA = re.compile(r"\d{4}-\d{2}-\d{2}")
_FECHA_ZIP = (2026, 1, 1, 0, 0, 0)
_INSTANTE_FIJO = "2026-01-01T00:00:00Z"
_SISTEMA_UNIX = 3  # ``ZipInfo`` usa el del equipo: fijarlo da los mismos bytes en Windows y Linux


@dataclass(frozen=True, slots=True)
class Membresia:
    numero_socio: int
    ciclo: int
    estado: str
    plan: str
    inicio: date
    pago: str
    monto: Decimal

    @property
    def fin(self) -> date:
        return self.inicio + timedelta(days=DURACION_DIAS[self.plan])


# ------------------------------------------------------------------ decisiones deterministas


def _sorteo(modulo: int, *clave: object) -> int:
    """Entero en ``[0, modulo)`` que solo depende de la semilla y de ``clave``."""
    texto = "|".join(str(parte) for parte in (SEMILLA, *clave))
    return int.from_bytes(hashlib.sha256(texto.encode()).digest()[:8], "big") % modulo


def _ocurre(por_mil: int, *clave: object) -> bool:
    return _sorteo(1000, *clave) < por_mil


def _plan_inicial(indice: int) -> str:
    """Reparto fijo del cupo mensual: 14 anuales, 7 trimestrales, 4 semestrales y 15 mensuales."""
    if indice % 3 == 0:
        return ANUAL
    if indice % 6 == 1:
        return TRIMESTRAL
    if indice % 12 == 2:
        return SEMESTRAL
    return MENSUAL


def _membresia(numero: int, ciclo: int, estado: str, plan: str, inicio: date) -> Membresia:
    promocion = _ocurre(PROMOCION, "promocion", numero, ciclo)
    monto = PRECIO[plan] * FACTOR_PROMOCION if promocion else PRECIO[plan]
    pago = FORMAS_PAGO[_sorteo(len(FORMAS_PAGO), "pago", numero, ciclo)]
    return Membresia(numero, ciclo, estado, plan, inicio, pago, monto.quantize(CENTAVOS))


def _renueva(membresia: Membresia) -> bool:
    """Renuevan mas los socios antiguos y los planes largos; menos quien entro con promocion."""
    por_mil = RENOVACION_BASE[membresia.plan]
    por_mil += min(membresia.ciclo, MAX_CICLOS_CON_EFECTO) * RENOVACION_POR_CICLO
    if membresia.monto < PRECIO[membresia.plan]:
        por_mil -= RENOVACION_MENOS_POR_PROMOCION
    return _ocurre(por_mil, "renueva", membresia.numero_socio, membresia.ciclo)


def _siguiente(membresia: Membresia) -> Membresia | None:
    """Membresia que sigue a ``membresia``, o ``None`` si el socio no vuelve."""
    numero, ciclo = membresia.numero_socio, membresia.ciclo
    if _renueva(membresia):
        estado = ESTADO_RENOVACION
        dias = _sorteo(DIAS_HASTA_RENOVAR, "dias", numero, ciclo)
    elif _ocurre(REINGRESO, "reingreso", numero, ciclo):
        estado = ESTADO_REINGRESO
        dias = DIAS_MINIMOS_REINGRESO + _sorteo(DIAS_EXTRA_REINGRESO, "dias", numero, ciclo)
    else:
        return None
    mismo_plan = _ocurre(MISMO_PLAN, "plan", numero, ciclo)
    plan = membresia.plan if mismo_plan else PLAN_ALTERNATIVO[membresia.plan]
    return _membresia(numero, ciclo + 1, estado, plan, membresia.fin + timedelta(days=dias))


def _historia_del_socio(primera: Membresia, corte: date) -> Iterator[Membresia]:
    actual: Membresia | None = primera
    while actual is not None and actual.inicio <= corte:
        yield actual
        actual = _siguiente(actual)


# ------------------------------------------------------------------ calendario


def fecha_corte(fecha_base: date) -> date:
    """Ultimo dia del mes anterior a ``fecha_base``: el ultimo mes cerrado."""
    return fecha_base.replace(day=1) - timedelta(days=1)


def fecha_vigencia(corte: date) -> date:
    """Ultima fecha cuya lista cubre un mes completo de vencimientos de planes anuales."""
    return corte + timedelta(days=DURACION_DIAS[ANUAL] - HORIZONTE_LISTA)


def _meses_hasta(corte: date) -> Iterator[date]:
    mes = PRIMER_MES
    while mes <= corte:
        yield mes
        mes = (mes + timedelta(days=calendar.monthrange(mes.year, mes.month)[1])).replace(day=1)


def simular(corte: date) -> list[Membresia]:
    """Membresias con inicio hasta ``corte``, en orden cronologico."""
    membresias: list[Membresia] = []
    for posicion, mes in enumerate(_meses_hasta(corte)):
        dias_del_mes = calendar.monthrange(mes.year, mes.month)[1]
        for indice in range(SOCIOS_NUEVOS_POR_MES):
            numero = posicion * SOCIOS_NUEVOS_POR_MES + indice + 1
            dia = 1 + indice * dias_del_mes // SOCIOS_NUEVOS_POR_MES
            primera = _membresia(
                numero, 0, ESTADO_NUEVO, _plan_inicial(indice), mes.replace(day=dia)
            )
            membresias.extend(_historia_del_socio(primera, corte))
    return sorted(membresias, key=lambda m: (m.inicio, m.numero_socio, m.ciclo))


# ------------------------------------------------------------------ libros


def _nombre(numero: int) -> str:
    nombre = NOMBRES[numero % len(NOMBRES)]
    apellido = APELLIDOS[numero // len(NOMBRES) % len(APELLIDOS)]
    return f"{nombre} Demo {apellido}"


def _fila(membresia: Membresia, secuencia: int) -> tuple[object, ...]:
    numero = membresia.numero_socio
    return (
        None,
        membresia.estado,
        f"001-001-{secuencia:06d}",
        _nombre(numero),
        f"0999{numero:06d}",
        f"0900{numero:06d}",
        f"socio{numero:04d}@example.com",
        membresia.plan,
        membresia.inicio,
        membresia.fin,
        membresia.pago,
        f"DEMO-{secuencia:05d}",
        None,
        membresia.monto,
        membresia.monto,
        None,
    )


def _libro(anio: int, meses: Sequence[int], filas: dict[int, list[tuple[object, ...]]]) -> Workbook:
    libro = Workbook()
    libro.remove(libro.worksheets[0])
    libro.properties.creator = AUTOR
    libro.properties.lastModifiedBy = AUTOR
    libro.properties.title = f"Control Gym {anio} demo"
    for mes in meses:
        hoja = libro.create_sheet(MESES[mes - 1])
        hoja.append(ENCABEZADO)
        for fila in filas[mes]:
            hoja.append(fila)
    return libro


def _guardar_determinista(libro: Workbook, ruta: Path) -> None:
    """Guarda el libro con metadatos y entradas del zip fijos (mismos bytes en cada ejecucion)."""
    buffer = io.BytesIO()
    libro.save(buffer)
    buffer.seek(0)
    with (
        zipfile.ZipFile(buffer) as origen,
        zipfile.ZipFile(ruta, "w", zipfile.ZIP_DEFLATED) as destino,
    ):
        for entrada in origen.infolist():
            datos = origen.read(entrada.filename)
            if entrada.filename == "docProps/core.xml":
                datos = re.sub(
                    rb"(<dcterms:(?:created|modified)[^>]*>)[^<]*",
                    rb"\g<1>" + _INSTANTE_FIJO.encode(),
                    datos,
                )
            fija = zipfile.ZipInfo(entrada.filename, date_time=_FECHA_ZIP)
            fija.compress_type = zipfile.ZIP_DEFLATED
            fija.create_system = _SISTEMA_UNIX
            fija.external_attr = 0o600 << 16
            destino.writestr(fija, datos)


def generar(fecha_base: date, salida: Path) -> list[Path]:
    """Escribe los libros y ``vigencia.txt`` en ``salida``; devuelve las rutas escritas."""
    corte = fecha_corte(fecha_base)
    filas: dict[int, dict[int, list[tuple[object, ...]]]] = {}
    for mes in _meses_hasta(corte):
        filas.setdefault(mes.year, {})[mes.month] = []
    for secuencia, membresia in enumerate(simular(corte), start=1):
        filas[membresia.inicio.year][membresia.inicio.month].append(_fila(membresia, secuencia))

    salida.mkdir(parents=True, exist_ok=True)
    rutas: list[Path] = []
    for anio, por_mes in filas.items():
        ruta = salida / f"Control Gym {anio} demo.xlsx"
        _guardar_determinista(_libro(anio, sorted(por_mes), por_mes), ruta)
        rutas.append(ruta)
    vigencia = salida / "vigencia.txt"
    # En bytes: con texto, Windows escribiria CRLF y el archivo dependeria del sistema.
    vigencia.write_bytes(f"{fecha_vigencia(corte).isoformat()}\n".encode("ascii"))
    rutas.append(vigencia)
    return rutas


# ------------------------------------------------------------------ punto de entrada


def _fecha(texto: str) -> date:
    if _FORMATO_FECHA.fullmatch(texto) is None:
        raise argparse.ArgumentTypeError("la fecha debe tener el formato AAAA-MM-DD")
    try:
        return date.fromisoformat(texto)
    except ValueError as error:
        raise argparse.ArgumentTypeError("la fecha no existe en el calendario") from error


def main(argumentos: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Genera el dataset sintetico del demo.")
    parser.add_argument("--fecha-base", type=_fecha, required=True, help="AAAA-MM-DD")
    parser.add_argument("--salida", type=Path, required=True, help="carpeta de destino")
    opciones = parser.parse_args(argumentos)
    if opciones.fecha_base < FECHA_BASE_MINIMA:
        parser.error(f"--fecha-base debe ser {FECHA_BASE_MINIMA.isoformat()} o posterior")
    for ruta in generar(opciones.fecha_base, opciones.salida):
        print(ruta.name)
    return 0


if __name__ == "__main__":
    sys.exit(main())
