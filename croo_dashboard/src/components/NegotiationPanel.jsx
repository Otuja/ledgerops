import React from 'react';

export default function NegotiationPanel({ negotiations, loading }) {
  if (loading && negotiations.length === 0) {
    return (
      <div className="glass rounded-2xl p-6 border-t border-t-white/10 flex items-center justify-center h-full">
        <div className="animate-pulse w-8 h-8 border-4 border-surface-600 border-t-purple-500 rounded-full animate-spin"></div>
      </div>
    );
  }

  return (
    <div className="glass rounded-2xl border-t border-t-white/10 flex flex-col h-full animate-fade-in-up" style={{ animationDelay: '0.1s' }}>
      <div className="p-6 border-b border-white/5">
        <h3 className="text-xl font-bold text-white tracking-tight">Recent Negotiations</h3>
        <p className="text-sm text-surface-400">Real-time negotiation lifecycle tracking.</p>
      </div>
      
      <div className="flex-1 overflow-y-auto p-4 space-y-3">
        {negotiations.length === 0 ? (
          <div className="text-center text-surface-500 py-10">No negotiations found.</div>
        ) : (
          negotiations.slice(0, 10).map((neg) => (
            <div key={neg.negotiation_id} className="bg-surface-800/50 rounded-xl p-4 border border-white/5 hover:border-white/10 transition-colors">
              <div className="flex justify-between items-start mb-2">
                <span className="font-mono text-xs text-purple-400 bg-purple-400/10 px-2 py-0.5 rounded">
                  {neg.negotiation_id.substring(0, 12)}...
                </span>
                <span className={`text-[10px] font-bold uppercase tracking-widest px-2 py-0.5 rounded-full ${
                  neg.status === 'accepted' ? 'bg-accent-500/20 text-accent-400' : 'bg-amber-500/20 text-amber-400'
                }`}>
                  {neg.status}
                </span>
              </div>
              <div className="text-sm text-surface-200 mb-2 truncate">
                Service: <span className="font-semibold text-white">{neg.service_id || 'Unknown'}</span>
              </div>
              <div className="flex items-center gap-2 text-[10px] text-surface-400 uppercase">
                <span className="bg-surface-900 px-2 py-1 rounded">Req: {neg.requester_agent_id.substring(0,8) || 'N/A'}</span>
                <span className="text-surface-600">→</span>
                <span className="bg-surface-900 px-2 py-1 rounded">Prov: {neg.provider_agent_id.substring(0,8) || 'N/A'}</span>
              </div>
            </div>
          ))
        )}
      </div>
    </div>
  );
}
