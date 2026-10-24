'use client'

interface StockMetrics {
  market_cap?: number
  pe_ratio?: number
  dividend_yield?: number
  beta?: number
  fifty_two_week_high?: number
  fifty_two_week_low?: number
  volatility_252d?: number
}

interface MetricsPanelProps {
  metrics: StockMetrics
}

export default function MetricsPanel({ metrics }: MetricsPanelProps) {
  const formatCurrency = (value: number) => {
    if (value >= 1e12) return `$${(value / 1e12).toFixed(2)}T`
    if (value >= 1e9) return `$${(value / 1e9).toFixed(2)}B`
    if (value >= 1e6) return `$${(value / 1e6).toFixed(2)}M`
    return `$${value.toFixed(2)}`
  }

  const metricItems = [
    {
      label: 'Market Cap',
      value: metrics.market_cap ? formatCurrency(metrics.market_cap) : 'N/A',
    },
    {
      label: 'P/E Ratio',
      value: metrics.pe_ratio ? metrics.pe_ratio.toFixed(2) : 'N/A',
    },
    {
      label: 'Dividend Yield',
      value: metrics.dividend_yield ? `${(metrics.dividend_yield * 100).toFixed(2)}%` : 'N/A',
    },
    {
      label: 'Beta',
      value: metrics.beta ? metrics.beta.toFixed(2) : 'N/A',
    },
    {
      label: '52W High',
      value: metrics.fifty_two_week_high ? `$${metrics.fifty_two_week_high.toFixed(2)}` : 'N/A',
    },
    {
      label: '52W Low',
      value: metrics.fifty_two_week_low ? `$${metrics.fifty_two_week_low.toFixed(2)}` : 'N/A',
    },
    {
      label: 'Annual Volatility',
      value: metrics.volatility_252d ? `${(metrics.volatility_252d * 100).toFixed(2)}%` : 'N/A',
    },
  ]

  return (
    <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
      {metricItems.map((item) => (
        <div key={item.label} className="bg-slate-800/50 border border-slate-700 rounded-lg p-4">
          <div className="text-sm text-slate-400 mb-2">{item.label}</div>
          <div className="text-lg font-bold text-slate-100">{item.value}</div>
        </div>
      ))}
    </div>
  )
}
