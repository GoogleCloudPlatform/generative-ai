import React from "react";
import Head from "next/head";
import Layout from "../components/layout/Layout";
import Card from "../components/ui/Card";

const About = () => {
  return (
    <Layout>
      <Head>
        <title>About | AI Market Analyst</title>
        <meta
          name="description"
          content="Learn about the AI Market Analyst tool"
        />
        <link rel="icon" href="/favicon.ico" />
      </Head>

      <div className="max-w-6xl mx-auto px-4 py-8">
        {/* Hero Section */}
        <div className="text-center mb-16">
          <div className="inline-flex items-center px-4 py-2 bg-gradient-to-r from-blue-100 to-purple-100 rounded-full text-sm font-medium text-blue-800 mb-6">
            <span className="w-2 h-2 bg-blue-500 rounded-full mr-2 animate-pulse"></span>
            Powered by Advanced AI
          </div>
          <h1 className="text-5xl md:text-6xl font-bold bg-gradient-to-r from-blue-600 via-purple-600 to-blue-800 bg-clip-text text-transparent mb-6">
            AI Market Analyst
          </h1>
          <p className="text-xl text-gray-600 max-w-3xl mx-auto leading-relaxed">
            Transform your business with AI-powered insights. Discover tailored implementation opportunities 
            that drive real value in your industry.
          </p>
        </div>

        {/* Main Content Grid */}
        <div className="grid md:grid-cols-2 lg:grid-cols-3 gap-8 mb-16">
          {/* What We Do Card */}
          <Card className="group hover:shadow-2xl transition-all duration-300 transform hover:-translate-y-2 bg-gradient-to-br from-white to-blue-50 border-0 shadow-lg">
            <div className="p-8">
              <div className="w-16 h-16 bg-gradient-to-r from-blue-500 to-purple-600 rounded-2xl flex items-center justify-center mb-6 group-hover:scale-110 transition-transform duration-300">
                <svg className="w-8 h-8 text-white" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13 10V3L4 14h7v7l9-11h-7z" />
                </svg>
              </div>
              <h3 className="text-2xl font-bold text-gray-900 mb-4">What We Do</h3>
              <p className="text-gray-600 mb-6 leading-relaxed">
                We analyze your business and generate highly relevant AI use cases with detailed implementation roadmaps.
              </p>
              <div className="space-y-3">
                {[
                  "Business value propositions",
                  "Implementation complexity",
                  "Technology recommendations",
                  "Cross-functional benefits",
                  "Curated resources"
                ].map((item, index) => (
                  <div key={index} className="flex items-center text-sm text-gray-700">
                    <div className="w-2 h-2 bg-gradient-to-r from-blue-500 to-purple-600 rounded-full mr-3"></div>
                    {item}
                  </div>
                ))}
              </div>
            </div>
          </Card>

          {/* Technology Card */}
          <Card className="group hover:shadow-2xl transition-all duration-300 transform hover:-translate-y-2 bg-gradient-to-br from-white to-purple-50 border-0 shadow-lg">
            <div className="p-8">
              <div className="w-16 h-16 bg-gradient-to-r from-purple-500 to-pink-600 rounded-2xl flex items-center justify-center mb-6 group-hover:scale-110 transition-transform duration-300">
                <svg className="w-8 h-8 text-white" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9.663 17h4.673M12 3v1m6.364 1.636l-.707.707M21 12h-1M4 12H3m3.343-5.657l-.707-.707m2.828 9.9a5 5 0 117.072 0l-.548.547A3.374 3.374 0 0014 18.469V19a2 2 0 11-4 0v-.531c0-.895-.356-1.754-.988-2.386l-.548-.547z" />
                </svg>
              </div>
              <h3 className="text-2xl font-bold text-gray-900 mb-4">Our Technology</h3>
              <p className="text-gray-600 mb-6 leading-relaxed">
                Powered by state-of-the-art language models and multi-agent architecture for comprehensive insights.
              </p>
              <div className="space-y-3">
                {[
                  "Advanced AI research",
                  "Industry expertise",
                  "Resource discovery",
                  "Impact assessment",
                  "Real-time analysis"
                ].map((item, index) => (
                  <div key={index} className="flex items-center text-sm text-gray-700">
                    <div className="w-2 h-2 bg-gradient-to-r from-purple-500 to-pink-600 rounded-full mr-3"></div>
                    {item}
                  </div>
                ))}
              </div>
            </div>
          </Card>

          {/* How to Use Card */}
          <Card className="group hover:shadow-2xl transition-all duration-300 transform hover:-translate-y-2 bg-gradient-to-br from-white to-green-50 border-0 shadow-lg md:col-span-2 lg:col-span-1">
            <div className="p-8">
              <div className="w-16 h-16 bg-gradient-to-r from-green-500 to-teal-600 rounded-2xl flex items-center justify-center mb-6 group-hover:scale-110 transition-transform duration-300">
                <svg className="w-8 h-8 text-white" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 6.253v13m0-13C10.832 5.477 9.246 5 7.5 5S4.168 5.477 3 6.253v13C4.168 18.477 5.754 18 7.5 18s3.332.477 4.5 1.253m0-13C13.168 5.477 14.754 5 16.5 5c1.746 0 3.332.477 4.5 1.253v13C19.832 18.477 18.246 18 16.5 18c-1.746 0-3.332.477-4.5 1.253" />
                </svg>
              </div>
              <h3 className="text-2xl font-bold text-gray-900 mb-4">How to Use</h3>
              <p className="text-gray-600 mb-6 leading-relaxed">
                Simply enter your company details and let our AI generate tailored use cases in minutes.
              </p>
              <div className="space-y-4">
                {[
                  { step: "1", text: "Enter company/industry info" },
                  { step: "2", text: "AI analyzes your context" },
                  { step: "3", text: "Receive detailed report" }
                ].map((item, index) => (
                  <div key={index} className="flex items-center text-sm text-gray-700">
                    <div className="w-6 h-6 bg-gradient-to-r from-green-500 to-teal-600 rounded-full flex items-center justify-center text-white text-xs font-bold mr-3">
                      {item.step}
                    </div>
                    {item.text}
                  </div>
                ))}
              </div>
            </div>
          </Card>
        </div>

        {/* CTA Section */}
        <div className="text-center">
          <Card className="bg-gradient-to-r from-gray-50 to-white border-0 shadow-xl">
            <div className="p-12">
              <h2 className="text-3xl font-bold text-gray-900 mb-4">
                Ready to Transform Your Business?
              </h2>
              <p className="text-xl text-gray-600 mb-8 max-w-2xl mx-auto">
                Discover AI opportunities tailored to your industry and start your transformation journey today.
              </p>
              <a
                href="/"
                className="inline-block bg-gradient-to-r from-blue-600 to-purple-600 hover:from-blue-700 hover:to-purple-700 text-white font-semibold py-4 px-8 rounded-xl transition-all duration-300 transform hover:scale-105 shadow-lg hover:shadow-xl"
              >
                Get Started Now
              </a>
            </div>
          </Card>
        </div>
      </div>
    </Layout>
  );
};

export default About;