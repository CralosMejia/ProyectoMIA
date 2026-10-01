"""Comando ``python -m app.cli reentrenar`` (CU-02, T11) contra PostgreSQL real.

Se invoca ``main`` en proceso con ``DATABASE_URL`` apuntando a la base ``*_test`` y un reloj
fijo (hoy = 2026-09-30). Datos sinteticos de ``reentrenamiento_datos``.
"""

import subprocess
import sys
from collections.abc import Iterator
from datetime import date

import pytest
from sqlalchemy import Engine
from sqlalchemy.engine import URL

from app.cli import main
from app.infrastructure.persistence.unit_of_work_reentrenamiento import (
    AbridorBloqueoReentrenamiento,
)
from tests.integration.reentrenamiento_datos import (
    BACKEND_DIR,
    Reloj,
    contar,
    limpiar_base,
    proxima_fecha,
    sembrar,
)

pytestmark = pytest.mark.integration

PROGRAMADA = date(2026, 12, 15)


@pytest.fixture
def base(
    migrated_engine: Engine, test_database_url: URL, monkeypatch: pytest.MonkeyPatch
) -> Iterator[Engine]:
    monkeypatch.setenv("DATABASE_URL", test_database_url.render_as_string(hide_password=False))
    try:
        yield migrated_engine
    finally:
        limpiar_base(migrated_engine)


def _sin_datos_personales(texto: str) -> None:
    assert "Socio Sintetico" not in texto
    assert "SOCIO SINTETICO" not in texto


def test_reentrenar_con_datos_suficientes_entrena_v2_y_conserva_v1(
    base: Engine, capsys: pytest.CaptureFixture[str]
) -> None:
    sembrar(base, programada=PROGRAMADA)

    codigo = main(["reentrenar"], clock=Reloj())

    salida = capsys.readouterr()
    assert codigo == 0
    assert "ENTRENADO" in salida.out
    assert "v2" in salida.out
    _sin_datos_personales(salida.out + salida.err)
    assert contar(base, "SELECT version FROM modelos WHERE vigente") == 2
    assert contar(base, "SELECT count(*) FROM modelos WHERE version = 1 AND NOT vigente") == 1
    assert (
        contar(
            base,
            "SELECT count(*) FROM intentos_reentrenamiento "
            "WHERE disparador = 'MANUAL' AND resultado = 'ENTRENADO' AND modelo_id IS NOT NULL",
        )
        == 1
    )
    assert proxima_fecha(base) == date(2027, 3, 30)


def test_reentrenar_sin_datos_nuevos_criterios_no_cumplidos_sin_version_nueva(
    base: Engine, capsys: pytest.CaptureFixture[str]
) -> None:
    sembrar(base, programada=PROGRAMADA, nuevas=False)

    codigo = main(["reentrenar"], clock=Reloj())

    salida = capsys.readouterr()
    assert codigo == 0
    assert "CRITERIOS_NO_CUMPLIDOS" in salida.out
    assert "ciclos nuevos evaluables" in salida.out
    _sin_datos_personales(salida.out + salida.err)
    assert contar(base, "SELECT count(*) FROM modelos") == 1
    assert proxima_fecha(base) == PROGRAMADA


def test_reentrenar_con_el_bloqueo_tomado_por_otra_sesion_sale_con_2(
    base: Engine, capsys: pytest.CaptureFixture[str]
) -> None:
    sembrar(base, programada=PROGRAMADA)

    with AbridorBloqueoReentrenamiento(base)() as bloqueo:
        assert bloqueo.intentar_adquirir() is True
        try:
            codigo = main(["reentrenar"], clock=Reloj())
        finally:
            bloqueo.liberar()

    assert codigo == 2
    assert "Ya hay un reentrenamiento en curso." in capsys.readouterr().out
    assert contar(base, "SELECT count(*) FROM intentos_reentrenamiento") == 1  # el INICIAL


def test_reentrenar_sistema_no_listo_sale_con_1(
    base: Engine, capsys: pytest.CaptureFixture[str]
) -> None:
    limpiar_base(base)

    codigo = main(["reentrenar"], clock=Reloj())

    assert codigo == 1
    assert "El sistema aun no esta listo." in capsys.readouterr().out


def test_reentrenar_sin_database_url_sale_con_1_sin_mostrar_valores(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    monkeypatch.delenv("DATABASE_URL", raising=False)
    monkeypatch.setenv("CORS_ORIGINS", "http://valor-que-no-debe-salir.example")

    codigo = main(["reentrenar"])

    salida = capsys.readouterr()
    assert codigo == 1
    assert "DATABASE_URL" in salida.err
    assert "valor-que-no-debe-salir" not in salida.out + salida.err


def test_cli_sin_subcomando_muestra_ayuda_y_sale_con_2() -> None:
    proceso = subprocess.run(
        [sys.executable, "-m", "app.cli"],
        cwd=BACKEND_DIR,
        capture_output=True,
        text=True,
        timeout=60,
        check=False,
    )

    assert proceso.returncode == 2
    assert "reentrenar" in proceso.stdout
    assert "usage" in proceso.stdout.lower()
