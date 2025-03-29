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
import DialogContent from "@mui/material/DialogContent";
import DialogTitle from "@mui/material/DialogTitle";
import FormGroup from "@mui/material/FormGroup";
import TextField from "@mui/material/TextField";
import { Status } from "../context/StatusContext";
import Grid from "@mui/material/Grid";
import { useState } from "react";
import { LocalizationProvider } from "@mui/x-date-pickers/LocalizationProvider";
import { AdapterDayjs } from "@mui/x-date-pickers/AdapterDayjs";
import { DateTimePicker } from "@mui/x-date-pickers/DateTimePicker";
import dayjs from "dayjs";
import EventAvailableIcon from "@mui/icons-material/EventAvailable";
import Button from "@mui/material/Button";
import { addEvent } from "@/libs/calendar/calendar";
import Alert from "@mui/material/Alert";
import AlertTitle from "@mui/material/AlertTitle";
import IconButton from "@mui/material/IconButton";
import CloseIcon from "@mui/icons-material/Close";
import DialogActions from "@mui/material/DialogActions";
import Box from "@mui/material/Box";

export default function EditCalendar() {
  const [saving, setSaving] = useState<boolean>(false);
  const [error, setError] = useState<string>("");
  const { status, screenshot, setStatus, reset, updateEvent } = Status();
  const [successOpen, setSuccessOpen] = useState<boolean>(false);

  function handleSuccessClose() {
    setSuccessOpen(false);
    reset();
  }

  const disabled = saving;

  async function save(e: React.FormEvent) {
    e.preventDefault();
    try {
      setSaving(true);
      setError("");
      if (status.event) {
        const r = await addEvent(status.event);
        if (!r.ok) {
          if (r.error) {
            setError(`${r.error}`);
          }
          return;
        }
        status.active = false;
        setStatus(status);
        setSuccessOpen(true);
      }
    } catch (error) {
      console.error(error);
      setError(`${error}`);
    } finally {
      setSaving(false);
    }
  }

  function handleClose() {
    reset();
  }

  return (
    <>
      <Dialog maxWidth="md" open={successOpen}>
        <DialogTitle>Added to Calendar</DialogTitle>
        <IconButton
          aria-label="close"
          onClick={handleSuccessClose}
          sx={(theme) => ({
            position: "absolute",
            right: 8,
            top: 8,
            color: theme.palette.grey[500],
          })}>
          <CloseIcon />
        </IconButton>
        <DialogContent>
          Your event has been successfully added to your calendar.
        </DialogContent>
        <DialogActions>
          <Button onClick={handleSuccessClose} autoFocus>
            Close
          </Button>
          <Button
            href="https://calendar.google.com/"
            target="_blank"
            rel="noopener noreferrer"
            autoFocus>
            View
          </Button>
        </DialogActions>
      </Dialog>
      <Dialog
        fullWidth={true}
        maxWidth="md"
        open={status.active && status.processed}>
        <DialogTitle>
          {status.event?.summary} at {status.event?.location}
        </DialogTitle>
        <IconButton
          aria-label="close"
          onClick={handleClose}
          sx={(theme) => ({
            position: "absolute",
            right: 8,
            top: 8,
            color: theme.palette.grey[500],
          })}>
          <CloseIcon />
        </IconButton>
        <DialogContent>
          {screenshot && (
            <Box
              sx={{
                display: "flex",
                flexDirection: "column",
                m: "auto",
                maxWidth: "sm",
                width: "fit-content",
                overflow: "auto",
                height: "10vh",
                objectFit: "contain",
              }}>
              <Box
                component="img"
                sx={{
                  width: "100%",
                  height: "85%",
                  objectFit: "contain",
                }}
                src={`data:${screenshot.type};base64,${screenshot.base64}`}
                alt="Screenshot"
              />
            </Box>
          )}
          <form onSubmit={save}>
            <FormGroup>
              <TextField
                sx={{ width: "100%", mt: 1 }}
                value={status.event?.summary}
                onChange={(e) => updateEvent("summary", e.target.value)}
                label="Title"
                placeholder="Event Title"
                disabled={disabled}
              />
              <TextField
                sx={{ width: "100%", mt: 1 }}
                value={status.event?.location}
                onChange={(e) => updateEvent("location", e.target.value)}
                label="Location"
                placeholder="Event Location"
                disabled={disabled}
              />
            </FormGroup>
            <LocalizationProvider dateAdapter={AdapterDayjs}>
              <Grid container spacing={1}>
                <Grid size={{ xs: 12, sm: 6 }}>
                  <DateTimePicker
                    label="Start"
                    value={dayjs(status?.event?.start || new Date())}
                    onChange={(e) =>
                      updateEvent("start", e?.toDate() || new Date())
                    }
                    sx={{ width: "100%", mt: 1 }}
                    disabled={disabled}
                  />
                </Grid>
                <Grid size={{ xs: 12, sm: 6 }}>
                  <DateTimePicker
                    label="End"
                    value={dayjs(status?.event?.end || new Date())}
                    onChange={(e) =>
                      updateEvent("end", e?.toDate() || new Date())
                    }
                    sx={{ width: "100%", mt: 1 }}
                    disabled={disabled}
                  />
                </Grid>
              </Grid>
            </LocalizationProvider>
            <FormGroup>
              <TextField
                sx={{ width: "100%", mt: 1 }}
                value={status.event?.description}
                onChange={(e) => updateEvent("description", e.target.value)}
                label="Description"
                placeholder="Event Description"
                multiline={true}
                rows={4}
                disabled={disabled}
              />
            </FormGroup>
            {error && (
              <Alert severity="error" sx={{ mb: 2 }}>
                <AlertTitle>Calendar Error</AlertTitle>
                <>{error}</>
              </Alert>
            )}
            <FormGroup>
              <Button
                type="submit"
                loading={saving}
                disabled={disabled}
                variant="contained"
                endIcon={<EventAvailableIcon />}
                sx={{ mt: 2 }}>
                Add to Calendar
              </Button>
            </FormGroup>
          </form>
        </DialogContent>
      </Dialog>
    </>
  );
}
