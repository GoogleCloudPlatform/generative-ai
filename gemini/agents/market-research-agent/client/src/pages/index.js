import React from "react";
import Head from "next/head";
import Layout from "../components/layout/Layout";
import AnalysisForm from "../components/forms/AnalysisForm";

const Home = () => {
  return (
    <Layout>
      <Head>
        <title>AI Market Analyst | Generate AI Use Cases</title>
        <meta
          name="description"
          content="Generate AI and GenAI use cases for your company or industry"
        />
        <link rel="icon" href="/favicon.ico" />
      </Head>

      <div className="min-h-screen bg-gradient-to-br from-blue-50 via-white to-purple-50">
        {/* Hero Section */}
        <div className="max-w-7xl mx-auto px-4 py-12">
          <div className="text-center mb-16">
            {/* Badge */}
            <div className="inline-flex items-center px-6 py-3 bg-gradient-to-r from-blue-100 to-purple-100 rounded-full text-sm font-medium text-blue-800 mb-8 shadow-sm">
              <svg className="w-4 h-4 mr-2" fill="currentColor" viewBox="0 0 20 20">
                <path fillRule="evenodd" d="M11.3 1.046A1 1 0 0112 2v5h4a1 1 0 01.82 1.573l-7 10A1 1 0 018 18v-5H4a1 1 0 01-.82-1.573l7-10a1 1 0 011.12-.38z" clipRule="evenodd" />
              </svg>
              AI-Powered Business Intelligence
            </div>

            {/* Main Heading */}
            <h1 className="text-5xl md:text-7xl font-bold mb-6">
              <span className="bg-gradient-to-r from-blue-600 via-purple-600 to-blue-800 bg-clip-text text-transparent">
                AI Market
              </span>
              <br />
              <span className="bg-gradient-to-r from-purple-600 to-pink-600 bg-clip-text text-transparent">
                Analyst
              </span>
            </h1>

            {/* Subtitle */}
            <p className="text-xl md:text-2xl text-gray-600 max-w-4xl mx-auto leading-relaxed mb-12">
              Discover <span className="font-semibold text-blue-600">tailored AI opportunities</span> for your business.
              Get actionable insights, implementation roadmaps, and curated resources in minutes.
            </p>

            {/* Stats */}
            <div className="grid grid-cols-2 md:grid-cols-4 gap-8 max-w-3xl mx-auto mb-16">
              {[
                { number: "500+", label: "Use Cases" },
                { number: "50+", label: "Industries" },
                { number: "95%", label: "Accuracy" },
                { number: "< 5min", label: "Analysis Time" }
              ].map((stat, index) => (
                <div key={index} className="text-center">
                  <div className="text-2xl md:text-3xl font-bold bg-gradient-to-r from-blue-600 to-purple-600 bg-clip-text text-transparent mb-1">
                    {stat.number}
                  </div>
                  <div className="text-sm text-gray-500 font-medium">{stat.label}</div>
                </div>
              ))}
            </div>
          </div>

          {/* Form Section */}
          <div className="max-w-3xl mx-auto mb-20">
            <div className="bg-white/80 backdrop-blur-sm rounded-3xl shadow-2xl border border-white/20 p-8 md:p-12">
              <div className="text-center mb-8">
                <h2 className="text-2xl font-bold text-gray-900 mb-3">
                  Start Your AI Journey
                </h2>
                <p className="text-gray-600">
                  Enter your company or industry details to generate personalized AI use cases
                </p>
              </div>
              <AnalysisForm />
            </div>
          </div>

          {/* How It Works Section */}
          <div className="max-w-6xl mx-auto">
            <div className="text-center mb-16">
              <h2 className="text-4xl font-bold bg-gradient-to-r from-gray-900 to-gray-600 bg-clip-text text-transparent mb-4">
                How It Works
              </h2>
              <p className="text-xl text-gray-600 max-w-2xl mx-auto">
                Our advanced AI system analyzes your business context and delivers actionable insights
              </p>
            </div>

            <div className="grid md:grid-cols-3 gap-8">
              {/* Step 1 */}
              <div className="group relative">
                <div className="bg-white rounded-2xl p-8 shadow-lg hover:shadow-2xl transition-all duration-300 transform hover:-translate-y-2 border border-gray-100">
                  {/* Icon */}
                  <div className="w-16 h-16 bg-gradient-to-r from-blue-500 to-blue-600 rounded-2xl flex items-center justify-center mb-6 group-hover:scale-110 transition-transform duration-300">
                    <svg className="w-8 h-8 text-white" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z" />
                    </svg>
                  </div>
                  
                  {/* Step Number */}
                  <div className="absolute -top-4 -right-4 w-8 h-8 bg-gradient-to-r from-blue-500 to-purple-600 rounded-full flex items-center justify-center text-white font-bold text-sm shadow-lg">
                    1
                  </div>

                  <h3 className="text-xl font-bold text-gray-900 mb-4">
                    Research & Analyze
                  </h3>
                  <p className="text-gray-600 leading-relaxed">
                    Our AI deeply researches your company or industry, understanding specific contexts, 
                    challenges, and market opportunities to provide relevant insights.
                  </p>

                  {/* Features */}
                  <div className="mt-6 space-y-2">
                    {["Industry analysis", "Market research", "Context understanding"].map((feature, index) => (
                      <div key={index} className="flex items-center text-sm text-gray-500">
                        <div className="w-1.5 h-1.5 bg-blue-500 rounded-full mr-3"></div>
                        {feature}
                      </div>
                    ))}
                  </div>
                </div>
              </div>

              {/* Step 2 */}
              <div className="group relative">
                <div className="bg-white rounded-2xl p-8 shadow-lg hover:shadow-2xl transition-all duration-300 transform hover:-translate-y-2 border border-gray-100">
                  {/* Icon */}
                  <div className="w-16 h-16 bg-gradient-to-r from-purple-500 to-purple-600 rounded-2xl flex items-center justify-center mb-6 group-hover:scale-110 transition-transform duration-300">
                    <svg className="w-8 h-8 text-white" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13 10V3L4 14h7v7l9-11h-7z" />
                    </svg>
                  </div>
                  
                  {/* Step Number */}
                  <div className="absolute -top-4 -right-4 w-8 h-8 bg-gradient-to-r from-purple-500 to-pink-600 rounded-full flex items-center justify-center text-white font-bold text-sm shadow-lg">
                    2
                  </div>

                  <h3 className="text-xl font-bold text-gray-900 mb-4">
                    Generate Use Cases
                  </h3>
                  <p className="text-gray-600 leading-relaxed">
                    Advanced algorithms create tailored AI use cases with detailed business value propositions, 
                    implementation complexity, and expected ROI for your specific needs.
                  </p>

                  {/* Features */}
                  <div className="mt-6 space-y-2">
                    {["Business value analysis", "Implementation roadmap", "ROI calculations"].map((feature, index) => (
                      <div key={index} className="flex items-center text-sm text-gray-500">
                        <div className="w-1.5 h-1.5 bg-purple-500 rounded-full mr-3"></div>
                        {feature}
                      </div>
                    ))}
                  </div>
                </div>
              </div>

              {/* Step 3 */}
              <div className="group relative">
                <div className="bg-white rounded-2xl p-8 shadow-lg hover:shadow-2xl transition-all duration-300 transform hover:-translate-y-2 border border-gray-100">
                  {/* Icon */}
                  <div className="w-16 h-16 bg-gradient-to-r from-green-500 to-green-600 rounded-2xl flex items-center justify-center mb-6 group-hover:scale-110 transition-transform duration-300">
                    <svg className="w-8 h-8 text-white" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 11H5m14 0a2 2 0 012 2v6a2 2 0 01-2 2H5a2 2 0 01-2-2v-6a2 2 0 012-2m14 0V9a2 2 0 00-2-2M5 11V9a2 2 0 012-2m0 0V5a2 2 0 012-2h6a2 2 0 012 2v2M7 7h10" />
                    </svg>
                  </div>
                  
                  {/* Step Number */}
                  <div className="absolute -top-4 -right-4 w-8 h-8 bg-gradient-to-r from-green-500 to-teal-600 rounded-full flex items-center justify-center text-white font-bold text-sm shadow-lg">
                    3
                  </div>

                  <h3 className="text-xl font-bold text-gray-900 mb-4">
                    Curate Resources
                  </h3>
                  <p className="text-gray-600 leading-relaxed">
                    For each use case, we provide comprehensive implementation resources including 
                    relevant datasets, code repositories, and research papers to accelerate your journey.
                  </p>

                  {/* Features */}
                  <div className="mt-6 space-y-2">
                    {["Datasets & APIs", "Code repositories", "Research papers"].map((feature, index) => (
                      <div key={index} className="flex items-center text-sm text-gray-500">
                        <div className="w-1.5 h-1.5 bg-green-500 rounded-full mr-3"></div>
                        {feature}
                      </div>
                    ))}
                  </div>
                </div>
              </div>
            </div>       
          </div>

          {/* Trust Section */}
          <div className="max-w-4xl mx-auto text-center mt-20">
            <div className="bg-gradient-to-r from-blue-600 to-purple-700 rounded-3xl p-8 md:p-12 text-white">
              <h3 className="text-2xl md:text-3xl font-bold mb-4">
                Grow Like Forward-Thinking Companies
              </h3>
              <p className="text-blue-100 text-lg mb-8">
                Join hundreds of organizations already transforming their business with AI
              </p>
              <div className="flex flex-wrap justify-center gap-8 text-blue-200">
                {["Healthcare", "Finance", "Retail", "Manufacturing", "Technology", "Education"].map((industry, index) => (
                  <div key={index} className="px-4 py-2 bg-white/10 rounded-full text-sm font-medium">
                    {industry}
                  </div>
                ))}
              </div>
            </div>
          </div>
        </div>
      </div>
    </Layout>
  );
};

export default Home;