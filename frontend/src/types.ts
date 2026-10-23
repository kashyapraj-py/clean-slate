export type Risk = 'safe' | 'review';
export type View = 'overview' | 'candidates' | 'projects' | 'history' | 'duplicates' | 'rules';

export interface Project {
  path: string;
  name: string;
  ecosystems: string[];
  git_repository: boolean;
}

export interface Candidate {
  id: string;
  path: string;
  project_path: string;
  name: string;
  rule_id: string;
  category: string;
  risk: Risk;
  reason: string;
  bytes: number;
  files: number;
  fingerprint: string;
  protected_reason: string | null;
  can_clean: boolean;
}

export interface ScanResult {
  scan_id: string;
  root: string;
  scanned_at: string;
  projects: Project[];
  candidates: Candidate[];
  warnings: string[];
  total_bytes: number;
  safe_bytes: number;
  protected_count: number;
}

export interface CleanupItem {
  id: string;
  operation_id: string;
  original_path: string;
  quarantine_path: string;
  category: string;
  bytes: number;
  restored_at: string | null;
}

export interface CleanupOperation {
  id: string;
  root: string;
  created_at: string;
  status: 'running' | 'completed' | 'partial' | 'failed';
  bytes: number;
  restored_count: number;
  items: CleanupItem[];
}

export interface MutationResult {
  operation: CleanupOperation;
  moved_count?: number;
  restored_count?: number;
  errors: string[];
}

export interface DuplicateGroup {
  bytes_per_file: number;
  reclaimable_bytes: number;
  sha256: string;
  paths: string[];
}

export interface DuplicatesResult {
  root: string;
  files_scanned: number;
  files_skipped: number;
  reclaimable_bytes: number;
  groups: DuplicateGroup[];
  truncated: boolean;
  notice: string;
}

export interface Rule {
  id: string;
  label: string;
  category: string;
  ecosystems: string[];
  risk: Risk;
  explanation: string;
}

export interface Meta {
  version: string;
  default_workspace: string;
  data_dir: string;
  safety: string;
}
