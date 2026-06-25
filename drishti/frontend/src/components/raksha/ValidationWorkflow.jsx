import React, { useEffect, useState } from 'react';
import { AlertTriangle, Clock, CheckCircle, Calendar } from 'lucide-react';
import { raksha } from '../../utils/api';
import { colors, psiColor } from '../../utils/colors';
import { SectionHead, Badge, Spinner } from '../ui';

function ModelCard({ model, accentColor, onUpdate }) {
  const [updating, setUpdating] = useState(false);

  const handleChange = (newStatus) => {
    setUpdating(true);
    raksha.updateStatus(model.id, { validation_status: newStatus, notes: 'Updated via DRISHTI workflow' })
      .then(() => { onUpdate?.(); setUpdating(false); })
      .catch(() => setUpdating(false));
  };

  const psiC = psiColor(model.psi_current);

  return (
    <div className="p-4 rounded-2xl transition-all"
      style={{
        background: `linear-gradient(145deg, ${accentColor}08, rgba(5,13,26,0.6))`,
        border: `1px solid ${accentColor}20`,
      }}>
      <div className="flex items-start justify-between gap-2 mb-3">
        <div>
          <div className="text-xs font-semibold" style={{ color: colors.textPri }}>{model.name}</div>
          <div className="text-xs font-mono mt-1" style={{ color: colors.textMut }}>
            {model.id} · Tier {model.tier}
          </div>
        </div>
        <span className="text-xs font-mono font-bold px-2 py-0.5 rounded-lg flex-shrink-0"
          style={{ background: psiC + '15', color: psiC, border: `1px solid ${psiC}25` }}>
          PSI {model.psi_current?.toFixed(2)}
        </span>
      </div>

      {model.days_overdue != null && (
        <div className="flex items-center gap-1.5 text-xs font-mono mb-2.5"
          style={{ color: colors.crimson }}>
          <AlertTriangle size={11} />
          {model.days_overdue}d overdue
        </div>
      )}

      <div className="text-xs mb-3" style={{ color: colors.textMut }}>
        Last validated: {model.last_validated ?? 'Never'}
      </div>

      {onUpdate && (
        <select
          onChange={e => e.target.value && handleChange(e.target.value)}
          disabled={updating}
          className="w-full text-xs font-mono px-2.5 py-2 rounded-xl outline-none"
          style={{
            background: 'rgba(255,255,255,0.04)',
            border: `1px solid ${accentColor}25`,
            color: colors.textSec,
          }}
          defaultValue=""
        >
          <option value="" disabled>Update status...</option>
          <option value="Validated">Mark Validated</option>
          <option value="Pending Revalidation">Pending Revalidation</option>
          <option value="Validation Overdue">Validation Overdue</option>
        </select>
      )}
    </div>
  );
}

function Column({ title, icon: Icon, color, models, onUpdate, urgent }) {
  return (
    <div className="flex-1 min-w-52 rounded-2xl overflow-hidden"
      style={{
        background: `linear-gradient(180deg, ${color}08 0%, rgba(5,13,26,0.6) 100%)`,
        border: `1px solid ${color}20`,
      }}>
      {/* Column header */}
      <div className="px-4 py-3 flex items-center gap-2"
        style={{ borderBottom: `1px solid ${color}15` }}>
        <Icon size={13} style={{ color }} />
        <span className="text-xs font-mono font-bold" style={{ color }}>{title}</span>
        {models.length > 0 && (
          <span className="ml-auto text-xs font-mono w-5 h-5 rounded-full flex items-center justify-center"
            style={{ background: `${color}20`, color }}>
            {models.length}
          </span>
        )}
      </div>

      <div className="p-3 space-y-3">
        {models.length === 0 && (
          <div className="text-xs font-mono py-4 text-center" style={{ color: colors.textMut }}>No models</div>
        )}
        {models.map(m => (
          <ModelCard key={m.id} model={m} accentColor={color} onUpdate={onUpdate} />
        ))}
      </div>
    </div>
  );
}

export default function ValidationWorkflow() {
  const [queue, setQueue] = useState({ overdue: [], due_soon: [], scheduled: [], completed: [] });
  const [loading, setLoading] = useState(true);

  const load = () => {
    raksha.validationQueue()
      .then(r => { setQueue(r.data); setLoading(false); })
      .catch(() => setLoading(false));
  };

  useEffect(() => { load(); }, []);

  if (loading) return <Spinner color={colors.mint} />;

  return (
    <div className="space-y-6">
      <SectionHead
        title="RAKSHA — Validation Queue"
        accent="रक्षा"
        subtitle="Model validation workflow · Status tracking · Priority management"
        color={colors.mint}
      />

      {/* Priority rule */}
      <div className="flex items-center gap-3 px-4 py-3 rounded-xl text-xs font-mono"
        style={{ background: 'rgba(201,168,76,0.05)', border: '1px solid rgba(201,168,76,0.12)', color: colors.textMut }}>
        <span style={{ color: colors.gold }}>Priority order: </span>
        <span style={{ color: colors.crimson }}>Overdue</span>
        <span>›</span>
        <span style={{ color: colors.amber }}>Critical PSI</span>
        <span>›</span>
        <span style={{ color: colors.electric }}>Scheduled</span>
        <span>›</span>
        <span style={{ color: colors.mint }}>Completed</span>
      </div>

      <div className="flex gap-4 overflow-x-auto pb-2">
        <Column title="OVERDUE" icon={AlertTriangle} color={colors.crimson} models={queue.overdue} onUpdate={load} urgent />
        <Column title="DUE SOON" icon={Clock} color={colors.amber} models={queue.due_soon} onUpdate={load} />
        <Column title="SCHEDULED" icon={Calendar} color={colors.electric} models={queue.scheduled} onUpdate={load} />
        <Column title="COMPLETED" icon={CheckCircle} color={colors.mint} models={queue.completed} onUpdate={null} />
      </div>
    </div>
  );
}
