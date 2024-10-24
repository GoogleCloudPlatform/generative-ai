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

"use strict";
"use client";

import { APILoader } from "@googlemaps/extended-component-library/react";
import PlaceAutoComplete from "./PlaceAutoComplete";
import { PostcardFlow } from "@/libs/genkit/schema";
import { useEffect, useState } from "react";
import { callPostcardFlow } from "@/libs/genkit/flows";
import PostcardImage from "./Postcard";
import Stack from "@mui/material/Stack";
import LoadingButton from "@mui/lab/LoadingButton";
import Container from "@mui/material/Container";
import { UserAuth } from "./AuthContext";
import CircularProgress from "@mui/material/CircularProgress";
import Alert from "@mui/material/Alert";
import Button from "@mui/material/Button";
import AlertTitle from "@mui/material/AlertTitle";
import TextField from "@mui/material/TextField";
import { firebaseConfig } from "@/libs/firebase/config";

export default function PostcardForm() {
  const [start, setStart] = useState<string>("");
  const [end, setEnd] = useState<string>("");
  const [sender, setSender] = useState<string>("");
  const [recipient, setRecpient] = useState<string>("");
  const [loading, setLoading] = useState<boolean>(true);
  const [postcardImage, setPostcardImage] = useState<string | null>(null);
  const [mapImage, setMapImage] = useState<string | null>(null);
  const [description, setDescription] = useState<string>("");
  const [story, setStory] = useState<string>("");
  const [error, setError] = useState<string | null>(null);
  const [loginError, setLoginError] = useState<string | null>(null);
  const [generating, setGenerating] = useState<boolean>(false);

  function updateStartAddress(e: Event) {
    if (e.target) {
      const eventValue = (e.target as HTMLSelectElement).value;
      const place = eventValue as unknown as google.maps.places.Place;
      setStart(`${place.displayName}, ${place.formattedAddress}`);
    }
  }

  function updateEndAddress(e: Event) {
    if (e.target) {
      const eventValue = (e.target as HTMLSelectElement).value;
      const place = eventValue as unknown as google.maps.places.Place;
      setEnd(`${place.displayName}, ${place.formattedAddress}`);
    }
  }

  async function generatePostcard(event: React.FormEvent) {
    try {
      event.preventDefault();
      setGenerating(true);
      const image = await callPostcardFlow(r);
      setError(null);
      setPostcardImage(image.image);
      setDescription(image.description);
      setStory(image.story);
      setMapImage(image.map);
    }
    catch {
      // TODO - show an error in the UI
      setError("An error occurred generating your postcard. Please try again.");
    }
    finally {
      setGenerating(false);
    }
  }
  // This page requires authentication, check we have that
  const { user, googleSignIn, enabled } = UserAuth();
  useEffect(() => {
    const checkAuthentication = async () => {
      await new Promise(resolve => setTimeout(resolve, 50));
      setLoading(false);
    };
    checkAuthentication();
  }, [user]);

  const handleSignIn = async () => {
    try {
      await googleSignIn();
      setLoginError(null);
    }
    catch (error) {
      setLoginError(`Login failed with error: ${error}`);
    }
  };

  const r = {
    start: start,
    end: end,
    stops: [],
    sender: sender,
    recipient: recipient,
  } as PostcardFlow;

  if (loading) {
    return <CircularProgress />;
  }

  if (!enabled) {
    <Alert severity="warning">
      <AlertTitle>Login is disabled in this project.</AlertTitle>
      {loginError}
    </Alert>;
  }

  if ((!user) && (enabled)) {
    // Install a proxying service worker if Firebase is configured
    if (("serviceWorker" in navigator) && (firebaseConfig) && (firebaseConfig.apiKey) && (firebaseConfig.apiKey !== "")) {
      navigator.serviceWorker.register("/auth-service-worker.js", { scope: "/" });
    }
    return (
      <>
        {loginError && !loading && (
          <Alert severity="error">
            <AlertTitle>An Error Occurred</AlertTitle>
            {loginError}
          </Alert>
        )}
        <Alert severity="warning" variant="outlined">Only logged-in users may view this page.</Alert>
        <Button color="inherit" onClick={handleSignIn}>
          Login with Google
        </Button>
      </>
    );
  }

  return (
    <Container maxWidth="lg">
      <PostcardImage postcardImage={postcardImage} generating={generating} description={description} start={start} end={end} error={error} mapImage={mapImage} story={story} />
      <form>
        <APILoader apiKey={process.env.NEXT_PUBLIC_GOOGLE_MAPS_PUBLIC_API_KEY} solutionChannel="GMP_GCC_placepicker_v1" />
        <Stack spacing={2} direction="row">
          <TextField required sx={{ width: "50%" }} label="Sender" variant="outlined" value={sender} onChange={e => setSender(e.target.value)} />
          <TextField required sx={{ width: "50%" }} label="Recipient" variant="outlined" value={recipient} onChange={e => setRecpient(e.target.value)} />
        </Stack>
        <Stack spacing={2} direction="column">
          <PlaceAutoComplete description="Starting Point" value="Search for a location" id="start" handleChange={updateStartAddress} />
          <PlaceAutoComplete description="Ending Point" value="Search for a location" id="end" handleChange={updateEndAddress} />
          <LoadingButton variant="contained" loading={generating} onClick={generatePostcard}>
            Generate Postcard
          </LoadingButton>
        </Stack>
      </form>
    </Container>
  );
}
