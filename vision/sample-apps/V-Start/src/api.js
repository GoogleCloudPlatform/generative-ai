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
export async function callGeminiApi(systemPrompt, contentParts = []) {
    // Read the selected auth method and credentials from the global UI elements
    const authMethod = document.getElementById('auth-method-select').value;
    const accessToken = document.getElementById('access-token-input').value;
    const projectId = document.getElementById('project-id-input').value;
    
    // Get API key if using API key auth method
    let apiKey = null;
    if (authMethod === 'api-key') {
        const apiKeyInput = document.getElementById('api-key-input');
        if (apiKeyInput) {
            apiKey = apiKeyInput.value;
        }
        
        // Validate API key is provided
        if (!apiKey) {
            throw new Error('API Key is required. Please enter your Gemini API key.');
        }
    }
    
    const payload = {
        authMethod,
        accessToken,
        projectId,
        apiKey,  // Include API key in payload
        systemPrompt,
        contentParts
    };
    
    try {
        const response = await fetch('/api/generate', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(payload)
        });
        
        if (!response.ok) {
            const errorBody = await response.json();
            throw new Error(`API Error: ${errorBody.error || 'Unknown server error'}`);
        }
        
        const result = await response.json();
        return result.text;
    } catch (error) {
        console.error("Error calling backend service:", error);
        throw error;
    }
}

export async function validateCredentials() {
    const authMethod = document.getElementById('auth-method-select').value;
    const accessToken = document.getElementById('access-token-input').value;
    const projectId = document.getElementById('project-id-input').value;
    const location = document.getElementById('location-select')?.value || 'us-central1';
    
    // Get API key if using API key auth method
    let apiKey = null;
    if (authMethod === 'api-key') {
        const apiKeyInput = document.getElementById('api-key-input');
        if (apiKeyInput) {
            apiKey = apiKeyInput.value;
        }
        
        if (!apiKey) {
            return { valid: false, message: 'API Key is required for validation.' };
        }
    }
    
    const payload = {
        authMethod,
        accessToken,
        projectId,
        location,
        apiKey  // Include API key in validation payload
    };
    
    try {
        const response = await fetch('/api/validate-token', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(payload)
        });
        
        const result = await response.json();
        return result;
    } catch (error) {
        console.error("Error validating credentials:", error);
        return { valid: false, message: error.message };
    }
}