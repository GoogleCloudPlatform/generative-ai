/**
 * Copyright 2024 Google LLC
 *
 * Licensed under the Apache License, Version 2.0 (the "License");
 * you may not use this file except in compliance with the License.
 * You may obtain a copy of the License at
 *
 *     http://www.apache.org/licenses/LICENSE-2.0
 *
 * Unless required by applicable law or agreed to in writing, software
 * distributed under the License is distributed on an "AS IS" BASIS,
 * WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
 * See the License for the specific language governing permissions and
 * limitations under the License.
 */

/**
 * Auth Service Worker
 *
 * This file intercepts all requests to the same service and injects
 * Firebase authentication headers. This is useful for Next.js server
 * actions and rest requests without having to add additional
 * boilerplate across the code base.
 *
 * After modification, this file needs to be rebuild:
 * npm run build-service-worker
 */

import { initializeApp } from "firebase/app";
import { Auth, getAuth, getIdToken } from "firebase/auth";
import { getInstallations, getToken } from "firebase/installations";
import { firebaseConfig } from "./libs/firebase/config";

// Configure Service Worker
self.addEventListener("install", () => {
  if (
    !firebaseConfig ||
    !firebaseConfig.apiKey ||
    firebaseConfig.apiKey === ""
  ) {
    console.warn(
      "Warning - Firebase config not provided. Proxying will not be enabled",
    );
  }
  // extract firebase config from query string
  console.log(
    `Initialised service worker. Project: ${firebaseConfig.projectId}`,
  );
});

function getOriginFromUrl(url: string) {
  // https://stackoverflow.com/questions/1420881/how-to-extract-base-url-from-a-string-in-javascript
  const pathArray = url.split("/");
  const protocol = pathArray[0];
  const host = pathArray[2];
  return protocol + "//" + host;
}

// Intercept fetch events to setup Firebase auth headers
self.addEventListener("fetch", (event) => {
  // Damned typescript...
  const e = event as FetchEvent;
  // Only append if doing request the same service and using https
  if (
    self.location.origin === getOriginFromUrl(e.request.url) &&
    (self.location.protocol === "https:" ||
      self.location.hostname === "localhost")
  ) {
    e.respondWith(fetchWithFirebaseHeaders(e.request));
    return;
  }
});

// Inject both Firebase token and Authz headers
async function fetchWithFirebaseHeaders(request: Request) {
  if (firebaseConfig) {
    const app = initializeApp(firebaseConfig);
    const auth = getAuth(app);
    const installations = getInstallations(app);
    const headers = new Headers(request.headers);
    const [authIdToken, installationToken] = await Promise.all([
      getAuthIdToken(auth),
      getToken(installations),
    ]);
    headers.append("Firebase-Instance-ID-Token", installationToken);
    if (authIdToken) {
      headers.append("Authorization", `Bearer ${authIdToken}`);
    }
    const newRequest = new Request(request, { headers });
    return await fetch(newRequest);
  }
  console.warn("No Firebase config found. Headers are not being injected.");
  return await fetch(request);
}

async function getAuthIdToken(auth: Auth) {
  await auth.authStateReady();
  if (!auth.currentUser) {
    return;
  }
  return await getIdToken(auth.currentUser);
}
