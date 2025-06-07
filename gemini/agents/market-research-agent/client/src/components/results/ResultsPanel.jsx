import React, { useEffect, useState } from "react";
import Card from "../ui/Card";
import Loader from "../ui/Loader";
import UseCaseCard from "./UseCaseCard";
import Button from "../ui/Button";
import { getAnalysis, getMarkdown } from "../../services/api";

export default function ResultsPanel({ requestId }) {
  const [analysisData, setAnalysisData] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [markdown, setMarkdown] = useState(null);
  const [showMarkdown, setShowMarkdown] = useState(false);

  // Poll for analysis results
  useEffect(() => {
    let intervalId;
    let isMounted = true;

    const fetchAnalysis = async () => {
      try {
        const data = await getAnalysis(requestId);

        if (isMounted) {
          setAnalysisData(data);

          // If analysis is complete or failed, stop polling
          if (data.status === "completed" || data.status === "failed") {
            clearInterval(intervalId);
            setLoading(false);

            // If completed, fetch markdown
            if (data.status === "completed") {
              try {
                const markdownData = await getMarkdown(requestId);
                setMarkdown(markdownData.markdown);
              } catch (error) {
                console.error("Error fetching markdown:", error);
              }
            }
          }
        }
      } catch (error) {
        if (isMounted) {
          setError("Failed to fetch analysis results");
          clearInterval(intervalId);
          setLoading(false);
        }
      }
    };

    // Fetch immediately
    fetchAnalysis();

    // Then poll every 5 seconds
    intervalId = setInterval(fetchAnalysis, 5000);

    return () => {
      isMounted = false;
      clearInterval(intervalId);
    };
  }, [requestId]);

  if (
    loading &&
    (!analysisData ||
      analysisData.status === "pending" ||
      analysisData.status === "running")
  ) {
    const statusMessage = analysisData
      ? analysisData.status === "pending"
        ? "Initializing analysis..."
        : "Running analysis..."
      : "Loading...";

    return (
      <div className="py-12">
        <Card>
          <div className="flex flex-col items-center py-8">
            <Loader size="large" message={statusMessage} />
            <p className="mt-4 text-sm text-gray-500">
              This may take a few minutes
            </p>
          </div>
        </Card>
      </div>
    );
  }

  if (error || (analysisData && analysisData.status === "failed")) {
    const errorMessage = error || analysisData?.error || "Analysis failed";

    return (
      <div className="py-12">
        <Card>
          <div className="text-center py-8">
            <svg
              xmlns="http://www.w3.org/2000/svg"
              className="h-12 w-12 text-red-500 mx-auto"
              fill="none"
              viewBox="0 0 24 24"
              stroke="currentColor">
              <path
                strokeLinecap="round"
                strokeLinejoin="round"
                strokeWidth={2}
                d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z"
              />
            </svg>
            <h3 className="mt-4 text-lg font-medium text-gray-900">
              Analysis Failed
            </h3>
            <p className="mt-2 text-sm text-gray-500">{errorMessage}</p>
            <div className="mt-6">
              <Button
                variant="outline"
                onClick={() => (window.location.href = "/")}>
                Start New Analysis
              </Button>
            </div>
          </div>
        </Card>
      </div>
    );
  }

  if (!analysisData || !analysisData.use_cases) {
    return (
      <div className="py-12">
        <Card>
          <div className="text-center py-8">
            <h3 className="text-lg font-medium text-gray-900">
              No Results Available
            </h3>
            <p className="mt-2 text-sm text-gray-500">
              No analysis data is available
            </p>
            <div className="mt-6">
              <Button
                variant="outline"
                onClick={() => (window.location.href = "/")}>
                Start New Analysis
              </Button>
            </div>
          </div>
        </Card>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      <div className="bg-white shadow rounded-lg overflow-hidden">
        <div className="px-4 py-5 sm:px-6 border-b border-gray-200">
          <div className="flex items-center justify-between">
            <h2 className="text-xl font-bold text-gray-900">
              {analysisData.company_info?.name
                ? `AI Use Cases for ${analysisData.company_info.name}`
                : `AI Use Cases for ${analysisData.industry_info?.name || "Industry"}`}
            </h2>
            <div>
              <Button
                variant="outline"
                onClick={() => setShowMarkdown(!showMarkdown)}
                className="mr-2">
                {showMarkdown ? "Show Cards" : "Show Markdown"}
              </Button>
              <Button
                variant="outline"
                onClick={() => {
                  if (markdown) {
                    const blob = new Blob([markdown], {
                      type: "text/markdown",
                    });
                    const url = URL.createObjectURL(blob);
                    const a = document.createElement("a");
                    a.href = url;
                    a.download = `use_cases_${requestId}.md`;
                    document.body.appendChild(a);
                    a.click();
                    document.body.removeChild(a);
                    URL.revokeObjectURL(url);
                  }
                }}>
                Download Markdown
              </Button>
            </div>
          </div>
        </div>
        <div className="px-4 py-5 sm:p-6">
          {showMarkdown && markdown ? (
            <div className="prose max-w-none">
              <pre className="whitespace-pre-wrap break-words bg-gray-50 p-4 rounded border border-gray-200 text-sm">
                {markdown}
              </pre>
            </div>
          ) : (
            <div>
              {analysisData.company_info && (
                <div className="mb-6">
                  <h3 className="text-lg font-medium text-gray-900">
                    Company Overview
                  </h3>
                  <div className="mt-2 grid grid-cols-1 gap-x-4 gap-y-2 sm:grid-cols-2">
                    <div className="sm:col-span-2">
                      <span className="text-sm font-medium text-gray-500">
                        Description:
                      </span>
                      <p className="mt-1 text-sm text-gray-900">
                        {analysisData.company_info.description}
                      </p>
                    </div>
                    <div>
                      <span className="text-sm font-medium text-gray-500">
                        Industry:
                      </span>
                      <p className="mt-1 text-sm text-gray-900">
                        {analysisData.company_info.industry}
                      </p>
                    </div>
                    {analysisData.company_info.products &&
                      analysisData.company_info.products.length > 0 && (
                        <div>
                          <span className="text-sm font-medium text-gray-500">
                            Products/Services:
                          </span>
                          <ul className="mt-1 text-sm text-gray-900 list-disc list-inside">
                            {analysisData.company_info.products.map(
                              (product, i) => (
                                <li key={i}>{product}</li>
                              ),
                            )}
                          </ul>
                        </div>
                      )}
                  </div>
                </div>
              )}

              {analysisData.industry_info && (
                <div className="mb-6">
                  <h3 className="text-lg font-medium text-gray-900">
                    Industry Insights
                  </h3>
                  <div className="mt-2 grid grid-cols-1 gap-x-4 gap-y-2 sm:grid-cols-2">
                    <div className="sm:col-span-2">
                      <span className="text-sm font-medium text-gray-500">
                        Description:
                      </span>
                      <p className="mt-1 text-sm text-gray-900">
                        {analysisData.industry_info.description}
                      </p>
                    </div>
                    {analysisData.industry_info.trends &&
                      analysisData.industry_info.trends.length > 0 && (
                        <div>
                          <span className="text-sm font-medium text-gray-500">
                            Trends:
                          </span>
                          <ul className="mt-1 text-sm text-gray-900 list-disc list-inside">
                            {analysisData.industry_info.trends.map(
                              (trend, i) => (
                                <li key={i}>{trend}</li>
                              ),
                            )}
                          </ul>
                        </div>
                      )}
                    {analysisData.industry_info.challenges &&
                      analysisData.industry_info.challenges.length > 0 && (
                        <div>
                          <span className="text-sm font-medium text-gray-500">
                            Challenges:
                          </span>
                          <ul className="mt-1 text-sm text-gray-900 list-disc list-inside">
                            {analysisData.industry_info.challenges.map(
                              (challenge, i) => (
                                <li key={i}>{challenge}</li>
                              ),
                            )}
                          </ul>
                        </div>
                      )}
                  </div>
                </div>
              )}

              <div className="mt-8">
                <h3 className="text-lg font-medium text-gray-900 mb-4">
                  AI and GenAI Use Cases
                </h3>
                {analysisData.use_cases.map((useCase, index) => (
                  <UseCaseCard
                    key={index}
                    useCase={useCase}
                    resources={analysisData.resources?.[useCase.title]}
                    index={index}
                  />
                ))}
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
