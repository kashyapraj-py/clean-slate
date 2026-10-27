import {
  Blocks, CircleHelp, FolderTree, HardDriveDownload, History,
  LayoutDashboard, ScanSearch, ShieldCheck, Sparkles,
} from 'lucide-react';
import type { ComponentType } from 'react';
import type { View } from '../types';

interface NavItem { id: View; label: string; icon: ComponentType<{ size?: number; strokeWidth?: number }>; }

const primary: NavItem[] = [
  { id: 'overview', label: 'Overview', icon: LayoutDashboard },
  { id: 'candidates', label: 'Cleanup candidates', icon: ScanSearch },
  { id: 'projects', label: 'Your projects', icon: FolderTree },
  { id: 'history', label: 'Recovery history', icon: History },
  { id: 'duplicates', label: 'Duplicate explorer', icon: Blocks },
];
const secondary: NavItem[] = [{ id: 'rules', label: 'Safety & rules', icon: ShieldCheck }];

export function Sidebar({ active, onChange, version }: { active: View; onChange: (view: View) => void; version: string }) {
  function nav(items: NavItem[]) {
    return items.map(({ id, label, icon: Icon }) => (
      <button key={id} type="button" className={`nav-item ${active === id ? 'nav-item-active' : ''}`}
        aria-current={active === id ? 'page' : undefined} onClick={() => onChange(id)}>
        <Icon size={18} strokeWidth={1.8} /><span>{label}</span>
      </button>
    ));
  }
  return (
    <aside className="sidebar">
      <button className="brand" type="button" onClick={() => onChange('overview')} aria-label="Clean Slate home">
        <span className="brand-mark"><Sparkles size={21} strokeWidth={2.3} /></span>
        <span className="brand-text">clean<span>slate</span><small>WORKSPACE INTELLIGENCE</small></span>
      </button>
      <div className="sidebar-main">
        <div className="nav-caption">WORKSPACE</div>
        <nav className="nav-group" aria-label="Main navigation">{nav(primary)}</nav>
        <div className="nav-caption nav-caption-second">PREFERENCES</div>
        <nav className="nav-group" aria-label="Preferences">{nav(secondary)}</nav>
      </div>
      <div className="sidebar-bottom">
        <div className="privacy-block"><HardDriveDownload size={17} /><div><strong>On your machine</strong><span>No uploads. No telemetry.</span></div></div>
        <div className="sidebar-version"><CircleHelp size={14} /><span>Clean Slate {version || '0.1.0'}</span><span className="status-dot" /></div>
      </div>
    </aside>
  );
}
