import React, { useEffect, useState } from 'react';
import { ChevronDown, ChevronUp } from 'lucide-react';
import { raksha } from '../../utils/api';
import { colors, psiColor } from '../../utils/colors';

function TierBadge({ tier }) {
  const c = tier === 1 ? colors.gold : tier === 2 ? colors.electric : colors.mint;
  return <span className="px-2 py-0.5 rounded text-xs font-mono font-bold" style={{ background: c + '20', color: c, border: `1px solid ${c}40` }}>T{tier}</span>;
}

function ValidationBadge({ status }) {
  const c = status === 'Validated' ? colors.mint
    : status === 'Pending Revalidation' ? '#F59E0B'
    : status === 'Validation Overdue' || status === 'Not Validated' ? colors.crimson
    : colors.textSec;
  return <span className="px-2 py-0.5 rounded text-xs font-mono" style={{ background: c + '15', color: c, border: `1px solid ${c}30` }}>{status}</span>;
}

function TieringModal({ onClose }) {
  const [form, setForm] = useState({ financial_materiality: 3, regulatory_nexus: false, complexity: 3, population_size: 50000 });
  const [result, setResult] = useState(null);
  const [loading, setLoading] = useState(false);

  const handleCompute = () => {
    setLoading(true);
    raksha.tierScore(form).then(r => { setResult(r.data); setLoading(false); }).catch(() => setLoading(false));
  };

  return (
    <div className="fixed inset-0 flex items-center justify-center z-50" style={{ background: 'rgba(5,13,26,0.8)' }}>
      <div className="rounded-xl border p-6 w-full max-w-md" style={{ background: colors.navy3, borderColor: colors.mint + '40' }}>
        <h3 className="font-bold font-mono mb-4" style={{ color: colors.mint }}>Model Tiering Engine</h3>

        <div className="space-y-4">
          {[
            { key: 'financial_materiality', label: 'Financial Materiality', min: 1, max: 5, step: 1 },
            { key: 'complexity', label: 'Model Complexity', min: 1, max: 5, step: 1 },
            { key: 'population_size', label: 'Population Size', min: 1000, max: 1000000, step: 1000 },
          ].map(({ key, label, min, max, step }) => (
            <div key={key}>
              <div className="flex justify-between mb-1">
                <label className="text-xs font-mono" style={{ color: colors.textSec }}>{label}</label>
                <span className="text-xs font-mono" style={{ color: colors.textPri }}>{form[key]}</span>
              </div>
              <input type="range" min={min} max={max} step={step} value={form[key]}
                onChange={e => setForm(p => ({ ...p, [key]: parseInt(e.target.value) }))}
                className="w-full accent-mint" />
            </div>
          ))}
          <div className="flex items-center gap-3">
            <label className="text-xs font-mono" style={{ color: colors.textSec }}>Regulatory Nexus</label>
            <button onClick={() => setForm(p => ({ ...p, regulatory_nexus: !p.regulatory_nexus }))}
              className="px-3 py-1 rounded text-xs font-mono"
              style={{ background: form.regulatory_nexus ? colors.mint + '20' : colors.navy4, color: form.regulatory_nexus ? colors.mint : colors.textSec, border: `1px solid ${form.regulatory_nexus ? colors.mint : colors.goldDim}40` }}>
              {form.regulatory_nexus ? 'YES' : 'NO'}
            </button>
          </div>
        </div>

        <button onClick={handleCompute} disabled={loading}
          className="mt-4 w-full py-2 rounded font-mono text-sm font-semibold"
          style={{ background: colors.mint, color: colors.navy }}>
          {loading ? 'Computing...' : 'Compute Tier Score'}
        </button>

        {result && (
          <div className="mt-4 p-4 rounded-lg" style={{ background: colors.navy4 }}>
            <div className="text-2xl font-bold font-mono" style={{ color: result.tier === 1 ? colors.gold : result.tier === 2 ? colors.electric : colors.mint }}>
              Tier {result.tier}
            </div>
            <div className="text-xs font-mono mt-1" style={{ color: colors.textSec }}>Score: {result.score}</div>
            <div className="text-xs mt-2" style={{ color: colors.textSec }}>{result.rationale}</div>
          </div>
        )}

        <button onClick={onClose} className="mt-3 w-full py-1.5 rounded text-xs font-mono" style={{ color: colors.textSec }}>Close</button>
      </div>
    </div>
  );
}

export default function ModelInventory() {
  const [models, setModels] = useState([]);
  const [expanded, setExpanded] = useState(null);
  const [showTiering, setShowTiering] = useState(false);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    raksha.inventory().then(r => { setModels(r.data.models || []); setLoading(false); }).catch(() => setLoading(false));
  }, []);

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h2 className="text-xl font-bold font-mono" style={{ color: colors.mint }}>RAKSHA — Model Inventory</h2>
          <p className="text-xs mt-1" style={{ color: colors.textSec }}>RBI MRM 2026 · {models.length} models registered</p>
        </div>
        <button onClick={() => setShowTiering(true)}
          className="px-4 py-2 rounded font-mono text-sm"
          style={{ background: colors.mint + '20', color: colors.mint, border: `1px solid ${colors.mint}40` }}>
          Run Tiering →
        </button>
      </div>

      {loading && <div className="text-xs font-mono" style={{ color: colors.textMut }}>Loading inventory...</div>}

      <div className="rounded-xl border overflow-hidden" style={{ borderColor: colors.mint + '30' }}>
        <div className="overflow-x-auto">
          <table className="w-full text-xs font-mono">
            <thead>
              <tr style={{ background: colors.navy3 }}>
                {['ID', 'Model Name', 'Type', 'Owner', 'Tier', 'Status', 'Validation', 'PSI', 'Last Validated', ''].map(h => (
                  <th key={h} className="px-3 py-3 text-left" style={{ color: colors.textSec }}>{h}</th>
                ))}
              </tr>
            </thead>
            <tbody>
              {models.map((m, i) => (
                <React.Fragment key={m.id}>
                  <tr
                    className="cursor-pointer transition-all hover:bg-navy-3"
                    style={{ background: i % 2 === 0 ? colors.navy2 : colors.navy4 + '60', borderTop: `1px solid ${colors.goldDim}20` }}
                    onClick={() => setExpanded(expanded === m.id ? null : m.id)}
                  >
                    <td className="px-3 py-3" style={{ color: colors.gold }}>{m.id}</td>
                    <td className="px-3 py-3 max-w-48 truncate" style={{ color: colors.textPri }}>{m.name}</td>
                    <td className="px-3 py-3" style={{ color: colors.textSec }}>{m.model_type}</td>
                    <td className="px-3 py-3" style={{ color: colors.textSec }}>{m.owner}</td>
                    <td className="px-3 py-3"><TierBadge tier={m.tier} /></td>
                    <td className="px-3 py-3">
                      <span className="px-2 py-0.5 rounded" style={{ background: colors.mint + '15', color: colors.mint }}>{m.status}</span>
                    </td>
                    <td className="px-3 py-3"><ValidationBadge status={m.validation_status} /></td>
                    <td className="px-3 py-3" style={{ color: psiColor(m.psi_current) }}>
                      {m.psi_current?.toFixed(2) ?? '—'}
                    </td>
                    <td className="px-3 py-3" style={{ color: colors.textMut }}>{m.last_validated ?? 'Never'}</td>
                    <td className="px-3 py-3" style={{ color: colors.textMut }}>
                      {expanded === m.id ? <ChevronUp size={14} /> : <ChevronDown size={14} />}
                    </td>
                  </tr>
                  {expanded === m.id && (
                    <tr style={{ background: colors.navy3 }}>
                      <td colSpan={10} className="px-5 py-4">
                        <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
                          <div>
                            <div style={{ color: colors.textMut }}>Purpose</div>
                            <div className="mt-1" style={{ color: colors.textPri }}>{m.purpose}</div>
                          </div>
                          <div>
                            <div style={{ color: colors.textMut }}>Use Scope</div>
                            <div className="mt-1" style={{ color: colors.textPri }}>{m.use_scope}</div>
                          </div>
                          <div>
                            <div style={{ color: colors.textMut }}>Performance</div>
                            <div className="mt-1 space-y-1">
                              <div>Gini: <span style={{ color: colors.electric }}>{m.gini?.toFixed(2) ?? 'N/A'}</span></div>
                              <div>AUC: <span style={{ color: colors.electric }}>{m.auc?.toFixed(2) ?? 'N/A'}</span></div>
                            </div>
                          </div>
                          <div>
                            <div style={{ color: colors.textMut }}>PSI Status</div>
                            <div className="mt-1">
                              <span style={{ color: psiColor(m.psi_current) }}>
                                {m.psi_status} ({m.psi_current?.toFixed(3)})
                              </span>
                            </div>
                          </div>
                        </div>
                        {m.notes && (
                          <div className="mt-3 text-xs" style={{ color: colors.textMut }}>Notes: {m.notes}</div>
                        )}
                      </td>
                    </tr>
                  )}
                </React.Fragment>
              ))}
            </tbody>
          </table>
        </div>
      </div>

      {showTiering && <TieringModal onClose={() => setShowTiering(false)} />}
    </div>
  );
}
