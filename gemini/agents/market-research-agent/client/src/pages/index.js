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

      <div className="max-w-3xl mx-auto">
        <div className="text-center mb-8">
          <h1 className="text-3xl font-bold text-gray-900">
            AI Market Analyst
          </h1>
          <p className="mt-2 text-lg text-gray-600">
            Generate tailored AI and GenAI use cases for your company or
            industry
          </p>
        </div>

        <AnalysisForm />

        <div className="mt-12 bg-white shadow rounded-lg overflow-hidden">
          <div className="px-4 py-5 sm:p-6">
            <h2 className="text-lg font-medium text-gray-900">How It Works</h2>
            <div className="mt-4 grid grid-cols-1 gap-6 sm:grid-cols-3">
              <div className="flex flex-col items-center text-center">
                <div className="flex items-center justify-center h-12 w-12 rounded-md bg-blue-500 text-white">
                  <span className="text-lg font-semibold">1</span>
                </div>
                <h3 className="mt-4 text-lg font-medium text-gray-900">
                  Research
                </h3>
                <p className="mt-2 text-sm text-gray-500">
                  Our AI researches your company or industry to understand the
                  specific context and challenges.
                </p>
              </div>
              <div className="flex flex-col items-center text-center">
                <div className="flex items-center justify-center h-12 w-12 rounded-md bg-blue-500 text-white">
                  <span className="text-lg font-semibold">2</span>
                </div>
                <h3 className="mt-4 text-lg font-medium text-gray-900">
                  Generate
                </h3>
                <p className="mt-2 text-sm text-gray-500">
                  Advanced AI algorithms generate tailored use cases with
                  business value and implementation details.
                </p>
              </div>
              <div className="flex flex-col items-center text-center">
                <div className="flex items-center justify-center h-12 w-12 rounded-md bg-blue-500 text-white">
                  <span className="text-lg font-semibold">3</span>
                </div>
                <h3 className="mt-4 text-lg font-medium text-gray-900">
                  Resource
                </h3>
                <p className="mt-2 text-sm text-gray-500">
                  For each use case, we find relevant datasets and
                  implementation resources to accelerate your AI journey.
                </p>
              </div>
            </div>
          </div>
        </div>
      </div>
    </Layout>
  );
};

export default Home;
