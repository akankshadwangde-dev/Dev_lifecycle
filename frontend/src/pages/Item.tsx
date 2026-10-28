import { useEffect, useState } from 'react'
import { api } from '../api'
import { Chip, ErrorNote, HelpButton, Icon, KindChip, Spinner, StatusChip } from '../components'
import { useApp } from '../context'
import { ROLES, actionLabel } from '../roles'
import type { Action, Flow, GateName, WorkItem } from '../types'
import { BuildView, DocumentView, HistoryView, ImpactView, IntakeView, KnowledgeView, PlanView, PublishView } from './StageViews'

const STEPS = [
  { key: 'intake', label: 'Intake' },
  { key: 'knowledge', label: 'Knowledge' },
  { key: 'impact', label: 'Impact' },
  { key: 'plan', label: 'Plan' },
  { key: 'build', label: 'Build' },
  { key: 'document', label: 'Document' },
  { key: 'publish', label: 'Published' },
] as const
type StepKey = typeof STEPS[number]['key']

const GATE_STAGE: Record<GateName, StepKey> = { recommendation: 'knowledge', plan: 'plan', change: 'build', pages: 'document' }
const SKIPPED_WITHOUT_CODE: StepKey[] = ['impact', 'plan', 'build']

interface Detail { item: WorkItem; flow: Flow }

export default function ItemPage({ itemKey }: { itemKey: string }) {
  const { role } = useApp()
  const [data, setData] = useState<Detail | null>(null)
  const [selected, setSelected] = useState<StepKey | null>(null)
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState('')
  const [revising, setRevising] = useState(false)
  const [comment, setComment] = useState('')

  const show = (d: Detail) => {
    setData(d)
    const out = d.flow.outputs ?? {}
    const gateStage = d.flow.gate ? GATE_STAGE[d.flow.gate.name] : null
    const last = [...STEPS].reverse().find(s => s.key in out)?.key ?? 'intake'
    setSelected(gateStage ?? last)
  }

  const load = () => api.get<Detail>(`/work-items/${encodeURIComponent(itemKey)}`).then(show).catch(e => setError(e.message))
  useEffect(() => { load() }, [itemKey])

  const run = async (path: string, body?: unknown) => {
    setBusy(true)
    setError('')
    try {
      show(await api.post<Detail>(`/work-items/${encodeURIComponent(itemKey)}/${path}`, body))
      setRevising(false)
      setComment('')
    } catch (e) {
      setError((e as Error).message)
    } finally {
      setBusy(false)
    }
  }

  if (!data) return <div className="page">{error ? <ErrorNote message={error} onRetry={load} /> : <Spinner />}</div>

  const { item, flow } = data
  const out = flow.outputs ?? {}
  const gate = flow.gate ?? null
  const gateStage = gate ? GATE_STAGE[gate.name] : null
  const noCode = flow.resolution === 'no_code'
  const canStart = ROLES[role].startsKinds.length > 0 || role === 'lead'

  const stepState = (key: StepKey) => {
    if (noCode && SKIPPED_WITHOUT_CODE.includes(key)) return 'skipped'
    if (key === gateStage) return 'current'
    if (key in out) return 'done'
    return 'todo'
  }

  const allowed = (a: Action) => gate?.actions.find(x => x.action === a)?.allowed ?? false
  const canDecide = gate?.actions.some(a => a.allowed) ?? false

  return (
    <div className="page">
      <a className="back" href="#/home"><Icon name="back" size={16} />Back</a>
      <div className="item-head">
        <div>
          <div className="row wrap">
            <span className="key big">{item.key}</span>
            <KindChip kind={item.kind} />
            {item.priority && <Chip>{item.priority}</Chip>}
            <StatusChip item={item} />
          </div>
          <h1>{item.title}</h1>
        </div>
        <HelpButton topic="item" />
      </div>

      {!flow.started ? (
        <div className="start-card">
          <IntakeView item={item} out={{}} />
          <div className="row">
            {canStart
              ? <button className="btn btn-primary" disabled={busy} onClick={() => run('start')}>{busy ? <><Spinner />Analysing…</> : 'Start analysis'}</button>
              : <span className="muted">Not started yet.</span>}
          </div>
          {busy && <p className="muted small">The AI is searching Confluence, past tickets and the SAP code. This can take a minute with a real model.</p>}
          {error && <ErrorNote message={error} />}
        </div>
      ) : (
        <>
          <ol className="stepper" aria-label="Progress">
            {STEPS.map(s => {
              const st = stepState(s.key)
              const clickable = st === 'done' || st === 'current'
              return (
                <li key={s.key} className={`step step-${st} ${selected === s.key ? 'selected' : ''}`}>
                  <button disabled={!clickable} onClick={() => setSelected(s.key)} aria-current={selected === s.key}>
                    <span className="dot">{st === 'done' ? <Icon name="check" size={12} /> : ''}</span>
                    <span>{s.label}</span>
                    {st === 'skipped' && <span className="small muted">skipped</span>}
                  </button>
                </li>
              )
            })}
          </ol>

          {flow.error && <ErrorNote message={`This step stopped: ${flow.error}`} onRetry={() => run('retry')} />}
          {error && <ErrorNote message={error} />}

          <section className="stage-card">
            {selected === 'intake' && <IntakeView item={item} out={out} />}
            {selected === 'knowledge' && <KnowledgeView out={out} />}
            {selected === 'impact' && <ImpactView out={out} />}
            {selected === 'plan' && <PlanView out={out} kind={item.kind} />}
            {selected === 'build' && <BuildView out={out} />}
            {selected === 'document' && <DocumentView out={out} />}
            {selected === 'publish' && <PublishView out={out} />}

            {gate && selected === gateStage && (
              <div className="decision">
                {busy ? (
                  <div className="row"><Spinner /><span>Working on the next step…</span></div>
                ) : !canDecide ? (
                  <div className="row"><Chip tone="warn">Waiting</Chip><span className="muted">for {gate.waiting_for.join(' or ')}</span></div>
                ) : revising ? (
                  <div className="stack">
                    <label htmlFor="revise-comment" className="small muted">What should change?</label>
                    <textarea id="revise-comment" rows={3} value={comment} onChange={e => setComment(e.target.value)} autoFocus />
                    <div className="row">
                      <button className="btn btn-primary" disabled={!comment.trim()} onClick={() => run('decide', { action: 'revise', comment })}>Send back</button>
                      <button className="btn" onClick={() => setRevising(false)}>Cancel</button>
                    </div>
                  </div>
                ) : (
                  <div className="row wrap">
                    {allowed('approve') && <button className="btn btn-primary" onClick={() => run('decide', { action: 'approve' })}>{actionLabel(role, gate.name, 'approve')}</button>}
                    {allowed('no_code') && <button className="btn" onClick={() => run('decide', { action: 'no_code' })}>{actionLabel(role, gate.name, 'no_code')}</button>}
                    {allowed('revise') && <button className="btn btn-ghost" onClick={() => setRevising(true)}>{actionLabel(role, gate.name, 'revise')}</button>}
                    {!allowed('approve') && <span className="muted small">Approval: {gate.waiting_for.join(' or ')}</span>}
                  </div>
                )}
              </div>
            )}
          </section>
          {flow.done && <div className="note note-ok">Done. Nothing else to decide.</div>}
          <HistoryView flow={flow} />
        </>
      )}
    </div>
  )
}
