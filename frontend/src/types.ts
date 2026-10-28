export type Role = 'developer' | 'ams' | 'lead' | 'architect' | 'functional' | 'pm' | 'admin'
export type Kind = 'new' | 'change' | 'incident'
export type GateName = 'recommendation' | 'plan' | 'change' | 'pages'
export type Action = 'approve' | 'revise' | 'no_code'

export interface WorkItem {
  id: number
  key: string
  title: string
  description: string
  kind: Kind
  priority: string
  source: string
  assignee: string
  objects: string[]
  stage: string
  gate: GateName | ''
  status: 'open' | 'in_progress' | 'waiting' | 'done' | 'error'
  error: string
  updated: string
  can_act?: boolean
}

export interface Source {
  source: 'confluence' | 'ticket' | 'studio' | 'sap'
  ref: string
  title: string
  excerpt: string
  url: string
  updated: string
  score: number | null
  used: boolean
}

export interface Knowledge {
  cause: string
  confidence: 'high' | 'medium' | 'low'
  needs_code: boolean
  estimate: string
  steps: string[]
  avoid: string
  sources: Source[]
  model: string
}

export interface ImpactObject {
  name: string
  callers: { name: string; type: string; description: string }[]
  transports: { id: string; owner: string; text: string }[]
  tests: string[]
}

export interface Impact {
  objects: ImpactObject[]
  risk: 'low' | 'medium' | 'high'
  summary: string
  notes: string[]
  model: string
}

export interface PlanItem {
  action: 'modify' | 'new' | 'config' | 'docs'
  object: string
  type: string
  change: string
  basis: string
  estimate_h: number
}

export interface DiffLine { t: '+' | '-' | ' ' | '@'; text: string }

export interface BuiltObject {
  name: string
  is_new: boolean
  before: string
  after: string
  diff: DiffLine[]
  added: number
  removed: number
  notes: string[]
}

export interface Build {
  objects: BuiltObject[]
  target: { basis_release: number | null; syntax: string; profile: { key: string; label: string } }
  model: string
}

export interface PageSection { heading: string; body: string | string[] }
export interface DraftPage {
  mode: 'create' | 'update'
  space: string
  parent: string
  title: string
  labels: string[]
  sections: PageSection[]
}

export interface Outputs {
  intake?: { kind: Kind; objects: string[]; priority: string; source: string }
  knowledge?: Knowledge
  impact?: Impact
  plan?: { items: PlanItem[]; total_h: number; model: string }
  build?: Build
  document?: { pages: DraftPage[]; model: string }
  publish?: { pages: { title: string; space: string; ref: string; url: string; simulated?: boolean; updated?: boolean }[] }
}

export interface Decision { gate: GateName; action: Action; comment: string; user: string; role: Role }

export interface Flow {
  started: boolean
  stage?: string
  resolution?: 'code' | 'no_code' | ''
  outputs?: Outputs
  history?: Decision[]
  gate?: { name: GateName; actions: { action: Action; allowed: boolean }[]; waiting_for: string[] } | null
  done?: boolean
  error?: string | null
}

export interface ModelConfig {
  id: number
  name: string
  provider: string
  model: string
  api_base: string
  secret_ref: string
  data_level: 'public' | 'code' | 'production'
  stages: string[]
  enabled: boolean
  priority: number
}

export interface Provider { label: string; prefix: string | null; needs_base: boolean; example: string }

export interface Connection {
  id: number
  kind: string
  name: string
  base_url: string
  auth: 'basic' | 'bearer'
  username: string
  secret_ref: string
  options: Record<string, unknown>
  enabled: boolean
  status: 'untested' | 'ok' | 'error'
  detail: string
}

export interface AuditEntry {
  id: number
  ts: string
  user: string
  role: Role
  action: string
  item_key: string
  detail: string
  model: string
}
