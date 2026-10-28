import { useEffect, useState } from 'react'
import { api } from '../api'
import { Empty, ErrorNote, PageHeader, Spinner } from '../components'
import { ROLES } from '../roles'
import type { AuditEntry } from '../types'

export default function AuditPage() {
  const [rows, setRows] = useState<AuditEntry[] | null>(null)
  const [error, setError] = useState('')
  useEffect(() => { api.get<AuditEntry[]>('/audit').then(setRows).catch(e => setError(e.message)) }, [])

  return (
    <div className="page">
      <PageHeader title="Audit trail" subtitle="Who did what, and when." help="audit" />
      {error && <ErrorNote message={error} />}
      {!rows ? (!error && <Spinner />) : rows.length === 0 ? <Empty title="Nothing recorded yet" /> : (
        <div className="table-wrap">
          <table>
            <thead><tr><th>When</th><th>Who</th><th>Action</th><th>Item</th><th>Detail</th></tr></thead>
            <tbody>
              {rows.map(r => (
                <tr key={r.id}>
                  <td className="nowrap small">{new Date(r.ts.endsWith('Z') || r.ts.includes('+') ? r.ts : `${r.ts}Z`).toLocaleString()}</td>
                  <td>{r.user}<div className="small muted">{ROLES[r.role]?.label ?? r.role}</div></td>
                  <td>{r.action}</td>
                  <td>{r.item_key && <a href={`#/item/${encodeURIComponent(r.item_key)}`} className="key">{r.item_key}</a>}</td>
                  <td className="small muted">{[r.detail, r.model].filter(Boolean).join(' · ')}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  )
}
