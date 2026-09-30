"""Casos de uso ``PrevisualizarCarga`` y ``ConfirmarCarga`` con dobles en memoria (R-007 T8).

Sin login (RT-12): no hay propietario ni pruebas de aislamiento entre usuarios.
Datos 100 % ficticios (``fila_plantilla`` de los fixtures sinteticos).
"""

import logging
from datetime import date

import pytest

from app.application.cargas.procesar_carga import (
    MENSAJE_CON_ERRORES,
    MENSAJE_MIGRACION_NO_COMPLETADA,
    MENSAJE_SIN_FILAS_NUEVAS,
    CargaConErroresError,
    CargaSinFilasNuevasError,
    ConfirmarCarga,
    MigracionNoCompletadaError,
    PrevisualizarCarga,
    nombre_base,
)
from app.domain.cargas.fila import FilaPlantilla, PlantillaLeida
from app.domain.common.enums import EstadoMigracion, OrigenMembresia, TipoCarga
from app.domain.historico.normalizacion import normalizar_nombre
from tests.fixtures.generar_fixtures import fila_plantilla
from tests.unit.application.cargas.dobles import (
    INSTANTE,
    Almacen,
    LectorEnMemoria,
    RelojFijo,
    SocioGuardado,
    UnidadDeTrabajoEnMemoria,
)

pytestmark = pytest.mark.unit

CONTENIDO = b"PK\x03\x04plantilla"


def filas(n: int = 6) -> list[FilaPlantilla]:
    return [FilaPlantilla.desde_valores(i + 2, fila_plantilla(i)) for i in range(n)]


def con_valor(fila: FilaPlantilla, indice_columna: int, valor: object) -> FilaPlantilla:
    valores = [fila.valor(letra) for letra in "ABCDEFGHIJKLMN"]
    valores[indice_columna] = valor
    return FilaPlantilla.desde_valores(fila.fila, valores)


def previsualizar(almacen: Almacen, lista: list[FilaPlantilla]) -> PrevisualizarCarga:
    return PrevisualizarCarga(
        LectorEnMemoria(PlantillaLeida(tuple(lista))), UnidadDeTrabajoEnMemoria(almacen)
    )


def confirmar(almacen: Almacen, lista: list[FilaPlantilla]) -> ConfirmarCarga:
    return ConfirmarCarga(
        LectorEnMemoria(PlantillaLeida(tuple(lista))),
        UnidadDeTrabajoEnMemoria(almacen),
        RelojFijo(),
    )


# ---------------------------------------------------------------- vista previa


def test_previsualizar_six_new_valid_rows_counts_and_writes_nothing() -> None:
    almacen = Almacen()
    lista = filas()

    vista = previsualizar(almacen, lista).ejecutar(CONTENIDO)

    assert vista.filas_leidas == 6
    assert vista.filas_validas == 6
    assert vista.filas_con_error == 0
    assert vista.filas_duplicadas == 0
    assert vista.errores == []
    assert vista.puede_confirmar is True
    vencimientos = [f.fecha_vencimiento for f in lista]
    assert vista.vencimiento_desde == min(v for v in vencimientos if isinstance(v, date))
    assert vista.vencimiento_hasta == max(v for v in vencimientos if isinstance(v, date))
    assert almacen.escrituras == []
    assert almacen.commits == 0
    assert "bloquear" not in almacen.eventos


def test_previsualizar_row_with_error_reports_row_column_and_cannot_confirm() -> None:
    almacen = Almacen()
    lista = filas()
    lista[1] = con_valor(lista[1], 2, "1700000000")  # verificador invalido en C

    vista = previsualizar(almacen, lista).ejecutar(CONTENIDO)

    assert vista.filas_con_error == 1
    assert vista.filas_validas == 5
    assert [(e.fila, e.columna) for e in vista.errores] == [(3, "C")]
    assert "1700000000" not in vista.errores[0].motivo
    assert vista.puede_confirmar is False


def test_previsualizar_empty_file_cannot_confirm() -> None:
    vista = previsualizar(Almacen(), []).ejecutar(CONTENIDO)

    assert vista.filas_leidas == 0
    assert vista.vencimiento_desde is None
    assert vista.vencimiento_hasta is None
    assert vista.puede_confirmar is False


def test_previsualizar_existing_membership_is_counted_as_duplicate() -> None:
    almacen = Almacen()
    confirmar(almacen, filas()).ejecutar(CONTENIDO, "plantilla.xlsx")

    vista = previsualizar(almacen, filas()).ejecutar(CONTENIDO)

    assert vista.filas_duplicadas == 6
    assert vista.filas_validas == 6
    assert vista.puede_confirmar is False


@pytest.mark.parametrize(
    "estado", [EstadoMigracion.PENDIENTE, EstadoMigracion.EN_CURSO], ids=lambda e: e.value
)
def test_previsualizar_migration_not_completed_raises(estado: EstadoMigracion) -> None:
    almacen = Almacen(estado=estado)

    with pytest.raises(MigracionNoCompletadaError, match=MENSAJE_MIGRACION_NO_COMPLETADA):
        previsualizar(almacen, filas()).ejecutar(CONTENIDO)


# ---------------------------------------------------------------- confirmacion


def test_confirmar_locks_before_querying_writes_everything_and_commits_once() -> None:
    almacen = Almacen()

    carga = confirmar(almacen, filas()).ejecutar(CONTENIDO, "C:\\datos\\septiembre.xlsx")

    assert almacen.eventos.index("bloquear") < almacen.eventos.index("consultas.socios_por_cedulas")
    assert almacen.eventos.index("bloquear") < almacen.eventos.index("consultas.claves_existentes")
    assert almacen.eventos[-1] == "commit"
    assert almacen.commits == 1
    assert len(almacen.socios) == 6
    assert len(almacen.membresias) == 6
    assert carga.id == 1
    assert carga.fecha_carga == INSTANTE
    assert carga.nombre_archivo == "septiembre.xlsx"
    assert (carga.filas_leidas, carga.filas_guardadas, carga.filas_duplicadas) == (6, 6, 0)
    assert carga.socios_enlazados == 0
    assert carga.avisos_enlace == []
    [guardada] = almacen.cargas
    assert guardada.tipo is TipoCarga.PLANTILLA
    assert guardada.fecha_carga == INSTANTE
    assert (guardada.filas_leidas, guardada.filas_guardadas, guardada.filas_duplicadas) == (
        6,
        6,
        0,
    )


def test_confirmar_memberships_follow_decision_i() -> None:
    almacen = Almacen()
    lista = filas()

    confirmar(almacen, lista).ejecutar(CONTENIDO, "plantilla.xlsx")

    for fila, membresia in zip(lista, almacen.membresias, strict=True):
        assert membresia.origen is OrigenMembresia.PLANTILLA
        assert membresia.carga_id == 1
        assert membresia.inicio_aproximado is False
        assert membresia.fecha_inicio == fila.fecha_inicio
        assert membresia.fecha_actividad == membresia.fecha_inicio
        assert membresia.fecha_vencimiento == fila.fecha_vencimiento
        assert membresia.referencia_origen is None
        assert membresia.plan_original == fila.plan
        assert membresia.forma_pago_original == fila.forma_pago
        assert membresia.estado_registro is not None
        assert membresia.estado_registro.value == fila.estado_registro


def test_confirmar_file_with_errors_raises_and_writes_nothing() -> None:
    almacen = Almacen()
    lista = filas()
    lista[1] = con_valor(lista[1], 2, "1700000000")

    with pytest.raises(CargaConErroresError, match=MENSAJE_CON_ERRORES):
        confirmar(almacen, lista).ejecutar(CONTENIDO, "plantilla.xlsx")

    assert almacen.escrituras == []
    assert almacen.commits == 0


def test_confirmar_same_content_twice_second_raises_without_new_rows() -> None:
    almacen = Almacen()
    confirmar(almacen, filas()).ejecutar(CONTENIDO, "plantilla.xlsx")

    with pytest.raises(CargaSinFilasNuevasError, match=MENSAJE_SIN_FILAS_NUEVAS):
        confirmar(almacen, filas()).ejecutar(CONTENIDO, "plantilla.xlsx")

    assert len(almacen.membresias) == 6
    assert len(almacen.cargas) == 1
    assert almacen.commits == 1


def test_confirmar_empty_file_raises_without_new_rows() -> None:
    almacen = Almacen()

    with pytest.raises(CargaSinFilasNuevasError):
        confirmar(almacen, []).ejecutar(CONTENIDO, "plantilla.xlsx")

    assert almacen.escrituras == []
    assert almacen.commits == 0


def test_confirmar_write_failure_midway_does_not_commit() -> None:
    almacen = Almacen(fallar_en_membresias=True)

    with pytest.raises(RuntimeError):
        confirmar(almacen, filas()).ejecutar(CONTENIDO, "plantilla.xlsx")

    assert almacen.commits == 0
    assert "commit" not in almacen.eventos


def test_confirmar_migration_not_completed_raises_and_writes_nothing() -> None:
    almacen = Almacen(estado=EstadoMigracion.PENDIENTE)

    with pytest.raises(MigracionNoCompletadaError):
        confirmar(almacen, filas()).ejecutar(CONTENIDO, "plantilla.xlsx")

    assert almacen.escrituras == []
    assert almacen.commits == 0


def test_confirmar_links_existing_by_cedula_and_by_unique_name() -> None:
    almacen = Almacen()
    lista = filas(2)
    cedula_0 = str(lista[0].cedula)
    por_cedula = almacen.agregar_socio(SocioGuardado(cedula_0, "OTRO NOMBRE"))
    por_nombre = almacen.agregar_socio(
        SocioGuardado(None, normalizar_nombre(lista[1].nombre), celular="0999999999")
    )

    carga = confirmar(almacen, lista).ejecutar(CONTENIDO, "plantilla.xlsx")

    assert carga.socios_enlazados == 2
    assert len(almacen.socios) == 2  # ningun socio nuevo
    assert almacen.socios[por_nombre].cedula == str(lista[1].cedula)
    assert almacen.socios[por_nombre].celular == "0999999999"
    assert [m.socio_id for m in almacen.membresias] == [por_cedula, por_nombre]


def test_confirmar_homonyms_create_new_member_with_notice_without_name() -> None:
    almacen = Almacen()
    lista = filas(1)
    nombre = normalizar_nombre(lista[0].nombre)
    almacen.agregar_socio(SocioGuardado(None, nombre))
    almacen.agregar_socio(SocioGuardado(None, nombre))

    carga = confirmar(almacen, lista).ejecutar(CONTENIDO, "plantilla.xlsx")

    assert carga.avisos_enlace == [
        "Fila 2: hay varios socios históricos con el mismo nombre; se creó un socio nuevo."
    ]
    assert nombre not in carga.avisos_enlace[0]
    assert carga.socios_enlazados == 0
    assert len(almacen.socios) == 3


def test_confirmar_partial_duplicates_saves_only_new_rows() -> None:
    almacen = Almacen()
    confirmar(almacen, filas(2)).ejecutar(CONTENIDO, "primera.xlsx")

    carga = confirmar(almacen, filas(4)).ejecutar(CONTENIDO, "segunda.xlsx")

    assert (carga.filas_leidas, carga.filas_guardadas, carga.filas_duplicadas) == (4, 2, 2)
    assert carga.socios_enlazados == 0  # las duplicadas no cuentan como enlazadas
    assert len(almacen.membresias) == 4


def test_confirmar_does_not_log_personal_data(caplog: pytest.LogCaptureFixture) -> None:
    lista = filas()

    with caplog.at_level(logging.DEBUG):
        confirmar(Almacen(), lista).ejecutar(CONTENIDO, "plantilla.xlsx")

    texto = caplog.text
    for fila in lista:
        for valor in (fila.nombre, fila.cedula, fila.celular, fila.correo):
            assert str(valor) not in texto


def test_nombre_base_strips_path_and_truncates_to_255() -> None:
    assert nombre_base("/datos/a/b.xlsx") == "b.xlsx"
    assert nombre_base("C:\\x\\y.xlsx") == "y.xlsx"
    assert len(nombre_base("n" * 300 + ".xlsx")) == 255
    assert nombre_base(None) == "plantilla.xlsx"
