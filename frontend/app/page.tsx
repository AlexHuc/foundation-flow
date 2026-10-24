'use client'

import Link from 'next/link'
import { useState, useEffect } from 'react'
import { api } from '@/lib/api'

export default function Home() {
  const [stocks, setStocks] = useState<string[]>([])
  const [searchQuery, setSearchQuery] = useState('')
  const [filteredStocks, setFilteredStocks] = useState<string[]>([])
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    const fetchStocks = async () => {
      try {
        const data = await api.get('/api/stocks')
        setStocks(data)
        setFilteredStocks(data.slice(0, 10))
      } catch (error) {
        console.error('Error fetching stocks:', error)
      } finally {
        setLoading(false)
      }
    }

    fetchStocks()
  }, [])

  const handleSearch = async (query: string) => {
    setSearchQuery(query)
    if (!query) {
      setFilteredStocks(stocks.slice(0, 10))
      return
    }

    try {
      const results = await api.get('/api/stocks/search', { q: query })
      setFilteredStocks(results)
    } catch (error) {
      console.error('Search error:', error)
      setFilteredStocks([])
    }
  }

  return (
    <div className="space-y-8">
      <section className="text-center py-12">
        <h1 className="text-5xl font-bold mb-4 bg-gradient-to-r from-blue-400 to-cyan-400 bg-clip-text text-transparent">
          Stock Analytics Platform
        </h1>
        <p className="text-xl text-slate-400 mb-8">
          Analyze stocks with real-time data and technical indicators
        </p>
      </section>

      <section className="bg-slate-900/50 rounded-lg border border-slate-700 p-8">
        <h2 className="text-2xl font-bold mb-6">Search Stocks</h2>
        <div className="relative">
          <input
            type="text"
            placeholder="Search ticker (e.g., AAPL)"
            value={searchQuery}
            onChange={(e) => handleSearch(e.target.value)}
            className="w-full bg-slate-800 border border-slate-600 rounded-lg px-4 py-3 focus:outline-none focus:border-blue-500 focus:ring-1 focus:ring-blue-500"
          />
        </div>
      </section>

      <section className="bg-slate-900/50 rounded-lg border border-slate-700 p-8">
        <h2 className="text-2xl font-bold mb-6">Available Stocks</h2>
        
        {loading ? (
          <div className="text-center text-slate-400">Loading stocks...</div>
        ) : (
          <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-4 gap-4">
            {filteredStocks.map((ticker) => (
              <Link
                key={ticker}
                href={`/stock/${ticker}`}
                className="group bg-slate-800/50 hover:bg-slate-800 border border-slate-700 rounded-lg p-4 transition cursor-pointer"
              >
                <div className="text-xl font-bold group-hover:text-blue-400 transition">
                  {ticker}
                </div>
                <div className="text-sm text-slate-400">View details →</div>
              </Link>
            ))}
          </div>
        )}
      </section>
    </div>
  )
}
