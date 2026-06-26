import React, { useEffect, useState } from 'react';
import { ChevronDown, ChevronUp, Copy, Check } from 'lucide-react';
import { raksha } from '../../utils/api';
import { colors } from '../../utils/colors';
import { Panel, SectionHead, Badge, ProgressBar, Spinner, Btn } from '../ui';

function GaugeRing({ score, size = 160 }) {
  const c = score >= 70 ? colors.mint : score >= 40 ? colors.amber : colors.crimson;
  const r = 54;
  const circ = 2 * Math.PI * r;
  const dash = (score / 100) * circ;

  return (
    <div className="flex flex-col items-center justify-center p-8" style={{ position: 'relative' }}>
      <svg width={size} height={size} viewBox="0 0 120 120">
        {/* Track */}
        <circle cx="60" cy="60" r={r} fill="none" stroke="rgba(255,255,255,0.04)" strokeWidth="10" />
        {/* Progress */}
        <circle cx="60" cy="60" r={r} fill="none" stroke={c} strokeWidth="10"
          strokeLinecap="round"
          strokeDasharray={`${dash} ${circ}`}
          transform="rotate(-90 60 60)"
          style={{ filter: `drop-shadow(0 0 6px ${c}80)`, transition: 'stroke-dasharray 1s ease' }}
        />
        {/* Glow ring */}
        <circle cx="60" cy="60" r={r} fill="none" stroke={c} strokeWidth="2"
          strokeDasharray={`${dash * 0.3} ${circ}`}
          transform="rotate(-90 60 60)"
          opacity="0.25"
        />
      </svg>
      <div className="absolute inset-0 flex flex-col items-center justify-center">
        <div className="text-4xl font-bold font-mono stat-value" style={{ color: c }}>{score}</div>
        <div className="text-xs font-mono mt-0.5" style={{ color: colors.textMut }}>/100</div>
      </div>
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

  if (loading) return <Spinner color={colors.mint} />;

  const statusColor = (s) => s === 'COMPLIANT' ? colors.mint : s === 'PARTIAL' ? colors.amber : colors.crimson;

  const handleCopy = () => {
    if (!data) return;
    const txt = [
      `DRISHTI — RBI MRM 2026 Compliance Report`,
      `Date: ${new Date().toLocaleDateString()} | Branch 554, Surat | IDBI Bank`,
      ``,
      `OVERALL: ${data.overall_score}/100 — ${data.overall_status}`,
      ``,
      `CRITICAL GAPS:`,
      ...data.top_gaps.map(g => `  × ${g}`),
      ``,
      `PRINCIPLE SCORES:`,
      ...data.principles.map(p => `  ${p.id} ${p.name}: ${p.score}/100 (${p.status})`),
      ``,
      `ACTION ITEMS: P4 Validation Independence · P6 Vendor Governance · P7 AI/ML XAI · P8 Risk Appetite`,
    ].join('\n');
    navigator.clipboard.writeText(txt);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  const overall = data?.overall_score || 0;
  const overallColor = overall >= 70 ? colors.mint : overall >= 40 ? colors.amber : colors.crimson;

  return (
    <div className="space-y-6 max-w-6xl mx-auto">
      <SectionHead
        title="RAKSHA — RBI MRM 2026 Compliance"
        accent="रक्षा"
        subtitle="Model Risk Management Guidance · 8 Principle Assessment · Remediation tracking"
        color={colors.mint}
      />

      {/* Top section */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-5">
        {/* Gauge */}
        <div className="rounded-2xl p-2 flex flex-col items-center"
          style={{
            background: `linear-gradient(145deg, ${overallColor}10, rgba(5,13,26,0.8))`,
            border: `1px solid ${overallColor}25`,
            boxShadow: `0 0 60px ${overallColor}08`,
          }}>
          <GaugeRing score={overall} />
          <div className="text-sm font-semibold font-mono mb-1" style={{ color: overallColor }}>
            {data?.overall_status}
          </div>
          <div className="text-xs text-center mb-4" style={{ color: colors.textMut }}>
            RBI MRM 2026 Overall Compliance
          </div>
          <Btn color={overallColor} variant="ghost" size="sm" onClick={handleCopy}>
            <div className="flex items-center gap-1.5">
              {copied ? <Check size={12} /> : <Copy size={12} />}
              {copied ? 'Copied!' : 'Export Board Report'}
            </div>
          </Btn>
        </div>

        {/* Critical gaps */}
        <div className="lg:col-span-2 rounded-2xl p-5"
          style={{
            background: 'linear-gradient(145deg, rgba(255,91,91,0.06), rgba(5,13,26,0.8))',
            border: '1px solid rgba(255,91,91,0.15)',
          }}>
          <div className="text-xs font-mono mb-4" style={{ color: colors.textMut }}>CRITICAL COMPLIANCE GAPS</div>
          <div className="space-y-2.5 mb-5">
            {data?.top_gaps.map((g, i) => (
              <div key={i} className="flex items-start gap-3 px-4 py-2.5 rounded-xl"
                style={{ background: 'rgba(255,91,91,0.06)', border: '1px solid rgba(255,91,91,0.12)' }}>
                <span style={{ color: colors.crimson }} className="flex-shrink-0 mt-0.5">✕</span>
                <span className="text-xs" style={{ color: colors.textSec }}>{g}</span>
              </div>
            ))}
          </div>

          {/* Score distribution */}
          <div className="text-xs font-mono mb-3" style={{ color: colors.textMut }}>Score Distribution</div>
          <div className="grid grid-cols-3 gap-3">
            {[
              { label: 'Non-Compliant', status: 'NON-COMPLIANT', color: colors.crimson },
              { label: 'Partial', status: 'PARTIAL', color: colors.amber },
              { label: 'Compliant', status: 'COMPLIANT', color: colors.mint },
            ].map(({ label, status, color }) => {
              const count = data?.principles.filter(p => p.status === status).length || 0;
              return (
                <div key={status} className="px-3 py-2.5 rounded-xl text-center"
                  style={{ background: `${color}10`, border: `1px solid ${color}20` }}>
                  <div className="text-2xl font-bold font-mono" style={{ color }}>{count}</div>
                  <div className="text-xs mt-0.5" style={{ color: colors.textMut }}>{label}</div>
                </div>
              );
            })}
          </div>
        </div>
      </div>

      {/* Principles grid */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
        {data?.principles.map(p => {
          const sc = statusColor(p.status);
          const isOpen = expanded === p.id;
          return (
            <div key={p.id}
              className="rounded-2xl overflow-hidden cursor-pointer transition-all"
              style={{
                background: `linear-gradient(145deg, ${sc}08, rgba(5,13,26,0.7))`,
                border: `1px solid ${sc}${isOpen ? '35' : '20'}`,
                boxShadow: isOpen ? `0 0 24px ${sc}08` : 'none',
              }}
              onClick={() => setExpanded(isOpen ? null : p.id)}
            >
              <div className="px-5 py-4">
                <div className="flex items-center justify-between mb-3">
                  <div className="flex items-center gap-2.5">
                    <span className="text-xs font-mono font-bold px-2 py-0.5 rounded-lg"
                      style={{ background: `${sc}20`, color: sc }}>{p.id}</span>
                    <span className="text-sm font-semibold" style={{ color: colors.textPri }}>{p.name}</span>
                  </div>
                  <div className="flex items-center gap-2">
                    <Badge label={p.status} color={sc} />
                    {isOpen ? <ChevronUp size={13} style={{ color: colors.textMut }} />
                      : <ChevronDown size={13} style={{ color: colors.textMut }} />}
                  </div>
                </div>

                <div className="flex items-center gap-3">
                  <ProgressBar value={p.score} max={100} color={sc} className="flex-1" />
                  <span className="text-sm font-bold font-mono w-14 text-right stat-value" style={{ color: sc }}>
                    {p.score}<span style={{ color: colors.textMut, fontSize: 10 }}>/100</span>
                  </span>
                </div>
              </div>

              {isOpen && (
                <div className="px-5 pb-4 text-xs leading-relaxed"
                  style={{ color: colors.textSec, borderTop: `1px solid ${sc}12` }}>
                  <div className="pt-3">{p.gap}</div>
                </div>
              )}
            </div>
          );
        })}
      </div>

      {/* Board summary */}
      <div className="rounded-2xl p-5"
        style={{ background: 'rgba(201,168,76,0.04)', border: '1px solid rgba(201,168,76,0.12)' }}>
        <div className="text-xs font-mono mb-3" style={{ color: colors.gold }}>BOARD REPORT SUMMARY</div>
        <div className="font-mono text-xs leading-relaxed p-4 rounded-xl"
          style={{ background: 'rgba(0,0,0,0.3)', color: colors.textSec, border: '1px solid rgba(255,255,255,0.04)' }}>
          <div style={{ color: colors.goldBr }}>DRISHTI · RBI MRM 2026 Status | Branch 554, Surat | {new Date().toLocaleDateString()}</div>
          <br />
          <div>Overall Compliance: <span style={{ color: overallColor }}>{data?.overall_score}/100 ({data?.overall_status})</span></div>
          <div>Critical findings: P4 (Validation Independence) · P6 (Vendor Governance) · P7 (AI/ML XAI) · P8 (Risk Appetite)</div>
          <div>Immediate action: M007 (Overdue 12mo) · M008 (Never validated) · M003 (PSI=0.28 CRITICAL)</div>
          <br />
          <div style={{ color: colors.textMut }}>
            Target: ≥85% by Q2 FY27 · DRISHTI directly addresses P4, P7 compliance gaps through integrated XAI layer
          </div>
        </div>
      </div>
    </div>
  );
}
