export type PageItem = number | "ellipsis";

/** Janela curta de páginas: 1 … n-1 n n+1 … last. */
export function pageWindow(current: number, max: number): PageItem[] {
  if (max < 1) return [];
  const cur = Math.min(Math.max(current, 1), max);
  if (max <= 7) {
    return Array.from({ length: max }, (_, i) => i + 1);
  }

  const pages = new Set<number>([1, max, cur, cur - 1, cur + 1]);
  if (cur <= 3) {
    pages.add(2);
    pages.add(3);
    pages.add(4);
  }
  if (cur >= max - 2) {
    pages.add(max - 1);
    pages.add(max - 2);
    pages.add(max - 3);
  }

  const sorted = [...pages].filter((p) => p >= 1 && p <= max).sort((a, b) => a - b);
  const out: PageItem[] = [];
  let prev = 0;
  for (const p of sorted) {
    if (prev > 0 && p - prev > 1) out.push("ellipsis");
    out.push(p);
    prev = p;
  }
  return out;
}
