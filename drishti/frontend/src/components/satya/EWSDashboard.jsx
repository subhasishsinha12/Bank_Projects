import React, { useEffect, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import Plot from 'react-plotly.js';
import { satya } from '../../utils/api';
import { colors, ewsColor } from '../../utils/colors';

export default function EWSDashboard() {
  const navigate = useNavigate();
  const [summary, setSummary] = useState(null);
  const [heatmap, setHeatmap] = useState(null);
  const [alerts, setAlerts] = useState([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    Promise.all([
      satya.portfolioSummary(),
      satya.heatmap(),
      satya.alerts(),
    ]).then(([s, h, a]) => {
      setSummary(s.data);
      setHeatmap(h.data);
      setAlerts(a.data.alerts?.slice(0, 10) || []);
      setLoading(false);
    }).catch(() => setLoading(false));
  }, []);

  const plotData = heatmap ? [{
    type: 'heatmap',
    x: heatmap.stages,
    y: heatmap.sectors,
    z: heatmap.matrix,
    colorscale: [
      [0, colors.navy4],
      [0.5, colors.violet + 'AA'],
      [1, colors.violet],
    ],
    showscale: true,
    text: heatmap.matrix?.map(row => row.map(v => `${v} accounts`)),
    texttemplate: '%{z}',
    textfont: { color: colors.textPri, family: 'IBM Plex Mono', size: 12 },
  }] : [];

  const plotLayout = {
    paper_bgcolor: colors.navy3,
    plot_bgcolor: colors.navy3,
    font: { family: 'IBM Plex Mono', color: colors.textSec, size: 11 },
    xaxis: { color: colors.textSec, tickfont: { size: 11 } },
    yaxis: { color: colors.textSec, tickfont: { size: 11 }, automargin: true },
    margin: { l: 90, r: 60, t: 20, b: 40 },
    height: 280,
  };

  if (loading) return <div className="text-xs font-mono p-6" style={{ color: colors.textMut }}>Loading EWS data...</div>;

  return (
    <div className="space-y-6">
      {/* Red alert banner */}
      {summary?.red_count > 0 && (
        <div className="flex items-center gap-3 px-4 py-3 rounded-xl border animate-pulse"
          style={{ background: colors.crimson + '15', borderColor: colors.crimson + '60' }}>
          <span className="h-2.5 w-2.5 rounded-full flex-shrink-0" style={{ background: colors.crimson }}></span>
          <span className="text-sm font-mono font-semibold" style={{ color: colors.crimson }}>
            {summary.red_count} accounts in RED EWS stage — ₹{summary.at_risk_exposure?.toFixed(0)}L at risk
          </span>
          <button onClick={() => navigate('/satya/portfolio?ews=RED')}
            className="ml-auto text-xs font-mono px-3 py-1 rounded"
            style={{ background: colors.crimson + '20', color: colors.crimson, border: `1px solid ${colors.crimson}40` }}>
            View RED Accounts →
          </button>
        </div>
      )}

      <div>
        <h2 className="text-xl font-bold font-mono" style={{ color: colors.violet }}>SATYA — EWS Dashboard</h2>
        <p className="text-xs mt-1" style={{ color: colors.textSec }}>Early Warning System · IndAS 109 · SICR Monitoring</p>
      </div>

      {/* Stats */}
      <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
        {[
          { label: 'Total Accounts', value: summary?.total_accounts, color: colors.gold },
          { label: 'RED Stage', value: summary?.red_count, color: colors.crimson },
          { label: 'Stage 2 IndAS', value: summary?.stage2_count, color: '#F59E0B' },
          { label: 'At-Risk (₹L)', value: summary?.at_risk_exposure?.toFixed(0), color: colors.violet },
        ].map((s, i) => (
          <div key={i} className="rounded-xl border p-4" style={{ background: colors.navy3, borderColor: s.color + '30' }}>
            <div className="text-xs font-mono" style={{ color: colors.textSec }}>{s.label}</div>
            <div className="text-2xl font-bold font-mono mt-1" style={{ color: s.color }}>{s.value ?? '—'}</div>
          </div>
        ))}
      </div>

      {/* Heatmap + Alerts */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        <div className="rounded-xl border p-5" style={{ background: colors.navy3, borderColor: colors.violet + '30' }}>
          <h3 className="font-bold font-mono text-sm mb-3" style={{ color: colors.violet }}>Portfolio Heatmap — Sector × EWS Stage</h3>
          {heatmap && (
            <Plot
              data={plotData}
              layout={plotLayout}
              config={{ displayModeBar: false, responsive: true }}
              style={{ width: '100%' }}
            />
          )}
        </div>

        <div className="rounded-xl border p-5" style={{ background: colors.navy3, borderColor: colors.violet + '30' }}>
          <h3 className="font-bold font-mono text-sm mb-3" style={{ color: colors.violet }}>Live Alert Feed</h3>
          <div className="space-y-2 max-h-72 overflow-y-auto">
            {alerts.map(a => (
              <div key={a.id}
                onClick={() => navigate(`/satya/borrower/${a.borrower_id}`)}
                className="flex items-start gap-3 p-3 rounded-lg cursor-pointer hover:opacity-80"
                style={{ background: colors.navy4 }}>
                <span className="h-2 w-2 rounded-full mt-1.5 flex-shrink-0"
                  style={{ background: a.severity === 1 ? colors.crimson : '#F59E0B' }}></span>
                <div className="flex-1 min-w-0">
                  <div className="flex items-center gap-2">
                    <span className="text-xs font-mono font-semibold"
                      style={{ color: a.severity === 1 ? colors.crimson : '#F59E0B' }}>{a.alert_type}</span>
                  </div>
                  <div className="text-xs" style={{ color: colors.textSec }}>{a.name}</div>
                  <div className="text-xs mt-0.5" style={{ color: colors.textMut }}>{a.shap_driver}</div>
                </div>
                <div className="text-xs font-mono flex-shrink-0" style={{ color: colors.textMut }}>
                  {new Date(a.raised_at).toLocaleDateString()}
                </div>
              </div>
            ))}
          </div>
        </div>
      </div>
    </div>
  );
}
