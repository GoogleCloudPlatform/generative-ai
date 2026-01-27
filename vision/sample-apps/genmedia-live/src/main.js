/*
 * Copyright 2026 Google LLC
 *
 * Licensed under the Apache License, Version 2.0 (the "License");
 * you may not use this file except in compliance with the License.
 * You may obtain a copy of the License at
 *
 * https://www.apache.org/licenses/LICENSE-2.0
 *
 * Unless required by applicable law or agreed to in writing, software
 * distributed under the License is distributed on an "AS IS" BASIS,
 * WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
 * See the License for the specific language governing permissions and
 * limitations under the License.
 */

import { getGenMediaContent, initGenMediaChat } from './features/genmedia-chat.js';
import { showToast } from './ui.js';

function initDarkMode() {
    const themeToggleBtn = document.getElementById('theme-toggle');
    const lightIcon = document.getElementById('theme-toggle-light-icon');
    const darkIcon = document.getElementById('theme-toggle-dark-icon');

    if (!themeToggleBtn || !lightIcon || !darkIcon) return;

    const savedTheme = localStorage.getItem('theme') || 'light';
    applyTheme(savedTheme);

    function applyTheme(theme) {
        const html = document.documentElement;
        if (theme === 'dark') {
            html.classList.add('dark');
            lightIcon.style.display = 'block';
            darkIcon.style.display = 'none';
        } else {
            html.classList.remove('dark');
            lightIcon.style.display = 'none';
            darkIcon.style.display = 'block';
        }
    }

    themeToggleBtn.addEventListener('click', () => {
        const isDark = document.documentElement.classList.contains('dark');
        const newTheme = isDark ? 'light' : 'dark';
        applyTheme(newTheme);
        localStorage.setItem('theme', newTheme);
        showToast(`Switched to ${newTheme} mode`, 'info', 2000);
    });

    setTimeout(() => {
        document.body.classList.add('transition-colors', 'duration-300');
    }, 100);
}

async function initApp() {
    try {
        initDarkMode();

        const mainContent = document.getElementById('main-content');
        if (!mainContent) {
            throw new Error('Main content container not found');
        }

        const chatContent = await getGenMediaContent();
        mainContent.innerHTML = chatContent;
        mainContent.classList.add('fade-in');
        setTimeout(() => mainContent.classList.remove('fade-in'), 500);

        initGenMediaChat();

        setTimeout(() => {
            const theme = document.documentElement.classList.contains('dark') ? 'dark' : 'light';
            showToast(`Welcome to GenMedia Live! (${theme} mode)`, 'success', 3000);
        }, 500);

    } catch (error) {
        console.error('Init failed:', error);
        showToast('Failed to load. Please refresh.', 'error');
    }
}

function initKeyboardShortcuts() {
    document.addEventListener('keydown', (e) => {
        if ((e.ctrlKey || e.metaKey) && e.shiftKey && e.key === 'D') {
            e.preventDefault();
            document.getElementById('theme-toggle')?.click();
        }
    });
}

document.addEventListener('visibilitychange', () => {
    if (!document.hidden) {
        const savedTheme = localStorage.getItem('theme');
        if (savedTheme) {
            const html = document.documentElement;
            const isDark = html.classList.contains('dark');
            if (savedTheme === 'dark' && !isDark) {
                html.classList.add('dark');
            } else if (savedTheme === 'light' && isDark) {
                html.classList.remove('dark');
            }
        }
    }
});

if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', () => {
        initApp();
        initKeyboardShortcuts();
    });
} else {
    initApp();
    initKeyboardShortcuts();
}

window.GenMediaLive = { version: '1.0.0', name: 'GenMedia Live' };
export { initApp };
