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

let alignmentResults = [];
let loadedPairs = [];
let loadedPrompts = [];
let loadedVideos = [];

// --- HELPER FUNCTIONS ---

function extractJSON(text) {
    try {
        const match = text.match(/\{[\s\S]*\}/);
        if (match) return JSON.parse(match[0]);
    } catch (e) { /* Fallback */ }
    throw new Error('Failed to parse valid JSON from the API response.');
}

function getScoreColor(score) {
    if (score >= 80) return { 
        bg: 'bg-green-100 dark:bg-green-900', 
        text: 'text-green-800 dark:text-green-200', 
        border: 'border-green-500 dark:border-green-400', 
        label: 'Excellent'
    };
    if (score >= 60) return { 
        bg: 'bg-blue-100 dark:bg-blue-900', 
        text: 'text-blue-800 dark:text-blue-200', 
        border: 'border-blue-500 dark:border-blue-400', 
        label: 'Good'
    };
    if (score >= 40) return { 
        bg: 'bg-yellow-100 dark:bg-yellow-900', 
        text: 'text-yellow-800 dark:text-yellow-200', 
        border: 'border-yellow-500 dark:border-yellow-400', 
        label: 'Fair'
    };
    return { 
        bg: 'bg-red-100 dark:bg-red-900', 
        text: 'text-red-800 dark:text-red-200', 
        border: 'border-red-500 dark:border-red-400', 
        label: 'Poor'
    };
}

function parsePromptsFromCSV(textContent) {
    return textContent
        .split(/\r?\n/)
        .map(line => line.trim())
        .filter(line => line.length > 0);
}

async function getVideoAsBase64(videoSource) {
    let blob;
    if (videoSource instanceof File) {
        blob = videoSource;
    } else if (typeof videoSource === 'string') {
        const response = await fetch('/api/proxy-video?url=' + encodeURIComponent(videoSource));
        if (!response.ok) {
            const errorData = await response.json();
            throw new Error(errorData.error || 'Failed to fetch video via proxy: ' + response.statusText);
        }
        blob = await response.blob();
    } else {
        throw new Error('Invalid video source provided.');
    }

    return new Promise((resolve, reject) => {
        const reader = new FileReader();
        reader.onload = () => resolve({
            base64Data: reader.result.split(',')[1],
            mimeType: blob.type
        });
        reader.onerror = reject;
        reader.readAsDataURL(blob);
    });
}

// --- DRAG AND DROP FUNCTIONS ---

function initDragAndDrop(listId, itemsArray, updateCallback) {
    const list = document.getElementById(listId);
    if (!list) return;
    
    let draggedElement = null;
    
    list.addEventListener('dragstart', (e) => {
        if (e.target.draggable) {
            draggedElement = e.target;
            e.target.style.opacity = '0.5';
            e.dataTransfer.effectAllowed = 'move';
        }
    });
    
    list.addEventListener('dragend', (e) => {
        if (e.target.draggable) {
            e.target.style.opacity = '';
        }
    });
    
    list.addEventListener('dragover', (e) => {
        e.preventDefault();
        e.dataTransfer.dropEffect = 'move';
        
        const afterElement = getDragAfterElement(list, e.clientY);
        if (afterElement == null) {
            list.appendChild(draggedElement);
        } else {
            list.insertBefore(draggedElement, afterElement);
        }
    });
    
    list.addEventListener('drop', (e) => {
        e.preventDefault();
        
        // Get the new order
        const items = [...list.querySelectorAll('[draggable="true"]')];
        const newOrder = items.map(item => parseInt(item.dataset.index));
        
        // Reorder the array
        const reorderedItems = newOrder.map(oldIndex => itemsArray[oldIndex]);
        
        // Update the original array
        itemsArray.length = 0;
        itemsArray.push(...reorderedItems);
        
        // Re-render
        updateCallback();
        
        showToast('Items reordered successfully!', 'success');
    });
}

function getDragAfterElement(container, y) {
    const draggableElements = [...container.querySelectorAll('[draggable="true"]:not([style*="opacity"])')];
    
    return draggableElements.reduce((closest, child) => {
        const box = child.getBoundingClientRect();
        const offset = y - box.top - box.height / 2;
        
        if (offset < 0 && offset > closest.offset) {
            return { offset: offset, element: child };
        } else {
            return closest;
        }
    }, { offset: Number.NEGATIVE_INFINITY }).element;
}

// --- HTML TEMPLATE LOADER ---

export async function getAlignmentEvalContent() {
    try {
        const response = await fetch('/src/features/templates/alignment-eval.html');
        if (!response.ok) {
            throw new Error('Network response was not ok: ' + response.statusText);
        }
        return await response.text();
    } catch (error) {
        console.error('Failed to fetch alignment-eval template:', error);
        return '<div>Error loading content. Please check the console for details.</div>';
    }
}

// --- INITIALIZATION AND LOGIC ---

function renderPromptsList() {
    const promptsList = document.getElementById('prompts-list');
    promptsList.innerHTML = '';
    
    loadedPrompts.forEach((prompt, index) => {
        const promptDiv = document.createElement('div');
        promptDiv.className = 'flex items-center gap-2 p-2 bg-gray-100 dark:bg-gray-700 rounded cursor-move hover:shadow-md transition-all duration-200 border border-transparent hover:border-gray-300 dark:hover:border-gray-600';
        promptDiv.draggable = true;
        promptDiv.dataset.index = index;
        
        const dragIcon = '<svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M4 6h16M4 12h16M4 18h16"></path></svg>';
        
        promptDiv.innerHTML = '<div class="text-gray-400 dark:text-gray-500 flex-shrink-0">' + dragIcon + '</div>' +
            '<div class="font-bold text-gray-500 dark:text-gray-400 flex-shrink-0">' + (index + 1) + '.</div>' +
            '<div class="flex-1 text-sm text-gray-800 dark:text-gray-200 truncate" title="' + prompt + '">' + prompt + '</div>';
        
        promptsList.appendChild(promptDiv);
    });
    
    initDragAndDrop('prompts-list', loadedPrompts, renderPromptsList);
}

function renderVideosList() {
    const videosList = document.getElementById('videos-list');
    videosList.innerHTML = '';
    
    loadedVideos.forEach((video, index) => {
        const videoName = (video.source instanceof File) ? video.source.name : video.source.split('/').pop();
        const videoDiv = document.createElement('div');
        videoDiv.className = 'flex items-center gap-2 p-2 bg-gray-100 dark:bg-gray-700 rounded cursor-move hover:shadow-md transition-all duration-200 border border-transparent hover:border-gray-300 dark:hover:border-gray-600';
        videoDiv.draggable = true;
        videoDiv.dataset.index = index;
        
        const dragIcon = '<svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M4 6h16M4 12h16M4 18h16"></path></svg>';
        
        videoDiv.innerHTML = '<div class="text-gray-400 dark:text-gray-500 flex-shrink-0">' + dragIcon + '</div>' +
            '<div class="font-bold text-gray-500 dark:text-gray-400 flex-shrink-0">' + (index + 1) + '.</div>' +
            '<div class="flex-1 text-sm text-gray-800 dark:text-gray-200 truncate" title="' + videoName + '">' + videoName + '</div>';
        
        videosList.appendChild(videoDiv);
    });
    
    initDragAndDrop('videos-list', loadedVideos, renderVideosList);
}

function renderFinalPairs() {
    const pairsContainer = document.getElementById('alignment-pairs-container');
    pairsContainer.innerHTML = '';
}

export function initAlignmentEval() {
    alignmentResults = [];
    loadedPairs = [];
    loadedPrompts = [];
    loadedVideos = [];

    const loadAndPairBtn = document.getElementById('load-and-pair-btn');
    const clearAllBtn = document.getElementById('clear-all-btn');
    const startEvalBtn = document.getElementById('start-alignment-eval-btn');
    const downloadBtn = document.getElementById('download-alignment-results-btn');
    const reorderSection = document.getElementById('reorder-section');
    const evalActionsContainer = document.getElementById('eval-actions-container');

    // STEP 1: Load inputs and automatically create pairs
    const loadAndCreatePairs = async () => {
        const csvInput = document.getElementById('prompts-csv-input');
        const textInput = document.getElementById('prompts-text-input');
        const videosFileInput = document.getElementById('batch-videos-input');
        const videosUrlInput = document.getElementById('videos-url-input');
        
        // Load prompts
        loadedPrompts = [];
        if (csvInput.files.length > 0) {
            loadedPrompts = parsePromptsFromCSV(await csvInput.files[0].text());
        } else if (textInput.value.trim()) {
            loadedPrompts = textInput.value.split(';').map(p => p.trim()).filter(p => p);
        }
        
        // Load videos
        loadedVideos = [];
        if (videosFileInput.files.length > 0) {
            const files = Array.from(videosFileInput.files);
            loadedVideos = files.map(file => ({ source: file }));
        } else if (videosUrlInput.value.trim()) {
            const urls = videosUrlInput.value.split(/\r?\n/).map(url => url.trim()).filter(url => url);
            loadedVideos = urls.map(url => ({ source: url }));
        }

        // Validation
        if (loadedPrompts.length === 0) {
            showToast('Please provide prompts either via CSV file or text input.', 'error');
            return;
        }
        
        if (loadedVideos.length === 0) {
            showToast('Please provide videos either via file upload or URL input.', 'error');
            return;
        }
        
        if (loadedPrompts.length !== loadedVideos.length) {
            showToast('Mismatch: ' + loadedPrompts.length + ' prompts and ' + loadedVideos.length + ' videos. Please ensure they match.', 'error');
            return;
        }
        
        // Automatically create pairs
        loadedPairs = loadedPrompts.map((prompt, i) => {
            const video = loadedVideos[i];
            const name = (video.source instanceof File) ? video.source.name : video.source.split('/').pop();
            return { 
                id: i + 1, 
                prompt: prompt, 
                videoSource: video.source, 
                videoName: name 
            };
        });
        
        // Show reordering only if more than 1 pair
        if (loadedPairs.length > 1) {
            renderPromptsList();
            renderVideosList();
            reorderSection.classList.remove('hidden');
            showToast('Created ' + loadedPairs.length + ' pairs. Drag to reorder if needed, then click "Start Evaluation".', 'success');
        } else {
            reorderSection.classList.add('hidden');
            showToast('Created ' + loadedPairs.length + ' pair. Ready for evaluation!', 'success');
        }
        
        renderFinalPairs();
        evalActionsContainer.classList.remove('hidden');
        
        // Update pairs when reordering (only if more than 1 pair)
        if (loadedPairs.length > 1) {
            const updatePairsFromReorder = () => {
                loadedPairs = loadedPrompts.map((prompt, i) => {
                    const video = loadedVideos[i];
                    const name = (video.source instanceof File) ? video.source.name : video.source.split('/').pop();
                    return { 
                        id: i + 1, 
                        prompt: prompt, 
                        videoSource: video.source, 
                        videoName: name 
                    };
                });
                renderFinalPairs();
            };
            
            // Re-initialize drag and drop with the update callback
            initDragAndDrop('prompts-list', loadedPrompts, () => {
                renderPromptsList();
                updatePairsFromReorder();
            });
            initDragAndDrop('videos-list', loadedVideos, () => {
                renderVideosList(); 
                updatePairsFromReorder();
            });
        }
    };

    const clearAll = () => {
        loadedPairs = [];
        loadedPrompts = [];
        loadedVideos = [];
        alignmentResults = [];
        
        document.getElementById('alignment-pairs-container').innerHTML = '';
        document.getElementById('prompts-list').innerHTML = '';
        document.getElementById('videos-list').innerHTML = '';
        
        reorderSection.classList.add('hidden');
        evalActionsContainer.classList.add('hidden');
        document.getElementById('alignment-results-container').classList.add('hidden');
        document.getElementById('download-alignment-results-container').classList.add('hidden');
        
        document.getElementById('prompts-csv-input').value = '';
        document.getElementById('prompts-text-input').value = '';
        document.getElementById('batch-videos-input').value = '';
        document.getElementById('videos-url-input').value = '';
        
        showToast('All data cleared.', 'info');
    };

    // STEP 2: Start evaluation
    const startAlignmentEvaluation = async () => {
        const btn = document.getElementById('start-alignment-eval-btn');
        const resultsContainer = document.getElementById('alignment-results-container');
        
        btn.disabled = true;
        btn.innerHTML = '<svg class="animate-spin -ml-1 mr-3 h-5 w-5 text-white inline" fill="none" viewBox="0 0 24 24">' +
            '<circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4"></circle>' +
            '<path class="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>' +
            '</svg>Evaluating...';
        
        resultsContainer.classList.remove('hidden');
        resultsContainer.innerHTML = '';
        document.getElementById('download-alignment-results-container').classList.add('hidden');
        alignmentResults = [];

        for (const pair of loadedPairs) {
            const resultCard = document.createElement('div');
            resultCard.className = 'bg-white dark:bg-gray-800 rounded-lg shadow-lg overflow-hidden border border-gray-200 dark:border-gray-700';
            
            const loadingHTML = '<div class="bg-gray-100 dark:bg-gray-700 text-gray-800 dark:text-gray-200 p-4 border-b border-gray-200 dark:border-gray-600">' +
                '<h3 class="font-bold text-lg">Pair #' + pair.id + ': Evaluating...</h3>' +
                '<p class="text-sm text-gray-600 dark:text-gray-400 mt-1 truncate" title="' + pair.videoName + '">' + pair.videoName + '</p>' +
                '</div>' +
                '<div class="p-6">' +
                '<div class="flex items-center justify-center">' +
                '<svg class="animate-spin h-8 w-8 text-cyan-600" fill="none" viewBox="0 0 24 24">' +
                '<circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4"></circle>' +
                '<path class="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>' +
                '</svg>' +
                '</div>' +
                '<p class="text-center text-gray-500 dark:text-gray-400 mt-3" id="progress-text-' + pair.id + '">Step 1: Preparing video data...</p>' +
                '</div>';
            
            resultCard.innerHTML = loadingHTML;
            resultsContainer.appendChild(resultCard);
            const progressText = document.getElementById('progress-text-' + pair.id);

            try {
                const videoData = await getVideoAsBase64(pair.videoSource);
                const base64Data = videoData.base64Data;
                const mimeType = videoData.mimeType;
                
                // Use camelCase to match server.js expectations
                const videoParts = [{ 
                    inlineData: { mimeType: mimeType, data: base64Data }
                }];
                
                progressText.textContent = 'Step 2: Analyzing video and generating score...';

                // Clean the prompt to avoid syntax issues
                const cleanPrompt = pair.prompt
                    .replace(/[\\`"'\n\r\t]/g, ' ')
                    .replace(/\s+/g, ' ')
                    .trim();

                // Build prompt using array join 
                const promptParts = [];
                promptParts.push('You are an expert video-to-prompt alignment auditor. Your job is to perform STRICT, CRITICAL evaluation.');
                promptParts.push('');
                promptParts.push('PROMPT TO EVALUATE: ' + cleanPrompt);
                promptParts.push('');
                promptParts.push('CRITICAL INSTRUCTION: You MUST actually watch and analyze the video content. Do not make assumptions.');
                promptParts.push('');
                promptParts.push('EVALUATION PROTOCOL:');
                promptParts.push('');
                promptParts.push('STEP 1 - FIRST DESCRIBE WHAT YOU SEE:');
                promptParts.push('Before evaluating, describe in one sentence what is actually visible in this video.');
                promptParts.push('');
                promptParts.push('STEP 2 - DECOMPOSE THE PROMPT:');
                promptParts.push('Extract EVERY verifiable element from the prompt:');
                promptParts.push('- SUBJECTS: All entities mentioned (people, animals, objects)');
                promptParts.push('- ACTIONS: All verbs and movements described');
                promptParts.push('- ATTRIBUTES: All descriptive details (colors, sizes, quantities, qualities)');
                promptParts.push('- SETTINGS: Locations, environments, time of day, weather');
                promptParts.push('- RELATIONSHIPS: Spatial arrangements, interactions between elements');
                promptParts.push('');
                promptParts.push('STEP 3 - DETERMINE QUESTION COUNT:');
                promptParts.push('Count the total distinct elements extracted above. Generate questions based on complexity:');
                promptParts.push('- 1-3 elements: Generate 3-5 questions');
                promptParts.push('- 4-6 elements: Generate 5-8 questions');
                promptParts.push('- 7-10 elements: Generate 8-12 questions');
                promptParts.push('- 11-15 elements: Generate 12-18 questions');
                promptParts.push('- 16+ elements: Generate 18-25 questions');
                promptParts.push('');
                promptParts.push('STEP 4 - IDENTIFY CORE REQUIREMENT:');
                promptParts.push('What is the SINGLE most important element that defines this video?');
                promptParts.push('');
                promptParts.push('STEP 5 - CREATE VERIFICATION QUESTIONS:');
                promptParts.push('Generate specific questions that test EXACT requirements:');
                promptParts.push('- Each question must test ONE specific claim from the prompt');
                promptParts.push('- If prompt says "red car", ask "Is the car red?" not just "Is there a car?"');
                promptParts.push('- If prompt says "jumping", ask "Is [subject] jumping?" not "Is there movement?"');
                promptParts.push('- Questions MUST have a mix of Yes and No answers based on what is actually in the video');
                promptParts.push('');
                promptParts.push('STEP 6 - EVALUATE THE VIDEO:');
                promptParts.push('For each question, look at what is ACTUALLY in the video:');
                promptParts.push('- YES: Element is clearly visible AND matches the exact requirement');
                promptParts.push('- NO: Element is absent, wrong, or does not match the requirement');
                promptParts.push('- UNCERTAIN: Only if genuinely impossible to determine');
                promptParts.push('');
                promptParts.push('CRITICAL EVALUATION RULES:');
                promptParts.push('- You MUST look at the actual video content, not guess based on the prompt');
                promptParts.push('- DEFAULT TO NO when in doubt');
                promptParts.push('- Partial matches are NO (blue car when prompt says red = NO)');
                promptParts.push('- Generic matches are NO (animal when prompt says cat = NO)');
                promptParts.push('- If the video shows something completely different from the prompt, most answers should be NO');
                promptParts.push('');
                promptParts.push('STEP 7 - CALCULATE SCORE:');
                promptParts.push('- Core element missing: Maximum 20 points');
                promptParts.push('- Core element present: Start with 100 points');
                promptParts.push('- For each NO: Deduct (80 / total_questions) points');
                promptParts.push('- For each UNCERTAIN: Deduct (40 / total_questions) points');
                promptParts.push('');
                promptParts.push('OUTPUT FORMAT - Return ONLY this JSON (no markdown):');
                promptParts.push('{');
                promptParts.push('  "core_subject": "the main subject from the prompt",');
                promptParts.push('  "core_subject_present": true or false based on actual video content,');
                promptParts.push('  "holistic_alignment_score": 0 to 100,');
                promptParts.push('  "answers": [');
                promptParts.push('    {"question": "Specific question?", "answer": "Yes/No/Uncertain"}');
                promptParts.push('  ]');
                promptParts.push('}');
                
                const systemPrompt = promptParts.join('\n');
                
                console.log('Sending evaluation request for pair #' + pair.id);
                console.log('Video data length:', base64Data ? base64Data.length : 0);
                const resultRaw = await callGeminiApi(systemPrompt, videoParts);
                console.log('Raw response for pair #' + pair.id + ':', resultRaw);
                
                const resultData = extractJSON(resultRaw);
                console.log('Parsed data for pair #' + pair.id + ':', JSON.stringify(resultData, null, 2));

                const answers = resultData.answers || [];
                const core_subject = resultData.core_subject || 'Unknown';
                const core_subject_present = resultData.core_subject_present || false;
                const holistic_alignment_score = resultData.holistic_alignment_score || 0;
                const score = holistic_alignment_score;
                
                // Validation check for evaluation quality
                if (answers && answers.length > 2) {
                    const yesCount = answers.filter(a => String(a.answer).toLowerCase() === 'yes').length;
                    const noCount = answers.filter(a => String(a.answer).toLowerCase() === 'no').length;
                    const yesPercentage = (yesCount / answers.length) * 100;
                    
                    console.log('Pair #' + pair.id + ' evaluation distribution: ' + yesCount + ' Yes, ' + noCount + ' No, ' + (answers.length - yesCount - noCount) + ' Uncertain');
                    
                    if (yesPercentage === 100 && answers.length > 3) {
                        console.warn('Warning: All answers are YES for pair #' + pair.id + ' - evaluation might be too lenient');
                    }
                }
                
                alignmentResults.push({
                    pairId: pair.id, 
                    prompt: pair.prompt, 
                    videoName: pair.videoName,
                    score: score, 
                    core_subject: core_subject, 
                    core_subject_present: core_subject_present, 
                    answers: answers
                });
                
                const colorScheme = getScoreColor(score);
                
                // Build result HTML
                let answersHTML = '';
                answers.forEach((a, idx) => {
                    const answer = String(a.answer).toLowerCase();
                    const answerColor = answer === 'yes' ? 'text-green-700 dark:text-green-400' : answer === 'no' ? 'text-red-700 dark:text-red-400' : 'text-yellow-700 dark:text-yellow-400';
                    const answerIcon = answer === 'yes' ? '[YES]' : answer === 'no' ? '[NO]' : '[?]';
                    answersHTML += '<div class="flex items-start text-sm">' +
                        '<span class="' + answerColor + ' mr-2 font-bold">' + answerIcon + '</span>' +
                        '<div class="flex-1">' +
                        '<p class="font-semibold text-gray-800 dark:text-gray-200">' + (idx + 1) + '. ' + a.question + '</p>' +
                        '<p class="' + answerColor + ' font-medium">' + a.answer + '</p>' +
                        '</div>' +
                        '</div>';
                });
                
                const yesCountFinal = answers.filter(a => String(a.answer).toLowerCase() === 'yes').length;
                
                resultCard.innerHTML = '<div class="' + colorScheme.bg + ' p-4 rounded-t-lg border-b-4 ' + colorScheme.border + '">' +
                    '<div class="flex justify-between items-start">' +
                    '<div>' +
                    '<h3 class="font-bold text-lg ' + colorScheme.text + '">Pair #' + pair.id + '</h3>' +
                    '<p class="text-sm text-gray-600 dark:text-gray-400 mt-1 truncate" title="' + pair.videoName + '">' + pair.videoName + '</p>' +
                    '</div>' +
                    '<div class="text-right flex-shrink-0 ml-4">' +
                    '<p class="text-4xl font-bold ' + colorScheme.text + '">' + score + '%</p>' +
                    '<p class="text-xs uppercase tracking-wide font-semibold ' + colorScheme.text + '">' + colorScheme.label + '</p>' +
                    '</div>' +
                    '</div>' +
                    '</div>' +
                    '<div class="p-4 bg-white dark:bg-gray-800">' +
                    '<div class="mb-3 text-sm text-gray-600 dark:text-gray-400">' +
                    '<p><strong>Prompt:</strong> "' + pair.prompt + '"</p>' +
                    '<p class="mt-2"><strong>Evaluation:</strong> ' + answers.length + ' criteria checked</p>' +
                    '</div>' +
                    '<details>' +
                    '<summary class="cursor-pointer font-semibold text-sm text-gray-600 dark:text-gray-400 hover:text-gray-900 dark:hover:text-gray-200">View Detailed Evaluation</summary>' +
                    '<div class="mt-3 space-y-3">' +
                    '<div class="flex items-start text-sm">' +
                    '<span class="' + (core_subject_present ? 'text-green-700 dark:text-green-400' : 'text-red-700 dark:text-red-400') + ' mr-2 font-bold">' + (core_subject_present ? '[YES]' : '[NO]') + '</span>' +
                    '<div class="flex-1">' +
                    '<p class="font-semibold text-gray-800 dark:text-gray-200">Core Subject: "' + core_subject + '"</p>' +
                    '<p class="' + (core_subject_present ? 'text-green-700 dark:text-green-400' : 'text-red-700 dark:text-red-400') + '">' + (core_subject_present ? 'Present in video' : 'Missing from video') + '</p>' +
                    '</div>' +
                    '</div>' +
                    answersHTML +
                    '<div class="mt-4 pt-3 border-t border-gray-200 dark:border-gray-700">' +
                    '<p class="text-xs text-gray-500 dark:text-gray-400">' +
                    'Summary: ' + yesCountFinal + '/' + answers.length + ' criteria met' +
                    (!core_subject_present ? ' (Core subject missing - score capped at 20%)' : '') +
                    '</p>' +
                    '</div>' +
                    '</div>' +
                    '</details>' +
                    '</div>';
                    
            } catch (error) {
                console.error('Error evaluating Pair #' + pair.id + ':', error);
                resultCard.innerHTML = '<div class="p-4 bg-white dark:bg-gray-800">' +
                    '<h3 class="font-bold text-lg text-red-700 dark:text-red-400 mb-2">Error evaluating Pair #' + pair.id + '</h3>' +
                    '<p class="text-red-600 dark:text-red-400 text-sm">' + error.message + '</p>' +
                    '</div>';
                showToast('Error on pair #' + pair.id + ': ' + error.message, 'error');
            }
        }
        
        if (alignmentResults.length > 0) {
            document.getElementById('download-alignment-results-container').classList.remove('hidden');
        }
        
        btn.disabled = false;
        btn.innerHTML = 'Start Evaluation';
    };

    const downloadAlignmentResults = () => {
        if (alignmentResults.length === 0) {
            showToast("No results to download.", "error");
            return;
        }

        const headers = ["Pair ID", "Prompt", "Video Name", "Overall Score", "Core Subject", "Core Subject Present", "Total Questions", "Questions Met", "Question", "Answer"];
        let csvRows = [headers.join(',')];

        alignmentResults.forEach(r => {
            const escapeCsv = (str) => '"' + String(str).replace(/"/g, '""') + '"';
            const totalQuestions = r.answers ? r.answers.length : 0;
            const questionsMet = r.answers ? r.answers.filter(a => String(a.answer).toLowerCase() === 'yes').length : 0;
            
            if (r.answers && r.answers.length > 0) {
                r.answers.forEach((answer, idx) => {
                    const row = [ 
                        r.pairId, 
                        escapeCsv(r.prompt), 
                        escapeCsv(r.videoName), 
                        r.score, 
                        escapeCsv(r.core_subject), 
                        r.core_subject_present,
                        totalQuestions,
                        questionsMet,
                        escapeCsv((idx + 1) + '. ' + answer.question), 
                        escapeCsv(answer.answer) 
                    ];
                    csvRows.push(row.join(','));
                });
            } else {
                const row = [ 
                    r.pairId, 
                    escapeCsv(r.prompt), 
                    escapeCsv(r.videoName), 
                    r.score, 
                    escapeCsv(r.core_subject), 
                    r.core_subject_present,
                    0,
                    0,
                    "N/A", 
                    "N/A" 
                ];
                csvRows.push(row.join(','));
            }
        });

        const csvContent = csvRows.join('\n');
        const blob = new Blob([csvContent], { type: 'text/csv;charset=utf-8;' });
        const link = document.createElement('a');
        link.href = URL.createObjectURL(blob);
        const dateStr = new Date().toISOString().slice(0,10);
        link.download = 'alignment_evaluation_results_' + dateStr + '.csv';
        document.body.appendChild(link);
        link.click();
        document.body.removeChild(link);
        
        showToast("Results downloaded successfully!", "success");
    };
    
    // Attach event listeners to the buttons 
    loadAndPairBtn.addEventListener('click', loadAndCreatePairs);
    clearAllBtn.addEventListener('click', clearAll);
    startEvalBtn.addEventListener('click', startAlignmentEvaluation);
    downloadBtn.addEventListener('click', downloadAlignmentResults);
}