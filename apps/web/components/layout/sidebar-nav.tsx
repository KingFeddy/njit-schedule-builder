'use client'

import Link from 'next/link'
import { usePathname } from 'next/navigation'
import { BookOpen, CalendarDays, Map } from 'lucide-react'

const NAV_ITEMS = [
  { label: 'Courses',   href: '/courses',   icon: BookOpen },
  { label: 'Scheduler', href: '/scheduler', icon: CalendarDays },
  { label: 'Planner',   href: '/planner',   icon: Map },
] as const

export function SidebarNav() {
  const pathname = usePathname()

  return (
    <aside className="w-60 flex-shrink-0 border-r border-border h-full flex flex-col py-6 px-3">
      {/* Logo */}
      <Link href="/" className="px-3 mb-8 flex items-center gap-2">
        <span className="font-mono font-bold text-sm text-njit-red">NJIT</span>
        <span className="font-mono text-sm text-muted">Schedule</span>
      </Link>

      {/* Nav */}
      <nav className="flex flex-col gap-0.5">
        {NAV_ITEMS.map(({ label, href, icon: Icon }) => {
          const active = pathname === href || pathname.startsWith(`${href}/`)
          return (
            <Link
              key={href}
              href={href}
              className={[
                'flex items-center gap-2.5 px-3 py-1.5 rounded-md text-sm transition-colors duration-150',
                active
                  ? 'bg-surface-2 text-text border-l-2 border-njit-red pl-[10px]'
                  : 'text-muted hover:bg-surface-2 hover:text-text',
              ].join(' ')}
            >
              <Icon className="w-4 h-4 flex-shrink-0" />
              {label}
            </Link>
          )
        })}
      </nav>
    </aside>
  )
}
