import React, { useEffect, useState } from 'react';
import { BarChart, Bar, XAxis, YAxis, Tooltip, ResponsiveContainer, ReferenceLine, Cell } from 'recharts';
import { viveka } from '../../utils/api';
import { colors, dirColor } from '../../utils/colors';
import { Panel, SectionHead, ProgressBar, Spinner, Badge } from '../ui';

function DirCard({ label, value, status, desc }) {
  const c = status === 'PASS' ? colors.mint : status === 'WATCH' ? colors.amber : colors.crimson;
  return (
    <div className="rounded-2xl p-5 relative overflow-hidden"
      style={{
        background: `linear-gradient(135deg, ${c}12, ${c}04)`,
        border: `1px solid ${c}25`,
        boxShadow: `0 0 24px ${c}08`,
      }}>
      <div className="absolute top-0 right-0 w-16 h-16 rounded-full blur-2xl opacity-30" style={{ background: c }} />
      <div className="text-xs font-mono mb-2" style={{ color: colors.textMut }}>{label}</div>
      <div className="text-3xl font-bold font-mono stat-value" style={{ color: c }}>
        {typeof value === 'number' ? value.toFixed(3) : value}
      </div>
      <div className="mt-2">
        <Badge label={status} color={c} />
      </div>
      {desc && <div className="text-xs mt-3 leading-relaxed" style={{ color: colors.textMut }}>{desc}</div>}
    </div>
  );
}

const CustomTooltip = ({ active, payload }) => {
  if (!active || !payload?.length) return null;
  return (
    <div className="glass rounded-xl px-3 py-2 text-xs font-mono" style={{ border: `1px solid ${colors.goldDim}40` }}>
      <div style={{ color: colors.textSec }}>{payload[0]?.payload?.district}</div>
      <div style={{ color: colors.electric }}>{(payload[0]?.value * 100)?.toFixed(1)}% approval rate</div>
    </div>
  );
};

export default function FairnessAudit() {
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    viveka.fairnessAudit().then(r => { setData(r.data); setLoading(false); }).catch(() => setLoading(false));
  }, []);

  if (loading) return <Spinner color={colors.electric} />;

  const dirStatus = (d) => d >= 0.90 ? 'PASS' : d >= 0.80 ? 'WATCH' : 'FAIL';

  const geoData = Object.entries(data?.by_geography || {}).map(([district, rate]) => ({ district, rate }));
  const minRate = Math.min(...geoData.map(d => d.rate));
  const maxRate = Math.max(...geoData.map(d => d.rate));

  return (
    <div className="space-y-6 max-w-6xl mx-auto">
      <SectionHead
        title="VIVEKA — Fairness Audit"
        accent="विवेक"
        subtitle="Fairlearn · Disparate Impact Ratio · Equalized Odds · RBI MRM 2026 Principle P7"
        color={colors.electric}
      />

      {/* Metric cards */}
      <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
        <DirCard label="DIR Overall (Gender)" value={data?.overall_dir}
          status={dirStatus(data?.overall_dir || 0)} desc="Min/Max approval rate ratio · ≥0.80 threshold" />
        <DirCard label="DIR — Gender Split" value={data?.by_gender?.dir}
          status={dirStatus(data?.by_gender?.dir || 0)}
          desc={`Male: ${(data?.by_gender?.male * 100)?.toFixed(1)}% · Female: ${(data?.by_gender?.female * 100)?.toFixed(1)}%`} />
        <DirCard label="Geographic DIR" value={data?.geo_dir}
          status={dirStatus(data?.geo_dir || 0)} desc="Approval rate ratio across districts" />
        <DirCard label="Equalized Odds Δ" value={Math.abs(data?.equalized_odds || 0)}
          status={Math.abs(data?.equalized_odds) < 0.1 ? 'PASS' : Math.abs(data?.equalized_odds) < 0.2 ? 'WATCH' : 'FAIL'}
          desc="Difference in error rates across gender groups" />
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-5">
        {/* Geo bar chart */}
        <Panel accentColor={colors.electric} title="Approval Rate by District">
          <ResponsiveContainer width="100%" height={220}>
            <BarChart data={geoData} margin={{ left: 5, right: 20, top: 10, bottom: 5 }}>
              <XAxis dataKey="district" tick={{ fill: colors.textSec, fontSize: 10, fontFamily: 'IBM Plex Mono' }} />
              <YAxis tick={{ fill: colors.textMut, fontSize: 9, fontFamily: 'IBM Plex Mono' }}
                tickFormatter={v => `${(v * 100).toFixed(0)}%`} domain={[0, 1]} />
              <Tooltip content={<CustomTooltip />} />
              <ReferenceLine y={0.80} stroke={colors.crimson} strokeDasharray="4 2"
                label={{ value: '80%', fill: colors.crimson, fontSize: 9, fontFamily: 'IBM Plex Mono' }} />
              <Bar dataKey="rate" radius={[4, 4, 0, 0]}>
                {geoData.map((entry, i) => (
                  <Cell key={i}
                    fill={entry.rate < 0.80 ? colors.crimson : colors.electric}
                    fillOpacity={0.85} />
                ))}
              </Bar>
            </BarChart>
          </ResponsiveContainer>

          {/* Range bar */}
          <div className="mt-3 px-1">
            <div className="flex justify-between text-xs font-mono mb-1.5">
              <span style={{ color: colors.textMut }}>District range</span>
              <span style={{ color: colors.electric }}>{(minRate * 100).toFixed(1)}% — {(maxRate * 100).toFixed(1)}%</span>
            </div>
            <div className="h-1.5 rounded-full" style={{ background: 'rgba(255,255,255,0.04)' }}>
              <div className="h-full rounded-full" style={{
                marginLeft: `${minRate * 100}%`,
                width: `${(maxRate - minRate) * 100}%`,
                background: `linear-gradient(90deg, ${colors.crimson}80, ${colors.electric})`,
              }} />
            </div>
          </div>
        </Panel>

        {/* Mitigation panel */}
        <Panel accentColor={data?.overall_dir < 0.85 ? colors.amber : colors.mint}
          title={data?.overall_dir < 0.85 ? "⚠ Mitigation Recommendations" : "✓ Fairness Status"}>
          {data?.overall_dir < 0.85 ? (
            <div className="space-y-3">
              {[
                { action: 'Threshold optimization', detail: 'Adjust decision boundary per demographic group to equalize approval rates' },
                { action: 'Reweighing preprocessing', detail: 'Up-weight underrepresented segments in model training data' },
                { action: 'Feature audit', detail: 'Remove proxy variables correlated with protected attributes (district, name)' },
                { action: 'Human-in-the-loop', detail: 'Review committee for borderline cases (PD 25–40%) across districts' },
                { action: 'Quarterly reassessment', detail: 'Fairness re-audit per RBI MRM 2026 Principle P7 schedule' },
              ].map((r, i) => (
                <div key={i} className="px-4 py-3 rounded-xl"
                  style={{ background: 'rgba(245,158,11,0.06)', border: '1px solid rgba(245,158,11,0.15)' }}>
                  <div className="text-xs font-semibold mb-0.5" style={{ color: colors.amber }}>{r.action}</div>
                  <div className="text-xs leading-relaxed" style={{ color: colors.textSec }}>{r.detail}</div>
                </div>
              ))}
            </div>
          ) : (
            <div className="flex flex-col items-center justify-center h-40 text-center">
              <div className="text-4xl mb-3">✓</div>
              <div className="text-sm font-semibold" style={{ color: colors.mint }}>Fairness metrics within threshold</div>
              <div className="text-xs mt-1" style={{ color: colors.textMut }}>DIR ≥ 0.90 across all sensitive features</div>
            </div>
          )}
        </Panel>
      </div>

      {/* By-group table */}
      <Panel accentColor={colors.electric} title="Group-Level Approval Rates">
        <div className="space-y-2">
          {Object.entries(data?.by_group || {}).map(([group, rate]) => (
            <div key={group} className="flex items-center gap-4 px-4 py-3 rounded-xl"
              style={{ background: 'rgba(255,255,255,0.02)' }}>
              <span className="text-xs font-mono w-20 flex-shrink-0" style={{ color: colors.textSec }}>{group}</span>
              <ProgressBar value={rate} max={1} color={rate < 0.8 ? colors.crimson : colors.electric} className="flex-1" />
              <span className="text-xs font-mono w-12 text-right" style={{ color: rate < 0.8 ? colors.crimson : colors.electric }}>
                {(rate * 100).toFixed(1)}%
              </span>
            </div>
          ))}
        </div>
      </Panel>
    </div>
  );
}
