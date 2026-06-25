import React, { useEffect, useState } from 'react';
import { LineChart, Line, XAxis, YAxis, Tooltip, ResponsiveContainer, ReferenceLine, Legend } from 'recharts';
import { satya } from '../../utils/api';
import { colors, psiColor } from '../../utils/colors';

export default function PSIMonitor() {
  const [models, setModels] = useState([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    satya.psiMonitor().then(r => { setModels(r.data.models || []); setLoading(false); }).catch(() => setLoading(false));
  }, []);

  if (loading) return <div className="text-xs font-mono p-6" style={{ color: colors.textMut }}>Loading PSI data...</div>;

  const statusColor = (s) => s === 'CRITICAL' ? colors.crimson : s === 'WATCH' ? '#F59E0B' : colors.mint;

  return (
    <div className="space-y-6">
      <div>
        <h2 className="text-xl font-bold font-mono" style={{ color: colors.violet }}>SATYA — PSI Monitor</h2>
        <p className="text-xs mt-1" style={{ color: colors.textSec }}>Population Stability Index · 6-month trend · All 8 models</p>
      </div>

      <div className="text-xs font-mono flex gap-6" style={{ color: colors.textMut }}>
        <span><span style={{ color: colors.mint }}>●</span> STABLE (&lt;0.10)</span>
        <span><span style={{ color: '#F59E0B' }}>●</span> WATCH (0.10–0.25)</span>
        <span><span style={{ color: colors.crimson }}>●</span> CRITICAL (&gt;0.25)</span>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-5">
        {models.map(m => {
          const chartData = m.psi_history?.map(h => ({ month: h.month.replace(' 2026', ''), psi: h.psi })) || [];
          const sc = statusColor(m.status);

          return (
            <div key={m.id} className="rounded-xl border p-5" style={{ background: colors.navy3, borderColor: sc + '40' }}>
              <div className="flex items-start justify-between mb-3">
                <div>
                  <div className="text-xs font-mono font-semibold" style={{ color: colors.textPri }}>{m.name}</div>
                  <div className="text-xs mt-0.5 font-mono" style={{ color: colors.textMut }}>{m.id}</div>
                </div>
                <div className="text-right">
                  <div className="text-2xl font-bold font-mono" style={{ color: sc }}>{m.current_psi?.toFixed(2)}</div>
                  <div className="text-xs font-mono px-2 py-0.5 rounded" style={{ background: sc + '20', color: sc }}>{m.status}</div>
                </div>
              </div>

              <ResponsiveContainer width="100%" height={140}>
                <LineChart data={chartData} margin={{ left: 5, right: 15, top: 5, bottom: 5 }}>
                  <XAxis dataKey="month" tick={{ fill: colors.textMut, fontSize: 9, fontFamily: 'IBM Plex Mono' }} />
                  <YAxis tick={{ fill: colors.textMut, fontSize: 9, fontFamily: 'IBM Plex Mono' }} domain={[0, 'auto']} />
                  <Tooltip
                    contentStyle={{ background: colors.navy4, border: `1px solid ${colors.goldDim}`, color: colors.textPri, fontFamily: 'IBM Plex Mono', fontSize: 10 }}
                    formatter={v => v.toFixed(3)}
                  />
                  <ReferenceLine y={0.10} stroke="#F59E0B" strokeDasharray="3 2" />
                  <ReferenceLine y={0.25} stroke={colors.crimson} strokeDasharray="3 2" />
                  <Line type="monotone" dataKey="psi" stroke={sc} strokeWidth={2} dot={{ fill: sc, r: 3 }} />
                </LineChart>
              </ResponsiveContainer>
            </div>
          );
        })}
      </div>
    </div>
  );
}
