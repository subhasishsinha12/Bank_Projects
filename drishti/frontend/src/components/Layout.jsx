import React, { useState } from 'react';
import { Outlet, NavLink, useLocation } from 'react-router-dom';
import { Eye, Shield, AlertTriangle, BarChart2, Home, ChevronRight, Activity, Cpu } from 'lucide-react';
import { colors } from '../utils/colors';

const navItems = [
  {
    label: 'Overview', path: '/', icon: Home, color: colors.gold,
    exact: true, sublabel: null,
  },
  {
    label: 'VIVEKA', sublabel: 'विवेक', path: '/viveka', icon: Eye, color: colors.electric,
    desc: 'XAI Validation',
    children: [
      { label: 'XAI Dashboard', path: '/viveka' },
      { label: 'Fairness Audit', path: '/viveka/fairness' },
    ],
  },
  {
    label: 'RAKSHA', sublabel: 'रक्षा', path: '/raksha', icon: Shield, color: colors.mint,
    desc: 'MRM Governance',
    children: [
      { label: 'Model Inventory', path: '/raksha' },
      { label: 'RBI MRM 2026', path: '/raksha/compliance' },
      { label: 'Validation Queue', path: '/raksha/workflow' },
    ],
  },
  {
    label: 'SATYA', sublabel: 'सत्य', path: '/satya', icon: AlertTriangle, color: colors.violet,
    desc: 'Early Warning',
    children: [
      { label: 'EWS Dashboard', path: '/satya' },
      { label: 'Portfolio View', path: '/satya/portfolio' },
      { label: 'PSI Monitor', path: '/satya/psi' },
    ],
  },
];

export default function Layout() {
  const location = useLocation();

  const activeModule = navItems.find(n => n.path !== '/' && location.pathname.startsWith(n.path));
  const accentColor = activeModule?.color || colors.gold;

  return (
    <div className="flex h-screen overflow-hidden" style={{ background: colors.bg }}>
      {/* ── Sidebar ── */}
      <aside
        className="w-56 flex-shrink-0 flex flex-col relative overflow-hidden"
        style={{
          background: 'linear-gradient(180deg, #05101E 0%, #030C18 100%)',
          borderRight: '1px solid rgba(201,168,76,0.08)',
        }}
      >
        {/* subtle side gradient */}
        <div className="absolute inset-y-0 right-0 w-px"
          style={{ background: 'linear-gradient(180deg, transparent, rgba(201,168,76,0.2) 40%, rgba(201,168,76,0.2) 60%, transparent)' }} />

        {/* Logo */}
        <div className="px-5 pt-6 pb-5">
          <div className="flex items-center gap-3 mb-1">
            <div className="w-8 h-8 rounded-xl flex items-center justify-center flex-shrink-0"
              style={{ background: 'linear-gradient(135deg, #C9A84C22, #C9A84C08)', border: '1px solid rgba(201,168,76,0.3)' }}>
              <Cpu size={15} style={{ color: colors.gold }} />
            </div>
            <div>
              <div className="text-base font-bold tracking-[0.12em] font-mono" style={{ color: colors.goldBr }}>DRISHTI</div>
              <div className="text-xs font-serif italic leading-none" style={{ color: colors.goldDim }}>दृष्टि</div>
            </div>
          </div>
          <div className="mt-2 text-xs leading-none font-mono" style={{ color: colors.textMut }}>IDBI Innovate 2026</div>
        </div>

        <div className="mx-4 h-px" style={{ background: 'linear-gradient(90deg, transparent, rgba(201,168,76,0.2), transparent)' }} />

        {/* Nav */}
        <nav className="flex-1 py-4 px-3 space-y-1 overflow-y-auto">
          {navItems.map((item) => {
            const Icon = item.icon;
            const isModuleActive = item.exact
              ? location.pathname === item.path
              : location.pathname.startsWith(item.path);

            return (
              <div key={item.path}>
                <NavLink
                  to={item.path}
                  end={item.exact}
                  className="flex items-center gap-2.5 px-3 py-2 rounded-xl text-sm transition-all duration-200 group"
                  style={({ isActive }) => ({
                    background: isActive
                      ? `linear-gradient(135deg, ${item.color}18, ${item.color}08)`
                      : 'transparent',
                    color: isActive ? item.color : colors.textSec,
                    boxShadow: isActive ? `inset 0 1px 0 ${item.color}15` : 'none',
                    border: isActive ? `1px solid ${item.color}20` : '1px solid transparent',
                  })}
                >
                  <Icon size={14} />
                  <span className="font-semibold text-xs tracking-wide">{item.label}</span>
                  {item.sublabel && (
                    <span className="ml-auto text-xs font-serif italic" style={{ color: colors.goldDim }}>{item.sublabel}</span>
                  )}
                </NavLink>

                {/* Sub-nav */}
                {item.children && isModuleActive && (
                  <div className="ml-4 mt-0.5 mb-1 space-y-0.5">
                    {item.children.map(child => (
                      <NavLink
                        key={child.path}
                        to={child.path}
                        end
                        className="flex items-center gap-2 px-3 py-1.5 rounded-lg text-xs transition-all duration-200"
                        style={({ isActive }) => ({
                          background: isActive ? `${item.color}10` : 'transparent',
                          color: isActive ? item.color : colors.textMut,
                        })}
                      >
                        <div className="w-1 h-1 rounded-full flex-shrink-0"
                          style={{ background: 'currentColor', opacity: 0.6 }} />
                        {child.label}
                      </NavLink>
                    ))}
                  </div>
                )}
              </div>
            );
          })}
        </nav>

        {/* Footer */}
        <div className="mx-4 h-px" style={{ background: 'linear-gradient(90deg, transparent, rgba(201,168,76,0.15), transparent)' }} />
        <div className="px-5 py-4">
          <div className="text-xs font-mono" style={{ color: colors.textMut }}>
            <div style={{ color: colors.textSec }}>Subhasish Sinha · FRM</div>
            <div>Branch 554, Surat</div>
          </div>
        </div>
      </aside>

      {/* ── Main ── */}
      <div className="flex-1 flex flex-col overflow-hidden">
        {/* Top bar */}
        <header
          className="h-14 flex items-center justify-between px-6 flex-shrink-0 relative"
          style={{
            background: 'rgba(3,12,24,0.8)',
            backdropFilter: 'blur(20px)',
            borderBottom: '1px solid rgba(201,168,76,0.08)',
          }}
        >
          {/* Active module indicator */}
          <div className="flex items-center gap-2.5">
            {activeModule ? (
              <>
                <div className="h-4 w-0.5 rounded-full" style={{ background: activeModule.color }} />
                <span className="font-bold text-sm font-mono tracking-wide" style={{ color: activeModule.color }}>
                  {activeModule.label}
                </span>
                <span className="text-xs font-serif italic" style={{ color: colors.goldDim }}>{activeModule.sublabel}</span>
                <ChevronRight size={12} style={{ color: colors.textMut }} />
                <span className="text-xs" style={{ color: colors.textSec }}>
                  {location.pathname.split('/').pop()?.replace('-', ' ') || 'Dashboard'}
                </span>
              </>
            ) : (
              <span className="font-bold text-sm font-mono" style={{ color: colors.gold }}>DRISHTI Overview</span>
            )}
          </div>

          {/* Right side */}
          <div className="flex items-center gap-4">
            <div className="flex items-center gap-2 px-3 py-1.5 rounded-lg"
              style={{ background: 'rgba(80,227,194,0.06)', border: '1px solid rgba(80,227,194,0.15)' }}>
              <span className="h-1.5 w-1.5 rounded-full pulse-dot" style={{ background: colors.mint }} />
              <span className="text-xs font-mono" style={{ color: colors.mint }}>RBI MRM 2026 Live</span>
            </div>
          </div>

          {/* Bottom accent line */}
          <div className="absolute bottom-0 left-56 right-0 h-px"
            style={{ background: `linear-gradient(90deg, ${accentColor}40, transparent 40%)` }} />
        </header>

        {/* Content */}
        <main className="flex-1 overflow-y-auto p-6 fade-in">
          <Outlet />
        </main>
      </div>
    </div>
  );
}
