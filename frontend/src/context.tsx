import { createContext, useContext } from 'react'
import type { ModelConfig, Project, Role } from './types'

export interface AppContext {
  role: Role
  user: string
  models: ModelConfig[]
  project: Project | null
  openHelp: (topic: string) => void
  navigate: (hash: string) => void
  reloadModels: () => void
  reloadProject: () => void
}

export const Ctx = createContext<AppContext | null>(null)

export function useApp(): AppContext {
  const ctx = useContext(Ctx)
  if (!ctx) throw new Error('useApp outside provider')
  return ctx
}
