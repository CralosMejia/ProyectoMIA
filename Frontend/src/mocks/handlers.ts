import type { RequestHandler } from 'msw'

interface HandlersModule {
  handlers?: RequestHandler[]
}

/**
 * Autodescubrimiento: cada feature declara sus handlers en
 * `features/<feature>/api/*.handlers.ts` exportando `handlers`.
 */
const modules = import.meta.glob<HandlersModule>('../features/*/api/*.handlers.ts', {
  eager: true,
})

export function collectHandlers(found: Record<string, HandlersModule>): RequestHandler[] {
  return Object.keys(found)
    .sort()
    .flatMap((key) => found[key]?.handlers ?? [])
}

export const handlers: RequestHandler[] = collectHandlers(modules)
