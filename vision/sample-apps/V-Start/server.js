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

// 3. Token validation endpoint
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
    // We'll try to list models which is a read-only operation
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
            // Token is valid and has permissions
            res.json({ 
                valid: true, 
                message: 'Access Token is valid and has permissions!' 
            });
        } else if (response.status === 401) {
            // Token is invalid or expired
            res.json({ 
                valid: false, 
                message: 'Token is invalid or expired. Please run: gcloud auth print-access-token' 
            });
        } else if (response.status === 403) {
            // Token is valid but lacks permissions
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
        
        // Check if it's a network error
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

// 4. Main Gemini API proxy endpoint (handles both auth methods)
app.post('/api/generate', async (req, res) => {
    console.log('Generate endpoint called');
    const { authMethod, accessToken, projectId, systemPrompt, contentParts } = req.body;
    
    const model = 'gemini-2.5-pro';
    let apiUrl;
    const headers = { 'Content-Type': 'application/json' };
    
    if (authMethod === 'access-token') {
        if (!projectId || !accessToken) {
            return res.status(400).json({ error: "Project ID and Access Token are required for gcloud auth." });
        }
        apiUrl = `https://us-central1-aiplatform.googleapis.com/v1/projects/${projectId}/locations/us-central1/publishers/google/models/${model}:generateContent`;
        headers['Authorization'] = `Bearer ${accessToken}`;
        console.log('Using gcloud auth for project:', projectId);
    } else {
        const apiKey = process.env.API_KEY;
        if (!apiKey) {
            return res.status(500).json({ error: 'API Key is not configured on the server. Please check your .env file.' });
        }
        apiUrl = `https://generativelanguage.googleapis.com/v1beta/models/${model}:generateContent?key=${apiKey}`;
        console.log('Using API key auth');
    }
    
    const payload = {
        contents: [{
            role: "user",
            parts: [ ...contentParts, { text: systemPrompt } ]
        }]
    };
    
    try {
        const apiResponse = await fetch(apiUrl, {
            method: 'POST',
            headers: headers,
            body: JSON.stringify(payload)
        });
        
        const result = await apiResponse.json();
        
        if (!apiResponse.ok) {
            console.error('API Error:', result);
            return res.status(apiResponse.status).json({ error: result.error?.message || 'An unknown API error occurred.' });
        }
        
        const text = result.candidates?.[0]?.content?.parts?.[0]?.text || '';
        res.json({ text: text.trim() });
    } catch (error) {
        console.error('Server error:', error);
        res.status(500).json({ error: 'An internal server error occurred: ' + error.message });
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
        ]
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