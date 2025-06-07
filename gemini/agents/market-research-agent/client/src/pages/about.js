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

      <div className="max-w-3xl mx-auto">
        <Card>
          <h1 className="text-2xl font-bold text-gray-900 mb-6">
            About AI Market Analyst
          </h1>

          <div className="prose prose-blue max-w-none">
            <p>
              AI Market Analyst is an advanced tool that leverages artificial
              intelligence to help companies identify and prioritize AI and
              GenAI implementation opportunities tailored to their specific
              industry and business needs.
            </p>

            <h2>What We Do</h2>
            <p>
              Our system analyzes your company or industry information and
              generates highly relevant AI use cases that can deliver
              significant business value. For each use case, we provide:
            </p>
            <ul>
              <li>Detailed description and business value proposition</li>
              <li>Implementation complexity assessment</li>
              <li>Relevant AI technologies</li>
              <li>Cross-functional benefits</li>
              <li>
                Curated implementation resources (datasets, code repositories,
                research papers)
              </li>
            </ul>

            <h2>Our Technology</h2>
            <p>
              AI Market Analyst is powered by state-of-the-art language models
              and a multi-agent architecture designed to provide comprehensive,
              accurate, and actionable insights. Our system combines:
            </p>
            <ul>
              <li>Advanced AI research capabilities</li>
              <li>Industry-specific knowledge</li>
              <li>Implementation resource discovery</li>
              <li>Business impact assessment</li>
            </ul>

            <h2>How to Use</h2>
            <p>
              Simply enter your company name, industry, or both, and our AI will
              generate tailored use cases for your specific context. The
              analysis typically takes a few minutes to complete, after which
              you'll receive a detailed report with prioritized use cases and
              implementation resources.
            </p>
          </div>
        </Card>
      </div>
    </Layout>
  );
};

export default About;
