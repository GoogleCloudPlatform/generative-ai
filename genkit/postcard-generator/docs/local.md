# Running Locally

## Requirements

### Environment Requirements

1. Node.js 20+

### Dependencies

Note: These dependencies can be automated by following the [deployment instructions](deploy.md).

1. A Google Cloud Project with Billing, Vertex enabled
2. A [Google Maps API key](https://developers.google.com/maps/documentation/embed/get-api-key). This is required for autocomplete, routing, and static map generation
3. Vertex AI enabled in your project

## Configuration

### Environment Variables

Copy `.env.example` to `.env` and populate it. The most important thing is a maps API key.

### Node Dependency Installation

Install genkit and Next.js dependencies:

```sh
npm install
```

## Development Servers

### Genkit

To start a genkit server, run the following:

```sh
npx genkit@latest start
```

You can now access the Genkit console on [localhost:4000](http://localhost:4000).

### Next.js

To start a Next.js development server, run the following:

```sh
npm run dev
```

You can access this on [localhost:3000](http://localhost:3000)
