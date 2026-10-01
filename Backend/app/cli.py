"""Comandos de operacion del backend (composition root propio, fuera de la API web).

Uso (dentro del contenedor del backend):

    docker compose exec backend python -m app.cli reentrenar

``reentrenar`` (CU-02, comando manual) evalua los mismos criterios que el reentrenamiento
programado sin mirar la fecha programada, e imprime una linea con el resultado y su motivo
(sin datos de socios). Codigos de salida:

- ``0``: intento registrado (``ENTRENADO``, ``CRITERIOS_NO_CUMPLIDOS``, ``NO_SUPERA_VIGENTE``);
- ``1``: ``FALLIDO``, sistema no listo o configuracion invalida;
- ``2``: ya hay un reentrenamiento en curso, o falta el subcomando (se muestra la ayuda).
"""

import argparse
import sys
from collections.abc import Sequence

from pydantic import ValidationError
from sqlalchemy.exc import ArgumentError, SQLAlchemyError

from app.api.dependencies import crear_reentrenamiento
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
    return parser


def reentrenar(*, predictor: PredictorModel | None = None, clock: Clock | None = None) -> int:
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
        resultado = crear_reentrenamiento(engine, settings, predictor, clock).ejecutar_manual()
    except SQLAlchemyError as exc:
        # Solo el tipo: el mensaje del driver puede citar el servidor o la consulta.
        print(f"No se pudo acceder a la base de datos ({type(exc).__name__}).", file=sys.stderr)
        return SALIDA_ERROR
    finally:
        engine.dispose()

    if resultado.en_curso:
        print(resultado.motivo)
        return SALIDA_EN_CURSO
    if resultado.resultado is None:
        print(resultado.motivo)
        return SALIDA_ERROR
    print(f"{resultado.resultado.value}: {resultado.motivo}")
    return SALIDA_OK if resultado.resultado in _REGISTRADOS else SALIDA_ERROR


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
    parser.print_help()
    return SALIDA_USO


if __name__ == "__main__":
    sys.exit(main())
