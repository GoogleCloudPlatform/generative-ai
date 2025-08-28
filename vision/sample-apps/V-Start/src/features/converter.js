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

// This function now fetches the HTML from an external file.
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
