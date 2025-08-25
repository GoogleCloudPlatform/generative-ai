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

// --- DATA FOR THE FORM ---
const textVideoSelectData = {
    camera_angle: { label: "Camera Angles", options: ["Eye-Level Shot", "Low-Angle Shot", "High-Angle Shot", "Bird's-Eye View", "Top-Down Shot", "Worm's-Eye View", "Dutch Angle", "Canted Angle", "Close-Up", "Extreme Close-Up", "Medium Shot", "Full Shot", "Long Shot", "Wide Shot", "Establishing Shot", "Over-the-Shoulder Shot", "Point-of-View (POV) Shot"] },
    camera_movement: { label: "Camera Movements", options: ["Static Shot (or fixed)", "Pan (left)", "Pan (right)", "Tilt (up)", "Tilt (down)", "Dolly (In)", "Dolly (Out)", "Zoom (In)", "Zoom (Out)", "Truck (Left)", "Truck (Right)", "Pedestal (Up)", "Pedestal (Down)", "Crane Shot", "Aerial Shot", "Drone Shot", "Handheld", "Shaky Cam", "Whip Pan", "Arc Shot"] },
    lens_effect: { label: "Lens & Optical Effects", options: ["Wide-Angle Lens (e.g., 24mm)", "Telephoto Lens (e.g., 85mm)", "Shallow Depth of Field", "Bokeh", "Deep Depth of Field", "Lens Flare", "Rack Focus", "Fisheye Lens Effect", "Vertigo Effect (Dolly Zoom)"] },
    visual_style: { label: "Visual Style & Aesthetics", options: ["Photorealistic", "Cinematic", "Vintage", "Japanese anime style", "Claymation style", "Stop-motion animation", "In the style of Van Gogh", "Surrealist painting", "Monochromatic black and white", "Vibrant and saturated", "Film noir style", "High-key lighting", "Low-key lighting", "Golden hour glow", "Volumetric lighting", "Backlighting to create a silhouette"] },
    temporal_element: { label: "Temporal Elements", options: ["Slow-motion", "Fast-paced action", "Time-lapse", "Hyperlapse", "Pulsating light", "Rhythmic movement"] },
    sound_effects: { label: "Sound Effects & Ambience", options: ["Sound of a phone ringing", "Water splashing", "Soft house sounds", "Ticking clock", "City traffic and sirens", "Waves crashing", "Quiet office hum"] }
};

// --- HELPER FUNCTIONS TO BUILD THE FORM ---
function createInputComponent(id, labelText, placeholder) {
    const container = document.createElement('div');
    const label = document.createElement('label');
    label.htmlFor = id;
    label.className = 'block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1';
    label.textContent = labelText;
    const input = document.createElement('input');
    input.type = 'text';
    input.id = id;
    input.autocomplete = 'off';
    input.className = 'w-full p-2 border border-gray-300 dark:border-gray-600 rounded-md shadow-sm bg-white dark:bg-gray-700 text-gray-900 dark:text-gray-100';
    input.placeholder = placeholder;
    container.appendChild(label);
    container.appendChild(input);
    return container;
}

function createSelectComponent(id, data) {
    const container = document.createElement('div');
    const label = document.createElement('label');
    label.htmlFor = id;
    label.className = 'block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1';
    label.textContent = data.label;
    const select = document.createElement('select');
    select.id = id;
    select.className = 'w-full p-2 border border-gray-300 dark:border-gray-600 rounded-md shadow-sm bg-white dark:bg-gray-700 text-gray-900 dark:text-gray-100';
    
    // FIXED: Moved "Custom..." option to be the second option
    select.innerHTML = `<option value="">-- None --</option><option value="custom">Custom...</option>` + data.options.map(o => `<option value="${o}">${o}</option>`).join('');
    
    const customInput = document.createElement('input');
    customInput.type = 'text';
    customInput.id = `${id}-custom`;
    customInput.className = 'custom-input w-full p-2 mt-2 border border-gray-300 dark:border-gray-600 rounded-md hidden bg-white dark:bg-gray-700 text-gray-900 dark:text-gray-100';
    customInput.placeholder = 'Enter custom value...';
    select.onchange = () => {
        customInput.style.display = select.value === 'custom' ? 'block' : 'none';
    };
    container.appendChild(label);
    container.appendChild(select);
    container.appendChild(customInput);
    return container;
}

function populateTextToVideoForm() {
    const container = document.querySelector('#text-to-video-content .grid');
    if (!container) return;
    container.innerHTML = '';
    const elements = [
        { type: 'input', id: 'subject-input', label: 'Subject', placeholder: 'e.g., A dog' },
        { type: 'input', id: 'action-input', label: 'Action', placeholder: 'e.g., running' },
        { type: 'input', id: 'scene-input', label: 'Scene / Context', placeholder: 'e.g., on a sunny beach' },
        ...Object.keys(textVideoSelectData).map(key => ({ type: 'select', id: key, data: textVideoSelectData[key] })),
        { type: 'input', id: 'dialogue-input', label: 'Dialogue', placeholder: `e.g., Let's go!` }
    ];
    elements.forEach(el => {
        if (el.type === 'input') container.appendChild(createInputComponent(el.id, el.label, el.placeholder));
        else if (el.type === 'select') container.appendChild(createSelectComponent(el.id, el.data));
    });
}

function populateImageToVideoForm() {
    const container = document.getElementById('image-to-video-fields');
    if (!container) return;
    container.innerHTML = '';
    const elements = [
        { type: 'input', id: 'image-action-input', label: 'Action', placeholder: 'e.g., snow falling gently' },
        { type: 'input', id: 'image-scene-input', label: 'Scene / Context', placeholder: 'e.g., steam rising from a coffee cup' },
        ...Object.keys(textVideoSelectData).map(key => ({ type: 'select', id: `image-${key}`, data: textVideoSelectData[key] })),
        { type: 'input', id: 'image-dialogue-input', label: 'Dialogue', placeholder: `e.g., a character sighs` }
    ];
    elements.forEach(el => {
        if (el.type === 'input') container.appendChild(createInputComponent(el.id, el.label, el.placeholder));
        else if (el.type === 'select') container.appendChild(createSelectComponent(el.id, el.data));
    });
}

// --- HTML TEMPLATE (with complete output sections) ---
export function getGeneratorContent() {
    return `
        <div id="generator-content">
            <section id="generator">
                <div class="bg-white dark:bg-gray-800 rounded-2xl shadow-xl p-6 md:p-8">
                    <h3 class="text-xl font-bold text-gray-800 dark:text-gray-200 mb-2">Prompt Generator</h3>
                    <p class="text-gray-600 dark:text-gray-400 mb-6">Build a detailed prompt from scratch by selecting various cinematic elements, or generate one for an uploaded image.</p>
                    <div class="border-b border-gray-200 dark:border-gray-700 mb-6">
                        <nav class="-mb-px flex space-x-4" aria-label="Tabs">
                            <button id="text-to-video-tab" class="whitespace-nowrap py-4 px-1 border-b-2 font-medium text-sm text-indigo-600 dark:text-indigo-400 border-indigo-500">Text-to-Video</button>
                            <button id="image-to-video-tab" class="whitespace-nowrap py-4 px-1 border-b-2 font-medium text-sm text-gray-500 dark:text-gray-400 border-transparent hover:text-gray-700 dark:hover:text-gray-200 hover:border-gray-300 dark:hover:border-gray-600">Image-to-Video</button>
                        </nav>
                    </div>

                    <div id="text-to-video-content">
                        <div class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6"></div>
                        <div class="mt-8">
                            <button id="generate-text-prompt-btn" class="w-full flex items-center justify-center bg-indigo-600 text-white py-3 px-4 rounded-lg font-bold hover:bg-indigo-700 dark:bg-indigo-500 dark:hover:bg-indigo-600 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-indigo-500 disabled:bg-indigo-400">
                                <svg xmlns="http://www.w3.org/2000/svg" class="h-6 w-6 mr-2" fill="none" viewBox="0 0 24 24" stroke="currentColor"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9.663 17h4.673M12 3v1m6.364 1.636l-.707.707M21 12h-1M4 12H3m3.343-5.657l-.707-.707m2.828 9.9a5 5 0 117.072 0l-.548.547A3.374 3.374 0 0014 18.469V19a2 2 0 11-4 0v-.531c0-.895-.356-1.754-.988-2.386l-.548-.547z" /></svg>
                                Generate Prompt
                            </button>
                        </div>
                        <div id="text-prompt-output-container" class="mt-6 p-4 bg-gray-50 dark:bg-gray-700 rounded-lg border border-gray-200 dark:border-gray-600 hidden">
                             <div id="text-short-prompt-section">
                                 <div class="flex justify-between items-center mb-2">
                                     <h4 class="font-semibold text-indigo-700 dark:text-indigo-400">Generated Prompt:</h4>
                                     <button onclick="window.copyToClipboard('text-prompt-output')" class="p-1 text-gray-500 dark:text-gray-400 hover:text-indigo-600 dark:hover:text-indigo-400 rounded-md" title="Copy Prompt"><svg xmlns="http://www.w3.org/2000/svg" class="h-5 w-5" fill="none" viewBox="0 0 24 24" stroke="currentColor"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M8 16H6a2 2 0 01-2-2V6a2 2 0 012-2h8a2 2 0 012 2v2m-6 12h8a2 2 0 002-2v-8a2 2 0 00-2-2h-8a2 2 0 00-2 2v8a2 2 0 002 2z" /></svg></button>
                                 </div>
                                 <p id="text-prompt-output" class="text-gray-700 dark:text-gray-300 bg-white dark:bg-gray-800 p-3 rounded-md break-words"></p>
                             </div>
                            <div id="text-long-prompt-section" class="mt-4 hidden">
                                 <div class="flex justify-between items-center mb-2">
                                     <h4 class="font-semibold text-green-700 dark:text-green-400">Enhanced Prompt:</h4>
                                     <button onclick="window.copyToClipboard('text-long-prompt-output')" class="p-1 text-gray-500 dark:text-gray-400 hover:text-green-600 dark:hover:text-green-400 rounded-md" title="Copy Enhanced Prompt"><svg xmlns="http://www.w3.org/2000/svg" class="h-5 w-5" fill="none" viewBox="0 0 24 24" stroke="currentColor"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M8 16H6a2 2 0 01-2-2V6a2 2 0 012-2h8a2 2 0 012 2v2m-6 12h8a2 2 0 002-2v-8a2 2 0 00-2-2h-8a2 2 0 00-2 2v8a2 2 0 002 2z" /></svg></button>
                                 </div>
                                 <p id="text-long-prompt-output" class="text-gray-700 dark:text-gray-300 bg-white dark:bg-gray-800 p-3 rounded-md break-words"></p>
                             </div>
                            <button id="generate-longer-text-prompt-btn" class="mt-4 py-2 px-4 bg-green-600 text-white rounded-md font-semibold hover:bg-green-700 dark:bg-green-500 dark:hover:bg-green-600 hidden">
                                Generate Longer Prompt
                            </button>
                        </div>
                    </div>

                    <div id="image-to-video-content" class="hidden">
                         <div>
                             <h4 class="text-lg font-semibold text-gray-800 dark:text-gray-200 mb-2">1. Upload Image</h4>
                             <input type="file" id="image-upload" accept="image/*" class="w-full text-sm text-gray-500 dark:text-gray-400 file:mr-4 file:py-2 file:px-4 file:rounded-full file:border-0 file:text-sm file:font-semibold file:bg-indigo-50 dark:file:bg-indigo-900 file:text-indigo-600 dark:file:text-indigo-300 hover:file:bg-indigo-100 dark:hover:file:bg-indigo-800"/>
                             <div id="image-preview-container" class="mt-4 hidden"><img id="image-preview" src="#" alt="Image Preview" class="max-h-48 rounded-lg shadow-md mx-auto"/></div>
                         </div>
                        <h4 class="text-lg font-semibold text-gray-800 dark:text-gray-200 mt-6 mb-2">2. Add Details</h4>
                        <div class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6" id="image-to-video-fields"></div>
                        <div class="mt-8">
                            <button id="generate-image-prompt-btn" class="w-full flex items-center justify-center bg-indigo-600 text-white py-3 px-4 rounded-lg font-bold hover:bg-indigo-700 dark:bg-indigo-500 dark:hover:bg-indigo-600 disabled:bg-indigo-400">
                                <svg xmlns="http://www.w3.org/2000/svg" class="h-6 w-6 mr-2" fill="none" viewBox="0 0 24 24" stroke="currentColor"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M14.752 11.168l-3.197-2.132A1 1 0 0010 9.87v4.263a1 1 0 001.555.832l3.197-2.132a1 1 0 000-1.664z" /><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M21 12a9 9 0 11-18 0 9 9 0 0118 0z" /></svg>
                                Generate Prompt
                            </button>
                        </div>
                        <div id="image-prompt-output-container" class="mt-6 p-4 bg-gray-50 dark:bg-gray-700 rounded-lg border border-gray-200 dark:border-gray-600 hidden">
                           <div id="image-short-prompt-section">
                               <div class="flex justify-between items-center mb-2">
                                   <h4 class="font-semibold text-indigo-700 dark:text-indigo-400">Generated Prompt:</h4>
                                   <button onclick="window.copyToClipboard('image-prompt-output')" class="p-1 text-gray-500 dark:text-gray-400 hover:text-indigo-600 dark:hover:text-indigo-400 rounded-md" title="Copy Prompt"><svg xmlns="http://www.w3.org/2000/svg" class="h-5 w-5" fill="none" viewBox="0 0 24 24" stroke="currentColor"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M8 16H6a2 2 0 01-2-2V6a2 2 0 012-2h8a2 2 0 012 2v2m-6 12h8a2 2 0 002-2v-8a2 2 0 00-2-2h-8a2 2 0 00-2 2v8a2 2 0 002 2z" /></svg></button>
                               </div>
                               <p id="image-prompt-output" class="text-gray-700 dark:text-gray-300 bg-white dark:bg-gray-800 p-3 rounded-md break-words"></p>
                           </div>
                           <div id="image-long-prompt-section" class="mt-4 hidden">
                               <div class="flex justify-between items-center mb-2">
                                   <h4 class="font-semibold text-green-700 dark:text-green-400">Enhanced Prompt:</h4>
                                   <button onclick="window.copyToClipboard('image-long-prompt-output')" class="p-1 text-gray-500 dark:text-gray-400 hover:text-green-600 dark:hover:text-green-400 rounded-md" title="Copy Enhanced Prompt"><svg xmlns="http://www.w3.org/2000/svg" class="h-5 w-5" fill="none" viewBox="0 0 24 24" stroke="currentColor"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M8 16H6a2 2 0 01-2-2V6a2 2 0 012-2h8a2 2 0 012 2v2m-6 12h8a2 2 0 002-2v-8a2 2 0 00-2-2h-8a2 2 0 00-2 2v8a2 2 0 002 2z" /></svg></button>
                               </div>
                               <p id="image-long-prompt-output" class="text-gray-700 dark:text-gray-300 bg-white dark:bg-gray-800 p-3 rounded-md break-words"></p>
                           </div>
                           <button id="generate-longer-image-prompt-btn" class="mt-4 py-2 px-4 bg-green-600 text-white rounded-md font-semibold hover:bg-green-700 dark:bg-green-500 dark:hover:bg-green-600 hidden">
                               Generate Longer Prompt
                           </button>
                        </div>
                    </div>
                </div>
            </section>
        </div>
    `;
}

async function generateLongerPrompt(type) {
    const isText = type === 'text';
    const shortPromptElement = document.getElementById(isText ? 'text-prompt-output' : 'image-prompt-output');
    const longPromptSection = document.getElementById(isText ? 'text-long-prompt-section' : 'image-long-prompt-section');
    const longPromptOutputElement = document.getElementById(isText ? 'text-long-prompt-output' : 'image-long-prompt-output');
    const generateBtn = document.getElementById(isText ? 'generate-longer-text-prompt-btn' : 'generate-longer-image-prompt-btn');
    
    const initialPrompt = shortPromptElement.textContent;
    if (!initialPrompt) {
        showToast("Initial prompt is missing.", 'error');
        return;
    }
    generateBtn.disabled = true;
    generateBtn.textContent = 'Enhancing...';
    longPromptSection.classList.remove('hidden');
    longPromptOutputElement.textContent = "Enhancing prompt with more cinematic detail...";
    const systemPrompt = `You are a video director. Enhance this prompt to be more cinematic for an AI video model: "${initialPrompt}". Output ONLY the final enhanced prompt.`;
    try {
        const result = await callGeminiApi(systemPrompt);
        longPromptOutputElement.textContent = result;
        generateBtn.classList.add('hidden');
    } catch (error) {
        showToast(error.message, 'error');
        longPromptOutputElement.textContent = `Error: ${error.message}`;
        generateBtn.disabled = false;
        generateBtn.textContent = 'Generate Longer Prompt';
    }
}

// --- MAIN INITIALIZATION FUNCTION ---
export function initGenerator() {
    window.copyToClipboard = copyToClipboard;
    
    populateTextToVideoForm();
    populateImageToVideoForm();

    const textTab = document.getElementById('text-to-video-tab');
    const imageTab = document.getElementById('image-to-video-tab');
    const textContent = document.getElementById('text-to-video-content');
    const imageContent = document.getElementById('image-to-video-content');
    const generateTextBtn = document.getElementById('generate-text-prompt-btn');
    const generateLongerTextBtn = document.getElementById('generate-longer-text-prompt-btn');
    const generateImageBtn = document.getElementById('generate-image-prompt-btn');
    const generateLongerImageBtn = document.getElementById('generate-longer-image-prompt-btn');
    const imageUpload = document.getElementById('image-upload');
    const imagePreviewContainer = document.getElementById('image-preview-container');
    const imagePreview = document.getElementById('image-preview');

    textTab.addEventListener('click', () => {
        textContent.classList.remove('hidden');
        imageContent.classList.add('hidden');
        textTab.classList.add('text-indigo-600', 'dark:text-indigo-400', 'border-indigo-500');
        textTab.classList.remove('text-gray-500', 'dark:text-gray-400', 'border-transparent');
        imageTab.classList.add('text-gray-500', 'dark:text-gray-400', 'border-transparent');
        imageTab.classList.remove('text-indigo-600', 'dark:text-indigo-400', 'border-indigo-500');
    });
    imageTab.addEventListener('click', () => {
        imageContent.classList.remove('hidden');
        textContent.classList.add('hidden');
        imageTab.classList.add('text-indigo-600', 'dark:text-indigo-400', 'border-indigo-500');
        imageTab.classList.remove('text-gray-500', 'dark:text-gray-400', 'border-transparent');
        textTab.classList.add('text-gray-500', 'dark:text-gray-400', 'border-transparent');
        textTab.classList.remove('text-indigo-600', 'dark:text-indigo-400', 'border-indigo-500');
    });

    imageUpload.addEventListener('change', () => {
        const file = imageUpload.files[0];
        if (file) {
            const reader = new FileReader();
            reader.onload = (e) => {
                imagePreview.src = e.target.result;
                imagePreviewContainer.classList.remove('hidden');
            };
            reader.readAsDataURL(file);
        } else {
            imagePreviewContainer.classList.add('hidden');
        }
    });

    generateTextBtn.addEventListener('click', async () => {
        const keywords = [];
        ['subject-input', 'action-input', 'scene-input', 'dialogue-input'].forEach(id => {
            const element = document.getElementById(id);
            if (element && element.value) {
                keywords.push(id === 'dialogue-input' ? `A character says: '${element.value}'` : element.value);
            }
        });
        Object.keys(textVideoSelectData).forEach(key => {
            const select = document.getElementById(key);
            if (!select) return;
            let value = select.value;
            if (value === 'custom') {
                const customInput = document.getElementById(`${key}-custom`);
                value = customInput ? customInput.value : '';
            }
            if (value) keywords.push(value);
        });
        if (keywords.length === 0) {
            showToast("Please provide at least one keyword.", 'error');
            return;
        }
        const systemPrompt = `You are an expert video prompt engineer. Construct a prompt using these keywords: [${keywords.join(', ')}]. Synthesize them into a cinematic instruction. Output ONLY the final prompt string. Never use Markdown formatting like asterisks.`;
        const outputContainer = document.getElementById('text-prompt-output-container');
        const outputElement = document.getElementById('text-prompt-output');
        const originalButtonHtml = generateTextBtn.innerHTML;
        generateTextBtn.disabled = true;
        generateTextBtn.innerHTML = 'Generating...';
        outputContainer.classList.remove('hidden');
        document.getElementById('text-long-prompt-section').classList.add('hidden');
        generateLongerTextBtn.classList.add('hidden');
        outputElement.textContent = 'Processing...';
        try {
            const result = await callGeminiApi(systemPrompt);
            outputElement.textContent = result;
            if (result && !result.toLowerCase().startsWith('error')) {
                generateLongerTextBtn.classList.remove('hidden');
            }
        } catch (error) {
            showToast(error.message, 'error');
            outputElement.textContent = `Error: ${error.message}`;
        } finally {
            generateTextBtn.disabled = false;
            generateTextBtn.innerHTML = originalButtonHtml;
        }
    });

    // --- FIXED: Added event listener and logic for Image-to-Video generate button ---
    generateImageBtn.addEventListener('click', async () => {
        const imageFile = imageUpload.files[0];
        if (!imageFile) {
            showToast("Please upload an image first.", 'error');
            return;
        }

        const reader = new FileReader();
        const base64Data = await new Promise(resolve => {
            reader.onload = () => resolve(reader.result.split(',')[1]);
            reader.readAsDataURL(imageFile);
        });
        
        const imagePart = { inline_data: { mime_type: imageFile.type, data: base64Data } };

        const keywords = [];
        ['image-action-input', 'image-scene-input', 'image-dialogue-input'].forEach(id => {
            const element = document.getElementById(id);
            if (element && element.value) {
                keywords.push(id === 'image-dialogue-input' ? `A character says: '${element.value}'` : element.value);
            }
        });
        Object.keys(textVideoSelectData).forEach(key => {
            const select = document.getElementById(`image-${key}`);
            if (!select) return;
            let value = select.value;
            if (value === 'custom') {
                const customInput = document.getElementById(`image-${key}-custom`);
                value = customInput ? customInput.value : '';
            }
            if (value) keywords.push(value);
        });
        
        const systemPrompt = `Based on the attached image, generate a cinematic video prompt that incorporates these keywords if provided: [${keywords.join(', ')}]. If no keywords are provided, describe the image cinematically. Output ONLY the final prompt.`;
        const outputContainer = document.getElementById('image-prompt-output-container');
        const outputElement = document.getElementById('image-prompt-output');
        const originalButtonHtml = generateImageBtn.innerHTML;

        generateImageBtn.disabled = true;
        generateImageBtn.innerHTML = 'Generating...';
        outputContainer.classList.remove('hidden');
        document.getElementById('image-long-prompt-section').classList.add('hidden');
        generateLongerImageBtn.classList.add('hidden');
        outputElement.textContent = 'Processing...';

        try {
            const result = await callGeminiApi(systemPrompt, [imagePart]);
            outputElement.textContent = result;
            if (result && !result.toLowerCase().startsWith('error')) {
                generateLongerImageBtn.classList.remove('hidden');
            }
        } catch (error) {
            showToast(error.message, 'error');
            outputElement.textContent = `Error: ${error.message}`;
        } finally {
            generateImageBtn.disabled = false;
            generateImageBtn.innerHTML = originalButtonHtml;
        }
    });

    generateLongerTextBtn.addEventListener('click', () => generateLongerPrompt('text'));
    generateLongerImageBtn.addEventListener('click', () => generateLongerPrompt('image'));
}