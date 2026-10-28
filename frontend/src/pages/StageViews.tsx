import { useState } from 'react'
import { Chip, Icon } from '../components'
import { useApp } from '../context'
import { ROLES } from '../roles'
import type { BuiltObject, Flow, Outputs, Source, WorkItem } from '../types'

const SOURCE_LABELS: Record<Source['source'], string> = {
  confluence: 'Confluence', ticket: 'Past ticket', studio: 'Studio page', sap: 'SAP code',
}
const TONE = { high: 'ok', medium: 'warn', low: 'bad' } as const
const RISK_TONE = { low: 'ok', medium: 'warn', high: 'bad' } as const

function ModelNote({ model }: { model?: string }) {
  return model ? <p className="muted small">Prepared by {model}</p> : null
}

export function IntakeView({ item, out }: { item: WorkItem; out: Outputs }) {
  const objects = out.intake?.objects ?? item.objects
  return (
    <div className="stack">
      <p className="lead-text">{item.description || 'No description.'}</p>
      <dl className="facts">
        <dt>Source</dt><dd>{item.source}</dd>
        <dt>Priority</dt><dd>{item.priority || '—'}</dd>
        <dt>Assignee</dt><dd>{item.assignee || '—'}</dd>
        <dt>Objects</dt>
        <dd className="row wrap">{objects.length ? objects.map(o => <code key={o} className="tag">{o}</code>) : '—'}</dd>
      </dl>
    </div>
  )
}

export function KnowledgeView({ out }: { out: Outputs }) {
  const k = out.knowledge
  if (!k) return null
  return (
    <div className="split">
      <div className="stack">
        <div className="row wrap">
          <Chip tone={TONE[k.confidence]}>Confidence: {k.confidence}</Chip>
          <Chip tone={k.needs_code ? 'accent' : 'ok'}>{k.needs_code ? 'Code change needed' : 'No code change needed'}</Chip>
          {k.estimate && <Chip>Estimate: {k.estimate}</Chip>}
        </div>
        <div>
          <h3>Likely cause</h3>
          <p>{k.cause}</p>
        </div>
        <div>
          <h3>Recommended steps</h3>
          <ol className="steps">{k.steps.map(s => <li key={s}>{s}</li>)}</ol>
        </div>
        {k.avoid && <div className="note note-warn"><b>Avoid:</b> {k.avoid}</div>}
        <ModelNote model={k.model} />
      </div>
      <aside className="panel">
        <h3>Sources</h3>
        {k.sources.length === 0 && <p className="muted">No sources found.</p>}
        <ul className="sources">
          {k.sources.map(s => (
            <li key={s.ref} className={s.used ? '' : 'unused'}>
              <div className="row between">
                <span className="small muted">{SOURCE_LABELS[s.source]}</span>
                {s.used ? <Chip tone="accent">Used</Chip> : s.score != null && <span className="small muted">{s.score}% match</span>}
              </div>
              {s.url ? <a href={s.url} target="_blank" rel="noreferrer">{s.title}</a> : <b>{s.title}</b>}
              {s.updated && <span className="small muted">Updated {s.updated}</span>}
            </li>
          ))}
        </ul>
      </aside>
    </div>
  )
}

export function ImpactView({ out }: { out: Outputs }) {
  const im = out.impact
  if (!im) return null
  const transports = im.objects.flatMap(o => o.transports.map(t => ({ ...t, object: o.name })))
  return (
    <div className="stack">
      <div className="row wrap">
        <Chip tone={RISK_TONE[im.risk]}>Risk: {im.risk}</Chip>
        <Chip>{im.objects.reduce((n, o) => n + o.callers.length, 0)} callers</Chip>
        <Chip>{im.objects.reduce((n, o) => n + o.tests.length, 0)} existing unit tests</Chip>
      </div>
      <p>{im.summary}</p>
      {transports.map(t => (
        <div key={t.id} className="note note-warn">
          Open transport <code>{t.id}</code> ({t.owner}) also changes {t.object}: {t.text}
        </div>
      ))}
      {im.objects.map(o => (
        <div key={o.name}>
          <h3><code>{o.name}</code> is used by</h3>
          {o.callers.length === 0 ? <p className="muted">No callers found.</p> : (
            <div className="table-wrap">
              <table>
                <thead><tr><th>Object</th><th>Type</th><th>Where</th></tr></thead>
                <tbody>{o.callers.map(c => <tr key={c.name}><td><code>{c.name}</code></td><td>{c.type}</td><td>{c.description}</td></tr>)}</tbody>
              </table>
            </div>
          )}
        </div>
      ))}
      {im.notes.length > 0 && <ul className="plain-list">{im.notes.map(n => <li key={n}>{n}</li>)}</ul>}
      <ModelNote model={im.model} />
    </div>
  )
}

const ACTION_TONE = { modify: 'warn', new: 'ok', config: 'neutral', docs: 'accent' } as const

export function PlanView({ out, kind }: { out: Outputs; kind: WorkItem['kind'] }) {
  const p = out.plan
  if (!p) return null
  return (
    <div className="stack">
      <div className="table-wrap">
        <table>
          <thead><tr><th>Action</th><th>{kind === 'new' ? 'RICEFW' : 'Type'}</th><th>Object</th><th>What changes</th><th>Based on</th><th className="num">Hours</th></tr></thead>
          <tbody>
            {p.items.map((i, n) => (
              <tr key={n}>
                <td><Chip tone={ACTION_TONE[i.action] ?? 'neutral'}>{i.action}</Chip></td>
                <td><span className="type-badge">{i.type}</span></td>
                <td><code>{i.object}</code></td>
                <td>{i.change}</td>
                <td className="muted">{i.basis}</td>
                <td className="num">{i.estimate_h}</td>
              </tr>
            ))}
          </tbody>
          <tfoot><tr><td colSpan={5}>Total</td><td className="num"><b>{p.total_h} h</b></td></tr></tfoot>
        </table>
      </div>
      <ModelNote model={p.model} />
    </div>
  )
}

function download(name: string, text: string) {
  const url = URL.createObjectURL(new Blob([text], { type: 'text/plain' }))
  const a = document.createElement('a')
  a.href = url
  a.download = `${name.toLowerCase()}.abap`
  a.click()
  URL.revokeObjectURL(url)
}

function CodeObject({ obj }: { obj: BuiltObject }) {
  const [full, setFull] = useState(obj.is_new)
  const [copied, setCopied] = useState(false)
  const copy = async () => {
    await navigator.clipboard.writeText(obj.after)
    setCopied(true)
    setTimeout(() => setCopied(false), 1500)
  }
  return (
    <div className="code-block">
      <div className="code-head">
        <code>{obj.name}</code>
        {obj.is_new ? <Chip tone="ok">New</Chip> : <span className="small"><span className="add">+{obj.added}</span> <span className="del">−{obj.removed}</span></span>}
        <div className="row push">
          {!obj.is_new && (
            <div className="filters small-filters">
              <button className={!full ? 'on' : ''} onClick={() => setFull(false)}>Changes</button>
              <button className={full ? 'on' : ''} onClick={() => setFull(true)}>Full source</button>
            </div>
          )}
          <button className="btn btn-sm" onClick={copy}><Icon name={copied ? 'check' : 'copy'} size={14} />{copied ? 'Copied' : 'Copy'}</button>
          <button className="btn btn-sm" onClick={() => download(obj.name, obj.after)}><Icon name="download" size={14} />Download</button>
        </div>
      </div>
      <pre className="code">
        {full
          ? obj.after
          : obj.diff.map((l, n) => <span key={n} className={`ln ln-${l.t === '+' ? 'add' : l.t === '-' ? 'del' : l.t === '@' ? 'hunk' : 'ctx'}`}>{l.t === '@' ? l.text : `${l.t} ${l.text}`}{'\n'}</span>)}
      </pre>
      {obj.notes.length > 0 && <ul className="plain-list small">{obj.notes.map(n => <li key={n}>{n}</li>)}</ul>}
    </div>
  )
}

export function BuildView({ out }: { out: Outputs }) {
  const { role } = useApp()
  const b = out.build
  if (!b) return null
  return (
    <div className="stack">
      <div className="row wrap">
        <Chip>SAP_BASIS {b.target.basis_release ?? 'unknown'}</Chip>
        <Chip tone="accent">{b.target.profile.label} profile</Chip>
        <Chip>Syntax {b.target.syntax}</Chip>
      </div>
      {!ROLES[role].viewCode
        ? <div className="note">Code is hidden for your role. {b.objects.length} object(s) changed.</div>
        : b.objects.length === 0
          ? <div className="note">No code was generated for this plan.</div>
          : b.objects.map(o => <CodeObject key={o.name} obj={o} />)}
      <div className="note">Deploy to SAP, ATC review and unit test runs arrive in Phase 2. For now, copy the source into ADT or SE80.</div>
      <ModelNote model={b.model} />
    </div>
  )
}

export function DocumentView({ out }: { out: Outputs }) {
  const d = out.document
  if (!d) return null
  return (
    <div className="stack">
      {d.pages.map(p => (
        <article key={p.title} className="page-preview">
          <div className="row wrap between">
            <span className="small muted">{p.space}{p.parent ? ` › ${p.parent}` : ''}</span>
            <Chip tone={p.mode === 'update' ? 'warn' : 'ok'}>{p.mode === 'update' ? 'Update existing page' : 'New page'}</Chip>
          </div>
          <h3 className="page-title">{p.title}</h3>
          {p.labels.length > 0 && <div className="row wrap">{p.labels.map(l => <span key={l} className="label">{l}</span>)}</div>}
          {p.sections.map(s => (
            <section key={s.heading}>
              <h4>{s.heading}</h4>
              {Array.isArray(s.body) ? <ul>{s.body.map(x => <li key={x}>{x}</li>)}</ul> : <p>{s.body}</p>}
            </section>
          ))}
        </article>
      ))}
      <ModelNote model={d.model} />
    </div>
  )
}

export function PublishView({ out }: { out: Outputs }) {
  const p = out.publish
  if (!p) return null
  return (
    <div className="stack">
      <div className="note note-ok">Published and added to the knowledge base. The next similar ticket will find it.</div>
      <ul className="plain-list">
        {p.pages.map(pg => (
          <li key={pg.ref}>
            {pg.url ? <a href={pg.url} target="_blank" rel="noreferrer">{pg.title} <Icon name="external" size={13} /></a> : <b>{pg.title}</b>}
            <span className="muted small"> · {pg.space} · {pg.ref}{pg.simulated ? ' · demo, not sent to Confluence' : ''}{pg.updated ? ' · updated' : ''}</span>
          </li>
        ))}
      </ul>
    </div>
  )
}

export function HistoryView({ flow }: { flow: Flow }) {
  if (!flow.history?.length) return null
  return (
    <details className="history">
      <summary>Decisions ({flow.history.length})</summary>
      <ul className="plain-list small">
        {flow.history.map((h, n) => (
          <li key={n}><b>{h.user}</b> ({ROLES[h.role]?.label ?? h.role}) · {h.gate}: {h.action}{h.comment ? ` · “${h.comment}”` : ''}</li>
        ))}
      </ul>
    </details>
  )
}
