# Next.js Stock Analytics Frontend

Modern, responsive React dashboard for stock analysis built with Next.js 14.

## Overview

The frontend provides:
- Real-time stock search and discovery
- Interactive candlestick charts with TradingView Lightweight Charts
- Technical indicators and metrics display
- Responsive design for mobile and desktop
- Type-safe development with TypeScript

## Tech Stack

- **Next.js 14**: React framework with App Router
- **TypeScript**: Type-safe development
- **Tailwind CSS**: Utility-first styling
- **TradingView Lightweight Charts**: Interactive candlestick charts
- **Axios**: HTTP client for API calls

## Features

### Home Page (/)
- Stock discovery
- Search stocks by ticker
- Browse available stocks
- Quick access to stock details

### Stock Detail Page (/stock/[ticker])
- Interactive price charts with candlesticks
- Technical indicators
- Fundamental metrics display
- Return calculations
- 52-week high/low tracking

## Installation

```bash
# Install dependencies
npm install

# Set environment variables
export NEXT_PUBLIC_API_URL=http://localhost:8000
export NEXT_PUBLIC_API_TIMEOUT=30000

# Development server
npm run dev

# Build for production
npm run build

# Start production server
npm start
```

## Project Structure

```
frontend/
├── app/                        # Next.js App Router
│   ├── layout.tsx             # Root layout with header/footer
│   ├── page.tsx               # Home page (stock search)
│   ├── stock/
│   │   └── [ticker]/
│   │       └── page.tsx       # Stock detail page
│   └── globals.css
├── components/                 # React components
│   ├── PriceChart.tsx         # Candlestick chart
│   └── MetricsPanel.tsx       # Metrics display
├── lib/                        # Utilities
│   └── api.ts                 # API client
├── hooks/                      # Custom React hooks (future)
├── styles/                     # Additional styles (future)
├── package.json
├── next.config.js
├── tailwind.config.js
└── README.md
```

## Usage

### Searching Stocks

1. Go to home page (/)
2. Type stock ticker (e.g., "AAPL")
3. Click result or navigate directly to /stock/AAPL

### Viewing Stock Details

- **Price Chart**: Interactive candlestick chart with zoom/pan
- **Metrics Panel**: Key fundamental metrics
- **Historical Data**: 90 days of price history

## API Integration

All API calls go through `/lib/api.ts`:

```typescript
import { api } from '@/lib/api'

// Fetch stock metrics
const metrics = await api.get('/api/stocks/AAPL')

// Fetch prices
const prices = await api.get('/api/stocks/AAPL/prices', { days: 30 })

// Search stocks
const results = await api.get('/api/stocks/search', { q: 'APP' })
```

## Configuration

Set environment variables in `.env.local`:

```bash
NEXT_PUBLIC_API_URL=http://localhost:8000
NEXT_PUBLIC_API_TIMEOUT=30000
```

## Development Workflow

```bash
# Start dev server with hot reload
npm run dev

# Type checking
npm run type-check

# Linting
npm run lint

# Build and test production build
npm run build && npm start
```

## Performance

- **Code Splitting**: Automatic with Next.js
- **Image Optimization**: Next.js Image component (future)
- **Font Optimization**: System fonts, with fallbacks
- **CSS**: Tailwind for minimal bundle size

## Styling

Uses Tailwind CSS utility classes:
- Dark theme by default
- Responsive breakpoints (sm, md, lg)
- Custom color palette (slate, blue, green, red)

## Components

### PriceChart
Interactive candlestick chart using TradingView Lightweight Charts.

Props:
- `data`: Array of price data
- `ticker`: Stock ticker symbol

### MetricsPanel
Display fundamental metrics and technical indicators.

Props:
- `metrics`: Stock metrics object

## Browser Support

- Chrome/Edge (latest)
- Firefox (latest)
- Safari (latest)
- Mobile browsers

## Troubleshooting

### API Connection Failed
- Check NEXT_PUBLIC_API_URL environment variable
- Verify backend is running on correct port
- Check browser console for CORS errors

### Charts Not Rendering
- Clear browser cache
- Check console for errors
- Verify data format matches PriceData interface

### Build Errors
- Delete `.next` folder and rebuild
- Clear npm cache: `npm cache clean --force`
- Reinstall dependencies: `rm -rf node_modules && npm install`

## Future Enhancements

- [ ] Advanced technical indicators
- [ ] Portfolio tracking
- [ ] Price alerts
- [ ] Dark/light theme toggle
- [ ] More chart types (OHLC, Heikin-Ashi)
- [ ] Performance analytics
- [ ] News integration

## Related Components

- [Backend API](../backend/README.md)
- [Airflow DAGs](../airflow/README.md)
- [dbt Transformations](../dbt/README.md)
- [Infrastructure](../infrastructure/README.md)
