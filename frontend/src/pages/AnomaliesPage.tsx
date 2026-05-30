import { AlertTriangle, Shield } from 'lucide-react'
import { AnomalyCard } from '../components/AnomalyCard'
import { useAnomalies } from '../hooks/useApi'
import { motion } from 'framer-motion'

interface AnomaliesPageProps {
  storeId: string
}

export function AnomaliesPage({ storeId }: AnomaliesPageProps) {
  const { data: anomalies, loading } = useAnomalies(storeId, { refreshInterval: 10000 })

  const criticalCount = anomalies.filter(a => a.severity === 'CRITICAL').length
  const warnCount = anomalies.filter(a => a.severity === 'WARN').length
  const infoCount = anomalies.filter(a => a.severity === 'INFO').length

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h2 className="text-2xl font-bold text-white tracking-tight">Anomaly Detection</h2>
          <p className="text-sm text-slate-400 mt-1">Active alerts for {storeId}</p>
        </div>
        <div className="flex items-center gap-3">
          {criticalCount > 0 && (
            <div className="px-3 py-1.5 bg-rose-500/10 border border-rose-500/20 rounded-lg">
              <span className="text-xs font-bold text-rose-400">{criticalCount} Critical</span>
            </div>
          )}
          {warnCount > 0 && (
            <div className="px-3 py-1.5 bg-amber-500/10 border border-amber-500/20 rounded-lg">
              <span className="text-xs font-bold text-amber-400">{warnCount} Warning</span>
            </div>
          )}
          <div className="px-3 py-1.5 bg-slate-800 rounded-lg">
            <span className="text-xs font-bold text-slate-400">{infoCount} Info</span>
          </div>
        </div>
      </div>

      {loading && anomalies.length === 0 ? (
        <div className="flex items-center justify-center h-64">
          <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-violet-500" />
        </div>
      ) : anomalies.length === 0 ? (
        <motion.div
          initial={{ opacity: 0, scale: 0.95 }}
          animate={{ opacity: 1, scale: 1 }}
          className="flex flex-col items-center justify-center py-20 bg-slate-900/50 border border-slate-800 rounded-2xl"
        >
          <div className="w-16 h-16 bg-emerald-500/10 rounded-full flex items-center justify-center mb-4">
            <Shield className="w-8 h-8 text-emerald-400" />
          </div>
          <h3 className="text-lg font-semibold text-white mb-2">All Systems Normal</h3>
          <p className="text-sm text-slate-400">No active anomalies detected for this store</p>
        </motion.div>
      ) : (
        <div className="grid grid-cols-1 gap-3">
          {anomalies.map((anomaly, idx) => (
            <AnomalyCard key={`${anomaly.anomaly_type}-${idx}`} anomaly={anomaly} index={idx} />
          ))}
        </div>
      )}
    </div>
  )
}
