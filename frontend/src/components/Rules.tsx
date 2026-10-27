import { CheckCheck, FileCode2, GitBranch, HardDrive, LockKeyhole, RotateCcw, ShieldCheck, ShieldOff } from 'lucide-react';
import { Panel } from './Panel';
import type { Meta, Rule } from '../types';

export function Rules({ rules, meta }: { rules: Rule[]; meta: Meta | null }) {
  return <>
    <div className="section-intro"><div><div className="section-eyebrow"><ShieldCheck size={14} /> BUILT FOR TRUST</div><h1>Safety & rules</h1>
      <p>Plain-language cleanup policies. No hidden deletion rules, no automatic cleanup.</p></div></div>
    <div className="safety-principles">
      {[{ icon: <GitBranch />, title: 'Git-aware', desc: 'Git-tracked files are excluded even inside build or cache directories.' },
      { icon: <LockKeyhole />, title: 'Sensitive-file guard', desc: 'Environment files, keys, database files, and symlinked items block cleanup.' },
      { icon: <RotateCcw />, title: 'Reversible moves', desc: 'Files move into private quarantine. Restore never overwrites a destination.' },
      { icon: <ShieldOff />, title: 'Local only', desc: 'No telemetry, cloud uploads, background jobs, or internet access are required.' }].map(item =>
        <div className="principle-card" key={item.title}><span>{item.icon}</span><h3>{item.title}</h3><p>{item.desc}</p></div>)}
    </div>
    <Panel title="Built-in detection rules" subtitle="Only known generated artifacts are recommended; review items are never selected automatically.">
      <div className="rule-list">{rules.map(rule => <div className="rule-row" key={rule.id}><div><h3>{rule.label}</h3><span>{rule.explanation}</span>
        <div className="rule-ecosystems">{rule.ecosystems.map(ecosystem => <small key={ecosystem}>{ecosystem}</small>)}</div></div>
        <span className={rule.risk === 'safe' ? 'risk risk-safe' : 'risk risk-review'}>{rule.risk === 'safe' ? <CheckCheck size={14} /> : <ShieldCheck size={14} />} {rule.risk}</span></div>)}</div>
    </Panel>
    <div className="content-two-col"><Panel title="Workspace configuration" subtitle="Optional .cleanslate.toml in the scanned root">
      <div className="code-note"><div><FileCode2 size={16} /> .cleanslate.toml</div><pre>{`[scan]\nexclude = ["**/fixtures/**", "my-important-build"]\ndisable_rules = ["node-modules"]`}</pre></div>
      <p className="muted-note">Exclusions protect paths from discovery and removal. This configuration is entirely local.</p></Panel>
      <Panel title="Private recovery location" subtitle="Files remain on your computer"><div className="recovery-address"><HardDrive size={21} /><code>{meta?.data_dir ?? 'Loading…'}</code></div>
        <p className="muted-note">Do not manually delete quarantine contents if you want to preserve the restore capability. Your data stays in this directory until you manage it yourself.</p></Panel></div>
  </>;
}
