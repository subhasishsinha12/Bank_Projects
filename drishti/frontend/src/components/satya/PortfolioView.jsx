import React, { useEffect, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { ArrowUp, ArrowDown, Filter } from 'lucide-react';
import { satya } from '../../utils/api';
import { colors, ewsColor, ewsBg, stageColor, pdColor } from '../../utils/colors';
import { SectionHead, Spinner, Badge } from '../ui';

const SECTORS = ['Textile', 'Chemical', 'Diamond', 'Packaging', 'Engineering', 'Pharma'];
const EWS_STAGES = ['GREEN', 'AMBER', 'RED'];
const INAS_STAGES = ['Stage 1', 'Stage 2', 'Stage 3'];

const FilterSelect = ({ value, onChange, options, placeholder }) => (
  <select value={value} onChange={e => onChange(e.target.value)}
    className="text-xs font-mono px-3 py-2 rounded-xl outline-none transition-all"
    style={{
      background: 'rgba(255,255,255,0.04)',
      border: value ? '1px solid rgba(201,168,76,0.35)' : '1px solid rgba(201,168,76,0.12)',
      color: value ? colors.textPri : colors.textMut,
    }}>
    <option value="">{placeholder}</option>
    {options.map(o => <option key={o} value={o}>{o}</option>)}
  </select>
);

function SortIcon({ active, dir }) {
  if (!active) return null;
  return dir === 1 ? <ArrowUp size={10} /> : <ArrowDown size={10} />;
}

export default function PortfolioView() {
  const navigate = useNavigate();
  const [borrowers, setBorrowers] = useState([]);
  const [filters, setFilters] = useState({ sector: '', stage: '', ews: '' });
  const [loading, setLoading] = useState(true);
  const [sortKey, setSortKey] = useState('id');
  const [sortDir, setSortDir] = useState(1);

  const load = (f = filters) => {
    const params = {};
    if (f.sector) params.sector = f.sector;
    if (f.stage) params.stage = f.stage;
    if (f.ews) params.ews = f.ews;
    satya.portfolio(params).then(r => { setBorrowers(r.data.borrowers || []); setLoading(false); }).catch(() => setLoading(false));
  };

  useEffect(() => { setLoading(true); load(); }, [filters]);

  const handleSort = (key) => {
    if (sortKey === key) setSortDir(d => -d);
    else { setSortKey(key); setSortDir(1); }
  };

  const sorted = [...borrowers].sort((a, b) => {
    const av = a[sortKey] ?? '';
    const bv = b[sortKey] ?? '';
    return av < bv ? -sortDir : av > bv ? sortDir : 0;
  });

  const hasFilters = filters.sector || filters.stage || filters.ews;

  const cols = [
    { key: 'id', label: 'ID' },
    { key: 'name', label: 'Borrower' },
    { key: 'sector', label: 'Sector' },
    { key: 'district', label: 'District' },
    { key: 'loan_amount', label: 'Loan (₹L)' },
    { key: 'pd_current', label: 'PD %' },
    { key: 'ews_stage', label: 'EWS' },
    { key: 'inas_stage', label: 'IndAS' },
    { key: 'sicr_alert', label: 'SICR' },
  ];

  return (
    <div className="space-y-5 max-w-6xl mx-auto">
      <div className="flex items-start justify-between gap-4 flex-wrap">
        <SectionHead
          title="SATYA — Portfolio View"
          accent="सत्य"
          subtitle={`${borrowers.length} borrowers · MSME cluster · Surat region`}
          color={colors.violet}
        />
      </div>

      {/* Filter bar */}
      <div className="flex items-center gap-3 flex-wrap">
        <div className="flex items-center gap-1.5 text-xs font-mono" style={{ color: colors.textMut }}>
          <Filter size={11} /> Filters
        </div>
        <FilterSelect value={filters.sector} onChange={v => setFilters(p => ({ ...p, sector: v }))} options={SECTORS} placeholder="All Sectors" />
        <FilterSelect value={filters.ews} onChange={v => setFilters(p => ({ ...p, ews: v }))} options={EWS_STAGES} placeholder="All EWS" />
        <FilterSelect value={filters.stage} onChange={v => setFilters(p => ({ ...p, stage: v }))} options={INAS_STAGES} placeholder="All IndAS" />
        {hasFilters && (
          <button onClick={() => setFilters({ sector: '', stage: '', ews: '' })}
            className="text-xs font-mono px-3 py-2 rounded-xl transition-all"
            style={{ color: colors.textMut, background: 'rgba(255,255,255,0.03)', border: '1px solid rgba(255,255,255,0.06)' }}>
            Clear ×
          </button>
        )}
        {hasFilters && (
          <span className="text-xs font-mono" style={{ color: colors.violet }}>{borrowers.length} results</span>
        )}
      </div>

      {/* Table */}
      <div className="rounded-2xl overflow-hidden"
        style={{ border: '1px solid rgba(167,139,250,0.15)', boxShadow: '0 0 40px rgba(167,139,250,0.04)' }}>
        <div className="overflow-x-auto">
          <table className="w-full">
            <thead>
              <tr style={{ background: 'rgba(167,139,250,0.06)', borderBottom: '1px solid rgba(167,139,250,0.1)' }}>
                {cols.map(({ key, label }) => (
                  <th key={key}
                    className="px-4 py-3 text-left cursor-pointer select-none"
                    onClick={() => handleSort(key)}
                    style={{ color: sortKey === key ? colors.violet : colors.textMut }}>
                    <div className="flex items-center gap-1 text-xs font-mono uppercase tracking-wider">
                      {label}
                      <SortIcon active={sortKey === key} dir={sortDir} />
                    </div>
                  </th>
                ))}
              </tr>
            </thead>
            <tbody>
              {loading ? (
                <tr><td colSpan={9} className="py-12 text-center">
                  <div className="flex justify-center"><Spinner color={colors.violet} /></div>
                </td></tr>
              ) : sorted.map((b, i) => (
                <tr key={b.id}
                  className="tr-hover cursor-pointer transition-all"
                  style={{
                    background: i % 2 === 0 ? 'rgba(5,13,26,0.4)' : 'rgba(10,22,40,0.3)',
                    borderBottom: '1px solid rgba(255,255,255,0.02)',
                  }}
                  onClick={() => navigate(`/satya/borrower/${b.id}`)}>
                  <td className="px-4 py-3 text-xs font-mono font-bold" style={{ color: colors.violet }}>{b.id}</td>
                  <td className="px-4 py-3 text-sm" style={{ color: colors.textPri }}>{b.name}</td>
                  <td className="px-4 py-3 text-xs" style={{ color: colors.textSec }}>{b.sector}</td>
                  <td className="px-4 py-3 text-xs" style={{ color: colors.textMut }}>{b.district}</td>
                  <td className="px-4 py-3 text-xs font-mono" style={{ color: colors.textSec }}>{b.loan_amount?.toFixed(0)}</td>
                  <td className="px-4 py-3">
                    <span className="text-xs font-mono font-semibold" style={{ color: pdColor(b.pd_current) }}>
                      {(b.pd_current * 100).toFixed(1)}%
                    </span>
                  </td>
                  <td className="px-4 py-3">
                    <span className="px-2.5 py-1 rounded-lg text-xs font-mono font-semibold"
                      style={{ background: ewsBg(b.ews_stage), color: ewsColor(b.ews_stage) }}>
                      {b.ews_stage}
                    </span>
                  </td>
                  <td className="px-4 py-3">
                    <span className="text-xs font-mono" style={{ color: stageColor(b.inas_stage) }}>
                      {b.inas_stage}
                    </span>
                  </td>
                  <td className="px-4 py-3 text-center">
                    {b.sicr_alert && (
                      <span className="text-sm" title="SICR Alert" style={{ color: colors.amber }}>⚠</span>
                    )}
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
