'use client'

import { useState, useEffect } from 'react'
import { getScraperStatus } from '@/lib/api'

const POLL_INTERVAL_MS = 3 * 60 * 1000  // 3 minutes
const STALE_THRESHOLD_MS = 45 * 60 * 1000  // 45 minutes

export function useScraperStatus() {
  const [lastScrape, setLastScrape] = useState<Date | null>(null)
  const [isStale, setIsStale] = useState(false)

  async function checkStatus() {
    try {
      const data = await getScraperStatus()
      if (data.last_scrape) {
        const scrapeTime = new Date(data.last_scrape)
        setLastScrape(scrapeTime)
        setIsStale(Date.now() - scrapeTime.getTime() > STALE_THRESHOLD_MS)
      }
    } catch {
      setIsStale(true)
    }
  }

  useEffect(() => {
    // eslint-disable-next-line react-hooks/set-state-in-effect
    checkStatus()
    const interval = setInterval(checkStatus, POLL_INTERVAL_MS)
    return () => clearInterval(interval)
  }, [])

  return { lastScrape, isStale }
}
