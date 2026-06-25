import React, { useEffect, useState } from 'react';
import { LineChart, Line, XAxis, YAxis, Tooltip, ResponsiveContainer, ReferenceLine } from 'recharts';
import { satya } from '../../utils/api';
import { colors, psiColor } from '../../utils/colors';
import { SectionHead, Badge, Spinner } from '../ui';

const CustomTooltip = ({ active, payload, label }) => {
  if (!active || !payload?.length) return null;
  return (
    <div className="glass rounded-xl px-3 py-2 text-xs font-mono" style={{ border: `1px solid ${colors.goldDim}40` }}>
      <div style={{ color: colors.textMut }}>{label}</div>
      <div style={{ color: payload[0]?.stroke }}>PSI: {payload[0]?.value?.toFixed(4)}</div>
    </div>
  );
};

function PSICard({ model }) {
  const chartData = model.psi_history?.map(h => ({
    month: h.month.replace(' 2026', ''),
    psi: h.psi,
  })) || [];

  const c = psiColor(model.current_psi);
  const status = model.status;
  const trend = chartData.length >= 2
    ? chartData[chartData.length - 1].psi - chartData[chartData.length - 2].psi
    : 0;

  return (
    <div className="rounded-2xl overflow-hidden"
      style={{
        background: `linear-gradient(145deg, ${c}08, rgba(5,13,26,0.7))`,
        border: `1px solid ${c}25`,
        boxShadow: status === 'CRITICAL' ? `0 0 30px ${c}10` : 'none',
      }}>
      <div className="px-5 pt-4 pb-3">
        <div className="flex items-start justify-between gap-3">
          <div className="min-w-0">
            <div className="text-sm font-semibold truncate" style={{ color: colors.textPri }}>{model.name}</div>
            <div className="text-xs font-mono mt-0.5" style={{ color: colors.textMut }}>{model.id}</div>
          </div>
          <div className="flex flex-col items-end gap-1.5 flex-shrink-0">
            <div className="text-2xl font-bold font-mono stat-value" style={{ color: c }}>
              {model.current_psi?.toFixed(3)}
            </div>
            <Badge label={status} color={c} />
          </div>
        </div>

        {/* Trend arrow */}
        {trend !== 0 && (
          <div className="mt-2 text-xs font-mono flex items-center gap-1"
            style={{ color: trend > 0 ? colors.crimson : colors.mint }}>
            {trend > 0 ? '↑' : '↓'} {Math.abs(trend).toFixed(3)} vs last month
          </div>
        )}
      </div>

      <div className="px-2 pb-3">
        <ResponsiveContainer width="100%" height={120}>
          <LineChart data={chartData} margin={{ left: 5, right: 15, top: 5, bottom: 0 }}>
            <XAxis dataKey="month" tick={{ fill: colors.textMut, fontSize: 8, fontFamily: 'IBM Plex Mono' }} />
            <YAxis tick={{ fill: colors.textMut, fontSize: 8, fontFamily: 'IBM Plex Mono' }}
              domain={[0, Math.max(0.35, model.current_psi * 1.2)]} />
            <Tooltip content={<CustomTooltip />} />
            <ReferenceLine y={0.10} stroke={colors.amber} strokeDasharray="3 2" strokeOpacity={0.5} />
            <ReferenceLine y={0.25} stroke={colors.crimson} strokeDasharray="3 2" strokeOpacity={0.5} />
            <Line
              type="monotone" dataKey="psi"
              stroke={c} strokeWidth={2}
              dot={{ fill: c, r: 2.5, strokeWidth: 0 }}
              activeDot={{ r: 4, fill: c }}
            />
          </LineChart>
        </ResponsiveContainer>
      </div>
    </div>
  );
}

export default function PSIMonitor() {
  const [models, setModels] = useState([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    satya.psiMonitor().then(r => { setModels(r.data.models || []); setLoading(false); }).catch(() => setLoading(false));
  }, []);

  if (loading) return <Spinner color={colors.violet} />;

  const critical = models.filter(m => m.status === 'CRITICAL');
  const watch = models.filter(m => m.status === 'WATCH');
  const stable = models.filter(m => m.status === 'STABLE');

  return (
    <div className="space-y-6 max-w-6xl mx-auto">
      <SectionHead
        title="SATYA — PSI Monitor"
        accent="सत्य"
        subtitle="Population Stability Index · 6-month trend · Automated drift detection"
        color={colors.violet}
      />

      {/* Threshold legend */}
      <div className="flex items-center gap-6 px-4 py-3 rounded-xl text-xs font-mono"
        style={{ background: 'rgba(255,255,255,0.02)', border: '1px solid rgba(255,255,255,0.05)' }}>
        <span style={{ color: colors.textMut }}>PSI thresholds:</span>
        <span className="flex items-center gap-1.5"><span className="w-5 h-px inline-block" style={{ background: colors.mint }} /> <span style={{ color: colors.mint }}>STABLE (&lt;0.10)</span></span>
        <span className="flex items-center gap-1.5"><span className="w-5 h-px inline-block" style={{ background: colors.amber, borderTop: '2px dashed' }} /> <span style={{ color: colors.amber }}>WATCH (0.10–0.25)</span></span>
        <span className="flex items-center gap-1.5"><span className="w-5 h-px inline-block" style={{ background: colors.crimson }} /> <span style={{ color: colors.crimson }}>CRITICAL (&gt;0.25)</span></span>
      </div>

      {/* Critical models first */}
      {critical.length > 0 && (
        <div>
          <div className="text-xs font-mono mb-3 flex items-center gap-2">
            <span className="h-1.5 w-1.5 rounded-full pulse-dot" style={{ background: colors.crimson }} />
            <span style={{ color: colors.crimson }}>CRITICAL — Immediate revalidation required</span>
          </div>
          <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
            {critical.map(m => <PSICard key={m.id} model={m} />)}
          </div>
        </div>
      )}

      {watch.length > 0 && (
        <div>
          <div className="text-xs font-mono mb-3" style={{ color: colors.amber }}>WATCH — Increased monitoring</div>
          <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
            {watch.map(m => <PSICard key={m.id} model={m} />)}
          </div>
        </div>
      )}

      {stable.length > 0 && (
        <div>
          <div className="text-xs font-mono mb-3" style={{ color: colors.mint }}>STABLE — Routine monitoring</div>
          <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
            {stable.map(m => <PSICard key={m.id} model={m} />)}
          </div>
        </div>
      )}
    </div>
  );
}
