import React, { useEffect, useState } from 'react';
import { ChevronDown, ChevronUp, Copy, Check } from 'lucide-react';
import { raksha } from '../../utils/api';
import { colors } from '../../utils/colors';

function ScoreGauge({ score }) {
  const c = score >= 70 ? colors.mint : score >= 40 ? '#F59E0B' : colors.crimson;
  return (
    <div className="flex flex-col items-center justify-center p-8">
      <div className="relative w-40 h-40">
        <svg viewBox="0 0 100 100" className="w-full h-full -rotate-90">
          <circle cx="50" cy="50" r="40" fill="none" stroke={colors.navy4} strokeWidth="8" />
          <circle cx="50" cy="50" r="40" fill="none" stroke={c} strokeWidth="8"
            strokeDasharray={`${score * 2.51} 251`} strokeLinecap="round" />
        </svg>
        <div className="absolute inset-0 flex flex-col items-center justify-center">
          <div className="text-4xl font-bold font-mono" style={{ color: c }}>{score}</div>
          <div className="text-xs font-mono" style={{ color: colors.textMut }}>/100</div>
        </div>
      </div>
      <div className="text-sm font-mono mt-2" style={{ color: c }}>
        {score >= 70 ? 'COMPLIANT' : score >= 40 ? 'PARTIAL' : 'NON-COMPLIANT'}
      </div>
      <div className="text-xs mt-1" style={{ color: colors.textMut }}>RBI MRM 2026 Overall Score</div>
    </div>
  );
}

export default function ComplianceScorecard() {
  const [data, setData] = useState(null);
  const [expanded, setExpanded] = useState(null);
  const [copied, setCopied] = useState(false);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    raksha.complianceScorecard().then(r => { setData(r.data); setLoading(false); }).catch(() => setLoading(false));
  }, []);

  const statusColor = (s) => s === 'COMPLIANT' ? colors.mint : s === 'PARTIAL' ? '#F59E0B' : colors.crimson;

  const handleCopy = () => {
    if (!data) return;
    const report = `DRISHTI — RBI MRM 2026 Compliance Board Report
Generated: ${new Date().toLocaleDateString()}
Branch: 554, Surat | IDBI Bank

OVERALL COMPLIANCE SCORE: ${data.overall_score}/100 — ${data.overall_status}

KEY FINDINGS:
${data.top_gaps.join('\n')}

PRINCIPLE-WISE SCORES:
${data.principles.map(p => `${p.id} ${p.name}: ${p.score}/100 (${p.status})`).join('\n')}

IMMEDIATE ACTIONS REQUIRED:
- P4: Establish structural independence for model validation
- P6: Obtain contractual audit rights for CIBIL vendor model
- P7: Deploy SHAP/LIME XAI layer for all AI/ML models
- P8: Formulate quantitative model risk appetite statement`;
    navigator.clipboard.writeText(report);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  if (loading) return <div className="text-xs font-mono p-6" style={{ color: colors.textMut }}>Loading compliance data...</div>;

  return (
    <div className="space-y-6">
      <div>
        <h2 className="text-xl font-bold font-mono" style={{ color: colors.mint }}>RAKSHA — RBI MRM 2026 Compliance Scorecard</h2>
        <p className="text-xs mt-1" style={{ color: colors.textSec }}>Model Risk Management Guidance 2026 · 8 Principles Assessment</p>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        <div className="rounded-xl border" style={{ background: colors.navy3, borderColor: colors.crimson + '40' }}>
          <ScoreGauge score={data?.overall_score || 0} />
        </div>

        <div className="lg:col-span-2 rounded-xl border p-5" style={{ background: colors.navy3, borderColor: colors.mint + '30' }}>
          <h3 className="font-bold font-mono text-sm mb-3" style={{ color: colors.mint }}>Critical Gaps</h3>
          <div className="space-y-2">
            {data?.top_gaps.map((g, i) => (
              <div key={i} className="flex gap-2 text-xs px-3 py-2 rounded" style={{ background: colors.crimson + '15', border: `1px solid ${colors.crimson}30` }}>
                <span style={{ color: colors.crimson }}>✗</span>
                <span style={{ color: colors.textSec }}>{g}</span>
              </div>
            ))}
          </div>
          <div className="mt-4 text-xs" style={{ color: colors.textMut }}>
            Overall compliance is {data?.overall_score}% — significant gap to regulatory expectation. Immediate remediation required for P4, P6, P7, P8.
          </div>
        </div>
      </div>

      {/* Principles grid */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
        {data?.principles.map(p => {
          const sc = statusColor(p.status);
          const isOpen = expanded === p.id;
          return (
            <div key={p.id} className="rounded-xl border overflow-hidden" style={{ borderColor: sc + '40', background: colors.navy3 }}>
              <div className="p-4 cursor-pointer" onClick={() => setExpanded(isOpen ? null : p.id)}
                style={{ borderLeft: `3px solid ${sc}` }}>
                <div className="flex items-center justify-between">
                  <div className="flex items-center gap-2">
                    <span className="text-xs font-mono font-bold" style={{ color: sc }}>{p.id}</span>
                    <span className="text-sm font-semibold" style={{ color: colors.textPri }}>{p.name}</span>
                  </div>
                  <div className="flex items-center gap-3">
                    <span className="px-2 py-0.5 rounded text-xs font-mono" style={{ background: sc + '20', color: sc }}>{p.status}</span>
                    {isOpen ? <ChevronUp size={14} style={{ color: colors.textMut }} /> : <ChevronDown size={14} style={{ color: colors.textMut }} />}
                  </div>
                </div>

                <div className="mt-3 flex items-center gap-3">
                  <div className="flex-1 h-2 rounded-full overflow-hidden" style={{ background: colors.navy4 }}>
                    <div className="h-full rounded-full" style={{ width: `${p.score}%`, background: sc }} />
                  </div>
                  <span className="text-xs font-mono font-bold w-12 text-right" style={{ color: sc }}>{p.score}/100</span>
                </div>
              </div>

              {isOpen && (
                <div className="px-4 pb-4 text-xs" style={{ color: colors.textSec, borderTop: `1px solid ${colors.navy4}` }}>
                  <div className="pt-3 leading-relaxed">{p.gap}</div>
                </div>
              )}
            </div>
          );
        })}
      </div>

      {/* Board report */}
      <div className="rounded-xl border p-5" style={{ background: colors.navy3, borderColor: colors.goldDim + '40' }}>
        <div className="flex items-center justify-between mb-3">
          <h3 className="font-bold font-mono text-sm" style={{ color: colors.gold }}>Board Report Summary</h3>
          <button onClick={handleCopy}
            className="flex items-center gap-2 px-3 py-1.5 rounded text-xs font-mono"
            style={{ background: colors.gold + '20', color: colors.gold, border: `1px solid ${colors.gold}40` }}>
            {copied ? <Check size={12} /> : <Copy size={12} />}
            {copied ? 'Copied!' : 'Copy Report'}
          </button>
        </div>
        <div className="text-xs font-mono leading-relaxed p-4 rounded" style={{ background: colors.navy, color: colors.textSec }}>
          <div style={{ color: colors.gold }}>DRISHTI — RBI MRM 2026 Board Summary | Branch 554, Surat</div>
          <div className="mt-2">Overall Compliance: <span style={{ color: colors.crimson }}>{data?.overall_score}/100 ({data?.overall_status})</span></div>
          <div className="mt-1">Critical findings: P4 (Validation Independence), P6 (Vendor Governance), P7 (AI/ML XAI), P8 (Risk Appetite)</div>
          <div className="mt-1">Models requiring immediate action: M007 (Overdue 12mo), M008 (Never validated), M003 (PSI=0.28)</div>
          <div className="mt-1 text-xs" style={{ color: colors.textMut }}>Target: ≥85% compliance by Q2 FY27 | DRISHTI platform addresses P4/P7 compliance gaps directly</div>
        </div>
      </div>
    </div>
  );
}
