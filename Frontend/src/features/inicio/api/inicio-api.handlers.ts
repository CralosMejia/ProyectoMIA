import { http, HttpResponse } from 'msw'

/** Datos simulados coherentes con los ejemplos del contrato (sistema y alertas). */
export const handlers = [
  http.get('*/api/v1/sistema/estado', () =>
    HttpResponse.json({
      estado: 'LISTO',
      migracion_historica: 'COMPLETADA',
      modelo_vigente: {
        version: 'v1',
        fecha_entrenamiento: '2026-09-28T14:30:00Z',
        ciclos_entrenamiento: 1843,
      },
      ultima_carga_en: '2026-09-27T16:05:00Z',
      proxima_fecha_reentrenamiento: '2026-10-28',
    }),
  ),
  http.get('*/api/v1/alertas', () => HttpResponse.json({ vencidas: 2, hoy: 3, proximos_7_dias: 5 })),
]
