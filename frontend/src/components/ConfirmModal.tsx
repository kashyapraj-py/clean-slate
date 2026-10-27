import { AlertTriangle, ArrowRight, ShieldCheck, X } from 'lucide-react';
import { useEffect, useRef, useState } from 'react';
import { formatBytes, plural } from '../format';
import type { Candidate } from '../types';

export function ConfirmModal({ selection, busy, onCancel, onConfirm }: {
  selection: Candidate[]; busy: boolean; onCancel: () => void; onConfirm: (confirmReview: boolean) => void;
}) {
  const review = selection.some(c => c.risk === 'review');
  const [acknowledged, setAcknowledged] = useState('');
  const cancelRef = useRef<HTMLButtonElement>(null);
  const total = selection.reduce((n, c) => n + c.bytes, 0);
  useEffect(() => {
    cancelRef.current?.focus();
    function escapeKey(event: KeyboardEvent) { if (event.key === 'Escape' && !busy) onCancel(); }
    document.addEventListener('keydown', escapeKey);
    return () => document.removeEventListener('keydown', escapeKey);
  }, [busy, onCancel]);
  return <div className="modal-backdrop" onMouseDown={event => { if (event.target === event.currentTarget && !busy) onCancel(); }}>
    <div className="modal" role="dialog" aria-modal="true" aria-labelledby="modal-title">
      <div className="modal-top"><span className="modal-emblem"><AlertTriangle size={22} /></span><button className="icon-link" aria-label="Close dialog" disabled={busy} onClick={onCancel}><X size={20} /></button></div>
      <h2 id="modal-title">Review before cleanup</h2>
      <p>You are about to move <strong>{plural(selection.length, 'item')}</strong> ({formatBytes(total)}) into Clean Slate's private quarantine. Nothing will be permanently deleted.</p>
      <div className="modal-items">{selection.slice(0, 5).map(c => <div key={c.id}><span title={c.path}>{c.path.split(/[\\/]/).pop()}</span><strong>{formatBytes(c.bytes)}</strong></div>)}
        {selection.length > 5 && <small>And {selection.length - 5} more…</small>}</div>
      {review && <div className="modal-warning"><AlertTriangle size={18} /><div><strong>Review-risk artifacts included</strong>
        <p>These may contain local changes or require substantial work to recreate. Type <b>REVIEW</b> to proceed.</p>
        <input aria-label="Type REVIEW to confirm" autoComplete="off" placeholder="Type REVIEW" value={acknowledged} onChange={e => setAcknowledged(e.target.value)} /></div></div>}
      <div className="modal-actions"><button className="btn btn-outline" ref={cancelRef} disabled={busy} onClick={onCancel}>Cancel</button>
        <button className="btn btn-primary" disabled={busy || (review && acknowledged !== 'REVIEW')} onClick={() => onConfirm(review)}>
          {busy ? 'Moving files…' : 'Move to recovery'} <ArrowRight size={17} /></button></div>
      <div className="modal-assurance"><ShieldCheck size={15} /> Full restore is available from Recovery history.</div>
    </div>
  </div>;
}
