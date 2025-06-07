const API_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

export async function startAnalysis(request) {
  const response = await fetch(`${API_URL}/api/analyze`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
    },
    body: JSON.stringify(request),
  });

  if (!response.ok) {
    const error = await response.json();
    throw new Error(error.detail || "Failed to start analysis");
  }

  return response.json();
}

export async function getAnalysis(requestId) {
  const response = await fetch(`${API_URL}/api/analysis/${requestId}`);

  if (!response.ok) {
    const error = await response.json();
    throw new Error(error.detail || "Failed to get analysis");
  }

  return response.json();
}

export async function getMarkdown(requestId) {
  const response = await fetch(`${API_URL}/api/markdown/${requestId}`);

  if (!response.ok) {
    const error = await response.json();
    throw new Error(error.detail || "Failed to get markdown");
  }

  return response.json();
}
