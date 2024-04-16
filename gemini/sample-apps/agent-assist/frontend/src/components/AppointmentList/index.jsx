import { Card, CardContent, Grid, Typography } from "@mui/material";
import Appointment from "./Appointment";

// This component displays a list of appointments.
export default function AppointmentList({ payload }) {
  const events = payload; // Renamed to 'events' for clarity

  console.log("events", events); // Log the events for debugging purposes

  return (
    <Card sx={{ maxWidth: 650 }}>
      <CardContent>
        <Typography variant="h5" color="primary" align="left">
          Appointments
        </Typography>
        <br />
        {events.length > 0 && (
          <Grid
            container
            spacing={2}
            sx={{ overflowY: "scroll", maxHeight: "250px" }}
          >
            {events.map((event) => (
              <Grid item xs={12} marginBottom={2}>
                <Appointment event={event} />
              </Grid>
            ))}
          </Grid>
        )}
        {events.length === 0 && (
          <Typography variant="body-md" align="left">
            No Upcoming Appointments
          </Typography>
        )}
      </CardContent>
    </Card>
  );
}

//default props
AppointmentList.defaultProps = {
  payload: [],
};
