import React from 'react';

export default function WalletBreakdown({ wallets, totalBalance }) {
  // Guard against divide by zero or parsing errors
  const total = parseFloat(totalBalance) || 1;

  return (
    <div className="glass rounded-2xl border-t border-t-white/10 flex flex-col h-full animate-fade-in-up" style={{ animationDelay: '0.2s' }}>
      <div className="p-6 border-b border-white/5">
        <h3 className="text-xl font-bold text-white tracking-tight">Agent Wallets</h3>
        <p className="text-sm text-surface-400">Distribution of USDC balances.</p>
      </div>

      <div className="flex-1 p-6 overflow-y-auto space-y-6">
        {wallets.length === 0 ? (
          <div className="text-center text-surface-500 py-10">No active wallets.</div>
        ) : (
          wallets.map(wallet => {
            const balance = parseFloat(wallet.balance_usdc);
            const percentage = Math.min(100, Math.max(0, (balance / total) * 100));
            
            return (
              <div key={wallet.agent_id} className="space-y-2">
                <div className="flex justify-between items-end">
                  <span className="font-mono text-sm text-brand-300 font-medium">{wallet.agent_id}</span>
                  <span className="font-mono text-sm text-white">{(parseFloat(wallet.balance_usdc) / 1_000_000).toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 })}</span>
                </div>
                <div className="w-full bg-surface-800 rounded-full h-1.5 overflow-hidden">
                  <div 
                    className="h-full bg-gradient-to-r from-brand-500 to-accent-500 transition-all duration-1000 ease-out"
                    style={{ width: `${percentage}%` }}
                  ></div>
                </div>
              </div>
            );
          })
        )}
      </div>
    </div>
  );
}
