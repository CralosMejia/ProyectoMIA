"""Datos conocidos de gestiones para alertas (CU-09) y dashboard (CU-11) en ``app_db_test``.

Cada gestion tiene su propia membresia (una gestion por ciclo) y su prediccion en una lista
de un modelo ficticio. Todo es sintetico: ningun nombre, celular ni cedula real. Sirve tanto
dentro de una transaccion con rollback (``db_session``) como con datos confirmados en las
pruebas de API (que limpian con ``limpiar_retencion``).
"""

from dataclasses import dataclass, field
from datetime import UTC, date, datetime

from sqlalchemy import Connection, Engine, text

from tests.integration.persistence.test_migrations import insert, membresia, modelo, socio

INSTANTE = datetime(2026, 9, 30, 15, 0, tzinfo=UTC)
HOY = date(2026, 9, 30)
VENCIMIENTO = date(2026, 10, 5)

_TABLAS = (
    "gestiones_retencion, predicciones, listas_priorizadas, membresias, socios, cargas, "
    "intentos_reentrenamiento, modelos"
)


@dataclass
class Sembrador:
    """Crea gestiones ficticias sobre ``conexion`` (sin confirmar: lo decide quien llama)."""

    conexion: Connection
    version_modelo: int = 9101
    _lista_id: int | None = field(default=None, init=False)
    _socio_id: int | None = field(default=None, init=False)
    _n: int = field(default=0, init=False)

    def _lista(self) -> int:
        if self._lista_id is None:
            self._lista_id = insert(
                self.conexion,
                "listas_priorizadas",
                {
                    "modelo_id": modelo(self.conexion, version=self.version_modelo),
                    "fecha_generacion": HOY,
                    "horizonte_dias": 30,
                    "top_k": 10,
                    "creada_en": INSTANTE,
                    "nombre": "Lista ficticia de seguimiento",
                },
            )
        return self._lista_id

    def _socio(self) -> int:
        if self._socio_id is None:
            self._socio_id = socio(
                self.conexion,
                nombre="Socio Ficticio",
                nombre_normalizado="SOCIO FICTICIO",
                celular="0990000000",
            )
        return self._socio_id

    def campania(self, nombre: str) -> int:
        return insert(
            self.conexion,
            "campanias",
            {
                "nombre": nombre,
                "activa": True,
                "niveles_riesgo": ["ALTO"],
                "planes": ["MENSUAL"],
                "prioridad": 1,
                "es_ejemplo": False,
            },
        )

    def gestion(
        self,
        fecha_seguimiento: date = HOY,
        *,
        estado: str = "PENDIENTE",
        campania: tuple[int, str] | None = None,
        creada_en: datetime = INSTANTE,
        borrada: bool = False,
        contactado: bool | None = None,
        ofrecida: str | None = None,
        aceptada: str | None = None,
        renovo: str | None = None,
        responsable: str | None = "Responsable ficticio",
    ) -> tuple[int, int]:
        """Inserta una gestion y devuelve ``(gestion_id, prediccion_id)``."""
        self._n += 1
        membresia_id = membresia(
            self.conexion,
            socio_id=self._socio(),
            plan="MENSUAL",
            fecha_vencimiento=VENCIMIENTO,
        )
        prediccion_id = insert(
            self.conexion,
            "predicciones",
            {
                "lista_id": self._lista(),
                "membresia_id": membresia_id,
                "score": "0.81234567",
                "nivel_riesgo": "ALTO",
                "factores_principales": "[]",
                "prioridad": self._n,
                "dentro_top_k": True,
            },
        )
        gestion_id = insert(
            self.conexion,
            "gestiones_retencion",
            {
                "prediccion_id": prediccion_id,
                "membresia_id": membresia_id,
                "campania_id": None if campania is None else campania[0],
                "campania_nombre": None if campania is None else campania[1],
                "fecha_asignacion": creada_en.date(),
                "fecha_seguimiento": fecha_seguimiento,
                "estado": estado,
                "responsable": responsable,
                "contactado": contactado,
                "campania_ofrecida": ofrecida,
                "campania_aceptada": aceptada,
                "renovo_declarado": renovo,
                "cerrada_en": creada_en if estado == "CERRADA" else None,
                "created_at": creada_en,
                "updated_at": creada_en,
                "deleted_at": INSTANTE if borrada else None,
            },
        )
        return gestion_id, prediccion_id


@dataclass(frozen=True)
class DatosSeguimiento:
    """Ids de la siembra de alertas (hoy 2026-09-30)."""

    vencidas: tuple[int, ...]
    hoy: int
    hoy_prediccion: int
    proximas: tuple[int, ...]
    fuera_de_ventana: int


def sembrar_seguimiento(conexion: Connection) -> DatosSeguimiento:
    """Pendientes 09-20, 09-29, 09-30, 10-01, 10-07, 10-08 + cerrada con campana (09-30) +
    sin campana (cerrada, 09-30) + pendiente borrada (09-30).

    Esperado con hoy 2026-09-30: vencidas 2, hoy 1, proximas 2.
    """
    s = Sembrador(conexion)
    campania = (s.campania("Campaña ficticia de seguimiento"), "Campaña congelada")
    v1, _ = s.gestion(date(2026, 9, 20), campania=campania)
    v2, _ = s.gestion(date(2026, 9, 29), campania=campania)
    hoy, hoy_prediccion = s.gestion(HOY, campania=campania)
    p1, _ = s.gestion(date(2026, 10, 1), campania=campania)
    p2, _ = s.gestion(date(2026, 10, 7), campania=campania)
    fuera, _ = s.gestion(date(2026, 10, 8), campania=campania)
    s.gestion(HOY, campania=campania, estado="CERRADA", contactado=False, renovo="NO")
    s.gestion(HOY, estado="CERRADA", responsable=None)
    s.gestion(HOY, campania=campania, borrada=True)
    return DatosSeguimiento(
        vencidas=(v1, v2),
        hoy=hoy,
        hoy_prediccion=hoy_prediccion,
        proximas=(p1, p2),
        fuera_de_ventana=fuera,
    )


@dataclass(frozen=True)
class DatosDashboard:
    campania_a: int
    campania_b: int


SEPTIEMBRE = datetime(2026, 9, 15, 15, 0, tzinfo=UTC)
OCTUBRE = datetime(2026, 10, 10, 15, 0, tzinfo=UTC)
# 2026-09-30 22:00 en Ecuador: fecha de negocio de septiembre aunque en UTC ya sea octubre.
FRONTERA = datetime(2026, 10, 1, 3, 0, tzinfo=UTC)


def sembrar_dashboard(conexion: Connection) -> DatosDashboard:
    """Septiembre 2026: campana A (12: 10 cerradas con resultado -4 SI, 6 NO- y 2 pendientes),
    campana B (9 cerradas con resultado: 3 SI, 6 NO), 3 sin campana (cerradas, sin resultado),
    1 de A en octubre y 1 de B borrada.

    Embudo de septiembre (solo con campana): asignadas 21, contactadas 17, ofrecidas 11,
    aceptadas 7, renovaron 7. Por campana: A 12/8/4/10, B 9/9/3/9 (gestiones, contactados,
    renovaciones, cerradas con resultado); sin campana 3/0/0/0. Una gestion de A se crea el
    2026-10-01 03:00Z (septiembre en Ecuador).
    """
    s = Sembrador(conexion, version_modelo=9201)
    a = s.campania("Zeta renovacion")
    b = s.campania("alfa fidelizacion")
    ca, cb = (a, "Zeta renovacion"), (b, "alfa fidelizacion")

    # A: 4 SI (contactadas, ofrecidas, aceptadas), una de ellas en la frontera de mes.
    for i in range(4):
        s.gestion(
            campania=ca,
            estado="CERRADA",
            creada_en=FRONTERA if i == 0 else SEPTIEMBRE,
            contactado=True,
            ofrecida="SI",
            aceptada="SI",
            renovo="SI",
        )
    # A: 6 NO; 3 contactadas y ofrecidas sin aceptar, 3 sin contacto.
    for i in range(6):
        contactada = i < 3
        s.gestion(
            campania=ca,
            estado="CERRADA",
            creada_en=SEPTIEMBRE,
            contactado=contactada,
            ofrecida="SI" if contactada else "NO_APLICA",
            aceptada="NO" if contactada else "NO_APLICA",
            renovo="NO",
        )
    # A: 2 pendientes, una contactada con renovo PENDIENTE y otra sin resultado.
    s.gestion(
        campania=ca,
        creada_en=SEPTIEMBRE,
        contactado=True,
        ofrecida="SI",
        aceptada="PENDIENTE",
        renovo="PENDIENTE",
    )
    s.gestion(campania=ca, creada_en=SEPTIEMBRE)
    # B: 9 cerradas con resultado: 3 SI (aceptadas), 6 NO (contactadas, no ofrecidas).
    for i in range(9):
        renovo = "SI" if i < 3 else "NO"
        s.gestion(
            campania=cb,
            estado="CERRADA",
            creada_en=SEPTIEMBRE,
            contactado=True,
            ofrecida="SI" if i < 3 else "NO",
            aceptada="SI" if i < 3 else "NO_APLICA",
            renovo=renovo,
        )
    # Sin campana: nacen cerradas, sin resultado (nulo nunca cuenta).
    for _ in range(3):
        s.gestion(estado="CERRADA", creada_en=SEPTIEMBRE, responsable=None)
    # Fuera del mes o borrada.
    s.gestion(
        campania=ca,
        estado="CERRADA",
        creada_en=OCTUBRE,
        contactado=True,
        ofrecida="SI",
        aceptada="SI",
        renovo="SI",
    )
    s.gestion(
        campania=cb,
        estado="CERRADA",
        creada_en=SEPTIEMBRE,
        borrada=True,
        contactado=True,
        ofrecida="SI",
        aceptada="SI",
        renovo="SI",
    )
    return DatosDashboard(campania_a=a, campania_b=b)


def limpiar_retencion(engine: Engine) -> None:
    """Vacia gestiones, historial y modelos y borra las campanas propias (solo ``*_test``).

    Las campanas de ejemplo de ``0007`` se conservan.
    """
    nombre = engine.url.database or ""
    if not nombre.endswith("_test"):
        raise RuntimeError("limpiar_retencion solo puede ejecutarse contra una base *_test")
    with engine.begin() as conexion:
        conexion.execute(text(f"TRUNCATE {_TABLAS} RESTART IDENTITY CASCADE"))
        conexion.execute(text("DELETE FROM campanias WHERE NOT es_ejemplo"))
        conexion.execute(
            text(
                "UPDATE estado_sistema SET migracion_historica = 'PENDIENTE', "
                "proxima_fecha_reentrenamiento = NULL WHERE id = 1"
            )
        )
