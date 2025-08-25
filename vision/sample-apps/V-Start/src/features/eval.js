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

import { showToast } from '../ui.js';

// --- MODULE-LEVEL STATE ---
const questions = [
    {
        id: 'q_quality_comparison',
        text: 'How would you rate the overall quality of Video A compared to Video B?',
        options: [
            'Video A is higher quality',
            'Video B is higher quality',
            'They are about the same quality'
        ]
    }
];

let evaluationPairs = [];
let currentPairIndex = 0;
let evaluationResults = [];
let isPreloadedStudy = false;

// --- DATA FETCHING ---
async function fetchVeoYouTubeStudy() {
    try {
        const response = await fetch('/data/veo-youtube-study.json');
        if (!response.ok) {
            throw new Error(`HTTP error! status: ${response.status}`);
        }
        return await response.json();
    } catch (error) {
        console.error("Error fetching YouTube study data:", error);
        showToast("Could not load the YouTube study. Please try again later.", "error");
        return [];
    }
}

// --- HTML TEMPLATE ---

export function getEvalContent() {
    return `
        <div id="eval-content">
            <div id="choice-section" class="max-w-lg mx-auto bg-white dark:bg-gray-800 p-8 rounded-lg shadow-md text-center">
                <h1 class="text-3xl md:text-4xl font-bold text-gray-900 dark:text-gray-200">A/B Video Evaluation</h1>
                <p class="text-gray-600 dark:text-gray-400 mt-4 mb-6">Participate in existing studies or create your own.</p>
                <div class="space-y-4">
                    <div class="relative">
                        <button id="participate-button" class="w-full bg-green-600 text-white font-bold py-3 px-8 rounded-lg hover:bg-green-700 flex items-center justify-center">
                            <span>Participate in Veo Prompt Format Study</span>
                            <svg id="info-icon" class="ml-2 w-5 h-5 cursor-pointer" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M13 16h-1v-4h-1m1-4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z"></path></svg>
                        </button>
                        <div id="veo-study-details" class="hidden mt-2 bg-blue-50 dark:bg-blue-900 border border-blue-200 dark:border-blue-700 rounded-lg p-4 text-left">
                            <h3 class="font-semibold text-blue-900 dark:text-blue-200 mb-2">About the Veo Study</h3>
                            <p class="text-sm text-blue-800 dark:text-blue-300">This study evaluates the impact of prompt format on video quality. You'll compare videos generated using <strong>JSON-structured prompts</strong> versus <strong>plain text prompts</strong>.</p>
                        </div>
                    </div>
                    <button id="create-button" class="w-full bg-indigo-600 text-white font-bold py-3 px-8 rounded-lg hover:bg-indigo-700">Create Your Own Study</button>
                </div>
            </div>

            <div id="setup-section" class="hidden max-w-2xl mx-auto bg-white dark:bg-gray-800 p-8 rounded-lg shadow-md">
                <h1 class="text-3xl md:text-4xl font-bold text-gray-900 dark:text-gray-200 text-center">Create Your Own Study</h1>
                <p class="text-gray-600 dark:text-gray-400 mt-4 mb-6 text-center">Upload local files or paste public URLs. Both groups must have the same number of videos.</p>
                <div class="grid grid-cols-1 md:grid-cols-2 gap-6">
                    <div>
                        <label class="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">Group A Videos</label>
                        <input type="file" id="group-a-files" multiple accept="video/*" class="w-full text-sm text-gray-500 dark:text-gray-400 file:mr-4 file:py-2 file:px-4 file:rounded-lg file:border-0 file:bg-white dark:file:bg-gray-600 hover:file:bg-gray-100 dark:hover:file:bg-gray-500 file:text-gray-700 dark:file:text-gray-200 border border-gray-300 dark:border-gray-600 bg-white dark:bg-gray-700">
                        <textarea id="group-a-urls" rows="4" class="mt-2 w-full p-2 border border-gray-300 dark:border-gray-600 rounded-md bg-white dark:bg-gray-700 text-gray-900 dark:text-gray-100" placeholder="Or paste URLs (one per line)"></textarea>
                    </div>
                    <div>
                        <label class="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">Group B Videos</label>
                        <input type="file" id="group-b-files" multiple accept="video/*" class="w-full text-sm text-gray-500 dark:text-gray-400 file:mr-4 file:py-2 file:px-4 file:rounded-lg file:border-0 file:bg-white dark:file:bg-gray-600 hover:file:bg-gray-100 dark:hover:file:bg-gray-500 file:text-gray-700 dark:file:text-gray-200 border border-gray-300 dark:border-gray-600 bg-white dark:bg-gray-700">
                        <textarea id="group-b-urls" rows="4" class="mt-2 w-full p-2 border border-gray-300 dark:border-gray-600 rounded-md bg-white dark:bg-gray-700 text-gray-900 dark:text-gray-100" placeholder="Or paste URLs (one per line)"></textarea>
                    </div>
                </div>
                <div class="mt-6 flex items-center justify-center">
                    <label class="flex items-center">
                        <input type="checkbox" id="randomize-pairs-checkbox" class="h-4 w-4 text-indigo-600 border-gray-300 dark:border-gray-600 rounded bg-white dark:bg-gray-700">
                        <span class="ml-2 text-sm text-gray-700 dark:text-gray-300">Randomize video pairs</span>
                    </label>
                </div>
                <div class="mt-8 grid grid-cols-2 gap-4">
                    <button id="back-button-creator" class="w-full bg-gray-200 dark:bg-gray-600 text-gray-800 dark:text-gray-200 font-bold py-3 px-4 rounded-lg hover:bg-gray-300 dark:hover:bg-gray-500">Back</button>
                    <button id="start-eval-button-creator" class="w-full bg-indigo-600 text-white font-bold py-3 px-4 rounded-lg hover:bg-indigo-700 disabled:bg-indigo-400" disabled>Start Evaluation</button>
                </div>
            </div>

            <div id="main-eval-content" class="hidden">
                <header class="text-center mb-8 relative">
                    <h1 class="text-3xl font-bold text-gray-900 dark:text-gray-200" id="study-title">A/B Video Evaluation</h1>
                    <p id="study-subtitle" class="text-gray-600 dark:text-gray-400 mt-2"></p>
                </header>
                <main>
                    <p id="progress-counter" class="text-lg font-semibold text-center mb-4 text-gray-800 dark:text-gray-200"></p>
                    <div class="grid grid-cols-1 md:grid-cols-2 gap-8 mb-8">
                        <div>
                            <h2 class="text-xl font-semibold mb-4 text-center text-gray-800 dark:text-gray-200">Video A</h2>
                            <div class="video-container bg-black rounded-md">
                                <iframe id="video-a" class="w-full h-full" frameborder="0" allow="accelerometer; autoplay; clipboard-write; encrypted-media; gyroscope; picture-in-picture" allowfullscreen></iframe>
                                <video id="video-a-tag" controls playsinline class="w-full h-full bg-black rounded-md hidden"></video>
                            </div>
                        </div>
                        <div>
                            <h2 class="text-xl font-semibold mb-4 text-center text-gray-800 dark:text-gray-200">Video B</h2>
                            <div class="video-container bg-black rounded-md">
                                <iframe id="video-b" class="w-full h-full" frameborder="0" allow="accelerometer; autoplay; clipboard-write; encrypted-media; gyroscope; picture-in-picture" allowfullscreen></iframe>
                                <video id="video-b-tag" controls playsinline class="w-full h-full bg-black rounded-md hidden"></video>
                            </div>
                        </div>
                    </div>
                    <div id="questions-container" class="bg-white dark:bg-gray-800 p-6 rounded-lg shadow-md border border-gray-200 dark:border-gray-700"></div>
                    <div class="mt-8 text-center space-x-4">
                        <button id="previous-pair" class="bg-gray-500 text-white font-bold py-3 px-6 rounded-lg hover:bg-gray-600 disabled:bg-gray-300 disabled:text-gray-500" disabled>Previous</button>
                        <button id="submit-vote" class="bg-indigo-600 text-white font-bold py-3 px-8 rounded-lg hover:bg-indigo-700 disabled:bg-gray-400">Submit & Next</button>
                    </div>
                    <div class="mt-4 text-center">
                        <button id="back-to-choice-button" class="text-sm text-gray-600 dark:text-gray-400 hover:underline"> &larr; Back to Main Menu</button>
                    </div>
                </main>
            </div>

            <div id="thank-you-section" class="hidden max-w-3xl mx-auto">
                <div class="bg-white dark:bg-gray-800 p-8 rounded-lg shadow-md">
                    <h2 class="text-3xl font-bold text-green-600 dark:text-green-400 text-center">Evaluation Complete!</h2>
                    <div id="results-summary" class="mt-8">
                        <h3 class="text-xl font-semibold mb-4 text-gray-800 dark:text-gray-200">Your Results</h3>
                        <div id="results-chart" class="bg-gray-50 dark:bg-gray-700 p-6 rounded-lg border border-gray-200 dark:border-gray-600"></div>
                    </div>
                    <div id="results-interpretation" class="mt-6 bg-blue-50 dark:bg-blue-900 p-6 rounded-lg border border-blue-200 dark:border-blue-700">
                        <h4 class="font-semibold text-blue-900 dark:text-blue-200 mb-2">Analysis</h4>
                        <div id="interpretation-text" class="text-sm text-blue-800 dark:text-blue-300"></div>
                    </div>
                    <div class="mt-8 flex flex-col sm:flex-row gap-4 justify-center">
                        <button id="download-results" class="bg-blue-600 text-white font-bold py-3 px-6 rounded-lg hover:bg-blue-700">Download Results (CSV)</button>
                        <button id="back-to-menu-final" class="bg-gray-200 dark:bg-gray-600 text-gray-800 dark:text-gray-200 font-bold py-3 px-6 rounded-lg hover:bg-gray-300 dark:hover:bg-gray-500">Back to Main Menu</button>
                    </div>
                </div>
            </div>
        </div>
    `;
}

// --- MAIN INITIALIZATION AND LOGIC ---

export function initEval() {
    const choiceSection = document.getElementById('choice-section');
    const setupSection = document.getElementById('setup-section');
    const mainEvalContent = document.getElementById('main-eval-content');
    const thankYouSection = document.getElementById('thank-you-section');
    
    const participateButton = document.getElementById('participate-button');
    const createButton = document.getElementById('create-button');
    const backButtonCreator = document.getElementById('back-button-creator');
    const startEvalButtonCreator = document.getElementById('start-eval-button-creator');
    const submitButton = document.getElementById('submit-vote');
    const previousButton = document.getElementById('previous-pair');
    const backToChoiceButton = document.getElementById('back-to-choice-button');
    const backToMenuFinal = document.getElementById('back-to-menu-final');
    const infoIcon = document.getElementById('info-icon');
    const veoStudyDetails = document.getElementById('veo-study-details');

    const showSection = (sectionId) => {
        [choiceSection, setupSection, mainEvalContent, thankYouSection].forEach(section => {
            section.style.display = section.id === sectionId ? 'block' : 'none';
        });
    };
    
    const resetState = () => {
        currentPairIndex = 0;
        evaluationResults = [];
        evaluationPairs = [];
        isPreloadedStudy = false;
        showSection('choice-section');
    };

    const startEvaluation = () => {
        if (isPreloadedStudy) {
            document.getElementById('study-title').textContent = 'Veo Prompt Format Evaluation';
            document.getElementById('study-subtitle').textContent = 'Comparing JSON vs Plain Text prompts';
        } else {
            document.getElementById('study-title').textContent = 'A/B Video Evaluation';
            document.getElementById('study-subtitle').textContent = 'Comparing Group A vs Group B';
        }
        
        showSection('main-eval-content');
        renderQuestions();
        loadVideoPair(currentPairIndex);
    };

    const renderQuestions = () => {
        const questionsContainer = document.getElementById('questions-container');
        questionsContainer.innerHTML = '';
        questions.forEach(q => {
            const optionsHtml = q.options.map(option => `
                <label class="inline-flex items-center mr-4 mb-2">
                    <input type="radio" class="form-radio h-5 w-5 text-indigo-600 bg-white dark:bg-gray-700 border-gray-300 dark:border-gray-600" name="${q.id}" value="${option}" required>
                    <span class="ml-2 text-gray-700 dark:text-gray-300">${option}</span>
                </label>
            `).join('');
            questionsContainer.innerHTML += `<div class="mb-4"><p class="font-semibold mb-3 text-lg text-gray-800 dark:text-gray-200">${q.text}</p><div class="flex flex-wrap justify-center">${optionsHtml}</div></div>`;
        });
    };
    
    const loadVideoPair = (index) => {
        if (index >= evaluationPairs.length) {
            showResultsAnalysis();
            return;
        }
        
        previousButton.disabled = (index === 0);
        document.getElementById('progress-counter').textContent = `Pair ${index + 1} of ${evaluationPairs.length}`;
        submitButton.disabled = true;
        
        const pair = evaluationPairs[index];
        const isBFirst = document.getElementById('randomize-pairs-checkbox')?.checked ? Math.random() > 0.5 : false;
        
        const iframeA = document.getElementById('video-a');
        const iframeB = document.getElementById('video-b');
        const videoTagA = document.getElementById('video-a-tag');
        const videoTagB = document.getElementById('video-b-tag');
        
        let videoSrcA = isBFirst ? pair.videoB : pair.videoA;
        let videoSrcB = isBFirst ? pair.videoA : pair.videoB;
        
        let readyCount = 0;
        const onReady = () => {
            readyCount++;
            if (readyCount === 2) {
                submitButton.disabled = false;
            }
        };

        if (isPreloadedStudy) { // YouTube Study
            iframeA.style.display = 'block';
            iframeB.style.display = 'block';
            videoTagA.style.display = 'none';
            videoTagB.style.display = 'none';

            iframeA.src = `${videoSrcA}?autoplay=1&mute=1&loop=1&playlist=${videoSrcA.split('/').pop()}`;
            iframeB.src = `${videoSrcB}?autoplay=1&mute=1&loop=1&playlist=${videoSrcB.split('/').pop()}`;
            iframeA.onload = onReady;
            iframeB.onload = onReady;

            iframeA.dataset.group = isBFirst ? 'json' : 'plain';
            iframeB.dataset.group = isBFirst ? 'plain' : 'json';
        } else { // User-created study
            iframeA.style.display = 'none';
            iframeB.style.display = 'none';
            videoTagA.style.display = 'block';
            videoTagB.style.display = 'block';

            if (typeof videoSrcA === 'string' && videoSrcA.startsWith('http')) {
                videoSrcA = `/api/proxy-video?url=${encodeURIComponent(videoSrcA)}`;
            }
            if (typeof videoSrcB === 'string' && videoSrcB.startsWith('http')) {
                videoSrcB = `/api/proxy-video?url=${encodeURIComponent(videoSrcB)}`;
            }
            
            videoTagA.src = videoSrcA;
            videoTagB.src = videoSrcB;
            videoTagA.oncanplay = onReady;
            videoTagB.oncanplay = onReady;
            videoTagA.load();
            videoTagB.load();

            videoTagA.dataset.group = isBFirst ? 'B' : 'A';
            videoTagB.dataset.group = isBFirst ? 'A' : 'B';
        }
        
        document.querySelectorAll('input[type="radio"]').forEach(radio => { radio.checked = false; });
    };

    const handleSubmit = () => {
        const selectedOption = document.querySelector(`input[name="${questions[0].id}"]:checked`);
        if (!selectedOption) {
            showToast('Please select an answer.', 'error');
            return;
        }
        
        const videoTagA = document.getElementById('video-a-tag');
        const iframeA = document.getElementById('video-a');

        const newResult = {
            pairId: currentPairIndex + 1,
            assignment: { 
                videoA_group: isPreloadedStudy ? iframeA.dataset.group : videoTagA.dataset.group, 
                videoB_group: isPreloadedStudy ? document.getElementById('video-b').dataset.group : document.getElementById('video-b-tag').dataset.group 
            },
            response: selectedOption.value
        };
        
        const resultIndex = evaluationResults.findIndex(r => r.pairId === newResult.pairId);
        if (resultIndex >= 0) {
            evaluationResults[resultIndex] = newResult;
        } else {
            evaluationResults.push(newResult);
        }

        currentPairIndex++;
        loadVideoPair(currentPairIndex);
    };
    
    const handlePrevious = () => {
        if (currentPairIndex > 0) {
            currentPairIndex--;
            loadVideoPair(currentPairIndex);
            
            const previousResult = evaluationResults.find(r => r.pairId === currentPairIndex + 1);
            if (previousResult) {
                const radioButton = document.querySelector(`input[name="${questions[0].id}"][value="${previousResult.response}"]`);
                if (radioButton) radioButton.checked = true;
            }
        }
    };
    
    const calculateResults = () => {
        const stats = { totalPairs: evaluationResults.length, groupA_wins: 0, groupB_wins: 0, ties: 0 };
        
        evaluationResults.forEach(result => {
            if (result.response === 'Video A is higher quality') {
                if (result.assignment.videoA_group === 'plain' || result.assignment.videoA_group === 'A') stats.groupA_wins++;
                else stats.groupB_wins++;
            } else if (result.response === 'Video B is higher quality') {
                if (result.assignment.videoB_group === 'plain' || result.assignment.videoB_group === 'A') stats.groupA_wins++;
                else stats.groupB_wins++;
            } else {
                stats.ties++;
            }
        });

        if (isPreloadedStudy) {
            stats.plain_wins = stats.groupA_wins;
            stats.json_wins = stats.groupB_wins;
        }
        
        return stats;
    };
    
    const generateInterpretation = (stats) => {
        if (stats.totalPairs === 0) return '<p>No results to analyze.</p>';
        const tiePercent = (stats.ties / stats.totalPairs) * 100;

        if (isPreloadedStudy) {
            const jsonPercent = (stats.json_wins / stats.totalPairs) * 100;
            const plainPercent = (stats.plain_wins / stats.totalPairs) * 100;
            if (tiePercent > 50) return `<p><strong>Conclusion: The model appears robust to prompt format.</strong> Both formats produced comparable results.</p>`;
            if (stats.json_wins > stats.plain_wins) return `<p><strong>Conclusion: JSON-structured prompts performed better.</strong> Videos from JSON prompts were preferred in ${jsonPercent.toFixed(1)}% of evaluations.</p>`;
            if (stats.plain_wins > stats.json_wins) return `<p><strong>Conclusion: Plain text prompts performed better.</strong> Videos from plain text prompts were preferred in ${plainPercent.toFixed(1)}% of evaluations.</p>`;
            return `<p><strong>Conclusion: The results were tied.</strong> Both formats performed equally well.</p>`;
        } else {
            const groupAPercent = (stats.groupA_wins / stats.totalPairs) * 100;
            const groupBPercent = (stats.groupB_wins / stats.totalPairs) * 100;
            return `<p><strong>Results:</strong> Group A was preferred ${groupAPercent.toFixed(1)}% of the time, and Group B was preferred ${groupBPercent.toFixed(1)}% of the time.</p>`;
        }
    };
    
    const showResultsAnalysis = () => {
        showSection('thank-you-section');
        const stats = calculateResults();
        
        const chartContainer = document.getElementById('results-chart');
        chartContainer.innerHTML = '';
        
        const data = isPreloadedStudy 
            ? [['Format', 'Wins'], ['JSON', stats.json_wins], ['Plain Text', stats.plain_wins], ['Tie', stats.ties]]
            : [['Group', 'Wins'], ['Group A', stats.groupA_wins], ['Group B', stats.groupB_wins], ['Tie', stats.ties]];
        
        data.slice(1).forEach(row => {
            const percent = stats.totalPairs > 0 ? ((row[1] / stats.totalPairs) * 100).toFixed(1) : 0;
            const bar = document.createElement('div');
            bar.innerHTML = `
                <div class="flex justify-between mb-1">
                    <span class="text-sm font-medium text-gray-700 dark:text-gray-300">${row[0]}</span>
                    <span class="text-sm font-medium text-gray-700 dark:text-gray-300">${row[1]}/${stats.totalPairs} (${percent}%)</span>
                </div>
                <div class="w-full bg-gray-200 dark:bg-gray-600 rounded-full h-6"><div class="bg-blue-600 dark:bg-blue-500 h-6 rounded-full flex items-center justify-center text-white text-xs" style="width: ${percent}%">${percent}%</div></div>
            `;
            bar.className = 'mb-4';
            chartContainer.appendChild(bar);
        });

        document.getElementById('interpretation-text').innerHTML = generateInterpretation(stats);
        
        const downloadButton = document.getElementById('download-results');
        const csvContent = "pair_id,video_a_group,video_b_group,response\n" + evaluationResults.map(r => 
            [r.pairId, r.assignment.videoA_group, r.assignment.videoB_group, `"${r.response}"`].join(',')
        ).join('\n');
        
        const blob = new Blob([csvContent], { type: 'text/csv;charset=utf-8;' });
        const url = URL.createObjectURL(blob);
        
        downloadButton.onclick = () => {
            const a = document.createElement('a');
            a.href = url;
            a.download = isPreloadedStudy ? 'Veo_YouTube_Study_Results.csv' : 'AB_Eval_Results.csv';
            document.body.appendChild(a);
            a.click();
            document.body.removeChild(a);
            showToast('Results downloaded successfully!', 'success');
        };
    };
    
    const validateAndLoadCustomPairs = () => {
        const groupAFiles = Array.from(document.getElementById('group-a-files').files);
        const groupAUrls = document.getElementById('group-a-urls').value.split('\n').filter(url => url.trim() !== '');
        const groupBFiles = Array.from(document.getElementById('group-b-files').files);
        const groupBUrls = document.getElementById('group-b-urls').value.split('\n').filter(url => url.trim() !== '');

        const groupAVideos = [...groupAUrls, ...groupAFiles.map(file => URL.createObjectURL(file))];
        const groupBVideos = [...groupBUrls, ...groupBFiles.map(file => URL.createObjectURL(file))];

        if (groupAVideos.length > 0 && groupAVideos.length === groupBVideos.length) {
            startEvalButtonCreator.disabled = false;
            evaluationPairs = groupAVideos.map((videoA, index) => ({ videoA, videoB: groupBVideos[index] }));
        } else {
            startEvalButtonCreator.disabled = true;
        }
    };

    // --- Event Listeners ---
    infoIcon.addEventListener('click', (e) => {
        e.stopPropagation();
        veoStudyDetails.classList.toggle('hidden');
    });
    
    participateButton.addEventListener('click', async (e) => {
        if (e.target !== infoIcon && !infoIcon.contains(e.target)) {
            veoStudyDetails.classList.add('hidden');
            const data = await fetchVeoYouTubeStudy();
            if (data && data.length > 0) {
                evaluationPairs = data;
                isPreloadedStudy = true;
                startEvaluation();
            }
        }
    });
    
    createButton.addEventListener('click', () => {
        veoStudyDetails.classList.add('hidden');
        showSection('setup-section');
    });
    
    backButtonCreator.addEventListener('click', resetState);
    backToChoiceButton.addEventListener('click', resetState);
    backToMenuFinal.addEventListener('click', resetState);
    
    document.getElementById('group-a-files').addEventListener('change', validateAndLoadCustomPairs);
    document.getElementById('group-a-urls').addEventListener('input', validateAndLoadCustomPairs);
    document.getElementById('group-b-files').addEventListener('change', validateAndLoadCustomPairs);
    document.getElementById('group-b-urls').addEventListener('input', validateAndLoadCustomPairs);

    startEvalButtonCreator.addEventListener('click', () => {
        isPreloadedStudy = false; // Make sure to set this flag
        startEvaluation();
    });
    submitButton.addEventListener('click', handleSubmit);
    previousButton.addEventListener('click', handlePrevious);
    
    resetState();
}