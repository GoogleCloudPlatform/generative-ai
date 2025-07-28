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
import Dialog from "@mui/material/Dialog";
import DialogTitle from "@mui/material/DialogTitle";
import IconButton from "@mui/material/IconButton";
import CloseIcon from "@mui/icons-material/Close";
import DialogContent from "@mui/material/DialogContent";
import Box from "@mui/material/Box";
import { Status } from "../context/StatusContext";
import FormGroup from "@mui/material/FormGroup";
import Button from "@mui/material/Button";
import AutoAwesomeIcon from "@mui/icons-material/AutoAwesome";

interface Props {
  open: boolean;
  handleClose: () => void;
  upload: () => void;
}

export default function Preview({ open, handleClose, upload }: Props) {
  const { screenshot } = Status();
  if (screenshot) {
    return (
      <Dialog fullWidth={true} maxWidth="md" open={open}>
        <DialogTitle>Image Preview</DialogTitle>
        <IconButton
          aria-label="close"
          onClick={handleClose}
          sx={(theme) => ({
            position: "absolute",
            right: 8,
            top: 8,
            color: theme.palette.grey[500],
          })}
        >
          <CloseIcon />
        </IconButton>
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
              objectFit: "contain",
            }}
          >
            <Box
              component="img"
              sx={{
                width: "100%",
                height: "85%",
                objectFit: "contain",
              }}
              src={`data:${screenshot.type};base64,${screenshot?.base64}`}
              alt="Screenshot"
            />
          </Box>
          <FormGroup>
              <Button type="submit" variant="contained" endIcon={<AutoAwesomeIcon />} sx={{ mt: 2 }} onClick={upload}>
                Process Image
              </Button>
            </FormGroup>
        </DialogContent>
      </Dialog>
    );
  }
}
