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

import { SettingsController } from './controllers/settings-controller';
import { setTheme } from './theme/tokens';
import { LitElement, html } from 'lit';
import { customElement, state } from 'lit/decorators.js';
import './avatar-setup';
import './avatar-session';
import './live-setup';
import './live-session';
import './app-settings';
import './components/ui/ga-toast-region';
import { renderIcon } from './components/ui/icons';
import type { AvatarConfigEvent, LiveConfigEvent } from './domain/presets';
import { SOURCE_REPO_URL } from './domain/links';

type AppView =
  | 'avatar-setup'
  | 'avatar-session'
  | 'live-setup'
  | 'live-session'
  | 'settings';

@customElement('my-element')
export class MyElement extends LitElement {
  @state()
  private avatarConfig: AvatarConfigEvent | null = null;

  @state()
  private liveConfig: LiveConfigEvent | null = null;

  @state()
  private activeView: AppView = this.resolveInitialView();

  // Applies the saved colour theme now and whenever Settings change it.
  private readonly settings = new SettingsController(this, (next) =>
    setTheme(next.theme),
  );

  private readonly onPopState = () => {
    this.avatarConfig = null;
    this.liveConfig = null;
    this.activeView = this.resolveInitialView();
  };

  override connectedCallback(): void {
    super.connectedCallback();
    setTheme(this.settings.value.theme);
    window.addEventListener('popstate', this.onPopState);
  }

  override disconnectedCallback(): void {
    window.removeEventListener('popstate', this.onPopState);
    super.disconnectedCallback();
  }

  // Disable Shadow DOM so Tailwind classes cascade down the component tree
  protected override createRenderRoot() {
    return this;
  }

  private resolveInitialView(): AppView {
    const path = window.location.pathname.toLowerCase();
    if (path.startsWith('/live')) {
      return 'live-setup';
    }
    if (path.startsWith('/settings')) {
      return 'settings';
    }
    return 'avatar-setup';
  }

  private navigateTo(view: 'avatar-setup' | 'live-setup' | 'settings') {
    this.avatarConfig = null;
    this.liveConfig = null;
    this.activeView = view;
    const targetPath =
      view === 'live-setup' ? '/live' : view === 'settings' ? '/settings' : '/';
    if (window.location.pathname !== targetPath) {
      window.history.pushState(null, '', targetPath);
    }
  }

  private renderBrandHeader(compact = false) {
    return html`
      <div class="flex items-center gap-3 ${compact ? '' : 'mb-10'}">
        <div
          class="w-8 h-8 rounded-full bg-surface-container-lowest flex items-center justify-center text-primary-text font-bold"
        >
          G
        </div>
        <h1
          class="${compact ? 'text-lg' : 'text-xl'} font-bold text-on-nav"
        >
          Gemini Live Studio
        </h1>
      </div>
    `;
  }

  protected override render() {
    const isAvatarMode =
      this.activeView === 'avatar-setup' ||
      this.activeView === 'avatar-session';
    const isLiveMode =
      this.activeView === 'live-setup' || this.activeView === 'live-session';

    return html`
      <div class="min-h-screen bg-surface text-on-surface font-sans flex">
        <!-- Sidebar Navigation -->
        <aside
          class="w-64 bg-nav border-r border-on-nav/20 flex flex-col p-6 hidden md:flex text-on-nav"
        >
          ${this.renderBrandHeader(false)}

          <nav aria-label="Main navigation" class="flex flex-col gap-2">
            <button
              type="button"
              aria-current="${isAvatarMode ? 'page' : 'false'}"
              @click="${() => this.navigateTo('avatar-setup')}"
              class="text-left px-4 py-3 rounded-xl transition-colors flex items-center gap-3 ${
                isAvatarMode
                  ? 'bg-on-nav/20 font-semibold'
                  : 'hover:bg-on-nav/10'
              }"
            >
              ${renderIcon('video-cam', 'w-5 h-5')}
              <span>Avatar Studio</span>
            </button>

            <button
              type="button"
              aria-current="${isLiveMode ? 'page' : 'false'}"
              @click="${() => this.navigateTo('live-setup')}"
              class="text-left px-4 py-3 rounded-xl transition-colors flex items-center gap-3 ${
                isLiveMode ? 'bg-on-nav/20 font-semibold' : 'hover:bg-on-nav/10'
              }"
            >
              ${renderIcon('mic', 'w-5 h-5')}
              <span>Live Audio</span>
            </button>

            <button
              type="button"
              aria-current="${
                this.activeView === 'settings' ? 'page' : 'false'
              }"
              @click="${() => this.navigateTo('settings')}"
              class="text-left px-4 py-3 rounded-xl transition-colors flex items-center gap-3 ${
                this.activeView === 'settings'
                  ? 'bg-on-nav/20 font-semibold'
                  : 'hover:bg-on-nav/10'
              }"
            >
              ${renderIcon('bolt', 'w-5 h-5')}
              <span>Settings</span>
            </button>
          </nav>

          <div
            class="mt-auto pt-6 border-t border-on-nav/20 flex flex-col gap-3"
          >
            <a
              href="${SOURCE_REPO_URL}"
              target="_blank"
              rel="noopener noreferrer"
              class="inline-flex items-center gap-1.5 text-sm text-on-nav hover:underline focus:outline-none focus-visible:ring-2 focus-visible:ring-on-nav rounded"
            >
              ${renderIcon('external-link', 'w-4 h-4 shrink-0')}
              <span>View source on GitHub</span>
              <span class="sr-only">(opens in a new tab)</span>
            </a>
            <p class="text-xs text-on-nav/70">Powered by Google Cloud</p>
          </div>
        </aside>

        <!-- Main Content Area -->
        <main
          class="flex-1 flex flex-col h-screen overflow-hidden bg-surface"
        >
          <!-- Mobile Header -->
          <header
            class="md:hidden bg-nav p-4 flex items-center justify-between text-on-nav shadow-md z-10"
          >
            ${this.renderBrandHeader(true)}
            <div class="flex items-center gap-1 text-xs font-semibold">
              <button
                type="button"
                @click="${() => this.navigateTo('avatar-setup')}"
                class="px-2.5 py-1.5 rounded-lg ${
                  isAvatarMode ? 'bg-on-nav/20' : 'hover:bg-on-nav/10'
                }"
              >
                Avatar
              </button>
              <button
                type="button"
                @click="${() => this.navigateTo('live-setup')}"
                class="px-2.5 py-1.5 rounded-lg ${
                  isLiveMode ? 'bg-on-nav/20' : 'hover:bg-on-nav/10'
                }"
              >
                Live
              </button>
              <button
                type="button"
                @click="${() => this.navigateTo('settings')}"
                class="px-2.5 py-1.5 rounded-lg ${
                  this.activeView === 'settings'
                    ? 'bg-on-nav/20'
                    : 'hover:bg-on-nav/10'
                }"
              >
                Settings
              </button>
              <a
                href="${SOURCE_REPO_URL}"
                target="_blank"
                rel="noopener noreferrer"
                aria-label="View source on GitHub (opens in a new tab)"
                title="View source on GitHub"
                class="p-1.5 rounded-lg hover:bg-on-nav/10 focus:outline-none focus-visible:ring-2 focus-visible:ring-on-nav"
              >
                ${renderIcon('external-link', 'w-4 h-4 shrink-0')}
              </a>
            </div>
          </header>

          <div
            class="flex-1 overflow-y-auto p-4 md:p-8 lg:p-12 flex flex-col"
          >
            <div class="max-w-5xl mx-auto w-full flex-1 flex flex-col min-h-0">
              ${
                this.activeView === 'settings'
                  ? html`<app-settings></app-settings>`
                  : this.activeView === 'live-setup'
                    ? html`<live-setup
                      @connect="${(e: CustomEvent<LiveConfigEvent>) => {
                        this.liveConfig = e.detail;
                        this.activeView = 'live-session';
                      }}"
                    ></live-setup>`
                    : this.activeView === 'live-session' && this.liveConfig
                      ? html`<live-session
                        .config="${this.liveConfig}"
                        @disconnect="${() => {
                          this.liveConfig = null;
                          this.activeView = 'live-setup';
                        }}"
                        class="flex-1 flex flex-col min-h-0"
                      ></live-session>`
                      : this.activeView === 'avatar-session' &&
                          this.avatarConfig
                        ? html`<avatar-session
                          .config="${this.avatarConfig}"
                          @disconnect="${() => {
                            this.avatarConfig = null;
                            this.activeView = 'avatar-setup';
                          }}"
                          class="flex-1 flex flex-col min-h-0"
                        ></avatar-session>`
                        : html`<avatar-setup
                          @connect="${(e: CustomEvent<AvatarConfigEvent>) => {
                            this.avatarConfig = e.detail;
                            this.activeView = 'avatar-session';
                          }}"
                        ></avatar-setup>`
              }
            </div>
          </div>
        </main>

        <ga-toast-region></ga-toast-region>
      </div>
    `;
  }
}

declare global {
  interface HTMLElementTagNameMap {
    'my-element': MyElement;
  }
}
