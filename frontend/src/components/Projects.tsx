import { ArrowRight, CodeXml, FolderGit2, FolderOpen, GitBranch, Layers3 } from 'lucide-react';
import { EmptyState, Panel } from './Panel';
import { formatBytes, plural, shortenPath } from '../format';
import type { ScanResult, View } from '../types';

const ecosystemLabel: Record<string, string> = { node: 'Node.js', python: 'Python', rust: 'Rust', php: 'PHP', other: 'Other' };

export function Projects({ result, onNavigate, onScan }: {
  result: ScanResult | null; onNavigate: (view: View) => void; onScan: () => void;
}) {
  const projects = result?.projects ?? [];
  return <>
    <div className="section-intro"><div><div className="section-eyebrow"><CodeXml size={14} /> PROJECT INVENTORY</div><h1>Your projects</h1><p>Every recognized codebase, along with its cleanup opportunities.</p></div>
      <button className="btn btn-outline" onClick={onScan}><FolderOpen size={17} /> Scan again</button></div>
    <Panel title="Detected repositories" subtitle={plural(projects.length, 'project') + ' found in the latest scan'}>
      {projects.length ? <div className="project-grid">{projects.map(project => {
        const candidates = result!.candidates.filter(c => c.project_path === project.path);
        const space = candidates.filter(c => c.can_clean).reduce((n, c) => n + c.bytes, 0);
        return <article className="project-card" key={project.path}>
          <div className="project-card-top"><span className="project-symbol"><Layers3 size={20} /></span><span className="project-space">{formatBytes(space)}</span></div>
          <h3 title={project.path}>{project.name}</h3><p title={project.path}>{shortenPath(project.path, 43)}</p>
          <div className="project-chips">{project.ecosystems.map(eco => <span className="eco-chip" key={eco}>{ecosystemLabel[eco] ?? eco}</span>)}
            {project.git_repository && <span className="eco-chip git-chip"><GitBranch size={12} /> Git</span>}</div>
          <div className="project-bottom"><span>{plural(candidates.length, 'candidate')}</span><button className="icon-link" aria-label={`Review candidates for ${project.name}`} onClick={() => onNavigate('candidates')}><ArrowRight size={17} /></button></div>
        </article>;
      })}</div> : <EmptyState icon={<FolderGit2 />} title="No projects discovered" description="Scan a workspace containing package.json, pyproject.toml, Cargo.toml or composer.json." action={<button className="btn btn-outline" onClick={onScan}>Find projects <ArrowRight size={16} /></button>} />}
    </Panel>
  </>;
}
