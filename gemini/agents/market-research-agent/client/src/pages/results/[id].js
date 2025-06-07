import React from "react";
import { useRouter } from "next/router";
import Head from "next/head";
import Layout from "../../components/layout/Layout";
import ResultsPanel from "../../components/results/ResultsPanel";

const ResultsPage = () => {
  const router = useRouter();
  const { id } = router.query;

  return (
    <Layout>
      <Head>
        <title>Analysis Results | AI Market Analyst</title>
        <meta
          name="description"
          content="View generated AI and GenAI use cases"
        />
        <link rel="icon" href="/favicon.ico" />
      </Head>

      {id ? (
        <ResultsPanel requestId={id} />
      ) : (
        <div className="text-center py-12">
          <p>Loading...</p>
        </div>
      )}
    </Layout>
  );
};

export default ResultsPage;
