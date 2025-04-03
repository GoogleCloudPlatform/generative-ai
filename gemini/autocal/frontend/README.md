# AutoCal Frontend

## TL;DR

### Running locally

```sh
cp .env.example .env
# Make edits to .env as needed
npm install
npm run dev
```

### Deploying to Firebase App Hosting

First configure secrets:

```sh
export PROJECT_ID=PROJECT_ID
firebase apphosting:secrets:set CLIENT_SECRET --project "${PROJECT_ID}"
firebase apphosting:secrets:set ENCRYPTION_KEY --project "${PROJECT_ID}"
```

Then create the hosting backend:

```sh
firebase apphosting:backends:create --project "${PROJECT_ID}" --location europe-west4
```

That's it! Sit back and relax ☕.

## Architecture

This is a [Next.js](https://nextjs.org) app that uses [MUI](https://mui.com/) components for its UI. It supports the following flow:

1. User logs in with Google Credentials and accepts Calendar scopes
   - Access + Refresh tokens are encrypted and persisted in Firestore
   - The ID token is stored as a http only cookie
2. User uploads a screenshot or image for their calendar
   - The image is copied to Google Cloud storage in a user-specific folder protected with Firebase Security Rules
   - Two firestore documents are created:
     1. `screenshots/[email]-[uuid]` - an immutable record of the original event. This triggers the backend function (below)
     2. `state/[email]-[uuid]` - the state of the process. The app listens on this document for changes.
3. The `screenshots/` collection has a trigger that invokes the backend function - this processes the uploaded image and writes to the `state/` collection its results
4. When the `state/[email]-[uuid]` document is updated with `processed=true` then the UI shows the extracted calendar event
   1. This event can be edited or refined
   2. The user confirms and clicks to add it to their calendar

All entries are timestamped, so a theoretical clean-up could then happen with existing images and database records.

## Auth

Auth is complicated. There are three parts:

1. Client authentication - this is done with the [@react-oauth/google](https://www.npmjs.com/package/@react-oauth/google) package. This provides the client login flow and initial auth code retrieval.
2. Server authentication - the auth code is then exchanged for an access token, a refresh token, and an ID token. This happens server-side using the [google-auth-library](https://www.npmjs.com/package/google-auth-library) and is invoked via [libs/auth/auth.ts](libs/auth/auth.ts). A http only cookie is then set with the ID Token.
3. Firebase authentication - once an ID token is retrieved, this is exchanged with Firebase to obtain a user via `signInWithCredential`. If no user exists in browser state then the server is queried for an ID token and this is exchanged for the rest of the session. As the Firebase user is the last link in the chain it is also the source of truth for a user being logged-in or not.
