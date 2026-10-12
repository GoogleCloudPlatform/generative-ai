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

/**
 * Visual & Page-Level Accessibility Check (`npm run visual` / `make visual-check`)
 *
 * - Builds the frontend bundle (unless `--no-build` is passed).
 * - Serves `dist/` with SPA fallback and a deterministic `/api/config` stub.
 * - Opens headless Chromium (honours `CHROMIUM_PATH`) with `reducedMotion: 'reduce'`.
 * - Visits `/`, `/live`, `/settings` across `desktop` (1280x900) and `mobile` (390x844)
 *   in both `light` and `dark` themes, plus stubbed-WebSocket session views (`/session-avatar`,
 *   `/session-live`).
 * - Runs `axe-core` (WCAG 2.x A/AA) on every view/theme/viewport.
 * - Saves PNG screenshots to `--out <dir>` (default `/tmp/gemini-live-studio-visual`) and
 *   optionally pixel-diffs against `--baseline <dir>`.
 */

import { execFileSync } from 'node:child_process';
import { existsSync, mkdirSync, readFileSync, writeFileSync } from 'node:fs';
import {
  createServer,
  type IncomingMessage,
  type ServerResponse,
} from 'node:http';
import type { AddressInfo } from 'node:net';
import { extname, join, resolve } from 'node:path';
import { fileURLToPath } from 'node:url';
import { chromium, type Browser, type Page } from 'playwright';

const FRONTEND_DIR = fileURLToPath(new URL('..', import.meta.url));
const DIST_DIR = join(FRONTEND_DIR, 'dist');
const AXE_PATH = join(FRONTEND_DIR, 'node_modules/axe-core/axe.min.js');

const KNOWN_CONTRAST_EXCEPTIONS = [
  '.bg-primary',
  '.bg-primary *',
  '.bg-nav',
  '.bg-nav *',
  '.bg-success.text-on-success',
];

// 1x1 solid slate PNG for deterministic offline preset thumbnails.
const STUB_PNG = Buffer.from(
  'iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mNk+M9QDwADhgGAWjR9awAAAABJRU5ErkJggg==',
  'base64',
);

const MIME_BY_EXT: Record<string, string> = {
  '.html': 'text/html; charset=utf-8',
  '.js': 'text/javascript; charset=utf-8',
  '.css': 'text/css; charset=utf-8',
  '.svg': 'image/svg+xml',
  '.png': 'image/png',
  '.ttf': 'font/ttf',
  '.json': 'application/json; charset=utf-8',
};

interface CliOptions {
  build: boolean;
  outDir: string;
  baselineDir: string | null;
}

function parseArgs(argv: string[]): CliOptions {
  let build = true;
  let outDir = '/tmp/gemini-live-studio-visual';
  let baselineDir: string | null = null;

  for (let i = 0; i < argv.length; i++) {
    const arg = argv[i];
    if (arg === '--no-build') {
      build = false;
    } else if (arg === '--out' && argv[i + 1]) {
      outDir = resolve(argv[++i]);
    } else if (arg === '--baseline' && argv[i + 1]) {
      baselineDir = resolve(argv[++i]);
    }
  }
  return { build, outDir, baselineDir };
}

function startDistServer(
  distDir: string,
): Promise<{ url: string; close: () => Promise<void> }> {
  return new Promise((resolvePromise) => {
    const server = createServer((req: IncomingMessage, res: ServerResponse) => {
      const reqUrl = new URL(req.url ?? '/', 'http://127.0.0.1');
      if (reqUrl.pathname === '/api/config') {
        res.writeHead(200, { 'Content-Type': 'application/json' });
        res.end(
          JSON.stringify({
            liveModel: 'gemini-3.8-live',
            liveLocation: 'us-central1',
            imageModel: 'gemini-nano-banana-2.1',
            imageLocation: 'global',
            availableLiveModels: ['gemini-3.8-live'],
            availableLocations: ['us-central1', 'global'],
            availableImageModels: [
              'gemini-nano-banana-2.1',
              'gemini-3.1-flash-image',
              'gemini-3-pro-image',
              'gemini-3.1-flash-lite-image',
            ],
          }),
        );
        return;
      }

      const trimmed = reqUrl.pathname.replace(/^\/+|\/+$/g, '');
      const isSpaRoute =
        trimmed === '' ||
        trimmed === 'live' ||
        trimmed === 'avatar' ||
        trimmed === 'settings';
      const filePath = isSpaRoute
        ? join(distDir, 'index.html')
        : join(distDir, trimmed);

      if (!existsSync(filePath)) {
        res.writeHead(404);
        res.end('Not found');
        return;
      }
      const ext = extname(filePath);
      res.writeHead(200, {
        'Content-Type': MIME_BY_EXT[ext] ?? 'application/octet-stream',
      });
      res.end(readFileSync(filePath));
    });

    server.listen(0, '127.0.0.1', () => {
      const addr = server.address() as AddressInfo;
      resolvePromise({
        url: `http://127.0.0.1:${addr.port}`,
        close: () => new Promise((r) => server.close(() => r())),
      });
    });
  });
}

async function runAxeCheck(page: Page, label: string): Promise<void> {
  await page.addScriptTag({ path: AXE_PATH });
  const violations = await page.evaluate((exceptions: string[]) => {
    type AxeRun = (
      context: Document,
      options: Record<string, unknown>,
    ) => Promise<{
      violations: Array<{
        id: string;
        impact?: string;
        help: string;
        nodes: Array<{ target: Array<string | string[]> }>;
      }>;
    }>;
    const axeGlobal = (window as unknown as { axe: { run: AxeRun } }).axe;
    return axeGlobal
      .run(document, {
        runOnly: {
          type: 'tag',
          values: ['wcag2a', 'wcag2aa', 'wcag21a', 'wcag21aa'],
        },
      })
      .then((res) =>
        res.violations
          .map((v) =>
            v.id === 'color-contrast'
              ? {
                  ...v,
                  nodes: v.nodes.filter(
                    (n) =>
                      !exceptions.some((sel) =>
                        document
                          .querySelector(String(n.target[0]))
                          ?.matches(sel),
                      ),
                  ),
                }
              : v,
          )
          .filter((v) => v.nodes.length > 0),
      );
  }, KNOWN_CONTRAST_EXCEPTIONS);

  if (violations.length > 0) {
    const details = violations
      .map(
        (v) =>
          `  - ${v.id} (${v.impact ?? 'unknown'}): ${v.help}\n    ${v.nodes.map((n) => n.target.join(' ')).join('\n    ')}`,
      )
      .join('\n');
    throw new Error(`axe violation(s) on ${label}:\n${details}`);
  }
}

async function diffScreenshots(
  browser: Browser,
  currentPng: Buffer,
  baselinePng: Buffer,
): Promise<{ diffPixels: number; totalPixels: number }> {
  const page = await browser.newPage();
  try {
    const curUrl = `data:image/png;base64,${currentPng.toString('base64')}`;
    const baseUrl = `data:image/png;base64,${baselinePng.toString('base64')}`;
    return await page.evaluate(
      async ({ a, b }) => {
        const load = (src: string) =>
          new Promise<HTMLImageElement>((resolveImg, rejectImg) => {
            const img = new Image();
            img.onload = () => resolveImg(img);
            img.onerror = rejectImg;
            img.src = src;
          });
        const [imgA, imgB] = await Promise.all([load(a), load(b)]);
        const w = Math.max(imgA.width, imgB.width);
        const h = Math.max(imgA.height, imgB.height);
        const canvasA = document.createElement('canvas');
        const canvasB = document.createElement('canvas');
        canvasA.width = canvasB.width = w;
        canvasA.height = canvasB.height = h;
        const ctxA = canvasA.getContext('2d')!;
        const ctxB = canvasB.getContext('2d')!;
        ctxA.drawImage(imgA, 0, 0);
        ctxB.drawImage(imgB, 0, 0);
        const dataA = ctxA.getImageData(0, 0, w, h).data;
        const dataB = ctxB.getImageData(0, 0, w, h).data;
        let diffPixels = 0;
        for (let i = 0; i < dataA.length; i += 4) {
          if (
            dataA[i] !== dataB[i] ||
            dataA[i + 1] !== dataB[i + 1] ||
            dataA[i + 2] !== dataB[i + 2] ||
            dataA[i + 3] !== dataB[i + 3]
          ) {
            diffPixels++;
          }
        }
        return { diffPixels, totalPixels: w * h };
      },
      { a: curUrl, b: baseUrl },
    );
  } finally {
    await page.close();
  }
}

async function main(): Promise<void> {
  const opts = parseArgs(process.argv.slice(2));
  if (opts.build) {
    console.log('Building frontend...');
    execFileSync('npm', ['run', 'build'], {
      cwd: FRONTEND_DIR,
      stdio: 'inherit',
    });
  }
  mkdirSync(opts.outDir, { recursive: true });

  const server = await startDistServer(DIST_DIR);
  const browser = await chromium.launch({
    executablePath: process.env.CHROMIUM_PATH || undefined,
  });

  const viewports = [
    { name: 'desktop', width: 1280, height: 900 },
    { name: 'mobile', width: 390, height: 844 },
  ] as const;
  const themes = ['light', 'dark'] as const;
  const routes = [
    { name: 'avatar-setup', path: '/' },
    { name: 'live-setup', path: '/live' },
    { name: 'settings', path: '/settings' },
  ] as const;

  let checksRun = 0;
  try {
    for (const theme of themes) {
      for (const vp of viewports) {
        const context = await browser.newContext({
          viewport: { width: vp.width, height: vp.height },
          reducedMotion: 'reduce',
        });
        await context.route('https://www.gstatic.com/**', (route) =>
          route.fulfill({
            status: 200,
            contentType: 'image/png',
            body: STUB_PNG,
          }),
        );
        await context.addInitScript((t: string) => {
          localStorage.setItem(
            'gemini_avatar_settings',
            JSON.stringify({ theme: t }),
          );
        }, theme);

        const page = await context.newPage();
        for (const route of routes) {
          const label = `${route.name}-${theme}-${vp.name}`;
          await page.goto(`${server.url}${route.path}`, {
            waitUntil: 'networkidle',
          });
          await page.evaluate(() => document.fonts.ready);
          await runAxeCheck(page, label);

          const shotPath = join(opts.outDir, `${label}.png`);
          const png = await page.screenshot({ fullPage: true });
          writeFileSync(shotPath, png);
          checksRun++;

          if (opts.baselineDir) {
            const baseFile = join(opts.baselineDir, `${label}.png`);
            if (existsSync(baseFile)) {
              const { diffPixels, totalPixels } = await diffScreenshots(
                browser,
                png,
                readFileSync(baseFile),
              );
              const pct = ((diffPixels / totalPixels) * 100).toFixed(3);
              console.log(`  [diff] ${label}: ${diffPixels} px (${pct}%)`);
            }
          }
        }
        await context.close();
      }

      // Stubbed-WebSocket session checks (avatar-session and live-session)
      const sessionContext = await browser.newContext({
        viewport: { width: 1280, height: 900 },
        reducedMotion: 'reduce',
      });
      await sessionContext.route('https://www.gstatic.com/**', (route) =>
        route.fulfill({
          status: 200,
          contentType: 'image/png',
          body: STUB_PNG,
        }),
      );
      await sessionContext.addInitScript((t: string) => {
        localStorage.setItem(
          'gemini_avatar_settings',
          JSON.stringify({ theme: t }),
        );
        class StubWebSocket extends EventTarget {
          static readonly CONNECTING = 0;
          static readonly OPEN = 1;
          static readonly CLOSING = 2;
          static readonly CLOSED = 3;
          readonly CONNECTING = 0;
          readonly OPEN = 1;
          readonly CLOSING = 2;
          readonly CLOSED = 3;
          readyState = 1;
          binaryType = 'arraybuffer';
          onopen: ((ev: Event) => void) | null = null;
          onmessage: ((ev: MessageEvent) => void) | null = null;
          onclose: ((ev: CloseEvent) => void) | null = null;
          onerror: ((ev: Event) => void) | null = null;
          constructor(url: string) {
            super();
            setTimeout(() => {
              const openEv = new Event('open');
              this.onopen?.(openEv);
              this.dispatchEvent(openEv);
              const emit = (payload: Record<string, unknown>) => {
                const msgEv = new MessageEvent('message', {
                  data: JSON.stringify(payload),
                });
                this.onmessage?.(msgEv);
                this.dispatchEvent(msgEv);
              };
              emit({
                type: 'session_info',
                mode: url.includes('/ws/live') ? 'audio' : 'avatar',
                model: 'gemini-3.8-live',
                location: 'us-central1',
              });
              emit({
                type: 'output_transcript',
                text: 'Hello! How can I help you today?',
                finished: true,
              });
            }, 10);
          }
          send(): void {}
          close(): void {
            this.readyState = 3;
          }
        }
        (window as unknown as { WebSocket: unknown }).WebSocket = StubWebSocket;
      }, theme);

      const sessionPage = await sessionContext.newPage();
      for (const sessionRoute of [
        { name: 'avatar-session', path: '/', buttonText: 'Connect to Avatar' },
        {
          name: 'live-session',
          path: '/live',
          buttonText: 'Start Live Session',
        },
      ]) {
        const label = `${sessionRoute.name}-${theme}-desktop`;
        await sessionPage.goto(`${server.url}${sessionRoute.path}`, {
          waitUntil: 'networkidle',
        });
        await sessionPage
          .getByRole('button', { name: sessionRoute.buttonText })
          .click();
        await sessionPage.waitForTimeout(60);
        await runAxeCheck(sessionPage, label);
        const png = await sessionPage.screenshot({ fullPage: true });
        writeFileSync(join(opts.outDir, `${label}.png`), png);
        checksRun++;
      }
      await sessionContext.close();
    }

    console.log(
      `✓ Visual & axe check passed (${checksRun} views/themes/viewports audited, screenshots in ${opts.outDir})`,
    );
  } finally {
    await browser.close();
    await server.close();
  }
}

main().catch((err) => {
  console.error(err);
  process.exit(1);
});
