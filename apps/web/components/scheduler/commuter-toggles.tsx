'use client'

import { useSchedulerStore } from '@/store/scheduler'

export function CommuterToggles() {
  const { commuterOptions, setCommuterOptions } = useSchedulerStore()
  const { compact_week } = commuterOptions

  return (
    <div className="flex flex-col gap-4">
      <p className="text-xs font-medium uppercase tracking-wider text-muted">Commuter Mode</p>

      {/* Compact Week toggle */}
      <div
        className="flex items-center justify-between cursor-pointer group"
        onClick={() => setCommuterOptions({ compact_week: !compact_week })}
      >
        <div>
          <p className="text-sm font-medium text-text">Compact Week</p>
          <p className="text-xs text-muted">Prefer schedules with fewer campus days</p>
        </div>
        <div
          className="relative flex-shrink-0 w-9 h-5 rounded-full border transition-colors duration-150"
          style={
            compact_week
              ? { background: 'var(--njit-red)', borderColor: 'var(--njit-red)' }
              : { background: 'var(--surface-2)', borderColor: 'var(--border)' }
          }
        >
          <span
            className="absolute top-0.5 w-4 h-4 rounded-full bg-text transition-transform duration-150"
            style={{ transform: compact_week ? 'translateX(16px)' : 'translateX(2px)' }}
          />
        </div>
      </div>
    </div>
  )
}
