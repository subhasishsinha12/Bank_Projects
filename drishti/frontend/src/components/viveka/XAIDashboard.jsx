import React, { useEffect, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { BarChart, Bar, XAxis, YAxis, Tooltip, ResponsiveContainer, Cell } from 'recharts';
import { viveka, satya } from '../../utils/api';
import { colors } from '../../utils/colors';
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
    if (id) {
      setLoadingBorrower(true);
      viveka.explain(id).then(r => {
        setBorrowerExplain(r.data);
        setLoadingBorrower(false);
      }).catch(() => setLoadingBorrower(false));
    }
  };

  const handleComputeCustom = () => {
    setLoadingCustom(true);
    viveka.explainCustom(customFeatures).then(r => {
      setCustomResult(r.data);
      setLoadingCustom(false);
    }).catch(() => setLoadingCustom(false));
  };

  const chartData = globalShap?.shap_summary?.map(s => ({
    feature: s.feature.replace(/_/g, ' '),
    value: s.mean_abs_shap,
  })) || [];

  return (
    <div className="space-y-6">
      <div>
        <h2 className="text-xl font-bold font-mono" style={{ color: colors.electric }}>VIVEKA — XAI Dashboard</h2>
        <p className="text-xs mt-1" style={{ color: colors.textSec }}>Explainable AI · SHAP · LIME · Fairlearn</p>
      </div>

      {/* Global SHAP */}
      <div className="rounded-xl border p-5" style={{ background: colors.navy3, borderColor: colors.electric + '30' }}>
        <h3 className="font-bold font-mono text-sm mb-4" style={{ color: colors.electric }}>Global Feature Importance (Mean |SHAP|)</h3>
        {chartData.length > 0 ? (
          <ResponsiveContainer width="100%" height={250}>
            <BarChart data={chartData} layout="vertical" margin={{ left: 100, right: 20, top: 5, bottom: 5 }}>
              <XAxis type="number" tick={{ fill: colors.textSec, fontSize: 10, fontFamily: 'IBM Plex Mono' }} />
              <YAxis type="category" dataKey="feature" tick={{ fill: colors.textSec, fontSize: 10, fontFamily: 'IBM Plex Mono' }} width={100} />
              <Tooltip
                contentStyle={{ background: colors.navy4, border: `1px solid ${colors.goldDim}`, color: colors.textPri, fontFamily: 'IBM Plex Mono', fontSize: 11 }}
                formatter={(v) => v.toFixed(4)}
              />
              <Bar dataKey="value">
                {chartData.map((entry, i) => (
                  <Cell key={i} fill={i < 3 ? colors.crimson : colors.electric} />
                ))}
              </Bar>
            </BarChart>
          </ResponsiveContainer>
        ) : (
          <div className="h-40 flex items-center justify-center text-xs" style={{ color: colors.textMut }}>Loading SHAP data...</div>
        )}
      </div>

      {/* Score New Application */}
      <div className="rounded-xl border p-5" style={{ background: colors.navy3, borderColor: colors.electric + '30' }}>
        <h3 className="font-bold font-mono text-sm mb-4" style={{ color: colors.electric }}>Score New Application — Live SHAP</h3>
        <div className="grid grid-cols-2 lg:grid-cols-5 gap-3 mb-4">
          {Object.entries(FEATURE_RANGES).map(([feat, [min, max, step]]) => (
            <div key={feat}>
              <label className="text-xs font-mono block mb-1" style={{ color: colors.textSec }}>
                {feat.replace(/_/g, ' ')}
              </label>
              <input
                type="number"
                min={min} max={max} step={step}
                value={customFeatures[feat]}
                onChange={e => setCustomFeatures(p => ({ ...p, [feat]: parseFloat(e.target.value) || 0 }))}
                className="w-full text-xs font-mono px-2 py-1.5 rounded border"
                style={{ background: colors.navy4, borderColor: colors.goldDim + '40', color: colors.textPri }}
              />
            </div>
          ))}
        </div>
        <button
          onClick={handleComputeCustom}
          disabled={loadingCustom}
          className="px-5 py-2 rounded font-mono text-sm font-semibold transition-all"
          style={{ background: colors.electric, color: colors.navy }}
        >
          {loadingCustom ? 'Computing SHAP...' : 'Compute SHAP Explanation'}
        </button>

        {customResult && (
          <div className="mt-5">
            <div className="flex items-center gap-4 mb-4">
              <div className="px-4 py-2 rounded-lg" style={{ background: colors.navy4 }}>
                <div className="text-xs font-mono" style={{ color: colors.textSec }}>PD Score</div>
                <div className="text-2xl font-bold font-mono" style={{ color: customResult.pd_score > 0.3 ? colors.crimson : colors.mint }}>
                  {(customResult.pd_score * 100).toFixed(1)}%
                </div>
              </div>
              <div>
                <div className="text-xs font-mono mb-1" style={{ color: colors.textSec }}>Adverse Factors</div>
                <div className="flex flex-wrap gap-2">
                  {customResult.adverse_factors.map((f, i) => (
                    <span key={i} className="px-2 py-0.5 rounded text-xs font-mono" style={{ background: colors.crimson + '20', color: colors.crimson, border: `1px solid ${colors.crimson}40` }}>
                      {f.replace(/_/g, ' ')}
                    </span>
                  ))}
                </div>
              </div>
            </div>
            <SHAPWaterfall
              shapValues={customResult.shap_values}
              baseValue={customResult.base_value}
              finalPD={customResult.pd_score}
            />
          </div>
        )}
      </div>

      {/* Borrower Selector */}
      <div className="rounded-xl border p-5" style={{ background: colors.navy3, borderColor: colors.electric + '30' }}>
        <h3 className="font-bold font-mono text-sm mb-4" style={{ color: colors.electric }}>Borrower Explainability</h3>
        <select
          value={selectedBorrower}
          onChange={e => handleBorrowerSelect(e.target.value)}
          className="w-full max-w-xs text-xs font-mono px-3 py-2 rounded border mb-4"
          style={{ background: colors.navy4, borderColor: colors.goldDim + '40', color: colors.textPri }}
        >
          <option value="">Select borrower...</option>
          {borrowers.map(b => (
            <option key={b.id} value={b.id}>{b.id} — {b.name} ({b.sector})</option>
          ))}
        </select>

        {loadingBorrower && <div className="text-xs font-mono" style={{ color: colors.textMut }}>Computing SHAP...</div>}

        {borrowerExplain && !loadingBorrower && (
          <div>
            <div className="flex items-center gap-4 mb-4 flex-wrap">
              <div className="px-4 py-2 rounded-lg" style={{ background: colors.navy4 }}>
                <div className="text-xs font-mono" style={{ color: colors.textSec }}>{borrowerExplain.borrower_name}</div>
                <div className="text-2xl font-bold font-mono" style={{ color: borrowerExplain.pd_score > 0.3 ? colors.crimson : colors.mint }}>
                  PD: {(borrowerExplain.pd_score * 100).toFixed(1)}%
                </div>
              </div>
              <div>
                <div className="text-xs font-mono mb-1" style={{ color: colors.textSec }}>Top Adverse Factors</div>
                <div className="flex flex-wrap gap-2">
                  {borrowerExplain.adverse_factors.map((f, i) => (
                    <span key={i} className="px-2 py-0.5 rounded text-xs font-mono" style={{ background: colors.crimson + '20', color: colors.crimson, border: `1px solid ${colors.crimson}40` }}>
                      {f.replace(/_/g, ' ')}
                    </span>
                  ))}
                </div>
              </div>
              <button
                onClick={() => navigate(`/viveka/explain/${selectedBorrower}`)}
                className="px-3 py-1.5 rounded text-xs font-mono"
                style={{ background: colors.electric + '20', color: colors.electric, border: `1px solid ${colors.electric}40` }}
              >
                Full Detail →
              </button>
            </div>

            <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
              <div>
                <div className="text-xs font-mono mb-2" style={{ color: colors.textSec }}>SHAP Waterfall</div>
                <SHAPWaterfall
                  shapValues={borrowerExplain.shap_values}
                  baseValue={borrowerExplain.base_value}
                  finalPD={borrowerExplain.pd_score}
                />
              </div>
              <div>
                <div className="text-xs font-mono mb-2" style={{ color: colors.textSec }}>LIME Explanation</div>
                <div className="space-y-2">
                  {borrowerExplain.lime_explanation?.map((item, i) => (
                    <div key={i} className="flex items-center justify-between gap-3 px-3 py-2 rounded" style={{ background: colors.navy4 }}>
                      <span className="text-xs font-mono" style={{ color: colors.textSec }}>{item.feature.replace(/_/g, ' ')}</span>
                      <div className="flex items-center gap-2">
                        <div className="h-1.5 w-20 rounded-full overflow-hidden" style={{ background: colors.navy }}>
                          <div
                            className="h-full rounded-full"
                            style={{
                              width: `${Math.abs(item.weight) * 200}%`,
                              maxWidth: '100%',
                              background: item.weight > 0 ? colors.crimson : colors.electric,
                            }}
                          />
                        </div>
                        <span className="text-xs font-mono w-16 text-right" style={{ color: item.weight > 0 ? colors.crimson : colors.electric }}>
                          {item.weight > 0 ? '+' : ''}{item.weight.toFixed(3)}
                        </span>
                      </div>
                    </div>
                  ))}
                </div>
              </div>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
