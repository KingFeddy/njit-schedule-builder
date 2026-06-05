'use client'

import { useState, useEffect, useRef, type KeyboardEvent } from 'react'
import { X, Loader2 } from 'lucide-react'
import { generatePlan, type ParsedDegreeValidated, type SemesterPlan } from '@/lib/api'

interface PreferencesFormProps {
  parsed: ParsedDegreeValidated
  onPlanGenerated: (semesters: SemesterPlan[], graduation: string, warnings: string[]) => void
  onBrowseGer?: () => void
}

const CREDIT_OPTIONS = [
  { label: 'Light', credits: 12 },
  { label: 'Normal', credits: 15 },
  { label: 'Heavy', credits: 18 },
] as const

export function PreferencesForm({ parsed, onPlanGenerated, onBrowseGer }: PreferencesFormProps) {
  const [courses, setCourses] = useState<string[]>([])
  const [creditsPerSemester, setCreditsPerSemester] = useState(15)
  const [inputValue, setInputValue] = useState('')
  const [isLoading, setIsLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const inputRef = useRef<HTMLInputElement>(null)

  useEffect(() => {
    try {
      const saved = localStorage.getItem('njit-dw-preferences')
      if (saved) {
        const prefs = JSON.parse(saved) as { courses: string[]; creditsPerSemester: number }
        // eslint-disable-next-line react-hooks/set-state-in-effect
        setCourses(prefs.courses || [])
        setCreditsPerSemester(prefs.creditsPerSemester || 15)
      }
    } catch { /* ignore */ }
  }, [])

  useEffect(() => {
    try {
      localStorage.setItem('njit-dw-preferences', JSON.stringify({ courses, creditsPerSemester }))
    } catch { /* ignore */ }
  }, [courses, creditsPerSemester])

  function addCourse(raw: string) {
    const code = raw.toUpperCase().replace(/\s+/g, '')
    if (code && !courses.includes(code)) {
      setCourses((prev) => [...prev, code])
    }
  }

  function removeCourse(code: string) {
    setCourses((prev) => prev.filter((c) => c !== code))
  }

  function onKeyDown(e: KeyboardEvent<HTMLInputElement>) {
    if ((e.key === 'Enter' || e.key === ',') && inputValue.trim()) {
      e.preventDefault()
      addCourse(inputValue.trim())
      setInputValue('')
    } else if (e.key === 'Backspace' && !inputValue && courses.length > 0) {
      setCourses((prev) => prev.slice(0, -1))
    }
  }

  async function handleGenerate() {
    if (isLoading) return
    setIsLoading(true)
    setError(null)
    try {
      const res = await generatePlan(parsed, { courses, credits_per_semester: creditsPerSemester })
      try {
        localStorage.setItem(
          'njit-dw-plan',
          JSON.stringify({ semesters: res.semesters, graduation: res.projected_graduation }),
        )
      } catch { /* ignore */ }
      onPlanGenerated(res.semesters, res.projected_graduation, res.warnings)
    } catch (err) {
      const msg = err instanceof Error ? err.message : ''
      if (msg.includes('429')) {
        setError('Too many requests — please wait a moment and try again.')
      } else {
        setError('Failed to generate plan. Please try again.')
      }
    } finally {
      setIsLoading(false)
    }
  }

  return (
    <div className="rounded-xl border border-border bg-surface p-6">
      <p className="text-xs font-medium uppercase tracking-wider text-muted mb-5">Preferences</p>

      <div className="flex flex-col gap-5">
        {/* Electives tag input */}
        <div className="flex flex-col gap-2">
          <p className="text-xs font-medium uppercase tracking-wider text-muted">
            Electives I want to take
          </p>
          <div
            className="min-h-10 flex flex-wrap gap-1.5 p-2 rounded-md border border-border bg-surface-2 cursor-text"
            onClick={() => inputRef.current?.focus()}
          >
            {courses.map((c) => (
              <span
                key={c}
                className="inline-flex items-center gap-1 font-mono text-xs px-2 py-0.5 rounded-md bg-surface border border-border text-text"
              >
                {c}
                <button
                  onClick={(e) => { e.stopPropagation(); removeCourse(c) }}
                  className="text-faint hover:text-text transition-colors duration-150"
                >
                  <X className="w-3 h-3" />
                </button>
              </span>
            ))}
            <input
              ref={inputRef}
              value={inputValue}
              onChange={(e) => setInputValue(e.target.value)}
              onKeyDown={onKeyDown}
              placeholder={courses.length === 0 ? 'e.g. CS375, CS445' : ''}
              className="bg-transparent font-mono text-xs text-text placeholder:text-faint outline-none flex-1 min-w-[8rem]"
            />
          </div>
          {onBrowseGer && (
            <button
              onClick={onBrowseGer}
              className="text-xs text-muted underline underline-offset-2 hover:text-text self-start transition-colors duration-150"
            >
              View available GER Humanities courses →
            </button>
          )}
        </div>

        {/* Credits per semester */}
        <div className="flex flex-col gap-2">
          <p className="text-xs font-medium uppercase tracking-wider text-muted">
            Credits per semester
          </p>
          <div className="flex gap-2">
            {CREDIT_OPTIONS.map(({ label, credits }) => (
              <button
                key={credits}
                onClick={() => setCreditsPerSemester(credits)}
                className={[
                  'flex-1 flex flex-col items-center py-2 rounded-md border text-xs transition-colors duration-150',
                  creditsPerSemester === credits
                    ? 'border-njit-red bg-red-dim text-text'
                    : 'border-border bg-surface-2 text-muted hover:border-border-strong hover:text-text',
                ].join(' ')}
              >
                <span className="font-medium">{label}</span>
                <span className="font-mono text-[10px] text-faint">{credits} cr</span>
              </button>
            ))}
          </div>
        </div>

        {/* Generate button */}
        <div className="flex flex-col gap-2">
          <button
            onClick={handleGenerate}
            disabled={isLoading}
            className="w-full flex items-center justify-center gap-2 py-2.5 rounded-md bg-njit-red text-white text-sm font-medium disabled:opacity-60 hover:opacity-90 transition-opacity duration-150"
          >
            {isLoading ? (
              <>
                <Loader2 className="w-4 h-4 animate-spin" />
                Generating your plan…
              </>
            ) : (
              'Generate My Plan'
            )}
          </button>
          {error && <p className="text-sm text-njit-red">{error}</p>}
        </div>
      </div>
    </div>
  )
}
