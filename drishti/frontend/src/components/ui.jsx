import React from 'react';
import { colors } from '../utils/colors';

/* ── Spinner ── */
export function Spinner({ color = colors.gold }) {
  return (
    <div className="flex items-center justify-center py-16">
      <div className="relative w-10 h-10">
        <div className="absolute inset-0 rounded-full border-2 border-transparent"
          style={{ borderTopColor: color, animation: 'spin 0.8s linear infinite' }} />
        <div className="absolute inset-2 rounded-full border-2 border-transparent"
          style={{ borderTopColor: color + '55', animation: 'spin 1.4s linear infinite reverse' }} />
      </div>
      <style>{`@keyframes spin { to { transform: rotate(360deg); } }`}</style>
    </div>
  );
}

/* ── Section heading ── */
export function SectionHead({ title, subtitle, color = colors.gold, accent }) {
  return (
    <div className="mb-6">
      <div className="flex items-baseline gap-3">
        <h2 className="text-2xl font-bold tracking-tight" style={{ color }}>
          {title}
        </h2>
        {accent && (
          <span className="text-sm font-serif italic" style={{ color: colors.goldDim }}>{accent}</span>
        )}
      </div>
      {subtitle && <p className="text-sm mt-1" style={{ color: colors.textSec }}>{subtitle}</p>}
    </div>
  );
}

/* ── Stat card ── */
export function StatCard({ label, value, sub, color, icon: Icon, onClick, pulse }) {
  return (
    <div
      onClick={onClick}
      className={`glass rounded-2xl p-5 relative overflow-hidden ${onClick ? 'cursor-pointer module-card' : ''}`}
      style={{ boxShadow: `0 0 30px ${color}12, inset 0 1px 0 rgba(255,255,255,0.04)` }}
    >
      {/* corner glow */}
      <div className="absolute top-0 right-0 w-20 h-20 rounded-full opacity-30 blur-2xl"
        style={{ background: color }} />
      <div className="relative">
        <div className="flex items-center justify-between mb-3">
          <span className="text-xs font-mono uppercase tracking-widest" style={{ color: colors.textMut }}>{label}</span>
          {Icon && <Icon size={14} style={{ color: color + '80' }} />}
        </div>
        <div className="flex items-end gap-2">
          <span className="text-3xl font-bold stat-value" style={{ color }}>{value ?? '—'}</span>
          {pulse && <span className="h-2 w-2 rounded-full mb-2 pulse-dot" style={{ background: color }} />}
        </div>
        {sub && <p className="text-xs mt-1.5" style={{ color: colors.textMut }}>{sub}</p>}
      </div>
    </div>
  );
}

/* ── Badge ── */
export function Badge({ label, color, size = 'sm' }) {
  const pad = size === 'sm' ? 'px-2 py-0.5 text-xs' : 'px-3 py-1 text-sm';
  return (
    <span className={`${pad} rounded-full font-mono font-semibold`}
      style={{ background: color + '18', color, border: `1px solid ${color}30` }}>
      {label}
    </span>
  );
}

/* ── Section divider ── */
export function Divider({ label, color = colors.goldDim }) {
  return (
    <div className="flex items-center gap-3 my-4">
      <div className="flex-1 h-px" style={{ background: `linear-gradient(90deg, ${color}40, transparent)` }} />
      {label && <span className="text-xs font-mono uppercase tracking-widest" style={{ color: colors.textMut }}>{label}</span>}
      <div className="flex-1 h-px" style={{ background: `linear-gradient(270deg, ${color}40, transparent)` }} />
    </div>
  );
}

/* ── Panel ── */
export function Panel({ children, className = '', accentColor, title, titleRight }) {
  return (
    <div
      className={`glass rounded-2xl overflow-hidden ${className}`}
      style={{
        boxShadow: accentColor ? `0 0 40px ${accentColor}08, inset 0 1px 0 rgba(255,255,255,0.03)` : 'inset 0 1px 0 rgba(255,255,255,0.03)',
        border: accentColor ? `1px solid ${accentColor}20` : '1px solid rgba(201,168,76,0.10)',
      }}
    >
      {title && (
        <div className="flex items-center justify-between px-5 py-4 border-b"
          style={{ borderColor: accentColor ? accentColor + '15' : 'rgba(201,168,76,0.08)' }}>
          <span className="text-sm font-semibold font-mono" style={{ color: accentColor || colors.gold }}>{title}</span>
          {titleRight && <div>{titleRight}</div>}
        </div>
      )}
      <div className="p-5">{children}</div>
    </div>
  );
}

/* ── Thin progress bar ── */
export function ProgressBar({ value, max = 100, color, height = 4, className = '' }) {
  const pct = Math.min(100, (value / max) * 100);
  return (
    <div className={`rounded-full overflow-hidden ${className}`}
      style={{ height, background: 'rgba(255,255,255,0.05)' }}>
      <div className="h-full rounded-full transition-all duration-700"
        style={{
          width: `${pct}%`,
          background: `linear-gradient(90deg, ${color}99, ${color})`,
          boxShadow: `0 0 8px ${color}60`,
        }} />
    </div>
  );
}

/* ── Button ── */
export function Btn({ children, color = colors.gold, onClick, disabled, size = 'md', variant = 'filled' }) {
  const pad = size === 'sm' ? 'px-3 py-1.5 text-xs' : 'px-5 py-2.5 text-sm';
  const base = `${pad} rounded-xl font-mono font-semibold transition-all duration-200 disabled:opacity-40`;
  if (variant === 'ghost') {
    return (
      <button onClick={onClick} disabled={disabled} className={base}
        style={{ color, border: `1px solid ${color}30`, background: `${color}10` }}>
        {children}
      </button>
    );
  }
  return (
    <button onClick={onClick} disabled={disabled} className={base}
      style={{
        background: `linear-gradient(135deg, ${color}EE, ${color}BB)`,
        color: '#020810',
        boxShadow: `0 4px 16px ${color}30`,
      }}>
      {children}
    </button>
  );
}
