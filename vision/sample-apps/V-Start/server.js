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

// Middleware & Static File Serving
app.use(express.json({ limit: '50mb' }));
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
        console.log(`Proxying video from: ${videoUrl}`);
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
    const { projectId, accessToken, location } = req.body;
    const validationLocation = location || 'us-central1';
    console.log(`Fast validation using Flash for project: ${projectId} in location: ${validationLocation}`);

    if (projectId && !accessToken) {
        return res.status(400).json({ 
            valid: false, 
            message: 'Access Token is required for validation.' 
        });
    }

    // Store original env variable to restore later
    const originalAuthToken = process.env.GOOGLE_AUTH_TOKEN;
    
    try {
        let ai;
        
        if (accessToken) {
            // Access token validation
            process.env.GOOGLE_AUTH_TOKEN = accessToken;
            
            ai = new GoogleGenAI({
                vertexai: true,
                project: projectId,
                location: validationLocation
            });
        } else {
            // API key validation
            const apiKey = process.env.API_KEY || process.env.GEMINI_API_KEY;
            if (!apiKey) {
                return res.json({ 
                    valid: false, 
                    message: 'No API key configured on server.' 
                });
            }
            
            ai = new GoogleGenAI({
                vertexai: false,
                apiKey: apiKey
            });
        }
        
        console.log('Running fast validation with gemini-2.0-flash...');
        
        // Use Flash model for much faster validation
        const response = await ai.models.generateContent({
            model: 'gemini-2.5-flash',  
            contents: [{
                role: "user",
                parts: [{ text: "1+1" }]  // Minimal math question
            }],
            generationConfig: {
                maxOutputTokens: 1,
                temperature: 0
            }
        });
        
        // If we get here, credentials are valid
        console.log('Flash validation successful');
        res.json({ 
            valid: true, 
            message: 'Credentials validated successfully!' 
        });
        
    } catch (error) {
        console.error('Validation error:', error.message);
        
        // Use a generic error message for all credential-related failures
        res.json({ 
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
});

// 4. Main Gemini API proxy endpoint using SDK
app.post('/api/generate', async (req, res) => {
    console.log('========== Generate endpoint called ==========');
    const { authMethod, accessToken, projectId, location, systemPrompt, contentParts } = req.body;
    const model = 'gemini-2.5-pro';  

    // Debug logging
    console.log('Request received with:', {
        authMethod,
        hasToken: !!accessToken,
        hasProjectId: !!projectId,
        location: location || 'us-central1',
        systemPromptLength: systemPrompt?.length || 0,
        contentPartsCount: contentParts?.length || 0
    });

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
            console.log(`Using Gen AI SDK with access token for project: ${projectId} in location: ${vertexLocation}`);
            
            // The SDK can use access tokens through environment variables
            // Store the original value to restore later
            const originalAuthToken = process.env.GOOGLE_AUTH_TOKEN;
            
            try {
                // Set the access token as environment variable for the SDK
                process.env.GOOGLE_AUTH_TOKEN = accessToken;
                
                // Initialize SDK with Vertex AI configuration
                // The SDK will automatically use the GOOGLE_AUTH_TOKEN we just set
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
                    console.log('Added system prompt to parts');
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
                            console.log(`Added media to parts: ${part.inlineData.mimeType}`);
                        }
                    });
                }
                
                console.log(`Sending ${parts.length} parts via SDK to Vertex AI in ${vertexLocation}`);
                
                // Generate content using the SDK
                response = await ai.models.generateContent({
                    model: model,
                    contents: [{
                        role: "user",
                        parts: parts
                    }]
                });
                
                const text = response.text;
                console.log('Response received, text length:', text.length);
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
            const apiKey = process.env.API_KEY || process.env.GEMINI_API_KEY;
            if (!apiKey) {
                return res.status(500).json({ 
                    error: 'API Key is not configured on the server. Please check your .env file.',
                    validationError: true
                });
            }

            console.log('Using Gen AI SDK with API key');
            
            // Initialize SDK with API key
            ai = new GoogleGenAI({
                vertexai: false,
                apiKey: apiKey
            });
            
            // Build parts array
            const parts = [];
            
            // Add text prompt first
            if (systemPrompt) {
                parts.push({ text: systemPrompt });
                console.log('Added system prompt to parts');
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
                        console.log(`Added media to parts: ${part.inlineData.mimeType}`);
                    }
                });
            }
            
            console.log(`Sending ${parts.length} parts via SDK to Gemini API`);
            
            // Generate content using the SDK
            response = await ai.models.generateContent({
                model: model,
                contents: [{
                    role: "user",
                    parts: parts
                }]
            });
            
            const text = response.text;
            console.log('Response received, text length:', text.length);
            res.json({ text: text.trim() });
        }

    } catch (error) {
        console.error('Generation error:', error);
        
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
    console.log('Environment variables configured:');
    console.log('  API_KEY/GEMINI_API_KEY:', !!(process.env.API_KEY || process.env.GEMINI_API_KEY));
    console.log('  GOOGLE_CLOUD_PROJECT:', process.env.GOOGLE_CLOUD_PROJECT || 'Not set');
    console.log('  GOOGLE_CLOUD_LOCATION:', process.env.GOOGLE_CLOUD_LOCATION || 'Not set (will use UI selection)');
});