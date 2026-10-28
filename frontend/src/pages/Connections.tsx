import { useEffect, useState, type FormEvent } from 'react'
import { api } from '../api'
import { Chip, Drawer, Empty, ErrorNote, Icon, PageHeader } from '../components'
import type { Connection } from '../types'

type Draft = Omit<Connection, 'id' | 'status' | 'detail'>
const EMPTY: Draft = { kind: 'jira', name: '', base_url: '', auth: 'basic', username: '', secret_ref: '', options: { deployment: 'cloud' }, enabled: true }

const URL_HINT: Record<string, string> = {
  jira: 'https://yourorg.atlassian.net',
  confluence: 'https://yourorg.atlassian.net/wiki',
  sap_adt: 'https://s4d.example.com:44300',
  sap_rfc: 'Application server host',
}

export default function ConnectionsPage() {
  const [conns, setConns] = useState<Connection[]>([])
  const [kinds, setKinds] = useState<Record<string, string>>({})
  const [draft, setDraft] = useState<Draft | null>(null)
  const [testing, setTesting] = useState<number | null>(null)
  const [error, setError] = useState('')

  const load = () => api.get<Connection[]>('/connections').then(setConns).catch(e => setError(e.message))
  useEffect(() => {
    load()
    api.get<Record<string, string>>('/connections/kinds').then(setKinds).catch(() => undefined)
  }, [])

  const opt = (key: string) => String(draft?.options[key] ?? '')
  const setOpt = (key: string, value: unknown) => draft && setDraft({ ...draft, options: { ...draft.options, [key]: value } })

  const save = async (e: FormEvent) => {
    e.preventDefault()
    if (!draft) return
    setError('')
    try {
      const options = { ...draft.options }
      if (typeof options.spaces === 'string') options.spaces = (options.spaces as string).split(',').map(s => s.trim()).filter(Boolean)
      const created = await api.post<Connection>('/connections', { ...draft, options })
      setDraft(null)
      await load()
      test(created.id)
    } catch (err) {
      setError((err as Error).message)
    }
  }

  const test = async (id: number) => {
    setTesting(id)
    try {
      await api.post(`/connections/${id}/test`)
      await load()
    } finally {
      setTesting(null)
    }
  }

  const remove = async (id: number) => {
    await api.del(`/connections/${id}`).catch(e => setError(e.message))
    load()
  }

  return (
    <div className="page">
      <PageHeader title="Connections" subtitle="Where the studio reads tickets, documents and code." help="connections"
        actions={<button className="btn btn-primary" onClick={() => setDraft({ ...EMPTY })}><Icon name="plus" size={16} />Add connection</button>} />
      {error && !draft && <ErrorNote message={error} />}
      {conns.length === 0 ? (
        <Empty title="No connections yet">Demo data is used until you add Jira, Confluence or an SAP system.</Empty>
      ) : (
        <div className="table-wrap">
          <table>
            <thead><tr><th>Name</th><th>Type</th><th>Address</th><th>Status</th><th /></tr></thead>
            <tbody>
              {conns.map(c => (
                <tr key={c.id}>
                  <td><b>{c.name}</b></td>
                  <td>{kinds[c.kind] ?? c.kind}</td>
                  <td className="small"><code>{c.base_url}</code></td>
                  <td>
                    {testing === c.id ? <span className="muted small">Testing…</span>
                      : <Chip tone={c.status === 'ok' ? 'ok' : c.status === 'error' ? 'bad' : 'neutral'}>{c.status === 'ok' ? 'Connected' : c.status === 'error' ? 'Failed' : 'Not tested'}</Chip>}
                    {c.detail && <div className="small muted clamp">{c.detail}</div>}
                  </td>
                  <td className="row push">
                    <button className="btn btn-sm" onClick={() => test(c.id)}>Test</button>
                    <button className="btn btn-sm btn-ghost" onClick={() => remove(c.id)}>Remove</button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}

      <Drawer open={!!draft} title="Add connection" onClose={() => setDraft(null)}>
        {draft && (
          <form className="form" onSubmit={save}>
            <label>Type
              <select value={draft.kind} onChange={e => setDraft({ ...draft, kind: e.target.value, options: e.target.value.startsWith('sap') ? {} : { deployment: 'cloud' } })}>
                {Object.entries(kinds).map(([k, label]) => <option key={k} value={k}>{label}</option>)}
              </select>
            </label>
            <label>Name<input required value={draft.name} onChange={e => setDraft({ ...draft, name: e.target.value })} placeholder="e.g. S4D development" /></label>
            <label>{draft.kind === 'sap_rfc' ? 'Host' : 'URL'}<input required value={draft.base_url} onChange={e => setDraft({ ...draft, base_url: e.target.value })} placeholder={URL_HINT[draft.kind]} /></label>

            {(draft.kind === 'jira' || draft.kind === 'confluence') && (
              <label>Deployment
                <select value={opt('deployment')} onChange={e => setOpt('deployment', e.target.value)}>
                  <option value="cloud">Cloud</option><option value="datacenter">Data Center / Server</option>
                </select>
              </label>
            )}
            {draft.kind !== 'sap_rfc' && (
              <label>Sign-in
                <select value={draft.auth} onChange={e => setDraft({ ...draft, auth: e.target.value as Draft['auth'] })}>
                  <option value="basic">User + API token / password</option><option value="bearer">Personal access token</option>
                </select>
              </label>
            )}
            {(draft.auth === 'basic' || draft.kind === 'sap_rfc') && (
              <label>User<input value={draft.username} onChange={e => setDraft({ ...draft, username: e.target.value })} /></label>
            )}
            <label>Secret reference<input value={draft.secret_ref} onChange={e => setDraft({ ...draft, secret_ref: e.target.value })} placeholder="env:JIRA_TOKEN" /></label>

            {draft.kind === 'jira' && (
              <label>Which tickets (JQL)<input value={opt('jql')} onChange={e => setOpt('jql', e.target.value)} placeholder="project = O2C AND statusCategory != Done" /></label>
            )}
            {draft.kind === 'confluence' && (
              <>
                <label>Spaces to read<input value={opt('spaces')} onChange={e => setOpt('spaces', e.target.value)} placeholder="O2C, AMS, DEV" /></label>
                <label>Space the studio may write to<input value={opt('publish_space')} onChange={e => setOpt('publish_space', e.target.value)} placeholder="AMS" /></label>
              </>
            )}
            {draft.kind === 'sap_adt' && (
              <div className="row">
                <label className="grow">Client<input value={opt('client')} onChange={e => setOpt('client', e.target.value)} placeholder="100" /></label>
                <label className="check"><input type="checkbox" checked={!!draft.options.cloud} onChange={e => setOpt('cloud', e.target.checked)} />ABAP Cloud</label>
              </div>
            )}
            {draft.kind === 'sap_rfc' && (
              <div className="row">
                <label className="grow">System no.<input value={opt('sysnr')} onChange={e => setOpt('sysnr', e.target.value)} placeholder="00" /></label>
                <label className="grow">Client<input value={opt('client')} onChange={e => setOpt('client', e.target.value)} placeholder="100" /></label>
              </div>
            )}
            {error && <ErrorNote message={error} />}
            <div className="row"><button className="btn btn-primary" type="submit">Save and test</button><button className="btn" type="button" onClick={() => setDraft(null)}>Cancel</button></div>
          </form>
        )}
      </Drawer>
    </div>
  )
}
