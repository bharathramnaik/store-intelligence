import { type ReactNode } from 'react'
import { Activity, Store, Settings, BarChart3, AlertTriangle, HeartPulse } from 'lucide-react'
import { Link, useLocation } from 'react-router-dom'
import { cn } from '../lib/utils'

interface LayoutProps {
  children: ReactNode
  storeId: string
  onStoreChange: (id: string) => void
}

const stores = [
  'STORE_BLR_002',
  'STORE_BLR_003', 
  'STORE_MUM_001',
  'STORE_DEL_001',
  'STORE_HYD_001',
]

const navItems = [
  { path: '/', icon: BarChart3, label: 'Dashboard' },
  { path: '/anomalies', icon: AlertTriangle, label: 'Anomalies' },
  { path: '/health', icon: HeartPulse, label: 'System Health' },
]

export function Layout({ children, storeId, onStoreChange }: LayoutProps) {
  const location = useLocation()

  return (
    <div className="min-h-screen bg-slate-950 text-slate-100 font-sans">
      {/* Sidebar */}
      <aside className="fixed left-0 top-0 h-full w-64 bg-slate-900 border-r border-slate-800 z-50">
        <div className="p-6">
          <div className="flex items-center gap-3 mb-8">
            <div className="w-10 h-10 rounded-xl bg-gradient-to-br from-violet-500 to-fuchsia-500 flex items-center justify-center shadow-lg shadow-violet-500/20">
              <Store className="w-5 h-5 text-white" />
            </div>
            <div>
              <h1 className="font-bold text-lg tracking-tight">Apex Retail</h1>
              <p className="text-xs text-slate-400">Intelligence Platform</p>
            </div>
          </div>

          <div className="mb-6">
            <label className="text-xs font-semibold text-slate-500 uppercase tracking-wider mb-2 block">
              Select Store
            </label>
            <select
              value={storeId}
              onChange={(e) => onStoreChange(e.target.value)}
              className="w-full bg-slate-800 border border-slate-700 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-violet-500 transition-all"
            >
              {stores.map(s => (
                <option key={s} value={s}>{s}</option>
              ))}
            </select>
          </div>

          <nav className="space-y-1">
            {navItems.map(item => {
              const isActive = location.pathname === item.path
              return (
                <Link
                  key={item.path}
                  to={item.path}
                  className={cn(
                    "flex items-center gap-3 px-3 py-2.5 rounded-lg text-sm font-medium transition-all",
                    isActive
                      ? "bg-violet-500/10 text-violet-400 border border-violet-500/20"
                      : "text-slate-400 hover:text-slate-200 hover:bg-slate-800"
                  )}
                >
                  <item.icon className="w-4 h-4" />
                  {item.label}
                </Link>
              )
            })}
          </nav>
        </div>

        <div className="absolute bottom-0 left-0 right-0 p-6 border-t border-slate-800">
          <div className="flex items-center gap-2 text-xs text-slate-500">
            <Activity className="w-3 h-3" />
            <span>v0.1.0 • Real-time</span>
          </div>
        </div>
      </aside>

      {/* Main Content */}
      <main className="ml-64 min-h-screen">
        <div className="p-8 max-w-[1600px] mx-auto">
          {children}
        </div>
      </main>
    </div>
  )
}
