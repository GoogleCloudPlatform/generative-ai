/** @type {import('next').NextConfig} */
const nextConfig = {
  reactStrictMode: true,
  // Workaround Handlebar import issues
  // https://github.com/handlebars-lang/handlebars.js/issues/953
  webpack: (config) => {
    config.resolve.alias["handlebars"] = "handlebars/dist/handlebars.js";
    return config;
  },
  // Workaround dependency errors
  // https://github.com/open-telemetry/opentelemetry-js/pull/4214
  experimental: {
    instrumentationHook: true,
    serverComponentsExternalPackages: [
      "@opentelemetry/auto-instrumentations-node",
      "@opentelemetry/sdk-node",
    ],
  },
};

export default nextConfig;
