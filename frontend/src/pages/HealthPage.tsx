import { HeartPulse, Activity } from 'lucide-react'
import { HealthStatus } from '../components/HealthStatus'
import { useHealth } from '../hooks/useApi'

export function HealthPage() {
  const { data: health } = useHealth({ refreshInterval: 5000 })

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h2 className="text-2xl font-bold text-white tracking-tight">System Health</h2>
          <p className="text-sm text-slate-400 mt-1">Infrastructure monitoring & feed status</p>
        </div>
        <div className="flex items-center gap-2 px-4 py-2 bg-slate-800 rounded-full">
          <Activity className="w-4 h-4 text-violet-400" />
          <span className="text-xs font-semibold text-slate-300">Auto-refresh every 5s</span>
        </div>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        <HealthStatus data={health} />

        <div className="bg-slate-900/80 backdrop-blur-xl border border-slate-800 rounded-2xl p-6">
          <div className="flex items-center gap-3 mb-6">
            <div className="p-2 rounded-lg bg-gradient-to-br from-violet-500 to-fuchsia-500">
              <HeartPulse className="w-4 h-4 text-white" />
            </div>
            <div>
              <h3 className="font-semibold text-white">API Performance</h3>
              <p className="text-xs text-slate-400">Response times & availability</p>
            </div>
          </div>

          <div className="space-y-4">
            {[
              { label: 'API Latency', value: '45ms', status: 'good' },
              { label: 'Uptime (24h)', value: '99.9%', status: 'good' },
              { label: 'Event Ingestion', value: '2.4K/min', status: 'good' },
              { label: 'DB Connections', value: '12/50', status: 'good' },
            ].map((metric) => (
              <div key={metric.label} className="flex items-center justify-between p-3 bg-slate-800/50 rounded-lg">
                <span className="text-sm text-slate-300">{metric.label}</span>
                <div className="flex items-center gap-2">
                  <span className="text-sm font-semibold text-white">{metric.value}</span>
                  <div className="w-2 h-2 rounded-full bg-emerald-400" />
                </div>
              </div>
            ))}
          </div>
        </div>
      </div>
    </div>
  )
}
