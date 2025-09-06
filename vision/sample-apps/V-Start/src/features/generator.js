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

export async function getGeneratorContent() {
    try {
        const response = await fetch('/src/features/templates/generator.html');
        if (!response.ok) {
            throw new Error(`Network response was not ok: ${response.statusText}`);
        }
        return await response.text();
    } catch (error) {
        console.error('Failed to fetch generator template:', error);
        return '<div>Error loading content. Please check the console for details.</div>';
    }
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
    
    const originalButtonHtml = generateBtn.innerHTML;
    generateBtn.disabled = true;
    generateBtn.innerHTML = `
        <svg class="animate-spin -ml-1 mr-3 h-5 w-5 text-white" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24">
          <circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4"></circle>
          <path class="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
        </svg>
        Enhancing...
    `;

    longPromptSection.classList.remove('hidden');
    longPromptOutputElement.textContent = "Enhancing prompt with more cinematic detail...";
    
    const systemPrompt = `You are a Google Veo3 prompt engineer. Enhance this video prompt to be more cinematic and detailed: "${initialPrompt}". Output ONLY the enhanced video prompt text - no analysis, no markdown, no asterisks, no brackets, no explanations. Just the pure enhanced prompt text that will be sent to Veo3.`;
    
    try {
        const result = await callGeminiApi(systemPrompt);
        longPromptOutputElement.textContent = result;
        generateBtn.classList.add('hidden');
    } catch (error) {
        showToast(error.message, 'error');
        longPromptOutputElement.textContent = `Error: ${error.message}`;
    } finally {
        if (!generateBtn.classList.contains('hidden')) {
             generateBtn.disabled = false;
             generateBtn.innerHTML = originalButtonHtml;
        }
    }
}

function clearForm(type) {
    const prefix = type === 'image' ? 'image-' : '';
    
    const inputs = document.querySelectorAll(`#${type}-to-video-content input[type="text"], #${type}-to-video-content textarea`);
    inputs.forEach(input => input.value = '');

    const selects = document.querySelectorAll(`#${type}-to-video-content select`);
    selects.forEach(select => {
        select.selectedIndex = 0;
        const customInput = document.getElementById(`${select.id}-custom`);
        if (customInput) {
            customInput.style.display = 'none';
        }
    });
    
    if (type === 'image') {
        const imageUpload = document.getElementById('image-upload');
        const imagePreviewContainer = document.getElementById('image-preview-container');
        if(imageUpload) imageUpload.value = '';
        if(imagePreviewContainer) imagePreviewContainer.classList.add('hidden');
        document.getElementById('image-prompt-output-container').classList.add('hidden');
        document.getElementById('image-long-prompt-section').classList.add('hidden');
    } else {
        document.getElementById('text-prompt-output-container').classList.add('hidden');
        document.getElementById('text-long-prompt-section').classList.add('hidden');
    }
    
    showToast(`${type.charAt(0).toUpperCase() + type.slice(1)} form cleared!`, 'info');
}

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
    
    const clearTextFormBtn = document.getElementById('clear-text-form-btn');
    const clearImageFormBtn = document.getElementById('clear-image-form-btn');

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

    // TEXT TO VIDEO GENERATION
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
        
        // PROMPT for Veo3
        const systemPrompt = `You are a Google Veo3 prompt engineer. Create a cinematic video prompt using these keywords: [${keywords.join(', ')}]. Synthesize them into a single cohesive video instruction. Output ONLY the video prompt text - no analysis, no markdown, no asterisks, no explanations. Just the pure prompt text that will be sent to Veo3.`;
        
        const outputContainer = document.getElementById('text-prompt-output-container');
        const outputElement = document.getElementById('text-prompt-output');
        const originalButtonHtml = generateTextBtn.innerHTML;
        generateTextBtn.disabled = true;
        generateTextBtn.innerHTML = `
            <svg class="animate-spin -ml-1 mr-3 h-5 w-5 text-white" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24">
              <circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4"></circle>
              <path class="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
            </svg>
            Generating...
        `;
        outputContainer.classList.remove('hidden');
        document.getElementById('text-long-prompt-section').classList.add('hidden');
        generateLongerTextBtn.classList.add('hidden');
        outputElement.textContent = 'Processing...';
        try {
            const result = await callGeminiApi(systemPrompt);
            outputElement.textContent = result;
            if (result && !result.toLowerCase().startsWith('error')) {
                generateLongerTextBtn.innerHTML = 'Generate Longer Prompt';
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

    // IMAGE TO VIDEO GENERATION
    generateImageBtn.addEventListener('click', async () => {
        const imageFile = imageUpload.files[0];
        if (!imageFile) {
            showToast("Please upload an image first.", 'error');
            return;
        }

        // Read the file and ensure we get proper base64 data
        const reader = new FileReader();
        reader.onload = async (e) => {
            try {
                // Get the data URL and extract base64
                const dataUrl = e.target.result;
                const base64Data = dataUrl.split(',')[1];
                
                // Verify we have valid base64 data
                if (!base64Data || typeof base64Data !== 'string') {
                    showToast("Failed to read image data", 'error');
                    console.error('Invalid base64 data:', typeof base64Data);
                    return;
                }
                
                console.log('Image loaded successfully:', {
                    fileType: imageFile.type,
                    fileSize: imageFile.size,
                    base64Length: base64Data.length
                });
                
                // Create the image part with proper structure
                const imagePart = { 
                    inlineData: { 
                        mimeType: imageFile.type, 
                        data: base64Data 
                    } 
                };

                // Collect keywords
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
                
                // PROMPT for Veo3 
                const systemPrompt = keywords.length > 0 
                    ? `You are a Google Veo3 prompt engineer. Based on the uploaded image, create a cinematic video prompt that brings this exact scene to life with motion, incorporating these keywords: [${keywords.join(', ')}]. Output ONLY the video prompt text - no analysis, no markdown, no asterisks, no explanations. Just the pure prompt text that will be sent to Veo3.`
                    : `You are a Google Veo3 prompt engineer. Based on the uploaded image, create a cinematic video prompt that brings this exact scene to life with motion and animation. Output ONLY the video prompt text - no analysis, no markdown, no asterisks, no explanations. Just the pure prompt text that will be sent to Veo3.`;
                
                const outputContainer = document.getElementById('image-prompt-output-container');
                const outputElement = document.getElementById('image-prompt-output');
                const originalButtonHtml = generateImageBtn.innerHTML;

                generateImageBtn.disabled = true;
                generateImageBtn.innerHTML = `
                    <svg class="animate-spin -ml-1 mr-3 h-5 w-5 text-white" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24">
                      <circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4"></circle>
                      <path class="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
                    </svg>
                    Generating...
                `;
                
                outputContainer.classList.remove('hidden');
                document.getElementById('image-long-prompt-section').classList.add('hidden');
                generateLongerImageBtn.classList.add('hidden');
                outputElement.textContent = 'Processing image...';

                try {
                    // Call the API with the image
                    const result = await callGeminiApi(systemPrompt, [imagePart]);
                    outputElement.textContent = result;
                    if (result && !result.toLowerCase().startsWith('error')) {
                        generateLongerImageBtn.innerHTML = 'Generate Longer Prompt'; 
                        generateLongerImageBtn.disabled = false;
                        generateLongerImageBtn.classList.remove('hidden');
                    }
                } catch (error) {
                    showToast(error.message, 'error');
                    outputElement.textContent = `Error: ${error.message}`;
                } finally {
                    generateImageBtn.disabled = false;
                    generateImageBtn.innerHTML = originalButtonHtml;
                }
            } catch (error) {
                console.error('Error processing image:', error);
                showToast('Failed to process image', 'error');
                generateImageBtn.disabled = false;
                generateImageBtn.innerHTML = originalButtonHtml;
            }
        };
        
        reader.onerror = () => {
            showToast('Failed to read image file', 'error');
            console.error('FileReader error');
        };
        
        // Start reading the file
        reader.readAsDataURL(imageFile);
    });

    generateLongerTextBtn.addEventListener('click', () => generateLongerPrompt('text'));
    generateLongerImageBtn.addEventListener('click', () => generateLongerPrompt('image'));
    clearTextFormBtn.addEventListener('click', () => clearForm('text'));
    clearImageFormBtn.addEventListener('click', () => clearForm('image'));
}