/**
 * Calls the given Gemini model with the given image and/or text
 * parts, streaming output (as a generator function).
 */


export function callGemini({model = 'gemini-1.5-pro', contents = [] } = {}) {
  return fetch('/api/trialGenerate', {
    method: 'POST',
    headers: {'content-type': 'application/json'},
    body: JSON.stringify({ model, contents })
  })
  .then(response => {
    if (!response.ok) {
      throw new Error('Network response was not ok');
    }
    return response.json();
  })
  .then(data => {
    return data.response; // Return the generated text from Gemini
  })
  .catch(error => {
    console.error('Error:', error);
    throw error; // Re-throw the error to be handled by the caller
  });
}



