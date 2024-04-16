import ExpandMoreIcon from "@mui/icons-material/ExpandMore";
import {
  Accordion,
  AccordionDetails,
  AccordionSummary,
  Alert,
  Box,
  Button,
  Collapse,
  Grid,
  Typography,
} from "@mui/material";
import { DatePicker, TimePicker } from "@mui/x-date-pickers";
import { AdapterDateFns } from "@mui/x-date-pickers/AdapterDateFns";
import { AdapterDayjs } from "@mui/x-date-pickers/AdapterDayjs";
import { LocalizationProvider } from "@mui/x-date-pickers/LocalizationProvider";
import { deDE } from "@mui/x-date-pickers/locales";
import { format } from "date-fns";
import dayjs from "dayjs";
import { useState } from "react";
import axios_workbench from "../../apis/workbench";

const BACKENDURL = process.env.REACT_APP_API_URL;

const EventTimeInput = () => {
  const [startValue, setStartValue] = useState(null); // State variable to store the start time
  const [endValue, setEndValue] = useState(null); // State variable to store the end time
  const [meetDate, setMeetDate] = useState(null); // State variable to store the meeting date
  const [openAlert, setOpenAlert] = useState(false); // State variable to control the visibility of the alert

  const emailId = "channitdak@gmail.com"; // Hardcoded email ID for testing purposes

  const handleSubmit = async () => {
    // Function to handle the form submission
    console.log(format(startValue, "HH:mm:ss")); // Log the formatted start time
    console.log(format(endValue, "HH:mm:ss")); // Log the formatted end time
    console.log(meetDate.format("YYYY-MM-DD")); // Log the formatted meeting date
    axios_workbench["post"]("/users/create_calendar_event", {
      emailId: emailId,
      startValue: format(startValue, "HH:mm:ss"),
      endValue: format(endValue, "HH:mm:ss"),
      meetDate: meetDate.format("YYYY-MM-DD"),
    }) // Make a POST request to the backend API to create a calendar event
      .then((result) => {
        console.log(result); // Log the result of the API call
        setOpenAlert(true); // Set the openAlert state to true to show the alert
        setTimeout(() => {
          setOpenAlert(false); // Set the openAlert state to false to hide the alert after 3 seconds
        }, 3000);
      })
      .catch((err) => {
        console.log(err); // Log any errors that occur during the API call
      });
  };

  return (
    <>
      <Accordion sx={{ marginTop: "16px", width: "100%" }} elevation={0}>
        <AccordionSummary
          expandIcon={<ExpandMoreIcon />}
          aria-controls="panel1a-content"
          id="panel1a-header"
        >
          <Typography variant="h6" color={"primary"} fontWeight={"normal"}>
            Set Up a Meeting
          </Typography>
        </AccordionSummary>
        <AccordionDetails>
          <Grid spacing={2} container sx={{ width: "100%" }}>
            <Grid item xs={3}>
              <LocalizationProvider dateAdapter={AdapterDateFns}>
                <TimePicker
                  label="Start Time"
                  value={startValue}
                  onChange={setStartValue}
                  ampm={false}
                />
              </LocalizationProvider>
            </Grid>
            <Grid item xs={3}>
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

            <Grid item xs={3}>
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
            <Grid item xs={3}>
              <Button
                variant="contained"
                size="large"
                onClick={handleSubmit}
                disabled={
                  startValue === null || endValue === null || meetDate === null
                }
              >
                Set Up
              </Button>
            </Grid>
          </Grid>
          <Box sx={{ width: "100%", marginTop: "16px" }}>
            <Collapse in={openAlert}>
              <Alert>Meet scheduled successfully!</Alert>
            </Collapse>
          </Box>
        </AccordionDetails>
      </Accordion>
    </>
  );
};

export default EventTimeInput;
