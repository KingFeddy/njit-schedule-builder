'use client'

import { useState } from 'react'
import { Copy, Check } from 'lucide-react'
import type { ScheduleResult, SectionSlot } from '@/lib/api'
import { SeatStatus } from '@/components/ui/seat-status'
import { formatAgo } from '@/lib/utils'

// Copied verbatim from professor-modal.tsx's formatName rather than shared —
// keeps this component independently shippable with no cross-file coupling.
function formatName(raw: string): string {
  if (!raw.includes(',')) return raw
  const [last, first = ''] = raw.split(', ')
  return `${first} ${last}`.trim()
}

export function isAsyncSection(s: SectionSlot): boolean {
  return !s.days || !s.start_time || !s.end_time
}

function formatMeeting(s: SectionSlot): string {
  return `${s.days} ${s.start_time}–${s.end_time}`
}

export function SectionList({ result }: { result: ScheduleResult }) {
  const [copied, setCopied] = useState(false)
  const crns = result.sections.map((s) => s.crn)

  async function copyCrns() {
    try {
      await navigator.clipboard.writeText(crns.join(', '))
      setCopied(true)
      setTimeout(() => setCopied(false), 2000)
    } catch {
      /* clipboard unavailable — CRNs below are select-all for manual copy */
    }
  }

  // Oldest-wins: the footer must report the STALEST section's data age, not
  // the freshest — a "just updated" footer over data that's actually 40
  // minutes old would be the worst kind of silent failure this list exists
  // to prevent. Nulls filtered first; footer omitted entirely if none survive.
  const scrapedTimes = result.sections
    .map((s) => s.scraped_at)
    .filter((t): t is string => t !== null)
  const oldestScrape =
    scrapedTimes.length > 0
      ? scrapedTimes.reduce((oldest, t) => (t < oldest ? t : oldest))
      : null

  return (
    <div className="w-full xl:w-80 flex-shrink-0 flex flex-col rounded-xl border border-border bg-surface overflow-hidden max-h-64 xl:max-h-none">
      <div className="flex-shrink-0 flex items-center justify-between px-4 py-2.5 border-b border-border bg-surface-2">
        <p className="text-xs font-medium uppercase tracking-wider text-muted">Sections</p>
        <button
          onClick={copyCrns}
          className="inline-flex items-center gap-1.5 px-2 py-1 rounded-md text-xs font-medium border border-border text-muted hover:border-border-strong hover:text-text transition-colors duration-150"
        >
          {copied ? <Check className="w-3 h-3 text-green" /> : <Copy className="w-3 h-3" />}
          {copied ? 'Copied' : 'Copy CRNs'}
        </button>
      </div>

      <ul className="flex-1 overflow-y-auto divide-y divide-border">
        {result.sections.map((s) => (
          <li key={s.crn} className="px-4 py-3 flex flex-col gap-1">
            <div className="flex items-center justify-between gap-2">
              <span className="font-mono text-sm text-text">
                {s.course_code}
                {s.section_number && <span className="text-muted"> §{s.section_number}</span>}
              </span>
              <SeatStatus open={s.open_seats} total={s.total_seats} />
            </div>
            <p className="text-xs text-muted truncate">
              {s.professor_name ? formatName(s.professor_name) : 'Staff / TBA'}
            </p>
            <div className="flex items-center justify-between gap-2">
              {isAsyncSection(s) ? (
                <span className="text-xs font-mono text-yellow">Online / async</span>
              ) : (
                <span className="font-mono text-xs text-muted truncate">
                  {formatMeeting(s)}
                  {s.location ? ` · ${s.location}` : ''}
                </span>
              )}
              <span className="font-mono text-xs text-text select-all flex-shrink-0">
                CRN {s.crn}
              </span>
            </div>
          </li>
        ))}
      </ul>

      {oldestScrape && (
        <p className="flex-shrink-0 px-4 py-2 border-t border-border text-xs text-muted">
          Seats updated {formatAgo(oldestScrape)}
        </p>
      )}
    </div>
  )
}
