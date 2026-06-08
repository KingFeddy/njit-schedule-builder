import { create } from 'zustand'
import { persist, createJSONStorage } from 'zustand/middleware'
import type { ProfessorResponse, ScheduleResult } from '@/lib/api'

export interface CommuterOptions {
  earliest_start: string
  latest_end: string
  minimize_gaps: boolean
  compact_week: boolean
}

const defaultCommuterOptions: CommuterOptions = {
  earliest_start: '07:00',
  latest_end: '21:00',
  minimize_gaps: false,
  compact_week: false,
}

interface SchedulerState {
  // persisted
  selectedCourses: string[]
  term: string
  commuterOptions: CommuterOptions
  professorPreferences: Record<string, string[]>
  activeResultIndex: number

  // not persisted
  results: ScheduleResult[]
  isLoading: boolean
  error: string | null
  solveWarnings: string[]
  professorCache: Record<string, ProfessorResponse | null>
  professorsByCourse: Record<string, string[]>

  // actions
  addCourse: (code: string) => void
  removeCourse: (code: string) => void
  setTerm: (term: string) => void
  setCommuterOptions: (opts: Partial<CommuterOptions>) => void
  setProfessorPreferences: (code: string, profs: string[]) => void
  setActiveResultIndex: (i: number) => void
  setResults: (results: ScheduleResult[], warnings: string[]) => void
  setLoading: (loading: boolean) => void
  setError: (error: string | null) => void
  setProfessorCache: (entries: Record<string, ProfessorResponse | null>) => void
  setProfessorsByCourse: (code: string, profs: string[]) => void
}

const safeStorage = {
  getItem: (key: string) => {
    try { return localStorage.getItem(key) } catch { return null }
  },
  setItem: (key: string, value: string) => {
    try { localStorage.setItem(key, value) } catch { /* Safari private mode */ }
  },
  removeItem: (key: string) => {
    try { localStorage.removeItem(key) } catch { /* Safari private mode */ }
  },
}

export const useSchedulerStore = create<SchedulerState>()(
  persist(
    (set) => ({
      // persisted defaults
      selectedCourses: [],
      term: '202690',
      commuterOptions: defaultCommuterOptions,
      professorPreferences: {},
      activeResultIndex: 0,

      // not persisted
      results: [],
      isLoading: false,
      error: null,
      solveWarnings: [],
      professorCache: {},
      professorsByCourse: {},

      // actions
      addCourse: (code) =>
        set((s) => ({
          selectedCourses: s.selectedCourses.includes(code)
            ? s.selectedCourses
            : [...s.selectedCourses, code],
        })),

      removeCourse: (code) =>
        set((s) => ({
          selectedCourses: s.selectedCourses.filter((c) => c !== code),
          professorPreferences: Object.fromEntries(
            Object.entries(s.professorPreferences).filter(([k]) => k !== code),
          ),
        })),

      setTerm: (term) => set({ term }),

      setCommuterOptions: (opts) =>
        set((s) => ({ commuterOptions: { ...s.commuterOptions, ...opts } })),

      setProfessorPreferences: (code, profs) =>
        set((s) => ({
          professorPreferences: profs.length
            ? { ...s.professorPreferences, [code]: profs }
            : Object.fromEntries(
                Object.entries(s.professorPreferences).filter(([k]) => k !== code),
              ),
        })),

      setActiveResultIndex: (i) => set({ activeResultIndex: i }),

      setResults: (results, warnings) =>
        set({ results, solveWarnings: warnings, activeResultIndex: 0, error: null }),

      setLoading: (isLoading) => set({ isLoading }),

      setError: (error) => set({ error }),

      setProfessorCache: (entries) =>
        set((s) => ({ professorCache: { ...s.professorCache, ...entries } })),

      setProfessorsByCourse: (code, profs) =>
        set((s) => ({ professorsByCourse: { ...s.professorsByCourse, [code]: profs } })),
    }),
    {
      name: 'njit-scheduler',
      storage: createJSONStorage(() => safeStorage),
      version: 2,
      partialize: (s) => ({
        selectedCourses: s.selectedCourses,
        term: s.term,
        commuterOptions: s.commuterOptions,
        professorPreferences: s.professorPreferences,
        activeResultIndex: s.activeResultIndex,
      }),
      migrate(state, version) {
        if (version < 2) {
          return {
            ...(state as Partial<SchedulerState>),
            commuterOptions: defaultCommuterOptions,
          }
        }
        return state as SchedulerState
      },
    },
  ),
)
