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

// Import Google AI SDK (only for API key auth)
const { GoogleGenerativeAI } = require('@google/generative-ai');

require('dotenv').config();

const app = express();
const port = process.env.PORT || 8080;

// Middleware & Static File Serving
app.use(express.json({ limit: '50mb' }));
app.use(express.static(path.join(__dirname))); // Serves files like index.html, src/, etc.

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

// 2. Endpoint to proxy video URLs to avoid CORS issues for user-created studies
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

// 3. Token validation endpoint (still using fetch for validation)
app.post('/api/validate-token', async (req, res) => {
    const { projectId, accessToken } = req.body;
    console.log('Validating token for project:', projectId);

    if (!projectId || !accessToken) {
        return res.status(400).json({ 
            valid: false, 
            message: 'Project ID and Token are required.' 
        });
    }

    // Use a simple endpoint to validate the token
    const validationUrl = `https://us-central1-aiplatform.googleapis.com/v1/projects/${projectId}/locations/us-central1/models`;

    try {
        console.log('Making validation request to:', validationUrl);
        const response = await fetch(validationUrl, {
            method: 'GET',
            headers: {
                'Authorization': `Bearer ${accessToken}`,
                'Content-Type': 'application/json'
            }
        });

        console.log('Validation response status:', response.status);

        if (response.ok) {
            res.json({ 
                valid: true, 
                message: 'Access Token is valid and has permissions!' 
            });
        } else if (response.status === 401) {
            res.json({ 
                valid: false, 
                message: 'Token is invalid or expired. Please run: gcloud auth print-access-token' 
            });
        } else if (response.status === 403) {
            res.json({ 
                valid: false, 
                message: 'Token is valid but lacks permissions. Ensure Vertex AI API is enabled.' 
            });
        } else {
            const errorData = await response.text();
            console.error('Validation error response:', errorData);
            res.json({ 
                valid: false, 
                message: `Validation failed with status ${response.status}` 
            });
        }
    } catch (error) {
        console.error('Validation error:', error);
        
        if (error.code === 'ENOTFOUND' || error.code === 'ECONNREFUSED') {
            res.status(500).json({ 
                valid: false, 
                message: 'Cannot connect to Google Cloud. Check your internet connection.' 
            });
        } else {
            res.status(500).json({ 
                valid: false, 
                message: 'Server error during validation: ' + error.message 
            });
        }
    }
});

// 4. Main Gemini API proxy endpoint (hybrid approach)
app.post('/api/generate', async (req, res) => {
    console.log('Generate endpoint called');
    const { authMethod, accessToken, projectId, systemPrompt, contentParts } = req.body;
    const model = 'gemini-2.5-pro';

    try {
        if (authMethod === 'access-token') {
            // Use manual HTTP call for access token auth 
            if (!projectId || !accessToken) {
                return res.status(400).json({ 
                    error: "Project ID and Access Token are required for gcloud auth." 
                });
            }

            console.log('Using manual HTTP call with access token for project:', projectId);
            
            const apiUrl = `https://us-central1-aiplatform.googleapis.com/v1/projects/${projectId}/locations/us-central1/publishers/google/models/${model}:generateContent`;
            
            const payload = {
                contents: [{
                    role: "user",
                    parts: [
                        ...contentParts,
                        { text: systemPrompt }
                    ]
                }]
            };

            const apiResponse = await fetch(apiUrl, {
                method: 'POST',
                headers: {
                    'Authorization': `Bearer ${accessToken}`,
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify(payload)
            });

            const result = await apiResponse.json();

            if (!apiResponse.ok) {
                console.error('Vertex AI API Error:', result);
                
                // Handle specific error cases
                if (apiResponse.status === 401) {
                    return res.status(401).json({ 
                        error: 'Authentication failed. Please run: gcloud auth print-access-token' 
                    });
                }
                
                if (apiResponse.status === 403) {
                    return res.status(403).json({ 
                        error: 'Permission denied. Ensure Vertex AI API is enabled for your project.' 
                    });
                }

                return res.status(apiResponse.status).json({ 
                    error: result.error?.message || 'An unknown API error occurred.' 
                });
            }

            const text = result.candidates?.[0]?.content?.parts?.[0]?.text || '';
            res.json({ text: text.trim() });

        } else {
            // Use Google AI SDK for API key auth
            const apiKey = process.env.API_KEY;
            if (!apiKey) {
                return res.status(500).json({ 
                    error: 'API Key is not configured on the server. Please check your .env file.' 
                });
            }

            console.log('Using Google AI SDK with API key');
            
            const generativeAIClient = new GoogleGenerativeAI(apiKey);
            const generativeModel = generativeAIClient.getGenerativeModel({ model: model });

            // Prepare the content parts
            const parts = [
                ...contentParts,
                { text: systemPrompt }
            ];

            // Generate content using the SDK
            const result = await generativeModel.generateContent({
                contents: [{
                    role: "user",
                    parts: parts
                }]
            });

            const response = await result.response;
            const text = response.text();

            res.json({ text: text.trim() });
        }

    } catch (error) {
        console.error('Generation error:', error);

        // Handle specific error types
        if (error.message?.includes('API_KEY_INVALID')) {
            return res.status(401).json({ 
                error: 'Invalid API key. Please check your .env configuration.' 
            });
        }

        if (error.message?.includes('quota')) {
            return res.status(429).json({ 
                error: 'API quota exceeded. Please try again later.' 
            });
        }

        if (error.code === 'ENOTFOUND' || error.code === 'ECONNREFUSED') {
            return res.status(500).json({ 
                error: 'Cannot connect to Google services. Check your internet connection.' 
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
            googleGenerativeAI: require('@google/generative-ai/package.json').version
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
    console.log('API_KEY configured for fallback:', !!process.env.API_KEY);
    console.log('Available endpoints:');
    console.log('  GET  /api/health');
    console.log('  POST /api/validate-token');
    console.log('  POST /api/generate');
    console.log('  GET  /api/proxy-video');
    console.log('  GET  /api/study/veo-youtube-study');
});

