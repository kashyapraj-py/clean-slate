import { ArrowRight, CircleCheck, ClipboardList, FolderCode, HardDrive, Info, Layers3, RotateCcw, ShieldCheck, Sparkles } from 'lucide-react';
import { EmptyState, Panel } from './Panel';
import type { ReactNode } from 'react';
import { formatBytes, formatDate, plural, shortenPath } from '../format';
import type { CleanupOperation, ScanResult, View } from '../types';

function Stat({ label, value, note, icon }: { label: string; value: string; note: string; icon: ReactNode }) {
  return <div className="stat-card"><div className="stat-card-head"><span>{label}</span><span className="stat-icon">{icon}</span></div>
    <strong>{value}</strong><span className="stat-note">{note}</span></div>;
}

export function Overview({ result, history, onNavigate, onScan }: {
  result: ScanResult | null; history: CleanupOperation[];
  onNavigate: (view: View) => void; onScan: () => void;
}) {
  const ready = result?.candidates.filter(c => c.can_clean) ?? [];
  const safe = ready.filter(c => c.risk === 'safe');
  const categories = Object.entries(ready.reduce<Record<string, number>>((acc, candidate) => {
    acc[candidate.category] = (acc[candidate.category] ?? 0) + candidate.bytes;
    return acc;
  }, {})).sort((a, b) => b[1] - a[1]);
  const total = categories.reduce((sum, [, bytes]) => sum + bytes, 0);
  const palette = ['#20b18a', '#6ac7a6', '#b5d1ca', '#d5e7dd'];
  let cumulative = 0;
  const segments = categories.map(([, bytes], index) => {
    const start = total ? cumulative / total * 100 : 0;
    cumulative += bytes;
    return `${palette[index % palette.length]} ${start}% ${total ? cumulative / total * 100 : 100}%`;
  });
  const recent = history.slice(0, 3);
  return <>
    <div className="hero">
      <div className="hero-copy"><div className="eyebrow"><Sparkles size={14} /> YOUR WORKSPACE, CLEARER</div>
        <h1>Less clutter.<br /><em>More room to build.</em></h1>
        <p>Find the build leftovers slowing down your machine. See what’s safe, review everything else, and restore anything you clean.</p>
        <div className="hero-actions"><button className="btn btn-primary" onClick={onScan}><HardDrive size={17} /> Scan workspace <ArrowRight size={16} /></button>
          <button className="btn btn-ghost-on-dark" onClick={() => onNavigate('rules')}><ShieldCheck size={17} /> How it stays safe</button></div>
      </div>
      <div className="hero-deco" aria-hidden="true"><div className="hero-orbit hero-orbit-one" /><div className="hero-orbit hero-orbit-two" /><div className="hero-core"><Layers3 size={49} strokeWidth={1.3} /></div>
        <span className="hero-spark hero-spark-a" /><span className="hero-spark hero-spark-b" /></div>
    </div>
    <div className="stats-grid">
      <Stat label="Potential space" value={result ? formatBytes(result.total_bytes) : '—'} note="Reclaimable, with review" icon={<HardDrive size={20} />} />
      <Stat label="Safe to clean" value={result ? formatBytes(result.safe_bytes) : '—'} note={plural(safe.length, 'safe candidate')} icon={<CircleCheck size={20} />} />
      <Stat label="Projects found" value={result ? String(result.projects.length) : '—'} note="Across this workspace" icon={<FolderCode size={20} />} />
      <Stat label="Protected items" value={result ? String(result.protected_count) : '—'} note="Never moved automatically" icon={<ShieldCheck size={20} />} />
    </div>
    <div className="content-two-col">
      <Panel title="Storage breakdown" subtitle="What is occupying reclaimable space" action={result && <span className="subtle-chip">Last scan · {formatDate(result.scanned_at)}</span>}>
        {result && total > 0 ? <div className="storage-inner">
          <div className="donut" style={{ background: `conic-gradient(${segments.join(', ')})` }}>
            <div className="donut-hole"><small>RECOVERABLE</small><strong>{formatBytes(total)}</strong></div>
          </div>
          <div className="storage-legend">{categories.map(([name, bytes], index) =>
            <div key={name} className="legend-row"><span className={`legend-dot legend-${index % 4}`} />
              <span className="legend-title">{name.charAt(0).toUpperCase() + name.slice(1)}</span>
              <strong>{formatBytes(bytes)}</strong></div>)}</div>
        </div> : <EmptyState icon={<ClipboardList />} title="Your next scan starts here" description="Run a scan to get a breakdown of recoverable storage across projects." action={<button className="btn btn-outline" onClick={onScan}>Scan now <ArrowRight size={16} /></button>} />}
      </Panel>
      <Panel title="Cleanup opportunities" subtitle="Largest verified recommendations" action={<button className="text-action" onClick={() => onNavigate('candidates')}>See all <ArrowRight size={15} /></button>}>
        {ready.length ? <div className="opportunity-list">{ready.slice(0, 4).map((candidate, i) =>
          <div className="opportunity" key={candidate.id}><span className="opportunity-number">{String(i + 1).padStart(2, '0')}</span>
            <div className="opportunity-info"><strong>{candidate.name}</strong><span title={candidate.path}>{shortenPath(candidate.path, 40)}</span></div>
            <div className="opportunity-right"><strong>{formatBytes(candidate.bytes)}</strong><small className={candidate.risk === 'safe' ? 'green-text' : 'orange-text'}>{candidate.risk === 'safe' ? 'Safe' : 'Review'}</small></div>
          </div>)}</div> : <EmptyState icon={<Layers3 />} title="Nothing to review yet" description="Scan a project to find cleanup candidates, or enjoy a clutter-free workspace." />}
      </Panel>
    </div>
    <div className="content-two-col">
      <Panel title="Recent activity" subtitle="Your cleanup history stays on this device" action={<button className="text-action" onClick={() => onNavigate('history')}>Recovery center <ArrowRight size={15} /></button>}>
        {recent.length ? <div className="activity-list">{recent.map(op => <div className="activity-row" key={op.id}>
          <span className="activity-icon"><RotateCcw size={17} /></span><div><strong>{op.items.length} items moved to recovery</strong><span>{formatDate(op.created_at)}</span></div>
          <span className="activity-size">{formatBytes(op.bytes)}</span></div>)}</div> : <EmptyState icon={<RotateCcw />} title="No cleanup history" description="Every cleanup you apply will show here with its restore option." />}
      </Panel>
      <div className="insight-card"><div className="insight-icon"><Info size={20} /></div>
        <h3>Your files stay yours.</h3><p>Everything happens locally. Clean Slate never uploads project contents, and cleanup moves items into quarantine instead of permanently deleting them.</p>
        <div className="insight-divider" /><div className="insight-foot"><ShieldCheck size={17} /><span>Git-aware · Preview-first · Reversible</span></div></div>
    </div>
  </>;
}
