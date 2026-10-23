export function formatBytes(bytes: number): string {
  if (bytes < 1024) return `${bytes.toLocaleString()} B`;
  const unit = Math.min(Math.floor(Math.log(bytes) / Math.log(1024)), 4);
  return `${(bytes / 1024 ** unit).toFixed(bytes < 10 * 1024 ** unit ? 2 : 1)} ${['B', 'KB', 'MB', 'GB', 'TB'][unit]}`;
}

export function formatDate(date: string): string {
  return new Date(date).toLocaleString(undefined, { dateStyle: 'medium', timeStyle: 'short' });
}

export function shortenPath(path: string, max = 65): string {
  if (path.length <= max) return path;
  return `…${path.slice(-(max - 1))}`;
}

export function plural(num: number, noun: string): string {
  return `${num.toLocaleString()} ${noun}${num === 1 ? '' : 's'}`;
}
