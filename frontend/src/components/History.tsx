import { ArchiveRestore, CheckCircle2, Clock3, FolderDown, History as HistoryIcon, RotateCcw, ShieldCheck } from 'lucide-react';
import { EmptyState, Panel } from './Panel';
import { formatBytes, formatDate, shortenPath } from '../format';
import type { CleanupOperation } from '../types';

export function History({ operations, onRestore, busy }: {
  operations: CleanupOperation[]; onRestore: (id: string) => void; busy: boolean;
}) {
  const recoverable = operations.reduce((count, op) => count + op.items.filter(item => !item.restored_at).length, 0);
  return <>
    <div className="section-intro"><div><div className="section-eyebrow"><ArchiveRestore size={14} /> PRIVATE RECOVERY CENTER</div><h1>Recovery history</h1>
      <p>Restore files without overwriting anything that has appeared in their place.</p></div></div>
    <div className="summary-strip"><div><span>Cleanup operations</span><strong>{operations.length}</strong></div><div><span>Recoverable items</span><strong>{recoverable}</strong></div><div><span>Total moved</span><strong>{formatBytes(operations.reduce((n, o) => n + o.bytes, 0))}</strong></div>
      <span className="summary-hint"><ShieldCheck size={17} /> Nothing permanently deleted</span></div>
    <Panel title="Operation timeline" subtitle="Stored in a local SQLite journal">
      {operations.length ? <div className="history-timeline">{operations.map(op => {
        const remaining = op.items.filter(item => !item.restored_at);
        return <article key={op.id} className="history-entry"><div className="history-entry-head">
          <div className="history-entry-title"><span className="timeline-symbol"><FolderDown size={19} /></span><div><h3>Workspace cleanup</h3><p><Clock3 size={13} /> {formatDate(op.created_at)}</p></div></div>
          <div className="history-controls"><span className={`status-label ${remaining.length ? 'status-ready' : 'status-done'}`}>
            {remaining.length ? `${remaining.length} recoverable` : 'Restored / empty'}</span>
            <button className="btn btn-small btn-outline" disabled={!remaining.length || busy} onClick={() => onRestore(op.id)}><RotateCcw size={15} /> Restore all</button></div>
        </div><div className="history-entry-meta"><strong>{formatBytes(op.bytes)}</strong><span>{op.items.length} items</span><span>{op.status}</span><code title={op.id}>#{op.id.slice(0, 10)}</code></div>
          <div className="history-file-list">{op.items.map(item => <div className="history-file" key={item.id}>
            {item.restored_at ? <CheckCircle2 size={15} className="green-text" /> : <ArchiveRestore size={15} />}
            <span title={item.original_path}>{shortenPath(item.original_path, 90)}</span><strong>{formatBytes(item.bytes)}</strong>
          </div>)}</div></article>;
      })}</div> : <EmptyState icon={<HistoryIcon />} title="A clean history, literally" description="When you clean a workspace, the files are quarantined and their restore records appear here." />}
    </Panel>
  </>;
}
