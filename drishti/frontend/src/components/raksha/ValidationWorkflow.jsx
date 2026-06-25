import React, { useEffect, useState } from 'react';
import { AlertTriangle, Clock, CheckCircle, Calendar } from 'lucide-react';
import { raksha } from '../../utils/api';
import { colors, psiColor } from '../../utils/colors';

function ModelCard({ model, onUpdate }) {
  const [updating, setUpdating] = useState(false);

  const handleStatusChange = (newStatus) => {
    setUpdating(true);
    raksha.updateStatus(model.id, { validation_status: newStatus, notes: `Updated via DRISHTI workflow` })
      .then(() => { onUpdate(); setUpdating(false); })
      .catch(() => setUpdating(false));
  };

  return (
    <div className="p-3 rounded-lg border" style={{ background: colors.navy4, borderColor: colors.goldDim + '30' }}>
      <div className="flex items-start justify-between gap-2">
        <div>
          <div className="text-xs font-mono font-semibold" style={{ color: colors.textPri }}>{model.name}</div>
          <div className="text-xs mt-0.5 font-mono" style={{ color: colors.textMut }}>
            T{model.tier} · PSI: <span style={{ color: psiColor(model.psi_current) }}>{model.psi_current?.toFixed(2)}</span>
          </div>
          {model.days_overdue && (
            <div className="text-xs mt-1 font-mono" style={{ color: colors.crimson }}>⚠ {model.days_overdue}d overdue</div>
          )}
          <div className="text-xs mt-0.5" style={{ color: colors.textMut }}>Last: {model.last_validated || 'Never'}</div>
        </div>
      </div>
      {onUpdate && (
        <select
          onChange={e => handleStatusChange(e.target.value)}
          disabled={updating}
          className="mt-2 w-full text-xs font-mono px-2 py-1 rounded"
          style={{ background: colors.navy, borderColor: colors.goldDim + '40', color: colors.textSec, border: `1px solid ${colors.goldDim}30` }}
          defaultValue=""
        >
          <option value="" disabled>Update status...</option>
          <option value="Validated">Validated</option>
          <option value="Pending Revalidation">Pending Revalidation</option>
          <option value="Validation Overdue">Validation Overdue</option>
        </select>
      )}
    </div>
  );
}

function Column({ title, icon: Icon, color, models, onUpdate }) {
  return (
    <div className="flex-1 min-w-52 rounded-xl border p-4" style={{ background: colors.navy3, borderColor: color + '40' }}>
      <div className="flex items-center gap-2 mb-3 pb-3 border-b" style={{ borderColor: color + '30' }}>
        <Icon size={14} style={{ color }} />
        <span className="text-xs font-mono font-bold" style={{ color }}>{title}</span>
        <span className="ml-auto text-xs font-mono px-2 py-0.5 rounded-full" style={{ background: color + '20', color }}>{models.length}</span>
      </div>
      <div className="space-y-2">
        {models.length === 0 && <div className="text-xs font-mono" style={{ color: colors.textMut }}>No models</div>}
        {models.map(m => <ModelCard key={m.id} model={m} onUpdate={onUpdate} />)}
      </div>
    </div>
  );
}

export default function ValidationWorkflow() {
  const [queue, setQueue] = useState({ overdue: [], due_soon: [], scheduled: [], completed: [] });
  const [loading, setLoading] = useState(true);

  const load = () => {
    raksha.validationQueue().then(r => { setQueue(r.data); setLoading(false); }).catch(() => setLoading(false));
  };

  useEffect(() => { load(); }, []);

  if (loading) return <div className="text-xs font-mono" style={{ color: colors.textMut }}>Loading validation queue...</div>;

  return (
    <div className="space-y-6">
      <div>
        <h2 className="text-xl font-bold font-mono" style={{ color: colors.mint }}>RAKSHA — Validation Queue</h2>
        <p className="text-xs mt-1" style={{ color: colors.textSec }}>Model validation workflow · Status tracking · RBI MRM 2026</p>
      </div>

      <div className="flex gap-4 overflow-x-auto pb-2">
        <Column title="OVERDUE" icon={AlertTriangle} color={colors.crimson} models={queue.overdue} onUpdate={load} />
        <Column title="DUE SOON" icon={Clock} color="#F59E0B" models={queue.due_soon} onUpdate={load} />
        <Column title="SCHEDULED" icon={Calendar} color={colors.electric} models={queue.scheduled} onUpdate={load} />
        <Column title="COMPLETED" icon={CheckCircle} color={colors.mint} models={queue.completed} onUpdate={null} />
      </div>

      <div className="rounded-xl border p-4 text-xs font-mono" style={{ background: colors.navy3, borderColor: colors.goldDim + '30', color: colors.textSec }}>
        <span style={{ color: colors.gold }}>Validation Priority Order: </span>
        Overdue (immediate) → Critical PSI (&gt;0.25) → Tier-1 Scheduled → Tier-2/3 Routine
      </div>
    </div>
  );
}
