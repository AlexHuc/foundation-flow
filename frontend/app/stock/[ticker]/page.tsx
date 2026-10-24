'use client'

import { useEffect, useState } from 'react'
import { api } from '@/lib/api'
import PriceChart from '@/components/PriceChart'
import MetricsPanel from '@/components/MetricsPanel'

interface StockDetailProps {
  params: {
    ticker: string
  }
}

export default function StockDetail({ params }: StockDetailProps) {
  const { ticker } = params
  const [metrics, setMetrics] = useState<any>(null)
  const [prices, setPrices] = useState<any[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    const fetchStockData = async () => {
      try {
        setLoading(true)
        const [metricsData, pricesData] = await Promise.all([
          api.get(`/api/stocks/${ticker}`),
          api.get(`/api/stocks/${ticker}/prices`, { days: 90 }),
        ])
        
        setMetrics(metricsData)
        setPrices(pricesData)
        setError(null)
      } catch (err) {
        setError(`Failed to load data for ${ticker}`)
        console.error(err)
      } finally {
        setLoading(false)
      }
    }

    fetchStockData()
  }, [ticker])

  if (loading) {
    return (
      <div className="flex items-center justify-center min-h-screen">
        <div className="text-xl text-slate-400">Loading {ticker} data...</div>
      </div>
    )
  }

  if (error) {
    return (
      <div className="flex items-center justify-center min-h-screen">
        <div className="text-xl text-red-400">{error}</div>
      </div>
    )
  }

  return (
    <div className="space-y-8">
      <div className="flex items-center justify-between">
        <h1 className="text-4xl font-bold">{ticker}</h1>
        {metrics && (
          <div className="text-right">
            <div className="text-4xl font-bold text-blue-400">
              ${metrics.current_price?.toFixed(2)}
            </div>
            <div className={`text-lg ${metrics.daily_return >= 0 ? 'text-green-400' : 'text-red-400'}`}>
              {metrics.daily_return ? `${(metrics.daily_return * 100).toFixed(2)}%` : 'N/A'}
            </div>
          </div>
        )}
      </div>

      {metrics && <MetricsPanel metrics={metrics} />}

      <div className="bg-slate-900/50 rounded-lg border border-slate-700 p-8">
        <h2 className="text-2xl font-bold mb-6">Price Chart</h2>
        {prices.length > 0 && <PriceChart data={prices} ticker={ticker} />}
      </div>
    </div>
  )
}
