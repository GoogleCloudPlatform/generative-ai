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

// --- HTML TEMPLATE ---

export function getEnhancerContent() {
    return `
        <div id="enhancer-content">
            <section id="enhancer">
                <div class="bg-white dark:bg-gray-800 rounded-2xl shadow-xl p-6 md:p-8">
                    <h3 class="text-xl font-bold text-gray-800 dark:text-gray-200 mb-4">Prompt Enhancer</h3>
                    <p class="text-gray-600 dark:text-gray-400 mb-4">Paste your existing prompt below and let Gemini make it more cinematic and descriptive.</p>
                    <div>
                        <label for="enhancer-input" class="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">Your Prompt</label>
                        <textarea id="enhancer-input" rows="4" class="w-full p-2 border border-gray-300 dark:border-gray-600 rounded-md shadow-sm focus:ring-indigo-500 focus:border-indigo-500 bg-white dark:bg-gray-700 text-gray-900 dark:text-gray-100" placeholder="e.g., A cat sitting on a couch."></textarea>
                    </div>
                    <div class="mt-6">
                        <button id="enhance-prompt-btn" class="w-full flex items-center justify-center bg-purple-600 text-white py-3 px-4 rounded-lg font-bold hover:bg-purple-700 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-purple-500 disabled:bg-purple-400 transition-all">
                            <svg xmlns="http://www.w3.org/2000/svg" class="h-6 w-6 mr-2" viewBox="0 0 20 20" fill="currentColor"><path fill-rule="evenodd" d="M5 2a1 1 0 011 1v1h1a1 1 0 010 2H6v1a1 1 0 01-2 0V6H3a1 1 0 010-2h1V3a1 1 0 011-1zm0 10a1 1 0 011 1v1h1a1 1 0 110 2H6v1a1 1 0 11-2 0v-1H3a1 1 0 110-2h1v-1a1 1 0 011-1zM12 2a1 1 0 01.967.744L14.146 7.2 17.5 9.134a1 1 0 010 1.732l-3.354 1.935-1.18 4.455a1 1 0 01-1.933 0L9.854 12.8l-3.354-1.935a1 1 0 010-1.732L10.146 7.2A1 1 0 0112 2z" clip-rule="evenodd" /></svg>
                            Enhance Prompt
                        </button>
                    </div>
                    <div id="enhancer-output-container" class="mt-6 p-4 bg-gray-50 dark:bg-gray-700 rounded-lg border border-gray-200 dark:border-gray-600 hidden">
                        <div class="flex justify-between items-center mb-2">
                            <h4 class="font-semibold text-purple-700 dark:text-purple-400">Enhanced Prompt:</h4>
                            <button onclick="window.copyToClipboard('enhancer-output')" class="p-1 text-gray-500 dark:text-gray-400 hover:text-purple-600 dark:hover:text-purple-400 rounded-md" title="Copy Enhanced Prompt">
                                <svg xmlns="http://www.w3.org/2000/svg" class="h-5 w-5" fill="none" viewBox="0 0 24 24" stroke="currentColor"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M8 16H6a2 2 0 01-2-2V6a2 2 0 012-2h8a2 2 0 012 2v2m-6 12h8a2 2 0 002-2v-8a2 2 0 00-2-2h-8a2 2 0 00-2 2v8a2 2 0 002 2z" /></svg>
                            </button>
                        </div>
                        <p id="enhancer-output" class="text-gray-700 dark:text-gray-300 bg-white dark:bg-gray-800 p-3 rounded-md whitespace-pre-wrap border border-gray-200 dark:border-gray-600"></p>
                    </div>
                </div>
            </section>
        </div>
    `;
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

        // --- THIS IS THE FIX ---
        // This prompt is much stricter and tells the AI exactly what to output.
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