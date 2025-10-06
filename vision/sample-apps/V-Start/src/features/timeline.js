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

export async function getTimelineContent() {
    try {
        const response = await fetch('/src/features/templates/timeline.html');
        if (!response.ok) {
            throw new Error(`Network response was not ok: ${response.statusText}`);
        }
        return await response.text();
    } catch (error) {
        console.error('Failed to fetch timeline template:', error);
        return '<div>Error loading content. Please check the console for details.</div>';
    }
}

// --- INITIALIZATION AND LOGIC ---

export function initTimeline() {
    window.copyToClipboard = copyToClipboard;
    let segmentIdCounter = 0;

    const addSegmentBtn = document.getElementById('add-timeline-segment-btn');
    const segmentsContainer = document.getElementById('timeline-segments-container');
    const generateBtn = document.getElementById('generate-timeline-prompt-btn');
    const clearBtn = document.getElementById('clear-timeline-btn');

    const updateTimelineVisualizer = () => {
        const visualizer = document.getElementById('timeline-visualizer');
        if (!visualizer) return;
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

    const clearAll = () => {
        segmentsContainer.innerHTML = '';
        segmentIdCounter = 0;
        addTimelineSegment(); // Add back one default segment
        document.getElementById('timeline-output-container').classList.add('hidden');
        showToast('Timeline cleared!', 'info');
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
        generateBtn.innerHTML = `
            <svg class="animate-spin -ml-1 mr-3 h-5 w-5 text-white" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24">
              <circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4"></circle>
              <path class="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
            </svg>
            Generating...
        `;
        outputContainer.classList.remove('hidden');
        outputElement.textContent = 'Creating a cinematic timeline...';
        
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
    clearBtn.addEventListener('click', clearAll);

    // Add the first segment by default
    addTimelineSegment();
}

