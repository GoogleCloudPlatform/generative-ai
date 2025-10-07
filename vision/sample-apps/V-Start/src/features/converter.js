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

import { callGeminiApi } from '../api.js';
import { showToast, copyToClipboard } from '../ui.js';

export async function getConverterContent() {
    try {
        const response = await fetch('/src/features/templates/converter.html');
        if (!response.ok) {
            throw new Error(`Network response was not ok: ${response.statusText}`);
        }
        return await response.text();
    } catch (error) {
        console.error('Failed to fetch converter template:', error);
        return '<div>Error loading content. Please check the console for details.</div>';
    }
}

export function initConverter() {
    window.copyToClipboard = copyToClipboard;

    const convertBtn = document.getElementById('convert-format-btn');
    const clearBtn = document.getElementById('clear-converter-btn');
    const converterInput = document.getElementById('converter-input');
    const formatSelect = document.getElementById('format-select');
    const outputContainer = document.getElementById('converter-output-container');
    const outputElement = document.getElementById('converter-output');

    const clearAll = () => {
        converterInput.value = '';
        outputElement.textContent = '';
        outputContainer.style.display = 'none';
        formatSelect.selectedIndex = 0;
        showToast('Converter form cleared!', 'info');
    };

    convertBtn.addEventListener('click', async () => {
        const inputText = converterInput.value;
        const targetFormat = formatSelect.value;

        if (!inputText.trim()) {
            showToast('Please enter a prompt to convert.', 'error');
            return;
        }

        const systemPrompt = `You are a data format converter. Convert the following text into the ${targetFormat} format. Provide only the converted text as a raw string, without any additional explanation or markdown code fences (e.g., \`\`\`json). Text to convert:\n\n${inputText}`;

        const originalButtonHtml = convertBtn.innerHTML;
        convertBtn.disabled = true;
        convertBtn.innerHTML = `
            <svg class="animate-spin -ml-1 mr-3 h-5 w-5 text-white" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24">
              <circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4"></circle>
              <path class="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
            </svg>
            Converting...
        `;
        outputContainer.style.display = 'block';
        outputElement.textContent = `Converting to ${targetFormat}...`;

        try {
            const convertedText = await callGeminiApi(systemPrompt);
            outputElement.textContent = convertedText;
            showToast('Format converted successfully!', 'success');
        } catch (error) {
            console.error('Conversion error:', error);
            outputElement.textContent = `Error: ${error.message}`;
            showToast('Failed to convert the format.', 'error');
        } finally {
            convertBtn.disabled = false;
            convertBtn.innerHTML = originalButtonHtml;
        }
    });

    clearBtn.addEventListener('click', clearAll);
}

