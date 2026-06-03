'use client'

import { Loader2 } from 'lucide-react'
import { useSchedulerStore } from '@/store/scheduler'
import { solveShedule } from '@/lib/api'
import { CourseSelector } from '@/components/scheduler/course-selector'
import { CommuterToggles } from '@/components/scheduler/commuter-toggles'
import { ResultNavigator } from '@/components/scheduler/result-navigator'
import { ScheduleGrid } from '@/components/calendar/schedule-grid'

export default function SchedulerPage() {
  const {
    selectedCourses,
    term,
    commuterOptions,
    professorPreferences,
    results,
    activeResultIndex,
    isLoading,
    solveWarnings,
    setLoading,
    setResults,
    setError,
  } = useSchedulerStore()

  async function handleSolve() {
    if (isLoading || selectedCourses.length === 0) return
    setLoading(true)
    setError(null)
    try {
      const res = await solveShedule({
        course_codes: selectedCourses,
        term,
        blocked_days: commuterOptions.blocked_days,
        earliest_start: commuterOptions.earliest_start || '07:00',
        latest_end: commuterOptions.latest_end || '21:00',
        minimize_gaps: commuterOptions.minimize_gaps,
        professor_preferences: Object.fromEntries(
          Object.entries(professorPreferences).filter(([, v]) => v.length > 0),
        ),
        top_n: 50,
      })
      setResults(res.results, res.warnings)
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to solve schedule')
    } finally {
      setLoading(false)
    }
  }

  const activeResult = results[activeResultIndex] ?? null

  return (
    <div className="flex h-screen overflow-hidden">
      {/* Left panel */}
      <div className="w-72 flex-shrink-0 border-r border-border flex flex-col gap-6 p-5 overflow-y-auto">
        <div>
          <p className="text-xs font-medium uppercase tracking-wider text-muted mb-3">
            Add Courses
          </p>
          <CourseSelector />
        </div>

        <div className="border-t border-border pt-5">
          <CommuterToggles />
        </div>

        <div className="border-t border-border pt-5 mt-auto flex flex-col gap-3">
          <button
            onClick={handleSolve}
            disabled={isLoading || selectedCourses.length === 0}
            className="w-full flex items-center justify-center gap-2 py-2 rounded-lg text-sm font-medium bg-njit-red text-white hover:opacity-90 disabled:opacity-40 transition-opacity duration-150"
          >
            {isLoading ? (
              <>
                <Loader2 className="w-4 h-4 animate-spin" />
                Solving…
              </>
            ) : (
              'Solve'
            )}
          </button>

          {solveWarnings.length > 0 && (
            <ul className="flex flex-col gap-1.5">
              {solveWarnings.map((w, i) => (
                <li
                  key={i}
                  className="text-xs text-yellow px-2 py-1 rounded bg-surface-2 border border-border"
                >
                  {w}
                </li>
              ))}
            </ul>
          )}
        </div>
      </div>

      {/* Right panel */}
      <div className="flex-1 flex flex-col p-5 gap-4 min-w-0">
        {results.length > 0 && <ResultNavigator />}
        <ScheduleGrid result={activeResult} />
      </div>
    </div>
  )
}
