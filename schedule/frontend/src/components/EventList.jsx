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
            const st = ev.start_time.slice(11, 16)
            const et = ev.end_time ? ev.end_time.slice(11, 16) : ''
            const t = et ? st + '~' + et : st
            return (
              <div key={ev.id} className="flex items-center gap-3 p-3 rounded-lg border border-gray-200 hover:border-blue-300 transition-colors group">
                {selMode && (
                  <input type="checkbox" checked={selIds.has(ev.id)} onChange={() => onToggleSel(ev.id)} className="w-4 h-4" />
                )}
                <div className="flex-1 min-w-0">
                  <div className="font-medium text-sm truncate">{ev.title}</div>
                  <div className="text-xs text-gray-400">{t}</div>
                  {ev.cost_factor ? <div className="text-xs text-blue-400">系数: {ev.cost_factor}</div> : null}
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
