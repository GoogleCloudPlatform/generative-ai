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

export async function getEvalContent() {
    try {
        const response = await fetch('/src/features/templates/eval.html');
        if (!response.ok) {
            throw new Error(`Network response was not ok: ${response.statusText}`);
        }
        return await response.text();
    } catch (error) {
        console.error('Failed to fetch eval template:', error);
        return '<div>Error loading content. Please check the console for details.</div>';
    }
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
