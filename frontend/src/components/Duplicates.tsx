import { ArrowRight, CopyCheck, Fingerprint, FolderSearch, ShieldCheck } from 'lucide-react';
import { EmptyState, Panel } from './Panel';
import { formatBytes, shortenPath } from '../format';
import type { DuplicatesResult } from '../types';

export function Duplicates({ result, busy, onSearch }: {
  result: DuplicatesResult | null; busy: boolean; onSearch: () => void;
}) {
  return <>
    <div className="section-intro"><div><div className="section-eyebrow"><Fingerprint size={14} /> CONTENT HASH ANALYSIS</div><h1>Duplicate explorer</h1>
      <p>Find files with identical SHA-256 hashes. Analysis is always read-only.</p></div>
      <button className="btn btn-primary" disabled={busy} onClick={onSearch}><FolderSearch size={17} />{busy ? 'Analyzing…' : 'Find duplicates'} <ArrowRight size={17} /></button></div>
    <div className="notice-box"><ShieldCheck size={20} /><div><strong>Your files are never modified.</strong><span>Files are grouped by size before hashing. Source control internals and installed dependencies are excluded to keep scans focused.</span></div></div>
    <div className="stats-grid stats-grid-three"><div className="stat-card"><span>Potential duplicate space</span><strong>{result ? formatBytes(result.reclaimable_bytes) : '—'}</strong></div>
      <div className="stat-card"><span>Files inspected</span><strong>{result ? result.files_scanned.toLocaleString() : '—'}</strong></div>
      <div className="stat-card"><span>Duplicate groups</span><strong>{result ? result.groups.length : '—'}</strong></div></div>
    <Panel title="Matching file groups" subtitle="Each group contains files with exactly matching content hashes">
      {result && result.groups.length ? <div className="duplicate-groups">{result.groups.map(group => <div className="duplicate-group" key={group.sha256}>
        <div className="duplicate-head"><span className="duplicate-icon"><CopyCheck size={20} /></span><div><h3>{group.paths.length} matching files</h3><p>SHA-256 · {group.sha256.slice(0, 20)}…</p></div>
          <div className="duplicate-size"><strong>{formatBytes(group.reclaimable_bytes)}</strong><span>potential duplicate space</span></div></div>
        {group.paths.map(path => <div className="duplicate-path" title={path} key={path}>{shortenPath(path, 125)}</div>)}
      </div>)}</div> : <EmptyState icon={<Fingerprint />} title={result ? 'No duplicates found' : 'Find identical files'} description={result ? 'No matching duplicate groups were found in this scan.' : 'Run a read-only analysis to detect duplicate files by their content, not just their names.'} action={!result && <button className="btn btn-outline" disabled={busy} onClick={onSearch}>Start analysis <ArrowRight size={16} /></button>} />}
      {result?.truncated && <p className="data-note">Showing the first 100 groups. Narrow your workspace to inspect the rest.</p>}
    </Panel>
  </>;
}
