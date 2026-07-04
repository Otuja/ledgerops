import React, { useState } from 'react';
import { ShieldCheck, Search, Check, AlertTriangle } from 'lucide-react';

const ReceiptVerification = () => {
  const [orderId, setOrderId] = useState('');
  const [status, setStatus] = useState('idle'); // idle, loading, verified, failed
  
  const handleVerify = (e) => {
    e.preventDefault();
    if (!orderId) return;
    
    setStatus('loading');
    
    // Simulate network request to verify the receipt
    setTimeout(() => {
      if (orderId.length > 20) {
        setStatus('verified');
      } else {
        setStatus('failed');
      }
    }, 1500);
  };

  return (
    <div className="flex-1 overflow-y-auto">
      <div className="p-8 max-w-4xl mx-auto">
        {/* Header */}
        <div className="text-center mb-12">
          <div className="inline-flex items-center justify-center w-16 h-16 rounded-full bg-teal-500/10 mb-6 border border-teal-500/20 shadow-[0_0_30px_rgba(20,184,166,0.15)]">
            <ShieldCheck className="w-8 h-8 text-teal-400" />
          </div>
          <h1 className="text-4xl font-semibold text-slate-100 mb-4">
            Receipt Verification
          </h1>
          <p className="text-slate-400 text-lg">
            Cryptographically verify the authenticity and on-chain settlement of any LedgerOps transaction.
          </p>
        </div>

        {/* Search Bar */}
        <div className="bg-slate-800/60 rounded-2xl border border-slate-700/50 backdrop-blur-md p-8 shadow-xl">
          <form onSubmit={handleVerify} className="relative">
            <div className="absolute inset-y-0 left-0 pl-4 flex items-center pointer-events-none">
              <Search className="w-6 h-6 text-slate-400" />
            </div>
            <input
              type="text"
              value={orderId}
              onChange={(e) => setOrderId(e.target.value)}
              className="block w-full pl-12 pr-32 py-4 bg-slate-900/50 border border-slate-600 rounded-xl text-slate-200 placeholder-slate-500 focus:outline-none focus:ring-2 focus:ring-teal-500/50 focus:border-teal-500 transition-all font-mono text-lg"
              placeholder="Enter Order ID or Transaction Hash..."
            />
            <button 
              type="submit"
              disabled={status === 'loading'}
              className="absolute inset-y-2 right-2 px-6 bg-teal-500 hover:bg-teal-400 text-slate-900 font-semibold rounded-lg transition-colors flex items-center justify-center disabled:opacity-50"
            >
              {status === 'loading' ? 'Verifying...' : 'Verify'}
            </button>
          </form>

          {/* Results */}
          {status === 'verified' && (
            <div className="mt-8 p-6 bg-teal-500/10 border border-teal-500/20 rounded-xl flex items-start gap-4 animate-in fade-in slide-in-from-bottom-4 duration-500">
              <div className="w-10 h-10 rounded-full bg-teal-500/20 flex items-center justify-center flex-shrink-0">
                <Check className="w-6 h-6 text-teal-400" />
              </div>
              <div>
                <h3 className="text-lg font-medium text-teal-400 mb-1">Receipt Verified</h3>
                <p className="text-slate-300 leading-relaxed mb-4">
                  This transaction has been cryptographically verified on the Base network. The cryptographic signature matches the LedgerOps Oracle provider.
                </p>
                <div className="grid grid-cols-2 gap-4">
                  <div className="bg-slate-900/50 p-3 rounded-lg border border-slate-700/50">
                    <span className="block text-xs text-slate-500 uppercase font-semibold mb-1">Status</span>
                    <span className="text-sm font-mono text-teal-400">SETTLED</span>
                  </div>
                  <div className="bg-slate-900/50 p-3 rounded-lg border border-slate-700/50">
                    <span className="block text-xs text-slate-500 uppercase font-semibold mb-1">Network</span>
                    <span className="text-sm font-mono text-slate-300">Base Mainnet</span>
                  </div>
                </div>
              </div>
            </div>
          )}

          {status === 'failed' && (
            <div className="mt-8 p-6 bg-rose-500/10 border border-rose-500/20 rounded-xl flex items-start gap-4 animate-in fade-in slide-in-from-bottom-4 duration-500">
              <div className="w-10 h-10 rounded-full bg-rose-500/20 flex items-center justify-center flex-shrink-0">
                <AlertTriangle className="w-6 h-6 text-rose-400" />
              </div>
              <div>
                <h3 className="text-lg font-medium text-rose-400 mb-1">Verification Failed</h3>
                <p className="text-slate-300 leading-relaxed">
                  We could not verify a receipt for the provided Order ID on the Base network. Please check the ID and try again, or ensure the transaction has fully settled.
                </p>
              </div>
            </div>
          )}

        </div>
      </div>
    </div>
  );
};

export default ReceiptVerification;
