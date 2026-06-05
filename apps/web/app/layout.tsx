import type { Metadata } from 'next'
import { Geist, Geist_Mono } from 'next/font/google'
import { SidebarNav } from '@/components/layout/sidebar-nav'
import './globals.css'

const geistSans = Geist({
  variable: '--font-geist-sans',
  subsets: ['latin'],
})

const geistMono = Geist_Mono({
  variable: '--font-geist-mono',
  subsets: ['latin'],
})

export const metadata: Metadata = {
  title: 'NJIT Schedule Builder',
  description: 'Conflict-free schedule generation for NJIT students.',
}

export default function RootLayout({
  children,
}: Readonly<{ children: React.ReactNode }>) {
  return (
    <html
      lang="en"
      className={`dark ${geistSans.variable} ${geistMono.variable}`}
    >
      <body className="bg-bg text-text antialiased">
        <div className="flex h-screen overflow-hidden">
          <SidebarNav />
          <div className="flex-1 flex flex-col overflow-y-auto">
            {children}
          </div>
        </div>
      </body>
    </html>
  )
}
