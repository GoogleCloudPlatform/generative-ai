import React from "react";
import Card from "../ui/Card";

export default function UseCaseCard({ useCase, resources, index }) {
  const complexityColor =
    {
      Low: "bg-green-100 text-green-800",
      Medium: "bg-yellow-100 text-yellow-800",
      High: "bg-red-100 text-red-800",
    }[useCase.implementation_complexity] || "bg-gray-100 text-gray-800";

  return (
    <Card className="mb-6">
      <div className="flex items-start justify-between">
        <h3 className="text-xl font-semibold text-gray-900">
          {index + 1}. {useCase.title}
        </h3>
        {useCase.priority_score && (
          <span className="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium bg-blue-100 text-blue-800">
            Priority: {useCase.priority_score}/10
          </span>
        )}
      </div>

      <div className="mt-4 grid grid-cols-1 md:grid-cols-2 gap-4">
        <div>
          <h4 className="text-sm font-medium text-gray-500">Description</h4>
          <p className="mt-1 text-gray-900">{useCase.description}</p>

          <h4 className="mt-4 text-sm font-medium text-gray-500">
            Business Value
          </h4>
          <p className="mt-1 text-gray-900">{useCase.business_value}</p>

          {useCase.prioritization_rationale && (
            <>
              <h4 className="mt-4 text-sm font-medium text-gray-500">
                Prioritization Rationale
              </h4>
              <p className="mt-1 text-gray-900">
                {useCase.prioritization_rationale}
              </p>
            </>
          )}
        </div>

        <div>
          <h4 className="text-sm font-medium text-gray-500">
            Implementation Details
          </h4>
          <div className="mt-1 space-y-2">
            <div className="flex items-center">
              <span className="text-sm text-gray-500 w-32">Complexity:</span>
              <span
                className={`inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium ${complexityColor}`}>
                {useCase.implementation_complexity}
              </span>
            </div>

            <div className="flex items-start">
              <span className="text-sm text-gray-500 w-32">Technologies:</span>
              <div className="flex flex-wrap gap-1">
                {useCase.ai_technologies.map((tech, i) => (
                  <span
                    key={i}
                    className="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium bg-indigo-100 text-indigo-800">
                    {tech}
                  </span>
                ))}
              </div>
            </div>

            {useCase.keywords && useCase.keywords.length > 0 && (
              <div className="flex items-start">
                <span className="text-sm text-gray-500 w-32">Keywords:</span>
                <div className="flex flex-wrap gap-1">
                  {useCase.keywords.map((keyword, i) => (
                    <span
                      key={i}
                      className="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium bg-gray-100 text-gray-800">
                      {keyword}
                    </span>
                  ))}
                </div>
              </div>
            )}
          </div>

          {useCase.cross_functional_benefits &&
            useCase.cross_functional_benefits.length > 0 && (
              <>
                <h4 className="mt-4 text-sm font-medium text-gray-500">
                  Cross-Functional Benefits
                </h4>
                <div className="mt-1 space-y-2">
                  {useCase.cross_functional_benefits.map((benefit, i) => (
                    <div key={i} className="flex items-start">
                      <span className="text-sm font-medium text-gray-500 w-32">
                        {benefit.department}:
                      </span>
                      <span className="text-sm text-gray-900">
                        {benefit.benefit}
                      </span>
                    </div>
                  ))}
                </div>
              </>
            )}
        </div>
      </div>

      {resources && resources.length > 0 && (
        <div className="mt-6">
          <h4 className="text-sm font-medium text-gray-500">
            Implementation Resources
          </h4>
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
      )}
    </Card>
  );
}
