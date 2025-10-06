# Demo Flow

You can optionally show [deploying this app to Firebase App Hosting](deploy.md) as well if you wish. This is otherwise not covered in this flow.

## Overview

1. Show the running app (either in Google Cloud or locally)
2. Talk through its flow and features used
3. Open the Genkit developer console and show the development loop
4. Show those changes being made in production

### Step 1: Show the running App

**Note:** If you have deployed to Firebase App Hosting, you don't need to run the demo locally and should show it running there.

#### Start a Development Server

Introduce the fact that this is a Next.js app using server and client-side rendering. It's an AI app that uses a combination of Vertex AI and Google Maps from a single codebase.

Start up the development server:

```sh
npm run dev
```

#### Create a Postcard

You can then navigate to [localhost:3000](http://localhost:3000) and send a demo postcard. Pick major landmarks in a city near you.

## AI Flow

1. User inputs start and end addresses and the names of the recipient and sender for the postcard
   - Addresses are autocompleted in the web app using the Maps API
2. A map between the addresses is created using the [Google Maps routes API](https://developers.google.com/maps/documentation/routes) and [Google Maps static API](https://developers.google.com/maps/documentation/maps-static/overview)
3. The map image is sent to Gemini alongside the rest of the data to generate highlights of a journey and a story for the back of the postcard
   - The prompt can be seen in [prompts/postcard-map.prompt](prompts/postcard-map.prompt)
   - This prompt requests Gemini returns the response in structured JSON, the schema of which can be seen in [libs/genkit/schema.ts](libs/genkit/schema.ts).
   - An example [partial prompt](https://firebase.google.com/docs/genkit/dotprompt#partials) in [prompts/\_example-highlights.prompt](prompts/_example-highlights.prompt)
4. The highlights of the route alongside the start and end is sent to Imagen 3
   - This prompt can be seen in [prompts/postcard-image.prompt](prompts/postcard-image.prompt)
5. The flow returns the generated image, the story created, and the map image

### Web App

This is a [Next.js](https://nextjs.org) app that uses both server and client-side rendering. It is protected with [Firebase Auth](https://firebase.google.com/docs/auth) to ensure only Googlers can access it. If you are deploying it yourself, I recommend using [a blocking function](https://firebase.google.com/docs/auth/extend-with-blocking-functions) to secure it.

The web app can be deployed with [Firebase App Hosting](https://firebase.google.com/docs/app-hosting) and instructions to do so are further down in this document.

Quickstart:

```sh
npm run dev
```

### Genkit Demo

There are prompts in the [prompts/](prompts/) folder that can be modified and the flow code lives in [libs/genkit/flows.ts](libs/genkit/flows.ts).

Quickstart:

```sh
npm run genkit:dev
```
