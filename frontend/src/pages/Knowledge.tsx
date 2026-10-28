import { useEffect, useState, type FormEvent } from 'react'
import { api } from '../api'
import { Chip, Empty, ErrorNote, Icon, PageHeader, Spinner } from '../components'
import { useApp } from '../context'
import type { Source } from '../types'

const LABELS: Record<string, string> = { confluence: 'Confluence', ticket: 'Past tickets', studio: 'Written by the studio' }

export default function KnowledgePage() {
  const { role } = useApp()
  const [counts, setCounts] = useState<Record<string, number>>({})
  const [query, setQuery] = useState('')
  const [hits, setHits] = useState<Source[] | null>(null)
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState('')

  const loadCounts = () => api.get<Record<string, number>>('/knowledge/sources').then(setCounts).catch(e => setError(e.message))
  useEffect(() => { loadCounts() }, [])

  const search = async (e: FormEvent) => {
    e.preventDefault()
    if (!query.trim()) return
    setError('')
    try {
      setHits(await api.get<Source[]>(`/knowledge/search?q=${encodeURIComponent(query)}`))
    } catch (err) {
      setError((err as Error).message)
    }
  }

  const refresh = async () => {
    setBusy(true)
    setError('')
    try {
      await api.post('/knowledge/reindex')
      await loadCounts()
    } catch (err) {
      setError((err as Error).message)
    } finally {
      setBusy(false)
    }
  }

  return (
    <div className="page">
      <PageHeader title="Knowledge" subtitle="What the AI searches before it recommends anything." help="knowledge"
        actions={role === 'admin' && <button className="btn" onClick={refresh} disabled={busy}>{busy ? <Spinner /> : <Icon name="refresh" size={16} />}Refresh</button>} />
      {error && <ErrorNote message={error} />}
      <div className="row wrap">
        {Object.entries(LABELS).map(([k, label]) => <Chip key={k} tone={k === 'studio' ? 'ok' : 'neutral'}>{label}: {counts[k] ?? 0}</Chip>)}
      </div>
      <form className="search" onSubmit={search}>
        <Icon name="search" />
        <input value={query} onChange={e => setQuery(e.target.value)} placeholder="Search, e.g. shipping condition IDoc" aria-label="Search the knowledge base" />
        <button className="btn btn-primary" type="submit">Search</button>
      </form>
      {hits && (hits.length === 0
        ? <Empty title="No matches">Try other words, or an object name such as ZCL_SD_SHIP_COND.</Empty>
        : (
          <ul className="results">
            {hits.map(h => (
              <li key={h.ref}>
                <div className="row between">
                  <span className="small muted">{LABELS[h.source] ?? h.source} · {h.ref}</span>
                  <span className="small muted">{h.score}% match</span>
                </div>
                {h.url ? <a href={h.url} target="_blank" rel="noreferrer"><b>{h.title}</b></a> : <b>{h.title}</b>}
                <p className="muted small">{h.excerpt}</p>
              </li>
            ))}
          </ul>
        ))}
    </div>
  )
}
