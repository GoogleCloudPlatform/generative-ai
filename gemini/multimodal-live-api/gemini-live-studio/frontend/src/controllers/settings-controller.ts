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

import type { ReactiveController, ReactiveControllerHost } from 'lit';
import { Store, type AppSettings } from '../store';

/**
 * ReactiveController that synchronizes a LitElement with `Store` settings and
 * automatically subscribes/unsubscribes to the window `settings-updated` event.
 */
export class SettingsController implements ReactiveController {
  value: AppSettings;
  private readonly host: ReactiveControllerHost;
  private readonly onChange?: (settings: AppSettings) => void;

  constructor(
    host: ReactiveControllerHost,
    onChange?: (settings: AppSettings) => void,
  ) {
    this.host = host;
    this.onChange = onChange;
    this.value = Store.getSettings();
    host.addController(this);
  }

  private readonly handleWindowUpdate = (e: Event) => {
    const detail = (e as CustomEvent<AppSettings>).detail;
    this.value = detail ?? Store.getSettings();
    this.onChange?.(this.value);
    this.host.requestUpdate();
  };

  hostConnected(): void {
    this.value = Store.getSettings();
    globalThis.window?.addEventListener(
      'settings-updated',
      this.handleWindowUpdate,
    );
  }

  hostDisconnected(): void {
    globalThis.window?.removeEventListener(
      'settings-updated',
      this.handleWindowUpdate,
    );
  }

  save(next: AppSettings): void {
    this.value = next;
    Store.saveSettings(next);
    this.host.requestUpdate();
  }
}
