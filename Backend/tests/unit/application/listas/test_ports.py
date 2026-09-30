"""Contratos del puerto de listas priorizadas (R-004 T2): Protocol, DTOs y aislamiento.

Sin login (RT-12): no hay propietario ni pruebas de aislamiento entre usuarios.
"""

import ast
import inspect
from collections.abc import Sequence
from dataclasses import FrozenInstanceError, replace
from datetime import UTC, date, datetime
from decimal import Decimal

import pytest

from app.application.listas import ports
from app.application.listas.ports import (
    ItemLista,
    ListaDetalle,
    ListaRepository,
    ListaResumen,
    NuevaLista,
    NuevaPrediccion,
)
from app.domain.common.enums import NivelRiesgo, Plan

pytestmark = pytest.mark.unit

INSTANTE = datetime(2026, 9, 1, 12, 0, tzinfo=UTC)


def nueva_prediccion(**cambios: object) -> NuevaPrediccion:
    base = NuevaPrediccion(
        membresia_id=1,
        socio_id=1,
        score=Decimal("0.75"),
        nivel_riesgo=NivelRiesgo.ALTO,
        factores_principales=("Pocos ciclos previos",),
        prioridad=1,
        dentro_top_k=True,
    )
    return replace(base, **cambios)  # type: ignore[arg-type]  # construccion generica del test


class ListaRepositoryEnMemoria:
    def __init__(self) -> None:
        self.listas: list[ListaDetalle] = []

    def crear(self, lista: NuevaLista, predicciones: Sequence[NuevaPrediccion]) -> int:
        lista_id = len(self.listas) + 1
        items = tuple(
            ItemLista(
                prediccion_id=i + 1,
                membresia_id=p.membresia_id,
                socio_id=p.socio_id,
                prioridad=p.prioridad,
                socio_nombre="Socio Sintetico",
                celular=None,
                cedula=None,
                plan=Plan.MENSUAL,
                fecha_vencimiento=date(2026, 9, 15),
                monto_cobrado=None,
                score=p.score,
                nivel_riesgo=p.nivel_riesgo,
                factores_principales=list(p.factores_principales),
                dentro_top_k=p.dentro_top_k,
            )
            for i, p in enumerate(predicciones)
        )
        self.listas.append(
            ListaDetalle(
                id=lista_id,
                modelo_id=lista.modelo_id,
                modelo_version=1,
                fecha_generacion=lista.fecha_generacion,
                creada_en=INSTANTE,
                horizonte_dias=lista.horizonte_dias,
                top_k=lista.top_k,
                umbral_alto=Decimal("0.7"),
                umbral_medio=Decimal("0.4"),
                items=items,
            )
        )
        return lista_id

    def obtener(self, lista_id: int) -> ListaDetalle | None:
        return next((lista for lista in self.listas if lista.id == lista_id), None)

    def ultima(self) -> ListaDetalle | None:
        return self.listas[-1] if self.listas else None

    def listar(self) -> list[ListaResumen]:
        return [
            ListaResumen(
                id=lista.id,
                fecha_generacion=lista.fecha_generacion,
                creada_en=lista.creada_en,
                modelo_version=lista.modelo_version,
                horizonte_dias=lista.horizonte_dias,
                top_k=lista.top_k,
                total_items=len(lista.items),
            )
            for lista in reversed(self.listas)
        ]


def test_port_in_memory_double_satisfies_protocol() -> None:
    repo: ListaRepository = ListaRepositoryEnMemoria()

    assert isinstance(repo, ListaRepository)
    assert not isinstance(object(), ListaRepository)


def test_in_memory_double_follows_the_contract() -> None:
    repo = ListaRepositoryEnMemoria()
    lista_id = repo.crear(NuevaLista(1, date(2026, 8, 31), 30, 25), [nueva_prediccion()])

    detalle = repo.obtener(lista_id)
    assert detalle is not None
    assert detalle.items[0].score == Decimal("0.75")
    assert repo.obtener(999) is None
    assert repo.ultima() == detalle
    assert [r.total_items for r in repo.listar()] == [1]


@pytest.mark.parametrize("score", [Decimal("-0.0001"), Decimal("1.0001"), Decimal("2")])
def test_nueva_prediccion_score_out_of_range_raises_value_error(score: Decimal) -> None:
    with pytest.raises(ValueError, match="score"):
        nueva_prediccion(score=score)


@pytest.mark.parametrize("score", [Decimal("0"), Decimal("1")])
def test_nueva_prediccion_score_limits_are_accepted(score: Decimal) -> None:
    assert nueva_prediccion(score=score).score == score


def test_nueva_prediccion_non_positive_priority_raises_value_error() -> None:
    with pytest.raises(ValueError, match="prioridad"):
        nueva_prediccion(prioridad=0)


def test_nueva_lista_non_positive_horizon_or_top_k_raises_value_error() -> None:
    with pytest.raises(ValueError, match="horizonte_dias"):
        NuevaLista(modelo_id=1, fecha_generacion=date(2026, 8, 31), horizonte_dias=0, top_k=25)
    with pytest.raises(ValueError, match="top_k"):
        NuevaLista(modelo_id=1, fecha_generacion=date(2026, 8, 31), horizonte_dias=30, top_k=0)


@pytest.mark.parametrize(
    ("valor", "campo"),
    [
        (nueva_prediccion(), "score"),
        (NuevaLista(1, date(2026, 8, 31), 30, 25), "top_k"),
    ],
)
def test_dtos_are_frozen(valor: object, campo: str) -> None:
    with pytest.raises(FrozenInstanceError):
        setattr(valor, campo, 1)


def test_ports_module_does_not_depend_on_infrastructure_or_data_libraries() -> None:
    arbol = ast.parse(inspect.getsource(ports))
    importados: set[str] = set()
    for nodo in ast.walk(arbol):
        if isinstance(nodo, ast.Import):
            importados.update(alias.name for alias in nodo.names)
        elif isinstance(nodo, ast.ImportFrom) and nodo.module:
            importados.add(nodo.module)

    assert not any(m.startswith(("sqlalchemy", "app.infrastructure")) for m in importados)
    assert not any(m.split(".")[0] in {"pandas", "numpy", "sklearn"} for m in importados)


def test_ports_docstring_states_no_commit_rollback_nor_delete() -> None:
    doc = inspect.getdoc(ports) or ""

    assert "commit" in doc
    assert "rollback" in doc
    assert "delete" in doc
    assert not any(n.startswith(("delete", "borrar")) for n in dir(ListaRepository))
