import React, { useEffect, useState } from 'react';
import { BarChart, Bar, XAxis, YAxis, Tooltip, ResponsiveContainer, ReferenceLine, Cell } from 'recharts';
import { viveka } from '../../utils/api';
import { colors, dirColor } from '../../utils/colors';

function MetricCard({ label, value, status, desc }) {
  const c = status === 'PASS' ? colors.mint : status === 'WATCH' ? '#F59E0B' : colors.crimson;
  return (
    <div className="rounded-xl p-4 border" style={{ background: colors.navy3, borderColor: c + '40' }}>
      <div className="text-xs font-mono" style={{ color: colors.textSec }}>{label}</div>
      <div className="text-2xl font-bold font-mono mt-1" style={{ color: c }}>{value}</div>
      <div className="mt-1 px-2 py-0.5 rounded text-xs font-mono inline-block" style={{ background: c + '20', color: c }}>{status}</div>
      {desc && <div className="text-xs mt-2" style={{ color: colors.textMut }}>{desc}</div>}
    </div>
  );
}

export default function FairnessAudit() {
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    viveka.fairnessAudit().then(r => { setData(r.data); setLoading(false); }).catch(() => setLoading(false));
  }, []);

  if (loading) return <div className="text-xs font-mono p-6" style={{ color: colors.textMut }}>Running Fairlearn audit...</div>;
  if (!data) return <div className="text-xs font-mono p-6" style={{ color: colors.crimson }}>Failed to load fairness audit.</div>;

  const geoData = Object.entries(data.by_geography || {}).map(([district, rate]) => ({
    district,
    approval_rate: rate,
  }));

  const dirStatus = (d) => d >= 0.90 ? 'PASS' : d >= 0.80 ? 'WATCH' : 'FAIL';

  return (
    <div className="space-y-6">
      <div>
        <h2 className="text-xl font-bold font-mono" style={{ color: colors.electric }}>VIVEKA — Fairness Audit</h2>
        <p className="text-xs mt-1" style={{ color: colors.textSec }}>Fairlearn · Disparate Impact Ratio · Equalized Odds</p>
      </div>

      <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
        <MetricCard
          label="DIR Overall (Gender)"
          value={data.overall_dir?.toFixed(3)}
          status={dirStatus(data.overall_dir)}
          desc="Disparate Impact Ratio · ≥0.80 required"
        />
        <MetricCard
          label="DIR — Male vs Female"
          value={data.by_gender?.dir?.toFixed(3)}
          status={dirStatus(data.by_gender?.dir || 0)}
          desc={`Male: ${(data.by_gender?.male * 100).toFixed(1)}% · Female: ${(data.by_gender?.female * 100).toFixed(1)}%`}
        />
        <MetricCard
          label="Geographic DIR"
          value={data.geo_dir?.toFixed(3)}
          status={dirStatus(data.geo_dir || 0)}
          desc="Approval rate across districts"
        />
        <MetricCard
          label="Equalized Odds Diff"
          value={Math.abs(data.equalized_odds)?.toFixed(3)}
          status={Math.abs(data.equalized_odds) < 0.1 ? 'PASS' : Math.abs(data.equalized_odds) < 0.2 ? 'WATCH' : 'FAIL'}
          desc="Difference in error rates across groups"
        />
      </div>

      {/* Geo chart */}
      <div className="rounded-xl border p-5" style={{ background: colors.navy3, borderColor: colors.electric + '30' }}>
        <h3 className="font-bold font-mono text-sm mb-4" style={{ color: colors.electric }}>Approval Rate by District</h3>
        <ResponsiveContainer width="100%" height={220}>
          <BarChart data={geoData} margin={{ left: 20, right: 20, top: 10, bottom: 5 }}>
            <XAxis dataKey="district" tick={{ fill: colors.textSec, fontSize: 11, fontFamily: 'IBM Plex Mono' }} />
            <YAxis tick={{ fill: colors.textSec, fontSize: 10, fontFamily: 'IBM Plex Mono' }} tickFormatter={v => `${(v * 100).toFixed(0)}%`} />
            <Tooltip
              contentStyle={{ background: colors.navy4, border: `1px solid ${colors.goldDim}`, color: colors.textPri, fontFamily: 'IBM Plex Mono', fontSize: 11 }}
              formatter={(v) => `${(v * 100).toFixed(1)}%`}
            />
            <ReferenceLine y={0.8} stroke={colors.crimson} strokeDasharray="4 2" label={{ value: '80% threshold', fill: colors.crimson, fontSize: 10, fontFamily: 'IBM Plex Mono' }} />
            <Bar dataKey="approval_rate">
              {geoData.map((entry, i) => (
                <Cell key={i} fill={entry.approval_rate < 0.8 ? colors.crimson : colors.electric} />
              ))}
            </Bar>
          </BarChart>
        </ResponsiveContainer>
      </div>

      {/* Mitigation */}
      {data.overall_dir < 0.85 && (
        <div className="rounded-xl border p-5" style={{ background: colors.navy3, borderColor: '#F59E0B40' }}>
          <h3 className="font-bold font-mono text-sm mb-3" style={{ color: '#F59E0B' }}>Mitigation Recommendations</h3>
          <div className="space-y-2">
            {[
              'Apply threshold optimization — adjust decision boundary per demographic group',
              'Consider reweighing preprocessing — up-weight underrepresented segments',
              'Audit feature set — remove proxy variables that correlate with protected attributes',
              'Implement human-in-the-loop review for borderline cases (PD 25–40%)',
              'Conduct quarterly fairness re-assessment per RBI MRM 2026 Principle P7',
            ].map((r, i) => (
              <div key={i} className="flex gap-2 text-xs" style={{ color: colors.textSec }}>
                <span style={{ color: '#F59E0B' }}>{i + 1}.</span>
                <span>{r}</span>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}
