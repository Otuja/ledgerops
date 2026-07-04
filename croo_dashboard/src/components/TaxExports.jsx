import React, { useEffect, useState } from 'react';
import { Download, FileText, Calendar, CheckCircle } from 'lucide-react';

const TaxExports = () => {
  const [exports, setExports] = useState([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    // Fetch stats and filter for Tax Export transactions
    fetch('http://localhost:8000/api/stats/')
      .then((res) => res.json())
      .then((data) => {
        const taxTx = (data.transactions || []).filter(tx => 
          tx.service_id.includes('0f76f68d') || tx.service_id.toLowerCase().includes('tax') || tx.service_id.toLowerCase().includes('export')
        );
        setExports(taxTx);
        setLoading(false);
      })
      .catch((err) => {
        console.error(err);
        setLoading(false);
      });
  }, []);

  return (
    <div className="flex-1 overflow-y-auto">
      <div className="p-8">
        {/* Header */}
        <div className="flex justify-between items-center mb-8">
          <div>
            <h1 className="text-3xl font-semibold text-slate-100 flex items-center gap-3">
              <FileText className="w-8 h-8 text-emerald-500" />
              Tax CSV Exports
            </h1>
            <p className="text-slate-400 mt-2 text-lg">
              Downloadable, compliant tax records for your automated agents.
            </p>
          </div>
          <button className="flex items-center gap-2 bg-emerald-500/10 hover:bg-emerald-500/20 text-emerald-400 px-4 py-2 rounded-lg border border-emerald-500/20 transition-all font-medium">
            <Calendar className="w-4 h-4" />
            Generate New Report
          </button>
        </div>

        {/* Content */}
        <div className="bg-slate-800/40 rounded-xl border border-slate-700/50 backdrop-blur-md overflow-hidden">
          <div className="p-6 border-b border-slate-700/50">
            <h2 className="text-xl font-medium text-slate-200">Recent Exports</h2>
          </div>
          
          <div className="overflow-x-auto">
            <table className="w-full text-left">
              <thead className="bg-slate-900/50 text-slate-400 text-xs uppercase font-semibold">
                <tr>
                  <th className="px-6 py-4">Report ID</th>
                  <th className="px-6 py-4">Buyer Agent</th>
                  <th className="px-6 py-4">Status</th>
                  <th className="px-6 py-4">Date Generated</th>
                  <th className="px-6 py-4 text-right">Action</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-700/50">
                {loading ? (
                  <tr>
                    <td colSpan="5" className="px-6 py-12 text-center text-slate-400">Loading exports...</td>
                  </tr>
                ) : exports.length === 0 ? (
                  <tr>
                    <td colSpan="5" className="px-6 py-12 text-center text-slate-400">No tax exports found. Run a test to generate one!</td>
                  </tr>
                ) : (
                  exports.map((tx, idx) => (
                    <tr key={idx} className="hover:bg-slate-800/60 transition-colors">
                      <td className="px-6 py-4">
                        <span className="font-mono text-slate-300 text-sm">
                          TAX-{tx.order_id.substring(0, 8).toUpperCase()}
                        </span>
                      </td>
                      <td className="px-6 py-4">
                        <div className="flex items-center gap-2">
                          <div className="w-6 h-6 rounded bg-slate-700 flex items-center justify-center text-xs font-mono text-slate-400">
                            {tx.buyer_id.substring(0, 2)}
                          </div>
                          <span className="font-mono text-slate-400 text-sm">{tx.buyer_id.substring(0, 12)}...</span>
                        </div>
                      </td>
                      <td className="px-6 py-4">
                        <div className="flex items-center gap-1.5 text-emerald-400 bg-emerald-400/10 px-2.5 py-1 rounded-full w-fit text-xs font-medium border border-emerald-400/20">
                          <CheckCircle className="w-3.5 h-3.5" />
                          VERIFIED
                        </div>
                      </td>
                      <td className="px-6 py-4 text-slate-400 text-sm">
                        {new Date(tx.created_at || Date.now()).toLocaleString()}
                      </td>
                      <td className="px-6 py-4 text-right">
                        <button className="inline-flex items-center gap-1.5 text-blue-400 hover:text-blue-300 bg-blue-500/10 hover:bg-blue-500/20 px-3 py-1.5 rounded transition-all text-sm font-medium">
                          <Download className="w-4 h-4" />
                          Download CSV
                        </button>
                      </td>
                    </tr>
                  ))
                )}
              </tbody>
            </table>
          </div>
        </div>
      </div>
    </div>
  );
};

export default TaxExports;
