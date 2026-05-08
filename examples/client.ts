/**
 * Minimal TypeScript client for printd.
 *
 * No dependencies — drop into a Vite/Next/Remix frontend or a Node script.
 *
 * Usage:
 *   const c = new Printd("http://printd.local:8080", "secret");
 *   await c.printDataUrl(canvas.toDataURL("image/png"));
 */

export interface PrintOptions {
  cut?: boolean;
  feed?: number;
  partial_cut?: boolean;
}

export class Printd {
  constructor(private readonly baseUrl: string, private readonly apiKey?: string) {}

  private headers(extra: Record<string, string> = {}) {
    return {
      ...(this.apiKey ? { Authorization: `Bearer ${this.apiKey}` } : {}),
      ...extra,
    };
  }

  async health(): Promise<{ ok: boolean; printer: string; kind: string; target: string }> {
    const r = await fetch(`${this.baseUrl}/healthz`);
    if (!r.ok) throw new Error(`printd /healthz ${r.status}`);
    return r.json();
  }

  async printDataUrl(image: string, opts: PrintOptions = {}) {
    const r = await fetch(`${this.baseUrl}/print`, {
      method: "POST",
      headers: this.headers({ "Content-Type": "application/json" }),
      body: JSON.stringify({ image, cut: opts.cut ?? true, feed: opts.feed, partial_cut: opts.partial_cut ?? false }),
    });
    if (!r.ok) throw new Error(`printd /print ${r.status}: ${await r.text()}`);
    return (await r.json()) as { ok: true; width: number; height: number };
  }

  async printBlob(image: Blob, opts: PrintOptions = {}) {
    const fd = new FormData();
    fd.append("image", image, "ticket.png");
    if (opts.cut !== undefined) fd.append("cut", String(opts.cut));
    if (opts.feed !== undefined) fd.append("feed", String(opts.feed));
    if (opts.partial_cut !== undefined) fd.append("partial_cut", String(opts.partial_cut));
    const r = await fetch(`${this.baseUrl}/print/upload`, {
      method: "POST",
      headers: this.headers(),
      body: fd,
    });
    if (!r.ok) throw new Error(`printd /print/upload ${r.status}: ${await r.text()}`);
    return (await r.json()) as { ok: true; width: number; height: number };
  }

  async cut(partial = false) {
    const r = await fetch(`${this.baseUrl}/cut`, {
      method: "POST",
      headers: this.headers({ "Content-Type": "application/json" }),
      body: JSON.stringify({ partial }),
    });
    if (!r.ok) throw new Error(`printd /cut ${r.status}`);
  }

  async feed(lines: number) {
    const r = await fetch(`${this.baseUrl}/feed`, {
      method: "POST",
      headers: this.headers({ "Content-Type": "application/json" }),
      body: JSON.stringify({ lines }),
    });
    if (!r.ok) throw new Error(`printd /feed ${r.status}`);
  }
}
