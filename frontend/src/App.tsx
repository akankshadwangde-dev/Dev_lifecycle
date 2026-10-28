import { useCallback, useEffect, useMemo, useState } from 'react'
import { api, setIdentity } from './api'
import { Drawer, Icon } from './components'
import { Ctx, type AppContext } from './context'
import { HELP } from './help'
import { PAGE_LABELS, ROLES, type PageKey } from './roles'
import type { ModelConfig, Project, Role } from './types'
import Home from './pages/Home'
import ItemPage from './pages/Item'
import KnowledgePage from './pages/Knowledge'
import SettingsPage, { type SettingsTab } from './pages/Settings'
import AuditPage from './pages/Audit'

const NAV_ICONS: Record<PageKey, string> = { home: 'home', knowledge: 'book', audit: 'list', settings: 'gear' }
const SETTINGS_TABS: SettingsTab[] = ['general', 'models', 'connections']

function readStored<T>(key: string, fallback: T): T {
  try {
    const raw = localStorage.getItem(key)
    return raw ? (JSON.parse(raw) as T) : fallback
  } catch {
    return fallback
  }
}

function store(key: string, value: unknown) {
  try {
    localStorage.setItem(key, JSON.stringify(value))
  } catch {
    /* storage unavailable: settings last for this visit only */
  }
}

type Route = { page: PageKey | 'item'; key?: string; tab?: SettingsTab }

function parseHash(hash: string): Route {
  const [, page, sub] = hash.replace(/^#/, '').split('/')
  if (page === 'item' && sub) return { page: 'item', key: decodeURIComponent(sub) }
  if (page === 'settings') return { page: 'settings', tab: SETTINGS_TABS.includes(sub as SettingsTab) ? (sub as SettingsTab) : 'general' }
  if (page && page in PAGE_LABELS) return { page: page as PageKey }
  return { page: 'home' }
}

export default function App() {
  const [role, setRole] = useState<Role>(() => readStored('studio.role', 'developer'))
  const [user, setUser] = useState<string>(() => readStored('studio.user', 'demo.user'))
  const [modelId, setModelId] = useState<number | null>(() => readStored('studio.model', null))
  const [models, setModels] = useState<ModelConfig[]>([])
  const [project, setProject] = useState<Project | null>(null)
  const [route, setRoute] = useState(() => parseHash(window.location.hash))
  const [helpTopic, setHelpTopic] = useState<string | null>(null)
  const [ready, setReady] = useState(false)
  const [offline, setOffline] = useState(false)

  setIdentity({ user, role, modelId })

  useEffect(() => {
    const onHash = () => setRoute(parseHash(window.location.hash))
    window.addEventListener('hashchange', onHash)
    return () => window.removeEventListener('hashchange', onHash)
  }, [])

  const reloadModels = useCallback(() => {
    api.get<ModelConfig[]>('/models').then(setModels).catch(() => setModels([]))
  }, [])
  const reloadProject = useCallback(() => {
    api.get<Project>('/project').then(p => { setProject(p); setOffline(false) }).catch(() => setOffline(true)).finally(() => setReady(true))
  }, [])

  useEffect(() => {
    reloadProject()
    reloadModels()
  }, [reloadModels, reloadProject])

  // A role without access to the current page lands on its home screen.
  useEffect(() => {
    if (route.page !== 'item' && !ROLES[role].nav.includes(route.page)) window.location.hash = '#/home'
  }, [role, route.page])

  // Forget a chosen model that no longer exists.
  useEffect(() => {
    if (modelId != null && models.length && !models.some(m => m.id === modelId && m.enabled)) {
      setModelId(null)
      store('studio.model', null)
    }
  }, [models, modelId])

  const changeRole = (next: Role) => {
    setRole(next)
    store('studio.role', next)
    if (route.page !== 'settings') window.location.hash = '#/home'
  }
  const changeModel = (value: string) => {
    const id = value ? Number(value) : null
    setModelId(id)
    store('studio.model', id)
  }

  const ctx: AppContext = useMemo(() => ({
    role, user, models, project, reloadModels, reloadProject,
    openHelp: (topic: string) => setHelpTopic(topic),
    navigate: (hash: string) => { window.location.hash = hash },
  }), [role, user, models, project, reloadModels, reloadProject])

  const enabledModels = models.filter(m => m.enabled)
  const helpKey = helpTopic && HELP[helpTopic] ? helpTopic : 'start'
  const help = HELP[helpKey]
  const pageHelp = route.page === 'item' ? 'item' : route.page

  return (
    <Ctx.Provider value={ctx}>
      <div className="shell">
        <header className="topbar">
          <a className="brand" href="#/home"><span className="brand-mark">AB</span>Lifecycle Studio</a>
          {project && <span className="project-name">{project.name}</span>}
          {project?.sample_data && <a className="chip chip-warn" href="#/settings/general" title="Sample tickets, pages and code are shown. Turn off under Settings.">Sample data</a>}
          <div className="topbar-controls">
            <label className="select-label">
              <span>Model</span>
              <select value={modelId ?? ''} onChange={e => changeModel(e.target.value)} aria-label="Model">
                <option value="">{enabledModels.length ? 'Auto' : 'None set up'}</option>
                {enabledModels.map(m => <option key={m.id} value={m.id}>{m.name}</option>)}
              </select>
            </label>
            <label className="select-label">
              <span>Role</span>
              <select value={role} onChange={e => changeRole(e.target.value as Role)} aria-label="Role">
                {(Object.keys(ROLES) as Role[]).map(r => <option key={r} value={r}>{ROLES[r].label}</option>)}
              </select>
            </label>
            <input className="user-input" value={user} aria-label="Your name"
              onChange={e => { setUser(e.target.value); store('studio.user', e.target.value) }} />
            <button className="icon-btn" onClick={() => setHelpTopic(pageHelp)} aria-label="Help" title="Help">
              <Icon name="help" />
            </button>
          </div>
        </header>

        <nav className="sidenav" aria-label="Main">
          {ROLES[role].nav.map(page => (
            <a key={page} href={`#/${page}`} className={route.page === page || (page === 'home' && route.page === 'item') ? 'active' : ''}>
              <Icon name={NAV_ICONS[page]} />
              <span>{page === 'home' ? ROLES[role].home : PAGE_LABELS[page]}</span>
            </a>
          ))}
          <button className="sidenav-help" onClick={() => setHelpTopic('start')}>
            <Icon name="help" /><span>How it works</span>
          </button>
        </nav>

        <main className="content">
          {!ready ? null
            : offline ? (
              <div className="page"><div className="note note-bad">The server is not reachable. Start the backend (start-dev.cmd) and refresh this page.</div></div>
            )
            : route.page === 'item' && route.key ? <ItemPage key={`${route.key}-${role}`} itemKey={route.key} />
            : route.page === 'knowledge' ? <KnowledgePage />
            : route.page === 'settings' ? <SettingsPage tab={route.tab ?? 'general'} />
            : route.page === 'audit' ? <AuditPage />
            : <Home key={role} />}
        </main>
      </div>

      <Drawer open={helpTopic !== null} title={help.title} onClose={() => setHelpTopic(null)}>
        <p className="help-intro">{help.intro}</p>
        {help.sections.map(s => (
          <section key={s.heading} className="help-section">
            <h3>{s.heading}</h3>
            <ul>{s.body.map(line => <li key={line}>{line}</li>)}</ul>
          </section>
        ))}
        <div className="help-topics">
          <span className="eyebrow">Other topics</span>
          {Object.entries(HELP).filter(([k]) => k !== helpKey).map(([k, t]) => (
            <button key={k} className="link-btn" onClick={() => setHelpTopic(k)}>{t.title}</button>
          ))}
        </div>
      </Drawer>
    </Ctx.Provider>
  )
}
