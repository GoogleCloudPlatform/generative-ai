import PersonIcon from "@mui/icons-material/Person"; // Icon for the person
import Button from "@mui/joy/Button"; // Button component
import Card from "@mui/joy/Card"; // Card component
import CardActions from "@mui/joy/CardActions"; // Card actions component
import CardContent from "@mui/joy/CardContent"; // Card content component
import CircularProgress from "@mui/joy/CircularProgress"; // Circular progress component
import Typography from "@mui/joy/Typography"; // Typography component
import * as React from "react"; // React library

export default function Appointment({ event }) {
  // Appointment component

  // Extract the start and end date and time from the event
  const startDateTime = new Date(event.start.dateTime);
  const endDateTime = new Date(event.end.dateTime);

  // Format the date and time using the options object
  const options = { hour: "numeric", minute: "numeric", hour12: true };
  const date = startDateTime.toLocaleDateString("en-IN");
  const startTime = startDateTime.toLocaleTimeString("en-IN", options);
  const endTime = endDateTime.toLocaleTimeString("en-IN", options);
  const time = `${startTime} - ${endTime}`;

  return (
    <Card variant="solid" color="primary" invertedColors>
      <CardContent orientation="horizontal">
        <CircularProgress size="lg" determinate value={20}>
          <PersonIcon fontSize="large" />
        </CircularProgress>
        <CardContent>
          <Typography level="body-md">Meeting with</Typography>
          <Typography level="h5">{event.attendees[1].email}</Typography>
        </CardContent>
      </CardContent>
      <CardActions>
        <Button variant="soft" size="sm">
          {date}
        </Button>
        <Button variant="solid" size="sm">
          {time}
        </Button>
      </CardActions>
    </Card>
  );
}
