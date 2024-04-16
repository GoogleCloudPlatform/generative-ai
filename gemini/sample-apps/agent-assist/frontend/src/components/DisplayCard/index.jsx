import { Card, CardContent, Typography } from "@mui/material";
import CountUp from "react-countup";

const DisplayCard = (props) => {
  let { metric, value, period, animation, percent, decimal } = props;
  // This card component displays a metric, its value, and a period.
  // It can also animate the value using CountUp and display a percentage sign if needed.
  return (
    <Card sx={{ minWidth: 275 }}>
      <CardContent>
        <Typography
          variant="h5"
          color="text.secondary"
          component="div"
          align="center"
        >
          {metric}
        </Typography>

        <Typography
          variant="h3"
          component="div"
          align={"center"}
          sx={{ fontSize: "3em" }}
        >
          {!animation && value}
          {decimal && <CountUp end={value} duration={2} decimals={2} />}
          {percent && "%"}
          {!decimal && !percent && animation && (
            <CountUp end={value} duration={2} />
          )}
        </Typography>
        <Typography sx={{ mb: 1.5 }} color="text.secondary" align="center">
          {"(" + period + ")"}
        </Typography>
      </CardContent>
    </Card>
  );
};

DisplayCard.defaultProps = {
  description: "description",
  metric: "Metric",
  value: "value",
  period: "period",
  animation: false,
  percent: false,
  decimal: false,
};

export default DisplayCard;
