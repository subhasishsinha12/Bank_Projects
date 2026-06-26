import React, { useEffect, useState } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { ArrowLeft, TrendingUp, TrendingDown } from 'lucide-react';
import { AreaChart, Area, XAxis, YAxis, Tooltip, ResponsiveContainer, ReferenceLine } from 'recharts';
import { satya } from '../../utils/api';
import { colors, ewsColor, ewsBg, stageColor, pdColor } from '../../utils/colors';
import { Panel, Spinner, Badge } from '../ui';

const MONTHS = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun'];
const FEATURE_LABELS = {
  dscr: 'DSCR', current_ratio: 'Current Ratio', tol_tnw: 'TOL/TNW',
  cmr_score: 'CMR Score', vintage_years: 'Vintage (yrs)', collateral_pct: 'Collateral %',
  gst_compliance: 'GST Compliance', upi_txn_drop: 'UPI Txn Drop',
  sector_stress: 'Sector Stress', bureau_dpd: 'Bureau DPD',
};

const RECS = {
  RED: [
    'Initiate restructuring discussion — arrange RM site visit within 7 days',
    'Review and enforce collateral coverage — obtain updated valuation',
    'Place on Special Mention Account (SMA-1/2) watchlist immediately',
    'Escalate to Credit Review Committee for resolution strategy',
  ],
  AMBER: [
    'Schedule 30-day financial review — request updated P&L and bank statements',
    'Monitor UPI transaction volume weekly for further deterioration signals',
    'Verify covenant compliance with relationship manager',
    'Consider proactive restructuring to prevent RED migration',
  ],
  GREEN: [
    'Continue standard quarterly monitoring per credit review schedule',
    'Assess eligibility for credit limit enhancement if DSCR trends improve',
    'Verify GST filing compliance at next review',
  ],
};

export default function BorrowerDetail() {
  const { id } = useParams();
  const navigate = useNavigate();
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    satya.borrower(id).then(r => { setData(r.data); setLoading(false); }).catch(() => setLoading(false));
  }, [id]);

  if (loading) return <Spinner color={colors.violet} />;
  if (!data) return <div className="text-xs font-mono p-6" style={{ color: colors.crimson }}>Borrower not found.</div>;

  const ewsC = ewsColor(data.ews_stage);
  const stageC = stageColor(data.inas_stage);
  const pc = pdColor(data.pd_current);

  const pdChartData = (data.pd_history || []).map((pd, i) => ({
    month: MONTHS[i] || `M${i + 1}`,
    pd: parseFloat((pd * 100).toFixed(2)),
  }));

  const pdTrend = pdChartData.length >= 2
    ? pdChartData[pdChartData.length - 1].pd - pdChartData[0].pd
    : 0;

  return (
    <div className="space-y-5 max-w-6xl mx-auto fade-in">
      {/* Back + title */}
      <div className="flex items-center gap-3">
        <button onClick={() => navigate('/satya/portfolio')}
          className="w-8 h-8 rounded-xl flex items-center justify-center transition-all"
          style={{ background: 'rgba(255,255,255,0.04)', border: '1px solid rgba(255,255,255,0.08)' }}>
          <ArrowLeft size={15} style={{ color: colors.textSec }} />
        </button>
        <div>
          <h2 className="text-xl font-bold" style={{ color: colors.violet }}>{data.name}</h2>
          <p className="text-xs font-mono mt-0.5" style={{ color: colors.textMut }}>
            {id} · {data.sector} · {data.district}
          </p>
        </div>
      </div>

      {/* Top row: Profile + PD chart + SHAP */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-4">
        {/* Profile card */}
        <div className="rounded-2xl p-5 relative overflow-hidden"
          style={{
            background: `linear-gradient(145deg, ${ewsC}12, rgba(5,13,26,0.8))`,
            border: `1px solid ${ewsC}30`,
            boxShadow: `0 0 40px ${ewsC}08`,
          }}>
          <div className="absolute top-0 right-0 w-24 h-24 rounded-full blur-3xl opacity-20" style={{ background: ewsC }} />

          {/* EWS Stage — prominent */}
          <div className="flex items-center gap-2 mb-4">
            <div className="px-3 py-1.5 rounded-xl text-sm font-bold font-mono"
              style={{ background: ewsBg(data.ews_stage), color: ewsC, border: `1px solid ${ewsC}40` }}>
              {data.ews_stage}
            </div>
            <div className="px-3 py-1.5 rounded-xl text-xs font-mono"
              style={{ background: `${stageC}15`, color: stageC, border: `1px solid ${stageC}30` }}>
              {data.inas_stage}
            </div>
          </div>

          {/* PD */}
          <div className="mb-4">
            <div className="text-xs font-mono" style={{ color: colors.textMut }}>PD Score</div>
            <div className="text-4xl font-bold font-mono stat-value mt-1" style={{ color: pc }}>
              {(data.pd_current * 100).toFixed(1)}%
            </div>
            <div className="flex items-center gap-1.5 mt-1">
              {pdTrend > 0 ? <TrendingUp size={12} style={{ color: colors.crimson }} /> : <TrendingDown size={12} style={{ color: colors.mint }} />}
              <span className="text-xs font-mono" style={{ color: pdTrend > 0 ? colors.crimson : colors.mint }}>
                {pdTrend > 0 ? '+' : ''}{pdTrend.toFixed(1)}% over 6 months
              </span>
            </div>
          </div>

          {/* Profile fields */}
          <div className="space-y-2 text-xs">
            {[
              { label: 'Loan Amount', value: `₹${data.loan_amount?.toFixed(0)}L` },
              { label: 'Sector', value: data.sector },
              { label: 'District', value: data.district },
              { label: 'Gender', value: data.gender },
              { label: 'DSCR', value: data.dscr?.toFixed(3) },
              { label: 'CMR Score', value: data.cmr_score },
              { label: 'Bureau DPD', value: `${data.bureau_dpd} days` },
            ].map(({ label, value }) => (
              <div key={label} className="flex justify-between">
                <span style={{ color: colors.textMut }}>{label}</span>
                <span className="font-mono" style={{ color: colors.textSec }}>{value}</span>
              </div>
            ))}
          </div>

          {/* SICR alert */}
          {data.sicr_alert && (
            <div className="mt-4 px-3 py-2 rounded-xl text-xs font-mono"
              style={{ background: 'rgba(245,158,11,0.1)', border: '1px solid rgba(245,158,11,0.25)', color: colors.amber }}>
              ⚠ SICR Alert — Stage 2 migration required under IndAS 109
            </div>
          )}
        </div>

        {/* PD Trajectory */}
        <Panel accentColor={colors.violet} title="PD Trajectory — 6 Month History">
          <ResponsiveContainer width="100%" height={220}>
            <AreaChart data={pdChartData} margin={{ left: 5, right: 15, top: 10, bottom: 5 }}>
              <defs>
                <linearGradient id={`pdGrad-${id}`} x1="0" y1="0" x2="0" y2="1">
                  <stop offset="5%" stopColor={ewsC} stopOpacity={0.25} />
                  <stop offset="95%" stopColor={ewsC} stopOpacity={0} />
                </linearGradient>
              </defs>
              <XAxis dataKey="month" tick={{ fill: colors.textMut, fontSize: 10, fontFamily: 'IBM Plex Mono' }} />
              <YAxis tick={{ fill: colors.textMut, fontSize: 9, fontFamily: 'IBM Plex Mono' }}
                tickFormatter={v => `${v}%`} domain={[0, 'auto']} />
              <Tooltip
                contentStyle={{ background: colors.bg3, border: `1px solid ${colors.goldDim}`, color: colors.textPri, fontFamily: 'IBM Plex Mono', fontSize: 11 }}
                formatter={v => [`${v}%`, 'PD']}
              />
              <ReferenceLine y={25} stroke={colors.amber} strokeDasharray="4 2" strokeOpacity={0.4} />
              <ReferenceLine y={50} stroke={colors.crimson} strokeDasharray="4 2" strokeOpacity={0.4} />
              <Area type="monotone" dataKey="pd" stroke={ewsC} fill={`url(#pdGrad-${id})`}
                strokeWidth={2} dot={{ fill: ewsC, r: 3, strokeWidth: 0 }} />
            </AreaChart>
          </ResponsiveContainer>
        </Panel>

        {/* SHAP Drivers */}
        <Panel accentColor={colors.violet} title="PD Drivers — SHAP Attribution">
          <div className="space-y-2">
            {data.shap_pd_change?.map((item, i) => {
              const c = item.contribution > 0 ? colors.crimson : colors.electric;
              const maxV = Math.max(...data.shap_pd_change.map(x => Math.abs(x.contribution)));
              const pct = maxV > 0 ? Math.min(100, (Math.abs(item.contribution) / maxV) * 100) : 0;
              return (
                <div key={i} className="px-3 py-2.5 rounded-xl"
                  style={{ background: `${c}08`, border: `1px solid ${c}18` }}>
                  <div className="flex justify-between items-center mb-1.5">
                    <span className="text-xs" style={{ color: colors.textSec }}>
                      {FEATURE_LABELS[item.feature] || item.feature}
                    </span>
                    <span className="text-xs font-mono font-bold" style={{ color: c }}>
                      {item.contribution > 0 ? '+' : ''}{(item.contribution * 100).toFixed(2)}%
                    </span>
                  </div>
                  <div className="h-1 rounded-full" style={{ background: 'rgba(255,255,255,0.05)' }}>
                    <div className="h-full rounded-full"
                      style={{ width: `${pct}%`, background: `linear-gradient(90deg, ${c}60, ${c})` }} />
                  </div>
                </div>
              );
            })}
          </div>
        </Panel>
      </div>

      {/* Recommendations */}
      <div className="rounded-2xl p-5"
        style={{
          background: `linear-gradient(145deg, ${ewsC}06, rgba(5,13,26,0.7))`,
          border: `1px solid ${ewsC}20`,
        }}>
        <div className="text-xs font-mono mb-4" style={{ color: ewsC }}>RECOMMENDED ACTIONS — {data.ews_stage} STAGE</div>
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-3">
          {(RECS[data.ews_stage] || RECS.GREEN).map((r, i) => (
            <div key={i} className="flex items-start gap-3 px-4 py-3 rounded-xl"
              style={{ background: `${ewsC}08`, border: `1px solid ${ewsC}15` }}>
              <span className="text-sm font-bold font-mono flex-shrink-0 mt-0.5" style={{ color: ewsC }}>{i + 1}.</span>
              <span className="text-sm" style={{ color: colors.textSec }}>{r}</span>
            </div>
          ))}
          {data.sicr_alert && (
            <div className="flex items-start gap-3 px-4 py-3 rounded-xl"
              style={{ background: 'rgba(245,158,11,0.08)', border: '1px solid rgba(245,158,11,0.2)' }}>
              <span className="text-sm font-bold font-mono flex-shrink-0 mt-0.5" style={{ color: colors.amber }}>★</span>
              <span className="text-sm" style={{ color: colors.textSec }}>
                Move to Stage 2 provisioning — increase ECL per IndAS 109 expected credit loss framework
              </span>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
