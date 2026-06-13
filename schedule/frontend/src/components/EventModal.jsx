import { useState, useEffect } from 'react'

// 弹窗组件：用于创建或编辑事件
export default function EventModal({ type, date, event, onSave, onDelete, onClose }) {
  const [title, setTitle] = useState('')
  const [date, setDate] = useState('')
  const [note, setNote] = useState('')
  const [priority, setPriority] = useState(0)
  const [completed, setCompleted] = useState(false)

  useEffect(() => {
    if (event) {
      setTitle(event.title)
      setDate(event.date)
      setNote(event.note || '')
      setPriority(event.priority || 0)
      setCompleted(Boolean(event.completed))
    } else if (date) {
      setTitle('')
      setDate(date)
      setNote('')
      setPriority(0)
      setCompleted(false)
    }
  }, [event, date])

  const submit = (e) => {
    e.preventDefault()
    if (!title.trim()) return
    onSave({
      title: title.trim(),
      date: date,
      priority: Number(priority) || 0,
      completed: Boolean(completed),
      note: note.trim(),
    })
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
