"""Validacion por fila de la hoja ``Registros`` (CU-01, columnas A..N; decisiones (e) y (h)).

``validar_fila`` devuelve la fila convertida (``FilaValida``) o **todos** sus errores. Los
motivos citan la columna, nunca el valor de la celda (RN-01.4). Los montos son ``Decimal``
(RN-01.1); el estado del registro es solo informativo (RN-01.7).
"""

import re
from dataclasses import dataclass, field
from datetime import date, datetime
from decimal import Decimal, InvalidOperation

from app.domain.cargas.documento import documento_valido, es_pasaporte, normalizar_documento
from app.domain.cargas.fila import FilaPlantilla
from app.domain.common.enums import EstadoRegistro, FormaPago, Plan
from app.domain.historico.normalizacion import normalizar_nombre

FECHA_MINIMA = date(2024, 1, 1)
FECHA_MAXIMA = date(2035, 12, 31)
DURACION_MINIMA_DIAS = 21
DURACION_MAXIMA_DIAS = 400
ASISTENCIAS_MAXIMAS = 400
MINIMO_LETRAS_NOMBRE = 5

FORMAS_PAGO_PLANTILLA: frozenset[FormaPago] = frozenset(FormaPago) - {FormaPago.SIN_DATO}
"""``SIN_DATO`` es solo del historico: la plantilla exige una forma de pago del catalogo."""

_CENTAVO = Decimal("0.01")
_DIEZ_DIGITOS = re.compile(r"[0-9]{10}")
_CORREO = re.compile(r"[^@\s]+@[^@\s]+\.[^@\s]+")
_FECHA_ISO = re.compile(r"[0-9]{4}-[0-9]{2}-[0-9]{2}")
_NUMERO = re.compile(r"-?[0-9]+(\.[0-9]+)?")


@dataclass(frozen=True, slots=True)
class ErrorFila:
    """Error de una fila: numero de fila de Excel, letra de columna y motivo sin valores."""

    fila: int
    columna: str
    motivo: str


@dataclass(frozen=True, slots=True)
class FilaValida:
    """Fila sin errores, con los valores ya convertidos. El ``repr`` omite datos personales."""

    fila: int
    estado_registro: EstadoRegistro | None
    nombre: str = field(repr=False)
    nombre_normalizado: str = field(repr=False)
    documento: str = field(repr=False)
    celular: str | None = field(repr=False)
    correo: str | None = field(repr=False)
    plan: Plan
    plan_original: str
    fecha_inicio: date
    fecha_vencimiento: date
    forma_pago: FormaPago
    forma_pago_original: str
    monto_facturado: Decimal | None
    monto_cobrado: Decimal
    asistencias: int | None
    observaciones: str | None = field(repr=False)


class _ValorInvalidoError(Exception):
    """Uso interno: el valor de la celda no se pudo convertir."""


def _texto(valor: object) -> str:
    if valor is None:
        return ""
    if isinstance(valor, float) and valor.is_integer():
        return str(int(valor))
    return str(valor).strip()


def _opcional(valor: object) -> str | None:
    return _texto(valor) or None


def _fecha(valor: object) -> date | None:
    """``None`` si la celda esta vacia; error si no es fecha ni texto ``AAAA-MM-DD``."""
    if isinstance(valor, datetime):
        return valor.date()
    if isinstance(valor, date):
        return valor
    if valor is not None and not isinstance(valor, str):
        raise _ValorInvalidoError
    texto = _texto(valor)
    if texto == "":
        return None
    if not _FECHA_ISO.fullmatch(texto):
        raise _ValorInvalidoError
    try:
        return date.fromisoformat(texto)
    except ValueError as error:
        raise _ValorInvalidoError from error


def _decimal(valor: object) -> Decimal | None:
    """``None`` si vacia; error si no es numero (texto admite punto o coma decimal)."""
    if isinstance(valor, bool):
        raise _ValorInvalidoError
    if isinstance(valor, int):
        return Decimal(valor)
    if isinstance(valor, float):
        numero = Decimal(repr(valor))
        if not numero.is_finite():
            raise _ValorInvalidoError
        return numero
    texto = _texto(valor)
    if texto == "":
        return None
    if "," in texto and "." in texto:
        raise _ValorInvalidoError
    texto = texto.replace(",", ".")
    if not _NUMERO.fullmatch(texto):
        raise _ValorInvalidoError
    try:
        return Decimal(texto)
    except InvalidOperation as error:  # pragma: no cover - la expresion regular lo impide
        raise _ValorInvalidoError from error


def _en_catalogo[E: (EstadoRegistro, Plan, FormaPago)](
    valor: object, catalogo: type[E], permitidos: frozenset[E] | None = None
) -> E | None:
    """Miembro del catalogo (``strip().upper()``); ``None`` si vacio; error si no esta."""
    texto = _texto(valor).upper()
    if texto == "":
        return None
    try:
        miembro = catalogo(texto)
    except ValueError as error:
        raise _ValorInvalidoError from error
    if permitidos is not None and miembro not in permitidos:
        raise _ValorInvalidoError
    return miembro


class _Validador:
    """Acumula los errores de una fila mientras convierte cada columna."""

    def __init__(self, fila: FilaPlantilla) -> None:
        self.fila = fila
        self.errores: list[ErrorFila] = []

    def error(self, columna: str, motivo: str) -> None:
        self.errores.append(ErrorFila(self.fila.fila, columna, motivo))

    def estado(self) -> EstadoRegistro | None:
        try:
            return _en_catalogo(self.fila.estado_registro, EstadoRegistro)
        except _ValorInvalidoError:
            self.error("A", "El estado del registro no está en el catálogo.")
            return None

    def nombre(self) -> tuple[str, str]:
        nombre = _texto(self.fila.nombre)
        normalizado = normalizar_nombre(nombre)
        if nombre == "":
            self.error("B", "Falta el nombre.")
        elif len(normalizado.replace(" ", "")) < MINIMO_LETRAS_NOMBRE:
            self.error("B", "El nombre debe tener al menos 5 letras.")
        return nombre, normalizado

    def documento(self, observaciones: str | None) -> str:
        documento = normalizar_documento(self.fila.cedula)
        if documento == "":
            self.error("C", "Falta la cédula.")
        elif documento_valido(documento, observaciones):
            pass
        elif es_pasaporte(observaciones):
            self.error("C", "El pasaporte debe tener de 5 a 20 letras o números.")
        elif not _DIEZ_DIGITOS.fullmatch(documento):
            self.error("C", "La cédula debe tener 10 dígitos.")
        else:
            self.error("C", "La cédula no tiene un dígito verificador válido.")
        return documento

    def correo(self) -> str | None:
        correo = _opcional(self.fila.correo)
        if correo is not None and not _CORREO.fullmatch(correo):
            self.error("E", "El correo no tiene un formato válido.")
        return correo

    def plan(self) -> Plan | None:
        try:
            plan = _en_catalogo(self.fila.plan, Plan)
        except _ValorInvalidoError:
            self.error("F", "El tipo de plan no está en el catálogo.")
            return None
        if plan is None:
            self.error("F", "Falta el tipo de plan.")
        return plan

    def fecha(self, valor: object, columna: str, nombre: str) -> date | None:
        try:
            fecha = _fecha(valor)
        except _ValorInvalidoError:
            self.error(columna, f"La fecha de {nombre} no es una fecha válida.")
            return None
        if fecha is None:
            self.error(columna, f"Falta la fecha de {nombre}.")
        elif not FECHA_MINIMA <= fecha <= FECHA_MAXIMA:
            self.error(columna, f"La fecha de {nombre} debe estar entre 2024-01-01 y 2035-12-31.")
            return None
        return fecha

    def duracion(self, inicio: date, vencimiento: date, plan: Plan | None) -> None:
        dias = (vencimiento - inicio).days
        if dias <= 0:
            self.error("H", "La fecha de vencimiento debe ser posterior a la de inicio.")
        elif dias > DURACION_MAXIMA_DIAS:
            self.error("H", "La duración es mayor a 400 días; revise las fechas.")
        elif plan is not None and plan is not Plan.DIARIO and dias < DURACION_MINIMA_DIAS:
            self.error("H", "La duración es menor a 21 días; revise las fechas.")

    def forma_pago(self) -> FormaPago | None:
        try:
            forma = _en_catalogo(self.fila.forma_pago, FormaPago, FORMAS_PAGO_PLANTILLA)
        except _ValorInvalidoError:
            self.error("I", "La forma de pago no está en el catálogo.")
            return None
        if forma is None:
            self.error("I", "Falta la forma de pago.")
        return forma

    def monto(self, valor: object, columna: str, nombre: str, obligatorio: bool) -> Decimal | None:
        try:
            monto = _decimal(valor)
        except _ValorInvalidoError:
            self.error(columna, f"El {nombre} no es un número válido.")
            return None
        if monto is None:
            if obligatorio:
                self.error(columna, f"Falta el {nombre}.")
            return None
        if monto < 0:
            self.error(columna, f"El {nombre} no puede ser negativo.")
            return None
        if monto != monto.quantize(_CENTAVO):
            self.error(columna, f"El {nombre} admite como máximo 2 decimales.")
            return None
        return monto

    def asistencias(self) -> int | None:
        motivo = "Las asistencias deben ser un número entero entre 0 y 400."
        try:
            numero = _decimal(self.fila.asistencias)
        except _ValorInvalidoError:
            self.error("M", motivo)
            return None
        if numero is None:
            return None
        if numero != numero.to_integral_value() or not 0 <= numero <= ASISTENCIAS_MAXIMAS:
            self.error("M", motivo)
            return None
        return int(numero)


def validar_fila(fila: FilaPlantilla) -> FilaValida | tuple[ErrorFila, ...]:
    """Valida y convierte las columnas A..N; devuelve la fila valida o todos sus errores."""
    v = _Validador(fila)
    observaciones = _opcional(fila.observaciones)
    estado = v.estado()
    nombre, nombre_normalizado = v.nombre()
    documento = v.documento(observaciones)
    correo = v.correo()
    plan = v.plan()
    inicio = v.fecha(fila.fecha_inicio, "G", "inicio")
    vencimiento = v.fecha(fila.fecha_vencimiento, "H", "vencimiento")
    if inicio is not None and vencimiento is not None:
        v.duracion(inicio, vencimiento, plan)
    forma_pago = v.forma_pago()
    facturado = v.monto(fila.monto_facturado, "K", "monto a facturar", obligatorio=False)
    cobrado = v.monto(fila.monto_cobrado, "L", "monto cobrado", obligatorio=True)
    asistencias = v.asistencias()

    # Un obligatorio en None siempre deja un error registrado; la comprobacion informa a mypy.
    if (
        v.errores
        or plan is None
        or forma_pago is None
        or cobrado is None
        or inicio is None
        or vencimiento is None
    ):
        return tuple(v.errores)
    return FilaValida(
        fila=fila.fila,
        estado_registro=estado,
        nombre=nombre,
        nombre_normalizado=nombre_normalizado,
        documento=documento,
        celular=_opcional(fila.celular),
        correo=correo,
        plan=plan,
        plan_original=_texto(fila.plan),
        fecha_inicio=inicio,
        fecha_vencimiento=vencimiento,
        forma_pago=forma_pago,
        forma_pago_original=_texto(fila.forma_pago),
        monto_facturado=facturado,
        monto_cobrado=cobrado,
        asistencias=asistencias,
        observaciones=observaciones,
    )
