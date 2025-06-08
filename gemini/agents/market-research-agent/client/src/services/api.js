// Get API URL from environment, with fallback for development
const getApiUrl = () => {
  if (typeof window !== 'undefined') {
    // Client-side
    return process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";
  }
  // Server-side
  return process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";
};

const API_URL = getApiUrl();

export async function startAnalysis(request) {
  try {
    const response = await fetch(`${API_URL}/api/analyze`, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
      },
      body: JSON.stringify(request),
    });

    if (!response.ok) {
      const error = await response.json().catch(() => ({ detail: 'Network error' }));
      throw new Error(error.detail || "Failed to start analysis");
    }

    return response.json();
  } catch (error) {
    console.error('API Error:', error);
    throw error;
  }
}

export async function getAnalysis(requestId) {
  try {
    const response = await fetch(`${API_URL}/api/analysis/${requestId}`);

    if (!response.ok) {
      const error = await response.json().catch(() => ({ detail: 'Network error' }));
      throw new Error(error.detail || "Failed to get analysis");
    }

    return response.json();
  } catch (error) {
    console.error('API Error:', error);
    throw error;
  }
}

export async function getMarkdown(requestId) {
  try {
    const response = await fetch(`${API_URL}/api/markdown/${requestId}`);

    if (!response.ok) {
      const error = await response.json().catch(() => ({ detail: 'Network error' }));
      throw new Error(error.detail || "Failed to get markdown");
    }

    return response.json();
  } catch (error) {
    console.error('API Error:', error);
    throw error;
  }
}

// Health check function
export async function healthCheck() {
  try {
    const response = await fetch(`${API_URL}/health`);
    return response.ok;
  } catch (error) {
    console.error('Health check failed:', error);
    return false;
  }
}