import { useEffect, useState, type FormEvent } from 'react'
import { api } from '../api'
import { ErrorNote, PageHeader } from '../components'
import { useApp } from '../context'
import type { Project } from '../types'
import ConnectionsPage from './Connections'
import ModelsPage from './Models'

export type SettingsTab = 'general' | 'models' | 'connections'

const TABS: { key: SettingsTab; label: string }[] = [
  { key: 'general', label: 'General' },
  { key: 'models', label: 'AI models' },
  { key: 'connections', label: 'Connections' },
]

// SAP_BASIS releases with the systems that typically run on them.
const RELEASES: { value: number; label: string }[] = [
  { value: 700, label: '7.00 · ECC 6.0 (EhP0–3), CRM 2007' },
  { value: 702, label: '7.02 · ECC EhP4–5, CRM 7.0 EhP1' },
  { value: 731, label: '7.31 · ECC EhP6, CRM 7.0 EhP2' },
  { value: 740, label: '7.40 · ECC EhP7, CRM 7.0 EhP3' },
  { value: 750, label: '7.50 · ECC EhP8, CRM 7.0 EhP4' },
  { value: 752, label: '7.52 · S/4HANA 1709' },
  { value: 753, label: '7.53 · S/4HANA 1809' },
  { value: 754, label: '7.54 · S/4HANA 1909' },
  { value: 755, label: '7.55 · S/4HANA 2020' },
  { value: 756, label: '7.56 · S/4HANA 2021' },
  { value: 757, label: '7.57 · S/4HANA 2022' },
  { value: 758, label: '7.58 · S/4HANA 2023' },
]

function General({ canEdit }: { canEdit: boolean }) {
  const { project, reloadProject, reloadModels } = useApp()
  const [form, setForm] = useState<Project | null>(project)
  const [saving, setSaving] = useState(false)
  const [saved, setSaved] = useState(false)
  const [error, setError] = useState('')

  useEffect(() => { setForm(project) }, [project])
  if (!form) return null

  const save = async (e: FormEvent) => {
    e.preventDefault()
    setSaving(true)
    setError('')
    try {
      await api.put('/project', { name: form.name, sap_release: form.sap_release, sap_cloud: form.sap_cloud, sample_data: form.sample_data })
      reloadProject()
      reloadModels()
      setSaved(true)
      setTimeout(() => setSaved(false), 2000)
    } catch (err) {
      setError((err as Error).message)
    } finally {
      setSaving(false)
    }
  }

  const sampleOff = project?.sample_data && !form.sample_data

  return (
    <form className="form settings-form" onSubmit={save}>
      <fieldset disabled={!canEdit}>
        <label>Project name<input required value={form.name} onChange={e => setForm({ ...form, name: e.target.value })} /></label>

        <div className="field-group">
          <span className="field-title">Target SAP release</span>
          <span className="small muted">Used for generated code while no SAP system is connected. A connected system's own release always wins.</span>
          <div className="row wrap">
            <select value={form.sap_release ?? ''} disabled={form.sap_cloud}
              onChange={e => setForm({ ...form, sap_release: e.target.value ? Number(e.target.value) : null })} aria-label="Target SAP release">
              <option value="">Not set</option>
              {RELEASES.map(r => <option key={r.value} value={r.value}>{r.label}</option>)}
            </select>
            <label className="check"><input type="checkbox" checked={form.sap_cloud} onChange={e => setForm({ ...form, sap_cloud: e.target.checked })} />ABAP Cloud (BTP, S/4HANA Cloud)</label>
          </div>
        </div>

        <div className="field-group">
          <label className="check switch-row">
            <input type="checkbox" checked={form.sample_data} onChange={e => setForm({ ...form, sample_data: e.target.checked })} />
            <span><b>Sample data</b><br /><span className="small muted">Five sample tickets, Confluence pages, SAP code and a sample model, for demos and training.</span></span>
          </label>
          {sampleOff && <div className="note note-warn">Saving removes the sample tickets, their flows and the sample model.</div>}
        </div>
      </fieldset>
      {error && <ErrorNote message={error} />}
      {canEdit && (
        <div className="row">
          <button className="btn btn-primary" type="submit" disabled={saving}>{saving ? 'Saving…' : 'Save'}</button>
          {saved && <span className="small muted">Saved</span>}
        </div>
      )}
    </form>
  )
}

export default function SettingsPage({ tab }: { tab: SettingsTab }) {
  const { role } = useApp()
  const canEdit = role === 'admin'
  return (
    <div className="page">
      <PageHeader title="Settings" subtitle="Project, AI models and connected systems." help="settings" />
      <nav className="tabs" aria-label="Settings sections">
        {TABS.map(t => <a key={t.key} href={`#/settings/${t.key}`} className={tab === t.key ? 'on' : ''}>{t.label}</a>)}
      </nav>
      {!canEdit && <div className="note">You can look at the settings. To change them, switch Role to <b>Admin</b> in the top bar.</div>}
      {tab === 'general' && <General canEdit={canEdit} />}
      {tab === 'models' && <ModelsPage />}
      {tab === 'connections' && <ConnectionsPage />}
    </div>
  )
}
