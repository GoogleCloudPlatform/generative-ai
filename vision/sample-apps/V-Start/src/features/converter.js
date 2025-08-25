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
import { showToast } from '../ui.js';

export function getConverterContent() {
    return `
        <div id="converter-content">
            <section id="converter">
                <div class="bg-white dark:bg-gray-800 rounded-2xl shadow-xl p-6 md:p-8">
                    <h3 class="text-xl font-bold text-gray-800 dark:text-gray-200 mb-4">Prompt Format Converter</h3>
                    <p class="text-gray-600 dark:text-gray-400 mb-4">Convert a prompt between plain text, JSON, YAML, or XML.</p>
                    <div class="grid grid-cols-1 md:grid-cols-5 gap-4">
                        <div class="md:col-span-4">
                            <label for="converter-input" class="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">Input Prompt (any format)</label>
                            <textarea id="converter-input" rows="6" class="w-full p-2 border border-gray-300 dark:border-gray-600 rounded-md shadow-sm focus:ring-indigo-500 focus:border-indigo-500 bg-white dark:bg-gray-700 text-gray-900 dark:text-gray-100" placeholder="Paste your prompt here... e.g., plain text, JSON, XML, or YAML"></textarea>
                        </div>
                        <div>
                            <label for="format-select" class="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">Convert To</label>
                            <select id="format-select" class="w-full p-2 border border-gray-300 dark:border-gray-600 rounded-md shadow-sm focus:ring-indigo-500 focus:border-indigo-500 bg-white dark:bg-gray-700 text-gray-900 dark:text-gray-100">
                                <option>JSON</option>
                                <option>YAML</option>
                                <option>XML</option>
                                <option>Plain Text</option>
                            </select>
                        </div>
                    </div>
                    <div class="mt-6">
                        <button id="convert-format-btn" class="w-full flex items-center justify-center bg-teal-600 text-white py-3 px-4 rounded-lg font-bold hover:bg-teal-700 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-teal-500 disabled:bg-teal-400 transition-all">
                            <svg xmlns="http://www.w3.org/2000/svg" class="h-6 w-6 mr-2" viewBox="0 0 20 20" fill="currentColor"><path fill-rule="evenodd" d="M15.28 4.72a.75.75 0 010 1.06l-4.25 4.25a.75.75 0 000 1.06l4.25 4.25a.75.75 0 11-1.06 1.06l-4.25-4.25a2.25 2.25 0 010-3.18l4.25-4.25a.75.75 0 011.06 0zm-8.56 0a.75.75 0 011.06 0l4.25 4.25a2.25 2.25 0 010 3.18l-4.25 4.25a.75.75 0 11-1.06-1.06l4.25-4.25a.75.75 0 000-1.06L4.72 5.78a.75.75 0 010-1.06z" clip-rule="evenodd" /></svg>
                            Convert Format
                        </button>
                    </div>
                    <div id="converter-output-container" class="mt-6 p-4 bg-gray-900 dark:bg-gray-950 text-white dark:text-gray-100 rounded-lg border border-gray-700 dark:border-gray-600" style="display: none;">
                        <div class="flex justify-between items-center mb-2">
                            <h4 class="font-semibold text-teal-300 dark:text-teal-400">Converted Output:</h4>
                            <button onclick="copyToClipboard('converter-output')" class="p-1 text-gray-300 dark:text-gray-400 hover:text-teal-300 dark:hover:text-teal-400 rounded-md" title="Copy Output">
                                <svg xmlns="http://www.w3.org/2000/svg" class="h-5 w-5" fill="none" viewBox="0 0 24 24" stroke="currentColor"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M8 16H6a2 2 0 01-2-2V6a2 2 0 012-2h8a2 2 0 012 2v2m-6 12h8a2 2 0 002-2v-8a2 2 0 00-2-2h-8a2 2 0 00-2 2v8a2 2 0 002 2z" /></svg>
                            </button>
                        </div>
                        <pre><code id="converter-output" class="text-sm text-gray-100 dark:text-gray-200"></code></pre>
                    </div>
                </div>
            </section>
        </div>
    `;
}

export function initConverter() {
    // Make copyToClipboard available globally for onclick
    window.copyToClipboard = (elementId) => {
        const element = document.getElementById(elementId);
        if (element) {
            navigator.clipboard.writeText(element.textContent).then(() => {
                showToast('Copied to clipboard!', 'success');
            }).catch(err => {
                console.error('Failed to copy:', err);
                showToast('Failed to copy to clipboard', 'error');
            });
        }
    };

    // --- Get references to the UI elements ---
    const convertBtn = document.getElementById('convert-format-btn');
    const converterInput = document.getElementById('converter-input');
    const formatSelect = document.getElementById('format-select');
    const outputContainer = document.getElementById('converter-output-container');
    const outputElement = document.getElementById('converter-output');

    // --- Add the click event listener to the button ---
    convertBtn.addEventListener('click', async () => {
        const inputText = converterInput.value;
        const targetFormat = formatSelect.value;

        // 1. Validate the input
        if (!inputText.trim()) {
            showToast('Please enter a prompt to convert.', 'error');
            return;
        }

        // 2. Define the system prompt for the API call
        const systemPrompt = `You are a data format converter. Convert the following text into the ${targetFormat} format. Provide only the converted text as a raw string, without any additional explanation or markdown code fences (e.g., \`\`\`json). Text to convert:\n\n${inputText}`;

        // 3. Handle UI loading state
        const originalButtonHtml = convertBtn.innerHTML;
        convertBtn.disabled = true;
        convertBtn.innerHTML = 'Converting...';
        outputContainer.style.display = 'block';
        outputElement.textContent = `Converting to ${targetFormat}...`;

        // 4. Call the API and handle the response
        try {
            const convertedText = await callGeminiApi(systemPrompt);
            // Using textContent is safer here to prevent HTML injection
            outputElement.textContent = convertedText;
            showToast('Format converted successfully!', 'success');
        } catch (error) {
            console.error('Conversion error:', error);
            outputElement.textContent = `Error: ${error.message}`;
            showToast('Failed to convert the format.', 'error');
        } finally {
            // 5. Reset the button state
            convertBtn.disabled = false;
            convertBtn.innerHTML = originalButtonHtml;
        }
    });
}