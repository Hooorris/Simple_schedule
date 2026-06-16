import { useState, useEffect, useCallback } from 'react'
import Header from './components/Header'
import Calendar from './components/Calendar'
import EventList from './components/EventList'
import EventModal from './components/EventModal'

// 前端与后端交互的基础 API 路径
const API = '/api/v1/events'

export default function App() {
  const [year, setYear] = useState(new Date().getFullYear())
  const [month, setMonth] = useState(new Date().getMonth() + 1)
  const [selDate, setSelDate] = useState(new Date().toISOString().slice(0, 10))
  const [events, setEvents] = useState([])
  const [modal, setModal] = useState(null)
  const [selMode, setSelMode] = useState(false)
  const [selIds, setSelIds] = useState(new Set())

  // 按月拉取事件，优先使用兼容的 API，失败则回退到 db-events
  const fetchEvents = useCallback(async () => {
    const y = year
    const m = String(month).padStart(2, '0')
    const days = new Date(year, month, 0).getDate()
    const d = String(days).padStart(2, '0')
    try {
      const res = await fetch(API + '?start=' + y + '-' + m + '-01&end=' + y + '-' + m + '-' + d)
      if (res.ok) { setEvents(await res.json()); return }
    } catch(e) { /* fetch failed, try fallback */ }
    // Fallback: try db-events endpoint
    try {
      const res = await fetch('/api/v1/db-events?start=' + y + '-' + m + '-01&end=' + y + '-' + m + '-' + d)
      if (res.ok) { setEvents(await res.json()); return }
    } catch(e) {}
    setEvents([])
  }, [year, month])

  useEffect(() => { fetchEvents() }, [fetchEvents])

  const eventDisplayDate = (event) => event.display_date || event.date
  const dayEvents = events.filter(e => eventDisplayDate(e) === selDate)
  // 未完成的放前面，已完成的靠后；同一状态下按优先级降序
  const sortedDayEvents = [...dayEvents].sort((a, b) => {
    const aDone = a.completed ? 1 : 0
    const bDone = b.completed ? 1 : 0
    if (aDone !== bDone) return aDone - bDone
    return (b.priority || 0) - (a.priority || 0)
  })
  const busyDates = new Set(events.map(e => eventDisplayDate(e)))
  // 将事件按日期分组并按优先级排序，供 Calendar 渲染每日缩略
  const eventsByDate = events.reduce((acc, e) => {
    const displayDate = eventDisplayDate(e)
    if (!displayDate) return acc
    acc[displayDate] = acc[displayDate] || []
    acc[displayDate].push(e)
    return acc
  }, {})
  Object.keys(eventsByDate).forEach(d => {
    eventsByDate[d].sort((a, b) => (b.priority || 0) - (a.priority || 0))
  })

  // 创建事件并刷新列表
  const add = async (data) => {
    const r = await fetch(API, { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(data) })
    if (!r.ok) throw new Error((await r.json()).detail || 'Failed')
    const created = await r.json()
    // 如果有 reminder 配置，创建 reminder
    if (data.reminder) {
      const rem = Object.assign({}, data.reminder, { event_id: created.id })
      await fetch('/api/v1/reminders', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(rem) })
    }
    await fetchEvents()
  }

  // 更新事件
  const upd = async (id, data) => {
    const r = await fetch(API + '/' + id, { method: 'PUT', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(data) })
    if (!r.ok) throw new Error((await r.json()).detail || 'Failed')
    await fetchEvents()
  }

  // 删除事件
  const del = async (id) => {
    await fetch(API + '/' + id, { method: 'DELETE' })
    await fetchEvents()
  }

  // 批量删除已选事件
  const batchDel = async () => {
    if (selIds.size === 0) return
    await fetch(API, { method: 'DELETE', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ ids: [...selIds] }) })
    setSelIds(new Set()); setSelMode(false)
    await fetchEvents()
  }

  // 切换选中状态（用于多选删除）
  const toggleSel = (id) => {
    const s = new Set(selIds)
    s.has(id) ? s.delete(id) : s.add(id)
    setSelIds(s)
  }

  return (
    <div className="max-w-2xl mx-auto px-4 py-6">
      <Header year={year} month={month}
        onPrev={() => { const d = new Date(year, month - 2, 1); setYear(d.getFullYear()); setMonth(d.getMonth() + 1) }}
        onNext={() => { const d = new Date(year, month, 1); setYear(d.getFullYear()); setMonth(d.getMonth() + 1) }}
        onToday={() => { const t = new Date(); setYear(t.getFullYear()); setMonth(t.getMonth() + 1); setSelDate(t.toISOString().slice(0, 10)) }}
        selMode={selMode} onToggleSel={() => { setSelMode(!selMode); setSelIds(new Set()) }} />

      <Calendar year={year} month={month} selDate={selDate} busyDates={busyDates}
        eventsByDate={eventsByDate}
        onSelect={d => { setSelDate(d); setSelMode(false); setSelIds(new Set()) }} />

      <EventList events={sortedDayEvents} selDate={selDate}
        selMode={selMode} selIds={selIds} onToggleSel={toggleSel}
        onEdit={e => setModal({ type: 'edit', event: e })}
        onDelete={id => { if (confirm('Delete?')) del(id) }}
        onToggleComplete={async (e) => { try { await upd(e.id, { completed: !e.completed }); } catch(err){ alert(err.message) } }} />

      {selMode && selIds.size > 0 && (
        <div className="fixed bottom-0 left-0 right-0 p-4 bg-white border-t shadow-lg flex justify-center z-40">
          <button onClick={() => { if (confirm('Delete ' + selIds.size + ' events?')) batchDel() }}
            className="bg-red-500 text-white px-8 py-3 rounded-lg text-lg font-medium">
            Delete Selected ({selIds.size})
          </button>
        </div>
      )}

      <button onClick={() => setModal({ type: 'add', date: selDate })}
        className="fixed bottom-6 right-6 w-14 h-14 bg-blue-500 text-white rounded-full text-3xl shadow-lg hover:bg-blue-600 flex items-center justify-center z-50">+</button>

      {modal && <EventModal {...modal}
        onSave={async data => { try { if (modal.type === 'add') await add(data); else await upd(modal.event.id, data); setModal(null) } catch (e) { alert(e.message) }}}
        onDelete={async () => { if (confirm('Delete?')) { await del(modal.event.id); setModal(null) }}}
        onClose={() => setModal(null)} />}
    </div>
  )
}
