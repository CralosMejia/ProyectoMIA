"""DTOs del modulo dashboard: embudo, resultados por campana, estado del modelo e indicadores
del piloto (CU-11; M04, R-018)."""

from datetime import date, datetime
from decimal import Decimal

from pydantic import BaseModel, ConfigDict, Field, field_serializer

from app.domain.modelo.piloto import EstadoIndicador

# Mes de consulta ``YYYY-MM`` con anio 1900..2999 y mes 01..12. S7 (R-013): el anio acotado
# evita ``date``/``datetime`` fuera de rango (0000-01, 9999-12) que daban 500.
MES_PATTERN = r"^(19|2\d)\d{2}-(0[1-9]|1[0-2])$"


class EmbudoDTO(BaseModel):
    """Embudo del mes sobre las gestiones **con campana** (``asignadas``).

    ``contactadas``: contactado si; ``ofrecidas``/``aceptadas``/``renovaron``: respuesta ``SI``.
    Un valor nulo (sin resultado) nunca cuenta.
    """

    model_config = ConfigDict(frozen=True)

    asignadas: int = Field(ge=0)
    contactadas: int = Field(ge=0)
    ofrecidas: int = Field(ge=0)
    aceptadas: int = Field(ge=0)
    renovaron: int = Field(ge=0)


class ResultadoCampaniaDTO(BaseModel):
    """Cifras descriptivas por campana; ``campania_id`` nulo = gestiones sin campana.

    ``gestiones_cerradas`` = gestiones cerradas **con resultado** (``renovo_declarado`` SI o
    NO). ``tasa_renovacion`` = ``renovaciones / gestiones_cerradas`` con 8 decimales, solo si
    hay al menos 10 cerradas con resultado; si no, nula y ``casos_insuficientes``.
    """

    model_config = ConfigDict(frozen=True)

    campania_id: int | None = None
    nombre: str
    gestiones: int = Field(ge=0)
    contactados: int = Field(ge=0)
    renovaciones: int = Field(ge=0)
    gestiones_cerradas: int = Field(ge=0)
    tasa_renovacion: Decimal | None = Field(default=None, ge=0, le=1)
    casos_insuficientes: bool


class EstadoModeloDTO(BaseModel):
    """Modelo vigente; ``ciclos_nuevos_evaluables`` con la misma regla que CU-02."""

    model_config = ConfigDict(frozen=True)

    version: str
    fecha_entrenamiento: datetime
    ciclos_entrenamiento: int = Field(ge=0)
    proxima_fecha_reentrenamiento: date | None = None
    ciclos_nuevos_evaluables: int = Field(ge=0)


def _decimal_fijo(valor: Decimal | None) -> str | None:
    # Notacion fija: ``Decimal("0E-8")`` saldria como "0E-8" con ``str``.
    return None if valor is None else format(valor, "f")


class IndicadorProporcionDTO(BaseModel):
    """``valor = numerador / denominador`` con 8 decimales (string), nulo sin denominador.

    ``n`` = casos considerados; ``pendientes`` = casos aun sin verificar a los 30 dias.
    """

    model_config = ConfigDict(frozen=True)

    valor: Decimal | None = Field(default=None, ge=0, le=1)
    numerador: int = Field(ge=0)
    denominador: int = Field(ge=0)
    n: int = Field(ge=0)
    pendientes: int = Field(ge=0)
    estado: EstadoIndicador

    @field_serializer("valor")
    def _serializar_valor(self, valor: Decimal | None) -> str | None:
        return _decimal_fijo(valor)


class IndicadorDiasDTO(BaseModel):
    """Promedio de dias entre el contacto y el vencimiento (1 decimal; puede ser <= 0)."""

    model_config = ConfigDict(frozen=True)

    valor: Decimal | None = None
    n: int = Field(ge=0)
    estado: EstadoIndicador

    @field_serializer("valor")
    def _serializar_valor(self, valor: Decimal | None) -> str | None:
        return _decimal_fijo(valor)


class IndicadorMontoDTO(BaseModel):
    """Monto retenido (2 decimales, string) de los contactados verificados que renovaron."""

    model_config = ConfigDict(frozen=True)

    total: Decimal | None = Field(default=None, ge=0)
    renovaciones: int = Field(ge=0)
    renovaciones_sin_monto: int = Field(ge=0)
    n: int = Field(ge=0)
    pendientes: int = Field(ge=0)
    estado: EstadoIndicador

    @field_serializer("total")
    def _serializar_total(self, total: Decimal | None) -> str | None:
        return _decimal_fijo(total)


class ListaPilotoDTO(BaseModel):
    model_config = ConfigDict(frozen=True)

    id: int
    nombre: str
    fecha_generacion: date


class IndicadoresPilotoDTO(BaseModel):
    """Indicadores del piloto sobre el top 25 de la lista del mes (cifras observadas, no
    causales). Sin lista en el mes -> ``estado = "SIN_DATOS"`` y ``lista`` nula.

    ``corte_verificacion`` = ultimo dia con datos (nulo si no hay ni modelo ni cargas);
    ``n_top`` = filas del top; ``sin_dato`` = filas sin vencimiento (fuera de los ``n``).
    """

    model_config = ConfigDict(frozen=True)

    estado: EstadoIndicador
    lista: ListaPilotoDTO | None = None
    corte_verificacion: date | None = None
    n_top: int = Field(ge=0)
    sin_dato: int = Field(ge=0)
    precision_top25: IndicadorProporcionDTO
    contactados_antes_vencimiento: IndicadorProporcionDTO
    dias_anticipacion: IndicadorDiasDTO
    tasa_renovacion_contactados: IndicadorProporcionDTO
    monto_retenido: IndicadorMontoDTO


class DashboardDTO(BaseModel):
    model_config = ConfigDict(frozen=True)

    mes: str = Field(pattern=MES_PATTERN)
    embudo: EmbudoDTO
    por_campania: list[ResultadoCampaniaDTO]
    estado_modelo: EstadoModeloDTO | None = None
    piloto: IndicadoresPilotoDTO
