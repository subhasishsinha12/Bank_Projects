import React, { useEffect, useState } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { ArrowLeft } from 'lucide-react';
import { viveka } from '../../utils/api';
import { colors, pdColor } from '../../utils/colors';
import { Panel, SectionHead, Spinner, Badge } from '../ui';
import SHAPWaterfall from './SHAPWaterfall';

const FEATURE_LABELS = {
  dscr: 'DSCR', current_ratio: 'Current Ratio', tol_tnw: 'TOL/TNW',
  cmr_score: 'CMR Score', vintage_years: 'Vintage (yrs)', collateral_pct: 'Collateral %',
  gst_compliance: 'GST Compliance', upi_txn_drop: 'UPI Txn Drop',
  sector_stress: 'Sector Stress', bureau_dpd: 'Bureau DPD',
};

export default function BorrowerExplain() {
  const { id } = useParams();
  const navigate = useNavigate();
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    viveka.explain(id).then(r => { setData(r.data); setLoading(false); }).catch(() => setLoading(false));
  }, [id]);

  if (loading) return <Spinner color={colors.electric} />;
  if (!data) return <div className="text-xs font-mono p-6" style={{ color: colors.crimson }}>Borrower not found.</div>;

  const pc = pdColor(data.pd_score);

  return (
    <div className="space-y-6 max-w-5xl mx-auto fade-in">
      <div className="flex items-center gap-3">
        <button onClick={() => navigate('/viveka')}
          className="w-8 h-8 rounded-xl flex items-center justify-center transition-all"
          style={{ background: 'rgba(255,255,255,0.04)', border: '1px solid rgba(255,255,255,0.08)' }}>
          <ArrowLeft size={15} style={{ color: colors.textSec }} />
        </button>
        <SectionHead
          title={data.borrower_name}
          subtitle={`${id} · Borrower Explainability Report`}
          color={colors.electric}
        />
      </div>

      {/* Score + adverse */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-4">
        <div className="rounded-2xl p-6 relative overflow-hidden"
          style={{
            background: `linear-gradient(145deg, ${pc}18, ${pc}04)`,
            border: `1px solid ${pc}30`,
            boxShadow: `0 0 40px ${pc}10`,
          }}>
          <div className="absolute top-0 right-0 w-24 h-24 rounded-full blur-3xl opacity-25" style={{ background: pc }} />
          <div className="text-xs font-mono mb-2" style={{ color: colors.textMut }}>Probability of Default</div>
          <div className="text-5xl font-bold font-mono stat-value" style={{ color: pc }}>
            {(data.pd_score * 100).toFixed(1)}%
          </div>
          <div className="mt-3">
            <Badge label={data.pd_score > 0.4 ? 'HIGH RISK' : data.pd_score > 0.2 ? 'MODERATE' : 'LOW RISK'} color={pc} />
          </div>
        </div>

        <div className="lg:col-span-2 rounded-2xl p-5"
          style={{ background: 'rgba(255,91,91,0.06)', border: '1px solid rgba(255,91,91,0.18)' }}>
          <div className="text-xs font-mono mb-3" style={{ color: colors.textMut }}>Adverse Action Reason Codes</div>
          <div className="space-y-2">
            {data.adverse_factors.map((f, i) => (
              <div key={i} className="flex items-center gap-3 px-4 py-2.5 rounded-xl"
                style={{ background: 'rgba(255,91,91,0.08)', border: '1px solid rgba(255,91,91,0.12)' }}>
                <span className="text-sm font-bold font-mono" style={{ color: colors.crimson }}>{String.fromCharCode(65 + i)}.</span>
                <span className="text-sm" style={{ color: colors.textSec }}>
                  {FEATURE_LABELS[f] || f.replace(/_/g, ' ')}
                </span>
              </div>
            ))}
          </div>
          <p className="text-xs mt-3 leading-relaxed" style={{ color: colors.textMut }}>
            Per RBI MRM 2026 P7: these SHAP-ranked factors must be communicated to the applicant upon adverse credit decision.
          </p>
        </div>
      </div>

      {/* SHAP Waterfall */}
      <Panel accentColor={colors.electric} title="SHAP Waterfall — Feature Contribution to PD">
        <SHAPWaterfall shapValues={data.shap_values} baseValue={data.base_value} finalPD={data.pd_score} />
      </Panel>

      {/* LIME */}
      <Panel accentColor={colors.electric} title="LIME Local Explanation — Neighborhood Approximation">
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-3">
          {data.lime_explanation?.map((item, i) => {
            const w = item.weight;
            const c = w > 0 ? colors.crimson : colors.electric;
            const maxW = Math.max(...data.lime_explanation.map(x => Math.abs(x.weight)));
            const pct = Math.min(100, (Math.abs(w) / maxW) * 100);
            return (
              <div key={i} className="px-4 py-3 rounded-xl"
                style={{ background: `${c}08`, border: `1px solid ${c}18` }}>
                <div className="flex justify-between items-center mb-2">
                  <span className="text-xs font-semibold" style={{ color: colors.textSec }}>
                    {FEATURE_LABELS[item.feature.split(' ')[0]] || item.feature}
                  </span>
                  <span className="text-xs font-mono font-bold" style={{ color: c }}>
                    {w > 0 ? '+' : ''}{w.toFixed(4)}
                  </span>
                </div>
                <div className="h-1.5 rounded-full" style={{ background: 'rgba(255,255,255,0.05)' }}>
                  <div className="h-full rounded-full"
                    style={{ width: `${pct}%`, background: `linear-gradient(90deg, ${c}60, ${c})`, boxShadow: `0 0 6px ${c}50` }} />
                </div>
              </div>
            );
          })}
        </div>
      </Panel>
    </div>
  );
}
