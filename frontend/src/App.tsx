import { AlertCircle, Bell, CheckCircle2, ChevronRight, CircleDot, FolderOpen, LoaderCircle, RefreshCw, Search, X } from 'lucide-react';
import { useCallback, useEffect, useMemo, useState } from 'react';
import { api } from './api';
import { Candidates } from './components/Candidates';
import { ConfirmModal } from './components/ConfirmModal';
import { Duplicates } from './components/Duplicates';
import { History } from './components/History';
import { Overview } from './components/Overview';
import { Projects } from './components/Projects';
import { Rules } from './components/Rules';
import { Sidebar } from './components/Sidebar';
import type { Candidate, CleanupOperation, DuplicatesResult, Meta, Rule, ScanResult, View } from './types';

const navNames: Record<View, string> = {
  overview: 'Overview', candidates: 'Cleanup candidates', projects: 'Projects',
  history: 'Recovery history', duplicates: 'Duplicate explorer', rules: 'Safety & rules',
};

function getSavedWorkspace(): string {
  try { return localStorage.getItem('cleanslate.workspace') || ''; }
  catch { return ''; }
}

function App() {
  const [active, setActive] = useState<View>('overview');
  const [workspace, setWorkspace] = useState(getSavedWorkspace);
  const [meta, setMeta] = useState<Meta | null>(null);
  const [rules, setRules] = useState<Rule[]>([]);
  const [history, setHistory] = useState<CleanupOperation[]>([]);
  const [scanResult, setScanResult] = useState<ScanResult | null>(null);
  const [duplicatesResult, setDuplicatesResult] = useState<DuplicatesResult | null>(null);
  const [selected, setSelected] = useState<Set<string>>(new Set());
  const [busy, setBusy] = useState<'scan' | 'clean' | 'restore' | 'duplicates' | null>(null);
  const [showConfirm, setShowConfirm] = useState(false);
  const [toast, setToast] = useState<{ text: string; error: boolean } | null>(null);

  const notify = useCallback((text: string, error = false) => setToast({ text, error }), []);

  useEffect(() => {
    let live = true;
    void Promise.allSettled([api.meta(), api.rules(), api.history()]).then(results => {
      if (!live) return;
      const [metaResult, ruleResult, historyResult] = results;
      if (metaResult.status === 'fulfilled') {
        setMeta(metaResult.value);
        setWorkspace(current => current || metaResult.value.default_workspace);
      } else notify(metaResult.reason instanceof Error ? metaResult.reason.message : 'Could not load local API.', true);
      if (ruleResult.status === 'fulfilled') setRules(ruleResult.value);
      if (historyResult.status === 'fulfilled') setHistory(historyResult.value);
    });
    return () => { live = false; };
  }, [notify]);

  const saveWorkspace = useCallback((value: string) => {
    setWorkspace(value);
    try { localStorage.setItem('cleanslate.workspace', value); } catch { /* local preferences are optional */ }
  }, []);

  const runScan = useCallback(async (goToCandidates = true) => {
    if (!workspace.trim()) { notify('Enter a workspace directory first.', true); return; }
    setBusy('scan');
    try {
      const result = await api.scan(workspace.trim());
      setScanResult(result);
      setSelected(new Set());
      setDuplicatesResult(null);
      if (goToCandidates) setActive('candidates');
      notify(`Scan complete: ${result.projects.length} projects, ${result.candidates.length} recommendations.`);
    } catch (error) { notify(error instanceof Error ? error.message : 'Scan failed.', true); }
    finally { setBusy(null); }
  }, [workspace, notify]);

  const refreshHistory = useCallback(async () => {
    try { setHistory(await api.history()); }
    catch (error) { notify(error instanceof Error ? error.message : 'Could not load history.', true); }
  }, [notify]);

  const selection = useMemo(() => (scanResult?.candidates ?? []).filter(c => selected.has(c.id) && c.can_clean), [scanResult, selected]);
  const toggleSelected = useCallback((id: string) => setSelected(previous => {
    const next = new Set(previous);
    if (next.has(id)) next.delete(id); else next.add(id);
    return next;
  }), []);
  const selectSafe = useCallback(() => setSelected(new Set((scanResult?.candidates ?? [])
    .filter(c => c.can_clean && c.risk === 'safe').map(c => c.id))), [scanResult]);

  const confirmCleanup = async (confirmReview: boolean) => {
    if (!scanResult || !selection.length) return;
    setBusy('clean');
    try {
      const outcome = await api.clean(scanResult.scan_id, selection.map(c => c.id), confirmReview);
      setShowConfirm(false);
      setSelected(new Set());
      setScanResult(null); // Receipt is one-use and the filesystem is now different.
      await refreshHistory();
      setActive('history');
      if (outcome.errors.length) notify(`Partial cleanup: ${outcome.errors.join(' · ')}`, true);
      else notify(`${outcome.moved_count ?? 0} items moved to recovery. You can restore them anytime.`);
    } catch (error) {
      setShowConfirm(false);
      setScanResult(null); // One-use scan receipt consumed, even on validation failure.
      notify(error instanceof Error ? error.message : 'Cleanup failed. Run a new scan.', true);
    } finally { setBusy(null); }
  };

  const runRestore = async (operationId: string) => {
    if (!window.confirm('Restore all available files in this operation? Existing files will never be overwritten.')) return;
    setBusy('restore');
    try {
      const outcome = await api.restore(operationId);
      await refreshHistory();
      setScanResult(null);
      if (outcome.errors.length) notify(`Some items were not restored: ${outcome.errors.join(' · ')}`, true);
      else notify(`${outcome.restored_count ?? 0} items restored successfully.`);
    } catch (error) { notify(error instanceof Error ? error.message : 'Restore failed.', true); }
    finally { setBusy(null); }
  };

  const runDuplicates = async () => {
    if (!workspace.trim()) { notify('Enter a workspace directory first.', true); return; }
    setBusy('duplicates');
    try {
      const result = await api.duplicates(workspace.trim());
      setDuplicatesResult(result);
      notify(`Duplicate analysis complete: ${result.groups.length} matching groups.`);
    } catch (error) { notify(error instanceof Error ? error.message : 'Duplicate scan failed.', true); }
    finally { setBusy(null); }
  };

  const activeContent = () => {
    switch (active) {
      case 'overview': return <Overview result={scanResult} history={history} onScan={() => void runScan()} onNavigate={setActive} />;
      case 'candidates': return <Candidates result={scanResult} selected={selected} onToggle={toggleSelected} onSelectSafe={selectSafe}
        onClear={() => setSelected(new Set())} onCleanup={() => setShowConfirm(true)} onScan={() => void runScan()} busy={busy !== null} />;
      case 'projects': return <Projects result={scanResult} onNavigate={setActive} onScan={() => void runScan()} />;
      case 'history': return <History operations={history} onRestore={id => void runRestore(id)} busy={busy !== null} />;
      case 'duplicates': return <Duplicates result={duplicatesResult} onSearch={() => void runDuplicates()} busy={busy !== null} />;
      case 'rules': return <Rules meta={meta} rules={rules} />;
    }
  };

  return <div className="app-layout">
    <Sidebar active={active} onChange={setActive} version={meta?.version ?? ''} />
    <div className="app-main"><header className="app-topbar">
      <div className="breadcrumb"><span>Workspace</span><ChevronRight size={14} /><strong>{navNames[active]}</strong></div>
      <div className="topbar-actions"><span className="local-indicator"><CircleDot size={14} /> LOCAL MODE</span>
        <span className="topbar-separator" /><button className="round-icon" aria-label="View recovery history" onClick={() => setActive('history')}><Bell size={18} /></button>
        <span className="avatar" title="Local profile">CS</span></div>
    </header>
      <main className="main-inner">
        <div className="workspace-bar"><div className="workspace-bar-label"><FolderOpen size={16} /><span>ACTIVE WORKSPACE</span></div>
          <div className="workspace-input-wrap"><Search size={17} /><input aria-label="Workspace directory path" spellCheck={false}
            placeholder="/home/you/Projects or C:\\Users\\You\\Projects"
            value={workspace} onChange={e => saveWorkspace(e.target.value)} onKeyDown={event => { if (event.key === 'Enter') void runScan(); }} />
            <button title="Scan directory" aria-label="Scan directory" disabled={busy !== null} onClick={() => void runScan()}>{busy === 'scan' ? <LoaderCircle className="spin" size={18} /> : <RefreshCw size={18} />}</button></div>
          <span className="workspace-bar-caption">Folders stay on your computer.</span>
        </div>
        {scanResult?.warnings.length ? <div className="scan-warnings" role="status"><AlertCircle size={18} /><span>{scanResult.warnings.length} folder(s) could not be inspected. Results may be incomplete.</span></div> : null}
        {activeContent()}
        <footer className="page-footer"><span>© {new Date().getFullYear()} Clean Slate · Built for developers</span>
          <span><CheckCircle2 size={14} /> Local-first. Reversible by default.</span></footer>
      </main></div>
    {showConfirm && selection.length > 0 && <ConfirmModal selection={selection as Candidate[]} busy={busy !== null}
      onCancel={() => setShowConfirm(false)} onConfirm={confirmReview => void confirmCleanup(confirmReview)} />}
    {toast && <div className={`toast ${toast.error ? 'toast-error' : ''}`} role="status">
      {toast.error ? <AlertCircle size={19} /> : <CheckCircle2 size={19} />}<span>{toast.text}</span>
      <button aria-label="Dismiss message" onClick={() => setToast(null)}><X size={16} /></button>
    </div>}
  </div>;
}

export default App;
