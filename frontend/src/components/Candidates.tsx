import { ArrowRight, Check, CircleAlert, FolderSearch, Search, ShieldAlert, ShieldCheck, Sparkles } from 'lucide-react';
import { useMemo, useState } from 'react';
import { EmptyState, Panel } from './Panel';
import { formatBytes, plural, shortenPath } from '../format';
import type { Candidate, ScanResult } from '../types';

type Filter = 'all' | 'safe' | 'review' | 'protected';

function RiskBadge({ item }: { item: Candidate }) {
  if (!item.can_clean) return <span className="risk risk-protected"><ShieldAlert size={13} /> Protected</span>;
  return item.risk === 'safe'
    ? <span className="risk risk-safe"><Check size={13} /> Safe</span>
    : <span className="risk risk-review"><CircleAlert size={13} /> Review</span>;
}

export function Candidates({ result, selected, onToggle, onSelectSafe, onClear, onCleanup, onScan, busy }: {
  result: ScanResult | null;
  selected: Set<string>;
  onToggle: (id: string) => void;
  onSelectSafe: () => void;
  onClear: () => void;
  onCleanup: () => void;
  onScan: () => void;
  busy: boolean;
}) {
  const [filter, setFilter] = useState<Filter>('all');
  const [query, setQuery] = useState('');
  const candidates = result?.candidates ?? [];
  const filtered = useMemo(() => candidates.filter(candidate => {
    const matches = filter === 'all' || (filter === 'protected' ? !candidate.can_clean : candidate.can_clean && candidate.risk === filter);
    return matches && `${candidate.path} ${candidate.name} ${candidate.category}`.toLowerCase().includes(query.toLowerCase());
  }), [candidates, query, filter]);
  const available = candidates.filter(candidate => candidate.can_clean);
  const selection = available.filter(candidate => selected.has(candidate.id));
  const totalSize = selection.reduce((sum, item) => sum + item.bytes, 0);
  const filters: { id: Filter; label: string; count: number }[] = [
    { id: 'all', label: 'All', count: candidates.length },
    { id: 'safe', label: 'Safe', count: candidates.filter(c => c.can_clean && c.risk === 'safe').length },
    { id: 'review', label: 'Review', count: candidates.filter(c => c.can_clean && c.risk === 'review').length },
    { id: 'protected', label: 'Protected', count: candidates.filter(c => !c.can_clean).length },
  ];
  return <>
    <div className="section-intro"><div><div className="section-eyebrow"><Sparkles size={14} /> VERIFIED SCAN RESULTS</div><h1>Cleanup candidates</h1>
      <p>Review exactly what is on your disk before choosing anything to clean.</p></div>
      <button className="btn btn-outline" onClick={onScan} disabled={busy}><FolderSearch size={17} /> Run new scan</button></div>
    <div className="summary-strip"><div><span>Detected items</span><strong>{candidates.length}</strong></div><div><span>Eligible space</span><strong>{formatBytes(result?.total_bytes ?? 0)}</strong></div><div><span>Selected space</span><strong>{formatBytes(totalSize)}</strong></div>
      <span className="summary-hint"><ShieldCheck size={17} /> Git-tracked files are protected</span></div>
    <Panel title="Review your files" subtitle="Only the items you explicitly select can be moved into recovery."
      action={<div className="inline-actions"><button className="btn btn-small btn-subtle" disabled={!result || busy} onClick={onSelectSafe}>Select safe</button><button className="btn btn-small btn-subtle" disabled={!selected.size || busy} onClick={onClear}>Clear</button></div>}>
      <div className="candidate-toolbar"><div className="filter-tabs" role="group" aria-label="Filter candidates">{filters.map(f =>
        <button key={f.id} onClick={() => setFilter(f.id)} className={`filter-tab ${filter === f.id ? 'filter-tab-active' : ''}`}>
          {f.label} <span>{f.count}</span></button>)}</div>
        <label className="table-search"><Search size={16} /><input aria-label="Search candidates" placeholder="Search files or paths" value={query} onChange={e => setQuery(e.target.value)} /></label>
      </div>
      {filtered.length ? <div className="candidate-table-scroll"><table className="candidate-table"><thead><tr>
        <th className="check-col"><span className="sr-only">Select</span></th><th>File or folder</th><th>Type</th><th>Risk</th><th className="align-right">Size</th></tr></thead>
        <tbody>{filtered.map(item => <tr key={item.id} className={`${!item.can_clean ? 'candidate-disabled' : ''} ${selected.has(item.id) ? 'candidate-selected' : ''}`}>
          <td className="check-col"><input type="checkbox" checked={selected.has(item.id)} disabled={!item.can_clean || busy} onChange={() => onToggle(item.id)} aria-label={`Select ${item.path}`} /></td>
          <td><div className="candidate-file"><div className="file-glyph"><FolderSearch size={18} /></div><div className="candidate-filename"><strong>{item.path.split(/[\\/]/).pop()}</strong>
            <span title={item.path}>{shortenPath(item.path, 73)}</span>
            <small>{item.protected_reason || item.reason}</small></div></div></td>
          <td><span className="cell-category">{item.category}</span></td><td><RiskBadge item={item} /></td><td className="align-right cell-metric"><strong>{formatBytes(item.bytes)}</strong><span>{plural(item.files, 'file')}</span></td>
        </tr>)}</tbody></table></div> : <EmptyState icon={<FolderSearch />} title="No matching candidates" description={result ? 'Try clearing the filter or choosing another workspace.' : 'Start a workspace scan to see files you can review.'} action={!result && <button className="btn btn-outline" onClick={onScan}>Scan workspace <ArrowRight size={16} /></button>} />}
      <div className="selection-footer"><span><strong>{selection.length}</strong> selected · {formatBytes(totalSize)}</span>
        <button className="btn btn-primary" disabled={!selection.length || busy} onClick={onCleanup}>
          {busy ? 'Working…' : 'Review cleanup'} <ArrowRight size={17} /></button></div>
    </Panel>
    <div className="footnote"><ShieldCheck size={16} /><span>Protected items are never selectable. Review-risk items require additional confirmation. <button onClick={onClear} disabled={!selected.size}>Clear selection</button></span></div>
  </>;
}
