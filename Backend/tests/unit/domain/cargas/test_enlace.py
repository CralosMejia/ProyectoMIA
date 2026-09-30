"""Plan de carga: enlace con el historico y duplicados (CU-01, RN-01.8, RN-01.9, D-03, D-04).

Datos sinteticos: cedulas generadas con modulo 10 y nombres ficticios.
"""

from dataclasses import replace
from datetime import date
from decimal import Decimal

import pytest

from app.domain.cargas.enlace import ClaveMembresia, PlanCarga, planificar
from app.domain.cargas.validacion import FilaValida
from app.domain.common.enums import FormaPago, Plan
from tests.fixtures.generar_fixtures import cedula_valida

pytestmark = pytest.mark.unit

CEDULA_A = cedula_valida(101)
CEDULA_B = cedula_valida(102)
NOMBRE = "LUIS FICTICIO PRUEBA"
AVISO_HOMONIMOS = (
    "Fila {}: hay varios socios históricos con el mismo nombre; se creó un socio nuevo."
)


def _fila(fila: int = 2, documento: str = CEDULA_A, **cambios: object) -> FilaValida:
    base = FilaValida(
        fila=fila,
        estado_registro=None,
        nombre="Luis Ficticio Prueba",
        nombre_normalizado=NOMBRE,
        documento=documento,
        celular="0980000002",
        correo=None,
        plan=Plan.MENSUAL,
        plan_original="MENSUAL",
        fecha_inicio=date(2026, 9, 1),
        fecha_vencimiento=date(2026, 10, 1),
        forma_pago=FormaPago.EFECTIVO,
        forma_pago_original="EFECTIVO",
        monto_facturado=None,
        monto_cobrado=Decimal("40"),
        asistencias=None,
        observaciones=None,
    )
    return replace(base, **cambios)


def _planificar(
    filas: list[FilaValida],
    socios_por_cedula: dict[str, int] | None = None,
    candidatos_por_nombre: dict[str, list[int]] | None = None,
    claves_existentes: set[ClaveMembresia] | None = None,
) -> PlanCarga:
    return planificar(
        filas,
        socios_por_cedula or {},
        candidatos_por_nombre or {},
        claves_existentes or set(),
    )


# ------------------------------------------------------------------ enlace


def test_planificar_cedula_existente_asocia_al_socio_existente() -> None:
    plan = _planificar([_fila()], socios_por_cedula={CEDULA_A: 7})
    (destino,) = plan.filas
    assert destino.socio_id == 7
    assert destino.socio_nuevo is None
    assert not destino.enlazado_por_nombre
    assert plan.socios_enlazados == 1
    assert plan.socios_nuevos == ()
    assert plan.cedulas_asignadas == ()


def test_planificar_cedula_existente_tiene_prioridad_sobre_el_nombre() -> None:
    plan = _planificar(
        [_fila()], socios_por_cedula={CEDULA_A: 7}, candidatos_por_nombre={NOMBRE: [9]}
    )
    assert plan.filas[0].socio_id == 7
    assert plan.cedulas_asignadas == ()


def test_planificar_nombre_con_un_candidato_sin_cedula_enlaza_y_asigna_cedula() -> None:
    plan = _planificar([_fila()], candidatos_por_nombre={NOMBRE: [9]})
    (destino,) = plan.filas
    assert destino.socio_id == 9
    assert destino.enlazado_por_nombre
    assert plan.socios_enlazados == 1
    (asignacion,) = plan.cedulas_asignadas
    assert (asignacion.socio_id, asignacion.cedula) == (9, CEDULA_A)
    assert asignacion.celular == "0980000002"
    assert asignacion.correo is None
    assert plan.avisos == ()


def test_planificar_nombre_con_dos_candidatos_crea_socio_nuevo_y_avisa() -> None:
    plan = _planificar([_fila(fila=5)], candidatos_por_nombre={NOMBRE: [9, 10]})
    (destino,) = plan.filas
    assert destino.socio_id is None
    assert destino.socio_nuevo == 0
    assert plan.avisos == (AVISO_HOMONIMOS.format(5),)
    assert NOMBRE not in plan.avisos[0]
    assert plan.socios_enlazados == 0
    assert plan.cedulas_asignadas == ()


def test_planificar_sin_cedula_ni_candidatos_crea_socio_nuevo() -> None:
    plan = _planificar([_fila()])
    (nuevo,) = plan.socios_nuevos
    assert (nuevo.cedula, nuevo.nombre_normalizado) == (CEDULA_A, NOMBRE)
    assert nuevo.nombre == "Luis Ficticio Prueba"
    assert plan.filas[0].socio_nuevo == 0
    assert plan.socios_enlazados == 0


def test_planificar_dos_filas_de_la_misma_cedula_nueva_crean_un_solo_socio() -> None:
    segunda = _fila(fila=3, fecha_inicio=date(2026, 10, 1), fecha_vencimiento=date(2026, 11, 1))
    plan = _planificar([_fila(), segunda])
    assert len(plan.socios_nuevos) == 1
    assert [d.socio_nuevo for d in plan.filas] == [0, 0]
    assert [d.duplicada for d in plan.filas] == [False, False]


def test_planificar_dos_filas_homonimas_ambiguas_con_misma_cedula_avisan_una_vez() -> None:
    segunda = _fila(fila=3, fecha_inicio=date(2026, 10, 1), fecha_vencimiento=date(2026, 11, 1))
    plan = _planificar([_fila(), segunda], candidatos_por_nombre={NOMBRE: [9, 10]})
    assert len(plan.socios_nuevos) == 1
    assert plan.avisos == (AVISO_HOMONIMOS.format(2),)


def test_planificar_candidato_tomado_por_otra_cedula_del_archivo_crea_socio_nuevo() -> None:
    otra = _fila(fila=3, documento=CEDULA_B)
    plan = _planificar([_fila(), otra], candidatos_por_nombre={NOMBRE: [9]})
    primera, segunda = plan.filas
    assert primera.socio_id == 9 and primera.enlazado_por_nombre
    assert segunda.socio_id is None and segunda.socio_nuevo == 0
    assert plan.socios_nuevos[0].cedula == CEDULA_B
    assert len(plan.cedulas_asignadas) == 1
    assert plan.avisos == ()


def test_planificar_segunda_fila_de_cedula_enlazada_por_nombre_reutiliza_el_enlace() -> None:
    segunda = _fila(fila=3, fecha_inicio=date(2026, 10, 1), fecha_vencimiento=date(2026, 11, 1))
    plan = _planificar([_fila(), segunda], candidatos_por_nombre={NOMBRE: [9]})
    assert [d.socio_id for d in plan.filas] == [9, 9]
    assert len(plan.cedulas_asignadas) == 1
    assert plan.socios_enlazados == 1


# ------------------------------------------------------------------ duplicados


def test_planificar_clave_existente_en_el_historico_marca_duplicada() -> None:
    clave = ClaveMembresia(7, date(2026, 9, 1), date(2026, 10, 1), Plan.MENSUAL)
    plan = _planificar([_fila()], socios_por_cedula={CEDULA_A: 7}, claves_existentes={clave})
    assert plan.filas[0].duplicada
    assert plan.filas_duplicadas == 1
    assert plan.filas_nuevas == ()
    assert plan.socios_enlazados == 0  # ninguna fila nueva quedo asociada


def test_planificar_clave_existente_de_socio_enlazado_por_nombre_marca_duplicada() -> None:
    clave = ClaveMembresia(9, date(2026, 9, 1), date(2026, 10, 1), Plan.MENSUAL)
    plan = _planificar([_fila()], candidatos_por_nombre={NOMBRE: [9]}, claves_existentes={clave})
    assert plan.filas[0].duplicada


def test_planificar_mismo_socio_con_otro_plan_no_es_duplicada() -> None:
    clave = ClaveMembresia(7, date(2026, 9, 1), date(2026, 10, 1), Plan.OTRO)
    plan = _planificar([_fila()], socios_por_cedula={CEDULA_A: 7}, claves_existentes={clave})
    assert not plan.filas[0].duplicada


def test_planificar_dos_filas_identicas_del_archivo_la_segunda_es_duplicada() -> None:
    plan = _planificar([_fila(), _fila(fila=3)])
    assert [d.duplicada for d in plan.filas] == [False, True]
    assert [d.fila.fila for d in plan.filas_nuevas] == [2]


def test_planificar_dos_filas_identicas_de_socio_existente_la_segunda_es_duplicada() -> None:
    plan = _planificar([_fila(), _fila(fila=3)], socios_por_cedula={CEDULA_A: 7})
    assert [d.duplicada for d in plan.filas] == [False, True]


# ------------------------------------------------------------------ determinismo


def test_planificar_resultado_en_orden_de_fila_y_determinista() -> None:
    filas = [_fila(fila=4, documento=CEDULA_B), _fila(fila=2), _fila(fila=3)]
    primero = _planificar(filas, candidatos_por_nombre={NOMBRE: [9]})
    segundo = _planificar(list(reversed(filas)), candidatos_por_nombre={NOMBRE: [9]})
    assert [d.fila.fila for d in primero.filas] == [2, 3, 4]
    assert primero == segundo
    # La fila 2 (cedula A) toma el candidato; la 4 (cedula B) crea socio nuevo.
    assert primero.filas[0].socio_id == 9
    assert primero.filas[2].socio_nuevo == 0


def test_planificar_sin_filas_devuelve_plan_vacio() -> None:
    plan = _planificar([])
    assert plan.filas == ()
    assert plan.filas_duplicadas == 0
    assert plan.socios_enlazados == 0


# ---------------------------------------------------- interpretaciones (test-engineer)


def test_planificar_dos_cedulas_distintas_ambiguas_avisan_una_vez_por_cedula() -> None:
    otra = _fila(fila=3, documento=CEDULA_B)
    plan = _planificar([_fila(), otra], candidatos_por_nombre={NOMBRE: [9, 10]})
    assert plan.avisos == (AVISO_HOMONIMOS.format(2), AVISO_HOMONIMOS.format(3))
    assert len(plan.socios_nuevos) == 2
    assert plan.cedulas_asignadas == ()


def test_planificar_tres_candidatos_crea_socio_nuevo_y_avisa() -> None:
    plan = _planificar([_fila()], candidatos_por_nombre={NOMBRE: [9, 10, 11]})
    assert plan.filas[0].socio_nuevo == 0
    assert plan.avisos == (AVISO_HOMONIMOS.format(2),)


def test_planificar_candidato_tomado_no_genera_aviso() -> None:
    otra = _fila(fila=3, documento=CEDULA_B)
    plan = _planificar([_fila(), otra], candidatos_por_nombre={NOMBRE: [9]})
    assert plan.avisos == ()


def test_planificar_socios_enlazados_cuenta_existentes_distintos_con_fila_nueva() -> None:
    cedula_c = cedula_valida(103)
    filas = [
        _fila(),  # socio 7 por cedula
        _fila(fila=3, fecha_inicio=date(2026, 10, 1), fecha_vencimiento=date(2026, 11, 1)),
        _fila(fila=4, documento=CEDULA_B, nombre_normalizado="OTRO NOMBRE FICTICIO"),  # 8
        _fila(fila=5, documento=cedula_c, nombre_normalizado="NUEVO NOMBRE FICTICIO"),  # nuevo
    ]
    plan = _planificar(filas, socios_por_cedula={CEDULA_A: 7, CEDULA_B: 8})
    assert plan.socios_enlazados == 2
    assert len(plan.socios_nuevos) == 1


def test_planificar_socios_enlazados_no_cuenta_socio_con_solo_filas_duplicadas() -> None:
    clave = ClaveMembresia(8, date(2026, 9, 1), date(2026, 10, 1), Plan.MENSUAL)
    filas = [_fila(), _fila(fila=3, documento=CEDULA_B)]
    plan = _planificar(
        filas, socios_por_cedula={CEDULA_A: 7, CEDULA_B: 8}, claves_existentes={clave}
    )
    assert [d.duplicada for d in plan.filas] == [False, True]
    assert plan.socios_enlazados == 1


def test_planificar_clave_difiere_en_una_fecha_no_es_duplicada() -> None:
    clave = ClaveMembresia(7, date(2026, 9, 1), date(2026, 10, 2), Plan.MENSUAL)
    plan = _planificar([_fila()], socios_por_cedula={CEDULA_A: 7}, claves_existentes={clave})
    assert not plan.filas[0].duplicada


def test_planificar_clave_de_otro_socio_no_marca_duplicada() -> None:
    clave = ClaveMembresia(8, date(2026, 9, 1), date(2026, 10, 1), Plan.MENSUAL)
    plan = _planificar([_fila()], socios_por_cedula={CEDULA_A: 7}, claves_existentes={clave})
    assert not plan.filas[0].duplicada


def test_planificar_misma_fecha_y_plan_de_cedulas_distintas_no_es_duplicada() -> None:
    otra = _fila(fila=3, documento=CEDULA_B)
    plan = _planificar([_fila(), otra])
    assert [d.duplicada for d in plan.filas] == [False, False]
    assert len(plan.socios_nuevos) == 2


def test_planificar_no_modifica_los_argumentos() -> None:
    filas = [_fila(fila=3), _fila(fila=2)]
    socios = {CEDULA_A: 7}
    candidatos = {NOMBRE: [9]}
    claves: set[ClaveMembresia] = set()
    planificar(filas, socios, candidatos, claves)
    assert [f.fila for f in filas] == [3, 2]
    assert socios == {CEDULA_A: 7}
    assert candidatos == {NOMBRE: [9]}
    assert claves == set()
