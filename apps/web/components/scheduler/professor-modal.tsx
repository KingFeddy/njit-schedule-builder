'use client'

import { useEffect, useState } from 'react'
import { X, Star, Zap } from 'lucide-react'
import { getProfessor, type ProfessorResponse } from '@/lib/api'
import { VibeCheckPill } from '@/components/ui/vibe-check-pill'

interface ProfessorModalProps {
  professorName: string
  courseCode: string
  onClose: () => void
}

function formatName(raw: string): string {
  if (!raw.includes(',')) return raw
  const [last, first = ''] = raw.split(', ')
  return `${first} ${last}`.trim()
}

function ratingColor(score: number): string {
  if (score >= 4.0) return 'text-green'
  if (score >= 2.5) return 'text-yellow'
  return 'text-njit-red'
}

function difficultyColor(score: number): string {
  if (score <= 2.5) return 'text-green'
  if (score <= 3.9) return 'text-yellow'
  return 'text-njit-red'
}

export function ProfessorModal({ professorName, courseCode, onClose }: ProfessorModalProps) {
  const [data, setData] = useState<ProfessorResponse | null | 'loading'>('loading')

  useEffect(() => {
    getProfessor(professorName).then(setData)
  }, [professorName])

  useEffect(() => {
    function onKey(e: KeyboardEvent) {
      if (e.key === 'Escape') onClose()
    }
    document.addEventListener('keydown', onKey)
    return () => document.removeEventListener('keydown', onKey)
  }, [onClose])

  const loading = data === 'loading'
  const prof = loading ? null : data

  return (
    <div
      className="fixed inset-0 z-50 flex items-center justify-center p-4"
      style={{ background: 'rgba(0,0,0,0.7)' }}
      onClick={onClose}
    >
      <div
        className="relative w-full max-w-lg rounded-xl border border-border bg-surface overflow-y-auto max-h-[85vh]"
        onClick={(e) => e.stopPropagation()}
      >
        <button
          onClick={onClose}
          className="absolute top-4 right-4 text-faint hover:text-text transition-colors duration-150"
        >
          <X className="w-4 h-4" />
        </button>

        <div className="p-6 space-y-5">
          {/* Header */}
          <div>
            {loading ? (
              <div className="h-3 w-8 rounded bg-surface-2 animate-pulse mb-2" />
            ) : (
              <p className="text-xs font-medium uppercase tracking-wider text-muted mb-1">
                {prof?.department ?? 'Unknown'}
              </p>
            )}
            <p className="text-xl font-semibold tracking-tight">{formatName(professorName)}</p>
          </div>

          {/* Ratings */}
          <div className="flex gap-8">
            <div>
              <p className="text-xs font-medium uppercase tracking-wider text-muted mb-1">Rating</p>
              {loading ? (
                <div className="h-6 w-20 rounded bg-surface-2 animate-pulse" />
              ) : (
                <p className={`font-mono text-xl ${ratingColor(prof?.rmp_score ?? 0)}`}>
                  ★{' '}
                  {prof?.rmp_score != null ? (
                    <>
                      {prof.rmp_score.toFixed(1)}
                      <span className="text-muted text-sm"> / 5.0</span>
                    </>
                  ) : (
                    'N/A'
                  )}
                </p>
              )}
            </div>
            <div>
              <p className="text-xs font-medium uppercase tracking-wider text-muted mb-1">
                Difficulty
              </p>
              {loading ? (
                <div className="h-6 w-20 rounded bg-surface-2 animate-pulse" />
              ) : (
                <p className={`font-mono text-xl ${difficultyColor(prof?.rmp_difficulty ?? 0)}`}>
                  ⚡{' '}
                  {prof?.rmp_difficulty != null ? (
                    <>
                      {prof.rmp_difficulty.toFixed(1)}
                      <span className="text-muted text-sm"> / 5.0</span>
                    </>
                  ) : (
                    'N/A'
                  )}
                </p>
              )}
            </div>
          </div>

          {/* Meta */}
          {!loading && (prof?.rmp_would_take_again != null || prof?.rmp_num_ratings != null) && (
            <p className="text-xs text-muted">
              {prof.rmp_would_take_again != null && (
                <span>Would take again: {prof.rmp_would_take_again}%&nbsp;&nbsp;</span>
              )}
              {prof.rmp_num_ratings != null && (
                <span>Based on {prof.rmp_num_ratings} ratings</span>
              )}
            </p>
          )}

          {/* Tags */}
          {!loading && prof?.rmp_tags && prof.rmp_tags.length > 0 && (
            <div className="flex flex-wrap gap-1.5">
              {prof.rmp_tags.map((tag) => (
                <VibeCheckPill key={tag} tag={tag} />
              ))}
            </div>
          )}

          {/* About */}
          <div className="rounded-xl border border-border bg-surface-2 p-4 space-y-2">
            <p className="text-xs font-medium uppercase tracking-wider text-muted">
              About this professor
            </p>
            <p className="text-sm text-text">
              No summary available — check RMP directly for reviews.
            </p>
          </div>

          {/* Tips */}
          <div className="rounded-xl border border-border bg-surface-2 p-4 space-y-2">
            <p className="text-xs font-medium uppercase tracking-wider text-muted">
              Tips for {courseCode}
            </p>
            <p className="text-sm text-text">
              No tips yet — check back after registration opens.
            </p>
          </div>
        </div>
      </div>
    </div>
  )
}
