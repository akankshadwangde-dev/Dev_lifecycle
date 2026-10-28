import { useEffect, useState, type FormEvent } from 'react'
import { api } from '../api'
import { Chip, Drawer, ErrorNote, Icon, PageHeader } from '../components'
import { useApp } from '../context'
import type { ModelConfig, Provider } from '../types'

interface Catalog { providers: Record<string, Provider>; data_levels: string[]; stages: string[] }
type Draft = Omit<ModelConfig, 'id'> & { id?: number }

const LEVEL_TONE = { public: 'neutral', code: 'accent', production: 'warn' } as const
const LEVEL_HELP: Record<string, string> = {
  public: 'Docs only', code: 'Code and tickets', production: 'Also production data',
}
const EMPTY: Draft = { name: '', provider: 'anthropic', model: '', api_base: '', secret_ref: '', data_level: 'code', stages: [], enabled: true, priority: 100 }

export default function ModelsPage() {
  const { role, models, reloadModels } = useApp()
  const canManage = role === 'admin'
  const [catalog, setCatalog] = useState<Catalog | null>(null)
  const [draft, setDraft] = useState<Draft | null>(null)
  const [tests, setTests] = useState<Record<number, { ok: boolean; message: string } | 'running'>>({})
  const [error, setError] = useState('')

  useEffect(() => { api.get<Catalog>('/models/providers').then(setCatalog).catch(e => setError(e.message)) }, [])

  const test = async (id: number) => {
    setTests(t => ({ ...t, [id]: 'running' }))
    const res = await api.post<{ ok: boolean; message: string }>(`/models/${id}/test`).catch(e => ({ ok: false, message: (e as Error).message }))
    setTests(t => ({ ...t, [id]: res }))
  }

  const save = async (e: FormEvent) => {
    e.preventDefault()
    if (!draft) return
    setError('')
    try {
      const { id, ...body } = draft
      if (id) await api.put(`/models/${id}`, body)
      else await api.post('/models', body)
      setDraft(null)
      reloadModels()
    } catch (err) {
      setError((err as Error).message)
    }
  }

  const remove = async (id: number) => {
    try {
      await api.del(`/models/${id}`)
      reloadModels()
    } catch (err) {
      setError((err as Error).message)
    }
  }

  const provider = draft && catalog ? catalog.providers[draft.provider] : null

  return (
    <div className="page">
      <PageHeader title="Models" subtitle="Any model your organisation allows. Users pick one in the top bar." help="models"
        actions={canManage && <button className="btn btn-primary" onClick={() => setDraft({ ...EMPTY })}><Icon name="plus" size={16} />Add model</button>} />
      {error && !draft && <ErrorNote message={error} />}
      {!canManage && <div className="note">Only admins can add or change models.</div>}
      <div className="table-wrap">
        <table>
          <thead><tr><th>Name</th><th>Provider</th><th>Data level</th><th>Default for</th><th>Status</th><th /></tr></thead>
          <tbody>
            {models.map(m => {
              const t = tests[m.id]
              return (
                <tr key={m.id}>
                  <td><b>{m.name}</b><div className="small muted">{m.model}</div></td>
                  <td>{catalog?.providers[m.provider]?.label ?? m.provider}</td>
                  <td><Chip tone={LEVEL_TONE[m.data_level]}>{m.data_level}</Chip></td>
                  <td className="small">{m.stages.length ? m.stages.join(', ') : <span className="muted">—</span>}</td>
                  <td>
                    {!m.enabled ? <Chip>Off</Chip>
                      : t === 'running' ? <span className="muted small">Testing…</span>
                      : t ? <Chip tone={t.ok ? 'ok' : 'bad'}>{t.ok ? 'Works' : 'Failed'}</Chip>
                      : <Chip tone="ok">On</Chip>}
                    {t && t !== 'running' && !t.ok && <div className="small muted clamp">{t.message}</div>}
                  </td>
                  <td className="row push">
                    <button className="btn btn-sm" onClick={() => test(m.id)}>Test</button>
                    {canManage && <button className="btn btn-sm" onClick={() => setDraft({ ...m })}>Edit</button>}
                    {canManage && <button className="btn btn-sm btn-ghost" onClick={() => remove(m.id)}>Remove</button>}
                  </td>
                </tr>
              )
            })}
          </tbody>
        </table>
      </div>

      <Drawer open={!!draft} title={draft?.id ? 'Edit model' : 'Add model'} onClose={() => setDraft(null)}>
        {draft && catalog && (
          <form className="form" onSubmit={save}>
            <label>Name<input required value={draft.name} onChange={e => setDraft({ ...draft, name: e.target.value })} placeholder="e.g. Claude Opus" /></label>
            <label>Provider
              <select value={draft.provider} onChange={e => setDraft({ ...draft, provider: e.target.value })}>
                {Object.entries(catalog.providers).map(([k, p]) => <option key={k} value={k}>{p.label}</option>)}
              </select>
            </label>
            <label>Model or deployment name<input required value={draft.model} onChange={e => setDraft({ ...draft, model: e.target.value })} placeholder={provider?.example} /></label>
            <label>Endpoint URL{!provider?.needs_base && <span className="muted"> (optional)</span>}
              <input required={provider?.needs_base} value={draft.api_base} onChange={e => setDraft({ ...draft, api_base: e.target.value })} placeholder="https://…" />
            </label>
            <label>Secret reference<input value={draft.secret_ref} onChange={e => setDraft({ ...draft, secret_ref: e.target.value })} placeholder="env:ANTHROPIC_API_KEY" /></label>
            <fieldset>
              <legend>Data this model may receive</legend>
              <div className="segmented">
                {catalog.data_levels.map(l => (
                  <button type="button" key={l} className={draft.data_level === l ? 'on' : ''} onClick={() => setDraft({ ...draft, data_level: l as Draft['data_level'] })}>
                    <b>{l}</b><span>{LEVEL_HELP[l]}</span>
                  </button>
                ))}
              </div>
            </fieldset>
            <fieldset>
              <legend>Default model for</legend>
              <div className="row wrap">
                {catalog.stages.map(s => (
                  <label key={s} className="check">
                    <input type="checkbox" checked={draft.stages.includes(s)}
                      onChange={e => setDraft({ ...draft, stages: e.target.checked ? [...draft.stages, s] : draft.stages.filter(x => x !== s) })} />
                    {s}
                  </label>
                ))}
              </div>
            </fieldset>
            <div className="row">
              <label className="grow">Priority<input type="number" value={draft.priority} onChange={e => setDraft({ ...draft, priority: Number(e.target.value) })} /></label>
              <label className="check"><input type="checkbox" checked={draft.enabled} onChange={e => setDraft({ ...draft, enabled: e.target.checked })} />Enabled</label>
            </div>
            {error && <ErrorNote message={error} />}
            <div className="row"><button className="btn btn-primary" type="submit">Save</button><button className="btn" type="button" onClick={() => setDraft(null)}>Cancel</button></div>
          </form>
        )}
      </Drawer>
    </div>
  )
}
