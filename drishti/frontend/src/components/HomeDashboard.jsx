import React, { useEffect, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { Eye, Shield, AlertTriangle, Activity } from 'lucide-react';
import { raksha, satya } from '../utils/api';
import { colors, ewsColor } from '../utils/colors';

function StatCard({ label, value, sub, color }) {
  return (
    <div className="rounded-xl p-5 border" style={{ background: colors.navy3, borderColor: color + '40' }}>
      <div className="text-xs font-mono mb-1" style={{ color: colors.textSec }}>{label}</div>
      <div className="text-3xl font-bold font-mono" style={{ color }}>{value}</div>
      {sub && <div className="text-xs mt-1" style={{ color: colors.textMut }}>{sub}</div>}
    </div>
  );
}

export default function HomeDashboard() {
  const navigate = useNavigate();
  const [summary, setSummary] = useState(null);
  const [board, setBoard] = useState(null);
  const [alerts, setAlerts] = useState([]);
  const [portSummary, setPortSummary] = useState(null);

  useEffect(() => {
    raksha.boardSummary().then(r => setBoard(r.data)).catch(() => {});
    raksha.complianceScorecard().then(r => setSummary(r.data)).catch(() => {});
    satya.alerts().then(r => setAlerts(r.data.alerts?.slice(0, 8) || [])).catch(() => {});
    satya.portfolioSummary().then(r => setPortSummary(r.data)).catch(() => {});
  }, []);

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-bold font-serif" style={{ color: colors.gold }}>DRISHTI — दृष्टि</h1>
        <p className="text-sm mt-1" style={{ color: colors.textSec }}>Banking Intelligence Platform · IDBI Innovate 2026 · Branch 554, Surat</p>
      </div>

      {/* Stat cards */}
      <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
        <StatCard label="Models in Inventory" value={board?.total_models ?? '—'} sub="8 total · 3 Tier-1" color={colors.gold} />
        <StatCard label="RBI MRM Compliance" value={summary ? `${summary.overall_score}%` : '—'} sub="Target: 100%" color={summary?.overall_score < 40 ? colors.crimson : '#F59E0B'} />
        <StatCard label="RED EWS Alerts" value={portSummary?.red_count ?? '—'} sub="Immediate action required" color={colors.crimson} />
        <StatCard label="At-Risk Exposure" value={portSummary ? `₹${portSummary.at_risk_exposure.toFixed(0)}L` : '—'} sub="AMBER + RED accounts" color={colors.violet} />
      </div>

      {/* Module cards + activity */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-4">
        {/* VIVEKA */}
        <div className="rounded-xl p-5 border cursor-pointer hover:border-electric transition-all"
          style={{ background: colors.navy3, borderColor: colors.electric + '40' }}
          onClick={() => navigate('/viveka')}>
          <div className="flex items-center gap-2 mb-3">
            <Eye size={18} style={{ color: colors.electric }} />
            <span className="font-bold font-mono" style={{ color: colors.electric }}>VIVEKA</span>
            <span className="text-xs font-serif italic" style={{ color: colors.goldDim }}>विवेक</span>
          </div>
          <p className="text-xs mb-3" style={{ color: colors.textSec }}>XAI Validation Engine — SHAP, LIME, Fairlearn</p>
          <div className="text-xs font-mono p-2 rounded" style={{ background: colors.navy4, color: colors.textSec }}>
            Real SHAP values · Fairness audit · Adverse action
          </div>
          <button className="mt-3 text-xs font-mono px-3 py-1.5 rounded" style={{ background: colors.electric + '20', color: colors.electric, border: `1px solid ${colors.electric}40` }}>
            Open XAI Dashboard →
          </button>
        </div>

        {/* RAKSHA */}
        <div className="rounded-xl p-5 border cursor-pointer hover:border-mint transition-all"
          style={{ background: colors.navy3, borderColor: colors.mint + '40' }}
          onClick={() => navigate('/raksha')}>
          <div className="flex items-center gap-2 mb-3">
            <Shield size={18} style={{ color: colors.mint }} />
            <span className="font-bold font-mono" style={{ color: colors.mint }}>RAKSHA</span>
            <span className="text-xs font-serif italic" style={{ color: colors.goldDim }}>रक्षा</span>
          </div>
          <p className="text-xs mb-3" style={{ color: colors.textSec }}>MRM Governance Hub — Model inventory, tiering, RBI compliance</p>
          <div className="grid grid-cols-2 gap-2 text-xs font-mono">
            <div className="p-2 rounded" style={{ background: colors.navy4 }}>
              <div style={{ color: colors.crimson }}>{board?.critical_findings ?? '—'} Critical</div>
              <div style={{ color: colors.textMut }}>findings</div>
            </div>
            <div className="p-2 rounded" style={{ background: colors.navy4 }}>
              <div style={{ color: summary?.overall_score < 40 ? colors.crimson : '#F59E0B' }}>{summary?.overall_score ?? '—'}%</div>
              <div style={{ color: colors.textMut }}>compliance</div>
            </div>
          </div>
          <button className="mt-3 text-xs font-mono px-3 py-1.5 rounded" style={{ background: colors.mint + '20', color: colors.mint, border: `1px solid ${colors.mint}40` }}>
            Open MRM Hub →
          </button>
        </div>

        {/* SATYA */}
        <div className="rounded-xl p-5 border cursor-pointer hover:border-violet transition-all"
          style={{ background: colors.navy3, borderColor: colors.violet + '40' }}
          onClick={() => navigate('/satya')}>
          <div className="flex items-center gap-2 mb-3">
            <AlertTriangle size={18} style={{ color: colors.violet }} />
            <span className="font-bold font-mono" style={{ color: colors.violet }}>SATYA</span>
            <span className="text-xs font-serif italic" style={{ color: colors.goldDim }}>सत्य</span>
          </div>
          <p className="text-xs mb-3" style={{ color: colors.textSec }}>Early Warning System — PD signals, PSI monitoring, portfolio heatmaps</p>
          <div className="grid grid-cols-3 gap-1 text-xs font-mono">
            <div className="p-2 rounded text-center" style={{ background: colors.mint + '15' }}>
              <div style={{ color: colors.mint }}>{portSummary?.green_count ?? '—'}</div>
              <div style={{ color: colors.textMut }}>GREEN</div>
            </div>
            <div className="p-2 rounded text-center" style={{ background: '#F59E0B15' }}>
              <div style={{ color: '#F59E0B' }}>{portSummary?.amber_count ?? '—'}</div>
              <div style={{ color: colors.textMut }}>AMBER</div>
            </div>
            <div className="p-2 rounded text-center" style={{ background: colors.crimson + '15' }}>
              <div style={{ color: colors.crimson }}>{portSummary?.red_count ?? '—'}</div>
              <div style={{ color: colors.textMut }}>RED</div>
            </div>
          </div>
          <button className="mt-3 text-xs font-mono px-3 py-1.5 rounded" style={{ background: colors.violet + '20', color: colors.violet, border: `1px solid ${colors.violet}40` }}>
            Open EWS Dashboard →
          </button>
        </div>
      </div>

      {/* Activity feed */}
      <div className="rounded-xl border p-5" style={{ background: colors.navy3, borderColor: colors.goldDim + '30' }}>
        <div className="flex items-center gap-2 mb-4">
          <Activity size={16} style={{ color: colors.gold }} />
          <h3 className="font-bold font-mono text-sm" style={{ color: colors.gold }}>Live EWS Alert Feed</h3>
        </div>
        <div className="space-y-2">
          {alerts.length === 0 && <div className="text-xs" style={{ color: colors.textMut }}>Loading alerts...</div>}
          {alerts.map(a => (
            <div key={a.id} className="flex items-start gap-3 p-3 rounded-lg" style={{ background: colors.navy4 }}>
              <span className="h-2 w-2 rounded-full mt-1 flex-shrink-0" style={{ background: a.severity === 1 ? colors.crimson : '#F59E0B' }}></span>
              <div className="flex-1 min-w-0">
                <div className="flex items-center gap-2">
                  <span className="text-xs font-mono font-semibold" style={{ color: a.severity === 1 ? colors.crimson : '#F59E0B' }}>{a.alert_type}</span>
                  <span className="text-xs" style={{ color: colors.textSec }}>{a.name}</span>
                </div>
                <div className="text-xs mt-0.5" style={{ color: colors.textMut }}>{a.trigger_reason}</div>
              </div>
              <span className="text-xs font-mono flex-shrink-0" style={{ color: colors.textMut }}>
                {new Date(a.raised_at).toLocaleDateString()}
              </span>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}
