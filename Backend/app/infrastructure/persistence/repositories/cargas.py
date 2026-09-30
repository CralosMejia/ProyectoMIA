"""Repositorios SQLAlchemy de la carga por plantilla (CU-01): consultas y escritura.

Trabajan siempre dentro de la transaccion de la ``Session`` recibida (unit of work): quien
llama la abre y decide si confirma o revierte; aqui no se controla la transaccion. Cada
lectura es **una** consulta parametrizada (listas con ``IN`` expandido), sin N+1, y filtra
siempre ``deleted_at IS NULL``. ``created_at``/``updated_at`` salen del ``Clock`` inyectado.

- Enlace por cedula (decision (d) de R-007): el historico guardo la cedula como digitos y
  perdio el cero inicial, asi que ``0XXXXXXXXX`` tambien se busca como ``XXXXXXXXX``; la
  coincidencia exacta tiene prioridad. La cedula historica no se reescribe.
- Enlace por nombre: solo socios sin cedula (``ix_socios_nombre_normalizado_sin_cedula``).
- Duplicados: claves de membresias con ambas fechas (``ix_membresias_socio_id_fecha_vencimiento``).
"""

from collections.abc import Iterable, Sequence

from sqlalchemy import ColumnElement, case, or_, select, update
from sqlalchemy.orm import InstrumentedAttribute, Session

from app.application.cargas.ports import ClaveMembresia
from app.application.historial.ports import NuevaCarga, NuevaMembresia, NuevoSocio
from app.domain.common.clock import Clock
from app.domain.common.enums import Plan
from app.infrastructure.persistence.models.historial import Membresia, Socio
from app.infrastructure.persistence.repositories.historial import (
    SqlAlchemyCargaRepository,
    SqlAlchemyMembresiaRepository,
    SqlAlchemySocioRepository,
)

_LONGITUD_CEDULA = 10


def _sin_cero_inicial(cedula: str) -> str | None:
    """Forma historica de una cedula de 10 digitos que empieza por 0 (9 digitos)."""
    if len(cedula) == _LONGITUD_CEDULA and cedula.startswith("0") and cedula.isdigit():
        return cedula[1:]
    return None


class SqlAlchemyConsultasCarga:
    """Implementa ``ConsultasCarga``."""

    def __init__(self, session: Session, clock: Clock) -> None:
        self._session = session
        self._clock = clock

    def socios_por_cedulas(self, cedulas: Iterable[str]) -> dict[str, int]:
        pedidas = sorted(set(cedulas))
        if not pedidas:
            return {}
        variantes = {c: _sin_cero_inicial(c) for c in pedidas}
        buscadas = set(pedidas) | {v for v in variantes.values() if v is not None}
        filas = self._session.execute(
            select(Socio.cedula, Socio.id).where(
                Socio.cedula.in_(sorted(buscadas)), Socio.deleted_at.is_(None)
            )
        ).all()
        por_cedula = {str(f.cedula): int(f.id) for f in filas}
        resultado: dict[str, int] = {}
        for cedula in pedidas:
            variante = variantes[cedula]
            if cedula in por_cedula:
                resultado[cedula] = por_cedula[cedula]
            elif variante is not None and variante in por_cedula:
                resultado[cedula] = por_cedula[variante]
        return resultado

    def socios_sin_cedula_por_nombres(self, nombres: Iterable[str]) -> dict[str, list[int]]:
        buscados = sorted(set(nombres))
        if not buscados:
            return {}
        filas = self._session.execute(
            select(Socio.nombre_normalizado, Socio.id)
            .where(
                Socio.nombre_normalizado.in_(buscados),
                Socio.cedula.is_(None),
                Socio.deleted_at.is_(None),
            )
            .order_by(Socio.id)
        ).all()
        resultado: dict[str, list[int]] = {}
        for fila in filas:
            resultado.setdefault(str(fila.nombre_normalizado), []).append(int(fila.id))
        return resultado

    def claves_existentes(self, socio_ids: Iterable[int]) -> set[ClaveMembresia]:
        ids = sorted(set(socio_ids))
        if not ids:
            return set()
        filas = self._session.execute(
            select(
                Membresia.socio_id,
                Membresia.fecha_inicio,
                Membresia.fecha_vencimiento,
                Membresia.plan,
            ).where(
                Membresia.socio_id.in_(ids),
                Membresia.deleted_at.is_(None),
                Membresia.fecha_inicio.is_not(None),
                Membresia.fecha_vencimiento.is_not(None),
            )
        ).all()
        return {
            ClaveMembresia(
                socio_id=int(f.socio_id),
                fecha_inicio=f.fecha_inicio,
                fecha_vencimiento=f.fecha_vencimiento,
                plan=Plan(f.plan),
            )
            for f in filas
        }


def _si_vacio(
    columna: InstrumentedAttribute[str | None], valor: str | None
) -> ColumnElement[str | None] | InstrumentedAttribute[str | None]:
    """``valor`` solo si la columna esta vacia (``NULL`` o ``''``) y hay valor nuevo."""
    if valor is None:
        return columna
    return case((or_(columna.is_(None), columna == ""), valor), else_=columna)


class SqlAlchemyEscrituraCarga:
    """Implementa ``EscrituraCarga`` reutilizando las inserciones masivas del historial."""

    def __init__(self, session: Session, clock: Clock) -> None:
        self._session = session
        self._clock = clock
        self._socios = SqlAlchemySocioRepository(session, clock)
        self._membresias = SqlAlchemyMembresiaRepository(session, clock)
        self._cargas = SqlAlchemyCargaRepository(session, clock)

    def crear_socios(self, socios: Sequence[NuevoSocio]) -> list[int]:
        return self._socios.insertar_en_bloque(socios)

    def asignar_cedula(
        self, socio_id: int, cedula: str, celular: str | None, correo: str | None
    ) -> None:
        self._session.execute(
            update(Socio)
            .where(Socio.id == socio_id, Socio.deleted_at.is_(None))
            .values(
                cedula=cedula,
                celular=_si_vacio(Socio.celular, celular),
                correo=_si_vacio(Socio.correo, correo),
                updated_at=self._clock.now(),
            )
        )

    def insertar_membresias(self, membresias: Sequence[NuevaMembresia]) -> int:
        return self._membresias.insertar_en_bloque(membresias)

    def crear_carga(self, carga: NuevaCarga) -> int:
        return self._cargas.crear(carga)
