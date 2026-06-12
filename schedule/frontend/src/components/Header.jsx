export default function Header({ year, month, onPrev, onNext, onToday, selMode, onToggleSel }) {
  return (
    <div className="flex items-center justify-between mb-4">
      <div className="flex items-center gap-3">
        <button onClick={onPrev} className="px-3 py-1.5 rounded-lg border border-gray-300 hover:bg-gray-100 text-lg">&lsaquo;</button>
        <h1 className="text-xl font-semibold">{year}年{month}月</h1>
        <button onClick={onNext} className="px-3 py-1.5 rounded-lg border border-gray-300 hover:bg-gray-100 text-lg">&rsaquo;</button>
      </div>
      <div className="flex gap-2">
        <button onClick={onToday} className="px-4 py-1.5 rounded-lg bg-blue-500 text-white text-sm hover:bg-blue-600">今天</button>
        <button onClick={onToggleSel}
          className={'px-3 py-1.5 rounded-lg border text-sm ' + (selMode ? 'bg-blue-100 border-blue-400 text-blue-600' : 'border-gray-300 hover:bg-gray-100')}>
          {selMode ? '退出多选' : '多选'}
        </button>
      </div>
    </div>
  )
}
