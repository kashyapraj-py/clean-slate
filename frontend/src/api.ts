import type { CleanupOperation, DuplicatesResult, Meta, MutationResult, Rule, ScanResult } from './types';

async function request<T>(path: string, payload?: unknown): Promise<T> {
  let response: Response;
  try {
    response = await fetch(`/api${path}`, {
      method: payload === undefined ? 'GET' : 'POST',
      ...(payload === undefined ? {} : { headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(payload) }),
    });
  } catch {
    throw new Error('Could not connect to Clean Slate. Start the local API using `cleanslate web`.');
  }
  if (!response.ok) {
    const error: unknown = await response.json().catch(() => null);
    const detail = typeof error === 'object' && error !== null && 'detail' in error ? error.detail : null;
    throw new Error(typeof detail === 'string' ? detail : `Request failed (${response.status}).`);
  }
  return response.json() as Promise<T>;
}

export const api = {
  meta: () => request<Meta>('/meta'),
  rules: () => request<Rule[]>('/rules'),
  history: () => request<CleanupOperation[]>('/history'),
  scan: (root: string, maxDepth = 8) => request<ScanResult>('/scans', { root, max_depth: maxDepth }),
  clean: (scanId: string, candidateIds: string[], confirmReview: boolean) =>
    request<MutationResult>('/cleanups', { scan_id: scanId, candidate_ids: candidateIds, confirm_review: confirmReview }),
  restore: (operationId: string) => request<MutationResult>('/restores', { operation_id: operationId }),
  duplicates: (root: string) => request<DuplicatesResult>('/duplicates', { root }),
};
