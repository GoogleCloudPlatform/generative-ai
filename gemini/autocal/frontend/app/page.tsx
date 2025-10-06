/**
 * Copyright 2025 Google LLC
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

"use client";

import { useEffect } from "react";
import {
  clientFirestore,
  firebaseAuth,
} from "@/libs/firebase/client/clientApp";
import { useAuthState } from "react-firebase-hooks/auth";
import Alert from "@mui/material/Alert";
import AlertTitle from "@mui/material/AlertTitle";
import { doc, onSnapshot } from "firebase/firestore";
import { processedScreenshotConverter } from "@/libs/schema/schema";
import dynamic from "next/dynamic";
import Box from "@mui/material/Box";
import { Typography } from "@mui/material";
import Link from "@mui/material/Link";
import { Status } from "@/components/context/StatusContext";
import UploadForm from "@/components/upload/UploadForm";

// Lazy load upload processor
const UploadProcessor = dynamic(
  () => import("@/components/upload/UploadProgress")
);
const EditCalendar = dynamic(() => import("@/components/upload/EditCalendar"));

export default function Home() {
  const { status, id, error, setStatus, screenshot } = Status();

  // Logged-in user
  const [user, loading, userError] = useAuthState(firebaseAuth);

  // Listen for changes in the uploaded document's status
  useEffect(() => {
    async function updateStatus() {
      if (id && user?.email) {
        console.log(`Listening on ${user.email}-${id}`);
        const unsubscribe = onSnapshot(
          doc(clientFirestore, "state", `${user.email}-${id}`).withConverter(
            processedScreenshotConverter
          ),
          (doc) => {
            if (doc.data()) {
              setStatus(doc.data()!);
            }
          }
        );
        return () => unsubscribe();
      }
    }
    updateStatus();
  }, [id, setStatus, user?.email]);

  if (loading) {
    return (
      <Alert severity="info" sx={{ m: 2 }}>
        <AlertTitle>Authentication</AlertTitle>
        Loading user information...
      </Alert>
    );
  }

  if (userError) {
    return (
      <Alert severity="error" sx={{ m: 2 }}>
        <AlertTitle>Authentication</AlertTitle>
        <>{userError}</>
      </Alert>
    );
  }

  return (
    <>
      <Box
        sx={{
          maxWidth: "md",
          width: "100%",
          display: "flex",
          flexDirection: "column",
          bgcolor: "background.paper",
          color: "foreground.paper",
          p: 4,
        }}>
        {/* <Typography variant="h2">Save Time</Typography> */}
        <Typography variant="body1">
          Upload your screenshot below and watch the magic of{" "}
          <Link
            href="https://cloud.google.com/vertex-ai/generative-ai/docs/gemini-v2"
            target="_blank"
            rel="noopener noreferrer">
            Gemini 2.0
          </Link>{" "}
          add it to your calendar! Powered by{" "}
          <Link
            href="https://firebase.google.com/docs/app-hosting"
            target="_blank"
            rel="noopener noreferrer">
            Firebase App Hosting
          </Link>
          .
        </Typography>
        {error && (
          <Alert severity="error" sx={{ m: 2 }}>
            <AlertTitle>Error</AlertTitle>
            <>{error}</>
          </Alert>
        )}
        {status && screenshot && !status.processed && <UploadProcessor />}
        {status && status.processed && !status.error && <EditCalendar />}
        {status && status.error && (
          <Alert severity="error" sx={{ m: 2 }}>
            <AlertTitle>Image Processing Error</AlertTitle>
            <>
              {status.message ||
                `An unknown error occurred processing this image`}
            </>
          </Alert>
        )}

        <UploadForm />
      </Box>
    </>
  );
}
