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

import { initGenerator, getGeneratorContent } from './features/generator.js';
import { initEnhancer, getEnhancerContent } from './features/enhancer.js';
import { initConverter, getConverterContent } from './features/converter.js';
import { initEval, getEvalContent } from './features/eval.js';
import { initAlignmentEval, getAlignmentEvalContent } from './features/alignment-eval.js';
import { initGallery, getGalleryContent } from './features/gallery.js';
import { initTimeline, getTimelineContent } from './features/timeline.js';

const mainContent = document.getElementById('main-content');
const authSectionContainer = document.getElementById('auth-section-container');

const tabs = {
    generator: { getContent: getGeneratorContent, init: initGenerator, needsAuth: true },
    enhancer: { getContent: getEnhancerContent, init: initEnhancer, needsAuth: true },
    converter: { getContent: getConverterContent, init: initConverter, needsAuth: true },
    'alignment-eval': { getContent: getAlignmentEvalContent, init: initAlignmentEval, needsAuth: true },
    eval: { getContent: getEvalContent, init: initEval, needsAuth: false },
    gallery: { getContent: getGalleryContent, init: initGallery, needsAuth: false },
    timeline: { getContent: getTimelineContent, init: initTimeline, needsAuth: true }
};

// Dark Mode Functions
function initDarkMode() {
    const themeToggleBtn = document.getElementById('theme-toggle');
    const lightIcon = document.getElementById('theme-toggle-light-icon');
    const darkIcon = document.getElementById('theme-toggle-dark-icon');
    
    if (!themeToggleBtn || !lightIcon || !darkIcon) {
        console.warn('Dark mode elements not found');
        return;
    }
    
    // Check for saved theme preference or default to light mode  
    const savedTheme = localStorage.getItem('theme');
    
    // Set initial theme - defaults to light mode
    let currentTheme = savedTheme || 'light';
    applyTheme(currentTheme);
    
    // Toggle theme function
    function toggleTheme() {
        currentTheme = currentTheme === 'light' ? 'dark' : 'light';
        applyTheme(currentTheme);
        localStorage.setItem('theme', currentTheme);
        
        // Show notification about theme change
        showNotification(`Switched to ${currentTheme} mode`, 'info', 2000);
    }
    
    // Apply theme function
    function applyTheme(theme) {
        const html = document.documentElement;
        const toggleBtn = document.getElementById('theme-toggle');
        
        if (theme === 'dark') {
            html.classList.add('dark');
            // In dark mode, show sun icon (click to go to light)
            lightIcon.style.display = 'block';
            darkIcon.style.display = 'none';
            if (toggleBtn) toggleBtn.title = 'Switch to light mode';
        } else {
            html.classList.remove('dark');
            // In light mode, show moon icon (click to go to dark)  
            lightIcon.style.display = 'none';
            darkIcon.style.display = 'block';
            if (toggleBtn) toggleBtn.title = 'Switch to dark mode';
        }
        
        // Update CSS custom properties for smoother transitions
        updateThemeProperties(theme);
    }
    
    // Update CSS custom properties
    function updateThemeProperties(theme) {
        const root = document.documentElement;
        
        if (theme === 'dark') {
            root.style.setProperty('--theme-bg', '#0f172a');
            root.style.setProperty('--theme-text', '#f1f5f9');
            root.style.setProperty('--theme-border', '#334155');
        } else {
            root.style.setProperty('--theme-bg', '#ffffff');
            root.style.setProperty('--theme-text', '#1e293b');
            root.style.setProperty('--theme-border', '#e2e8f0');
        }
    }
    

    
    // Add event listener to toggle button
    themeToggleBtn.addEventListener('click', toggleTheme);
    
    // Add smooth transition class after initial theme is set
    setTimeout(() => {
        document.body.classList.add('transition-colors', 'duration-300');
        
        // Add transitions to other elements
        const elementsToTransition = document.querySelectorAll('nav, .main-tab, input, textarea, select, button');
        elementsToTransition.forEach(element => {
            element.classList.add('transition-colors', 'duration-300');
        });
    }, 100);
    
    console.log(`Theme system initialized. Current theme: ${currentTheme} (defaults to light mode)`);
}

// This function is async to handle fetching HTML templates.
async function showMainTab(tabName) {
    const feature = tabs[tabName];
    if (!feature) {
        console.warn(`Tab ${tabName} not found`);
        return;
    }

    // Show/hide auth section based on feature needs
    authSectionContainer.style.display = feature.needsAuth ? 'block' : 'none';
    
    // Load tab content asynchronously.
    mainContent.innerHTML = await feature.getContent();
    feature.init();

    // Update active tab styling
    Object.keys(tabs).forEach(tabKey => {
        const tabEl = document.getElementById(`${tabKey}-main-tab`);
        if (tabEl) {
            tabEl.classList.toggle('main-tab-active', tabKey === tabName);
        }
    });
    
    // Add fade-in animation to content
    mainContent.classList.add('fade-in');
    setTimeout(() => {
        mainContent.classList.remove('fade-in');
    }, 500);
    
    console.log(`Switched to ${tabName} tab`);
}

// Fast validation using Gemini Flash model
async function validateAccessToken() {
    const accessToken = document.getElementById('access-token-input').value;
    const projectId = document.getElementById('project-id-input').value;
    const location = document.getElementById('location-input')?.value || 'us-central1';
    const statusElement = document.getElementById('access-token-status');
    const validateBtn = document.getElementById('validate-token-btn');
    const authMethod = document.getElementById('auth-method-select').value;

    // For API key mode, just do client-side check
    if (authMethod === 'api-key') {
        statusElement.textContent = '✅ Using server API key. Ready to generate!';
        statusElement.className = 'text-xs mt-2 h-4 text-blue-600 dark:text-blue-400';
        validateBtn.textContent = '✓ API Key Mode';
        setTimeout(() => {
            validateBtn.textContent = 'Validate';
        }, 2000);
        return;
    }

    // For access token mode, check fields first
    if (!projectId || !accessToken) {
        statusElement.textContent = 'Project ID and Token are required.';
        statusElement.className = 'text-xs mt-2 h-4 text-red-600 dark:text-red-400';
        return;
    }

    // Show loading state (should be quick with Flash)
    validateBtn.disabled = true;
    validateBtn.textContent = 'Validating...';
    validateBtn.classList.add('loading');
    statusElement.textContent = 'Checking credentials...';
    statusElement.className = 'text-xs mt-2 h-4 text-gray-500 dark:text-gray-400';
    
    try {
        const response = await fetch('/api/validate-token', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ projectId, accessToken, location })  
        });
        
        const result = await response.json();
        
        if (result.valid) {
            statusElement.textContent = '✅ ' + result.message;
            statusElement.className = 'text-xs mt-2 h-4 text-green-600 dark:text-green-400';
            validateBtn.textContent = '✓ Validated';
            validateBtn.classList.add('bg-green-600', 'hover:bg-green-700');
            showNotification(`Token validated for ${location}!`, 'success');
            
            setTimeout(() => {
                validateBtn.textContent = 'Validate';
                validateBtn.classList.remove('bg-green-600', 'hover:bg-green-700');
            }, 3000);
        } else {
            statusElement.textContent = `❌ ${result.message}`;
            statusElement.className = 'text-xs mt-2 h-4 text-red-600 dark:text-red-400';
            validateBtn.textContent = 'Retry';
            showNotification('Validation failed', 'error');
        }
    } catch (error) {
        console.error('Token validation error:', error);
        statusElement.textContent = 'Validation failed. Check server console.';
        statusElement.className = 'text-xs mt-2 h-4 text-red-600 dark:text-red-400';
        showNotification('Network error during validation', 'error');
    } finally {
        // Reset button state
        validateBtn.disabled = false;
        if (validateBtn.textContent === 'Validating...') {
            validateBtn.textContent = 'Validate';
        }
        validateBtn.classList.remove('loading');
    }
}

// Enhanced notification system with dark mode support
function showNotification(message, type = 'info', duration = 3000) {
    const toast = document.getElementById('notification-toast');
    
    if (!toast) {
        console.warn('Notification toast element not found');
        return;
    }
    
    // Clear any existing classes and timers
    clearTimeout(toast.hideTimer);
    toast.className = '';
    
    // Set the message
    toast.textContent = message;
    
    // Base classes for the toast
    const baseClasses = 'fixed bottom-20 left-1/2 transform -translate-x-1/2 px-6 py-3 rounded-full font-semibold text-sm shadow-lg transition-all duration-300 z-50';
    
    // Type-specific styling
    let typeClass = '';
    switch (type) {
        case 'success':
            typeClass = 'bg-green-500 text-white';
            break;
        case 'error':
            typeClass = 'bg-red-500 text-white';
            break;
        case 'warning':
            typeClass = 'bg-yellow-500 text-white';
            break;
        default:
            typeClass = 'bg-blue-500 text-white';
    }
    
    // Apply classes and show
    toast.className = `${baseClasses} ${typeClass} opacity-100 translate-y-0`;
    
    // Hide after duration
    toast.hideTimer = setTimeout(() => {
        toast.className = `${baseClasses} ${typeClass} opacity-0 translate-y-2`;
    }, duration);
    
    console.log(`Notification: ${message} (${type})`);
}

// Utility function to get current theme
function getCurrentTheme() {
    return document.documentElement.classList.contains('dark') ? 'dark' : 'light';
}

// Utility function to check if user prefers reduced motion
function prefersReducedMotion() {
    return window.matchMedia('(prefers-reduced-motion: reduce)').matches;
}

// Initialize keyboard shortcuts
function initKeyboardShortcuts() {
    document.addEventListener('keydown', (e) => {
        // Ctrl/Cmd + Shift + D to toggle dark mode
        if ((e.ctrlKey || e.metaKey) && e.shiftKey && e.key === 'D') {
            e.preventDefault();
            document.getElementById('theme-toggle')?.click();
        }
        
        // Ctrl/Cmd + 1-7 for tab switching
        if ((e.ctrlKey || e.metaKey) && e.key >= '1' && e.key <= '7') {
            e.preventDefault();
            const tabNames = Object.keys(tabs);
            const tabIndex = parseInt(e.key) - 1;
            if (tabNames[tabIndex]) {
                showMainTab(tabNames[tabIndex]);
            }
        }
    });
}

// Initialize animations based on user preference
function initAnimations() {
    if (prefersReducedMotion()) {
        document.documentElement.style.setProperty('--animation-duration', '0ms');
    }
}

// Main initialization function
document.addEventListener('DOMContentLoaded', () => {
    console.log('VeoStart application initializing...');
    
    // Get DOM elements
    const authMethodSelect = document.getElementById('auth-method-select');
    const apiKeySection = document.getElementById('api-key-auth-section');
    const accessTokenSection = document.getElementById('access-token-auth-section');
    const validateTokenBtn = document.getElementById('validate-token-btn');
    const authHeader = document.getElementById('auth-header');
    const authContent = document.getElementById('auth-content');
    const authChevron = document.getElementById('auth-chevron');

    // Initialize dark mode first
    initDarkMode();
    
    // Initialize animations
    initAnimations();
    
    // Initialize keyboard shortcuts
    initKeyboardShortcuts();

    // Collapsible auth section logic
    if (authHeader && authContent && authChevron) {
        authHeader.addEventListener('click', () => {
            const isHidden = authContent.classList.contains('hidden');
            authContent.classList.toggle('hidden');
            authChevron.classList.toggle('rotate-180');
            
            // Add smooth animation
            if (!prefersReducedMotion()) {
                authChevron.style.transform = isHidden ? 'rotate(0deg)' : 'rotate(180deg)';
            }
        });
    }

    // Auth method switching
    if (authMethodSelect && apiKeySection && accessTokenSection) {
        authMethodSelect.addEventListener('change', () => {
            const isApiKey = authMethodSelect.value === 'api-key';
            apiKeySection.style.display = isApiKey ? 'block' : 'none';
            accessTokenSection.style.display = isApiKey ? 'none' : 'block';
        });
    }

    // Token validation
    if (validateTokenBtn) {
        validateTokenBtn.addEventListener('click', validateAccessToken);
    }

    // Tab navigation
    Object.keys(tabs).forEach(tabKey => {
        const tabEl = document.getElementById(`${tabKey}-main-tab`);
        if (tabEl) {
            tabEl.addEventListener('click', () => showMainTab(tabKey));
        }
    });
    
    // Show default tab
    showMainTab('generator');
    
    // Welcome notification
    setTimeout(() => {
        const currentTheme = getCurrentTheme();
        showNotification(`Welcome to V-Start! Currently in ${currentTheme} mode. Press Ctrl+Shift+D to toggle theme.`, 'info', 5000);
    }, 1000);
    
    console.log('VeoStart application initialized successfully');
});

// Handle page visibility changes
document.addEventListener('visibilitychange', () => {
    if (!document.hidden) {
        // Refresh theme when page becomes visible again
        const savedTheme = localStorage.getItem('theme');
        if (savedTheme) {
            const html = document.documentElement;
            if (savedTheme === 'dark' && !html.classList.contains('dark')) {
                html.classList.add('dark');
            } else if (savedTheme === 'light' && html.classList.contains('dark')) {
                html.classList.remove('dark');
            }
        }
    }
});

// Export functions for use in other modules
export { showNotification, getCurrentTheme, showMainTab };