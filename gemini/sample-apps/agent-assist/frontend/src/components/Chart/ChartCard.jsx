import { Grid, Paper } from "@mui/material";
import Chart from ".";

// This component is a wrapper around the Chart component, and it provides a consistent styling and layout for all charts.
// The data, x, y1, y2, and title props are passed down to the Chart component.
// The Chart component is responsible for rendering the actual chart.
// The ChartCard component is used in the Dashboard component to display a grid of charts.

const ChartCard = ({ data, x, y1, y2, title }) => {
  return (
    <Grid container spacing={3}>
      <Grid item xs={12}>
        <Paper
          sx={{
            p: 2,
            display: "flex",
            flexDirection: "column",
            height: 290,
          }}
        >
          <Chart title={title} data={data} x={x} y1={y1} y2={y2} />
        </Paper>
      </Grid>
    </Grid>
  );
};

export default ChartCard;
