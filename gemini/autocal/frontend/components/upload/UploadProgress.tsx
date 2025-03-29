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

import Box from "@mui/material/Box";
import Dialog from "@mui/material/Dialog";
import DialogContent from "@mui/material/DialogContent";
import DialogTitle from "@mui/material/DialogTitle";
import LinearProgress from "@mui/material/LinearProgress";
import { Status } from "../context/StatusContext";

export default function UploadProgress() {
  const { status, screenshot } = Status();

  return (
    <Dialog fullWidth={true} maxWidth="xl" open={status.active && !status.processed}>
      <DialogTitle>Processing</DialogTitle>
      <DialogContent>
        <Box
          sx={{
            display: "flex",
            flexDirection: "column",
            m: "auto",
            maxWidth: "sm",
            width: "fit-content",
            overflow: "auto",
            height: "80vh",
            objectFit: "contain"

          }}
        >
          {screenshot && (
            <Box
              component="img"
              sx={{
                width: "100%",
                height: "95%",
                objectFit: "contain"
              }}
              src={`data:${screenshot.type};base64,${screenshot?.base64}`}
              alt="Screenshot"
            />
          )}
          <LinearProgress />
        </Box>
      </DialogContent>
    </Dialog>
  );
}
