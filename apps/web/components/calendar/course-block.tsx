import type { SectionSlot } from '@/lib/api'

const PX_PER_HOUR = 48
const START_HOUR = 7

// Six deterministic dark palette colors — picked by hashing the course code
const PALETTE = [
  '#1E3A5F', // deep navy
  '#1A3A2A', // deep forest
  '#3A1A2A', // deep plum
  '#3A2A1A', // deep bronze
  '#1A2A3A', // deep slate
  '#2A1A3A', // deep violet
]

function hashCode(str: string): number {
  let h = 0
  for (let i = 0; i < str.length; i++) h = (Math.imul(31, h) + str.charCodeAt(i)) | 0
  return Math.abs(h)
}

function courseColor(code: string): string {
  return PALETTE[hashCode(code) % PALETTE.length]
}

function timeToMinutes(timeStr: string): number {
  const ampm = /(\d+):(\d+)\s*(AM|PM)/i.exec(timeStr)
  if (ampm) {
    let h = parseInt(ampm[1], 10)
    const m = parseInt(ampm[2], 10)
    if (ampm[3].toUpperCase() === 'PM' && h !== 12) h += 12
    if (ampm[3].toUpperCase() === 'AM' && h === 12) h = 0
    return h * 60 + m
  }
  const parts = timeStr.split(':')
  return parseInt(parts[0], 10) * 60 + parseInt(parts[1], 10)
}

function minutesToPx(totalMinutes: number): number {
  return ((totalMinutes - START_HOUR * 60) / 60) * PX_PER_HOUR
}

interface CourseBlockProps {
  slot: SectionSlot
  hasConflict?: boolean
}

export function CourseBlock({ slot, hasConflict = false }: CourseBlockProps) {
  if (!slot.start_time || !slot.end_time) return null

  const startMin = timeToMinutes(slot.start_time)
  const endMin = timeToMinutes(slot.end_time)
  const topPx = minutesToPx(startMin)
  const heightPx = ((endMin - startMin) / 60) * PX_PER_HOUR
  const bg = courseColor(slot.course_code)

  return (
    <div
      className={[
        'absolute inset-x-0.5 rounded-md px-2 py-1 overflow-hidden',
        hasConflict ? 'opacity-50 ring-2 ring-njit-red' : '',
      ]
        .join(' ')
        .trim()}
      style={{ top: topPx, height: heightPx, backgroundColor: bg, border: `1px solid ${bg}cc` }}
    >
      <p className="font-mono font-bold text-xs text-text truncate">{slot.course_code}</p>
      {slot.location && (
        <p className="font-mono text-[10px] text-muted truncate">{slot.location}</p>
      )}
    </div>
  )
}
