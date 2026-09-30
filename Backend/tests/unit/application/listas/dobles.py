"""Dobles en memoria de los puertos de listas (sin base de datos ni scikit-learn).

Datos 100 % sinteticos: ningun nombre, celular ni cedula real.
"""

from collections.abc import Callable, Iterator, Sequence
from contextlib import AbstractContextManager, contextmanager
from dataclasses import dataclass, field
from datetime import UTC, date, datetime
from decimal import Decimal

from app.application.historial.ports import MembresiaParaPrediccion, NuevaMembresia
from app.application.listas.ports import (
    ContextoListas,
    ItemLista,
    ListaDetalle,
    ListaResumen,
    NuevaLista,
    NuevaPrediccion,
)
from app.application.modelo.ports import EstadoSistema, ModeloGuardado, NuevoModelo
from app.domain.common.enums import EstadoMigracion, FormaPago, Plan
from app.domain.common.predictor import FeatureRow, Prediction, TrainedModel

# Reloj por defecto el 2026-08-31 (tambien en Ecuador), la fecha de referencia de las pruebas.
INSTANTE = datetime(2026, 8, 31, 12, 0, tzinfo=UTC)


class RelojFijo:
    def __init__(self, instante: datetime = INSTANTE) -> None:
        self.instante = instante

    def now(self) -> datetime:
        return self.instante


def membresia(
    membresia_id: int,
    socio_id: int,
    inicio: date | None,
    vence: date | None,
    *,
    plan: Plan = Plan.MENSUAL,
    monto: Decimal | None = Decimal("40"),
    actividad: date | None = None,
    con_cedula: bool = True,
) -> MembresiaParaPrediccion:
    fecha_actividad = actividad or inicio
    assert fecha_actividad is not None
    return MembresiaParaPrediccion(
        membresia_id=membresia_id,
        socio_id=socio_id,
        plan=plan,
        forma_pago=FormaPago.EFECTIVO,
        fecha_inicio=inicio,
        fecha_vencimiento=vence,
        fecha_actividad=fecha_actividad,
        monto_cobrado=monto,
        inicio_aproximado=inicio is None,
        socio_con_cedula=con_cedula,
    )


def cedula_sintetica(m: MembresiaParaPrediccion) -> str | None:
    """Cedula inventada con cero inicial, o ``None`` si el socio no tiene cedula."""
    return f"09{m.socio_id:08d}" if m.socio_con_cedula else None


def modelo(
    modelo_id: int,
    version: int,
    *,
    alto: str = "0.70000000",
    medio: str = "0.50000000",
    metadata: dict[str, object] | None = None,
) -> ModeloGuardado:
    return ModeloGuardado(
        id=modelo_id,
        version=version,
        fecha_entrenamiento=INSTANTE,
        ciclos_entrenamiento=100,
        periodo_desde=date(2025, 1, 1),
        periodo_hasta=date(2026, 7, 31),
        prevalencia=Decimal("0.4"),
        umbral_alto=Decimal(alto),
        umbral_medio=Decimal(medio),
        porcentajes_umbral={"ALTO": 20, "MEDIO": 30, "BAJO": 50},
        artefacto=f"artefacto-v{version}".encode(),
        metadata_tecnica=metadata
        if metadata is not None
        else {"medianas_monto": {"por_plan": {"MENSUAL": "45"}, "general": "50"}},
    )


class PredictorPorMonto:
    """``score = monto_actual / 100``; registra cada llamada."""

    def __init__(self, error: Exception | None = None) -> None:
        self.llamadas: list[tuple[bytes, list[FeatureRow]]] = []
        self._error = error

    def train(
        self,
        features: Sequence[FeatureRow],
        labels: Sequence[int],
        numericas: Sequence[str],
        categoricas: Sequence[str],
        referencia: Sequence[FeatureRow] | None = None,
    ) -> TrainedModel:
        raise AssertionError("GenerarLista nunca entrena")

    def predict(self, artefacto: bytes, features: Sequence[FeatureRow]) -> list[Prediction]:
        self.llamadas.append((artefacto, list(features)))
        if self._error is not None:
            raise self._error
        predicciones = []
        for fila in features:
            monto = fila["monto_actual"]
            assert isinstance(monto, Decimal)
            factores = ("Plan: MENSUAL (+0,10)",) if monto > 60 else ()
            predicciones.append(Prediction(score=monto / 100, factores_principales=factores))
        return predicciones


@dataclass
class Almacen:
    """Estado compartido por todas las unidades de trabajo de una prueba."""

    membresias: list[MembresiaParaPrediccion] = field(default_factory=list)
    modelos: list[ModeloGuardado] = field(default_factory=list)
    estado: EstadoMigracion = EstadoMigracion.COMPLETADA
    cargas: list[datetime] = field(default_factory=list)
    listas: dict[int, tuple[NuevaLista, list[NuevaPrediccion], datetime]] = field(
        default_factory=dict
    )
    commits: int = 0
    lecturas_membresias: int = 0
    reloj: RelojFijo = field(default_factory=RelojFijo)


class ListasEnMemoria:
    def __init__(self, almacen: Almacen) -> None:
        self._a = almacen

    def crear(self, lista: NuevaLista, predicciones: Sequence[NuevaPrediccion]) -> int:
        lista_id = len(self._a.listas) + 1
        self._a.listas[lista_id] = (lista, list(predicciones), self._a.reloj.now())
        return lista_id

    def _modelo(self, modelo_id: int) -> ModeloGuardado:
        return next(m for m in self._a.modelos if m.id == modelo_id)

    def obtener(self, lista_id: int) -> ListaDetalle | None:
        if lista_id not in self._a.listas:
            return None
        lista, predicciones, creada_en = self._a.listas[lista_id]
        modelo_lista = self._modelo(lista.modelo_id)
        por_id = {m.membresia_id: m for m in self._a.membresias}
        items = []
        for i, p in enumerate(sorted(predicciones, key=lambda p: p.prioridad)):
            m = por_id[p.membresia_id]
            assert m.fecha_vencimiento is not None
            items.append(
                ItemLista(
                    prediccion_id=lista_id * 1000 + i + 1,
                    membresia_id=p.membresia_id,
                    socio_id=p.socio_id,
                    prioridad=p.prioridad,
                    socio_nombre=f"Socio Sintetico {m.socio_id}",
                    celular=None,
                    cedula=cedula_sintetica(m),
                    plan=m.plan,
                    fecha_vencimiento=m.fecha_vencimiento,
                    monto_cobrado=m.monto_cobrado,
                    score=p.score,
                    nivel_riesgo=p.nivel_riesgo,
                    factores_principales=list(p.factores_principales),
                    dentro_top_k=p.dentro_top_k,
                )
            )
        return ListaDetalle(
            id=lista_id,
            modelo_id=lista.modelo_id,
            modelo_version=modelo_lista.version,
            fecha_generacion=lista.fecha_generacion,
            creada_en=creada_en,
            horizonte_dias=lista.horizonte_dias,
            top_k=lista.top_k,
            umbral_alto=modelo_lista.umbral_alto,
            umbral_medio=modelo_lista.umbral_medio,
            items=tuple(items),
        )

    def ultima(self) -> ListaDetalle | None:
        return self.obtener(max(self._a.listas)) if self._a.listas else None

    def listar(self) -> list[ListaResumen]:
        resumenes = []
        for lista_id in sorted(self._a.listas, reverse=True):
            lista, predicciones, creada_en = self._a.listas[lista_id]
            resumenes.append(
                ListaResumen(
                    id=lista_id,
                    fecha_generacion=lista.fecha_generacion,
                    creada_en=creada_en,
                    modelo_version=self._modelo(lista.modelo_id).version,
                    horizonte_dias=lista.horizonte_dias,
                    top_k=lista.top_k,
                    total_items=len(predicciones),
                )
            )
        return resumenes


class ModelosEnMemoria:
    def __init__(self, almacen: Almacen) -> None:
        self._a = almacen

    def crear(self, modelo: NuevoModelo) -> int:
        raise AssertionError("no se usa en listas")

    def obtener_vigente(self) -> ModeloGuardado | None:
        return self._a.modelos[-1] if self._a.modelos else None


class EstadoEnMemoria:
    def __init__(self, almacen: Almacen) -> None:
        self._a = almacen

    def obtener(self) -> EstadoSistema:
        return EstadoSistema(self._a.estado, None)

    def fijar_migracion(self, estado: EstadoMigracion) -> None:
        raise AssertionError("no se usa en listas")

    def fijar_proxima_fecha(self, fecha: date) -> None:
        raise AssertionError("no se usa en listas")


class MembresiasEnMemoria:
    def __init__(self, almacen: Almacen) -> None:
        self._a = almacen

    def insertar_en_bloque(self, membresias: Sequence[NuevaMembresia]) -> int:
        raise AssertionError("no se usa en listas")

    def listar_para_prediccion(self) -> list[MembresiaParaPrediccion]:
        self._a.lecturas_membresias += 1
        return list(self._a.membresias)


class CargasEnMemoria:
    def __init__(self, almacen: Almacen) -> None:
        self._a = almacen

    def ultima_fecha_carga_hasta(self, instante: datetime) -> datetime | None:
        return max((c for c in self._a.cargas if c <= instante), default=None)


class Contexto:
    def __init__(self, almacen: Almacen) -> None:
        self._a = almacen
        self.listas = ListasEnMemoria(almacen)
        self.modelos = ModelosEnMemoria(almacen)
        self.estado = EstadoEnMemoria(almacen)
        self.membresias = MembresiasEnMemoria(almacen)
        self.cargas = CargasEnMemoria(almacen)

    def commit(self) -> None:
        self._a.commits += 1


def unidad_de_trabajo(almacen: Almacen) -> Callable[[], AbstractContextManager[ContextoListas]]:
    @contextmanager
    def abrir() -> Iterator[ContextoListas]:
        yield Contexto(almacen)

    return abrir
