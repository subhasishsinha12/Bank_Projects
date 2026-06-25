import React, { useEffect, useState } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { ArrowLeft } from 'lucide-react';
import { viveka } from '../../utils/api';
import { colors } from '../../utils/colors';
import SHAPWaterfall from './SHAPWaterfall';

export default function BorrowerExplain() {
  const { id } = useParams();
  const navigate = useNavigate();
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    viveka.explain(id).then(r => { setData(r.data); setLoading(false); }).catch(() => setLoading(false));
  }, [id]);

  if (loading) return <div className="text-xs font-mono p-6" style={{ color: colors.textMut }}>Computing SHAP explanation...</div>;
  if (!data) return <div className="text-xs font-mono p-6" style={{ color: colors.crimson }}>Borrower not found.</div>;

  const pdColor = data.pd_score > 0.5 ? colors.crimson : data.pd_score > 0.25 ? '#F59E0B' : colors.mint;

  return (
    <div className="space-y-6">
      <div className="flex items-center gap-3">
        <button onClick={() => navigate('/viveka')} className="p-1 rounded" style={{ color: colors.textSec }}>
          <ArrowLeft size={18} />
        </button>
        <div>
          <h2 className="text-xl font-bold font-mono" style={{ color: colors.electric }}>{data.borrower_name}</h2>
          <p className="text-xs" style={{ color: colors.textSec }}>{id} · Borrower Explainability</p>
        </div>
      </div>

      <div className="grid grid-cols-3 gap-4">
        <div className="rounded-xl p-4 border" style={{ background: colors.navy3, borderColor: pdColor + '40' }}>
          <div className="text-xs font-mono" style={{ color: colors.textSec }}>PD Score</div>
          <div className="text-3xl font-bold font-mono mt-1" style={{ color: pdColor }}>{(data.pd_score * 100).toFixed(1)}%</div>
        </div>
        <div className="rounded-xl p-4 border col-span-2" style={{ background: colors.navy3, borderColor: colors.crimson + '30' }}>
          <div className="text-xs font-mono mb-2" style={{ color: colors.textSec }}>Adverse Action Reason Codes</div>
          <div className="flex gap-2 flex-wrap">
            {data.adverse_factors.map((f, i) => (
              <span key={i} className="px-3 py-1 rounded text-xs font-mono" style={{ background: colors.crimson + '20', color: colors.crimson, border: `1px solid ${colors.crimson}40` }}>
                {String.fromCharCode(65 + i)}. {f.replace(/_/g, ' ')}
              </span>
            ))}
          </div>
        </div>
      </div>

      <div className="rounded-xl border p-5" style={{ background: colors.navy3, borderColor: colors.electric + '30' }}>
        <h3 className="font-bold font-mono text-sm mb-3" style={{ color: colors.electric }}>SHAP Waterfall — Feature Contribution to PD</h3>
        <SHAPWaterfall shapValues={data.shap_values} baseValue={data.base_value} finalPD={data.pd_score} />
      </div>

      <div className="rounded-xl border p-5" style={{ background: colors.navy3, borderColor: colors.electric + '30' }}>
        <h3 className="font-bold font-mono text-sm mb-3" style={{ color: colors.electric }}>LIME Local Explanation</h3>
        <div className="space-y-2">
          {data.lime_explanation?.map((item, i) => (
            <div key={i} className="flex items-center justify-between gap-3 px-3 py-2 rounded" style={{ background: colors.navy4 }}>
              <span className="text-xs font-mono" style={{ color: colors.textSec }}>{item.feature.replace(/_/g, ' ')}</span>
              <div className="flex items-center gap-3">
                <div className="h-2 w-32 rounded-full overflow-hidden" style={{ background: colors.navy }}>
                  <div className="h-full rounded-full" style={{
                    width: `${Math.min(100, Math.abs(item.weight) * 300)}%`,
                    background: item.weight > 0 ? colors.crimson : colors.electric,
                  }} />
                </div>
                <span className="text-xs font-mono w-16 text-right" style={{ color: item.weight > 0 ? colors.crimson : colors.electric }}>
                  {item.weight > 0 ? '+' : ''}{item.weight.toFixed(3)}
                </span>
              </div>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}
