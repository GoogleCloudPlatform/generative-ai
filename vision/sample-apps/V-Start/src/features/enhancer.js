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

// This function now fetches the HTML from an external file.
export async function getEnhancerContent() {
    try {
        const response = await fetch('/src/features/templates/enhancer.html');
        if (!response.ok) {
            throw new Error(`Network response was not ok: ${response.statusText}`);
        }
        return await response.text();
    } catch (error) {
        console.error('Failed to fetch enhancer template:', error);
        return '<div>Error loading content. Please check the console for details.</div>';
    }
}

// --- INITIALIZATION AND LOGIC ---

export function initEnhancer() {
    window.copyToClipboard = copyToClipboard;

    const enhanceBtn = document.getElementById('enhance-prompt-btn');
    const enhancerInput = document.getElementById('enhancer-input');
    const outputContainer = document.getElementById('enhancer-output-container');
    const outputElement = document.getElementById('enhancer-output');

    enhanceBtn.addEventListener('click', async () => {
        const originalPrompt = enhancerInput.value;

        if (!originalPrompt.trim()) {
            showToast('Please enter a prompt to enhance.', 'error');
            return;
        }

        const systemPrompt = `You are a world-class video director and an expert prompt engineer for Google's Veo model. Your task is to significantly enhance and improve the following prompt. Make it more cinematic, detailed, descriptive, and effective for an AI video generation model. Add specific details about camera work, lighting, mood, and visual style. Here is the prompt to improve: "${originalPrompt}"

Output ONLY the final, enhanced prompt string, without any introduction, explanation, or quotation marks.`;

        const originalButtonHtml = enhanceBtn.innerHTML;
        enhanceBtn.disabled = true;
        enhanceBtn.innerHTML = 'Enhancing...';
        outputContainer.classList.remove('hidden');
        outputElement.textContent = 'Generating a more cinematic version...';

        try {
            const enhancedPrompt = await callGeminiApi(systemPrompt);
            outputElement.textContent = enhancedPrompt;
            showToast('Prompt enhanced successfully!', 'success');
        } catch (error) {
            console.error('Enhancement error:', error);
            outputElement.textContent = `Error: ${error.message}`;
            showToast('Failed to enhance the prompt.', 'error');
        } finally {
            enhanceBtn.disabled = false;
            enhanceBtn.innerHTML = originalButtonHtml;
        }
    });
}
