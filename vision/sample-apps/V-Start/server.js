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

const express = require('express');
const path = require('path');
const fs = require('fs');
const fetch = (...args) => import('node-fetch').then(({default: fetch}) => fetch(...args));

// Import the new Google Gen AI SDK
const { GoogleGenAI } = require('@google/genai');

require('dotenv').config();

const app = express();
const port = process.env.PORT || 8080;

// Rate limiting configuration
const rateLimits = new Map();
const RATE_LIMIT_WINDOW_MS = 60 * 60 * 1000; // 1 hour
const MAX_REQUESTS_PER_WINDOW = 50; // 50 requests per hour per IP

// Clean up old entries periodically (every hour)
setInterval(() => {
    const now = Date.now();
    for (const [ip, timestamps] of rateLimits.entries()) {
        const recentRequests = timestamps.filter(time => now - time < RATE_LIMIT_WINDOW_MS);
        if (recentRequests.length === 0) {
            rateLimits.delete(ip);
        } else {
            rateLimits.set(ip, recentRequests);
        }
    }
}, 60 * 60 * 1000);

// Rate limiting middleware
const rateLimitMiddleware = (req, res, next) => {
    // Skip rate limiting for static files and health checks
    if (req.path === '/api/health' || req.path === '/' || req.path.includes('.')) {
        return next();
    }

    const ip = req.headers['x-forwarded-for'] || req.ip;
    const now = Date.now();
    
    if (!rateLimits.has(ip)) {
        rateLimits.set(ip, []);
    }
    
    const requests = rateLimits.get(ip).filter(time => now - time < RATE_LIMIT_WINDOW_MS);
    
    if (requests.length >= MAX_REQUESTS_PER_WINDOW) {
        return res.status(429).json({ 
            error: `Rate limit exceeded. Maximum ${MAX_REQUESTS_PER_WINDOW} requests per hour.`,
            message: 'To use without limits, deploy your own instance: https://github.com/GoogleCloudPlatform/generative-ai/tree/main/vision/sample-apps/V-Start'
        });
    }
    
    requests.push(now);
    rateLimits.set(ip, requests);
    
    // Add rate limit headers
    res.setHeader('X-RateLimit-Limit', MAX_REQUESTS_PER_WINDOW);
    res.setHeader('X-RateLimit-Remaining', MAX_REQUESTS_PER_WINDOW - requests.length);
    res.setHeader('X-RateLimit-Reset', new Date(now + RATE_LIMIT_WINDOW_MS).toISOString());
    
    next();
};

// Middleware & Static File Serving
app.use(express.json({ limit: '50mb' }));
app.use(rateLimitMiddleware); // Apply rate limiting
app.use(express.static(path.join(__dirname)));

// --- API ENDPOINTS ---

// 1. Endpoint to securely load the YouTube study data from a private file
app.get('/api/study/veo-youtube-study', (req, res) => {
    const filePath = path.join(__dirname, 'data', 'veo-youtube-study.json');
    fs.readFile(filePath, 'utf8', (err, data) => {
        if (err) {
            console.error("Error reading study file:", err);
            return res.status(500).json({ error: "Could not load the study data." });
        }
        try {
            const jsonData = JSON.parse(data);
            res.json(jsonData);
        } catch (parseErr) {
            console.error("Error parsing study JSON:", parseErr);
            return res.status(500).json({ error: "Study data is corrupted." });
        }
    });
});

// 2. Endpoint to proxy video URLs to avoid CORS issues
app.get('/api/proxy-video', async (req, res) => {
    const videoUrl = req.query.url;
    if (!videoUrl) {
        return res.status(400).json({ error: 'URL query parameter is required.' });
    }

    try {
        const videoResponse = await fetch(videoUrl);
        
        if (!videoResponse.ok) {
            throw new Error(`Failed to fetch video with status: ${videoResponse.statusText}`);
        }

        const contentType = videoResponse.headers.get('content-type');
        if (contentType) res.setHeader('Content-Type', contentType);
        
        videoResponse.body.pipe(res);
    } catch (error) {
        console.error('Error proxying video:', error.message);
        res.status(500).json({ error: `Failed to proxy video. Reason: ${error.message}` });
    }
});

// 3. Fast validation endpoint using Gemini Flash model
app.post('/api/validate-token', async (req, res) => {
    const { projectId, accessToken, location, apiKey } = req.body;
    const validationLocation = location || 'us-central1';
    
    // Determine which validation path to use
    if (apiKey) {
        // API KEY VALIDATION PATH
        console.log('==========================================');
        console.log('API KEY VALIDATION STARTING');
        console.log('API Key length:', apiKey ? apiKey.length : 0);
        console.log('First 10 chars:', apiKey ? apiKey.substring(0, 10) + '...' : 'none');
        console.log('==========================================');
        
        // Check if API key looks valid (basic format check)
        if (!apiKey || apiKey.length < 20) {
            console.log('API key too short or missing');
            return res.json({ 
                valid: false, 
                message: 'Invalid API key format. Keys should be 39+ characters.' 
            });
        }
        
        try {
            console.log('Creating GoogleGenAI instance...');
            
            // Create AI instance with user-provided API key
            const ai = new GoogleGenAI({
                vertexai: false,
                apiKey: apiKey
            });
            
            console.log('GoogleGenAI instance created, attempting API call...');
            
            // Try to make a real API call to validate the key
            const response = await ai.models.generateContent({
                model: 'gemini-2.5-flash',
                contents: [{
                    role: "user",
                    parts: [{ text: "Say exactly: test" }]
                }],
                generationConfig: {
                    maxOutputTokens: 10,
                    temperature: 0
                }
            });
            
            console.log('API call completed, checking response...');
            console.log('Response object exists:', !!response);
            console.log('Response has text property:', !!response?.text);
            
            // Check if we actually got a valid response
            if (!response) {
                console.log('No response object received');
                throw new Error('No response from API');
            }
            
            const responseText = response.text;
            console.log('Response text:', responseText);
            
            // Check if the response is what we expect
            if (!responseText || responseText.length === 0) {
                console.log('Empty response text');
                throw new Error('Empty response from API');
            }
            
            console.log('✅ API KEY IS VALID');
            return res.json({ 
                valid: true, 
                message: 'API key validated successfully!' 
            });
            
        } catch (error) {
            console.log('==========================================');
            console.log('❌ VALIDATION ERROR CAUGHT');
            console.log('Error type:', error.constructor.name);
            console.log('Error message:', error.message);
            console.log('Error code:', error.code);
            console.log('Error status:', error.status);
            console.log('Full error:', error);
            console.log('==========================================');
            
            // Parse the error to provide a clean message
            let errorMessage = 'Invalid API key. Please check your key from Google AI Studio.';
            
            if (error.message?.includes('quota')) {
                errorMessage = 'API quota exceeded for this key.';
            } else if (error.message?.includes('API_KEY_INVALID')) {
                errorMessage = 'Invalid API key. Please verify your key from Google AI Studio.';
            }
            
            return res.json({ 
                valid: false, 
                message: errorMessage
            });
        }
        
    } else if (projectId && accessToken) {
        // ACCESS TOKEN VALIDATION PATH
        console.log(`Validating access token for project: ${projectId} in location: ${validationLocation}`);
        
        // Store original env variable to restore later
        const originalAuthToken = process.env.GOOGLE_AUTH_TOKEN;
        
        try {
            // Set access token temporarily
            process.env.GOOGLE_AUTH_TOKEN = accessToken;
            
            // Create AI instance with access token
            const ai = new GoogleGenAI({
                vertexai: true,
                project: projectId,
                location: validationLocation
            });
            
            // Try to make a real API call to validate credentials
            const response = await ai.models.generateContent({
                model: 'gemini-2.5-flash',
                contents: [{
                    role: "user",
                    parts: [{ text: "Say test" }]
                }],
                generationConfig: {
                    maxOutputTokens: 10,
                    temperature: 0
                }
            });
            
            // Check if we got a valid response
            const result = response.text;
            console.log('Access token validation successful, got response:', result);
            
            return res.json({ 
                valid: true, 
                message: 'Credentials validated successfully!' 
            });
            
        } catch (error) {
            console.error('Access token validation error:', error.message);
            
            return res.json({ 
                valid: false, 
                message: 'Invalid credentials. Please check your configuration.' 
            });
            
        } finally {
            // Always restore the original environment variable
            if (originalAuthToken !== undefined) {
                process.env.GOOGLE_AUTH_TOKEN = originalAuthToken;
            } else {
                delete process.env.GOOGLE_AUTH_TOKEN;
            }
        }
        
    } else {
        // Missing required fields
        return res.json({ 
            valid: false, 
            message: 'Please provide either an API key or Project ID with Access Token.' 
        });
    }
});

// 4. Main Gemini API proxy endpoint using SDK
app.post('/api/generate', async (req, res) => {
    const { authMethod, accessToken, projectId, location, systemPrompt, contentParts, apiKey } = req.body;
    const model = 'gemini-2.5-pro';

    try {
        let ai;
        let response;
        
        if (authMethod === 'access-token') {
            // === ACCESS TOKEN PATH ===
            if (!projectId || !accessToken) {
                return res.status(400).json({ 
                    error: "Project ID and Access Token are required for gcloud auth.",
                    validationError: true
                });
            }

            const vertexLocation = location || 'us-central1';
            
            // The SDK can use access tokens through environment variables
            // Store the original value to restore later
            const originalAuthToken = process.env.GOOGLE_AUTH_TOKEN;
            
            try {
                // Set the access token as environment variable for the SDK
                process.env.GOOGLE_AUTH_TOKEN = accessToken;
                
                // Initialize SDK with Vertex AI configuration
                ai = new GoogleGenAI({
                    vertexai: true,
                    project: projectId,
                    location: vertexLocation
                });
                
                // Build parts array
                const parts = [];
                
                // Add text prompt first
                if (systemPrompt) {
                    parts.push({ text: systemPrompt });
                }
                
                // Add any images/videos from contentParts
                if (contentParts && contentParts.length > 0) {
                    contentParts.forEach((part, index) => {
                        if (part.inlineData && part.inlineData.data && part.inlineData.mimeType) {
                            parts.push({
                                inlineData: {
                                    mimeType: part.inlineData.mimeType,
                                    data: part.inlineData.data
                                }
                            });
                        }
                    });
                }
                
                // Generate content using the SDK
                response = await ai.models.generateContent({
                    model: model,
                    contents: [{
                        role: "user",
                        parts: parts
                    }]
                });
                
                const text = response.text;
                res.json({ text: text.trim() });
                
            } finally {
                // Always restore the original environment variable
                if (originalAuthToken !== undefined) {
                    process.env.GOOGLE_AUTH_TOKEN = originalAuthToken;
                } else {
                    delete process.env.GOOGLE_AUTH_TOKEN;
                }
            }
            
        } else {
            // === API KEY PATH ===
            // API key must be provided by the user 
            if (!apiKey) {
                return res.status(400).json({ 
                    error: 'API Key is required. Please enter your Gemini API key.',
                    validationError: true
                });
            }
            
            // Initialize SDK with user-provided API key
            ai = new GoogleGenAI({
                vertexai: false,
                apiKey: apiKey
            });
            
            // Build parts array
            const parts = [];
            
            // Add text prompt first
            if (systemPrompt) {
                parts.push({ text: systemPrompt });
            }
            
            // Add any images/videos from contentParts
            if (contentParts && contentParts.length > 0) {
                contentParts.forEach((part, index) => {
                    if (part.inlineData && part.inlineData.data && part.inlineData.mimeType) {
                        parts.push({
                            inlineData: {
                                mimeType: part.inlineData.mimeType,
                                data: part.inlineData.data
                            }
                        });
                    }
                });
            }
            
            // Generate content using the SDK
            response = await ai.models.generateContent({
                model: model,
                contents: [{
                    role: "user",
                    parts: parts
                }]
            });
            
            const text = response.text;
            res.json({ text: text.trim() });
        }

    } catch (error) {
        console.error('Generation error:', error.message);
        
        // Use generic error message for validation errors
        if (error.message?.includes('401') || error.message?.includes('Unauthorized') || error.message?.includes('invalid')) {
            return res.status(401).json({ 
                error: 'Invalid credentials. Please check your configuration.',
                validationError: true
            });
        }
        
        if (error.message?.includes('API_KEY_INVALID')) {
            return res.status(401).json({ 
                error: 'Invalid credentials. Please check your configuration.',
                validationError: true
            });
        }
        
        if (error.message?.includes('403') || error.message?.includes('Permission denied')) {
            return res.status(403).json({ 
                error: 'Invalid credentials. Please check your configuration.',
                validationError: true
            });
        }
        
        if (error.message?.includes('404') || error.message?.includes('not found')) {
            return res.status(404).json({ 
                error: 'Invalid credentials. Please check your configuration.',
                validationError: true
            });
        }
        
        if (error.message?.includes('quota')) {
            return res.status(429).json({ 
                error: 'API quota exceeded. Please try again later.' 
            });
        }
        
        if (error.code === 'ENOTFOUND' || error.code === 'ECONNREFUSED') {
            return res.status(500).json({ 
                error: 'Cannot connect to Google services. Check your internet connection.',
                validationError: true
            });
        }
        
        res.status(500).json({ 
            error: 'An internal server error occurred: ' + error.message 
        });
    }
});

// Test endpoint to verify server is running
app.get('/api/health', (req, res) => {
    res.json({ 
        status: 'healthy', 
        timestamp: new Date().toISOString(),
        endpoints: [
            '/api/health',
            '/api/validate-token',  
            '/api/generate',
            '/api/proxy-video',
            '/api/study/veo-youtube-study'
        ],
        sdkVersion: {
            '@google/genai': require('@google/genai/package.json').version
        },
        rateLimit: {
            windowMs: RATE_LIMIT_WINDOW_MS,
            maxRequests: MAX_REQUESTS_PER_WINDOW
        }
    });
});

// Root route to serve index.html
app.get('/', (req, res) => {
    res.sendFile(path.join(__dirname, 'index.html'));
});

// --- Server Start ---
app.listen(port, '0.0.0.0', () => {
    console.log(`Server listening at http://localhost:${port}`);
    console.log('Configuration:');
    console.log('  Authentication: Users must provide their own API key or Access Token');
    console.log('  GOOGLE_CLOUD_PROJECT:', process.env.GOOGLE_CLOUD_PROJECT || 'Not set');
    console.log('  GOOGLE_CLOUD_LOCATION:', process.env.GOOGLE_CLOUD_LOCATION || 'Not set (will use UI selection)');
    console.log(`  Rate limiting: ${MAX_REQUESTS_PER_WINDOW} requests per hour per IP`);
});