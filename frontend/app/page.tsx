'use client';

import { useState } from 'react';

export default function Home() {
  const [prompt, setPrompt] = useState('');
  const [loading, setLoading] = useState(false);
  const [workflowId, setWorkflowId] = useState(null);
  const [plan, setPlan] = useState(null);
  const [logs, setLogs] = useState([]);
  const [results, setResults] = useState([]);
  const [tteInfo, setTteInfo] = useState(null);

  // 1. Generate Plan with TTE Protection
  const handlePlan = async () => {
    setLoading(true);
    setLogs([]);
    setResults([]);
    try {
      const res = await fetch('http://localhost:8000/api/plan', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ prompt }),
      });
      const data = await res.json();
      setWorkflowId(data.workflow_id);
      setPlan(data.plan);
      setTteInfo({ secured: data.tte_secured, count: data.tokens_protected });
    } catch (err) {
      console.error(err);
    } finally {
      setLoading(false);
    }
  };

  // 2. Execute & Stream SSE Logs
  const handleExecute = async () => {
    setLoading(true);
    await fetch(`http://localhost:8000/api/workflows/${workflowId}/execute`, { method: 'POST' });

    // Open SSE Connection
    const eventSource = new EventSource(`http://localhost:8000/api/workflows/${workflowId}/stream`);
    
    eventSource.onmessage = (event) => {
      setLogs((prev) => [...prev, event.data]);
      if (event.data.includes("finished successfully")) {
        eventSource.close();
        fetchResults();
      }
    };
  };

  const fetchResults = async () => {
    const res = await fetch(`http://localhost:8000/api/workflows/${workflowId}/results`);
    const data = await res.json();
    setResults(data.results);
    setLoading(false);
  };

  return (
    <main className="min-h-screen bg-slate-900 text-slate-100 p-8 font-sans">
      <div className="max-w-5xl mx-auto space-y-6">
        <header className="border-b border-slate-800 pb-4 flex justify-between items-center">
          <div>
            <h1 className="text-3xl font-bold text-indigo-400">AI Data Intelligence Platform</h1>
            <p className="text-slate-400 text-sm">Natural Language to Traceable Dataset Pipeline</p>
          </div>
          {tteInfo?.secured && (
            <span className="bg-emerald-950 border border-emerald-500 text-emerald-400 text-xs px-3 py-1 rounded-full flex items-center gap-1 font-mono">
              🔒 TTE Protected ({tteInfo.count} Tokens Anonymized)
            </span>
          )}
        </header>

        {/* Input Bar */}
        <div className="flex gap-3">
          <input
            type="text"
            value={prompt}
            onChange={(e) => setPrompt(e.target.value)}
            placeholder="e.g. Extract AI funding rounds in 2026 for user test@company.com"
            className="flex-1 bg-slate-800 border border-slate-700 rounded-lg px-4 py-3 focus:outline-none focus:border-indigo-500 text-slate-100"
          />
          <button
            onClick={handlePlan}
            disabled={loading || !prompt}
            className="bg-indigo-600 hover:bg-indigo-500 disabled:opacity-50 text-white font-medium px-6 py-3 rounded-lg transition"
          >
            {loading ? 'Thinking...' : 'Plan Extraction'}
          </button>
        </div>

        {/* Planned Strategy */}
        {plan && (
          <div className="bg-slate-800/60 border border-slate-700 rounded-lg p-5 space-y-3">
            <h2 className="text-lg font-semibold text-emerald-400">Target Strategy</h2>
            <p className="text-sm"><strong>Search Query:</strong> {plan.search_query}</p>
            <div className="text-xs font-mono bg-slate-950 p-3 rounded border border-slate-800 text-indigo-300">
              {JSON.stringify(plan.target_schema, null, 2)}
            </div>
            <button
              onClick={handleExecute}
              className="bg-emerald-600 hover:bg-emerald-500 text-white font-medium px-5 py-2 rounded text-sm"
            >
              Start Web Collection
            </button>
          </div>
        )}

        {/* Live SSE Execution Logs */}
        {logs.length > 0 && (
          <div className="bg-slate-950 border border-slate-800 rounded-lg p-4 font-mono text-xs text-slate-300 space-y-1">
            <div className="text-slate-500 border-b border-slate-800 pb-1 mb-2 font-bold">LIVE AGENT LOGS</div>
            {logs.map((log, index) => (
              <div key={index} className="text-emerald-400"> &gt; {log}</div>
            ))}
          </div>
        )}

        {/* Traceable Data Results */}
        {results.length > 0 && (
          <div className="space-y-3">
            <h2 className="text-xl font-bold text-slate-200">Extracted Traceable Dataset</h2>
            <div className="overflow-x-auto border border-slate-800 rounded-lg">
              <table className="w-full text-left text-sm text-slate-300">
                <thead className="bg-slate-800 text-slate-400 text-xs uppercase">
                  <tr>
                    {Object.keys(results[0]).map((key) => (
                      <th key={key} className="p-3">{key}</th>
                    ))}
                  </tr>
                </thead>
                <tbody className="divide-y divide-slate-800">
                  {results.map((row, i) => (
                    <tr key={i} className="hover:bg-slate-800/40">
                      {Object.entries(row).map(([k, v], j) => (
                        <td key={j} className="p-3">
                          {k === "_source_url" ? (
                            <a href={v} target="_blank" rel="noreferrer" className="text-indigo-400 underline text-xs">
                              Source Link
                            </a>
                          ) : (
                            String(v)
                          )}
                        </td>
                      ))}
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>
        )}
      </div>
    </main>
  );
}