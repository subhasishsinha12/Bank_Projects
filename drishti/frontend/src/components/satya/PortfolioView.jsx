import React, { useEffect, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { satya } from '../../utils/api';
import { colors, ewsColor, stageColor } from '../../utils/colors';

const SECTORS = ['Textile', 'Chemical', 'Diamond', 'Packaging', 'Engineering', 'Pharma'];
const EWS_STAGES = ['GREEN', 'AMBER', 'RED'];
const INAS_STAGES = ['Stage 1', 'Stage 2', 'Stage 3'];

export default function PortfolioView() {
  const navigate = useNavigate();
  const [borrowers, setBorrowers] = useState([]);
  const [filters, setFilters] = useState({ sector: '', stage: '', ews: '' });
  const [loading, setLoading] = useState(true);
  const [sortKey, setSortKey] = useState('id');
  const [sortDir, setSortDir] = useState(1);

  const load = () => {
    const params = {};
    if (filters.sector) params.sector = filters.sector;
    if (filters.stage) params.stage = filters.stage;
    if (filters.ews) params.ews = filters.ews;
    satya.portfolio(params).then(r => { setBorrowers(r.data.borrowers || []); setLoading(false); }).catch(() => setLoading(false));
  };

  useEffect(() => { load(); }, [filters]);

  const handleSort = (key) => {
    if (sortKey === key) setSortDir(d => -d);
    else { setSortKey(key); setSortDir(1); }
  };

  const sorted = [...borrowers].sort((a, b) => {
    const av = a[sortKey] ?? '';
    const bv = b[sortKey] ?? '';
    return av < bv ? -sortDir : av > bv ? sortDir : 0;
  });

  return (
    <div className="space-y-4">
      <div>
        <h2 className="text-xl font-bold font-mono" style={{ color: colors.violet }}>SATYA — Portfolio View</h2>
        <p className="text-xs mt-1" style={{ color: colors.textSec }}>{borrowers.length} borrowers · Surat cluster</p>
      </div>

      {/* Filters */}
      <div className="flex gap-3 flex-wrap">
        {[
          { key: 'sector', label: 'Sector', options: SECTORS },
          { key: 'ews', label: 'EWS Stage', options: EWS_STAGES },
          { key: 'stage', label: 'IndAS Stage', options: INAS_STAGES },
        ].map(({ key, label, options }) => (
          <select key={key}
            value={filters[key]}
            onChange={e => setFilters(p => ({ ...p, [key]: e.target.value }))}
            className="text-xs font-mono px-3 py-1.5 rounded border"
            style={{ background: colors.navy3, borderColor: colors.goldDim + '40', color: colors.textPri }}>
            <option value="">All {label}s</option>
            {options.map(o => <option key={o} value={o}>{o}</option>)}
          </select>
        ))}
        {(filters.sector || filters.ews || filters.stage) && (
          <button onClick={() => setFilters({ sector: '', stage: '', ews: '' })}
            className="text-xs font-mono px-3 py-1.5 rounded"
            style={{ color: colors.textSec, background: colors.navy3 }}>
            Clear filters ×
          </button>
        )}
      </div>

      <div className="rounded-xl border overflow-hidden" style={{ borderColor: colors.violet + '30' }}>
        <div className="overflow-x-auto">
          <table className="w-full text-xs font-mono">
            <thead>
              <tr style={{ background: colors.navy3 }}>
                {[
                  { key: 'id', label: 'ID' }, { key: 'name', label: 'Borrower' },
                  { key: 'sector', label: 'Sector' }, { key: 'district', label: 'District' },
                  { key: 'loan_amount', label: 'Loan (₹L)' }, { key: 'pd_current', label: 'PD%' },
                  { key: 'ews_stage', label: 'EWS' }, { key: 'inas_stage', label: 'IndAS' },
                  { key: 'sicr_alert', label: 'SICR' },
                ].map(({ key, label }) => (
                  <th key={key} className="px-3 py-3 text-left cursor-pointer hover:opacity-80"
                    style={{ color: sortKey === key ? colors.violet : colors.textSec }}
                    onClick={() => handleSort(key)}>
                    {label} {sortKey === key ? (sortDir === 1 ? '↑' : '↓') : ''}
                  </th>
                ))}
              </tr>
            </thead>
            <tbody>
              {loading && (
                <tr><td colSpan={9} className="px-3 py-6 text-center" style={{ color: colors.textMut }}>Loading...</td></tr>
              )}
              {sorted.map((b, i) => (
                <tr key={b.id}
                  className="cursor-pointer transition-all"
                  style={{ background: i % 2 === 0 ? colors.navy2 : colors.navy4 + '60', borderTop: `1px solid ${colors.goldDim}15` }}
                  onClick={() => navigate(`/satya/borrower/${b.id}`)}>
                  <td className="px-3 py-2.5" style={{ color: colors.violet }}>{b.id}</td>
                  <td className="px-3 py-2.5" style={{ color: colors.textPri }}>{b.name}</td>
                  <td className="px-3 py-2.5" style={{ color: colors.textSec }}>{b.sector}</td>
                  <td className="px-3 py-2.5" style={{ color: colors.textSec }}>{b.district}</td>
                  <td className="px-3 py-2.5" style={{ color: colors.textPri }}>{b.loan_amount?.toFixed(0)}</td>
                  <td className="px-3 py-2.5">
                    <span style={{ color: b.pd_current > 0.3 ? colors.crimson : b.pd_current > 0.15 ? '#F59E0B' : colors.mint }}>
                      {(b.pd_current * 100).toFixed(1)}%
                    </span>
                  </td>
                  <td className="px-3 py-2.5">
                    <span className="px-2 py-0.5 rounded" style={{ background: ewsColor(b.ews_stage) + '20', color: ewsColor(b.ews_stage) }}>
                      {b.ews_stage}
                    </span>
                  </td>
                  <td className="px-3 py-2.5">
                    <span style={{ color: stageColor(b.inas_stage) }}>{b.inas_stage}</span>
                  </td>
                  <td className="px-3 py-2.5">
                    {b.sicr_alert && <span title="SICR Alert" style={{ color: '#F59E0B' }}>⚠</span>}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
}
