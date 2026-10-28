import type { ReactNode } from 'react'
import { useApp } from './context'
import { KIND_LABELS } from './roles'
import type { Kind, WorkItem } from './types'

const PATHS: Record<string, string> = {
  home: 'M3 10.5 12 3l9 7.5V20a1 1 0 0 1-1 1h-5v-6H9v6H4a1 1 0 0 1-1-1z',
  book: 'M4 4.5A1.5 1.5 0 0 1 5.5 3H20v15H5.5A1.5 1.5 0 0 0 4 19.5zM4 19.5A1.5 1.5 0 0 0 5.5 21H20',
  chip: 'M7 7h10v10H7zM9 3v4M15 3v4M9 17v4M15 17v4M3 9h4M3 15h4M17 9h4M17 15h4',
  plug: 'M9 3v5M15 3v5M6 8h12v3a6 6 0 0 1-12 0zM12 17v4',
  list: 'M8 6h13M8 12h13M8 18h13M3 6h.01M3 12h.01M3 18h.01',
  help: 'M9.1 9a3 3 0 0 1 5.8 1c0 2-3 2.5-3 4.5M12 18h.01M12 22a10 10 0 1 0 0-20 10 10 0 0 0 0 20z',
  back: 'M15 18l-6-6 6-6',
  refresh: 'M21 12a9 9 0 1 1-2.6-6.4M21 3v6h-6',
  copy: 'M9 9h11v11H9zM5 15H4V4h11v1',
  download: 'M12 3v12M7 10l5 5 5-5M5 21h14',
  close: 'M6 6l12 12M18 6 6 18',
  check: 'M5 12l5 5 9-10',
  search: 'M11 18a7 7 0 1 0 0-14 7 7 0 0 0 0 14zM21 21l-5-5',
  plus: 'M12 5v14M5 12h14',
  external: 'M14 4h6v6M20 4l-9 9M18 14v6H4V6h6',
}

export function Icon({ name, size = 18 }: { name: keyof typeof PATHS | string; size?: number }) {
  return (
    <svg width={size} height={size} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8"
      strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">
      <path d={PATHS[name] ?? ''} />
    </svg>
  )
}

type Tone = 'neutral' | 'accent' | 'ok' | 'warn' | 'bad'

export function Chip({ tone = 'neutral', children }: { tone?: Tone; children: ReactNode }) {
  return <span className={`chip chip-${tone}`}>{children}</span>
}

const KIND_TONE: Record<Kind, Tone> = { incident: 'bad', change: 'accent', new: 'ok' }

export function KindChip({ kind }: { kind: Kind }) {
  return <Chip tone={KIND_TONE[kind]}>{KIND_LABELS[kind]}</Chip>
}

export function StatusChip({ item }: { item: WorkItem }) {
  if (item.status === 'error') return <Chip tone="bad">Error</Chip>
  if (item.status === 'done') return <Chip tone="ok">Done</Chip>
  if (item.status === 'waiting') return <Chip tone="warn">Waiting · {item.gate}</Chip>
  if (item.status === 'in_progress') return <Chip tone="accent">In progress</Chip>
  return <Chip>Not started</Chip>
}

export function HelpButton({ topic, label }: { topic: string; label?: string }) {
  const { openHelp } = useApp()
  return (
    <button className="help-btn" onClick={() => openHelp(topic)} aria-label={label ?? 'Help'} title="Help">
      <Icon name="help" size={16} />
    </button>
  )
}

export function PageHeader({ title, subtitle, help, actions }: {
  title: string; subtitle?: string; help?: string; actions?: ReactNode
}) {
  return (
    <div className="page-header">
      <div>
        <h1>{title}{help && <HelpButton topic={help} />}</h1>
        {subtitle && <p className="muted">{subtitle}</p>}
      </div>
      {actions && <div className="row">{actions}</div>}
    </div>
  )
}

export function Stat({ value, label, tone }: { value: ReactNode; label: string; tone?: Tone }) {
  return (
    <div className={`stat ${tone ? `stat-${tone}` : ''}`}>
      <b>{value}</b>
      <span>{label}</span>
    </div>
  )
}

export function Empty({ title, children }: { title: string; children?: ReactNode }) {
  return (
    <div className="empty">
      <b>{title}</b>
      {children && <div className="muted">{children}</div>}
    </div>
  )
}

export function Spinner() {
  return <span className="spinner" aria-label="Loading" />
}

export function ErrorNote({ message, onRetry }: { message: string; onRetry?: () => void }) {
  return (
    <div className="note note-bad" role="alert">
      <span>{message}</span>
      {onRetry && <button className="btn btn-sm" onClick={onRetry}>Retry</button>}
    </div>
  )
}

export function Drawer({ open, title, onClose, children, wide }: {
  open: boolean; title: string; onClose: () => void; children: ReactNode; wide?: boolean
}) {
  if (!open) return null
  return (
    <div className="drawer-backdrop" onClick={onClose}>
      <aside className={`drawer ${wide ? 'drawer-wide' : ''}`} onClick={e => e.stopPropagation()} role="dialog" aria-label={title}>
        <header className="drawer-head">
          <h2>{title}</h2>
          <button className="icon-btn" onClick={onClose} aria-label="Close"><Icon name="close" /></button>
        </header>
        <div className="drawer-body">{children}</div>
      </aside>
    </div>
  )
}

export function timeAgo(iso: string): string {
  const then = new Date(iso.endsWith('Z') || iso.includes('+') ? iso : `${iso}Z`).getTime()
  const mins = Math.round((Date.now() - then) / 60000)
  if (mins < 1) return 'just now'
  if (mins < 60) return `${mins} min ago`
  const hours = Math.round(mins / 60)
  if (hours < 24) return `${hours} h ago`
  return `${Math.round(hours / 24)} d ago`
}
