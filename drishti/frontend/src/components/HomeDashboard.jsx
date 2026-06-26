import React, { useEffect, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { Eye, Shield, AlertTriangle, Activity, TrendingUp, ArrowRight } from 'lucide-react';
import { raksha, satya } from '../utils/api';
import { colors, ewsColor, pdColor } from '../utils/colors';
import { StatCard, Panel, Badge, Spinner } from './ui';

export default function HomeDashboard() {
  const navigate = useNavigate();
  const [board, setBoard] = useState(null);
  const [summary, setSummary] = useState(null);
  const [alerts, setAlerts] = useState([]);
  const [portSummary, setPortSummary] = useState(null);

  useEffect(() => {
    raksha.boardSummary().then(r => setBoard(r.data)).catch(() => {});
    raksha.complianceScorecard().then(r => setSummary(r.data)).catch(() => {});
    satya.alerts().then(r => setAlerts(r.data.alerts?.slice(0, 8) || [])).catch(() => {});
    satya.portfolioSummary().then(r => setPortSummary(r.data)).catch(() => {});
  }, []);

  const complianceColor = summary
    ? summary.overall_score >= 70 ? colors.mint : summary.overall_score >= 40 ? colors.amber : colors.crimson
    : colors.textMut;

  return (
    <div className="space-y-7 max-w-6xl mx-auto">
      {/* Header */}
      <div>
        <div className="flex items-baseline gap-4">
          <h1 className="text-3xl font-bold tracking-tight text-gradient-gold">DRISHTI</h1>
          <span className="text-xl font-serif italic" style={{ color: colors.goldDim }}>दृष्टि</span>
        </div>
        <p className="text-sm mt-1" style={{ color: colors.textSec }}>
          Digital Risk Intelligence & Scrutiny Hub · IDBI Innovate 2026 · Branch 554, Surat
        </p>
      </div>

      {/* Top stats */}
      <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
        <StatCard
          label="Models in Inventory"
          value={board?.total_models ?? '—'}
          sub={`Tier-1: ${board?.tier1_count ?? '—'} · Validated: ${board?.compliant_count ?? '—'}`}
          color={colors.gold}
          icon={Activity}
        />
        <StatCard
          label="MRM Compliance"
          value={summary ? `${summary.overall_score}%` : '—'}
          sub="RBI MRM 2026 · Target 100%"
          color={complianceColor}
          icon={Shield}
        />
        <StatCard
          label="RED EWS Accounts"
          value={portSummary?.red_count ?? '—'}
          sub="Imminent SMA risk"
          color={colors.crimson}
          icon={AlertTriangle}
          pulse={!!(portSummary?.red_count > 0)}
        />
        <StatCard
          label="At-Risk Exposure"
          value={portSummary ? `₹${portSummary.at_risk_exposure?.toFixed(0)}L` : '—'}
          sub="AMBER + RED accounts"
          color={colors.violet}
          icon={TrendingUp}
        />
      </div>

      {/* RED alert banner */}
      {portSummary?.red_count > 0 && (
        <div
          className="flex items-center gap-4 px-5 py-3 rounded-2xl cursor-pointer"
          style={{
            background: 'linear-gradient(135deg, rgba(255,91,91,0.08), rgba(255,91,91,0.04))',
            border: '1px solid rgba(255,91,91,0.25)',
            boxShadow: '0 0 30px rgba(255,91,91,0.08)',
          }}
          onClick={() => navigate('/satya')}
        >
          <div className="h-2.5 w-2.5 rounded-full flex-shrink-0 pulse-dot" style={{ background: colors.crimson }} />
          <span className="text-sm font-semibold" style={{ color: colors.crimson }}>
            {portSummary.red_count} accounts in RED EWS stage — ₹{portSummary.at_risk_exposure?.toFixed(0)}L at risk
          </span>
          <span className="ml-auto text-xs font-mono flex items-center gap-1" style={{ color: colors.crimson }}>
            View dashboard <ArrowRight size={12} />
          </span>
        </div>
      )}

      {/* Module cards */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-5">
        {/* VIVEKA */}
        <ModuleCard
          title="VIVEKA" sublabel="विवेक" desc="XAI Validation Engine"
          detail="SHAP · LIME · Fairlearn · Adverse Action"
          color={colors.electric} icon={Eye}
          onClick={() => navigate('/viveka')}
          metrics={[
            { label: 'Features', value: '10' },
            { label: 'Explainability', value: 'SHAP+LIME' },
          ]}
        />
        {/* RAKSHA */}
        <ModuleCard
          title="RAKSHA" sublabel="रक्षा" desc="MRM Governance Hub"
          detail="Model Inventory · Tiering · RBI MRM 2026"
          color={colors.mint} icon={Shield}
          onClick={() => navigate('/raksha')}
          metrics={[
            { label: 'Compliance', value: summary ? `${summary.overall_score}%` : '—', alert: summary?.overall_score < 40 },
            { label: 'Critical', value: board?.critical_findings ?? '—', alert: board?.critical_findings > 0 },
          ]}
        />
        {/* SATYA */}
        <ModuleCard
          title="SATYA" sublabel="सत्य" desc="Early Warning System"
          detail="PD Signals · PSI Monitor · Portfolio Heatmap"
          color={colors.violet} icon={AlertTriangle}
          onClick={() => navigate('/satya')}
          metrics={[
            { label: 'RED', value: portSummary?.red_count ?? '—', alert: portSummary?.red_count > 0 },
            { label: 'AMBER', value: portSummary?.amber_count ?? '—' },
          ]}
        />
      </div>

      {/* Alert feed */}
      <Panel accentColor={colors.gold} title="Live EWS Alert Feed" titleRight={
        <button onClick={() => navigate('/satya')} className="text-xs font-mono flex items-center gap-1" style={{ color: colors.gold }}>
          All alerts <ArrowRight size={11} />
        </button>
      }>
        {alerts.length === 0 ? (
          <div className="text-xs font-mono py-4" style={{ color: colors.textMut }}>Loading alerts...</div>
        ) : (
          <div className="space-y-1.5">
            {alerts.map((a, i) => (
              <div key={a.id}
                onClick={() => navigate(`/satya/borrower/${a.borrower_id}`)}
                className="flex items-center gap-4 px-4 py-3 rounded-xl cursor-pointer transition-all hover:opacity-80"
                style={{
                  background: a.severity === 1 ? 'rgba(255,91,91,0.05)' : 'rgba(245,158,11,0.05)',
                  border: `1px solid ${a.severity === 1 ? 'rgba(255,91,91,0.12)' : 'rgba(245,158,11,0.12)'}`,
                }}
              >
                <div className="h-1.5 w-1.5 rounded-full flex-shrink-0"
                  style={{ background: a.severity === 1 ? colors.crimson : colors.amber }} />
                <span className="text-xs font-mono font-semibold w-32 flex-shrink-0"
                  style={{ color: a.severity === 1 ? colors.crimson : colors.amber }}>
                  {a.alert_type}
                </span>
                <span className="text-xs flex-1 truncate" style={{ color: colors.textSec }}>{a.name}</span>
                <span className="text-xs flex-shrink-0" style={{ color: colors.textMut }}>{a.shap_driver}</span>
                <span className="text-xs font-mono flex-shrink-0" style={{ color: colors.textMut }}>
                  {new Date(a.raised_at).toLocaleDateString()}
                </span>
              </div>
            ))}
          </div>
        )}
      </Panel>
    </div>
  );
}

function ModuleCard({ title, sublabel, desc, detail, color, icon: Icon, onClick, metrics }) {
  return (
    <div
      onClick={onClick}
      className="module-card rounded-2xl p-5 cursor-pointer relative overflow-hidden"
      style={{
        background: `linear-gradient(145deg, rgba(10,22,40,0.8) 0%, rgba(5,13,26,0.9) 100%)`,
        border: `1px solid ${color}22`,
        boxShadow: `0 0 40px ${color}08, inset 0 1px 0 rgba(255,255,255,0.03)`,
      }}
    >
      {/* Bg glow */}
      <div className="absolute top-0 right-0 w-32 h-32 rounded-full blur-3xl opacity-20 pointer-events-none"
        style={{ background: color }} />

      <div className="relative">
        {/* Header */}
        <div className="flex items-center gap-2.5 mb-3">
          <div className="w-8 h-8 rounded-xl flex items-center justify-center flex-shrink-0"
            style={{ background: `${color}15`, border: `1px solid ${color}30` }}>
            <Icon size={15} style={{ color }} />
          </div>
          <div>
            <div className="font-bold font-mono text-sm tracking-wide" style={{ color }}>{title}</div>
            <div className="text-xs font-serif italic" style={{ color: colors.goldDim }}>{sublabel} — {desc}</div>
          </div>
        </div>

        {/* Detail */}
        <p className="text-xs mb-4 leading-relaxed" style={{ color: colors.textMut }}>{detail}</p>

        {/* Metrics */}
        <div className="flex gap-3 mb-4">
          {metrics.map((m, i) => (
            <div key={i} className="px-3 py-2 rounded-xl flex-1"
              style={{ background: m.alert ? `${colors.crimson}10` : `${color}08`, border: `1px solid ${m.alert ? colors.crimson : color}20` }}>
              <div className="text-xs" style={{ color: colors.textMut }}>{m.label}</div>
              <div className="text-base font-bold font-mono mt-0.5" style={{ color: m.alert ? colors.crimson : color }}>{m.value}</div>
            </div>
          ))}
        </div>

        {/* CTA */}
        <div className="flex items-center gap-1.5 text-xs font-mono" style={{ color }}>
          Open Module <ArrowRight size={11} />
        </div>
      </div>
    </div>
  );
}
