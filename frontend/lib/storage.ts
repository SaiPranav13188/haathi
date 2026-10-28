// Browser storage can be missing or throw (private mode, blocked site data). Never let that break the app.
export function load<T>(key: string, fallback: T): T {
  try {
    const raw = window.localStorage.getItem(`haathi:${key}`);
    return raw == null ? fallback : (JSON.parse(raw) as T);
  } catch {
    return fallback;
  }
}
export function save(key: string, value: unknown): void {
  try {
    window.localStorage.setItem(`haathi:${key}`, JSON.stringify(value));
  } catch {
    /* storage unavailable: keep working in memory */
  }
}
export function clearAll(): void {
  try {
    Object.keys(window.localStorage).filter((k) => k.startsWith("haathi:")).forEach((k) => window.localStorage.removeItem(k));
  } catch {
    /* ignore */
  }
}
