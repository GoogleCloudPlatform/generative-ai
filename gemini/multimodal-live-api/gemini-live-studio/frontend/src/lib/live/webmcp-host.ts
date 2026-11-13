// Copyright 2026 Google LLC
//
// Licensed under the Apache License, Version 2.0 (the "License");
// you may not use this file except in compliance with the License.
// You may obtain a copy of the License at
//
//     http://www.apache.org/licenses/LICENSE-2.0
//
// Unless required by applicable law or agreed to in writing, software
// distributed under the License is distributed on an "AS IS" BASIS,
// WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
// See the License for the specific language governing permissions and
// limitations under the License.

export interface WebmcpRegisteredTool {
  name: string;
  description: string;
  inputSchema?: Record<string, unknown> | string;
  window?: Window;
  origin?: string;
}

export interface WebmcpAnnotations {
  readOnlyHint?: boolean;
  consequentialHint?: boolean;
  untrustedContentHint?: boolean;
}

export interface ModelContextLike extends EventTarget {
  registerTool(
    tool: {
      name: string;
      description: string;
      inputSchema?: Record<string, unknown>;
      annotations?: WebmcpAnnotations;
      execute: (
        input: Record<string, unknown> | string,
        options?: { signal?: AbortSignal },
      ) => Promise<unknown>;
    },
    options?: { signal?: AbortSignal },
  ): Promise<void> | void;
  getTools(): Promise<WebmcpRegisteredTool[]>;
  executeTool(
    tool: WebmcpRegisteredTool,
    input: Record<string, unknown> | string,
    options?: { signal?: AbortSignal },
  ): Promise<string | null>;
}

/**
 * Returns `document.modelContext` when the browser supports WebMCP, else `null`.
 */
export function nativeModelContext(
  doc: Document | undefined = typeof document !== 'undefined'
    ? document
    : undefined,
): ModelContextLike | null {
  if (!doc) return null;
  const mc = (doc as unknown as { modelContext?: ModelContextLike })
    .modelContext;
  return mc &&
    typeof mc.registerTool === 'function' &&
    typeof mc.getTools === 'function' &&
    typeof mc.executeTool === 'function'
    ? mc
    : null;
}

export interface WebmcpToolInfo {
  name: string;
  description: string;
  inputSchema?: Record<string, unknown>;
}

export type WebmcpToolResult = Record<string, unknown>;
export type WebmcpCaller = 'live' | 'app' | 'external';

export interface WebmcpToolExecutionOutput {
  result: WebmcpToolResult;
  imageDataUrl?: string;
}

export interface WebmcpToolDefinition<TCtx = { signal: AbortSignal }> {
  name: string;
  description: string;
  inputSchema?: Record<string, unknown>;
  readOnly?: boolean;
  consequential?: boolean;
  untrusted?: boolean;
  /**
   * When true, concurrent calls with identical `(name, canonicalJSON(args))`
   * share the in-flight execution Promise instead of triggering duplicate UI
   * dialogs (such as double file pickers when a voice model emits back-to-back
   * identical FunctionCalls in a single turn).
   */
  coalesceInFlight?: boolean;
  execute: (
    args: Record<string, unknown>,
    ctx: TCtx,
  ) => Promise<WebmcpToolExecutionOutput>;
}

export class WebmcpToolError extends Error {
  constructor(message: string) {
    super(message);
    this.name = 'WebmcpToolError';
  }
}

export class WebmcpCallEvent extends Event {
  readonly caller: WebmcpCaller;
  readonly name: string;
  readonly args: Record<string, unknown>;
  readonly result: WebmcpToolResult;
  readonly imageDataUrl: string | undefined;
  readonly ms: number;

  constructor(
    caller: WebmcpCaller,
    name: string,
    args: Record<string, unknown>,
    result: WebmcpToolResult,
    ms: number,
    imageDataUrl?: string,
  ) {
    super('call');
    this.caller = caller;
    this.name = name;
    this.args = args;
    this.result = result;
    this.ms = ms;
    this.imageDataUrl = imageDataUrl;
  }
}

export interface WebmcpDiagnostics {
  schemaType: string;
  argsForm: 'object' | 'string' | null;
  firstError: string;
  dropped: string[];
  conflicts: string[];
}

/** Deterministic key-sorted JSON serialization for schema and argument comparison. */
export function canonicalJSON(value: unknown): string {
  return JSON.stringify(value, (_k, v: unknown) =>
    v && typeof v === 'object' && !Array.isArray(v)
      ? Object.fromEntries(
          Object.entries(v as Record<string, unknown>).sort(([a], [b]) =>
            a < b ? -1 : a > b ? 1 : 0,
          ),
        )
      : v,
  );
}

export function annotationsFor(
  def: Pick<
    WebmcpToolDefinition<unknown>,
    'readOnly' | 'consequential' | 'untrusted'
  >,
): WebmcpAnnotations | undefined {
  const a: WebmcpAnnotations = {
    ...(def.readOnly ? { readOnlyHint: true } : {}),
    ...(def.consequential ? { consequentialHint: true } : {}),
    ...(def.untrusted ? { untrustedContentHint: true } : {}),
  };
  return Object.keys(a).length ? a : undefined;
}

export function asObject(value: unknown): Record<string, unknown> | null {
  let v = value;
  if (typeof v === 'string') {
    try {
      v = JSON.parse(v) as unknown;
    } catch {
      return null;
    }
  }
  return v && typeof v === 'object' && !Array.isArray(v)
    ? (v as Record<string, unknown>)
    : null;
}

const PARSE_ERROR = /parse input arguments|not of type 'object'/i;

/**
 * Framework-agnostic WebMCP (`document.modelContext`) and fallback tool host:
 * - Verifies tool ownership (name, description, canonical schema, and window)
 *   before advertising or executing tools so third-party injected scripts
 *   cannot hijack model tool calls.
 * - Negotiates both Chrome 154 JSON-string arguments and CG spec object
 *   arguments automatically.
 * - Optionally coalesces concurrent identical calls (`coalesceInFlight: true`)
 *   to prevent duplicate interactive modals or file pickers.
 */
export class WebmcpToolHost<
  TCtx = { signal: AbortSignal },
> extends EventTarget {
  readonly mode: 'webmcp' | 'fallback';
  readonly running = new Set<string>();
  externalCalls = 0;
  readonly diagnostics: WebmcpDiagnostics = {
    schemaType: '',
    argsForm: null,
    firstError: '',
    dropped: [],
    conflicts: [],
  };

  private readonly mc: ModelContextLike | null;
  private readonly defs = new Map<string, WebmcpToolDefinition<TCtx>>();
  private readonly registrations = new Map<string, AbortController>();
  private readonly makeContext: (signal: AbortSignal) => TCtx;
  private readonly pendingOwn = new Map<string, { caller: WebmcpCaller }[]>();
  private readonly inFlight = new Map<
    string,
    Promise<WebmcpToolExecutionOutput>
  >();

  constructor(
    makeContext: (signal: AbortSignal) => TCtx,
    mc: ModelContextLike | null = nativeModelContext(),
  ) {
    super();
    this.mc = mc;
    this.mode = mc ? 'webmcp' : 'fallback';
    this.makeContext = makeContext;
    mc?.addEventListener('toolchange', () =>
      this.dispatchEvent(new Event('change')),
    );
  }

  async register(defs: readonly WebmcpToolDefinition<TCtx>[]): Promise<void> {
    for (const def of defs) {
      if (this.registrations.has(def.name)) continue;
      const ac = new AbortController();
      this.defs.set(def.name, def);
      this.registrations.set(def.name, ac);
      if (this.mc) {
        try {
          await this.mc.registerTool(
            {
              name: def.name,
              description: def.description,
              inputSchema: def.inputSchema,
              annotations: annotationsFor(def),
              execute: async (input, options) => {
                const out = await this.run(
                  def,
                  input === undefined || input === null
                    ? {}
                    : (asObject(input) ?? (input as Record<string, unknown>)),
                  options?.signal ?? new AbortController().signal,
                  this.pendingOwn.get(def.name)?.shift()?.caller ?? 'external',
                );
                return out.result;
              },
            },
            { signal: ac.signal },
          );
          this.diagnostics.conflicts = this.diagnostics.conflicts.filter(
            (c) => !c.startsWith(`${def.name}:`),
          );
        } catch (err) {
          this.registrations.delete(def.name);
          this.defs.delete(def.name);
          const why =
            err instanceof Error ? err.message || err.name : String(err);
          this.diagnostics.conflicts.push(`${def.name}: ${why}`);
          console.error(`registerTool(${def.name}) failed`, err);
        }
      }
    }
    if (!this.mc || this.diagnostics.conflicts.length > 0) {
      this.dispatchEvent(new Event('change'));
    }
  }

  unregister(names: readonly string[]): void {
    for (const name of names) {
      this.registrations.get(name)?.abort();
      this.registrations.delete(name);
      this.defs.delete(name);
    }
    if (!this.mc) this.dispatchEvent(new Event('change'));
  }

  isRegistered(name: string): boolean {
    return this.registrations.has(name);
  }

  async list(): Promise<WebmcpToolInfo[]> {
    if (this.mc) {
      const currentWindow = typeof window !== 'undefined' ? window : undefined;
      const tools = (await this.mc.getTools()).filter(
        (t) => !t.window || t.window === currentWindow,
      );
      if (tools.length) {
        this.diagnostics.schemaType = typeof tools[0].inputSchema;
      }
      const out: WebmcpToolInfo[] = [];
      this.diagnostics.dropped = [];
      for (const t of tools) {
        const info: WebmcpToolInfo = {
          name: t.name,
          description: t.description,
        };
        if (t.inputSchema !== undefined && t.inputSchema !== '') {
          const schema = asObject(t.inputSchema);
          if (!schema) {
            this.diagnostics.dropped.push(`${t.name}: unparseable inputSchema`);
            continue;
          }
          info.inputSchema = schema;
        }
        if (!this.isOurs(t, info.inputSchema)) {
          this.diagnostics.dropped.push(
            `${t.name}: not registered by this app${this.defs.has(t.name) ? ' (description or schema differs)' : ''}`,
          );
          continue;
        }
        out.push(info);
      }
      return out;
    }
    return [...this.defs.values()]
      .map((d) => ({
        name: d.name,
        description: d.description,
        inputSchema: d.inputSchema,
      }))
      .sort((a, b) => a.name.localeCompare(b.name));
  }

  async call(
    name: string,
    args: Record<string, unknown>,
    signal: AbortSignal,
    caller: Exclude<WebmcpCaller, 'external'> = 'app',
  ): Promise<WebmcpToolResult> {
    const out = await this.callWithOutput(name, args, signal, caller);
    return out.result;
  }

  async callWithOutput(
    name: string,
    args: Record<string, unknown>,
    signal: AbortSignal,
    caller: Exclude<WebmcpCaller, 'external'> = 'app',
  ): Promise<WebmcpToolExecutionOutput> {
    const token = { caller };
    try {
      if (this.mc) {
        const currentWindow =
          typeof window !== 'undefined' ? window : undefined;
        const tool = (await this.mc.getTools()).find(
          (t) => t.name === name && (!t.window || t.window === currentWindow),
        );
        if (!tool) {
          return {
            result: { error: `Tool ${name} is not available right now.` },
          };
        }
        const schema =
          tool.inputSchema === undefined || tool.inputSchema === ''
            ? undefined
            : (asObject(tool.inputSchema) ?? undefined);
        if (!this.isOurs(tool, schema)) {
          return {
            result: {
              error: `Tool ${name} on this page was not registered by this app; refusing to run it.`,
            },
          };
        }
        const queue = this.pendingOwn.get(name) ?? [];
        queue.push(token);
        this.pendingOwn.set(name, queue);
        const raw = await this.executeViaModelContext(tool, args, signal);
        return { result: parseToolResult(raw) };
      }
      const def = this.defs.get(name);
      if (!def) {
        return {
          result: { error: `Tool ${name} is not available right now.` },
        };
      }
      return await this.run(def, args, signal, caller);
    } catch (err) {
      if (signal.aborted) return { result: { error: 'cancelled' } };
      return {
        result: {
          error: `Tool failed: ${(err as Error).message || String(err)}`,
        },
      };
    } finally {
      const queue = this.pendingOwn.get(name);
      const i = queue?.indexOf(token) ?? -1;
      if (queue && i >= 0) queue.splice(i, 1);
    }
  }

  private isOurs(
    t: WebmcpRegisteredTool,
    schema: Record<string, unknown> | undefined,
  ): boolean {
    const def = this.defs.get(t.name);
    return (
      !!def &&
      def.description === t.description &&
      canonicalJSON(def.inputSchema ?? null) === canonicalJSON(schema ?? null)
    );
  }

  private async executeViaModelContext(
    tool: WebmcpRegisteredTool,
    args: Record<string, unknown>,
    signal: AbortSignal,
  ): Promise<string | null> {
    const mc = this.mc!;
    const d = this.diagnostics;
    const first =
      d.argsForm ??
      (typeof tool.inputSchema === 'string' ? 'string' : 'object');
    const invoke = (form: 'object' | 'string') =>
      mc.executeTool(tool, form === 'string' ? JSON.stringify(args) : args, {
        signal,
      });
    try {
      const r = await invoke(first);
      d.argsForm = first;
      return r;
    } catch (err) {
      const msg = (err as Error)?.message || String(err);
      if (d.argsForm !== null || signal.aborted || !PARSE_ERROR.test(msg)) {
        throw err;
      }
      d.firstError = `${first}: ${msg}`;
      const other = first === 'string' ? 'object' : 'string';
      const r = await invoke(other);
      d.argsForm = other;
      return r;
    }
  }

  private async run(
    def: WebmcpToolDefinition<TCtx>,
    args: Record<string, unknown>,
    signal: AbortSignal,
    caller: WebmcpCaller,
  ): Promise<WebmcpToolExecutionOutput> {
    const isObj =
      typeof args === 'object' && args !== null && !Array.isArray(args);
    const coalesceKey =
      isObj && def.coalesceInFlight
        ? `${def.name}:${canonicalJSON(args)}`
        : null;
    if (coalesceKey) {
      const existing = this.inFlight.get(coalesceKey);
      if (existing) {
        return existing;
      }
    }

    const execPromise = this.runSingle(def, args, signal, caller);
    if (coalesceKey) {
      this.inFlight.set(coalesceKey, execPromise);
      execPromise.finally(() => {
        if (this.inFlight.get(coalesceKey) === execPromise) {
          this.inFlight.delete(coalesceKey);
        }
      });
    }
    return execPromise;
  }

  private async runSingle(
    def: WebmcpToolDefinition<TCtx>,
    args: Record<string, unknown>,
    signal: AbortSignal,
    caller: WebmcpCaller,
  ): Promise<WebmcpToolExecutionOutput> {
    this.running.add(def.name);
    this.dispatchEvent(new Event('running'));
    if (caller === 'external') this.externalCalls++;
    const started = performance.now();
    let result: WebmcpToolResult;
    let imageDataUrl: string | undefined;
    try {
      if (typeof args !== 'object' || args === null || Array.isArray(args)) {
        throw new WebmcpToolError('Arguments must be a JSON object.');
      }
      const out = await def.execute(args, this.makeContext(signal));
      if (signal.aborted) {
        result = { error: 'cancelled' };
      } else {
        result = out.result;
        imageDataUrl = out.imageDataUrl;
      }
    } catch (err) {
      if (signal.aborted) result = { error: 'cancelled' };
      else if (err instanceof WebmcpToolError) result = { error: err.message };
      else {
        console.error(`tool ${def.name}`, err);
        result = {
          error: `Internal error in ${def.name}: ${(err as Error).message}`,
        };
      }
    } finally {
      this.running.delete(def.name);
      this.dispatchEvent(new Event('running'));
    }
    this.dispatchEvent(
      new WebmcpCallEvent(
        caller,
        def.name,
        args,
        result,
        Math.round(performance.now() - started),
        imageDataUrl,
      ),
    );
    return { result, imageDataUrl };
  }
}

function parseToolResult(json: unknown): WebmcpToolResult {
  if (json === null || json === undefined || json === '') return {};
  if (typeof json === 'object') {
    return Array.isArray(json) ? { result: json } : (json as WebmcpToolResult);
  }
  if (typeof json !== 'string') return { result: json };
  try {
    const v = JSON.parse(json) as unknown;
    return v && typeof v === 'object' && !Array.isArray(v)
      ? (v as WebmcpToolResult)
      : { result: v };
  } catch {
    return { result: json };
  }
}
