import { useEffect, useState } from 'react'
import { api } from '../api'
import { Chip, Empty, ErrorNote, Icon, KindChip, PageHeader, Spinner, Stat, StatusChip, timeAgo } from '../components'
import { useApp } from '../context'
import { ROLES, needsYou } from '../roles'
import type { Connection, Kind, Role, WorkItem } from '../types'

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
  switch (role) {
    case 'ams':
      return [
        { label: 'Open incidents', value: count(i => i.kind === 'incident' && i.status !== 'done') },
        { label: 'Needs you', value: mine, tone: mine ? 'warn' : undefined },
        { label: 'Errors', value: count(i => i.status === 'error'), tone: count(i => i.status === 'error') ? 'bad' : undefined },
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

function AdminHome() {
  const { models } = useApp()
  const [conns, setConns] = useState<Connection[]>([])
  const [sources, setSources] = useState<Record<string, number>>({})
  useEffect(() => {
    api.get<Connection[]>('/connections').then(setConns).catch(() => undefined)
    api.get<Record<string, number>>('/knowledge/sources').then(setSources).catch(() => undefined)
  }, [])
  const docs = Object.values(sources).reduce((a, b) => a + b, 0)
  const healthy = conns.filter(c => c.status === 'ok').length
  return (
    <>
      <div className="stats">
        <Stat value={models.filter(m => m.enabled).length} label="Models enabled" />
        <Stat value={`${healthy}/${conns.length}`} label="Connections healthy" tone={conns.length && healthy < conns.length ? 'warn' : undefined} />
        <Stat value={docs} label="Documents in knowledge base" />
        <Stat value={sources.studio ?? 0} label="Pages written by the studio" tone="ok" />
      </div>
      <div className="cards">
        <a className="card-link" href="#/models"><Icon name="chip" /><b>Models</b><span className="muted">Add a provider or change data levels</span></a>
        <a className="card-link" href="#/connections"><Icon name="plug" /><b>Connections</b><span className="muted">Jira, Confluence and SAP systems</span></a>
        <a className="card-link" href="#/knowledge"><Icon name="book" /><b>Knowledge</b><span className="muted">Search and refresh the index</span></a>
      </div>
      {conns.length === 0 && <div className="note">No connections yet, so demo data is used everywhere.</div>}
    </>
  )
}

export default function Home() {
  const { role } = useApp()
  const [items, setItems] = useState<WorkItem[] | null>(null)
  const [filter, setFilter] = useState<Kind | 'all'>('all')
  const [error, setError] = useState('')
  const [syncing, setSyncing] = useState(false)

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
  const header = (
    <PageHeader title={info.home} subtitle={SUBTITLES[role]} help="home"
      actions={role !== 'admin' && (
        <button className="btn" onClick={sync} disabled={syncing}>
          {syncing ? <Spinner /> : <Icon name="refresh" size={16} />}Sync
        </button>
      )} />
  )

  if (role === 'admin') return <div className="page">{header}<AdminHome /></div>
  if (!items) return <div className="page">{header}{error ? <ErrorNote message={error} onRetry={load} /> : <Spinner />}</div>

  const mine = needsYou(role, items)
  const shown = items.filter(i => filter === 'all' || i.kind === filter)
  const showNeedsYou = !['pm', 'functional'].includes(role)
  const byStage = ['intake', 'knowledge', 'impact', 'plan', 'build', 'document', 'publish']
    .map(s => ({ stage: s, n: items.filter(i => i.stage === s && i.status !== 'done').length }))

  return (
    <div className="page">
      {header}
      {error && <ErrorNote message={error} />}
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
          ? <Empty title="No items">Sync to pull tickets from Jira.</Empty>
          : <div className="list">{shown.map(i => <ItemRow key={i.key} item={i} />)}</div>}
      </section>
      {items.length > 0 && role === 'functional' && (
        <p className="muted small"><Chip>Read only</Chip> Open an item to follow its progress and read the plan.</p>
      )}
    </div>
  )
}
