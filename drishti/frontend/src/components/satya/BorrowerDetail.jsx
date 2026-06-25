import React, { useEffect, useState } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { ArrowLeft } from 'lucide-react';
import { AreaChart, Area, XAxis, YAxis, Tooltip, ResponsiveContainer } from 'recharts';
import { satya } from '../../utils/api';
import { colors, ewsColor, stageColor } from '../../utils/colors';

export default function BorrowerDetail() {
  const { id } = useParams();
  const navigate = useNavigate();
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    satya.borrower(id).then(r => { setData(r.data); setLoading(false); }).catch(() => setLoading(false));
  }, [id]);

  if (loading) return <div className="text-xs font-mono p-6" style={{ color: colors.textMut }}>Loading borrower data...</div>;
  if (!data) return <div className="text-xs font-mono p-6" style={{ color: colors.crimson }}>Borrower not found.</div>;

  const months = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun'];
  const pdChartData = (data.pd_history || []).map((pd, i) => ({ month: months[i] || `M${i+1}`, pd: parseFloat((pd * 100).toFixed(2)) }));

  const ewsC = ewsColor(data.ews_stage);
  const stageC = stageColor(data.inas_stage);

  const recommendations = {
    RED: [
      'Initiate restructuring discussion — contact RM for immediate site visit',
      'Review collateral coverage and enforce security interest',
      'Refer to Special Mention Account (SMA-1/2) review committee',
    ],
    AMBER: [
      'Schedule 30-day financial review — request updated P&L and bank statements',
      'Monitor UPI transaction volume weekly for further deterioration',
      'Engage relationship manager for covenant compliance verification',
    ],
    GREEN: [
      'Continue quarterly monitoring per standard credit review schedule',
      'Assess eligibility for credit limit enhancement if DSCR improves',
    ],
  };

  return (
    <div className="space-y-6">
      <div className="flex items-center gap-3">
        <button onClick={() => navigate('/satya/portfolio')} className="p-1 rounded" style={{ color: colors.textSec }}>
          <ArrowLeft size={18} />
        </button>
        <div>
          <h2 className="text-xl font-bold font-mono" style={{ color: colors.violet }}>{data.name}</h2>
          <p className="text-xs" style={{ color: colors.textSec }}>{id} · {data.sector} · {data.district}</p>
        </div>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-5">
        {/* Profile */}
        <div className="rounded-xl border p-5 space-y-4" style={{ background: colors.navy3, borderColor: ewsC + '40' }}>
          <h3 className="font-bold font-mono text-sm" style={{ color: ewsC }}>Borrower Profile</h3>
          <div className="space-y-2 text-xs">
            {[
              { label: 'Loan Amount', value: `₹${data.loan_amount?.toFixed(0)}L` },
              { label: 'DSCR', value: data.dscr?.toFixed(3) },
              { label: 'CMR Score', value: data.cmr_score },
              { label: 'Bureau DPD', value: `${data.bureau_dpd} days` },
              { label: 'Gender', value: data.gender },
            ].map(({ label, value }) => (
              <div key={label} className="flex justify-between">
                <span style={{ color: colors.textMut }}>{label}</span>
                <span className="font-mono" style={{ color: colors.textPri }}>{value}</span>
              </div>
            ))}
          </div>

          <div className="pt-3 border-t" style={{ borderColor: colors.goldDim + '30' }}>
            <div className="flex items-center justify-between mb-2">
              <span className="text-xs font-mono" style={{ color: colors.textSec }}>EWS Stage</span>
              <span className="text-lg font-bold font-mono px-3 py-1 rounded" style={{ background: ewsC + '20', color: ewsC }}>{data.ews_stage}</span>
            </div>
            <div className="flex items-center justify-between">
              <span className="text-xs font-mono" style={{ color: colors.textSec }}>IndAS 109</span>
              <span className="text-sm font-mono" style={{ color: stageC }}>{data.inas_stage}</span>
            </div>
            {data.sicr_alert && (
              <div className="mt-2 px-3 py-2 rounded text-xs font-mono" style={{ background: '#F59E0B20', color: '#F59E0B', border: '1px solid #F59E0B40' }}>
                ⚠ SICR Alert — Move to Stage 2
              </div>
            )}
          </div>

          <div className="text-2xl font-bold font-mono" style={{ color: data.pd_current > 0.3 ? colors.crimson : colors.mint }}>
            PD: {(data.pd_current * 100).toFixed(1)}%
          </div>
        </div>

        {/* PD Trajectory */}
        <div className="rounded-xl border p-5" style={{ background: colors.navy3, borderColor: colors.violet + '30' }}>
          <h3 className="font-bold font-mono text-sm mb-4" style={{ color: colors.violet }}>PD Trajectory — 6 Months</h3>
          <ResponsiveContainer width="100%" height={220}>
            <AreaChart data={pdChartData} margin={{ left: 5, right: 15, top: 10, bottom: 5 }}>
              <defs>
                <linearGradient id="pdGrad" x1="0" y1="0" x2="0" y2="1">
                  <stop offset="5%" stopColor={ewsC} stopOpacity={0.3} />
                  <stop offset="95%" stopColor={ewsC} stopOpacity={0} />
                </linearGradient>
              </defs>
              <XAxis dataKey="month" tick={{ fill: colors.textSec, fontSize: 10, fontFamily: 'IBM Plex Mono' }} />
              <YAxis tick={{ fill: colors.textSec, fontSize: 10, fontFamily: 'IBM Plex Mono' }} tickFormatter={v => `${v}%`} />
              <Tooltip
                contentStyle={{ background: colors.navy4, border: `1px solid ${colors.goldDim}`, color: colors.textPri, fontFamily: 'IBM Plex Mono', fontSize: 11 }}
                formatter={v => [`${v}%`, 'PD']}
              />
              <Area type="monotone" dataKey="pd" stroke={ewsC} fill="url(#pdGrad)" strokeWidth={2} dot={{ fill: ewsC, r: 3 }} />
            </AreaChart>
          </ResponsiveContainer>
        </div>

        {/* SHAP attribution */}
        <div className="rounded-xl border p-5" style={{ background: colors.navy3, borderColor: colors.violet + '30' }}>
          <h3 className="font-bold font-mono text-sm mb-4" style={{ color: colors.violet }}>PD Drivers — SHAP Attribution</h3>
          <div className="space-y-2">
            {data.shap_pd_change?.map((item, i) => (
              <div key={i} className="px-3 py-2 rounded" style={{ background: item.contribution > 0 ? colors.crimson + '15' : colors.electric + '15', border: `1px solid ${item.contribution > 0 ? colors.crimson : colors.electric}30` }}>
                <div className="flex justify-between items-center">
                  <span className="text-xs font-mono" style={{ color: colors.textSec }}>{item.feature.replace(/_/g, ' ')}</span>
                  <span className="text-xs font-mono font-semibold" style={{ color: item.contribution > 0 ? colors.crimson : colors.electric }}>
                    {item.contribution > 0 ? '+' : ''}{(item.contribution * 100).toFixed(2)}%
                  </span>
                </div>
                <div className="text-xs mt-0.5" style={{ color: colors.textMut }}>Value: {item.value?.toFixed(3)}</div>
              </div>
            ))}
          </div>
        </div>
      </div>

      {/* Recommendations */}
      <div className="rounded-xl border p-5" style={{ background: colors.navy3, borderColor: ewsC + '40' }}>
        <h3 className="font-bold font-mono text-sm mb-3" style={{ color: ewsC }}>Recommended Actions</h3>
        <div className="space-y-2">
          {(recommendations[data.ews_stage] || recommendations.GREEN).map((r, i) => (
            <div key={i} className="flex gap-2 text-sm px-3 py-2 rounded" style={{ background: ewsC + '10' }}>
              <span style={{ color: ewsC }}>{i + 1}.</span>
              <span style={{ color: colors.textSec }}>{r}</span>
            </div>
          ))}
          {data.sicr_alert && (
            <div className="flex gap-2 text-sm px-3 py-2 rounded" style={{ background: '#F59E0B15' }}>
              <span style={{ color: '#F59E0B' }}>★</span>
              <span style={{ color: colors.textSec }}>Move to Stage 2 — increase provisioning per IndAS 109 expected credit loss framework</span>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
