import React, { useState } from 'react';

export default function TransactionTable({ logs, loading }) {
  const [filter, setFilter] = useState('All');

  const filteredLogs = logs.filter(log => filter === 'All' || log.status === filter.toLowerCase());

  const getStatusColor = (status) => {
    switch(status) {
      case 'verified': return 'bg-accent-500/10 text-accent-400 border-accent-500/20';
      case 'failed': return 'bg-rose-500/10 text-rose-400 border-rose-500/20';
      case 'completed': return 'bg-brand-500/10 text-brand-400 border-brand-500/20';
      default: return 'bg-amber-500/10 text-amber-400 border-amber-500/20';
    }
  };

  const getStatusDot = (status) => {
    switch(status) {
      case 'verified': return 'bg-accent-500 shadow-[0_0_8px_rgba(16,185,129,0.5)]';
      case 'failed': return 'bg-rose-500 shadow-[0_0_8px_rgba(244,63,94,0.5)]';
      case 'completed': return 'bg-brand-500 shadow-[0_0_8px_rgba(99,102,241,0.5)]';
      default: return 'bg-amber-500 shadow-[0_0_8px_rgba(245,158,11,0.5)]';
    }
  };

  return (
    <div className="glass rounded-2xl border-t border-t-white/10 flex flex-col h-full animate-fade-in">
      <div className="p-6 border-b border-white/5 flex flex-col sm:flex-row justify-between items-start sm:items-center gap-4">
        <div>
          <h3 className="text-xl font-bold text-white tracking-tight">Audit Log</h3>
          <p className="text-sm text-surface-400">Real-time view of all processed transactions.</p>
        </div>
        
        <div className="flex bg-surface-900/50 p-1 rounded-xl border border-white/5 backdrop-blur-md">
          {['All', 'Verified', 'Pending', 'Failed'].map(f => (
            <button
              key={f}
              onClick={() => setFilter(f)}
              className={`px-4 py-1.5 text-sm font-medium rounded-lg transition-all ${
                filter === f 
                  ? 'bg-surface-700 text-white shadow-sm' 
                  : 'text-surface-400 hover:text-surface-200'
              }`}
            >
              {f}
            </button>
          ))}
        </div>
      </div>

      <div className="flex-1 overflow-auto">
        <table className="w-full text-left border-collapse">
          <thead className="bg-surface-900/40 text-surface-400 text-xs uppercase tracking-wider sticky top-0 z-10 backdrop-blur-md">
            <tr>
              <th className="px-6 py-4 font-semibold">Order ID</th>
              <th className="px-6 py-4 font-semibold">Buyer</th>
              <th className="px-6 py-4 font-semibold text-right">Amount (USDC)</th>
              <th className="px-6 py-4 font-semibold text-center">Status</th>
              <th className="px-6 py-4 font-semibold text-right">Time</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-white/5">
            {loading && logs.length === 0 ? (
              <tr>
                <td colSpan="5" className="px-6 py-12 text-center text-surface-400">
                  <div className="animate-pulse flex flex-col items-center gap-3">
                    <div className="w-8 h-8 border-4 border-surface-600 border-t-accent-500 rounded-full animate-spin"></div>
                    <p>Loading transactions...</p>
                  </div>
                </td>
              </tr>
            ) : filteredLogs.length === 0 ? (
              <tr>
                <td colSpan="5" className="px-6 py-16 text-center text-surface-500">
                  <span className="text-4xl mb-4 block">📭</span>
                  <p>No transactions found for filter: {filter}</p>
                </td>
              </tr>
            ) : (
              filteredLogs.map((log) => (
                <tr key={log.order_id} className="hover:bg-white/[0.02] transition-colors group">
                  <td className="px-6 py-4">
                    <span className="font-mono text-sm text-surface-200 group-hover:text-white transition-colors">
                      {log.order_id.substring(0, 16)}...
                    </span>
                  </td>
                  <td className="px-6 py-4">
                    <div className="flex flex-col">
                      <span className="font-mono text-xs text-brand-400">{log.buyer_id.substring(0, 12)}...</span>
                      {log.agent_id && <span className="text-[10px] text-surface-400 mt-1 uppercase tracking-widest">Agent: {log.agent_id}</span>}
                    </div>
                  </td>
                  <td className="px-6 py-4 text-right">
                    <span className="font-mono text-sm text-white font-medium">
                      {(parseFloat(log.amount_usdc) / 1_000_000).toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 })}
                    </span>
                  </td>
                  <td className="px-6 py-4">
                    <div className="flex justify-center">
                      <div className={`px-3 py-1 rounded-full text-xs font-bold border flex items-center gap-2 w-28 justify-center ${getStatusColor(log.status)}`}>
                        <div className={`w-1.5 h-1.5 rounded-full ${getStatusDot(log.status)}`}></div>
                        {log.status.toUpperCase()}
                      </div>
                    </div>
                  </td>
                  <td className="px-6 py-4 text-right">
                    <span className="text-xs text-surface-400">
                      {new Date(log.timestamp).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}
                    </span>
                  </td>
                </tr>
              ))
            )}
          </tbody>
        </table>
      </div>
    </div>
  );
}
