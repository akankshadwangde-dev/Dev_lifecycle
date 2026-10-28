import { useEffect, useState, type FormEvent } from 'react'
import { api } from '../api'
import { Chip, Drawer, Empty, ErrorNote, Icon, KindChip, PageHeader, Spinner, Stat, StatusChip, timeAgo } from '../components'
import { useApp } from '../context'
import { KIND_LABELS, ROLES, needsYou } from '../roles'
import type { Kind, Project, Role, WorkItem } from '../types'

const SUBTITLES: Record<Role, string> = {
  developer: 'Items to start and code changes to approve.',
  ams: 'Incidents first. Many can be solved from the knowledge base.',
  lead: 'Plans and pages waiting for your approval.',
  architect: 'Designs for new objects waiting for review.',
  functional: 'Requirements and how they are progressing.',
  pm: 'Progress across the project. Read only.',
  admin: 'Models, connections and knowledge.',
}

function stats(role: Role, items: WorkItem[]) {
  const count = (f: (i: WorkItem) => boolean) => items.filter(f).length
  const mine = needsYou(role, items).length
  const done = count(i => i.status === 'done')
  const active = count(i => i.status === 'in_progress' || i.status === 'waiting')
  const errors = count(i => i.status === 'error')
  switch (role) {
    case 'ams':
      return [
        { label: 'Open incidents', value: count(i => i.kind === 'incident' && i.status !== 'done') },
        { label: 'Needs you', value: mine, tone: mine ? 'warn' : undefined },
        { label: 'Errors', value: errors, tone: errors ? 'bad' : undefined },
        { label: 'Done', value: done, tone: 'ok' },
      ]
    case 'lead':
      return [
        { label: 'Waiting for you', value: mine, tone: mine ? 'warn' : undefined },
        { label: 'Plans to approve', value: count(i => i.gate === 'plan') },
        { label: 'Pages to publish', value: count(i => i.gate === 'pages') },
        { label: 'Done', value: done, tone: 'ok' },
      ]
    case 'architect':
      return [
        { label: 'Designs to review', value: count(i => i.gate === 'plan' && i.kind === 'new'), tone: 'warn' },
        { label: 'New requirements', value: count(i => i.kind === 'new') },
        { label: 'In progress', value: active },
        { label: 'Done', value: done, tone: 'ok' },
      ]
    case 'functional':
    case 'pm':
      return [
        { label: 'All items', value: items.length },
        { label: 'In progress', value: active },
        { label: 'Not started', value: count(i => i.status === 'open') },
        { label: 'Done', value: done, tone: 'ok' },
      ]
    default:
      return [
        { label: 'Needs you', value: mine, tone: mine ? 'warn' : undefined },
        { label: 'In progress', value: active },
        { label: 'Waiting on others', value: count(i => i.status === 'waiting' && !i.can_act) },
        { label: 'Done', value: done, tone: 'ok' },
      ]
  }
}

function nextStep(role: Role, item: WorkItem): string {
  if (item.status === 'error') return 'Stopped with an error'
  if (item.can_act) return { recommendation: 'Review the recommendation', plan: 'Review the plan', change: 'Review the code change', pages: 'Review the pages' }[item.gate as string] ?? 'Decide'
  if (item.status === 'open' && ROLES[role].startsKinds.includes(item.kind)) return 'Start analysis'
  return ''
}

function ItemRow({ item, showNext }: { item: WorkItem; showNext?: string }) {
  return (
    <a className="item-row" href={`#/item/${encodeURIComponent(item.key)}`}>
      <span className="key">{item.key}</span>
      <span className="item-title">{item.title}</span>
      {showNext ? <span className="next">{showNext}</span> : <span />}
      <KindChip kind={item.kind} />
      <StatusChip item={item} />
      <span className="muted small nowrap">{timeAgo(item.updated)}</span>
    </a>
  )
}

/** Shown until the essentials are set up. */
function SetupChecklist({ project, role }: { project: Project; role: Role }) {
  const s = project.setup
  const steps = [
    { done: s.model, what: 'Add an AI model', where: '#/settings/models', go: 'Models' },
    { done: s.jira || s.items > 0, what: 'Connect Jira, or add an item by hand', where: '#/settings/connections', go: 'Connections' },
    { done: s.confluence, what: 'Connect Confluence so recommendations use your documentation', where: '#/settings/connections', go: 'Connections' },
    { done: s.sap || project.sap_release != null || project.sap_cloud, what: 'Connect your SAP system, or set the target release', where: s.sap ? '#/settings/connections' : '#/settings/general', go: 'Settings' },
  ]
  if (steps.every(x => x.done)) return null
  return (
    <section className="setup" aria-label="Set up">
      <div className="row between wrap">
        <h2>Set up the studio</h2>
        {role !== 'admin' && <span className="small muted">Settings are changed with the Admin role.</span>}
      </div>
      <ol>
        {steps.map(x => (
          <li key={x.what} className={x.done ? 'done' : ''}>
            <span className="tick">{x.done && <Icon name="check" size={12} />}</span>
            <span className="what">{x.what}</span>
            {!x.done && <a href={x.where} className="small">{x.go}</a>}
          </li>
        ))}
      </ol>
    </section>
  )
}

function NewItemDrawer({ open, onClose }: { open: boolean; onClose: () => void }) {
  const { navigate, reloadProject } = useApp()
  const [kind, setKind] = useState<Kind>('change')
  const [title, setTitle] = useState('')
  const [description, setDescription] = useState('')
  const [priority, setPriority] = useState('')
  const [key, setKey] = useState('')
  const [error, setError] = useState('')
  const [saving, setSaving] = useState(false)

  const save = async (e: FormEvent) => {
    e.preventDefault()
    setSaving(true)
    setError('')
    try {
      const res = await api.post<{ item: WorkItem }>('/work-items', { kind, title, description, priority, key })
      reloadProject()
      navigate(`#/item/${encodeURIComponent(res.item.key)}`)
    } catch (err) {
      setError((err as Error).message)
    } finally {
      setSaving(false)
    }
  }

  return (
    <Drawer open={open} title="New item" onClose={onClose}>
      <form className="form" onSubmit={save}>
        <fieldset>
          <legend>Type</legend>
          <div className="kind-pick">
            {(['incident', 'change', 'new'] as Kind[]).map(k => (
              <button type="button" key={k} className={kind === k ? 'on' : ''} onClick={() => setKind(k)}>{KIND_LABELS[k]}</button>
            ))}
          </div>
        </fieldset>
        <label>Title<input required value={title} onChange={e => setTitle(e.target.value)} placeholder="Short summary" /></label>
        <label>Description
          <textarea rows={7} value={description} onChange={e => setDescription(e.target.value)}
            placeholder="What is needed or what goes wrong. Mention objects (e.g. ZCL_…), transactions and acceptance criteria." />
        </label>
        <div className="row">
          <label className="grow">Priority<input value={priority} onChange={e => setPriority(e.target.value)} placeholder="e.g. P2" /></label>
          <label className="grow">Key<input value={key} onChange={e => setKey(e.target.value)} placeholder="Automatic" /></label>
        </div>
        {error && <ErrorNote message={error} />}
        <div className="row">
          <button className="btn btn-primary" type="submit" disabled={saving}>{saving ? 'Adding…' : 'Add item'}</button>
          <button className="btn" type="button" onClick={onClose}>Cancel</button>
        </div>
      </form>
    </Drawer>
  )
}

function AdminHome() {
  const { models, project } = useApp()
  const [sources, setSources] = useState<Record<string, number>>({})
  useEffect(() => {
    api.get<Record<string, number>>('/knowledge/sources').then(setSources).catch(() => undefined)
  }, [])
  const docs = Object.values(sources).reduce((a, b) => a + b, 0)
  const s = project?.setup
  const connected = s ? [s.jira, s.confluence, s.sap].filter(Boolean).length : 0
  return (
    <>
      <div className="stats">
        <Stat value={models.filter(m => m.enabled).length} label="AI models enabled" />
        <Stat value={`${connected}/3`} label="Jira, Confluence, SAP connected" />
        <Stat value={docs} label="Documents in knowledge base" />
        <Stat value={sources.studio ?? 0} label="Pages written by the studio" tone="ok" />
      </div>
      <div className="cards">
        <a className="card-link" href="#/settings/models"><Icon name="chip" /><b>AI models</b><span className="muted">Add a provider or change data levels</span></a>
        <a className="card-link" href="#/settings/connections"><Icon name="plug" /><b>Connections</b><span className="muted">Jira, Confluence and SAP systems</span></a>
        <a className="card-link" href="#/settings/general"><Icon name="gear" /><b>General</b><span className="muted">Project name, SAP release, sample data</span></a>
      </div>
    </>
  )
}

export default function Home() {
  const { role, project } = useApp()
  const [items, setItems] = useState<WorkItem[] | null>(null)
  const [filter, setFilter] = useState<Kind | 'all'>('all')
  const [error, setError] = useState('')
  const [syncing, setSyncing] = useState(false)
  const [adding, setAdding] = useState(false)

  const load = () => api.get<WorkItem[]>('/work-items').then(setItems).catch(e => setError(e.message))
  useEffect(() => { load() }, [])

  const sync = async () => {
    setSyncing(true)
    setError('')
    try {
      await api.post('/work-items/sync')
      await load()
    } catch (e) {
      setError((e as Error).message)
    } finally {
      setSyncing(false)
    }
  }

  const info = ROLES[role]
  const canSync = !!project && (project.setup.jira || project.sample_data)
  const header = (
    <PageHeader title={info.home} subtitle={SUBTITLES[role]} help="home"
      actions={role !== 'admin' && (
        <>
          {canSync && <button className="btn" onClick={sync} disabled={syncing}>{syncing ? <Spinner /> : <Icon name="refresh" size={16} />}Sync from Jira</button>}
          {info.canCreate && <button className="btn btn-primary" onClick={() => setAdding(true)}><Icon name="plus" size={16} />New item</button>}
        </>
      )} />
  )
  const checklist = project && <SetupChecklist project={project} role={role} />

  if (role === 'admin') return <div className="page">{header}{checklist}<AdminHome /></div>
  if (!items) return <div className="page">{header}{error ? <ErrorNote message={error} onRetry={load} /> : <Spinner />}</div>

  const mine = needsYou(role, items)
  const shown = items.filter(i => filter === 'all' || i.kind === filter)
  const showNeedsYou = !['pm', 'functional'].includes(role) && items.length > 0
  const byStage = ['intake', 'knowledge', 'impact', 'plan', 'build', 'document', 'publish']
    .map(s => ({ stage: s, n: items.filter(i => i.stage === s && i.status !== 'done').length }))

  return (
    <div className="page">
      {header}
      {error && <ErrorNote message={error} />}
      {checklist}

      {items.length === 0 ? (
        <Empty title="No items yet">
          {info.canCreate ? 'Add an item with New item' : 'Items appear here once someone adds them'}{project?.setup.jira ? ', or sync from Jira.' : '.'}
        </Empty>
      ) : (
        <>
          <div className="stats">
            {stats(role, items).map(s => <Stat key={s.label} value={s.value} label={s.label} tone={s.tone as never} />)}
          </div>

          {showNeedsYou && (
            <section className="section">
              <h2>Needs you</h2>
              {mine.length === 0
                ? <Empty title="Nothing waiting for you">New items appear here when you can start or decide.</Empty>
                : <div className="list">{mine.map(i => <ItemRow key={i.key} item={i} showNext={nextStep(role, i)} />)}</div>}
            </section>
          )}

          {role === 'pm' && (
            <section className="section">
              <h2>Open items by step</h2>
              <div className="stage-bars">
                {byStage.map(({ stage, n }) => (
                  <div key={stage} className="stage-bar">
                    <span className="cap">{stage}</span>
                    <div className="bar"><div style={{ width: `${items.length ? (n / items.length) * 100 : 0}%` }} /></div>
                    <b>{n}</b>
                  </div>
                ))}
              </div>
            </section>
          )}

          <section className="section">
            <div className="section-head">
              <h2>All work</h2>
              <div className="filters" role="group" aria-label="Filter by type">
                {(['all', 'incident', 'change', 'new'] as const).map(k => (
                  <button key={k} className={filter === k ? 'on' : ''} onClick={() => setFilter(k)}>
                    {k === 'all' ? 'All' : k === 'incident' ? 'Incidents' : k === 'change' ? 'Changes' : 'New'}
                  </button>
                ))}
              </div>
            </div>
            {shown.length === 0
              ? <Empty title="No items of this type" />
              : <div className="list">{shown.map(i => <ItemRow key={i.key} item={i} />)}</div>}
          </section>
          {role === 'functional' && <p className="muted small"><Chip>Read only</Chip> Open an item to follow its progress and read the plan.</p>}
        </>
      )}
      <NewItemDrawer open={adding} onClose={() => setAdding(false)} />
    </div>
  )
}
