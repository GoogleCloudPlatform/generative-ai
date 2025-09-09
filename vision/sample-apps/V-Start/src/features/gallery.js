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

import { copyToClipboard, showToast } from '../ui.js';

// --- GALLERY DATA ---
const galleryData = {
    subject: {
        title: "Subject, Scene & Action",
        examples: [
            {
                title: "Complex Subject",
                prompt: "A hyper-realistic, cinematic portrait of a wise, androgynous shaman of indeterminate age. Their weathered skin is etched with intricate, bioluminescent circuit-like tattoos that pulse with a soft, cyan light. They are draped in ceremonial robes woven from dark moss and shimmering, metallic fiber-optic threads. In one hand, they hold a gnarled wooden staff entwined with glowing energy conduits and topped with a floating, crystalline artifact. Perched on their shoulder is a small, mechanical owl with holographic wings and camera-lens eyes that blink with a soft, red light. Their expression is serene and ancient, eyes holding a deep, knowing look.",
                youtubeId: "GKOpOcs8IF8"
            },
            {
                title: "Portrait",
                prompt: "A cinematic close-up portrait of a woman sitting in a café at night, with a very shallow depth of field. Her face is in sharp focus, while the city lights outside the window behind her are transformed into soft, beautiful bokeh circles.",
                youtubeId: "Ol66pK2N7L0"
            },
            {
                title: "Sequencing of Actions",
                prompt: "A gloved hand carefully slices open the spine of an ancient, leather-bound book with a scalpel. The hand then delicately extracts a tiny, metallic data chip hidden within the binding. The character's eyes, previously focused and calm, widen in a flash of alarm as a floorboard creaks off-screen. They quickly palm the chip, their head snapping up to scan the dimly lit room, their body tense and listening for any other sound.",
                youtubeId: "EbCAqMF2DBo"
            },
            {
                title: "Emotional Expression",
                prompt: "A close-up shot of a man's face, approximately 30-40 years old, with short brown hair and a beard, wearing a gray t-shirt. The man is seated at a table, looking at a document, and expressing a range of emotions, including surprise, sadness and frustration.",
                youtubeId: "lYMjzZHykCo"
            }
        ]
    },
    camera: {
        title: "Camera Work",
        examples: [
            {
                title: "Low Angle Shot",
                prompt: "Dynamic low-angle shot of a basketball player soaring for a slam dunk, stadium lights flaring.",
                youtubeId: "zCZ91E7tPeE"
            },
            {
                title: "Drone Shot",
                prompt: "Sweeping aerial drone shot flying over a tropical island chain.",
                youtubeId: "gvPtt5f-kKc"
            },
            {
                title: "Zoom In Shot",
                prompt: "A slow, dramatic zoom in on a mysterious, ancient compass lying on a dusty map. The camera starts wide, showing the map and a flickering candle, then smoothly zooms in until the intricate, glowing symbols on the compass face fill the entire frame.",
                youtubeId: "izn8VHHFy3c"
            },
            {
                title: "Over-the-Shoulder",
                prompt: "An over-the-shoulder shot from behind a seasoned detective, looking at a nervous informant sitting across a table in a dimly lit interrogation room. The focus is on the informant's expressive, anxious face.",
                youtubeId: "z73bvXtUC_0"
            },
            {
                title: "Rack Focus",
                prompt: "A medium shot of a detective's hand in the foreground, holding a single, spent bullet casing. The camera then performs a slow rack focus, shifting from the casing to reveal the anxious face of a witness in the background, now in sharp focus.",
                youtubeId: "-p6W4mCYuvc"
            },
            {
                title: "Handheld Camera",
                prompt: "An intense handheld camera shot during a chaotic marketplace chase. The camera struggles to keep up, with jerky movements and quick, unstable pans as it follows the character weaving through dense crowds and knocking over stalls.",
                youtubeId: "csnE4FNogJQ"
            }
        ]
    },
    style: {
        title: "Visual & Temporal Styles",
        examples: [
            {
                title: "Anime Style",
                prompt: "A dynamic scene in a vibrant Japanese anime style. A magical girl with silver hair and glowing blue eyes walks in a forest The style features sharp lines, bright, saturated colors, and expressive.",
                youtubeId: "vu2ZFw-9ZMI"
            },
            {
                title: "Lens Flare",
                prompt: "A cinematic shot of a couple embracing on a beach at sunset. As the sun dips below the horizon behind them, a warm, anamorphic lens flare streaks horizontally across the frame, adding a romantic and nostalgic feeling to the scene.",
                youtubeId: "jY3gQS73614"
            },
            {
                title: "Jump Cut",
                prompt: "A person sitting in the same position but wearing different outfits, with sharp jump cuts between each outfit change. The background should stay static and the person should reappear instantly in the new outfit, creating a fast-paced, rhythmic jump cut effect. The lighting and framing should remain consistent to emphasize the sudden changes.",
                youtubeId: "d-cGj3kAnsQ"
            },
            {
                title: "Time-Lapse",
                prompt: "A time-lapse of a bustling city skyline as day transitions to night. The camera is static. Watch as the sun sets, casting long shadows, and the city lights begin to twinkle on, with streaks of car headlights moving along the streets below.",
                youtubeId: "CT0PIze9w0Y"
            },
            {
                title: "Cyberpunk Lighting",
                prompt: "A hyper-realistic, cinematic shot of a rain-slicked cyberpunk alleyway at midnight. Pulsating pink and teal neon signs reflect off puddles on the ground, illuminating the steam rising from a street vendor's cart.",
                youtubeId: "bKIZ-pdCJnA"
            },
            {
                title: "Vintage Style",
                prompt: "A vintage 1920s street scene, sepia toned, film grain, with characters in period attire.",
                youtubeId: "WJwj6y7p8SI"
            }
        ]
    },
    audio: {
        title: "Audio",
        examples: [
            {
                title: "Ambient Noise",
                prompt: "A static, wide shot of a vast, ancient library at night. The only sounds are the soft, rhythmic ticking of a grandfather clock, the gentle rustle of turning pages, and the faint sound of wind howling outside the tall, arched windows.",
                youtubeId: "WsXXBDhO7l0"
            },
            {
                title: "Dialogue",
                prompt: "A medium shot in a dimly lit interrogation room. The seasoned detective says: Your story has holes. The nervous informant, sweating under a single bare bulb, replies: I'm telling you everything I know. The only other sounds are the slow, rhythmic ticking of a wall clock and the faint sound of rain against the window.",
                youtubeId: "yGcMvkFK9Zo"
            }
        ]
    }
};

export async function getGalleryContent() {
    try {
        const response = await fetch('/src/features/templates/gallery.html');
        if (!response.ok) {
            throw new Error(`Network response was not ok: ${response.statusText}`);
        }
        return await response.text();
    } catch (error) {
        console.error('Failed to fetch gallery template:', error);
        return '<div>Error loading content. Please check the console for details.</div>';
    }
}

export function initGallery() {
    window.copyToClipboard = copyToClipboard;

    const catContainer = document.getElementById('gallery-categories');
    const slidersContainer = document.getElementById('gallery-sliders-container');
    catContainer.innerHTML = '';
    slidersContainer.innerHTML = '';
    
    Object.keys(galleryData).forEach(key => {
        const button = document.createElement('button');
        button.className = 'gallery-category-button py-2 px-5 rounded-full font-semibold shadow-sm bg-gray-200 hover:bg-gray-300 dark:bg-gray-700 dark:hover:bg-gray-600 text-gray-700 dark:text-gray-300 transition-colors duration-200';
        button.textContent = galleryData[key].title;
        button.onclick = () => showGalleryCategory(key);
        catContainer.appendChild(button);
        slidersContainer.appendChild(createSlider(key, galleryData[key]));
    });

    showGalleryCategory('subject'); // Show the first category by default
}

function createSlider(categoryId, categoryData) {
    const sliderWrapper = document.createElement('div');
    sliderWrapper.id = `gallery-${categoryId}`;
    sliderWrapper.className = 'gallery-examples relative';
    sliderWrapper.innerHTML = `
        <div class="slider-container flex overflow-x-auto snap-x snap-mandatory gap-6 pb-4">
            ${categoryData.examples.map((ex, index) => {
                const promptId = `gallery-prompt-${categoryId}-${index}`;
                // Direct YouTube embed URL, autoplay=0 (no auto-play), mute=1 (no sound), controls=1
                const youtubeEmbedUrl = ex.youtubeId ?
                    `https://www.youtube.com/embed/${ex.youtubeId}?autoplay=0&mute=1&controls=1&modestbranding=1&rel=0` :
                    ''; // Empty if no YouTube ID

                return `
                    <div class="slider-item snap-start flex-shrink-0 w-full sm:w-1/2 lg:w-1/3 bg-white dark:bg-gray-800 rounded-xl shadow-lg overflow-hidden flex flex-col">
                        <div class="video-wrapper">
                            ${youtubeEmbedUrl ? `
                                <iframe
                                    src="${youtubeEmbedUrl}"
                                    title="${ex.title}"
                                    frameborder="0"
                                    allow="accelerometer; autoplay; clipboard-write; encrypted-media; gyroscope; picture-in-picture"
                                    allowfullscreen
                                ></iframe>
                            ` : `
                                <div class="flex items-center justify-center h-full text-gray-500 dark:text-gray-400">
                                    No video available
                                </div>
                            `}
                        </div>
                        <div class="p-6 flex-grow flex flex-col">
                            <h4 class="font-semibold text-lg mb-2 text-gray-800 dark:text-gray-200">${ex.title}</h4>
                            <p id="${promptId}" class="text-gray-700 dark:text-gray-300 text-sm flex-grow mb-4" style="text-align: justify;">${ex.prompt}</p>
                            <div class="flex gap-2">
                                <button onclick="copyToClipboard('${promptId}')" class="flex items-center gap-2 text-sm py-2 px-3 bg-gray-100 dark:bg-gray-700 hover:bg-gray-200 dark:hover:bg-gray-600 text-gray-700 dark:text-gray-300 rounded-md transition-colors">
                                    <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                        <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M8 16H6a2 2 0 01-2-2V6a2 2 0 012-2h8a2 2 0 012 2v2m-6 12h8a2 2 0 002-2v-8a2 2 0 00-2-2h-8a2 2 0 00-2 2v8a2 2 0 002 2z"></path>
                                    </svg>
                                    Copy Prompt
                                </button>
                                </div>
                        </div>
                    </div>`;
            }).join('')}
        </div>`;
    return sliderWrapper;
}

function showGalleryCategory(category) {
    document.querySelectorAll('.gallery-examples').forEach(el => el.style.display = 'none');
    document.querySelectorAll('.gallery-category-button').forEach(el => {
        el.classList.remove('bg-indigo-600', 'hover:bg-indigo-700', 'text-white');
        el.classList.add('bg-gray-200', 'hover:bg-gray-300', 'dark:bg-gray-700', 'dark:hover:bg-gray-600', 'text-gray-700', 'dark:text-gray-300');
    });
    
    const activeBtn = Array.from(document.querySelectorAll('.gallery-category-button')).find(btn => btn.textContent === galleryData[category].title);
    if (activeBtn) {
        document.getElementById(`gallery-${category}`).style.display = 'block';
        activeBtn.classList.remove('bg-gray-200', 'hover:bg-gray-300', 'dark:bg-gray-700', 'dark:hover:bg-gray-600', 'text-gray-700', 'dark:text-gray-300');
        activeBtn.classList.add('bg-indigo-600', 'hover:bg-indigo-700', 'text-white');
    }
}
