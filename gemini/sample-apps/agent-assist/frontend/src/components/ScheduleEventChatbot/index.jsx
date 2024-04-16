import {
  Autocomplete,
  Card,
  CardActions,
  CardContent,
  Chip,
  Grid,
  TextField,
} from "@mui/material";
import { DatePicker, TimePicker } from "@mui/x-date-pickers";
import { AdapterDateFns } from "@mui/x-date-pickers/AdapterDateFns";
import { AdapterDayjs } from "@mui/x-date-pickers/AdapterDayjs";
import { LocalizationProvider } from "@mui/x-date-pickers/LocalizationProvider";
import { deDE } from "@mui/x-date-pickers/locales";
import dayjs from "dayjs";
import customParseFormat from "dayjs/plugin/customParseFormat";
import { useState } from "react";

import { format } from "date-fns";
import axios_workbench from "../../apis/workbench";
import CircularIntegration from "../CircularIntegration";
import MeetCard from "../MeetCard";

const BACKENDURL = process.env.REACT_APP_API_URL;
dayjs.extend(customParseFormat);

const emails = ["channitdak@gmail.com"];

const ScheduleEventChatbot = ({ payload }) => {
  // State variables to store the start time, end time, meet date, participants, openAlert, loading, success, and event
  const [startValue, setStartValue] = useState(
    dayjs(payload.start_time, "HH:mm").toDate(),
  );
  const [endValue, setEndValue] = useState(
    dayjs(payload.end_time, "HH:mm").toDate(),
  );
  const [meetDate, setMeetDate] = useState(dayjs(payload.date, "DD/MM/YYYY"));
  const [participants, setParticipants] = useState(payload.participants);
  const [openAlert, setOpenAlert] = useState(false);
  const [loading, setLoading] = useState(false);
  const [success, setSuccess] = useState(false);
  const [event, setEvent] = useState(null);
  const emailId = "channitdak@gmail.com";
  console.log("participants", payload.participants);
  if (participants === "undefined") {
    setParticipants([]);
  }

  // Function to handle the form submission
  const handleSubmit = async () => {
    // Format the start time, end time, and meet date to the required format
    console.log(format(startValue, "HH:mm:ss"));
    console.log(format(endValue, "HH:mm:ss"));
    console.log(meetDate.format("YYYY-MM-DD"));
    console.log("participants on submit", participants);
    // Make a POST request to the backend to create the calendar event
    axios_workbench["post"]("/users/create_calendar_event", {
      emailId: participants,
      startValue: format(startValue, "HH:mm:ss"),
      endValue: format(endValue, "HH:mm:ss"),
      meetDate: meetDate.format("YYYY-MM-DD"),
    })
      .then((result) => {
        console.log(result);
        // Set the event, set success to true, set loading to false, and open the alert
        setEvent(result.data.event);
        setSuccess(true);
        setLoading(false);
        setOpenAlert(true);
        // Close the alert after 3 seconds
        setTimeout(() => {
          setOpenAlert(false);
        }, 3000);
      })
      .catch((err) => {
        console.log(err);
      });
  };

  return (
    <>
      <Card sx={{ maxWidth: 650, borderRadius: "20px" }}>
        <CardContent>
          <Grid spacing={2} container>
            <Grid item xs={4}>
              {/* Time picker for start time */}
              <LocalizationProvider dateAdapter={AdapterDateFns}>
                <TimePicker
                  label="Start Time"
                  value={startValue}
                  onChange={setStartValue}
                  ampm={false}
                />
              </LocalizationProvider>
            </Grid>
            <Grid item xs={4}>
              {/* Time picker for end time */}
              <LocalizationProvider dateAdapter={AdapterDateFns}>
                <TimePicker
                  label="End Time"
                  value={endValue}
                  onChange={setEndValue}
                  minTime={startValue ? startValue : endValue}
                  ampm={false}
                />
              </LocalizationProvider>
            </Grid>
            <Grid item xs={4}>
              {/* Date picker for meet date */}
              <LocalizationProvider dateAdapter={AdapterDayjs} locale={deDE}>
                <DatePicker
                  label="Meet Date"
                  value={dayjs(meetDate)}
                  onChange={setMeetDate}
                  defaultValue={dayjs(new Date())}
                  minDate={dayjs(new Date())}
                  slotProps={{
                    textField: {
                      error: false,
                    },
                  }}
                />
              </LocalizationProvider>
            </Grid>
            <Grid item xs={12}>
              {/* Autocomplete for participants */}
              <Autocomplete
                multiple
                id="tags-filled"
                options={emails}
                freeSolo
                defaultValue={participants}
                renderTags={(value, getTagProps) =>
                  value.map((option, index) => (
                    <Chip
                      variant="outlined"
                      label={option}
                      {...getTagProps({ index })}
                    />
                  ))
                }
                renderInput={(params) => (
                  <TextField
                    {...params}
                    variant="outlined"
                    label="Participants"
                    placeholder="Email"
                  />
                )}
                onChange={(event, value) => setParticipants(value)}
              />
            </Grid>
          </Grid>
        </CardContent>
        <CardActions
          sx={{
            display: "flex",
            justifyContent: "flex-end",
          }}
        >
          {/* Circular integration button for scheduling the event */}
          <CircularIntegration
            loading={loading}
            success={success}
            setLoading={setLoading}
            setSuccess={setSuccess}
            handleClick={handleSubmit}
            disabled={
              startValue === null || endValue === null || meetDate === null
            }
          >
            Schedule
          </CircularIntegration>
        </CardActions>
      </Card>

      {/* Meet card to display the event details if the event is created */}
      {event !== null && <MeetCard payload={event} />}
    </>
  );
};

export default ScheduleEventChatbot;
