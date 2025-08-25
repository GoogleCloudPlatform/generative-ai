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

export function getTimelineContent() {
    return `
        <div id="timeline-content">
            <section id="timeline">
                <div class="bg-white dark:bg-gray-800 rounded-2xl shadow-xl p-6 md:p-8">
                    <h3 class="text-xl font-bold text-gray-800 dark:text-gray-200 mb-4">Timeline Prompting</h3>
                    <p class="text-gray-600 dark:text-gray-400 mb-6">Define what happens at specific moments in your 8-second video. The AI will enhance your descriptions into a cinematic timeline.</p>
                    
                    <div class="mb-6">
                        <label class="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">8-Second Timeline</label>
                        <div id="timeline-visualizer" class="w-full h-8 bg-gray-200 dark:bg-gray-700 rounded-lg flex overflow-hidden border border-gray-300 dark:border-gray-600"></div>
                    </div>

                    <div id="timeline-segments-container" class="space-y-4"></div>

                    <div class="mt-4">
                        <button id="add-timeline-segment-btn" class="w-full flex items-center justify-center bg-gray-200 dark:bg-gray-600 text-gray-800 dark:text-gray-200 py-2 px-4 rounded-lg font-semibold hover:bg-gray-300 dark:hover:bg-gray-500">
                            <svg xmlns="http://www.w3.org/2000/svg" class="h-5 w-5 mr-2" viewBox="0 0 20 20" fill="currentColor"><path fill-rule="evenodd" d="M10 5a1 1 0 011 1v3h3a1 1 0 110 2h-3v3a1 1 0 11-2 0v-3H6a1 1 0 110-2h3V6a1 1 0 011-1z" clip-rule="evenodd" /></svg>
                            Add Segment
                        </button>
                    </div>

                    <div class="mt-8 border-t border-gray-200 dark:border-gray-700 pt-6">
                        <button id="generate-timeline-prompt-btn" class="w-full flex items-center justify-center bg-indigo-600 text-white py-3 px-4 rounded-lg font-bold hover:bg-indigo-700">
                            Generate Final Prompt with AI
                        </button>
                    </div>

                    <div id="timeline-output-container" class="mt-6 p-4 bg-gray-50 dark:bg-gray-700 rounded-lg border border-gray-200 dark:border-gray-600 hidden">
                        <div class="flex justify-between items-center mb-2">
                            <h4 class="font-semibold text-indigo-700 dark:text-indigo-400">AI-Generated Timeline Prompt:</h4>
                            <button onclick="window.copyToClipboard('timeline-output')" class="p-1 text-gray-500 dark:text-gray-400 hover:text-indigo-600 dark:hover:text-indigo-400 rounded-md" title="Copy Prompt">
                                <svg xmlns="http://www.w3.org/2000/svg" class="h-5 w-5" fill="none" viewBox="0 0 24 24" stroke="currentColor"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M8 16H6a2 2 0 01-2-2V6a2 2 0 012-2h8a2 2 0 012 2v2m-6 12h8a2 2 0 002-2v-8a2 2 0 00-2-2h-8a2 2 0 00-2 2v8a2 2 0 002 2z" /></svg>
                            </button>
                        </div>
                        <pre><code id="timeline-output" class="text-sm text-gray-800 dark:text-gray-300 bg-white dark:bg-gray-800 p-3 rounded-md block whitespace-pre-wrap border border-gray-200 dark:border-gray-600"></code></pre>
                    </div>
                </div>
            </section>
        </div>
    `;
}

// --- INITIALIZATION AND LOGIC ---

export function initTimeline() {
    window.copyToClipboard = copyToClipboard;
    let segmentIdCounter = 0;

    const addSegmentBtn = document.getElementById('add-timeline-segment-btn');
    const segmentsContainer = document.getElementById('timeline-segments-container');
    const generateBtn = document.getElementById('generate-timeline-prompt-btn');

    const updateTimelineVisualizer = () => {
        const visualizer = document.getElementById('timeline-visualizer');
        visualizer.innerHTML = '';
        const segments = Array.from(document.querySelectorAll('.timeline-segment'));
        let totalDuration = 0;

        segments.forEach(segment => {
            const start = parseFloat(segment.querySelector('.segment-start').value);
            const end = parseFloat(segment.querySelector('.segment-end').value);
            const duration = isNaN(end) || isNaN(start) || end <= start ? 0 : end - start;
            totalDuration += duration;
            
            const color = segment.dataset.color;
            const width = (duration / 8) * 100;

            if (width > 0) {
                const bar = document.createElement('div');
                bar.className = `h-full ${color}`;
                bar.style.width = `${width}%`;
                bar.title = `${start.toFixed(1)}s - ${end.toFixed(1)}s`;
                visualizer.appendChild(bar);
            }
        });

        if (totalDuration < 8) {
            const remainingWidth = ((8 - totalDuration) / 8) * 100;
            const emptyBar = document.createElement('div');
            emptyBar.className = 'h-full bg-gray-200 dark:bg-gray-700';
            emptyBar.style.width = `${remainingWidth}%`;
            visualizer.appendChild(emptyBar);
        }
    };

    const addTimelineSegment = () => {
        segmentIdCounter++;
        const segmentDiv = document.createElement('div');
        segmentDiv.className = 'timeline-segment bg-gray-50 dark:bg-gray-700 p-4 rounded-lg border border-gray-200 dark:border-gray-600';
        
        const colors = ['bg-red-400', 'bg-blue-400', 'bg-green-400', 'bg-yellow-400', 'bg-purple-400', 'bg-pink-400', 'bg-teal-400', 'bg-orange-400'];
        segmentDiv.dataset.color = colors[segmentIdCounter % colors.length];

        segmentDiv.innerHTML = `
            <div class="flex justify-between items-center mb-3">
                <h5 class="font-semibold text-gray-800 dark:text-gray-200">Segment ${segmentIdCounter}</h5>
                <button class="remove-segment-btn text-red-500 dark:text-red-400 hover:text-red-700 dark:hover:text-red-300 font-bold">&times; Remove</button>
            </div>
            <div class="grid grid-cols-1 md:grid-cols-5 gap-4">
                <div class="md:col-span-1">
                    <label class="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">Start (s)</label>
                    <input type="number" min="0" max="8" step="0.1" class="segment-start w-full p-2 border border-gray-300 dark:border-gray-600 rounded-md bg-white dark:bg-gray-800 text-gray-900 dark:text-gray-100" value="0.0">
                </div>
                <div class="md:col-span-1">
                    <label class="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">End (s)</label>
                    <input type="number" min="0" max="8" step="0.1" class="segment-end w-full p-2 border border-gray-300 dark:border-gray-600 rounded-md bg-white dark:bg-gray-800 text-gray-900 dark:text-gray-100" value="1.0">
                </div>
                <div class="md:col-span-3">
                    <label class="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">Prompt for this segment</label>
                    <textarea rows="2" class="segment-prompt w-full p-2 border border-gray-300 dark:border-gray-600 rounded-md bg-white dark:bg-gray-800 text-gray-900 dark:text-gray-100" placeholder="e.g., A cat appears on screen, a soft meow is heard"></textarea>
                </div>
            </div>
        `;
        segmentsContainer.appendChild(segmentDiv);
        
        segmentDiv.querySelector('.remove-segment-btn').addEventListener('click', () => {
            segmentDiv.remove();
            updateTimelineVisualizer();
        });

        segmentDiv.querySelectorAll('input, textarea').forEach(el => {
            el.addEventListener('change', updateTimelineVisualizer);
            el.addEventListener('input', updateTimelineVisualizer);
        });

        updateTimelineVisualizer();
    };

    const generateTimelinePrompt = async () => {
        const segments = Array.from(document.querySelectorAll('.timeline-segment'));
        const segmentData = [];
        let totalDuration = 0;

        for (const segment of segments) {
            const start = parseFloat(segment.querySelector('.segment-start').value);
            const end = parseFloat(segment.querySelector('.segment-end').value);
            const promptText = segment.querySelector('.segment-prompt').value;

            if (isNaN(start) || isNaN(end) || end <= start || !promptText.trim()) continue;
            
            totalDuration += (end - start);
            segmentData.push({
                timestamp: `${start.toFixed(2)}s-${end.toFixed(2)}s`,
                prompt: promptText
            });
        }

        if (segmentData.length === 0) {
            showToast('Please add at least one valid timeline segment.', 'error');
            return;
        }
        if (totalDuration > 8) {
            showToast(`Total duration exceeds 8 seconds (${totalDuration.toFixed(1)}s). Please adjust segments.`, 'error');
            return;
        }

        const outputContainer = document.getElementById('timeline-output-container');
        const outputElement = document.getElementById('timeline-output');
        const originalButtonHtml = generateBtn.innerHTML;

        generateBtn.disabled = true;
        generateBtn.innerHTML = 'Generating...';
        outputContainer.classList.remove('hidden');
        outputElement.textContent = 'Asking AI to create a cinematic timeline...';
        
        try {
            const systemPrompt = `You are an expert video prompt engineer. Your task is to take a series of timeline segments with simple descriptions and enhance them into a cinematic, ready-to-use prompt.

For each segment, you will output the timestamp on one line, followed by a single, detailed paragraph on the next line. This paragraph should cinematically describe the scene. If the user's input mentions sound, incorporate it naturally into the description. If not, describe only the visuals.

Example Input:
[
  {"timestamp":"0.00s-2.00s","prompt":"a cat appears, meow"},
  {"timestamp":"2.00s-5.00s","prompt":"it runs away"}
]

Example Output:
timestamp: "00:00-00:02"
A sleek black cat suddenly appears in a soft pool of light, looking directly at the camera. A gentle meow is heard.

timestamp: "00:02-00:05"
The cat darts quickly out of frame, its tail disappearing into the shadows.

Now, process the following user input and generate the final timeline prompt. Output ONLY the timeline.
User Input:
${JSON.stringify(segmentData, null, 2)}`;

            const result = await callGeminiApi(systemPrompt);
            outputElement.textContent = result;
            showToast('Timeline prompt generated successfully!', 'success');
        } catch (error) {
            console.error('Timeline generation error:', error);
            showToast(`Generation failed: ${error.message}`, 'error');
            outputElement.textContent = `Error: ${error.message}`;
        } finally {
            generateBtn.disabled = false;
            generateBtn.innerHTML = originalButtonHtml;
        }
    };

    // --- Attach Event Listeners ---
    addSegmentBtn.addEventListener('click', addTimelineSegment);
    generateBtn.addEventListener('click', generateTimelinePrompt);

    // Add the first segment by default
    addTimelineSegment();
}