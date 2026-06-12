import { useState, useEffect } from 'react'

// 弹窗组件：用于创建或编辑事件
export default function EventModal({ type, date, event, onSave, onDelete, onClose }) {
  const [title, setTitle] = useState('')
  const [start, setStart] = useState('')
  const [end, setEnd] = useState('')
  const [note, setNote] = useState('')
  const [costFactor, setCostFactor] = useState(0.0)

  useEffect(() => {
    if (event) {
      setTitle(event.title)
      setStart(event.start_time.slice(0, 16))
      setEnd(event.end_time ? event.end_time.slice(0, 16) : '')
      setNote(event.note || '')
      setCostFactor(event.cost_factor || 0)
    } else if (date) {
      setTitle('')
      setStart(date + 'T09:00')
      setEnd(date + 'T09:30')
      setNote('')
      setCostFactor(0.0)
    }
  }, [event, date])

  const submit = (e) => {
    e.preventDefault()
    if (!title.trim()) return
    onSave({
      title: title.trim(),
      start_time: start + ':00+08:00',
      end_time: end ? end + ':00+08:00' : null,
      note: note.trim(),
      cost_factor: costFactor,
    })
  }

  return (
    <div className="fixed inset-0 bg-black/30 flex items-center justify-center z-50" onClick={onClose}>
      <div className="bg-white rounded-2xl p-6 w-full max-w-sm mx-4 shadow-xl" onClick={e => e.stopPropagation()}>
        <h3 className="text-lg font-semibold mb-4">{type === 'add' ? 'Add Event' : 'Edit Event'}</h3>
        <form onSubmit={submit}>
          <input value={title} onChange={e => setTitle(e.target.value)} placeholder="Title" autoFocus
            className="w-full px-3 py-2 border border-gray-300 rounded-lg mb-3 text-sm" />
          <label className="text-xs text-gray-500">Start Time</label>
          <input type="datetime-local" value={start} onChange={e => setStart(e.target.value)}
            className="w-full px-3 py-2 border border-gray-300 rounded-lg mb-3 text-sm" />
          <label className="text-xs text-gray-500">End Time (optional)</label>
          <input type="datetime-local" value={end} onChange={e => setEnd(e.target.value)}
            className="w-full px-3 py-2 border border-gray-300 rounded-lg mb-3 text-sm" />
          <textarea value={note} onChange={e => setNote(e.target.value)} placeholder="Note (optional)" rows={2}
            className="w-full px-3 py-2 border border-gray-300 rounded-lg mb-3 text-sm resize-none" />
          <label className="text-xs text-gray-500">创意系数</label>
          <input type="number" value={costFactor} onChange={e => setCostFactor(parseFloat(e.target.value) || 0)} step="0.01"
            className="w-full px-3 py-2 border border-gray-300 rounded-lg mb-4 text-sm" />
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
