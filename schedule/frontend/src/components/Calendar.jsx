import { useMemo } from 'react'

export default function Calendar({ year, month, selDate, busyDates, eventsByDate = {}, onSelect }) {
  const cells = useMemo(() => {
    const first = new Date(year, month - 1, 1).getDay()
    const days = new Date(year, month, 0).getDate()
    const arr = []
    for (let i = 0; i < first; i++) arr.push(null)
    for (let d = 1; d <= days; d++) arr.push(d)
    return arr
  }, [year, month])

  const today = new Date().toISOString().slice(0, 10)
  const daysCn = ['日', '一', '二', '三', '四', '五', '六']

  return (
    <div>
      <div className="grid grid-cols-7 text-center text-sm text-gray-400 mb-1">
        {daysCn.map(d => <div key={d} className="py-1">{d}</div>)}
      </div>
      <div className="grid grid-cols-7 gap-px bg-gray-200 rounded-lg overflow-hidden">
        {cells.map((d, i) => {
          if (d === null) return <div key={'e' + i} className="bg-white min-h-[60px]" />
          const ds = year + '-' + String(month).padStart(2, '0') + '-' + String(d).padStart(2, '0')
          const isToday = ds === today
          const isSel = ds === selDate
          const busy = busyDates.has(ds)
          // compute background and text classes explicitly
          const base = 'h-24 p-1 cursor-pointer transition-colors'
          const bg = isSel ? 'bg-blue-50' : 'bg-white'
          let cls = `${base} ${bg} hover:bg-blue-50`
          const dayEvents = eventsByDate[ds] || []
          const pendingCount = dayEvents.filter(ev => !ev.completed).length
          const doneCount = dayEvents.filter(ev => ev.completed).length
          return (
            <div key={ds} onClick={() => onSelect(ds)} className={cls}>
              <div className={"text-sm font-medium " + (isToday ? 'text-green-600' : 'text-gray-800')}>{d}</div>
              {busy && !isToday && <div className="w-1.5 h-1.5 rounded-full mx-auto mt-1 bg-gray-400" />}
              {/* 显示当天事件计数：待办 / 已完成 */}
              {dayEvents.length > 0 && (
                <div className="mt-1 text-xs">
                  <div className="text-yellow-600">待办：{pendingCount}</div>
                  <div className="text-green-600">已完成：{doneCount}</div>
                </div>
              )}
            </div>
          )
        })}
      </div>
    </div>
  )
}
