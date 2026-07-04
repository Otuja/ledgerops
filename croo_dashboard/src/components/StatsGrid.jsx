import React from 'react';
import { DollarSign, Activity, FileCheck, XCircle, Wallet, Handshake } from 'lucide-react';

export default function StatsGrid({ stats }) {
  const formatUSDC = (val) => {
    let num = parseFloat(val);
    if (isNaN(num)) return '0.00';
    // total_balance is stored in plain USDC (e.g. 400000.000000), not micro-units
    return num.toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 });
  };

  return (
    <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6 animate-fade-in-up">
      {/* Balance Card */}
      <div className="glass-bright rounded-2xl p-6 border-t border-t-accent-500/50 relative overflow-hidden group">
        <div className="absolute -right-6 -top-6 w-24 h-24 bg-accent-500/10 rounded-full blur-2xl group-hover:bg-accent-500/20 transition-all duration-500"></div>
        <div className="flex items-start justify-between mb-4">
          <p className="text-surface-400 text-sm font-medium tracking-wide uppercase">Total Balance</p>
          <DollarSign className="text-accent-400 opacity-80" size={24} />
        </div>
        <div className="flex items-baseline gap-2">
          <h2 className="text-3xl lg:text-4xl font-bold font-mono text-white tracking-tight animate-counter">
            {formatUSDC(stats.total_balance)}
          </h2>
          <span className="text-accent-400 font-medium">USDC</span>
        </div>
      </div>

      {/* Transactions Card */}
      <div className="glass rounded-2xl p-6 border-t border-t-surface-600 hover:border-t-surface-500 transition-colors">
        <div className="flex items-start justify-between mb-4">
          <p className="text-surface-400 text-sm font-medium tracking-wide uppercase">Transactions</p>
          <Activity className="text-surface-400 opacity-80" size={24} />
        </div>
        <h2 className="text-3xl font-bold text-white mb-2">{stats.transaction_count}</h2>
        <div className="flex items-center gap-3 text-xs font-medium">
          <span className="text-accent-400 bg-accent-400/10 px-2 py-1 rounded-md">{(stats.verified_count || 0) + (stats.completed_count || 0)} ok</span>
          <span className="text-rose-400 bg-rose-400/10 px-2 py-1 rounded-md">{stats.failed_count || 0} failed</span>
        </div>
      </div>

      {/* Wallets Card */}
      <div className="glass rounded-2xl p-6 border-t border-t-brand-500/50">
        <div className="flex items-start justify-between mb-4">
          <p className="text-surface-400 text-sm font-medium tracking-wide uppercase">Active Wallets</p>
          <Wallet className="text-brand-400 opacity-80" size={24} />
        </div>
        <h2 className="text-3xl font-bold text-white mb-2">{stats.wallet_count}</h2>
        <p className="text-sm text-surface-400 mt-2">Agents connected</p>
      </div>

      {/* Negotiations Card */}
      <div className="glass rounded-2xl p-6 border-t border-t-purple-500/50">
        <div className="flex items-start justify-between mb-4">
          <p className="text-surface-400 text-sm font-medium tracking-wide uppercase">Negotiations</p>
          <Handshake className="text-purple-400 opacity-80" size={24} />
        </div>
        <h2 className="text-3xl font-bold text-white mb-2">{stats.negotiation_count}</h2>
        <div className="flex items-center gap-3 text-xs font-medium">
          <span className="text-purple-400 bg-purple-400/10 px-2 py-1 rounded-md">{stats.negotiations_accepted} accepted</span>
          <span className="text-amber-400 bg-amber-400/10 px-2 py-1 rounded-md">{stats.negotiations_pending} pending</span>
        </div>
      </div>
    </div>
  );
}
