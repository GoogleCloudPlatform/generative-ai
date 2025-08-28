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

    const payload = {
        authMethod,
        accessToken,
        projectId,
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
