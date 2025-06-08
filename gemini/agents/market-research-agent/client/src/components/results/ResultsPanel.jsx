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

          if (data.status === "completed" || data.status === "failed") {
            clearInterval(intervalId);
            setLoading(false);

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

    fetchAnalysis();
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
      <div className="min-h-screen bg-gradient-to-br from-slate-50 to-blue-50 py-12">
        <div className="max-w-4xl mx-auto px-4">
          <Card>
            <div className="flex flex-col items-center py-16">
              <div className="relative">
                <div className="w-16 h-16 border-4 border-blue-200 border-t-blue-600 rounded-full animate-spin"></div>
                <div className="absolute inset-0 w-16 h-16 border-4 border-transparent border-r-blue-300 rounded-full animate-spin animation-delay-150"></div>
              </div>
              <h3 className="mt-6 text-lg font-semibold text-gray-900">{statusMessage}</h3>
              <p className="mt-2 text-sm text-gray-500 max-w-sm text-center">
                We're analyzing your data and generating AI use cases. This may take a few minutes.
              </p>
              <div className="mt-6 flex space-x-2">
                <div className="w-2 h-2 bg-blue-400 rounded-full animate-bounce"></div>
                <div className="w-2 h-2 bg-blue-400 rounded-full animate-bounce animation-delay-75"></div>
                <div className="w-2 h-2 bg-blue-400 rounded-full animate-bounce animation-delay-150"></div>
              </div>
            </div>
          </Card>
        </div>
      </div>
    );
  }

  if (error || (analysisData && analysisData.status === "failed")) {
    const errorMessage = error || analysisData?.error || "Analysis failed";

    return (
      <div className="min-h-screen bg-gradient-to-br from-slate-50 to-red-50 py-12">
        <div className="max-w-4xl mx-auto px-4">
          <Card>
            <div className="text-center py-16">
              <div className="w-20 h-20 mx-auto mb-6 bg-red-100 rounded-full flex items-center justify-center">
                <svg
                  xmlns="http://www.w3.org/2000/svg"
                  className="h-10 w-10 text-red-500"
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
              </div>
              <h3 className="text-2xl font-bold text-gray-900 mb-3">Analysis Failed</h3>
              <p className="text-gray-600 mb-8 max-w-md mx-auto">{errorMessage}</p>
              <Button
                variant="outline"
                onClick={() => (window.location.href = "/")}
                className="bg-white hover:bg-gray-50 border-2 border-gray-300 px-8 py-3 text-base font-medium">
                Start New Analysis
              </Button>
            </div>
          </Card>
        </div>
      </div>
    );
  }

  if (!analysisData || !analysisData.use_cases) {
    return (
      <div className="min-h-screen bg-gradient-to-br from-slate-50 to-gray-50 py-12">
        <div className="max-w-4xl mx-auto px-4">
          <Card>
            <div className="text-center py-16">
              <div className="w-20 h-20 mx-auto mb-6 bg-gray-100 rounded-full flex items-center justify-center">
                <svg className="w-10 h-10 text-gray-400" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
                </svg>
              </div>
              <h3 className="text-2xl font-bold text-gray-900 mb-3">No Results Available</h3>
              <p className="text-gray-600 mb-8 max-w-md mx-auto">No analysis data is available for this request.</p>
              <Button
                variant="outline"
                onClick={() => (window.location.href = "/")}
                className="bg-white hover:bg-gray-50 border-2 border-gray-300 px-8 py-3 text-base font-medium">
                Start New Analysis
              </Button>
            </div>
          </Card>
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-gradient-to-br from-slate-50 via-blue-50 to-indigo-50">
      <div className="max-w-7xl mx-auto px-12 py-16">
        {/* Header Section */}
        <div className="bg-white shadow-xl rounded-2xl overflow-hidden mb-8">
          <div className="bg-gradient-to-r from-blue-600 via-blue-700 to-indigo-700 px-4 py-4">
            <div className="flex items-center justify-between">
              <div>
                <h1 className="text-3xl font-bold text-white mb-2">
                  {analysisData.company_info?.name
                    ? `AI Use Cases for ${analysisData.company_info.name}`
                    : `AI Use Cases for ${analysisData.industry_info?.name || "Industry"}`}
                </h1>
                <p className="text-blue-100 text-lg">Discover AI opportunities tailored for your business</p>
              </div>
              <div className="flex gap-3">
                <Button
                  variant="outline"
                  onClick={() => setShowMarkdown(!showMarkdown)}
                  className="bg-white/10 border-white/20 text-white hover:bg-white/20 backdrop-blur-sm">
                  <svg className="w-4 h-4 mr-2" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d={showMarkdown ? "M4 6a2 2 0 012-2h2a2 2 0 012 2v2a2 2 0 01-2 2H6a2 2 0 01-2-2V6zM14 6a2 2 0 012-2h2a2 2 0 012 2v2a2 2 0 01-2 2h-2a2 2 0 01-2-2V6zM4 16a2 2 0 012-2h2a2 2 0 012 2v2a2 2 0 01-2 2H6a2 2 0 01-2-2v-2zM14 16a2 2 0 012-2h2a2 2 0 012 2v2a2 2 0 01-2 2h-2a2 2 0 01-2-2v-2z" : "M4 6h16M4 10h16M4 14h16M4 18h16"} />
                  </svg>
                  {showMarkdown ? "Show Cards" : "Show Markdown"}
                </Button>
                <Button
                  variant="outline"
                  onClick={() => {
                    if (markdown) {
                      const blob = new Blob([markdown], { type: "text/markdown" });
                      const url = URL.createObjectURL(blob);
                      const a = document.createElement("a");
                      a.href = url;
                      a.download = `use_cases_${requestId}.md`;
                      document.body.appendChild(a);
                      a.click();
                      document.body.removeChild(a);
                      URL.revokeObjectURL(url);
                    }
                  }}
                  className="bg-white/10 border-white/20 text-white hover:bg-white/20 backdrop-blur-sm">
                  <svg className="w-4 h-4 mr-2" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 10v6m0 0l-3-3m3 3l3-3m2 8H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
                  </svg>
                  Download Report
                </Button>
              </div>
            </div>
          </div>

          <div className="px-8 py-8">
            {showMarkdown && markdown ? (
              <div className="prose max-w-none">
                <div className="bg-gray-50 rounded-xl p-6 border border-gray-200">
                  <pre className="whitespace-pre-wrap break-words text-sm text-gray-800 font-mono leading-relaxed">
                    {markdown}
                  </pre>
                </div>
              </div>
            ) : (
              <div className="space-y-8">
                {/* Company Overview */}
                {analysisData.company_info && (
                  <div className="bg-gradient-to-r from-blue-50 to-indigo-50 rounded-xl p-6 border border-blue-100">
                    <h3 className="text-xl font-bold text-gray-900 mb-4 flex items-center">
                      <div className="w-8 h-8 bg-blue-100 rounded-lg flex items-center justify-center mr-3">
                        <svg className="w-5 h-5 text-blue-600" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 21V5a2 2 0 00-2-2H7a2 2 0 00-2 2v16m14 0h2m-2 0h-4m-5 0H3m2 0h4M9 7h1m-1 4h1m4-4h1m-1 4h1m-5 10v-5a1 1 0 011-1h2a1 1 0 011 1v5m-4 0h4" />
                        </svg>
                      </div>
                      Company Overview
                    </h3>
                    <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
                      <div className="lg:col-span-2">
                        <h4 className="text-sm font-semibold text-gray-600 uppercase tracking-wider mb-2">Description</h4>
                        <p className="text-gray-800 leading-relaxed">{analysisData.company_info.description}</p>
                      </div>
                      <div>
                        <h4 className="text-sm font-semibold text-gray-600 uppercase tracking-wider mb-2">Industry</h4>
                        <span className="inline-flex items-center px-3 py-1 rounded-2xl text-sm font-medium bg-blue-100 text-blue-800">
                          {analysisData.company_info.industry}
                        </span>
                      </div>
                      {analysisData.company_info.products && analysisData.company_info.products.length > 0 && (
                        <div>
                          <h4 className="text-sm font-semibold text-gray-600 uppercase tracking-wider mb-3">Products/Services</h4>
                          <div className="flex flex-wrap gap-2">
                            {analysisData.company_info.products.map((product, i) => (
                              <span key={i} className="inline-flex items-center px-3 py-1 rounded-full text-sm font-medium bg-green-100 text-green-800">
                                {product}
                              </span>
                            ))}
                          </div>
                        </div>
                      )}
                    </div>
                  </div>
                )}

                {/* Industry Insights */}
                {analysisData.industry_info && (
                  <div className="bg-gradient-to-r from-green-50 to-emerald-50 rounded-xl p-6 border border-green-100">
                    <h3 className="text-xl font-bold text-gray-900 mb-4 flex items-center">
                      <div className="w-8 h-8 bg-green-100 rounded-lg flex items-center justify-center mr-3">
                        <svg className="w-5 h-5 text-green-600" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13 7h8m0 0v8m0-8l-8 8-4-4-6 6" />
                        </svg>
                      </div>
                      Industry Insights
                    </h3>
                    <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
                      <div className="lg:col-span-2">
                        <h4 className="text-sm font-semibold text-gray-600 uppercase tracking-wider mb-2">Description</h4>
                        <p className="text-gray-800 leading-relaxed">{analysisData.industry_info.description}</p>
                      </div>
                      {analysisData.industry_info.trends && analysisData.industry_info.trends.length > 0 && (
                        <div>
                          <h4 className="text-sm font-semibold text-gray-600 uppercase tracking-wider mb-3">Current Trends</h4>
                          <div className="space-y-2">
                            {analysisData.industry_info.trends.map((trend, i) => (
                              <div key={i} className="flex items-center">
                                <div className="w-2 h-2 bg-green-400 rounded-full mr-3"></div>
                                <span className="text-gray-800">{trend}</span>
                              </div>
                            ))}
                          </div>
                        </div>
                      )}
                      {analysisData.industry_info.challenges && analysisData.industry_info.challenges.length > 0 && (
                        <div>
                          <h4 className="text-sm font-semibold text-gray-600 uppercase tracking-wider mb-3">Key Challenges</h4>
                          <div className="space-y-2">
                            {analysisData.industry_info.challenges.map((challenge, i) => (
                              <div key={i} className="flex items-center">
                                <div className="w-2 h-2 bg-amber-400 rounded-full mr-3"></div>
                                <span className="text-gray-800">{challenge}</span>
                              </div>
                            ))}
                          </div>
                        </div>
                      )}
                    </div>
                  </div>
                )}

                {/* Use Cases */}
                <div>
                  <div className="flex items-center justify-between mb-6">
                    <h3 className="text-2xl font-bold text-gray-900 flex items-center">
                      <div className="w-10 h-10 bg-gradient-to-r from-purple-500 to-pink-500 rounded-xl flex items-center justify-center mr-4">
                        <svg className="w-6 h-6 text-white" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9.663 17h4.673M12 3v1m6.364 1.636l-.707.707M21 12h-1M4 12H3m3.343-5.657l-.707-.707m2.828 9.9a5 5 0 117.072 0l-.548.547A3.374 3.374 0 0014 18.469V19a2 2 0 11-4 0v-.531c0-.895-.356-1.754-.988-2.386l-.548-.547z" />
                        </svg>
                      </div>
                      AI & Gen AI Use Cases
                    </h3>
                    <div className="text-sm text-gray-500 bg-gray-100 px-3 py-1 rounded-full">
                      {analysisData.use_cases.length} use cases identified
                    </div>
                  </div>
                  <div className="space-y-6">
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
              </div>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}