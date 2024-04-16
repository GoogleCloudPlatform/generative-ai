import { Card, CardContent, Grid, Typography } from "@mui/material";
import { Fragment } from "react";

export default function Comparison({ payload }) {
  console.log("payload", payload); // Log the payload to the console for debugging purposes
  return (
    <Fragment>
      <Card sx={{ maxWidth: 650, borderRadius: "20px" }}>
        <CardContent>
          <Grid container spacing={2}>
            {Object.keys(payload).map((key, index) => (
              <Grid item xs={6} key={index}>
                <Typography variant="h6" component="div">
                  {key}
                </Typography>
                <Typography variant="body2">{payload[key]}</Typography>
              </Grid>
            ))}
          </Grid>
        </CardContent>
      </Card>
    </Fragment>
  );
}
