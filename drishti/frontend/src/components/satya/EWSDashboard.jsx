import React, { useEffect, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import Plot from 'react-plotly.js';
import { ArrowRight, AlertTriangle } from 'lucide-react';
import { satya } from '../../utils/api';
import { colors, ewsColor } from '../../utils/colors';
import { StatCard, Panel, SectionHead, Spinner, Badge } from '../ui';

export default function EWSDashboard() {
  const navigate = useNavigate();
  const [summary, setSummary] = useState(null);
  const [heatmap, setHeatmap] = useState(null);
  const [alerts, setAlerts] = useState([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    Promise.all([satya.portfolioSummary(), satya.heatmap(), satya.alerts()])
      .then(([s, h, a]) => {
        setSummary(s.data);
        setHeatmap(h.data);
        setAlerts(a.data.alerts?.slice(0, 10) || []);
        setLoading(false);
      }).catch(() => setLoading(false));
  }, []);

  if (loading) return <Spinner color={colors.violet} />;

  // Plotly heatmap
  const plotData = heatmap ? [{
    type: 'heatmap',
    x: heatmap.stages,
    y: heatmap.sectors,
    z: heatmap.matrix,
    colorscale: [
      [0, 'rgba(10,22,40,0.8)'],
      [0.01, 'rgba(80,227,194,0.2)'],
      [0.4, 'rgba(167,139,250,0.6)'],
      [0.7, 'rgba(245,158,11,0.8)'],
      [1.0, 'rgba(255,91,91,1)'],
    ],
    showscale: false,
    text: heatmap.matrix?.map(row => row.map(v => v > 0 ? `${v}` : '')),
    texttemplate: '%{text}',
    textfont: { color: '#E8E2D4', family: 'IBM Plex Mono', size: 14 },
    hovertemplate: '<b>%{y}</b> · %{x}<br>%{z} accounts<extra></extra>',
  }] : [];

  const plotLayout = {
    paper_bgcolor: 'transparent',
    plot_bgcolor: 'transparent',
    font: { family: 'IBM Plex Mono', color: colors.textSec, size: 10 },
    xaxis: { color: colors.textMut, tickfont: { size: 11 }, gridcolor: 'rgba(255,255,255,0.03)' },
    yaxis: { color: colors.textMut, tickfont: { size: 10 }, automargin: true, gridcolor: 'rgba(255,255,255,0.03)' },
    margin: { l: 90, r: 20, t: 10, b: 40 },
    height: 280,
  };

  return (
    <div className="space-y-6 max-w-6xl mx-auto">
      <SectionHead
        title="SATYA — EWS Dashboard"
        accent="सत्य"
        subtitle="Early Warning System · IndAS 109 Stage Migration · SICR Monitoring"
        color={colors.violet}
      />

      {/* RED alert banner */}
      {summary?.red_count > 0 && (
        <div
          className="flex items-center gap-4 px-5 py-3.5 rounded-2xl cursor-pointer"
          style={{
            background: 'linear-gradient(135deg, rgba(255,91,91,0.08), rgba(255,91,91,0.03))',
            border: '1px solid rgba(255,91,91,0.3)',
            boxShadow: '0 0 40px rgba(255,91,91,0.06)',
          }}
          onClick={() => navigate('/satya/portfolio')}
        >
          <AlertTriangle size={16} style={{ color: colors.crimson, flexShrink: 0 }} />
          <div>
            <span className="text-sm font-semibold" style={{ color: colors.crimson }}>
              {summary.red_count} accounts in RED EWS stage
            </span>
            <span className="text-sm ml-2" style={{ color: colors.textSec }}>
              — ₹{summary.at_risk_exposure?.toFixed(0)}L total at-risk exposure (AMBER + RED)
            </span>
          </div>
          <span className="ml-auto text-xs font-mono flex items-center gap-1 flex-shrink-0" style={{ color: colors.crimson }}>
            View portfolio <ArrowRight size={11} />
          </span>
        </div>
      )}

      {/* Stats */}
      <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
        <StatCard label="Total Accounts" value={summary?.total_accounts} sub="MSME · Surat cluster" color={colors.gold} />
        <StatCard label="RED Stage" value={summary?.red_count} sub="Imminent SMA risk" color={colors.crimson} pulse={summary?.red_count > 0} />
        <StatCard label="Stage 2 IndAS" value={summary?.stage2_count} sub="SICR triggered" color={colors.amber} />
        <StatCard label="At-Risk (₹L)" value={summary?.at_risk_exposure?.toFixed(0)} sub="AMBER + RED exposure" color={colors.violet} />
      </div>

      {/* Heatmap + Alerts */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-5">
        <Panel accentColor={colors.violet} title="Portfolio Heatmap — Sector × EWS Stage"
          titleRight={
            <button onClick={() => navigate('/satya/portfolio')} className="text-xs font-mono flex items-center gap-1" style={{ color: colors.violet }}>
              Full portfolio <ArrowRight size={11} />
            </button>
          }>
          {heatmap && (
            <Plot
              data={plotData}
              layout={plotLayout}
              config={{ displayModeBar: false, responsive: true }}
              style={{ width: '100%' }}
            />
          )}
          {/* Stage legend */}
          <div className="flex gap-4 mt-2 justify-center">
            {['GREEN', 'AMBER', 'RED'].map(s => (
              <div key={s} className="flex items-center gap-1.5 text-xs font-mono">
                <div className="w-2 h-2 rounded-sm" style={{ background: ewsColor(s) }} />
                <span style={{ color: colors.textMut }}>{s}</span>
              </div>
            ))}
          </div>
        </Panel>

        <Panel accentColor={colors.violet} title="Live Alert Feed"
          titleRight={
            <button onClick={() => navigate('/satya/portfolio?ews=RED')} className="text-xs font-mono flex items-center gap-1" style={{ color: colors.crimson }}>
              RED only <ArrowRight size={11} />
            </button>
          }>
          <div className="space-y-2 max-h-72 overflow-y-auto pr-1">
            {alerts.map(a => (
              <div key={a.id}
                onClick={() => navigate(`/satya/borrower/${a.borrower_id}`)}
                className="flex items-start gap-3 px-3 py-3 rounded-xl cursor-pointer transition-all hover:opacity-75"
                style={{
                  background: a.severity === 1 ? 'rgba(255,91,91,0.06)' : 'rgba(245,158,11,0.06)',
                  border: `1px solid ${a.severity === 1 ? 'rgba(255,91,91,0.15)' : 'rgba(245,158,11,0.15)'}`,
                }}>
                <div className="h-1.5 w-1.5 rounded-full mt-1.5 flex-shrink-0"
                  style={{ background: a.severity === 1 ? colors.crimson : colors.amber }} />
                <div className="flex-1 min-w-0">
                  <div className="flex items-center gap-2 mb-0.5">
                    <span className="text-xs font-mono font-semibold"
                      style={{ color: a.severity === 1 ? colors.crimson : colors.amber }}>
                      {a.alert_type}
                    </span>
                  </div>
                  <div className="text-xs truncate" style={{ color: colors.textSec }}>{a.name}</div>
                  <div className="text-xs mt-0.5 truncate" style={{ color: colors.textMut }}>{a.shap_driver}</div>
                </div>
                <span className="text-xs font-mono flex-shrink-0 mt-0.5" style={{ color: colors.textMut }}>
                  {new Date(a.raised_at).toLocaleDateString()}
                </span>
              </div>
            ))}
          </div>
        </Panel>
      </div>

      {/* Sector breakdown */}
      {summary?.sector_breakdown && (
        <Panel accentColor={colors.violet} title="Sector Risk Breakdown">
          <div className="grid grid-cols-2 lg:grid-cols-3 gap-3">
            {Object.entries(summary.sector_breakdown).map(([sector, data]) => {
              const redPct = data.count ? data.red / data.count : 0;
              const c = redPct > 0.3 ? colors.crimson : redPct > 0.1 ? colors.amber : colors.mint;
              return (
                <div key={sector} className="px-4 py-3 rounded-xl"
                  style={{ background: `${c}08`, border: `1px solid ${c}18` }}>
                  <div className="flex justify-between items-center mb-2">
                    <span className="text-xs font-semibold" style={{ color: colors.textSec }}>{sector}</span>
                    <span className="text-xs font-mono" style={{ color: colors.textMut }}>{data.count} accounts</span>
                  </div>
                  <div className="flex items-center gap-2">
                    <div className="flex-1 h-1 rounded-full" style={{ background: 'rgba(255,255,255,0.05)' }}>
                      <div className="h-full rounded-full" style={{ width: `${redPct * 100}%`, background: c }} />
                    </div>
                    <span className="text-xs font-mono" style={{ color: c }}>{data.red} RED</span>
                  </div>
                </div>
              );
            })}
          </div>
        </Panel>
      )}
    </div>
  );
}
