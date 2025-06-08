import React, { useState } from "react";
import Card from "../ui/Card";

export default function UseCaseCard({ useCase, resources, index }) {
  const [isExpanded, setIsExpanded] = useState(false);
  
  const complexityConfig = {
    Low: { 
      color: "bg-emerald-100 text-emerald-700 border-emerald-200", 
      gradient: "from-emerald-50 to-green-50",
      icon: "🟢",
      textColor: "text-emerald-800"
    },
    Medium: { 
      color: "bg-amber-100 text-amber-700 border-amber-200", 
      gradient: "from-amber-50 to-yellow-50",
      icon: "🟡",
      textColor: "text-amber-800"
    },
    High: { 
      color: "bg-rose-100 text-rose-700 border-rose-200", 
      gradient: "from-rose-50 to-red-50",
      icon: "🔴",
      textColor: "text-rose-800"
    }
  };

  const complexity = complexityConfig[useCase.implementation_complexity] || complexityConfig.Medium;

  return (
    <div className="group">
      <Card className="hover:shadow-xl transition-all duration-300 transform hover:-translate-y-1 border-0 shadow-lg">
        <div className="overflow-hidden">
          {/* Header with gradient background */}
          <div className={`bg-gradient-to-r ${complexity.gradient} px-6 py-5 border-b border-gray-100`}>
            <div className="flex items-start justify-between">
              <div className="flex items-start space-x-4 flex-1">
                <div className="flex-shrink-0">
                  <div className="w-12 h-12 bg-white rounded-xl shadow-sm flex items-center justify-center border border-gray-200">
                    <span className="text-lg font-bold text-gray-700">
                      {String(index + 1).padStart(2, '0')}
                    </span>
                  </div>
                </div>
                <div className="flex-1 min-w-0">
                  <h3 className="text-xl font-bold text-gray-900 leading-tight mb-2">
                    {useCase.title}
                  </h3>
                  <p className="text-gray-700 leading-relaxed">{useCase.description}</p>
                </div>
              </div>
              
              {useCase.priority_score && (
                <div className="flex-shrink-0 ml-4">
                  <div className="bg-white rounded-xl px-4 py-2 shadow-sm border border-gray-200">
                    <div className="flex items-center space-x-2">
                      <svg className="w-4 h-4 text-yellow-500 fill-current" viewBox="0 0 20 20">
                        <path d="M9.049 2.927c.3-.921 1.603-.921 1.902 0l1.07 3.292a1 1 0 00.95.69h3.462c.969 0 1.371 1.24.588 1.81l-2.8 2.034a1 1 0 00-.364 1.118l1.07 3.292c.3.921-.755 1.688-1.54 1.118l-2.8-2.034a1 1 0 00-1.175 0l-2.8 2.034c-.784.57-1.838-.197-1.539-1.118l1.07-3.292a1 1 0 00-.364-1.118L2.98 8.72c-.783-.57-.38-1.81.588-1.81h3.461a1 1 0 00.951-.69l1.07-3.292z" />
                      </svg>
                      <span className="text-sm font-bold text-gray-800">
                        {useCase.priority_score}/10
                      </span>
                    </div>
                    <p className="text-xs text-gray-500 mt-1">Priority Score</p>
                  </div>
                </div>
              )}
            </div>
          </div>

          {/* Content */}
          <div className="p-6">
            {/* Key Metrics */}
            <div className="grid grid-cols-1 md:grid-cols-2 gap-6 mb-6">
              <div className="space-y-4">
                <div>
                  <h4 className="text-sm font-semibold text-gray-600 uppercase tracking-wider mb-3">Business Impact</h4>
                  <div className="bg-blue-50 border border-blue-200 rounded-lg p-4">
                    <div className="flex items-start">
                      <div className="flex-shrink-0">
                        <div className="w-8 h-8 bg-blue-100 rounded-full flex items-center justify-center">
                          <svg className="w-4 h-4 text-blue-600" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 8c-1.657 0-3 .895-3 2s1.343 2 3 2 3 .895 3 2-1.343 2-3 2m0-8c1.11 0 2.08.402 2.599 1M12 8V7m0 1v8m0 0v1m0-1c-1.11 0-2.08-.402-2.599-1" />
                          </svg>
                        </div>
                      </div>
                      <div className="ml-3">
                        <p className="text-blue-800 font-medium">{useCase.business_value}</p>
                      </div>
                    </div>
                  </div>
                </div>

                {useCase.prioritization_rationale && (
                  <div>
                    <h4 className="text-sm font-semibold text-gray-600 uppercase tracking-wider mb-3">Why This Matters</h4>
                    <div className="bg-purple-50 border border-purple-200 rounded-lg p-4">
                      <p className="text-purple-800">{useCase.prioritization_rationale}</p>
                    </div>
                  </div>
                )}
              </div>

              <div className="space-y-4">
                <div>
                  <h4 className="text-sm font-semibold text-gray-600 uppercase tracking-wider mb-3">Implementation</h4>
                  <div className="space-y-3">
                    <div className="flex items-center justify-between p-3 bg-gray-50 rounded-lg">
                      <span className="text-sm font-medium text-gray-700">Complexity</span>
                      <div className="flex items-center space-x-2">
                        <span className="text-lg">{complexity.icon}</span>
                        <span className={`px-3 py-1 rounded-full text-xs font-semibold border ${complexity.color}`}>
                          {useCase.implementation_complexity}
                        </span>
                      </div>
                    </div>
                  </div>
                </div>

                <div>
                  <h4 className="text-sm font-semibold text-gray-600 uppercase tracking-wider mb-3">AI Technologies</h4>
                  <div className="flex flex-wrap gap-2">
                    {useCase.ai_technologies.slice(0, 3).map((tech, i) => (
                      <span key={i} className="px-3 py-1.5 bg-indigo-100 text-indigo-700 rounded-lg text-sm font-medium border border-indigo-200">
                        {tech}
                      </span>
                    ))}
                    {useCase.ai_technologies.length > 3 && (
                      <span className="px-3 py-1.5 bg-gray-100 text-gray-700 rounded-lg text-sm font-medium border border-gray-200">
                        +{useCase.ai_technologies.length - 3} more
                      </span>
                    )}
                  </div>
                </div>
              </div>
            </div>

            {/* Expand/Collapse */}
            <div className="border-t border-gray-100 pt-4">
              <button
                onClick={() => setIsExpanded(!isExpanded)}
                className="w-full flex items-center justify-center space-x-2 py-3 text-sm font-medium text-gray-600 hover:text-gray-900 transition-colors duration-200 rounded-lg hover:bg-gray-50"
              >
                <span>{isExpanded ? 'Show Less Details' : 'Show More Details'}</span>
                <svg 
                  className={`w-4 h-4 transition-transform duration-200 ${isExpanded ? 'rotate-180' : ''}`} 
                  fill="none" 
                  viewBox="0 0 24 24" 
                  stroke="currentColor"
                >
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 9l-7 7-7-7" />
                </svg>
              </button>
            </div>

            {/* Expanded Content */}
            {isExpanded && (
              <div className="mt-6 space-y-6 border-t border-gray-100 pt-6">
                {/* All Technologies */}
                <div>
                  <h4 className="text-sm font-semibold text-gray-900 mb-3">Complete Technology Stack</h4>
                  <div className="flex flex-wrap gap-2">
                    {useCase.ai_technologies.map((tech, i) => (
                      <span key={i} className="px-3 py-2 bg-indigo-100 text-indigo-700 rounded-lg text-sm font-medium border border-indigo-200">
                        {tech}
                      </span>
                    ))}
                  </div>
                </div>

                {/* Keywords */}
                {useCase.keywords && useCase.keywords.length > 0 && (
                  <div>
                    <h4 className="text-sm font-semibold text-gray-900 mb-3">Related Keywords</h4>
                                  <div className="flex flex-wrap gap-2">
                      {useCase.keywords.map((keyword, i) => (
                        <span key={i} className="px-2 py-1 bg-gray-100 text-gray-700 rounded-md text-xs font-medium border border-gray-200">
                          {keyword}
                        </span>
                      ))}
                    </div>
                  </div>
                )}

                {/* Resources */}
                {resources && (
                  <div>
                    <h4 className="text-sm font-semibold text-gray-900 mb-3">Additional Resources</h4>
                    <div className="space-y-3">
                      {resources.articles && resources.articles.length > 0 && (
                        <div>
                          <h5 className="text-xs font-semibold text-gray-600 uppercase tracking-wider mb-2">Articles</h5>
                          <div className="space-y-2">
                            {resources.articles.map((article, i) => (
                              <div key={i} className="flex items-start space-x-3 p-3 bg-blue-50 rounded-lg border border-blue-100">
                                <div className="flex-shrink-0 mt-0.5">
                                  <svg className="w-4 h-4 text-blue-600" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 6.253v13m0-13C10.832 5.477 9.246 5 7.5 5S4.168 5.477 3 6.253v13C4.168 18.477 5.754 18 7.5 18s3.332.477 4.5 1.253m0-13C13.168 5.477 14.754 5 16.5 5c1.746 0 3.332.477 4.5 1.253v13C20.832 18.477 19.246 18 17.5 18c-1.746 0-3.332.477-4.5 1.253" />
                                  </svg>
                                </div>
                                <div className="flex-1">
                                  <a 
                                    href={article.url} 
                                    target="_blank" 
                                    rel="noopener noreferrer"
                                    className="text-blue-800 hover:text-blue-900 font-medium text-sm hover:underline"
                                  >
                                    {article.title}
                                  </a>
                                  {article.description && (
                                    <p className="text-blue-700 text-xs mt-1">{article.description}</p>
                                  )}
                                </div>
                              </div>
                            ))}
                          </div>
                        </div>
                      )}

                      {resources.tools && resources.tools.length > 0 && (
                        <div>
                          <h5 className="text-xs font-semibold text-gray-600 uppercase tracking-wider mb-2">Tools & Platforms</h5>
                          <div className="space-y-2">
                            {resources.tools.map((tool, i) => (
                              <div key={i} className="flex items-start space-x-3 p-3 bg-green-50 rounded-lg border border-green-100">
                                <div className="flex-shrink-0 mt-0.5">
                                  <svg className="w-4 h-4 text-green-600" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M10.325 4.317c.426-1.756 2.924-1.756 3.35 0a1.724 1.724 0 002.573 1.066c1.543-.94 3.31.826 2.37 2.37a1.724 1.724 0 001.065 2.572c1.756.426 1.756 2.924 0 3.35a1.724 1.724 0 00-1.066 2.573c.94 1.543-.826 3.31-2.37 2.37a1.724 1.724 0 00-2.572 1.065c-.426 1.756-2.924 1.756-3.35 0a1.724 1.724 0 00-2.573-1.066c-1.543.94-3.31-.826-2.37-2.37a1.724 1.724 0 00-1.065-2.572c-1.756-.426-1.756-2.924 0-3.35a1.724 1.724 0 001.066-2.573c-.94-1.543.826-3.31 2.37-2.37.996.608 2.296.07 2.572-1.065z" />
                                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 12a3 3 0 11-6 0 3 3 0 016 0z" />
                                  </svg>
                                </div>
                                <div className="flex-1">
                                  <a 
                                    href={tool.url} 
                                    target="_blank" 
                                    rel="noopener noreferrer"
                                    className="text-green-800 hover:text-green-900 font-medium text-sm hover:underline"
                                  >
                                    {tool.name}
                                  </a>
                                  {tool.description && (
                                    <p className="text-green-700 text-xs mt-1">{tool.description}</p>
                                  )}
                                </div>
                              </div>
                            ))}
                          </div>
                        </div>
                      )}

                      {resources.case_studies && resources.case_studies.length > 0 && (
                        <div>
                          <h5 className="text-xs font-semibold text-gray-600 uppercase tracking-wider mb-2">Case Studies</h5>
                          <div className="space-y-2">
                            {resources.case_studies.map((caseStudy, i) => (
                              <div key={i} className="flex items-start space-x-3 p-3 bg-purple-50 rounded-lg border border-purple-100">
                                <div className="flex-shrink-0 mt-0.5">
                                  <svg className="w-4 h-4 text-purple-600" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
                                  </svg>
                                </div>
                                <div className="flex-1">
                                  <a 
                                    href={caseStudy.url} 
                                    target="_blank" 
                                    rel="noopener noreferrer"
                                    className="text-purple-800 hover:text-purple-900 font-medium text-sm hover:underline"
                                  >
                                    {caseStudy.title}
                                  </a>
                                  {caseStudy.company && (
                                    <p className="text-purple-600 text-xs mt-1 font-medium">
                                      Company: {caseStudy.company}
                                    </p>
                                  )}
                                  {caseStudy.description && (
                                    <p className="text-purple-700 text-xs mt-1">{caseStudy.description}</p>
                                  )}
                                </div>
                              </div>
                            ))}
                          </div>
                        </div>
                      )}
                    </div>
                  </div>
                )}

                {/* Implementation Steps */}
                {useCase.implementation_steps && useCase.implementation_steps.length > 0 && (
                  <div>
                    <h4 className="text-sm font-semibold text-gray-900 mb-3">Implementation Roadmap</h4>
                    <div className="space-y-3">
                      {useCase.implementation_steps.map((step, i) => (
                        <div key={i} className="flex items-start space-x-4 p-4 bg-gray-50 rounded-lg border border-gray-200">
                          <div className="flex-shrink-0">
                            <div className="w-8 h-8 bg-indigo-100 rounded-full flex items-center justify-center border-2 border-indigo-200">
                              <span className="text-sm font-bold text-indigo-700">{i + 1}</span>
                            </div>
                          </div>
                          <div className="flex-1">
                            <h5 className="text-sm font-semibold text-gray-900 mb-1">{step.title || `Step ${i + 1}`}</h5>
                            <p className="text-sm text-gray-700">{step.description || step}</p>
                            {step.duration && (
                              <div className="mt-2 flex items-center text-xs text-gray-500">
                                <svg className="w-3 h-3 mr-1" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 8v4l3 3m6-3a9 9 0 11-18 0 9 9 0 0118 0z" />
                                </svg>
                                Duration: {step.duration}
                              </div>
                            )}
                          </div>
                        </div>
                      ))}
                    </div>
                  </div>
                )}

                {/* ROI Metrics */}
                {useCase.roi_metrics && (
                  <div>
                    <h4 className="text-sm font-semibold text-gray-900 mb-3">Expected ROI & Metrics</h4>
                    <div className="bg-gradient-to-r from-green-50 to-emerald-50 rounded-lg p-4 border border-green-200">
                      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                        {useCase.roi_metrics.time_savings && (
                          <div className="flex items-center space-x-3">
                            <div className="w-8 h-8 bg-green-100 rounded-full flex items-center justify-center">
                              <svg className="w-4 h-4 text-green-600" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 8v4l3 3m6-3a9 9 0 11-18 0 9 9 0 0118 0z" />
                              </svg>
                            </div>
                            <div>
                              <p className="text-sm font-medium text-gray-900">Time Savings</p>
                              <p className="text-lg font-bold text-green-700">{useCase.roi_metrics.time_savings}</p>
                            </div>
                          </div>
                        )}
                        {useCase.roi_metrics.cost_reduction && (
                          <div className="flex items-center space-x-3">
                            <div className="w-8 h-8 bg-green-100 rounded-full flex items-center justify-center">
                              <svg className="w-4 h-4 text-green-600" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 8c-1.657 0-3 .895-3 2s1.343 2 3 2 3 .895 3 2-1.343 2-3 2m0-8c1.11 0 2.08.402 2.599 1M12 8V7m0 1v8m0 0v1m0-1c-1.11 0-2.08-.402-2.599-1" />
                              </svg>
                            </div>
                            <div>
                              <p className="text-sm font-medium text-gray-900">Cost Reduction</p>
                              <p className="text-lg font-bold text-green-700">{useCase.roi_metrics.cost_reduction}</p>
                            </div>
                          </div>
                        )}
                        {useCase.roi_metrics.efficiency_gain && (
                          <div className="flex items-center space-x-3">
                            <div className="w-8 h-8 bg-green-100 rounded-full flex items-center justify-center">
                              <svg className="w-4 h-4 text-green-600" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13 7h8m0 0v8m0-8l-8 8-4-4-6 6" />
                              </svg>
                            </div>
                            <div>
                              <p className="text-sm font-medium text-gray-900">Efficiency Gain</p>
                              <p className="text-lg font-bold text-green-700">{useCase.roi_metrics.efficiency_gain}</p>
                            </div>
                          </div>
                        )}
                        {useCase.roi_metrics.payback_period && (
                          <div className="flex items-center space-x-3">
                            <div className="w-8 h-8 bg-green-100 rounded-full flex items-center justify-center">
                              <svg className="w-4 h-4 text-green-600" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 7h6m0 10v-3m-3 3h.01M9 17h.01M9 14h.01M12 14h.01M15 11h.01M12 11h.01M9 11h.01M7 21h10a2 2 0 002-2V5a2 2 0 00-2-2H7a2 2 0 00-2 2v14a2 2 0 002 2z" />
                              </svg>
                            </div>
                            <div>
                              <p className="text-sm font-medium text-gray-900">Payback Period</p>
                              <p className="text-lg font-bold text-green-700">{useCase.roi_metrics.payback_period}</p>
                            </div>
                          </div>
                        )}
                      </div>
                    </div>
                  </div>
                )}

                {/* Risk Assessment */}
                {useCase.risks && useCase.risks.length > 0 && (
                  <div>
                    <h4 className="text-sm font-semibold text-gray-900 mb-3">Risk Assessment</h4>
                    <div className="space-y-2">
                      {useCase.risks.map((risk, i) => (
                        <div key={i} className="flex items-start space-x-3 p-3 bg-amber-50 rounded-lg border border-amber-200">
                          <div className="flex-shrink-0 mt-0.5">
                            <svg className="w-4 h-4 text-amber-600" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z" />
                            </svg>
                          </div>
                          <div className="flex-1">
                            <p className="text-amber-800 text-sm font-medium">{risk.title || risk}</p>
                            {risk.description && (
                              <p className="text-amber-700 text-xs mt-1">{risk.description}</p>
                            )}
                            {risk.mitigation && (
                              <p className="text-amber-600 text-xs mt-1">
                                <span className="font-medium">Mitigation:</span> {risk.mitigation}
                              </p>
                            )}
                          </div>
                        </div>
                      ))}
                    </div>
                  </div>
                )}
              </div>
            )}
          </div>
        </div>
      </Card>
    </div>
  );
}