import type { Metadata } from 'next'
import './globals.css'

export const metadata: Metadata = {
  title: 'Foundation Flow - Stock Analytics',
  description: 'Stock analysis platform with real-time data and technical indicators',
}

export default function RootLayout({
  children,
}: {
  children: React.ReactNode
}) {
  return (
    <html lang="en">
      <body className="bg-slate-950 text-slate-100">
        <div className="min-h-screen flex flex-col">
          <header className="border-b border-slate-700 bg-slate-900/50 backdrop-blur">
            <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-4">
              <div className="flex items-center justify-between">
                <div className="flex items-center gap-3">
                  <div className="w-8 h-8 bg-blue-500 rounded-lg flex items-center justify-center">
                    <span className="text-white font-bold">FF</span>
                  </div>
                  <h1 className="text-2xl font-bold">Foundation Flow</h1>
                </div>
                <nav className="flex items-center gap-8">
                  <a href="/" className="hover:text-blue-400 transition">Home</a>
                  <a href="/stocks" className="hover:text-blue-400 transition">Stocks</a>
                </nav>
              </div>
            </div>
          </header>
          
          <main className="flex-1 max-w-7xl mx-auto w-full px-4 sm:px-6 lg:px-8 py-8">
            {children}
          </main>
          
          <footer className="border-t border-slate-700 bg-slate-900/50 mt-12">
            <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
              <p className="text-slate-400 text-sm">
                &copy; 2024 Foundation Flow. Stock data from Yahoo Finance.
              </p>
            </div>
          </footer>
        </div>
      </body>
    </html>
  )
}
