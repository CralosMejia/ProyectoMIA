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

Perfil ``grabacion`` (R-022, ``--perfil grabacion``): la misma simulacion con otra semilla y
mas promociones que no renuevan (``REGLAS_GRABACION``: la lista muestra el nivel ALTO), para
grabar el demo con datos que parecen de un gimnasio real. Nombres con dos apellidos de las mismas
listas y **sin** la marca ``Demo``, correos ``nombre.apellidoN@example.com``, transacciones
``GRAB-NNNNN`` y libros ``Control Gym <anio>.xlsx``; cedulas y celulares como en el demo. Su
salida (``datos-grabacion/``) no se versiona: se regenera con la fecha del dia.

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
from collections.abc import Callable, Iterator, Mapping, Sequence
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


@dataclass(frozen=True, slots=True)
class Reglas:
    """Semilla y probabilidades (tanto por mil) que cambian entre perfiles."""

    semilla: str
    renovacion_base: Mapping[str, int]
    menos_por_promocion: int
    promocion: int


REGLAS_DEMO = Reglas(SEMILLA, RENOVACION_BASE, RENOVACION_MENOS_POR_PROMOCION, PROMOCION)
# Grabacion: mas promociones, y los socios nuevos de plan mensual o trimestral que entraron con
# promocion no renuevan. Con las reglas del demo el modelo no pasa de 0,69 y la lista no muestra
# el nivel ALTO (>= 0,70); con estas, la lista tiene socios en ALTO tambien a fin de mes (fechas
# base probadas cada 4 dias de 2026-11-03 a 2027-05).
REGLAS_GRABACION = Reglas(
    "mtabolic-grabacion-1",
    {MENSUAL: 250, TRIMESTRAL: 300, SEMESTRAL: 450, ANUAL: 500},
    menos_por_promocion=400,
    promocion=400,
)

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


def _sorteo(reglas: Reglas, modulo: int, *clave: object) -> int:
    """Entero en ``[0, modulo)`` que solo depende de la semilla de ``reglas`` y de ``clave``."""
    texto = "|".join(str(parte) for parte in (reglas.semilla, *clave))
    return int.from_bytes(hashlib.sha256(texto.encode()).digest()[:8], "big") % modulo


def _ocurre(reglas: Reglas, por_mil: int, *clave: object) -> bool:
    return _sorteo(reglas, 1000, *clave) < por_mil


def _plan_inicial(indice: int) -> str:
    """Reparto fijo del cupo mensual: 14 anuales, 7 trimestrales, 4 semestrales y 15 mensuales."""
    if indice % 3 == 0:
        return ANUAL
    if indice % 6 == 1:
        return TRIMESTRAL
    if indice % 12 == 2:
        return SEMESTRAL
    return MENSUAL


def _membresia(
    reglas: Reglas, numero: int, ciclo: int, estado: str, plan: str, inicio: date
) -> Membresia:
    promocion = _ocurre(reglas, reglas.promocion, "promocion", numero, ciclo)
    monto = PRECIO[plan] * FACTOR_PROMOCION if promocion else PRECIO[plan]
    pago = FORMAS_PAGO[_sorteo(reglas, len(FORMAS_PAGO), "pago", numero, ciclo)]
    return Membresia(numero, ciclo, estado, plan, inicio, pago, monto.quantize(CENTAVOS))


def _renueva(reglas: Reglas, membresia: Membresia) -> bool:
    """Renuevan mas los socios antiguos y los planes largos; menos quien entro con promocion."""
    por_mil = reglas.renovacion_base[membresia.plan]
    por_mil += min(membresia.ciclo, MAX_CICLOS_CON_EFECTO) * RENOVACION_POR_CICLO
    if membresia.monto < PRECIO[membresia.plan]:
        por_mil -= reglas.menos_por_promocion
    return _ocurre(reglas, por_mil, "renueva", membresia.numero_socio, membresia.ciclo)


def _siguiente(reglas: Reglas, membresia: Membresia) -> Membresia | None:
    """Membresia que sigue a ``membresia``, o ``None`` si el socio no vuelve."""
    numero, ciclo = membresia.numero_socio, membresia.ciclo
    if _renueva(reglas, membresia):
        estado = ESTADO_RENOVACION
        dias = _sorteo(reglas, DIAS_HASTA_RENOVAR, "dias", numero, ciclo)
    elif _ocurre(reglas, REINGRESO, "reingreso", numero, ciclo):
        estado = ESTADO_REINGRESO
        extra = _sorteo(reglas, DIAS_EXTRA_REINGRESO, "dias", numero, ciclo)
        dias = DIAS_MINIMOS_REINGRESO + extra
    else:
        return None
    mismo_plan = _ocurre(reglas, MISMO_PLAN, "plan", numero, ciclo)
    plan = membresia.plan if mismo_plan else PLAN_ALTERNATIVO[membresia.plan]
    inicio = membresia.fin + timedelta(days=dias)
    return _membresia(reglas, numero, ciclo + 1, estado, plan, inicio)


def _historia_del_socio(reglas: Reglas, primera: Membresia, corte: date) -> Iterator[Membresia]:
    actual: Membresia | None = primera
    while actual is not None and actual.inicio <= corte:
        yield actual
        actual = _siguiente(reglas, actual)


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


def simular(corte: date, reglas: Reglas = REGLAS_DEMO) -> list[Membresia]:
    """Membresias con inicio hasta ``corte``, en orden cronologico."""
    membresias: list[Membresia] = []
    for posicion, mes in enumerate(_meses_hasta(corte)):
        dias_del_mes = calendar.monthrange(mes.year, mes.month)[1]
        for indice in range(SOCIOS_NUEVOS_POR_MES):
            numero = posicion * SOCIOS_NUEVOS_POR_MES + indice + 1
            dia = 1 + indice * dias_del_mes // SOCIOS_NUEVOS_POR_MES
            primera = _membresia(
                reglas, numero, 0, ESTADO_NUEVO, _plan_inicial(indice), mes.replace(day=dia)
            )
            membresias.extend(_historia_del_socio(reglas, primera, corte))
    return sorted(membresias, key=lambda m: (m.inicio, m.numero_socio, m.ciclo))


# ------------------------------------------------------------------ libros


def _nombre(numero: int) -> str:
    nombre = NOMBRES[numero % len(NOMBRES)]
    apellido = APELLIDOS[numero // len(NOMBRES) % len(APELLIDOS)]
    return f"{nombre} Demo {apellido}"


def _correo_demo(numero: int) -> str:
    return f"socio{numero:04d}@example.com"


def _partes_grabacion(numero: int) -> tuple[str, str, str]:
    """Nombre y dos apellidos; la combinacion no se repite hasta el socio 13 824.

    Con ``numero % 24`` y ``numero // 24 % 24`` fijos, el segundo apellido avanza de 7 en 7
    (primo con 24) en cada bloque de 576 socios: no se repite en 24 bloques.
    """
    total = len(APELLIDOS)
    resto, bloque = numero % len(NOMBRES), numero // len(NOMBRES)
    segundo = (5 * resto + 11 * bloque + 7 * (bloque // total)) % total
    return NOMBRES[resto], APELLIDOS[bloque % total], APELLIDOS[segundo]


def _nombre_grabacion(numero: int) -> str:
    return " ".join(_partes_grabacion(numero))


def _correo_grabacion(numero: int) -> str:
    nombre, apellido, _ = _partes_grabacion(numero)
    return f"{nombre.lower()}.{apellido.lower()}{numero}@example.com"


def _cedula_demo(numero: int) -> str:
    return f"0999{numero:06d}"


def _cedula_grabacion(numero: int) -> str:
    """``0999`` + 5 digitos + verificador modulo 10: la plantilla de carga (CU-01) lo exige."""
    base = f"0999{numero:05d}"
    total = 0
    for posicion, caracter in enumerate(base):
        producto = int(caracter) * (2 if posicion % 2 == 0 else 1)
        total += producto - 9 if producto > 9 else producto
    return f"{base}{(10 - total % 10) % 10}"


@dataclass(frozen=True, slots=True)
class Perfil:
    """Variante del dataset: la misma simulacion con otras reglas y otros datos ficticios.

    ``meses_en_plantilla`` > 0: los ultimos N meses cerrados no van a los libros sino a una
    plantilla de carga (CU-01) por mes, para cargarlos despues de generar cada lista pasada.
    """

    reglas: Reglas
    sufijo_libro: str
    prefijo_transaccion: str
    nombre: Callable[[int], str]
    correo: Callable[[int], str]
    cedula: Callable[[int], str]
    meses_en_plantilla: int = 0


PERFIL_POR_DEFECTO = "demo"
MESES_EN_PLANTILLA_GRABACION = 4
PERFILES = {
    PERFIL_POR_DEFECTO: Perfil(REGLAS_DEMO, " demo", "DEMO", _nombre, _correo_demo, _cedula_demo),
    # Para grabar el demo: parece un gimnasio real, pero todo sigue siendo inventado.
    "grabacion": Perfil(
        REGLAS_GRABACION,
        "",
        "GRAB",
        _nombre_grabacion,
        _correo_grabacion,
        _cedula_grabacion,
        MESES_EN_PLANTILLA_GRABACION,
    ),
}

# Formato de la plantilla oficial de carga (hoja ``Registros``, titulos A..N de CU-01).
HOJA_PLANTILLA = "Registros"
TITULOS_PLANTILLA = (
    "ESTADO DEL REGISTRO",
    "NOMBRES Y APELLIDOS",
    "CÉDULA",
    "CELULAR",
    "CORREO",
    "TIPO DE PLAN",
    "FECHA DE INICIO",
    "FECHA DE VENCIMIENTO",
    "FORMA DE PAGO",
    "N.º DE TRANSACCIÓN",
    "MONTO A FACTURAR (USD)",
    "MONTO COBRADO (USD)",
    "ASISTENCIAS EN EL PERÍODO",
    "OBSERVACIONES",
)
# Catalogo de la plantilla (la de los libros escribe "TARJETA DATAFAST").
FORMA_PAGO_PLANTILLA = {
    "EFECTIVO": "EFECTIVO",
    "TRANSFERENCIA": "TRANSFERENCIA",
    "TARJETA DATAFAST": "TARJETA_DATAFAST",
}


def _fila(membresia: Membresia, secuencia: int, perfil: Perfil) -> tuple[object, ...]:
    numero = membresia.numero_socio
    return (
        None,
        membresia.estado,
        f"001-001-{secuencia:06d}",
        perfil.nombre(numero),
        perfil.cedula(numero),
        f"0900{numero:06d}",
        perfil.correo(numero),
        membresia.plan,
        membresia.inicio,
        membresia.fin,
        membresia.pago,
        f"{perfil.prefijo_transaccion}-{secuencia:05d}",
        None,
        membresia.monto,
        membresia.monto,
        None,
    )


def _fila_plantilla(membresia: Membresia, secuencia: int, perfil: Perfil) -> tuple[object, ...]:
    numero = membresia.numero_socio
    return (
        membresia.estado,
        perfil.nombre(numero),
        perfil.cedula(numero),
        f"0900{numero:06d}",
        perfil.correo(numero),
        membresia.plan,
        membresia.inicio,
        membresia.fin,
        FORMA_PAGO_PLANTILLA[membresia.pago],
        f"{perfil.prefijo_transaccion}-{secuencia:05d}",
        membresia.monto,
        membresia.monto,
        None,
        None,
    )


def _libro(
    titulo: str, meses: Sequence[int], filas: dict[int, list[tuple[object, ...]]]
) -> Workbook:
    libro = Workbook()
    libro.remove(libro.worksheets[0])
    libro.properties.creator = AUTOR
    libro.properties.lastModifiedBy = AUTOR
    libro.properties.title = titulo
    for mes in meses:
        hoja = libro.create_sheet(MESES[mes - 1])
        hoja.append(ENCABEZADO)
        for fila in filas[mes]:
            hoja.append(fila)
    return libro


def _plantilla(titulo: str, filas: Sequence[tuple[object, ...]]) -> Workbook:
    libro = Workbook()
    hoja = libro.worksheets[0]
    hoja.title = HOJA_PLANTILLA
    libro.properties.creator = AUTOR
    libro.properties.lastModifiedBy = AUTOR
    libro.properties.title = titulo
    hoja.append(TITULOS_PLANTILLA)
    for fila in filas:
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


def corte_de_libros(fecha_base: date, perfil: Perfil) -> date:
    """Fin del ultimo mes que va a los libros (antes de los meses en plantilla)."""
    corte = fecha_corte(fecha_base)
    for _ in range(perfil.meses_en_plantilla):
        corte = fecha_corte(corte)
    return corte


def nombre_plantilla(mes: date) -> str:
    """``Carga AAAA-MM.xlsx``: sin ``Control``/``Gym``, la migracion inicial no la lee."""
    return f"Carga {mes.year:04d}-{mes.month:02d}.xlsx"


def generar(
    fecha_base: date, salida: Path, perfil: Perfil = PERFILES[PERFIL_POR_DEFECTO]
) -> list[Path]:
    """Escribe libros, plantillas y ``vigencia.txt`` en ``salida``; devuelve las rutas."""
    corte = fecha_corte(fecha_base)
    corte_libros = corte_de_libros(fecha_base, perfil)
    filas: dict[int, dict[int, list[tuple[object, ...]]]] = {}
    for mes in _meses_hasta(corte_libros):
        filas.setdefault(mes.year, {})[mes.month] = []
    plantillas: dict[date, list[tuple[object, ...]]] = {}
    for secuencia, membresia in enumerate(simular(corte, perfil.reglas), start=1):
        if membresia.inicio <= corte_libros:
            fila = _fila(membresia, secuencia, perfil)
            filas[membresia.inicio.year][membresia.inicio.month].append(fila)
        else:
            mes = membresia.inicio.replace(day=1)
            plantillas.setdefault(mes, []).append(_fila_plantilla(membresia, secuencia, perfil))

    salida.mkdir(parents=True, exist_ok=True)
    rutas: list[Path] = []
    for anio, por_mes in filas.items():
        titulo = f"Control Gym {anio}{perfil.sufijo_libro}"
        ruta = salida / f"{titulo}.xlsx"
        _guardar_determinista(_libro(titulo, sorted(por_mes), por_mes), ruta)
        rutas.append(ruta)
    for mes, filas_mes in sorted(plantillas.items()):
        ruta = salida / nombre_plantilla(mes)
        _guardar_determinista(_plantilla(ruta.stem, filas_mes), ruta)
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
    parser.add_argument(
        "--perfil",
        choices=sorted(PERFILES),
        default=PERFIL_POR_DEFECTO,
        help="demo (por defecto) o grabacion (datos para grabar, sin la marca Demo)",
    )
    opciones = parser.parse_args(argumentos)
    if opciones.fecha_base < FECHA_BASE_MINIMA:
        parser.error(f"--fecha-base debe ser {FECHA_BASE_MINIMA.isoformat()} o posterior")
    for ruta in generar(opciones.fecha_base, opciones.salida, PERFILES[opciones.perfil]):
        print(ruta.name)
    return 0


if __name__ == "__main__":
    sys.exit(main())
