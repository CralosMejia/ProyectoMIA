"""Caso de uso MigrarHistorico con dobles en memoria (sin BD, sin pandas, sin scikit-learn).

La unidad de trabajo doble acumula las escrituras y solo las aplica a la "base" en
``commit()``: una unidad sin ``commit`` se descarta, como una transaccion revertida.
Nombres, cedulas, celulares y correos son inventados.
"""

import logging
from collections.abc import Iterator, Sequence
from contextlib import contextmanager
from dataclasses import dataclass, field
from datetime import UTC, date, datetime
from decimal import Decimal
from pathlib import Path
from types import TracebackType
from typing import Self

import pytest

from app.application.historial.ports import (
    LibroLeido,
    LibrosLeidos,
    MembresiaParaPrediccion,
    NuevaCarga,
    NuevaMembresia,
    NuevoSocio,
)
from app.application.modelo.ports import (
    BloqueoMigracion,
    EstadoSistema,
    ModeloGuardado,
    NuevoIntento,
    NuevoModelo,
)
from app.application.sistema.migrar_historico import MigrarHistorico
from app.application.sistema.ports import (
    FabricaUnidadDeTrabajo,
    LocalizadorLibros,
    RegistroMigracion,
    ResultadoMigracion,
    UnidadDeTrabajo,
)
from app.domain.common.enums import (
    DisparadorReentrenamiento,
    EstadoMigracion,
    OrigenMembresia,
    ResultadoReentrenamiento,
    TipoCarga,
)
from app.domain.common.predictor import FeatureRow, Prediction, TrainedModel
from app.domain.historico.errores import HojaSinEncabezadoError, LibroSinAnioError
from app.domain.historico.registro import FilaCruda

pytestmark = pytest.mark.unit

AHORA = datetime(2026, 9, 29, 10, 0, tzinfo=UTC)
MES = date(2026, 8, 1)
NOMBRES = ("Ana Ficticia Perez", "Bruno Inventado Soto", "Carla Supuesta Vera")
CEDULAS = ("1712345678", "0999000011")
CELULAR = "0991234567"
CORREO = "ana.ficticia@example.com"


def _celda(anio: int, mes: int, dia: int) -> datetime:
    return datetime(anio, mes, dia)  # noqa: DTZ001 - celda Excel sin zona


def _fila(fila: int, **campos: object) -> FilaCruda:
    return FilaCruda(anio=2026, hoja="AGOSTO", fila=fila, mes_hoja=MES, **campos)  # type: ignore[arg-type]  # campos opcionales de la fila


FILAS = (
    # Socio A (cedula): evaluable que renueva, y despues evaluable que no renueva.
    _fila(
        3,
        nombre=NOMBRES[0],
        cedula=CEDULAS[0],
        celular="0990000000",
        plan="1 MES",
        fecha_inicio=_celda(2026, 5, 1),
        fecha_fin=_celda(2026, 6, 1),
        monto_cobrado="30",
    ),
    _fila(
        4,
        nombre=NOMBRES[0],
        cedula=CEDULAS[0],
        celular=CELULAR,
        correo=CORREO,
        plan="1 MES",
        fecha_inicio=_celda(2026, 6, 2),
        fecha_fin=_celda(2026, 7, 2),
        monto_cobrado="30",
    ),
    # Socio B (sin cedula): evaluable que no renueva.
    _fila(
        5,
        nombre=NOMBRES[1],
        plan="1 MES",
        fecha_inicio=_celda(2026, 4, 1),
        fecha_fin=_celda(2026, 5, 1),
        monto_cobrado="25",
    ),
    # Socio C: pendiente (vence 08-20, T+30 > corte).
    _fila(
        6,
        nombre=NOMBRES[2],
        cedula=CEDULAS[1],
        plan="1 MES",
        fecha_inicio=_celda(2026, 7, 20),
        fecha_fin=_celda(2026, 8, 20),
    ),
)


# ---------------------------------------------------------------- dobles


@dataclass
class BaseEnMemoria:
    estado: EstadoMigracion = EstadoMigracion.PENDIENTE
    proxima_fecha: date | None = None
    cargas: list[NuevaCarga] = field(default_factory=list)
    socios: list[NuevoSocio] = field(default_factory=list)
    membresias: list[NuevaMembresia] = field(default_factory=list)
    modelos: list[NuevoModelo] = field(default_factory=list)
    intentos: list[NuevoIntento] = field(default_factory=list)
    commits: list[str] = field(default_factory=list)
    unidades_abiertas: int = 0


class UnidadDoble:
    def __init__(self, base: BaseEnMemoria) -> None:
        self._base = base
        self._pendiente: dict[str, list[object]] = {
            "cargas": [],
            "socios": [],
            "membresias": [],
            "modelos": [],
            "intentos": [],
        }
        self._estado: EstadoMigracion | None = None
        self._proxima: date | None = None

    # repositorios (la propia unidad hace de todos)
    @property
    def socios(self) -> "UnidadDoble":
        return self

    @property
    def membresias(self) -> "UnidadDoble":
        return self

    @property
    def cargas(self) -> "UnidadDoble":
        return self

    @property
    def modelos(self) -> "UnidadDoble":
        return self

    @property
    def intentos(self) -> "UnidadDoble":
        return self

    @property
    def estado(self) -> "UnidadDoble":
        return self

    # SocioRepository / MembresiaRepository
    def insertar_en_bloque(self, filas: Sequence[object]) -> list[int] | int:  # type: ignore[override]  # doble comun a socios y membresias
        if filas and isinstance(filas[0], NuevoSocio):
            inicio = len(self._base.socios) + len(self._pendiente["socios"])
            self._pendiente["socios"].extend(filas)
            return list(range(inicio + 1, inicio + 1 + len(filas)))
        self._pendiente["membresias"].extend(filas)
        return len(filas)

    def listar_para_prediccion(self) -> list[MembresiaParaPrediccion]:
        return []

    # CargaRepository / ModeloRepository / IntentoRepository
    def crear(self, objeto: object) -> int:
        clave = {NuevaCarga: "cargas", NuevoModelo: "modelos", NuevoIntento: "intentos"}[
            type(objeto)
        ]
        self._pendiente[clave].append(objeto)
        return len(getattr(self._base, clave)) + len(self._pendiente[clave])

    def ultima_fecha_carga(self) -> datetime | None:
        return None

    def hay_migracion_o_membresias(self) -> bool:
        return bool(self._base.cargas or self._base.membresias)

    def obtener_vigente(self) -> ModeloGuardado | None:
        return None

    # EstadoSistemaRepository
    def obtener(self) -> EstadoSistema:
        return EstadoSistema(self._estado or self._base.estado, self._base.proxima_fecha)

    def fijar_migracion(self, estado: EstadoMigracion) -> None:
        self._estado = estado

    def fijar_proxima_fecha(self, fecha: date) -> None:
        self._proxima = fecha

    # unidad de trabajo
    def commit(self) -> None:
        for clave, filas in self._pendiente.items():
            getattr(self._base, clave).extend(filas)
            filas.clear()
        if self._estado is not None:
            self._base.estado = self._estado
        if self._proxima is not None:
            self._base.proxima_fecha = self._proxima
        self._base.commits.append(self._base.estado.value)

    def __enter__(self) -> Self:
        self._base.unidades_abiertas += 1
        return self

    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc: BaseException | None,
        tb: TracebackType | None,
    ) -> None:
        return None


class BloqueoDoble:
    def __init__(self, disponible: bool = True) -> None:
        self.disponible = disponible
        self.adquirido = False
        self.liberaciones = 0

    def intentar_adquirir(self) -> bool:
        self.adquirido = self.disponible
        return self.disponible

    def liberar(self) -> None:
        self.liberaciones += 1
        self.adquirido = False


class LocalizadorDoble:
    def __init__(self, rutas: Sequence[Path]) -> None:
        self._rutas = list(rutas)

    def rutas(self) -> list[Path]:
        return list(self._rutas)


class LectorDoble:
    def __init__(self, filas: Sequence[FilaCruda], error: Exception | None = None) -> None:
        self.filas = filas
        self.error = error
        self.llamadas = 0

    def leer(self, rutas: Sequence[Path]) -> LibrosLeidos:
        self.llamadas += 1
        if self.error is not None:
            raise self.error
        libro = LibroLeido("Control Gym 2026.xlsx", 2026, ("AGOSTO",), ())
        return LibrosLeidos(filas=tuple(self.filas), libros=(libro,))


class PredictorDoble:
    def __init__(self, fallar: bool = False) -> None:
        self.fallar = fallar

    def train(
        self,
        features: Sequence[FeatureRow],
        labels: Sequence[int],
        numericas: Sequence[str],
        categoricas: Sequence[str],
        referencia: Sequence[FeatureRow] | None = None,
    ) -> TrainedModel:
        if self.fallar:
            raise RuntimeError(f"fallo con {NOMBRES[0]}")  # mensaje con dato personal
        return TrainedModel(artefacto=b"artefacto", metadata_tecnica={"algoritmo": "doble"})

    def predict(self, artefacto: bytes, features: Sequence[FeatureRow]) -> list[Prediction]:
        return [Prediction(Decimal("0.5"), ()) for _ in features]


class RelojFijo:
    def now(self) -> datetime:
        return AHORA


@dataclass
class Escenario:
    base: BaseEnMemoria = field(default_factory=BaseEnMemoria)
    bloqueo: BloqueoDoble = field(default_factory=BloqueoDoble)
    rutas: list[Path] = field(default_factory=lambda: [Path("Control Gym 2026.xlsx")])
    lector: LectorDoble = field(default_factory=lambda: LectorDoble(FILAS))
    predictor: PredictorDoble = field(default_factory=PredictorDoble)
    registro: RegistroMigracion = field(default_factory=RegistroMigracion)

    def caso_de_uso(self) -> MigrarHistorico:
        @contextmanager
        def abrir_bloqueo() -> Iterator[BloqueoMigracion]:
            yield self.bloqueo

        def fabrica() -> UnidadDeTrabajo:
            return UnidadDoble(self.base)  # type: ignore[return-value]  # doble estructural

        return MigrarHistorico(
            abrir_bloqueo=abrir_bloqueo,
            unidad_de_trabajo=fabrica,
            localizador=LocalizadorDoble(self.rutas),
            lector=self.lector,
            predictor=self.predictor,
            clock=RelojFijo(),
            registro=self.registro,
        )

    def ejecutar(self) -> ResultadoMigracion:
        return self.caso_de_uso().ejecutar()


# ---------------------------------------------------------------- pruebas


def test_dobles_cumplen_los_puertos() -> None:
    base = BaseEnMemoria()
    assert isinstance(UnidadDoble(base), UnidadDeTrabajo)
    assert isinstance(LocalizadorDoble([]), LocalizadorLibros)
    assert isinstance(lambda: UnidadDoble(base), FabricaUnidadDeTrabajo)


def test_ejecutar_exito_guarda_todo_en_una_transaccion() -> None:
    escenario = Escenario()

    resultado = escenario.ejecutar()

    base = escenario.base
    assert resultado is ResultadoMigracion.COMPLETADA
    assert base.commits == ["EN_CURSO", "COMPLETADA"]
    assert len(base.cargas) == 1
    carga = base.cargas[0]
    assert carga.tipo is TipoCarga.MIGRACION_HISTORICA
    assert carga.filas_leidas == 4
    assert carga.filas_guardadas == 4
    assert carga.filas_duplicadas == 0
    assert carga.socios_enlazados == 3
    assert carga.nombre_archivo == "Control Gym 2026.xlsx"
    assert len(base.socios) == 3  # identidades distintas
    assert len(base.membresias) == 4  # con_identidad
    assert all(m.origen is OrigenMembresia.HISTORICO for m in base.membresias)
    assert [m.referencia_origen.fila for m in base.membresias if m.referencia_origen] == [
        3,
        4,
        5,
        6,
    ]
    assert base.membresias[2].fecha_actividad == date(2026, 4, 1)
    assert len(base.modelos) == 1
    modelo = base.modelos[0]
    assert modelo.version == 1
    assert modelo.ciclos_entrenamiento == 3
    assert modelo.prevalencia == Decimal(2) / 3
    assert len(base.intentos) == 1
    intento = base.intentos[0]
    assert intento.disparador is DisparadorReentrenamiento.INICIAL
    assert intento.resultado is ResultadoReentrenamiento.ENTRENADO
    assert intento.modelo_id == 1
    assert base.proxima_fecha == date(2027, 3, 29)
    assert base.estado is EstadoMigracion.COMPLETADA
    assert escenario.registro.resultado is ResultadoMigracion.COMPLETADA
    assert escenario.registro.en_curso is False


def test_ejecutar_socio_toma_los_datos_del_registro_mas_reciente() -> None:
    escenario = Escenario()

    escenario.ejecutar()

    socio_a = escenario.base.socios[0]
    assert socio_a.cedula == CEDULAS[0]
    assert socio_a.celular == CELULAR
    assert socio_a.correo == CORREO
    ids_a = {m.socio_id for m in escenario.base.membresias[:2]}
    assert ids_a == {1}


def test_ejecutar_predictor_falla_no_hay_commit_de_datos_y_vuelve_a_pendiente() -> None:
    escenario = Escenario(predictor=PredictorDoble(fallar=True))

    resultado = escenario.ejecutar()

    base = escenario.base
    assert resultado is ResultadoMigracion.FALLIDA
    assert base.commits == ["EN_CURSO", "PENDIENTE"]
    assert base.estado is EstadoMigracion.PENDIENTE
    assert base.cargas == base.socios == base.membresias == []
    assert base.modelos == []
    assert base.intentos == []
    assert escenario.registro.resultado is ResultadoMigracion.FALLIDA
    assert escenario.bloqueo.liberaciones == 1


def test_ejecutar_sin_rutas_no_entrena_y_sigue_pendiente() -> None:
    escenario = Escenario(rutas=[])

    resultado = escenario.ejecutar()

    assert resultado is ResultadoMigracion.FALTAN_DATOS
    assert escenario.lector.llamadas == 0
    assert escenario.base.estado is EstadoMigracion.PENDIENTE
    assert escenario.base.commits == []
    assert escenario.registro.resultado is ResultadoMigracion.FALTAN_DATOS


@pytest.mark.parametrize(
    ("error", "en_log"),
    [
        (LibroSinAnioError("Control Gym.xlsx"), "Control Gym.xlsx"),
        (HojaSinEncabezadoError("Control Gym 2026.xlsx", "MARZO"), "MARZO"),
    ],
)
def test_ejecutar_libro_ilegible_faltan_datos_y_log_con_libro_y_hoja(
    error: Exception, en_log: str, caplog: pytest.LogCaptureFixture
) -> None:
    escenario = Escenario(lector=LectorDoble(FILAS, error=error))

    with caplog.at_level(logging.INFO):
        resultado = escenario.ejecutar()

    assert resultado is ResultadoMigracion.FALTAN_DATOS
    assert escenario.base.estado is EstadoMigracion.PENDIENTE
    assert escenario.base.cargas == []
    assert en_log in caplog.text


def test_ejecutar_hoja_sin_encabezado_faltan_datos_y_log_con_libro_y_hoja(
    caplog: pytest.LogCaptureFixture,
) -> None:
    error = HojaSinEncabezadoError("Control Gym 2026.xlsx", "MARZO")
    escenario = Escenario(lector=LectorDoble(FILAS, error=error))

    with caplog.at_level(logging.INFO):
        resultado = escenario.ejecutar()

    assert resultado is ResultadoMigracion.FALTAN_DATOS
    assert escenario.registro.resultado is ResultadoMigracion.FALTAN_DATOS
    assert escenario.base.modelos == []
    assert escenario.bloqueo.liberaciones == 1
    assert "Control Gym 2026.xlsx" in caplog.text
    assert "MARZO" in caplog.text


def test_ejecutar_sin_bloqueo_no_llama_al_lector() -> None:
    escenario = Escenario(bloqueo=BloqueoDoble(disponible=False))

    resultado = escenario.ejecutar()

    assert resultado is ResultadoMigracion.EN_OTRO_PROCESO
    assert escenario.lector.llamadas == 0
    assert escenario.base.commits == []
    assert escenario.bloqueo.liberaciones == 0


def test_ejecutar_base_ya_migrada_no_llama_al_lector() -> None:
    escenario = Escenario()
    escenario.ejecutar()
    commits = list(escenario.base.commits)

    segundo = Escenario(base=escenario.base)
    resultado = segundo.ejecutar()

    assert resultado is ResultadoMigracion.YA_MIGRADA
    assert segundo.lector.llamadas == 0
    assert escenario.base.commits == commits
    assert len(escenario.base.modelos) == 1


def test_ejecutar_estado_completada_no_llama_al_lector() -> None:
    escenario = Escenario(base=BaseEnMemoria(estado=EstadoMigracion.COMPLETADA))

    resultado = escenario.ejecutar()

    assert resultado is ResultadoMigracion.YA_MIGRADA
    assert escenario.lector.llamadas == 0


def test_ejecutar_en_curso_huerfano_se_trata_como_pendiente() -> None:
    escenario = Escenario(base=BaseEnMemoria(estado=EstadoMigracion.EN_CURSO))

    resultado = escenario.ejecutar()

    assert resultado is ResultadoMigracion.COMPLETADA
    assert escenario.base.estado is EstadoMigracion.COMPLETADA


def test_ejecutar_en_curso_huerfano_sin_libros_vuelve_a_pendiente() -> None:
    escenario = Escenario(base=BaseEnMemoria(estado=EstadoMigracion.EN_CURSO), rutas=[])

    resultado = escenario.ejecutar()

    assert resultado is ResultadoMigracion.FALTAN_DATOS
    assert escenario.base.estado is EstadoMigracion.PENDIENTE


def test_ejecutar_libera_el_bloqueo_tambien_si_falla() -> None:
    escenario = Escenario(predictor=PredictorDoble(fallar=True))

    escenario.ejecutar()

    assert escenario.bloqueo.liberaciones == 1
    assert escenario.bloqueo.adquirido is False


@pytest.mark.parametrize("fallar", [False, True])
def test_ejecutar_logs_sin_datos_personales(fallar: bool, caplog: pytest.LogCaptureFixture) -> None:
    escenario = Escenario(predictor=PredictorDoble(fallar=fallar))

    with caplog.at_level(logging.DEBUG):
        escenario.ejecutar()

    assert caplog.records
    for dato in (*NOMBRES, *CEDULAS, CELULAR, CORREO, NOMBRES[0].upper()):
        assert dato not in caplog.text


def test_ejecutar_marca_en_curso_mientras_corre() -> None:
    registro = RegistroMigracion()
    observado: list[bool] = []

    class LectorQueObserva(LectorDoble):
        def leer(self, rutas: Sequence[Path]) -> LibrosLeidos:
            observado.append(registro.en_curso)
            return super().leer(rutas)

    escenario = Escenario(lector=LectorQueObserva(FILAS), registro=registro)
    escenario.ejecutar()

    assert observado == [True]
    assert registro.en_curso is False
