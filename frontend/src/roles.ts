import type { Action, GateName, Kind, Role, WorkItem } from './types'

export type PageKey = 'home' | 'knowledge' | 'audit' | 'settings'

interface RoleInfo {
  label: string
  home: string
  nav: PageKey[]
  startsKinds: Kind[] // kinds this role starts analysing
  viewCode: boolean
  canCreate: boolean // can add items by hand
}

export const ROLES: Record<Role, RoleInfo> = {
  developer: { label: 'Developer', home: 'My work', nav: ['home', 'knowledge', 'audit', 'settings'], startsKinds: ['new', 'change'], viewCode: true, canCreate: true },
  ams: { label: 'AMS consultant', home: 'Incident desk', nav: ['home', 'knowledge', 'audit', 'settings'], startsKinds: ['incident'], viewCode: true, canCreate: true },
  lead: { label: 'Tech lead', home: 'Approvals', nav: ['home', 'knowledge', 'audit', 'settings'], startsKinds: ['new', 'change', 'incident'], viewCode: true, canCreate: true },
  architect: { label: 'Solution architect', home: 'Design reviews', nav: ['home', 'knowledge', 'audit', 'settings'], startsKinds: ['new'], viewCode: true, canCreate: true },
  functional: { label: 'Functional consultant', home: 'Requirements', nav: ['home', 'knowledge', 'settings'], startsKinds: [], viewCode: false, canCreate: true },
  pm: { label: 'Project manager', home: 'Delivery overview', nav: ['home', 'audit', 'settings'], startsKinds: [], viewCode: false, canCreate: false },
  admin: { label: 'Admin', home: 'Platform', nav: ['home', 'knowledge', 'audit', 'settings'], startsKinds: [], viewCode: false, canCreate: false },
}

export const PAGE_LABELS: Record<PageKey, string> = {
  home: 'Home',
  knowledge: 'Knowledge',
  audit: 'Audit trail',
  settings: 'Settings',
}

export const KIND_LABELS: Record<Kind, string> = { new: 'New requirement', change: 'Change', incident: 'Incident' }

export const GATE_LABELS: Record<GateName, string> = {
  recommendation: 'Accept recommendation',
  plan: 'Approve plan',
  change: 'Approve change',
  pages: 'Publish pages',
}

export function actionLabel(role: Role, gate: GateName, action: Action): string {
  if (action === 'revise') return 'Request changes'
  if (action === 'no_code') return 'Resolve without code'
  if (gate === 'recommendation') return role === 'ams' ? 'Hand off to developer' : 'Accept'
  if (gate === 'plan') return role === 'architect' ? 'Approve design' : 'Approve plan'
  if (gate === 'change') return 'Approve change'
  return 'Publish'
}

/** Items that need this role's attention right now. */
export function needsYou(role: Role, items: WorkItem[]): WorkItem[] {
  const startable = ROLES[role].startsKinds
  return items.filter(i => i.can_act || (i.status === 'open' && startable.includes(i.kind)) || i.status === 'error')
}
