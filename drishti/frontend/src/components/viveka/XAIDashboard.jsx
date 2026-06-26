import React, { useEffect, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { BarChart, Bar, XAxis, YAxis, Tooltip, ResponsiveContainer, Cell } from 'recharts';
import { Zap, ArrowRight } from 'lucide-react';
import { viveka, satya } from '../../utils/api';
import { colors } from '../../utils/colors';
import { Panel, Btn, Spinner, SectionHead, ProgressBar } from '../ui';
import SHAPWaterfall from './SHAPWaterfall';

const FEATURE_DEFAULTS = {
  dscr: 1.2, current_ratio: 1.5, tol_tnw: 1.8, cmr_score: 4,
  vintage_years: 8, collateral_pct: 100, gst_compliance: 0.85,
  upi_txn_drop: 0.0, sector_stress: 0.4, bureau_dpd: 0,
};
const FEATURE_RANGES = {
  dscr: [0.3, 2.5, 0.1], current_ratio: [0.8, 2.8, 0.1], tol_tnw: [0.2, 4.0, 0.1],
  cmr_score: [1, 8, 1], vintage_years: [1, 25, 1], collateral_pct: [60, 150, 5],
  gst_compliance: [0.4, 1.0, 0.05], upi_txn_drop: [-0.5, 0.3, 0.05],
  sector_stress: [0.0, 1.0, 0.05], bureau_dpd: [0, 90, 10],
};

const FEATURE_LABELS = {
  dscr: 'DSCR', current_ratio: 'Current Ratio', tol_tnw: 'TOL/TNW',
  cmr_score: 'CMR Score', vintage_years: 'Vintage (yrs)', collateral_pct: 'Collateral %',
  gst_compliance: 'GST Compliance', upi_txn_drop: 'UPI Txn Drop',
  sector_stress: 'Sector Stress', bureau_dpd: 'Bureau DPD',
};

const CustomTooltip = ({ active, payload }) => {
  if (!active || !payload?.length) return null;
  return (
    <div className="glass rounded-xl px-3 py-2 text-xs font-mono"
      style={{ border: `1px solid ${colors.goldDim}40` }}>
      <div style={{ color: colors.textSec }}>{payload[0]?.payload?.feature}</div>
      <div style={{ color: colors.gold }}>SHAP: {payload[0]?.value?.toFixed(4)}</div>
    </div>
  );
};

export default function XAIDashboard() {
  const navigate = useNavigate();
  const [globalShap, setGlobalShap] = useState(null);
  const [borrowers, setBorrowers] = useState([]);
  const [selectedBorrower, setSelectedBorrower] = useState('');
  const [borrowerExplain, setBorrowerExplain] = useState(null);
  const [customFeatures, setCustomFeatures] = useState({ ...FEATURE_DEFAULTS });
  const [customResult, setCustomResult] = useState(null);
  const [loadingCustom, setLoadingCustom] = useState(false);
  const [loadingBorrower, setLoadingBorrower] = useState(false);

  useEffect(() => {
    viveka.globalShap().then(r => setGlobalShap(r.data)).catch(() => {});
    satya.portfolio().then(r => setBorrowers(r.data.borrowers || [])).catch(() => {});
  }, []);

  const handleBorrowerSelect = (id) => {
    setSelectedBorrower(id);
    if (!id) return;
    setLoadingBorrower(true);
    viveka.explain(id).then(r => { setBorrowerExplain(r.data); setLoadingBorrower(false); }).catch(() => setLoadingBorrower(false));
  };

  const handleComputeCustom = () => {
    setLoadingCustom(true);
    viveka.explainCustom(customFeatures).then(r => { setCustomResult(r.data); setLoadingCustom(false); }).catch(() => setLoadingCustom(false));
  };

  const chartData = globalShap?.shap_summary?.map(s => ({
    feature: FEATURE_LABELS[s.feature] || s.feature,
    value: s.mean_abs_shap,
    raw: s.feature,
  })) || [];

  const pdCol = (pd) => pd > 0.4 ? colors.crimson : pd > 0.2 ? colors.amber : colors.mint;

  return (
    <div className="space-y-6 max-w-6xl mx-auto">
      <SectionHead
        title="VIVEKA — XAI Validation"
        accent="विवेक"
        subtitle="Explainable AI · SHAP · LIME · Fairlearn · Adverse Action Reason Codes"
        color={colors.electric}
      />

      {/* Global SHAP */}
      <Panel accentColor={colors.electric} title="Global Feature Importance — Mean |SHAP| Value">
        {chartData.length === 0 ? (
          <Spinner color={colors.electric} />
        ) : (
          <div className="grid grid-cols-1 lg:grid-cols-5 gap-6">
            <div className="lg:col-span-3">
              <ResponsiveContainer width="100%" height={240}>
                <BarChart data={chartData} layout="vertical" margin={{ left: 20, right: 30, top: 5, bottom: 5 }}>
                  <XAxis type="number" tick={{ fill: colors.textMut, fontSize: 9, fontFamily: 'IBM Plex Mono' }} />
                  <YAxis type="category" dataKey="feature" tick={{ fill: colors.textSec, fontSize: 10, fontFamily: 'IBM Plex Mono' }} width={110} />
                  <Tooltip content={<CustomTooltip />} />
                  <Bar dataKey="value" radius={[0, 4, 4, 0]}>
                    {chartData.map((entry, i) => (
                      <Cell key={i} fill={i < 3 ? colors.crimson : i < 6 ? colors.amber : colors.electric}
                        fillOpacity={1 - i * 0.06} />
                    ))}
                  </Bar>
                </BarChart>
              </ResponsiveContainer>
            </div>
            <div className="lg:col-span-2 space-y-2.5">
              <div className="text-xs font-mono mb-3" style={{ color: colors.textSec }}>Feature Ranking</div>
              {chartData.slice(0, 8).map((d, i) => (
                <div key={i} className="flex items-center gap-3">
                  <span className="text-xs font-mono w-5 text-right flex-shrink-0"
                    style={{ color: i < 3 ? colors.crimson : colors.textMut }}>
                    #{i + 1}
                  </span>
                  <span className="text-xs flex-1 truncate" style={{ color: colors.textSec }}>
                    {FEATURE_LABELS[d.raw] || d.raw}
                  </span>
                  <ProgressBar value={d.value} max={chartData[0]?.value} color={i < 3 ? colors.crimson : colors.electric} className="w-20" />
                </div>
              ))}
            </div>
          </div>
        )}
      </Panel>

      {/* Score New Application */}
      <Panel accentColor={colors.electric} title="Score New Application — Live SHAP Computation"
        titleRight={
          <div className="flex items-center gap-2">
            <span className="h-1.5 w-1.5 rounded-full" style={{ background: loadingCustom ? colors.amber : colors.mint }} />
            <span className="text-xs font-mono" style={{ color: colors.textMut }}>
              {loadingCustom ? 'Computing...' : 'Ready'}
            </span>
          </div>
        }>
        <div className="grid grid-cols-2 md:grid-cols-5 gap-3 mb-5">
          {Object.entries(FEATURE_RANGES).map(([feat, [min, max, step]]) => (
            <div key={feat}>
              <label className="text-xs font-mono block mb-1.5" style={{ color: colors.textMut }}>
                {FEATURE_LABELS[feat]}
              </label>
              <input
                type="number" min={min} max={max} step={step}
                value={customFeatures[feat]}
                onChange={e => setCustomFeatures(p => ({ ...p, [feat]: parseFloat(e.target.value) || 0 }))}
                className="w-full text-xs font-mono px-2.5 py-2 rounded-xl outline-none transition-all"
                style={{
                  background: 'rgba(255,255,255,0.04)',
                  border: '1px solid rgba(201,168,76,0.15)',
                  color: colors.textPri,
                }}
                onFocus={e => e.target.style.borderColor = colors.electric + '60'}
                onBlur={e => e.target.style.borderColor = 'rgba(201,168,76,0.15)'}
              />
            </div>
          ))}
        </div>

        <div className="flex items-center gap-3">
          <Btn color={colors.electric} onClick={handleComputeCustom} disabled={loadingCustom}>
            <div className="flex items-center gap-2">
              <Zap size={13} />
              {loadingCustom ? 'Computing SHAP...' : 'Compute SHAP Explanation'}
            </div>
          </Btn>
          <button onClick={() => setCustomFeatures({ ...FEATURE_DEFAULTS })}
            className="text-xs font-mono" style={{ color: colors.textMut }}>
            Reset to defaults
          </button>
        </div>

        {customResult && (
          <div className="mt-6">
            <div className="flex items-stretch gap-4 mb-6 flex-wrap">
              {/* PD Score */}
              <div className="px-5 py-4 rounded-2xl"
                style={{
                  background: `linear-gradient(135deg, ${pdCol(customResult.pd_score)}18, ${pdCol(customResult.pd_score)}08)`,
                  border: `1px solid ${pdCol(customResult.pd_score)}30`,
                }}>
                <div className="text-xs font-mono" style={{ color: colors.textMut }}>Probability of Default</div>
                <div className="text-4xl font-bold font-mono mt-1 stat-value"
                  style={{ color: pdCol(customResult.pd_score) }}>
                  {(customResult.pd_score * 100).toFixed(1)}%
                </div>
                <div className="mt-1.5 text-xs font-mono px-2 py-0.5 rounded-full inline-block"
                  style={{
                    background: pdCol(customResult.pd_score) + '20',
                    color: pdCol(customResult.pd_score),
                    border: `1px solid ${pdCol(customResult.pd_score)}30`,
                  }}>
                  {customResult.pd_score > 0.4 ? 'HIGH RISK' : customResult.pd_score > 0.2 ? 'MODERATE' : 'LOW RISK'}
                </div>
              </div>

              {/* Adverse factors */}
              <div className="flex-1 min-w-48 px-5 py-4 rounded-2xl"
                style={{ background: 'rgba(255,91,91,0.06)', border: '1px solid rgba(255,91,91,0.15)' }}>
                <div className="text-xs font-mono mb-3" style={{ color: colors.textMut }}>Adverse Action Reason Codes</div>
                <div className="space-y-2">
                  {customResult.adverse_factors.map((f, i) => (
                    <div key={i} className="flex items-center gap-2">
                      <span className="text-xs font-mono font-bold" style={{ color: colors.crimson }}>{String.fromCharCode(65 + i)}.</span>
                      <span className="text-xs" style={{ color: colors.textSec }}>{FEATURE_LABELS[f] || f.replace(/_/g, ' ')}</span>
                    </div>
                  ))}
                </div>
              </div>
            </div>
            <SHAPWaterfall shapValues={customResult.shap_values} baseValue={customResult.base_value} finalPD={customResult.pd_score} />
          </div>
        )}
      </Panel>

      {/* Borrower Selector */}
      <Panel accentColor={colors.electric} title="Borrower Explainability — Individual SHAP + LIME">
        <div className="flex items-center gap-3 mb-5">
          <select
            value={selectedBorrower}
            onChange={e => handleBorrowerSelect(e.target.value)}
            className="text-xs font-mono px-3 py-2 rounded-xl outline-none"
            style={{
              background: 'rgba(255,255,255,0.04)',
              border: '1px solid rgba(201,168,76,0.2)',
              color: colors.textPri,
              minWidth: 280,
            }}
          >
            <option value="">Select a borrower...</option>
            {borrowers.map(b => (
              <option key={b.id} value={b.id}>{b.id} — {b.name} ({b.sector})</option>
            ))}
          </select>
          {selectedBorrower && (
            <button onClick={() => navigate(`/viveka/explain/${selectedBorrower}`)}
              className="text-xs font-mono flex items-center gap-1"
              style={{ color: colors.electric }}>
              Full detail <ArrowRight size={11} />
            </button>
          )}
        </div>

        {loadingBorrower && <Spinner color={colors.electric} />}

        {borrowerExplain && !loadingBorrower && (
          <div className="fade-in">
            {/* Header row */}
            <div className="flex items-stretch gap-4 mb-5 flex-wrap">
              <div className="px-5 py-4 rounded-2xl"
                style={{
                  background: `linear-gradient(135deg, ${pdCol(borrowerExplain.pd_score)}15, transparent)`,
                  border: `1px solid ${pdCol(borrowerExplain.pd_score)}25`,
                }}>
                <div className="text-xs font-mono" style={{ color: colors.textMut }}>{borrowerExplain.borrower_name}</div>
                <div className="text-3xl font-bold font-mono mt-1 stat-value"
                  style={{ color: pdCol(borrowerExplain.pd_score) }}>
                  {(borrowerExplain.pd_score * 100).toFixed(1)}%
                </div>
                <div className="text-xs mt-0.5 font-mono" style={{ color: colors.textMut }}>PD Score</div>
              </div>
              <div className="flex-1 px-5 py-4 rounded-2xl" style={{ background: 'rgba(255,91,91,0.05)', border: '1px solid rgba(255,91,91,0.12)' }}>
                <div className="text-xs font-mono mb-2" style={{ color: colors.textMut }}>Adverse Factors</div>
                <div className="flex flex-wrap gap-2">
                  {borrowerExplain.adverse_factors.map((f, i) => (
                    <span key={i} className="px-2.5 py-1 rounded-lg text-xs font-mono"
                      style={{ background: colors.crimson + '18', color: colors.crimson, border: `1px solid ${colors.crimson}25` }}>
                      {FEATURE_LABELS[f] || f.replace(/_/g, ' ')}
                    </span>
                  ))}
                </div>
              </div>
            </div>

            {/* SHAP + LIME side by side */}
            <div className="grid grid-cols-1 lg:grid-cols-2 gap-5">
              <div>
                <div className="text-xs font-mono mb-3" style={{ color: colors.textSec }}>
                  SHAP Waterfall — Feature contribution to PD
                </div>
                <SHAPWaterfall shapValues={borrowerExplain.shap_values} baseValue={borrowerExplain.base_value} finalPD={borrowerExplain.pd_score} />
              </div>
              <div>
                <div className="text-xs font-mono mb-3" style={{ color: colors.textSec }}>
                  LIME Local Explanation — Feature weights
                </div>
                <div className="space-y-2">
                  {borrowerExplain.lime_explanation?.map((item, i) => {
                    const w = item.weight;
                    const c = w > 0 ? colors.crimson : colors.electric;
                    const maxW = Math.max(...borrowerExplain.lime_explanation.map(x => Math.abs(x.weight)));
                    const pct = Math.min(100, (Math.abs(w) / maxW) * 100);
                    return (
                      <div key={i} className="px-3 py-2.5 rounded-xl"
                        style={{ background: `${c}08`, border: `1px solid ${c}18` }}>
                        <div className="flex justify-between items-center mb-1.5">
                          <span className="text-xs" style={{ color: colors.textSec }}>
                            {FEATURE_LABELS[item.feature.split(' ')[0]] || item.feature}
                          </span>
                          <span className="text-xs font-mono font-semibold" style={{ color: c }}>
                            {w > 0 ? '+' : ''}{w.toFixed(3)}
                          </span>
                        </div>
                        <div className="h-1 rounded-full" style={{ background: 'rgba(255,255,255,0.05)' }}>
                          <div className="h-full rounded-full" style={{ width: `${pct}%`, background: `linear-gradient(90deg, ${c}80, ${c})` }} />
                        </div>
                      </div>
                    );
                  })}
                </div>
              </div>
            </div>
          </div>
        )}
      </Panel>
    </div>
  );
}
