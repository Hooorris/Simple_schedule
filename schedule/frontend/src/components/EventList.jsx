export default function EventList({ events, selDate, selMode, selIds, onToggleSel, onEdit, onDelete }) {
  const display = selDate.replace(/-/g, '/')
  return (
    <div className="mt-4">
      <h2 className="text-sm text-gray-500 mb-2">{display}</h2>
      {events.length === 0 ? (
        <p className="text-gray-400 text-sm py-4 text-center">No events</p>
      ) : (
        <div className="space-y-1">
          {events.map(ev => {
            // 使用新的字段：`priority` 与 `completed`
            return (
              <div key={ev.id} className={`flex items-center gap-3 p-3 rounded-lg border border-gray-200 hover:border-blue-300 transition-colors group ${ev.completed ? 'opacity-60 line-through' : ''}`}>
                {selMode && (
                  <input type="checkbox" checked={selIds.has(ev.id)} onChange={() => onToggleSel(ev.id)} className="w-4 h-4" />
                )}
                <div className="flex-1 min-w-0">
                  <div className="font-medium text-sm truncate">{ev.title}</div>
                  <div className="text-xs text-gray-400">优先级: {ev.priority ?? 0}</div>
                  {ev.note ? <div className="text-xs text-gray-500 truncate">{ev.note}</div> : null}
                </div>
                {!selMode && (
                  <div className="flex gap-1 opacity-0 group-hover:opacity-100 transition-opacity">
                    <button onClick={() => onEdit(ev)} className="text-xs text-blue-500 hover:bg-blue-50 px-2 py-1 rounded">Edit</button>
                    <button onClick={() => onDelete(ev.id)} className="text-xs text-red-400 hover:bg-red-50 px-2 py-1 rounded">Del</button>
                  </div>
                )}
              </div>
            )
          })}
        </div>
      )}
    </div>
  )
}
