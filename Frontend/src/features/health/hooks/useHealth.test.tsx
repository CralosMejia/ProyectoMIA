import { act, renderHook, waitFor } from '@testing-library/react'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { ApiError } from '../../../core/http/api-error'
import { getHealth } from '../api/health-api'
import type { Health } from '../types'
import { useHealth } from './useHealth'

vi.mock('../api/health-api', () => ({
  getHealth: vi.fn(),
}))

const getHealthMock = vi.mocked(getHealth)

const HEALTH: Health = {
  status: 'ok',
  database: 'up',
  checkedAt: new Date('2026-01-01T00:00:00Z'),
}

function deferred<T>() {
  let resolve!: (value: T) => void
  let reject!: (reason: unknown) => void
  const promise = new Promise<T>((res, rej) => {
    resolve = res
    reject = rej
  })
  return { promise, resolve, reject }
}

describe('useHealth', () => {
  beforeEach(() => {
    getHealthMock.mockReset()
  })

  afterEach(() => {
    vi.restoreAllMocks()
  })

  it('starts loading on mount and exposes data once resolved', async () => {
    const pending = deferred<Health>()
    getHealthMock.mockReturnValue(pending.promise)

    const { result } = renderHook(() => useHealth())

    expect(result.current.isLoading).toBe(true)
    expect(result.current.data).toBeNull()
    expect(result.current.error).toBeNull()

    await act(async () => {
      pending.resolve(HEALTH)
      await pending.promise
    })

    expect(result.current.isLoading).toBe(false)
    expect(result.current.data).toEqual(HEALTH)
    expect(result.current.error).toBeNull()
  })

  it('passes an AbortSignal to the service', async () => {
    getHealthMock.mockResolvedValue(HEALTH)

    const { result } = renderHook(() => useHealth())
    await waitFor(() => expect(result.current.isLoading).toBe(false))

    expect(getHealthMock.mock.calls[0]?.[0]).toBeInstanceOf(AbortSignal)
  })

  it('exposes only the error message when the service throws ApiError', async () => {
    getHealthMock.mockRejectedValue(
      new ApiError(500, 'Servidor caido', { secret: 'internal-detail' }),
    )

    const { result } = renderHook(() => useHealth())
    await waitFor(() => expect(result.current.isLoading).toBe(false))

    expect(result.current.data).toBeNull()
    expect(result.current.error).toEqual({ message: 'Servidor caido' })
    expect(result.current.error).not.toHaveProperty('body')
  })

  it('uses a generic message for non-ApiError failures', async () => {
    getHealthMock.mockRejectedValue(new Error('boom stack detail'))

    const { result } = renderHook(() => useHealth())
    await waitFor(() => expect(result.current.isLoading).toBe(false))

    expect(result.current.data).toBeNull()
    expect(result.current.error?.message).toBeTruthy()
    expect(result.current.error?.message).not.toContain('boom')
  })

  it('aborts on unmount and does not update state afterwards', async () => {
    const pending = deferred<Health>()
    let receivedSignal: AbortSignal | undefined
    getHealthMock.mockImplementation((signal?: AbortSignal) => {
      receivedSignal = signal
      return pending.promise
    })
    const consoleError = vi.spyOn(console, 'error').mockImplementation(() => {})

    const { result, unmount } = renderHook(() => useHealth())
    const snapshot = result.current
    unmount()

    expect(receivedSignal?.aborted).toBe(true)

    await act(async () => {
      pending.resolve(HEALTH)
      await pending.promise
    })

    expect(result.current).toBe(snapshot)
    expect(consoleError).not.toHaveBeenCalled()
  })

  it('does not surface an AbortError as a UI error', async () => {
    const pending = deferred<Health>()
    getHealthMock.mockReturnValue(pending.promise)
    const consoleError = vi.spyOn(console, 'error').mockImplementation(() => {})

    const { result, unmount } = renderHook(() => useHealth())
    unmount()

    await act(async () => {
      pending.reject(new DOMException('Aborted', 'AbortError'))
      await pending.promise.catch(() => undefined)
    })

    expect(result.current.error).toBeNull()
    expect(consoleError).not.toHaveBeenCalled()
  })

  it('refetch() calls the service again and updates data', async () => {
    getHealthMock.mockResolvedValueOnce(HEALTH)
    const degraded: Health = { ...HEALTH, status: 'degraded', database: 'down' }
    getHealthMock.mockResolvedValueOnce(degraded)

    const { result } = renderHook(() => useHealth())
    await waitFor(() => expect(result.current.data).toEqual(HEALTH))

    act(() => {
      result.current.refetch()
    })
    expect(result.current.isLoading).toBe(true)

    await waitFor(() => expect(result.current.isLoading).toBe(false))
    expect(getHealthMock).toHaveBeenCalledTimes(2)
    expect(result.current.data).toEqual(degraded)
  })

  it('refetch() clears a previous error when the retry succeeds', async () => {
    getHealthMock.mockRejectedValueOnce(new ApiError(0, 'Sin conexion'))
    getHealthMock.mockResolvedValueOnce(HEALTH)

    const { result } = renderHook(() => useHealth())
    await waitFor(() => expect(result.current.error).toEqual({ message: 'Sin conexion' }))

    act(() => {
      result.current.refetch()
    })

    await waitFor(() => expect(result.current.data).toEqual(HEALTH))
    expect(result.current.error).toBeNull()
  })

  it('aborts the in-flight request when refetch() starts a new one', async () => {
    const first = deferred<Health>()
    const signals: AbortSignal[] = []
    getHealthMock.mockImplementationOnce((signal?: AbortSignal) => {
      if (signal) signals.push(signal)
      return first.promise
    })
    getHealthMock.mockImplementationOnce((signal?: AbortSignal) => {
      if (signal) signals.push(signal)
      return Promise.resolve(HEALTH)
    })

    const { result } = renderHook(() => useHealth())
    act(() => {
      result.current.refetch()
    })

    await waitFor(() => expect(result.current.data).toEqual(HEALTH))
    expect(signals[0]?.aborted).toBe(true)

    await act(async () => {
      first.resolve({ ...HEALTH, status: 'degraded' })
      await first.promise
    })
    expect(result.current.data).toEqual(HEALTH)
  })
})

describe('useHealth (edge cases)', () => {
  beforeEach(() => {
    getHealthMock.mockReset()
  })

  afterEach(() => {
    vi.restoreAllMocks()
  })

  it('refetch falla con ApiError tras un exito previo → data=null y error con el mensaje', async () => {
    getHealthMock.mockResolvedValueOnce(HEALTH)
    getHealthMock.mockRejectedValueOnce(new ApiError(503, 'Servicio no disponible'))

    const { result } = renderHook(() => useHealth())
    await waitFor(() => expect(result.current.data).toEqual(HEALTH))

    act(() => {
      result.current.refetch()
    })

    await waitFor(() => expect(result.current.isLoading).toBe(false))
    expect(result.current.data).toBeNull()
    expect(result.current.error).toEqual({ message: 'Servicio no disponible' })
  })

  it('ApiError que llega despues de desmontar → no se refleja y no hay warnings', async () => {
    const pending = deferred<Health>()
    getHealthMock.mockReturnValue(pending.promise)
    const consoleError = vi.spyOn(console, 'error').mockImplementation(() => {})

    const { result, unmount } = renderHook(() => useHealth())
    unmount()

    await act(async () => {
      pending.reject(new ApiError(500, 'tarde'))
      await pending.promise.catch(() => undefined)
    })

    expect(result.current.error).toBeNull()
    expect(result.current.isLoading).toBe(true)
    expect(consoleError).not.toHaveBeenCalled()
  })

  it('refetch invocado varias veces seguidas → solo la ultima respuesta se aplica', async () => {
    const first = deferred<Health>()
    const second = deferred<Health>()
    const latest: Health = { ...HEALTH, database: 'down', status: 'degraded' }
    getHealthMock
      .mockReturnValueOnce(first.promise)
      .mockReturnValueOnce(second.promise)
      .mockResolvedValueOnce(latest)

    const { result } = renderHook(() => useHealth())
    act(() => {
      result.current.refetch()
    })
    act(() => {
      result.current.refetch()
    })

    await waitFor(() => expect(result.current.data).toEqual(latest))

    await act(async () => {
      first.resolve(HEALTH)
      second.reject(new ApiError(500, 'obsoleto'))
      await Promise.allSettled([first.promise, second.promise])
    })

    expect(getHealthMock).toHaveBeenCalledTimes(3)
    expect(result.current.data).toEqual(latest)
    expect(result.current.error).toBeNull()
    expect(result.current.isLoading).toBe(false)
  })
})
