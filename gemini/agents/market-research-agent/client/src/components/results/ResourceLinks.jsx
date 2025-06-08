/Users/prajwal/Developer/generative-ai/gemini/agents/market-research-agent/client/src/components/results/ResourceLinks.jsx

import React from "react";

export default function ResourceLinks({ title, resources }) {
  if (!resources || resources.length === 0) return null;

  return (
    <div className="mt-4">
      <h3 className="text-lg font-medium text-gray-900">{title}</h3>
      <div className="mt-2 space-y-2">
        {resources.map((resource, i) => (
          <div key={i} className="flex items-start">
            <div className="flex-1">
              <a
                href={resource.url}
                target="_blank"
                rel="noopener noreferrer"
                className="text-blue-600 hover:text-blue-800 font-medium">
                {resource.title}
              </a>
              <div className="mt-1 flex items-center space-x-2">
                <span className="text-xs text-gray-500 capitalize">
                  {resource.source}
                </span>
                {resource.relevance_score && (
                  <span className="inline-flex items-center px-2 py-0.5 rounded text-xs font-medium bg-blue-100 text-blue-800">
                    Relevance: {resource.relevance_score}/10
                  </span>
                )}
              </div>
              {resource.relevance_notes && (
                <p className="mt-1 text-sm text-gray-600">
                  {resource.relevance_notes}
                </p>
              )}
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}
