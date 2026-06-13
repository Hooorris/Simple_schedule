import { useState, useEffect } from 'react'

// 弹窗组件：用于创建或编辑事件
export default function EventModal({ type, date: initialDate, event, onSave, onDelete, onClose }) {
  const [title, setTitle] = useState('')
  const [date, setDate] = useState('')
  const [note, setNote] = useState('')
  const [priority, setPriority] = useState(0)
  const [completed, setCompleted] = useState(false)
  const [reminderEnabled, setReminderEnabled] = useState(false)
  const [reminderKind, setReminderKind] = useState('once')
  const [reminderTime, setReminderTime] = useState('09:00')
  const [reminderDate, setReminderDate] = useState('')
  const [reminderDay, setReminderDay] = useState(0)
  const [reminderWebhook, setReminderWebhook] = useState('')

  useEffect(() => {
    if (event) {
      setTitle(event.title)
      setDate(event.date)
      setNote(event.note || '')
      setPriority(event.priority || 0)
      setCompleted(Boolean(event.completed))
    } else if (initialDate) {
      setTitle('')
      setDate(initialDate)
      setNote('')
      setPriority(0)
      setCompleted(false)
      setReminderDate(initialDate)
    }
  }, [event, initialDate])

  const submit = (e) => {
    e.preventDefault()
    if (!title.trim()) return
    const payload = {
      title: title.trim(),
      date: date,
      priority: Number(priority) || 0,
      completed: Boolean(completed),
      note: note.trim(),
    }
    if (reminderEnabled) {
      payload.reminder = {
        kind: reminderKind,
        time: reminderTime,
        date: reminderKind === 'once' ? reminderDate : undefined,
        day: (reminderKind === 'weekly' || reminderKind === 'monthly') ? Number(reminderDay) : undefined,
        webhook: reminderWebhook || undefined,
        enabled: true
      }
    }
    onSave(payload)
  }

  return (
    <div className="fixed inset-0 bg-black/30 flex items-center justify-center z-50" onClick={onClose}>
      <div className="bg-white rounded-2xl p-6 w-full max-w-sm mx-4 shadow-xl" onClick={e => e.stopPropagation()}>
        <h3 className="text-lg font-semibold mb-4">{type === 'add' ? 'Add Event' : 'Edit Event'}</h3>
        <form onSubmit={submit}>
          <input value={title} onChange={e => setTitle(e.target.value)} placeholder="Title" autoFocus
            className="w-full px-3 py-2 border border-gray-300 rounded-lg mb-3 text-sm" />
          <label className="text-xs text-gray-500">Date</label>
          <input type="date" value={date} onChange={e => setDate(e.target.value)}
            className="w-full px-3 py-2 border border-gray-300 rounded-lg mb-3 text-sm" />
          <textarea value={note} onChange={e => setNote(e.target.value)} placeholder="Note (optional)" rows={2}
            className="w-full px-3 py-2 border border-gray-300 rounded-lg mb-3 text-sm resize-none" />
          <label className="text-xs text-gray-500">Priority (higher first)</label>
          <input type="number" value={priority} onChange={e => setPriority(parseInt(e.target.value) || 0)} step="1"
            className="w-full px-3 py-2 border border-gray-300 rounded-lg mb-3 text-sm" />
          <div className="mb-3">
            <label className="inline-flex items-center gap-2 text-sm"><input type="checkbox" checked={reminderEnabled} onChange={e => setReminderEnabled(e.target.checked)} /> 设置提醒</label>
            {reminderEnabled && (
              <div className="mt-2 space-y-2">
                <div className="flex gap-2">
                  <select value={reminderKind} onChange={e => setReminderKind(e.target.value)} className="px-2 py-1 border rounded">
                    <option value="once">单次</option>
                    <option value="daily">每天</option>
                    <option value="weekly">每周</option>
                    <option value="monthly">每月</option>
                  </select>
                  <input type="time" value={reminderTime} onChange={e => setReminderTime(e.target.value)} className="px-2 py-1 border rounded" />
                </div>
                {reminderKind === 'once' && (
                  <input type="date" value={reminderDate} onChange={e => setReminderDate(e.target.value)} className="w-full px-2 py-1 border rounded" />
                )}
                {reminderKind === 'weekly' && (
                  <select value={reminderDay} onChange={e => setReminderDay(e.target.value)} className="px-2 py-1 border rounded">
                    <option value={0}>周日</option>
                    <option value={1}>周一</option>
                    <option value={2}>周二</option>
                    <option value={3}>周三</option>
                    <option value={4}>周四</option>
                    <option value={5}>周五</option>
                    <option value={6}>周六</option>
                  </select>
                )}
                {reminderKind === 'monthly' && (
                  <input type="number" min={1} max={31} value={reminderDay} onChange={e => setReminderDay(e.target.value)} className="w-24 px-2 py-1 border rounded" />
                )}
                <input value={reminderWebhook} onChange={e => setReminderWebhook(e.target.value)} placeholder="Webhook (optional)"
                  className="w-full px-3 py-2 border border-gray-300 rounded-lg text-sm" />
              </div>
            )}
          </div>
          <label className="inline-flex items-center gap-2 text-sm mb-4"><input type="checkbox" checked={completed} onChange={e => setCompleted(e.target.checked)} /> 已完成</label>
          <div className="flex gap-2 justify-end">
            {type === 'edit' && (
              <button type="button" onClick={onDelete} className="px-4 py-2 rounded-lg text-sm text-red-500 hover:bg-red-50">Delete</button>
            )}
            <button type="button" onClick={onClose} className="px-4 py-2 rounded-lg text-sm text-gray-600 hover:bg-gray-100">Cancel</button>
            <button type="submit" className="px-6 py-2 rounded-lg text-sm bg-blue-500 text-white hover:bg-blue-600">Save</button>
          </div>
        </form>
      </div>
    </div>
  )
}
