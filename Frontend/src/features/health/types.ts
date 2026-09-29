export type HealthStatus = 'ok' | 'degraded'
export type DatabaseStatus = 'up' | 'down'

export interface Health {
  status: HealthStatus
  database: DatabaseStatus
  checkedAt: Date
}
