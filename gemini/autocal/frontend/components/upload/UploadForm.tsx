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
import Button from "@mui/material/Button";
import AutoAwesomeIcon from "@mui/icons-material/AutoAwesome";
import { styled } from "@mui/material/styles";
import {
  clientFirestore,
  firebaseAuth,
  firebaseStorage,
} from "@/libs/firebase/client/clientApp";
import { doc, runTransaction } from "firebase/firestore";
import { Status } from "../context/StatusContext";
import { ref, uploadString } from "firebase/storage";
import {
  ProcessedScreenshot,
  processedScreenshotConverter,
  ScreenshotUpload,
  screenshotUploadConverter,
} from "@/libs/schema/schema";
import { useState } from "react";
import { useAuthState } from "react-firebase-hooks/auth";
import Preview from "./Preview";

const VisuallyHiddenInput = styled("input")({
  clip: "rect(0 0 0 0)",
  clipPath: "inset(50%)",
  height: 1,
  overflow: "hidden",
  position: "absolute",
  bottom: 0,
  left: 0,
  whiteSpace: "nowrap",
  width: 1,
});

export default function UploadForm() {
  const [loading, setLoading] = useState<boolean>(false);
  const [showPreview, setShowPreview] = useState<boolean>(false);
  const { status, id, setError, screenshot, setScreenshot } = Status();
  const [user, userLoading] = useAuthState(firebaseAuth);
  const [fileKey, setFileKey] = useState<Date | null>();

  const disabled = loading || userLoading;

  async function upload() {
    try {
      setLoading(true);

      // Clear the current file selection so the same item can be re-uploaded
      setFileKey(new Date());

      if (!user || !user.email) {
        setError(
          "You must be logged in with a valid email address to upload a screenshot"
        );
        return;
      }
      if (!screenshot) {
        console.error("Screenshot is null");
        return;
      }

      const filePath = `screenshots/${user.email}/${id}-${screenshot.name}`;
      const docId = `${user.email}-${id}`;

      // Upload to Google Cloud Storage
      const storageRef = ref(firebaseStorage, filePath);
      await uploadString(storageRef, screenshot.base64, "base64");

      // Payload to save
      const screenshotUpload: ScreenshotUpload = {
        ID: docId,
        image: `gs://${firebaseStorage.app.options.storageBucket}/${filePath}`,
        type: screenshot.type,
      };
      status.active = true;
      const s: ProcessedScreenshot = {
        ID: docId,
        image: filePath,
        ...status,
      };

      const screenshotDocRef = doc(
        clientFirestore,
        "screenshots",
        docId
      ).withConverter(screenshotUploadConverter);
      const uploadDocRef = doc(clientFirestore, "state", docId).withConverter(
        processedScreenshotConverter
      );
      // Run as a transaction to update both collections at the same time
      await runTransaction(clientFirestore, async (transaction) => {
        transaction.set(screenshotDocRef, screenshotUpload);
        transaction.set(uploadDocRef, s);
      });
      setShowPreview(false);
    } catch (error) {
      console.error("Error uploading image:", error);
      setError(`${error}`);
    } finally {
      setLoading(false);
      setShowPreview(false);
    }
  }

  async function preview(files: FileList | null) {
    try {
      if (!files) {
        return;
      }
      if (!user || !user.email) {
        setError(
          "You must be logged in with a valid email address to upload a screenshot"
        );
        return;
      }
      const file = files[0];
      const buffer = Buffer.from(await file.arrayBuffer());
      const data = buffer.toString("base64");
      const screenshot = { base64: data, name: file.name, type: file.type };
      setShowPreview(true);
      setScreenshot(screenshot);
    } catch (error) {
      console.error(error);
    } finally {
      setLoading(false);
    }
  }

  return (
    <>
      <Preview
        open={showPreview}
        handleClose={() => setShowPreview(false)}
        upload={upload}
      />
      <Button
        component="label"
        role={undefined}
        variant="contained"
        tabIndex={-1}
        endIcon={<AutoAwesomeIcon />}
        disabled={disabled}
        loading={loading}
        sx={{ mt: 2 }}>
        Process Screenshot with Gemini
        <VisuallyHiddenInput
          type="file"
          key={fileKey?.toString() || ""}
          onChange={(event) => preview(event.target.files)}
          multiple={false}
        />
      </Button>
    </>
  );
}
