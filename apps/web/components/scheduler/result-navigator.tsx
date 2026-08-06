'use client'

import { ChevronLeft, ChevronRight } from 'lucide-react'
import { useSchedulerStore } from '@/store/scheduler'

function formatGap(minutes: number): string {
  const h = Math.floor(minutes / 60)
  const m = minutes % 60
  if (h > 0 && m > 0) return `${h}h ${m}min gap`
  if (h > 0) return `${h}h gap`
  return `${m}min gap`
}

export function ResultNavigator() {
  const { results, activeResultIndex, setActiveResultIndex } = useSchedulerStore()

  const total = results.length
  if (total === 0) return null

  const current = activeResultIndex + 1
  const activeResult = results[activeResultIndex]
  const gap = activeResult?.gap_minutes > 0 ? formatGap(activeResult.gap_minutes) : null

  return (
    <div className="flex items-center gap-2 px-1">
      <button
        disabled={activeResultIndex === 0}
        onClick={() => setActiveResultIndex(activeResultIndex - 1)}
        className="p-1 rounded-md text-muted hover:text-text disabled:opacity-30 transition-colors duration-150"
      >
        <ChevronLeft className="w-4 h-4" />
      </button>

      <div className="flex items-center gap-3 text-sm">
        <span className="text-text font-medium">
          Schedule{' '}
          <span className="font-mono tabular-nums">{current}</span>
          <span className="text-muted"> / </span>
          <span className="font-mono tabular-nums">{total}</span>
        </span>
        {gap && <span className="text-xs font-mono text-muted">{gap}</span>}
      </div>

      <button
        disabled={activeResultIndex === total - 1}
        onClick={() => setActiveResultIndex(activeResultIndex + 1)}
        className="p-1 rounded-md text-muted hover:text-text disabled:opacity-30 transition-colors duration-150"
      >
        <ChevronRight className="w-4 h-4" />
      </button>
    </div>
  )
}
