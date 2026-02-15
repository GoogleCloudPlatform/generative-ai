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

export function showToast(message, type = 'success', duration = 3000) {
    let toast = document.getElementById('notification-toast');
    if (!toast) {
        toast = document.createElement('div');
        toast.id = 'notification-toast';
        document.body.appendChild(toast);
    }

    clearTimeout(toast.hideTimer);
    toast.textContent = message;

    const baseClasses = 'fixed bottom-20 left-1/2 transform -translate-x-1/2 px-6 py-3 rounded-full font-semibold text-sm shadow-lg transition-all duration-300 z-50';
    const typeClasses = {
        success: 'bg-green-500 text-white',
        error: 'bg-red-500 text-white',
        warning: 'bg-yellow-500 text-white',
        info: 'bg-blue-500 text-white'
    };

    toast.className = `${baseClasses} ${typeClasses[type] || typeClasses.info} opacity-100 translate-y-0`;

    toast.hideTimer = setTimeout(() => {
        toast.className = `${baseClasses} ${typeClasses[type] || typeClasses.info} opacity-0 translate-y-2`;
    }, duration);
}

export async function copyToClipboard(elementId) {
    const element = document.getElementById(elementId);
    if (!element || !navigator.clipboard) {
        showToast('Clipboard not available', 'error');
        return;
    }

    try {
        await navigator.clipboard.writeText(element.innerText);
        showToast('Copied to clipboard!', 'success');
    } catch (err) {
        console.error('Copy failed:', err);
        showToast('Failed to copy', 'error');
    }
}
