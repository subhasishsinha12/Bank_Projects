import React, { useEffect, useState } from 'react';
import { ChevronDown, ChevronUp, SlidersHorizontal, X } from 'lucide-react';
import { raksha } from '../../utils/api';
import { colors, psiColor, psiGlow } from '../../utils/colors';
import { Panel, SectionHead, Badge, Spinner, Btn, ProgressBar } from '../ui';

function TierBadge({ tier }) {
  const c = tier === 1 ? colors.gold : tier === 2 ? colors.electric : colors.mint;
  const label = `T${tier}`;
  return (
    <span className="px-2.5 py-1 rounded-lg text-xs font-mono font-bold"
      style={{ background: `${c}18`, color: c, border: `1px solid ${c}30` }}>
      {label}
    </span>
  );
}

function ValidationBadge({ status }) {
  const c = status === 'Validated' ? colors.mint
    : status === 'Pending Revalidation' ? colors.amber
    : (status === 'Validation Overdue' || status === 'Not Validated') ? colors.crimson
    : colors.textSec;
  return <Badge label={status} color={c} />;
}

function TieringModal({ onClose }) {
  const [form, setForm] = useState({ financial_materiality: 3, regulatory_nexus: false, complexity: 3, population_size: 50000 });
  const [result, setResult] = useState(null);
  const [loading, setLoading] = useState(false);

  const handleCompute = () => {
    setLoading(true);
    raksha.tierScore(form).then(r => { setResult(r.data); setLoading(false); }).catch(() => setLoading(false));
  };

  const tierColor = result ? (result.tier === 1 ? colors.gold : result.tier === 2 ? colors.electric : colors.mint) : colors.textMut;

  return (
    <div className="fixed inset-0 flex items-center justify-center z-50"
      style={{ background: 'rgba(2,8,16,0.85)', backdropFilter: 'blur(8px)' }}>
      <div className="rounded-2xl p-6 w-full max-w-md relative"
        style={{
          background: 'linear-gradient(145deg, #081528, #05101E)',
          border: `1px solid ${colors.mint}30`,
          boxShadow: `0 0 60px ${colors.mint}12`,
        }}>
        <button onClick={onClose} className="absolute top-4 right-4 p-1" style={{ color: colors.textMut }}>
          <X size={16} />
        </button>

        <div className="text-sm font-bold font-mono mb-5" style={{ color: colors.mint }}>
          Model Tiering Engine — RBI MRM 2026
        </div>

        <div className="space-y-5">
          {[
            { key: 'financial_materiality', label: 'Financial Materiality', min: 1, max: 5, step: 1 },
            { key: 'complexity', label: 'Model Complexity', min: 1, max: 5, step: 1 },
          ].map(({ key, label, min, max, step }) => (
            <div key={key}>
              <div className="flex justify-between mb-2">
                <label className="text-xs font-mono" style={{ color: colors.textSec }}>{label}</label>
                <span className="text-xs font-mono font-bold" style={{ color: colors.mint }}>{form[key]} / 5</span>
              </div>
              <input type="range" min={min} max={max} step={step} value={form[key]}
                onChange={e => setForm(p => ({ ...p, [key]: parseInt(e.target.value) }))}
                className="w-full" style={{ accentColor: colors.mint }} />
              <div className="flex justify-between text-xs mt-1" style={{ color: colors.textMut }}>
                <span>Low</span><span>High</span>
              </div>
            </div>
          ))}

          <div>
            <div className="flex justify-between mb-2">
              <label className="text-xs font-mono" style={{ color: colors.textSec }}>Population Size</label>
              <span className="text-xs font-mono font-bold" style={{ color: colors.mint }}>{form.population_size.toLocaleString()}</span>
            </div>
            <input type="range" min={1000} max={1000000} step={1000} value={form.population_size}
              onChange={e => setForm(p => ({ ...p, population_size: parseInt(e.target.value) }))}
              className="w-full" style={{ accentColor: colors.mint }} />
          </div>

          <div className="flex items-center justify-between px-4 py-3 rounded-xl"
            style={{ background: 'rgba(255,255,255,0.03)', border: '1px solid rgba(255,255,255,0.06)' }}>
            <span className="text-xs font-mono" style={{ color: colors.textSec }}>Regulatory Nexus</span>
            <button onClick={() => setForm(p => ({ ...p, regulatory_nexus: !p.regulatory_nexus }))}
              className="relative w-10 h-5 rounded-full transition-all"
              style={{ background: form.regulatory_nexus ? colors.mint : 'rgba(255,255,255,0.1)' }}>
              <div className="absolute top-0.5 w-4 h-4 rounded-full bg-white transition-all"
                style={{ left: form.regulatory_nexus ? '1.25rem' : '0.125rem' }} />
            </button>
          </div>
        </div>

        <div className="mt-5">
          <Btn color={colors.mint} onClick={handleCompute} disabled={loading}>
            {loading ? 'Computing...' : 'Compute Tier Score'}
          </Btn>
        </div>

        {result && (
          <div className="mt-4 px-5 py-4 rounded-2xl"
            style={{
              background: `linear-gradient(135deg, ${tierColor}15, ${tierColor}05)`,
              border: `1px solid ${tierColor}30`,
            }}>
            <div className="flex items-baseline gap-2 mb-1">
              <span className="text-4xl font-bold font-mono stat-value" style={{ color: tierColor }}>Tier {result.tier}</span>
              <span className="text-sm font-mono" style={{ color: colors.textMut }}>Score: {result.score}</span>
            </div>
            <p className="text-xs leading-relaxed" style={{ color: colors.textSec }}>{result.rationale}</p>
          </div>
        )}
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

  if (loading) return <Spinner color={colors.mint} />;

  return (
    <div className="space-y-6 max-w-6xl mx-auto">
      <div className="flex items-start justify-between">
        <SectionHead
          title="RAKSHA — Model Inventory"
          accent="रक्षा"
          subtitle={`${models.length} models registered · RBI MRM 2026 · Tier-based governance`}
          color={colors.mint}
        />
        <Btn color={colors.mint} onClick={() => setShowTiering(true)} size="sm" variant="ghost">
          <div className="flex items-center gap-1.5"><SlidersHorizontal size={13} /> Run Tiering</div>
        </Btn>
      </div>

      <Panel accentColor={colors.mint}>
        <div className="overflow-x-auto -mx-5 -mb-5">
          <table className="w-full">
            <thead>
              <tr style={{ borderBottom: '1px solid rgba(80,227,194,0.1)' }}>
                {['ID', 'Model Name', 'Type', 'Owner', 'Tier', 'Validation', 'PSI', 'Last Validated'].map(h => (
                  <th key={h} className="px-4 py-3 text-left text-xs font-mono uppercase tracking-wider"
                    style={{ color: colors.textMut }}>
                    {h}
                  </th>
                ))}
                <th className="w-8" />
              </tr>
            </thead>
            <tbody className="divide-y" style={{ '--tw-divide-opacity': 1 }}>
              {models.map((m, i) => (
                <React.Fragment key={m.id}>
                  <tr
                    className="tr-hover cursor-pointer transition-all"
                    style={{ borderColor: 'rgba(255,255,255,0.03)' }}
                    onClick={() => setExpanded(expanded === m.id ? null : m.id)}
                  >
                    <td className="px-4 py-3.5 text-xs font-mono font-bold" style={{ color: colors.gold }}>{m.id}</td>
                    <td className="px-4 py-3.5 text-sm max-w-52" style={{ color: colors.textPri }}>
                      <div className="truncate">{m.name}</div>
                    </td>
                    <td className="px-4 py-3.5 text-xs" style={{ color: colors.textSec }}>{m.model_type}</td>
                    <td className="px-4 py-3.5 text-xs" style={{ color: colors.textSec }}>{m.owner}</td>
                    <td className="px-4 py-3.5"><TierBadge tier={m.tier} /></td>
                    <td className="px-4 py-3.5"><ValidationBadge status={m.validation_status} /></td>
                    <td className="px-4 py-3.5">
                      <span className="text-xs font-mono font-semibold" style={{ color: psiColor(m.psi_current) }}>
                        {m.psi_current?.toFixed(3) ?? '—'}
                      </span>
                    </td>
                    <td className="px-4 py-3.5 text-xs font-mono" style={{ color: colors.textMut }}>
                      {m.last_validated ?? 'Never'}
                    </td>
                    <td className="px-4 py-3.5" style={{ color: colors.textMut }}>
                      {expanded === m.id ? <ChevronUp size={14} /> : <ChevronDown size={14} />}
                    </td>
                  </tr>

                  {expanded === m.id && (
                    <tr>
                      <td colSpan={9} className="px-5 py-4"
                        style={{ background: 'rgba(80,227,194,0.03)', borderBottom: `1px solid ${colors.mint}15` }}>
                        <div className="grid grid-cols-2 lg:grid-cols-4 gap-4 text-xs">
                          <div>
                            <div className="font-mono mb-1" style={{ color: colors.textMut }}>Purpose</div>
                            <div style={{ color: colors.textSec }}>{m.purpose}</div>
                          </div>
                          <div>
                            <div className="font-mono mb-1" style={{ color: colors.textMut }}>Use Scope</div>
                            <div style={{ color: colors.textSec }}>{m.use_scope}</div>
                          </div>
                          <div>
                            <div className="font-mono mb-1" style={{ color: colors.textMut }}>Performance</div>
                            <div className="space-y-1">
                              <div>Gini: <span className="font-mono" style={{ color: colors.electric }}>{m.gini?.toFixed(2) ?? 'N/A'}</span></div>
                              <div>AUC: <span className="font-mono" style={{ color: colors.electric }}>{m.auc?.toFixed(2) ?? 'N/A'}</span></div>
                            </div>
                          </div>
                          <div>
                            <div className="font-mono mb-1" style={{ color: colors.textMut }}>PSI Status</div>
                            <div className="space-y-1">
                              <span className="font-mono font-semibold" style={{ color: psiColor(m.psi_current) }}>
                                {m.psi_status}
                              </span>
                              <ProgressBar value={m.psi_current} max={0.35} color={psiColor(m.psi_current)} className="mt-1.5" />
                              <div className="flex justify-between" style={{ color: colors.textMut }}>
                                <span>0</span><span>0.10</span><span>0.25</span><span>0.35</span>
                              </div>
                            </div>
                          </div>
                        </div>
                      </td>
                    </tr>
                  )}
                </React.Fragment>
              ))}
            </tbody>
          </table>
        </div>
      </Panel>

      {showTiering && <TieringModal onClose={() => setShowTiering(false)} />}
    </div>
  );
}
