import React, { useState } from 'react';
import { Outlet, NavLink, useLocation } from 'react-router-dom';
import { Eye, Shield, AlertTriangle, BarChart2, Home, ChevronRight } from 'lucide-react';
import { colors } from '../utils/colors';

const navItems = [
  { label: 'Dashboard', path: '/', icon: Home, color: colors.gold, exact: true },
  {
    label: 'VIVEKA', sublabel: 'विवेक', path: '/viveka', icon: Eye, color: colors.electric,
    children: [
      { label: 'XAI Dashboard', path: '/viveka' },
      { label: 'Fairness Audit', path: '/viveka/fairness' },
    ]
  },
  {
    label: 'RAKSHA', sublabel: 'रक्षा', path: '/raksha', icon: Shield, color: colors.mint,
    children: [
      { label: 'Model Inventory', path: '/raksha' },
      { label: 'RBI MRM Compliance', path: '/raksha/compliance' },
      { label: 'Validation Queue', path: '/raksha/workflow' },
    ]
  },
  {
    label: 'SATYA', sublabel: 'सत्य', path: '/satya', icon: AlertTriangle, color: colors.violet,
    children: [
      { label: 'EWS Dashboard', path: '/satya' },
      { label: 'Portfolio View', path: '/satya/portfolio' },
      { label: 'PSI Monitor', path: '/satya/psi' },
    ]
  },
];

export default function Layout() {
  const location = useLocation();
  const [collapsed, setCollapsed] = useState(false);

  const activeModule = navItems.find(n => n.path !== '/' && location.pathname.startsWith(n.path));
  const accentColor = activeModule?.color || colors.gold;

  return (
    <div className="flex h-screen overflow-hidden" style={{ background: colors.navy }}>
      {/* Sidebar */}
      <aside className="w-60 flex-shrink-0 flex flex-col border-r overflow-y-auto" style={{ background: colors.navy2, borderColor: colors.goldDim + '40' }}>
        {/* Logo */}
        <div className="p-5 border-b" style={{ borderColor: colors.goldDim + '40' }}>
          <div className="flex items-center gap-2">
            <BarChart2 size={22} style={{ color: colors.gold }} />
            <div>
              <div className="text-lg font-bold tracking-widest" style={{ color: colors.gold, fontFamily: 'IBM Plex Mono' }}>DRISHTI</div>
              <div className="text-xs font-serif italic" style={{ color: colors.goldDim }}>दृष्टि — Clear Vision</div>
            </div>
          </div>
          <div className="mt-1 text-xs" style={{ color: colors.textMut, fontFamily: 'IBM Plex Mono' }}>IDBI Innovate 2026</div>
        </div>

        {/* Nav */}
        <nav className="flex-1 py-4 px-2 space-y-1">
          {navItems.map((item) => {
            const Icon = item.icon;
            const isActive = item.exact
              ? location.pathname === item.path
              : location.pathname.startsWith(item.path);

            return (
              <div key={item.path}>
                <NavLink
                  to={item.path}
                  end={item.exact}
                  className="flex items-center gap-3 px-3 py-2 rounded-lg text-sm transition-all"
                  style={({ isActive: active }) => ({
                    background: active ? item.color + '22' : 'transparent',
                    color: active ? item.color : colors.textSec,
                    borderLeft: active ? `2px solid ${item.color}` : '2px solid transparent',
                  })}
                >
                  <Icon size={16} />
                  <span className="font-medium">{item.label}</span>
                  {item.sublabel && (
                    <span className="ml-auto text-xs font-serif italic" style={{ color: colors.goldDim }}>{item.sublabel}</span>
                  )}
                </NavLink>

                {item.children && isActive && (
                  <div className="ml-7 mt-1 space-y-1">
                    {item.children.map(child => (
                      <NavLink
                        key={child.path}
                        to={child.path}
                        end
                        className="flex items-center gap-2 px-3 py-1.5 rounded text-xs transition-all"
                        style={({ isActive: active }) => ({
                          background: active ? item.color + '15' : 'transparent',
                          color: active ? item.color : colors.textMut,
                        })}
                      >
                        <ChevronRight size={10} />
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
        <div className="p-4 border-t text-xs" style={{ borderColor: colors.goldDim + '30', color: colors.textMut, fontFamily: 'IBM Plex Mono' }}>
          <div>Branch 554, Surat</div>
          <div>Subhasish Sinha | FRM</div>
        </div>
      </aside>

      {/* Main */}
      <div className="flex-1 flex flex-col overflow-hidden">
        {/* Top bar */}
        <header className="h-14 flex items-center justify-between px-6 border-b flex-shrink-0" style={{ background: colors.navy2, borderColor: colors.goldDim + '40' }}>
          <div className="flex items-center gap-2">
            {activeModule && (
              <>
                <span className="font-bold text-sm" style={{ color: activeModule.color, fontFamily: 'IBM Plex Mono' }}>
                  {activeModule.label}
                </span>
                <span className="text-xs font-serif italic" style={{ color: colors.goldDim }}>
                  {activeModule.sublabel}
                </span>
                <ChevronRight size={12} style={{ color: colors.textMut }} />
                <span className="text-xs" style={{ color: colors.textSec }}>
                  {location.pathname.split('/').pop().replace('-', ' ') || 'Dashboard'}
                </span>
              </>
            )}
            {!activeModule && <span className="font-bold" style={{ color: colors.gold, fontFamily: 'IBM Plex Mono' }}>DRISHTI Overview</span>}
          </div>

          <div className="flex items-center gap-2">
            <span className="h-2 w-2 rounded-full animate-pulse" style={{ background: colors.mint }}></span>
            <span className="text-xs font-mono" style={{ color: colors.mint }}>RBI MRM 2026 Live</span>
          </div>
        </header>

        {/* Content */}
        <main className="flex-1 overflow-y-auto p-6" style={{ background: colors.navy }}>
          <Outlet />
        </main>
      </div>
    </div>
  );
}
