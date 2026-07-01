import React, { useState } from 'react';
import Sidebar from './components/Sidebar';
import StatsGrid from './components/StatsGrid';
import TransactionTable from './components/TransactionTable';
import NegotiationPanel from './components/NegotiationPanel';
import WalletBreakdown from './components/WalletBreakdown';
import HealthBadge from './components/HealthBadge';
import ServicesPanel from './components/ServicesPanel';
import RevenueChart from './components/RevenueChart';
import AgentLookup from './components/AgentLookup';

import { fetchStats, fetchLogs, fetchWallets, fetchNegotiations } from './lib/api';
import { usePolling } from './hooks/usePolling';

const mockLogs = [
  { order_id: 'ord_1a2b3c4d5e6f', buyer_id: 'wallet_0x123...abc', amount_usdc: '250.000000', timestamp: new Date().toISOString(), status: 'verified', agent_id: 'agent_A' },
  { order_id: 'ord_9f8e7d6c5b4a', buyer_id: 'wallet_0x456...def', amount_usdc: '15.500000', timestamp: new Date(Date.now() - 3600000).toISOString(), status: 'pending', agent_id: 'agent_B' },
  { order_id: 'ord_5x6y7z8w9v0u', buyer_id: 'wallet_0x789...ghi', amount_usdc: '1000.000000', timestamp: new Date(Date.now() - 7200000).toISOString(), status: 'failed', agent_id: 'agent_C' },
];

function App() {
  const [currentView, setCurrentView] = useState('dashboard');
  const [isSidebarOpen, setIsSidebarOpen] = useState(false);

  // Use 10-second polling for live updates
  const { data: stats = {}, loading: statsLoading } = usePolling(fetchStats, 10000);
  const { data: logs = [], loading: logsLoading } = usePolling(fetchLogs, 10000);
  const { data: wallets } = usePolling(fetchWallets, 10000);
  const { data: negotiations, loading: negLoading } = usePolling(fetchNegotiations, 10000);

  const safeNegotiations = negotiations || [];
  const safeWallets = wallets || [];

  const safeStats = stats || {};
  const safeLogs = logs || [];

  return (
    <div className="min-h-screen bg-bg text-text flex selection:bg-brand-500/30 selection:text-brand-200">
      <Sidebar 
        currentView={currentView} 
        setCurrentView={setCurrentView} 
        isOpen={isSidebarOpen}
        setIsOpen={setIsSidebarOpen}
      />

      <main className="flex-1 flex flex-col h-screen overflow-hidden md:ml-64 w-full">
        {/* Top Header */}
        <header className="h-20 border-b border-white/5 flex items-center justify-between px-4 md:px-8 shrink-0 bg-surface/50 backdrop-blur-md z-10 w-full">
          <div className="flex items-center gap-4">
            <button 
              className="md:hidden p-2 text-surface-400 hover:text-white hover:bg-surface-800 rounded-lg transition-colors"
              onClick={() => setIsSidebarOpen(true)}
            >
              <svg className="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 6h16M4 12h16M4 18h16" />
              </svg>
            </button>
            <h2 className="text-xl md:text-2xl font-bold tracking-tight text-white capitalize">{currentView}</h2>
          </div>
          <HealthBadge />
        </header>

        {/* Scrollable Content Area */}
        <div className="flex-1 overflow-y-auto p-4 md:p-8 bg-[radial-gradient(ellipse_at_top,_var(--tw-gradient-stops))] from-surface-800/50 via-bg to-bg">
          <div className="max-w-7xl mx-auto space-y-8">
            
            {currentView === 'dashboard' && (
              <>
                <StatsGrid stats={safeStats} />
                <div className="h-[350px]">
                  <RevenueChart logs={safeLogs} />
                </div>
                <div className="grid grid-cols-1 xl:grid-cols-3 gap-6 xl:h-[500px]">
                  <div className="xl:col-span-2 h-[400px] xl:h-full">
                    <TransactionTable logs={safeLogs} loading={logsLoading} />
                  </div>
                  <div className="h-full flex flex-col gap-6">
                    <div className="flex-1 h-[300px] xl:h-0">
                      <NegotiationPanel negotiations={safeNegotiations} loading={negLoading} />
                    </div>
                    <div className="flex-1 h-[300px] xl:h-0">
                      <WalletBreakdown wallets={safeWallets} totalBalance={safeStats.total_balance} />
                    </div>
                  </div>
                </div>
              </>
            )}

            {currentView === 'services' && (
              <div className="min-h-[600px]">
                <ServicesPanel />
              </div>
            )}

            {currentView === 'transactions' && (
              <div className="h-[800px]">
                <TransactionTable logs={safeLogs} loading={logsLoading} />
              </div>
            )}

            {currentView === 'negotiations' && (
              <div className="h-[800px]">
                <NegotiationPanel negotiations={safeNegotiations} loading={negLoading} />
              </div>
            )}

            {currentView === 'wallets' && (
              <div className="h-[800px]">
                <WalletBreakdown wallets={safeWallets} totalBalance={safeStats.total_balance} />
              </div>
            )}

            {currentView === 'lookup' && (
              <AgentLookup />
            )}

          </div>
        </div>
      </main>
    </div>
  );
}

export default App;
