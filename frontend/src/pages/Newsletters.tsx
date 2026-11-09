import { useCallback, useEffect, useMemo, useState, type FormEvent } from 'react'
import { api, fmt, json, type NewsletterRecipients, type NewsletterThread } from '../api'
import { useAuth } from '../auth'
import { ErrorNote, Modal } from '../components'

export default function Newsletters() {
  const { user } = useAuth()
  const [threads, setThreads] = useState<NewsletterThread[] | null>(null)
  const [selectedId, setSelectedId] = useState<number | null>(null)
  const [recipients, setRecipients] = useState<NewsletterRecipients>({ users: [], groups: [] })
  const [composing, setComposing] = useState(false)
  const [error, setError] = useState<string | null>(null)

  const load = useCallback(async (preferred?: number) => {
    try {
      const items = await api<NewsletterThread[]>('/newsletters')
      setThreads(items)
      setSelectedId((current) => preferred ?? current ?? items[0]?.id ?? null)
    } catch (e) { setError((e as Error).message) }
  }, [])

  useEffect(() => {
    load()
    api<NewsletterRecipients>('/newsletters/recipients').then(setRecipients).catch((e) => setError(e.message))
  }, [load])

  const selected = useMemo(() => threads?.find((item) => item.id === selectedId) ?? null, [threads, selectedId])
  const audience = (thread: NewsletterThread) => thread.group
    ? thread.group.name
    : thread.creator.id === user?.id
      ? thread.recipient?.full_name ?? 'Direct newsletter'
      : thread.creator.full_name

  return (
    <>
      <div className="page-head">
        <div><h2>Newsletters</h2><p className="muted small">Direct professor–student messages and group conversations.</p></div>
        <button className="primary" onClick={() => setComposing(true)}>+ New newsletter</button>
      </div>
      <ErrorNote error={error} />
      <div className="newsletter-layout">
        <aside className="card newsletter-list" aria-label="Newsletter conversations">
          {threads === null && <p className="muted">Loading…</p>}
          {threads?.length === 0 && <p className="muted">No newsletters yet. Start a direct or group conversation.</p>}
          {threads?.map((thread) => (
            <button key={thread.id} className={selectedId === thread.id ? 'on' : ''} onClick={() => setSelectedId(thread.id)}>
              <strong>{thread.subject}</strong>
              <span>{thread.group ? 'Group' : 'Direct'} · {audience(thread)}</span>
              <small>{fmt(thread.updated_at)}</small>
            </button>
          ))}
        </aside>
        <section className="card newsletter-thread">
          {selected ? (
            <>
              <header>
                <div><h3>{selected.subject}</h3><p className="muted small">{selected.group ? `Group · ${selected.group.name}` : `Direct · ${audience(selected)}`}</p></div>
                <span className="badge">{selected.messages.length} message{selected.messages.length === 1 ? '' : 's'}</span>
              </header>
              <div className="newsletter-messages">
                {selected.messages.map((message) => (
                  <article key={message.id} className={message.author.id === user?.id ? 'mine' : ''}>
                    <div><strong>{message.author.id === user?.id ? 'You' : message.author.full_name}</strong><time>{fmt(message.created_at)}</time></div>
                    <p>{message.body}</p>
                  </article>
                ))}
              </div>
              <ReplyForm threadId={selected.id} onSent={() => load(selected.id)} />
            </>
          ) : <div className="center muted">Select a newsletter to read it.</div>}
        </section>
      </div>
      {composing && <Compose recipients={recipients} onClose={() => setComposing(false)} onCreated={(id) => { setComposing(false); load(id) }} />}
    </>
  )
}

function ReplyForm({ threadId, onSent }: { threadId: number; onSent: () => void }) {
  const [body, setBody] = useState('')
  const [error, setError] = useState<string | null>(null)
  const [sending, setSending] = useState(false)
  const submit = async (e: FormEvent) => {
    e.preventDefault()
    if (!body.trim()) return
    setSending(true); setError(null)
    try {
      await api(`/newsletters/${threadId}/messages`, json('POST', { body: body.trim() }))
      setBody(''); onSent()
    } catch (err) { setError((err as Error).message) }
    finally { setSending(false) }
  }
  return <form className="newsletter-reply" onSubmit={submit}>
    <label>Reply<textarea required maxLength={5000} rows={3} value={body} onChange={(e) => setBody(e.target.value)} placeholder="Write a reply…" /></label>
    <ErrorNote error={error} />
    <div className="row end"><button className="primary" disabled={sending || !body.trim()}>{sending ? 'Sending…' : 'Send reply'}</button></div>
  </form>
}

function Compose({ recipients, onClose, onCreated }: {
  recipients: NewsletterRecipients; onClose: () => void; onCreated: (id: number) => void
}) {
  const [audience, setAudience] = useState(recipients.users[0] ? `user:${recipients.users[0].id}` : recipients.groups[0] ? `group:${recipients.groups[0].id}` : '')
  const [subject, setSubject] = useState('')
  const [body, setBody] = useState('')
  const [error, setError] = useState<string | null>(null)
  const submit = async (e: FormEvent) => {
    e.preventDefault()
    const [kind, rawId] = audience.split(':')
    if (!rawId) { setError('Choose a recipient or group.'); return }
    try {
      const payload = { subject: subject.trim(), body: body.trim(), ...(kind === 'user' ? { recipient_user_id: Number(rawId) } : { group_id: Number(rawId) }) }
      const created = await api<NewsletterThread>('/newsletters', json('POST', payload))
      onCreated(created.id)
    } catch (err) { setError((err as Error).message) }
  }
  return <Modal title="New newsletter" onClose={onClose}>
    <form className="form" onSubmit={submit}>
      <label>Send to<select required value={audience} onChange={(e) => setAudience(e.target.value)}>
        {!audience && <option value="">No recipients available</option>}
        {recipients.users.length > 0 && <optgroup label="People">{recipients.users.map((person) => <option key={`u${person.id}`} value={`user:${person.id}`}>{person.full_name} · {person.email}</option>)}</optgroup>}
        {recipients.groups.length > 0 && <optgroup label="Groups">{recipients.groups.map((group) => <option key={`g${group.id}`} value={`group:${group.id}`}>{group.name}</option>)}</optgroup>}
      </select></label>
      <label>Subject<input required maxLength={200} value={subject} onChange={(e) => setSubject(e.target.value)} /></label>
      <label>Message<textarea required maxLength={5000} rows={7} value={body} onChange={(e) => setBody(e.target.value)} /></label>
      <ErrorNote error={error} />
      <div className="row end"><button type="button" onClick={onClose}>Cancel</button><button className="primary">Send newsletter</button></div>
    </form>
  </Modal>
}
