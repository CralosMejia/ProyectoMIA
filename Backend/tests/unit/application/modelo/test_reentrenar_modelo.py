"""CU-02: servicio ``ReentrenarModelo`` con dobles en memoria (sin BD ni scikit-learn).

Reloj simulado: hoy = 2026-09-30 en Ecuador. El modelo vigente v1 se entreno el 2026-03-01
con corte 2026-02-28; las membresias se registraron despues. Salvo que la prueba diga otra
cosa, la ultima carga por plantilla es de hoy (R-015 T11: el corte de los datos es hoy).
Datos 100 % sinteticos: los socios son ids, sin nombres ni cedulas.
"""

import ast
import inspect
from collections.abc import Iterator, Sequence
from contextlib import contextmanager
from dataclasses import dataclass, field, replace
from datetime import UTC, date, datetime, timedelta
from decimal import Decimal

import pytest

from app.application.cargas import procesar_carga
from app.application.modelo.dtos import ResultadoReentrenamientoDTO
from app.application.modelo.mapeo import ciclo_de_membresia
from app.application.modelo.ports import (
    EstadoSistema,
    MembresiaParaEntrenamiento,
    ModeloGuardado,
    NuevoIntento,
    NuevoModelo,
)
from app.application.modelo.reentrenar_modelo import (
    MENSAJE_EN_CURSO,
    MENSAJE_NO_LISTO,
    ReentrenarModelo,
)
from app.domain.common.enums import (
    DisparadorReentrenamiento,
    EstadoMigracion,
    FormaPago,
    Plan,
    ResultadoReentrenamiento,
)
from app.domain.common.predictor import FeatureRow, Prediction, TrainedModel
from app.domain.modelo.reentrenamiento import (
    CriteriosReentrenamiento,
    ciclos_para_candidato,
    etiquetar_ciclos,
)
from app.domain.modelo.umbrales import meses_recientes_con_resultado

pytestmark = pytest.mark.unit

HOY = date(2026, 9, 30)
AHORA = datetime(2026, 9, 30, 15, 0, tzinfo=UTC)
ENTRENAMIENTO_V1 = datetime(2026, 3, 1, 10, 0, tzinfo=UTC)
REGISTRO_NUEVAS = datetime(2026, 9, 1, 10, 0, tzinfo=UTC)
ARTEFACTO_VIGENTE = b"vigente"
SEIS_MESES_DESPUES = date(2027, 3, 30)


# ---------------------------------------------------------------- datos sinteticos


def membresias(no_renuevan: int, renuevan: int) -> list[MembresiaParaEntrenamiento]:
    """Ciclos nuevos evaluables con vencimiento de febrero a agosto de 2026.

    Los que no renuevan son ``MENSUAL``; los que renuevan son ``TRIMESTRAL`` y tienen una
    membresia ``ANUAL`` que empieza 5 dias despues del vencimiento (vence en 2027: excluida).
    """
    resultado: list[MembresiaParaEntrenamiento] = []
    siguiente_id = 1

    def agregar(socio: int, plan: Plan, inicio: date, vence: date) -> None:
        nonlocal siguiente_id
        resultado.append(
            MembresiaParaEntrenamiento(
                membresia_id=siguiente_id,
                socio_id=socio,
                plan=plan,
                forma_pago=FormaPago.EFECTIVO,
                fecha_inicio=inicio,
                fecha_vencimiento=vence,
                fecha_actividad=inicio,
                monto_cobrado=Decimal("30.00"),
                inicio_aproximado=False,
                registrada_en=REGISTRO_NUEVAS,
            )
        )
        siguiente_id += 1

    for i in range(no_renuevan + renuevan):
        vence = date(2026, 2 + i % 7, 5 + i % 20)
        if i < no_renuevan:
            agregar(i, Plan.MENSUAL, vence - timedelta(days=30), vence)
        else:
            agregar(i, Plan.TRIMESTRAL, vence - timedelta(days=90), vence)
            renovacion = vence + timedelta(days=5)
            agregar(i, Plan.ANUAL, renovacion, renovacion + timedelta(days=365))
    return resultado


def modelo_vigente(version: int = 1) -> ModeloGuardado:
    return ModeloGuardado(
        id=version,
        version=version,
        fecha_entrenamiento=ENTRENAMIENTO_V1,
        ciclos_entrenamiento=500,
        periodo_desde=date(2025, 1, 1),
        periodo_hasta=date(2026, 1, 31),
        prevalencia=Decimal("0.5"),
        umbral_alto=Decimal("0.7"),
        umbral_medio=Decimal("0.4"),
        porcentajes_umbral={"ALTO": 20, "MEDIO": 30, "BAJO": 50},
        artefacto=ARTEFACTO_VIGENTE,
        metadata_tecnica={
            "fecha_corte": "2026-02-28",
            "medianas_monto": {"por_plan": {"MENSUAL": "30"}, "general": "30"},
        },
    )


# ---------------------------------------------------------------- dobles


@dataclass
class Almacen:
    """Estado "persistido": solo cambia con ``commit``."""

    estado: EstadoSistema
    membresias: list[MembresiaParaEntrenamiento]
    modelos: list[ModeloGuardado] = field(default_factory=list)
    vigente_id: int | None = None
    intentos: list[NuevoIntento] = field(default_factory=list)
    commits: int = 0
    aperturas: int = 0
    ultima_carga_plantilla: datetime | None = None

    @property
    def vigente(self) -> ModeloGuardado | None:
        return next((m for m in self.modelos if m.id == self.vigente_id), None)


class _Contexto:
    def __init__(self, almacen: Almacen) -> None:
        self._almacen = almacen
        self._estado = almacen.estado
        self._modelos = list(almacen.modelos)
        self._vigente_id = almacen.vigente_id
        self._intentos = list(almacen.intentos)

    @property
    def membresias(self) -> "_Contexto":
        return self

    @property
    def modelos(self) -> "_Contexto":
        return self

    @property
    def intentos(self) -> "_Intentos":
        return _Intentos(self)

    @property
    def estado(self) -> "_Estado":
        return _Estado(self)

    @property
    def cargas(self) -> "_Contexto":
        return self

    def listar_para_entrenamiento(self) -> list[MembresiaParaEntrenamiento]:
        return list(self._almacen.membresias)

    def ultima_carga_plantilla_hasta(self, instante: datetime) -> datetime | None:
        ultima = self._almacen.ultima_carga_plantilla
        return ultima if ultima is not None and ultima <= instante else None

    def crear(self, modelo: NuevoModelo) -> int:
        nuevo_id = len(self._modelos) + 1
        self._modelos.append(
            ModeloGuardado(
                id=nuevo_id,
                version=modelo.version,
                fecha_entrenamiento=modelo.fecha_entrenamiento,
                ciclos_entrenamiento=modelo.ciclos_entrenamiento,
                periodo_desde=modelo.periodo_desde,
                periodo_hasta=modelo.periodo_hasta,
                prevalencia=modelo.prevalencia,
                umbral_alto=modelo.umbral_alto,
                umbral_medio=modelo.umbral_medio,
                porcentajes_umbral=modelo.porcentajes_umbral,
                artefacto=modelo.artefacto,
                metadata_tecnica=modelo.metadata_tecnica,
            )
        )
        self._vigente_id = nuevo_id
        return nuevo_id

    def obtener_vigente(self) -> ModeloGuardado | None:
        return next((m for m in self._modelos if m.id == self._vigente_id), None)

    def commit(self) -> None:
        self._almacen.estado = self._estado
        self._almacen.modelos = list(self._modelos)
        self._almacen.vigente_id = self._vigente_id
        self._almacen.intentos = list(self._intentos)
        self._almacen.commits += 1


class _Intentos:
    def __init__(self, contexto: _Contexto) -> None:
        self._c = contexto

    def crear(self, intento: NuevoIntento) -> int:
        self._c._intentos.append(intento)
        return len(self._c._intentos)


class _Estado:
    def __init__(self, contexto: _Contexto) -> None:
        self._c = contexto

    def obtener(self) -> EstadoSistema:
        return self._c._estado

    def fijar_migracion(self, estado: EstadoMigracion) -> None:
        self._c._estado = replace(self._c._estado, migracion_historica=estado)

    def fijar_proxima_fecha(self, fecha: date) -> None:
        self._c._estado = replace(self._c._estado, proxima_fecha_reentrenamiento=fecha)


@dataclass
class UnidadEnMemoria:
    almacen: Almacen

    @contextmanager
    def __call__(self) -> Iterator[_Contexto]:
        self.almacen.aperturas += 1
        yield _Contexto(self.almacen)


@dataclass
class BloqueoDoble:
    ocupado: bool = False
    adquirido: bool = False
    liberaciones: int = 0

    def intentar_adquirir(self) -> bool:
        if self.ocupado:
            return False
        self.adquirido = True
        return True

    def liberar(self) -> None:
        self.liberaciones += 1


@dataclass
class AbridorDoble:
    bloqueo: BloqueoDoble

    @contextmanager
    def __call__(self) -> Iterator[BloqueoDoble]:
        yield self.bloqueo


@dataclass
class PredictorDoble:
    """El candidato puntua alto los ``MENSUAL`` (los que no renuevan): PR-AUC 1.

    ``candidato_acierta=False`` invierte la regla (PR-AUC = prevalencia). El vigente solo
    distingue los ``MENSUAL`` que vencen en junio de 2026: queda entre los dos.
    """

    candidato_acierta: bool = True
    fallar: bool = False
    entrenamientos: list[int] = field(default_factory=list)
    filas_entrenadas: list[list[FeatureRow]] = field(default_factory=list)

    def train(
        self,
        features: Sequence[FeatureRow],
        labels: Sequence[int],
        numericas: Sequence[str],
        categoricas: Sequence[str],
        referencia: Sequence[FeatureRow] | None = None,
    ) -> TrainedModel:
        if self.fallar:
            raise RuntimeError("fallo del entrenamiento")
        self.entrenamientos.append(len(features))
        self.filas_entrenadas.append(list(features))
        return TrainedModel(
            artefacto=f"entrenado-{len(self.entrenamientos)}".encode(),
            metadata_tecnica={"algoritmo": "doble"},
        )

    def predict(self, artefacto: bytes, features: Sequence[FeatureRow]) -> list[Prediction]:
        if artefacto == ARTEFACTO_VIGENTE:
            return [
                Prediction(
                    score=Decimal("0.6")
                    if f["plan"] == "MENSUAL" and f["mes_vencimiento"] == "2026-06"
                    else Decimal("0.5"),
                    factores_principales=(),
                )
                for f in features
            ]
        alto, bajo = (Decimal("0.9"), Decimal("0.1"))
        if not self.candidato_acierta:
            alto, bajo = bajo, alto
        return [
            Prediction(score=alto if f["plan"] == "MENSUAL" else bajo, factores_principales=())
            for f in features
        ]


class RelojFijo:
    def __init__(self, instante: datetime = AHORA) -> None:
        self._instante = instante

    def now(self) -> datetime:
        return self._instante


def escenario(
    *,
    programada: date | None = HOY,
    migracion: EstadoMigracion = EstadoMigracion.COMPLETADA,
    con_vigente: bool = True,
    datos: list[MembresiaParaEntrenamiento] | None = None,
    predictor: PredictorDoble | None = None,
    ocupado: bool = False,
    reloj: RelojFijo | None = None,
    ultima_carga: datetime | None = AHORA,
) -> tuple[ReentrenarModelo, Almacen, BloqueoDoble, PredictorDoble]:
    vigente = modelo_vigente()
    almacen = Almacen(
        estado=EstadoSistema(
            migracion_historica=migracion, proxima_fecha_reentrenamiento=programada
        ),
        membresias=membresias(100, 100) if datos is None else datos,
        modelos=[vigente] if con_vigente else [],
        vigente_id=vigente.id if con_vigente else None,
        ultima_carga_plantilla=ultima_carga,
    )
    bloqueo = BloqueoDoble(ocupado=ocupado)
    doble = predictor or PredictorDoble()
    servicio = ReentrenarModelo(
        unidad_de_trabajo=UnidadEnMemoria(almacen),
        abrir_bloqueo=AbridorDoble(bloqueo),
        predictor=doble,
        clock=reloj or RelojFijo(),
        criterios=CriteriosReentrenamiento(),
    )
    return servicio, almacen, bloqueo, doble


# ---------------------------------------------------------------- (1) programado entrenado


def test_revisar_programado_hoy_con_criterios_y_candidato_mejor_entrena_v2() -> None:
    servicio, almacen, bloqueo, _ = escenario()

    resultado = servicio.revisar_programado()

    assert resultado.resultado is ResultadoReentrenamiento.ENTRENADO
    assert resultado.version == 2
    assert almacen.vigente is not None
    assert almacen.vigente.version == 2
    assert [m.version for m in almacen.modelos] == [1, 2]
    assert almacen.commits == 1
    (intento,) = almacen.intentos
    assert intento.disparador is DisparadorReentrenamiento.PROGRAMADO
    assert intento.resultado is ResultadoReentrenamiento.ENTRENADO
    assert intento.fecha_programada == HOY
    assert intento.modelo_id == almacen.vigente.id
    assert intento.pr_auc_candidato == Decimal("1.00000000")
    assert intento.pr_auc_vigente is not None
    assert intento.pr_auc_vigente < intento.pr_auc_candidato
    assert intento.ciclos_nuevos == 200
    assert almacen.estado.proxima_fecha_reentrenamiento == SEIS_MESES_DESPUES
    assert bloqueo.liberaciones == 1


def test_revisar_programado_entrenado_guarda_metadatos_y_ciclos_de_todo_el_historial() -> None:
    servicio, almacen, _, doble = escenario()

    servicio.revisar_programado()

    nuevo = almacen.vigente
    assert nuevo is not None
    assert nuevo.fecha_entrenamiento == AHORA
    assert nuevo.metadata_tecnica["fecha_corte"] == "2026-09-30"
    assert nuevo.metadata_tecnica["pr_auc_candidato"] == "1.00000000"
    assert "pr_auc_vigente" in nuevo.metadata_tecnica
    assert "medianas_monto" in nuevo.metadata_tecnica
    # Candidato sin el conjunto de comparacion; modelo final con los 200 evaluables.
    candidato, final = doble.entrenamientos
    assert candidato < final == 200
    assert nuevo.ciclos_entrenamiento == 200


def test_revisar_programado_candidato_sin_comparacion_ni_margen_de_30_dias() -> None:
    # M01 (f). Comparacion = vencimientos de 2026-06 a 2026-08 (el primero, 2026-06-05):
    # el candidato no ve ciclos que vencen desde el 2026-05-06 (vencimiento + 30 >= 06-05).
    datos = membresias(100, 100)
    servicio, _, _, doble = escenario(datos=datos)

    servicio.revisar_programado()

    ciclos = etiquetar_ciclos([ciclo_de_membresia(m) for m in datos], HOY)
    evaluables = [c for c in ciclos if not c.excluido and c.no_renovo is not None]
    comparacion = meses_recientes_con_resultado(evaluables, 3)
    esperados = ciclos_para_candidato(evaluables, comparacion)
    vencimientos = sorted(c.fecha_vencimiento for c in esperados if c.fecha_vencimiento)
    assert vencimientos[-1] == date(2026, 5, 5)
    assert min(c.fecha_vencimiento for c in comparacion if c.fecha_vencimiento) == date(2026, 6, 5)
    candidato, final = doble.filas_entrenadas
    assert len(candidato) == len(esperados) < len(evaluables) - len(comparacion)
    assert sorted(str(f["mes_vencimiento"]) for f in candidato) == sorted(
        f"{v.year:04d}-{v.month:02d}" for v in vencimientos
    )
    # El modelo final sigue entrenandose con todos los evaluables.
    assert len(final) == len(evaluables) == 200


# ---------------------------------------------------------------- (1b) corte de los datos


CARGA_JULIO = datetime(2026, 7, 15, 15, 0, tzinfo=UTC)
CORTE_JULIO = date(2026, 7, 15)


def _evaluables_al(datos: list[MembresiaParaEntrenamiento], corte: date) -> int:
    ciclos = etiquetar_ciclos([ciclo_de_membresia(m) for m in datos], corte)
    return sum(1 for c in ciclos if not c.excluido and c.no_renovo is not None)


@pytest.mark.parametrize("metodo", ["revisar_programado", "ejecutar_manual"])
def test_etiqueta_al_corte_de_los_datos_no_a_hoy(metodo: str) -> None:
    # R-015 T11: con la ultima carga el 2026-07-15 los datos terminan ese dia; los ciclos que
    # vencen despues del 2026-06-15 aun no tienen su renovacion cargada: quedan pendientes, no
    # se cuentan como nuevos ni se entrena con ellos como "no renovo".
    datos = membresias(150, 150)
    servicio, almacen, _, doble = escenario(datos=datos, ultima_carga=CARGA_JULIO)

    resultado: ResultadoReentrenamientoDTO = getattr(servicio, metodo)()

    assert resultado.resultado is ResultadoReentrenamiento.ENTRENADO
    esperados = _evaluables_al(datos, CORTE_JULIO)
    assert 150 <= esperados < _evaluables_al(datos, HOY)
    (intento,) = almacen.intentos
    assert intento.ciclos_nuevos == esperados
    nuevo = almacen.vigente
    assert nuevo is not None
    assert nuevo.metadata_tecnica["fecha_corte"] == "2026-07-15"
    assert nuevo.ciclos_entrenamiento == esperados
    _, final = doble.filas_entrenadas
    assert max(str(f["mes_vencimiento"]) for f in final) == "2026-06"
    # La proxima fecha programada sigue contando desde hoy, no desde el corte de los datos.
    assert almacen.estado.proxima_fecha_reentrenamiento == SEIS_MESES_DESPUES


@pytest.mark.parametrize("metodo", ["revisar_programado", "ejecutar_manual"])
def test_sin_cargas_posteriores_el_corte_es_el_del_vigente_y_no_hay_ciclos_nuevos(
    metodo: str,
) -> None:
    # Sin cargas por plantilla los datos terminan en el corte del vigente (2026-02-28): ningun
    # ciclo es nuevo aunque hoy sea 2026-09-30.
    servicio, almacen, _, doble = escenario(ultima_carga=None)

    resultado: ResultadoReentrenamientoDTO = getattr(servicio, metodo)()

    assert resultado.resultado is ResultadoReentrenamiento.CRITERIOS_NO_CUMPLIDOS
    assert "Hay 0 ciclos nuevos" in resultado.motivo
    (intento,) = almacen.intentos
    assert intento.ciclos_nuevos == 0
    assert doble.entrenamientos == []
    assert [m.version for m in almacen.modelos] == [1]


# ---------------------------------------------------------------- (2) fecha perdida


def test_revisar_programado_fecha_pasada_registra_omitido_sin_entrenar() -> None:
    perdida = HOY - timedelta(days=3)
    servicio, almacen, _, doble = escenario(programada=perdida)

    resultado = servicio.revisar_programado()

    assert resultado.resultado is ResultadoReentrenamiento.OMITIDO
    assert resultado.version is None
    assert doble.entrenamientos == []
    (intento,) = almacen.intentos
    assert intento.resultado is ResultadoReentrenamiento.OMITIDO
    assert intento.disparador is DisparadorReentrenamiento.PROGRAMADO
    assert intento.fecha_programada == perdida
    assert almacen.estado.proxima_fecha_reentrenamiento == date(2027, 3, 27)
    assert [m.version for m in almacen.modelos] == [1]
    assert almacen.commits == 1


def test_revisar_programado_varias_fechas_perdidas_un_omitido_por_cada_una() -> None:
    servicio, almacen, _, doble = escenario(programada=date(2025, 1, 10))

    servicio.revisar_programado()

    assert [i.fecha_programada for i in almacen.intentos] == [
        date(2025, 1, 10),
        date(2025, 7, 10),
        date(2026, 1, 10),
        date(2026, 7, 10),
    ]
    assert {i.resultado for i in almacen.intentos} == {ResultadoReentrenamiento.OMITIDO}
    assert almacen.estado.proxima_fecha_reentrenamiento == date(2027, 1, 10)
    assert doble.entrenamientos == []


def test_revisar_programado_dos_veces_tras_omitir_no_repite_el_omitido() -> None:
    servicio, almacen, _, _ = escenario(programada=HOY - timedelta(days=3))

    servicio.revisar_programado()
    segundo = servicio.revisar_programado()

    assert segundo.resultado is None
    assert len(almacen.intentos) == 1


def test_revisar_programado_fecha_futura_o_nula_no_hace_nada() -> None:
    for programada in (HOY + timedelta(days=1), SEIS_MESES_DESPUES, None):
        servicio, almacen, bloqueo, doble = escenario(programada=programada)

        resultado = servicio.revisar_programado()

        assert resultado.resultado is None
        assert resultado.en_curso is False
        assert almacen.intentos == []
        assert almacen.commits == 0
        assert doble.entrenamientos == []
        assert almacen.estado.proxima_fecha_reentrenamiento == programada
        assert bloqueo.liberaciones == 1


def test_revisar_programado_usa_la_fecha_de_negocio() -> None:
    # 2026-10-01 03:00Z sigue siendo 2026-09-30 en Ecuador: toca hoy, no se omite.
    reloj = RelojFijo(datetime(2026, 10, 1, 3, 0, tzinfo=UTC))
    servicio, almacen, _, _ = escenario(reloj=reloj)

    resultado = servicio.revisar_programado()

    assert resultado.resultado is ResultadoReentrenamiento.ENTRENADO
    assert almacen.estado.proxima_fecha_reentrenamiento == SEIS_MESES_DESPUES


# ---------------------------------------------------------------- (3) criterios


@pytest.mark.parametrize(
    ("no_renuevan", "renuevan", "fragmento"),
    [(75, 74, "149 ciclos nuevos"), (150, 19, "19 que renovaron")],
)
def test_revisar_programado_criterios_no_cumplidos_registra_motivo_sin_modelo(
    no_renuevan: int, renuevan: int, fragmento: str
) -> None:
    servicio, almacen, _, doble = escenario(datos=membresias(no_renuevan, renuevan))

    resultado = servicio.revisar_programado()

    assert resultado.resultado is ResultadoReentrenamiento.CRITERIOS_NO_CUMPLIDOS
    assert fragmento in resultado.motivo
    assert doble.entrenamientos == []
    (intento,) = almacen.intentos
    assert intento.resultado is ResultadoReentrenamiento.CRITERIOS_NO_CUMPLIDOS
    assert intento.motivo is not None
    assert fragmento in intento.motivo
    assert intento.ciclos_nuevos == no_renuevan + renuevan
    assert intento.modelo_id is None
    assert [m.version for m in almacen.modelos] == [1]
    assert almacen.estado.proxima_fecha_reentrenamiento == SEIS_MESES_DESPUES


def test_revisar_programado_sin_membresias_nuevas_no_cumple_criterio_de_cobertura() -> None:
    antiguas = [replace(m, registrada_en=ENTRENAMIENTO_V1) for m in membresias(100, 100)]
    servicio, almacen, _, _ = escenario(datos=antiguas)

    resultado = servicio.revisar_programado()

    assert resultado.resultado is ResultadoReentrenamiento.CRITERIOS_NO_CUMPLIDOS
    assert "membresias nuevas" in resultado.motivo
    assert len(almacen.modelos) == 1


# ---------------------------------------------------------------- (4) no supera al vigente


def test_revisar_programado_candidato_peor_no_supera_vigente_con_ambas_cifras() -> None:
    servicio, almacen, _, doble = escenario(predictor=PredictorDoble(candidato_acierta=False))

    resultado = servicio.revisar_programado()

    assert resultado.resultado is ResultadoReentrenamiento.NO_SUPERA_VIGENTE
    assert resultado.version is None
    (intento,) = almacen.intentos
    assert intento.resultado is ResultadoReentrenamiento.NO_SUPERA_VIGENTE
    assert intento.pr_auc_candidato is not None
    assert intento.pr_auc_vigente is not None
    assert intento.pr_auc_candidato < intento.pr_auc_vigente
    assert str(intento.pr_auc_candidato) in resultado.motivo
    assert str(intento.pr_auc_vigente) in resultado.motivo
    assert almacen.vigente is not None
    assert almacen.vigente.version == 1
    assert len(doble.entrenamientos) == 1  # solo el candidato
    assert almacen.estado.proxima_fecha_reentrenamiento == SEIS_MESES_DESPUES


# ---------------------------------------------------------------- (5) fallido


def test_revisar_programado_predictor_falla_registra_fallido_y_sigue_el_vigente() -> None:
    servicio, almacen, bloqueo, _ = escenario(predictor=PredictorDoble(fallar=True))

    resultado = servicio.revisar_programado()

    assert resultado.resultado is ResultadoReentrenamiento.FALLIDO
    assert "RuntimeError" in resultado.motivo
    assert "fallo del entrenamiento" not in resultado.motivo
    (intento,) = almacen.intentos
    assert intento.resultado is ResultadoReentrenamiento.FALLIDO
    assert intento.modelo_id is None
    assert [m.version for m in almacen.modelos] == [1]
    assert almacen.vigente is not None
    assert almacen.vigente.version == 1
    assert almacen.estado.proxima_fecha_reentrenamiento == SEIS_MESES_DESPUES
    assert bloqueo.liberaciones == 1


# ---------------------------------------------------------------- (6) manual


def test_ejecutar_manual_criterios_no_cumplidos_no_cambia_la_proxima_fecha() -> None:
    programada = date(2026, 12, 15)
    servicio, almacen, _, _ = escenario(programada=programada, datos=membresias(10, 10))

    resultado = servicio.ejecutar_manual()

    assert resultado.resultado is ResultadoReentrenamiento.CRITERIOS_NO_CUMPLIDOS
    (intento,) = almacen.intentos
    assert intento.disparador is DisparadorReentrenamiento.MANUAL
    assert intento.fecha_programada is None
    assert almacen.estado.proxima_fecha_reentrenamiento == programada


def test_ejecutar_manual_no_supera_o_fallido_no_cambia_la_proxima_fecha() -> None:
    programada = date(2026, 12, 15)
    for doble in (PredictorDoble(candidato_acierta=False), PredictorDoble(fallar=True)):
        servicio, almacen, _, _ = escenario(programada=programada, predictor=doble)

        servicio.ejecutar_manual()

        assert almacen.estado.proxima_fecha_reentrenamiento == programada
        assert almacen.intentos[0].disparador is DisparadorReentrenamiento.MANUAL


def test_ejecutar_manual_entrenado_mueve_la_proxima_fecha_seis_meses() -> None:
    servicio, almacen, _, _ = escenario(programada=date(2026, 12, 15))

    resultado = servicio.ejecutar_manual()

    assert resultado.resultado is ResultadoReentrenamiento.ENTRENADO
    assert resultado.version == 2
    assert "v2" in resultado.motivo
    assert almacen.intentos[0].disparador is DisparadorReentrenamiento.MANUAL
    assert almacen.estado.proxima_fecha_reentrenamiento == SEIS_MESES_DESPUES


def test_ejecutar_manual_ignora_la_fecha_programada_pasada() -> None:
    servicio, almacen, _, _ = escenario(programada=HOY - timedelta(days=3))

    resultado = servicio.ejecutar_manual()

    assert resultado.resultado is ResultadoReentrenamiento.ENTRENADO
    assert [i.resultado for i in almacen.intentos] == [ResultadoReentrenamiento.ENTRENADO]


# ---------------------------------------------------------------- (7) bloqueo ocupado


@pytest.mark.parametrize("metodo", ["revisar_programado", "ejecutar_manual"])
def test_bloqueo_ocupado_no_toca_nada(metodo: str) -> None:
    servicio, almacen, bloqueo, doble = escenario(ocupado=True)

    resultado: ResultadoReentrenamientoDTO = getattr(servicio, metodo)()

    assert resultado.en_curso is True
    assert resultado.resultado is None
    assert resultado.motivo == MENSAJE_EN_CURSO == "Ya hay un reentrenamiento en curso."
    assert almacen.aperturas == 0
    assert almacen.intentos == []
    assert doble.entrenamientos == []
    assert bloqueo.liberaciones == 0


# ---------------------------------------------------------------- (8) sistema no listo


@pytest.mark.parametrize(
    ("migracion", "con_vigente"),
    [
        (EstadoMigracion.EN_CURSO, True),
        (EstadoMigracion.PENDIENTE, False),
        (EstadoMigracion.COMPLETADA, False),
    ],
)
@pytest.mark.parametrize("metodo", ["revisar_programado", "ejecutar_manual"])
def test_sistema_no_listo_no_hace_nada(
    migracion: EstadoMigracion, con_vigente: bool, metodo: str
) -> None:
    servicio, almacen, bloqueo, doble = escenario(migracion=migracion, con_vigente=con_vigente)

    resultado: ResultadoReentrenamientoDTO = getattr(servicio, metodo)()

    assert resultado.resultado is None
    assert resultado.en_curso is False
    assert resultado.motivo == MENSAJE_NO_LISTO == "El sistema aun no esta listo."
    assert almacen.intentos == []
    assert almacen.commits == 0
    assert doble.entrenamientos == []
    assert bloqueo.liberaciones == 1


# ---------------------------------------------------------------- (9) una carga no reentrena


def test_procesar_carga_no_usa_el_reentrenamiento() -> None:
    arbol = ast.parse(inspect.getsource(procesar_carga))
    importados = {
        nodo.module for nodo in ast.walk(arbol) if isinstance(nodo, ast.ImportFrom) and nodo.module
    }

    assert not any("reentrenar" in modulo for modulo in importados)
    assert "ReentrenarModelo" not in inspect.getsource(procesar_carga)


# ---------------------------------------------------------------- privacidad


def test_resultado_y_motivos_no_incluyen_datos_de_socios() -> None:
    servicio, almacen, _, _ = escenario()

    resultado = servicio.revisar_programado()

    texto = resultado.motivo + "".join(i.motivo or "" for i in almacen.intentos)
    assert "socio" not in texto.lower()
