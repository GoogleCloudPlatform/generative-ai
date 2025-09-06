/*
 * Copyright 2025 Google LLC
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

export function showToast(message, type = 'success') {
    const toast = document.getElementById('notification-toast');
    if (!toast) return;

    toast.textContent = message;
    toast.className = 'show';
    toast.classList.add(type); 

    setTimeout(() => {
        toast.classList.remove('show');
    }, 3000);
}

export async function copyToClipboard(elementId) {
    const element = document.getElementById(elementId);
    if (!element) return;

    const textToCopy = element.innerText;

    if (!navigator.clipboard) {
        showToast('Clipboard API not available.', 'error');
        return;
    }

    try {
        await navigator.clipboard.writeText(textToCopy);
        showToast('Copied to clipboard!', 'success');
    } catch (err) {
        console.error('Failed to copy text: ', err);
        showToast('Failed to copy.', 'error');
    }
}