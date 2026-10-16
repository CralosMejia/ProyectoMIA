"""Comandos de operacion del backend (composition root propio, fuera de la API web).

Uso (dentro del contenedor del backend):

    docker compose exec backend python -m app.cli reentrenar
    docker compose exec backend python -m app.cli adoptar-modelo

``reentrenar`` (CU-02, comando manual) evalua los mismos criterios que el reentrenamiento
programado sin mirar la fecha programada, e imprime una linea con el resultado y su motivo
(sin datos de socios). Codigos de salida:

- ``0``: intento registrado (``ENTRENADO``, ``CRITERIOS_NO_CUMPLIDOS``, ``NO_SUPERA_VIGENTE``);
- ``1``: ``FALLIDO``, sistema no listo o configuracion invalida;
- ``2``: ya hay un reentrenamiento en curso, o falta el subcomando (se muestra la ayuda).

``adoptar-modelo`` (R-015, M01) entrena con todos los evaluables al corte de los datos y pone en
uso la version ``vigente + 1`` (la anterior se conserva), sin los criterios de CU-02 y sin
mover la proxima fecha programada; modelo e intento en una sola transaccion. Codigos de
salida:

- ``0``: version nueva en uso (imprime "vN en uso");
- ``1``: sistema no listo o sin modelo vigente, fallo del entrenamiento (no se guarda nada),
  base inaccesible o configuracion invalida;
- ``2``: ya hay un reentrenamiento en curso.
"""

import argparse
import sys
from collections.abc import Callable, Sequence

from pydantic import ValidationError
from sqlalchemy import Engine
from sqlalchemy.exc import ArgumentError, SQLAlchemyError

from app.api.dependencies import crear_adopcion, crear_reentrenamiento
from app.application.modelo.dtos import ResultadoReentrenamientoDTO
from app.core.config import Settings
from app.domain.common.clock import Clock
from app.domain.common.enums import ResultadoReentrenamiento
from app.domain.common.predictor import PredictorModel
from app.infrastructure.persistence.database import create_database_engine

SALIDA_OK = 0
SALIDA_ERROR = 1
SALIDA_EN_CURSO = 2
SALIDA_USO = 2  # convencion de argparse para un uso incorrecto
MENSAJE_CONFIGURACION = (
    "Configuracion invalida: revise DATABASE_URL y las variables del reentrenamiento."
)
_REGISTRADOS = frozenset(
    {
        ResultadoReentrenamiento.ENTRENADO,
        ResultadoReentrenamiento.CRITERIOS_NO_CUMPLIDOS,
        ResultadoReentrenamiento.NO_SUPERA_VIGENTE,
    }
)


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="python -m app.cli", description=__doc__.split("\n")[0])
    subcomandos = parser.add_subparsers(dest="comando")
    subcomandos.add_parser(
        "reentrenar",
        help="Reentrena el modelo ahora si se cumplen los criterios (CU-02).",
    )
    subcomandos.add_parser(
        "adoptar-modelo",
        help="Entrena y pone en uso un modelo nuevo (version vigente + 1) sin criterios (M01).",
    )
    return parser


def _ejecutar(
    accion: Callable[[Engine, Settings], ResultadoReentrenamientoDTO],
) -> ResultadoReentrenamientoDTO | int:
    """Configuracion, motor y errores de base comunes; un ``int`` es el codigo de salida."""
    try:
        settings = Settings()  # valores desde variables de entorno
    except ValidationError:
        # Mensaje fijo: nunca se muestra el valor de ninguna variable.
        print(MENSAJE_CONFIGURACION, file=sys.stderr)
        return SALIDA_ERROR
    try:
        engine = create_database_engine(settings.DATABASE_URL.get_secret_value())
    except (ArgumentError, ValueError):
        print(MENSAJE_CONFIGURACION, file=sys.stderr)
        return SALIDA_ERROR
    try:
        return accion(engine, settings)
    except SQLAlchemyError as exc:
        # Solo el tipo: el mensaje del driver puede citar el servidor o la consulta.
        print(f"No se pudo acceder a la base de datos ({type(exc).__name__}).", file=sys.stderr)
        return SALIDA_ERROR
    finally:
        engine.dispose()


def reentrenar(*, predictor: PredictorModel | None = None, clock: Clock | None = None) -> int:
    resultado = _ejecutar(
        lambda engine, settings: crear_reentrenamiento(
            engine, settings, predictor, clock
        ).ejecutar_manual()
    )
    if isinstance(resultado, int):
        return resultado
    if resultado.en_curso:
        print(resultado.motivo)
        return SALIDA_EN_CURSO
    if resultado.resultado is None:
        print(resultado.motivo)
        return SALIDA_ERROR
    print(f"{resultado.resultado.value}: {resultado.motivo}")
    return SALIDA_OK if resultado.resultado in _REGISTRADOS else SALIDA_ERROR


def adoptar_modelo(*, predictor: PredictorModel | None = None, clock: Clock | None = None) -> int:
    resultado = _ejecutar(
        lambda engine, _settings: crear_adopcion(engine, predictor, clock).ejecutar()
    )
    if isinstance(resultado, int):
        return resultado
    print(resultado.motivo)
    if resultado.en_curso:
        return SALIDA_EN_CURSO
    if resultado.resultado is ResultadoReentrenamiento.ENTRENADO:
        return SALIDA_OK
    return SALIDA_ERROR


def main(
    argv: Sequence[str] | None = None,
    *,
    predictor: PredictorModel | None = None,
    clock: Clock | None = None,
) -> int:
    """Punto de entrada; ``predictor`` y ``clock`` explicitos solo para pruebas."""
    parser = _parser()
    argumentos = parser.parse_args(argv)
    if argumentos.comando == "reentrenar":
        return reentrenar(predictor=predictor, clock=clock)
    if argumentos.comando == "adoptar-modelo":
        return adoptar_modelo(predictor=predictor, clock=clock)
    parser.print_help()
    return SALIDA_USO


if __name__ == "__main__":
    sys.exit(main())
