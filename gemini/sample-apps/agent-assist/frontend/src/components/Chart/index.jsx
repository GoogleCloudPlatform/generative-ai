import { Tooltip, Typography } from "@mui/material";
import { useTheme } from "@mui/material/styles";
import * as React from "react";
import {
  Label,
  Legend,
  Line,
  LineChart,
  ResponsiveContainer,
  XAxis,
  YAxis,
} from "recharts";

const Chart = (props) => {
  const { data, x, y1, y2, title } = props;
  const theme = useTheme();

  // This is the main chart component that renders the line chart.
  return (
    <React.Fragment>
      <Typography component="h2" variant="h6" color="primary" gutterBottom>
        {title}
      </Typography>
      <ResponsiveContainer>
        <LineChart
          data={data}
          margin={{
            top: 16,
            right: 16,
            bottom: 0,
            left: 24,
          }}
        >
          <XAxis
            dataKey="x"
            stroke={theme.palette.text.secondary}
            style={theme.typography.body2}
          />

          <YAxis
            stroke={theme.palette.text.secondary}
            style={theme.typography.body2}
            yAxisId="y1"
          >
            <Label
              angle={270}
              position="left"
              style={{
                textAnchor: "middle",
                fill: theme.palette.text.primary,
                ...theme.typography.body1,
              }}
            >
              {y1}
            </Label>
          </YAxis>
          {y2 && (
            <YAxis
              stroke={theme.palette.text.secondary}
              style={theme.typography.body2}
              yAxisId="y2"
              orientation="right"
            >
              <Label
                angle={270}
                position="right"
                style={{
                  textAnchor: "middle",
                  fill: theme.palette.text.primary,
                  ...theme.typography.body1,
                }}
              >
                {y2}
              </Label>
            </YAxis>
          )}

          <Tooltip />
          <Legend />
          <Line
            type="monotone"
            dataKey="y1"
            name={y1}
            stroke="#8884d8"
            yAxisId="y1"
          />
          {y2 && (
            <Line
              type="monotone"
              dataKey="y2"
              name={y2}
              stroke="#82ca9d"
              yAxisId="y2"
            />
          )}
        </LineChart>
      </ResponsiveContainer>
    </React.Fragment>
  );
};

// These are the default props for the chart component.
Chart.defaultProps = {
  data: [],
  x: "x",
  y1: null,
  y2: null,
  title: "Chart",
};

export default Chart;
