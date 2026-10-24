'use client'

import { useEffect, useRef } from 'react'
import { createChart, ColorType } from 'lightweight-charts'

interface PriceData {
  date: string
  open: number
  high: number
  low: number
  close: number
  volume: number
}

interface PriceChartProps {
  data: PriceData[]
  ticker: string
}

export default function PriceChart({ data, ticker }: PriceChartProps) {
  const chartContainer = useRef<HTMLDivElement>(null)

  useEffect(() => {
    if (!chartContainer.current || !data.length) return

    const chart = createChart(chartContainer.current, {
      layout: { background: { type: ColorType.Solid, color: '#0f172a' } },
      width: chartContainer.current.clientWidth,
      height: 400,
    })

    const candleSeries = chart.addCandlestickSeries({ upColor: '#22c55e', downColor: '#ef4444' })

    const candleData = data
      .map((candle) => ({
        time: candle.date as any,
        open: candle.open,
        high: candle.high,
        low: candle.low,
        close: candle.close,
      }))
      .sort((a, b) => new Date(a.time).getTime() - new Date(b.time).getTime())

    candleSeries.setData(candleData)
    chart.timeScale().fitContent()

    const handleResize = () => {
      if (chartContainer.current) {
        chart.applyOptions({ width: chartContainer.current.clientWidth })
      }
    }

    window.addEventListener('resize', handleResize)

    return () => {
      window.removeEventListener('resize', handleResize)
      chart.remove()
    }
  }, [data])

  return <div ref={chartContainer} className="w-full" />
}
