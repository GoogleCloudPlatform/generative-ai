import ChartCard from "./ChartCard";

// This component displays a chart that shows the number of leads generated and the sales pipeline value for each platform.
export default function LeadsChart(props) {
  // The data prop is an array of objects, each of which represents a platform.
  const { data } = props;
  // The x-axis of the chart will show the platform names.
  const x = "Platforms";
  // The y1-axis of the chart will show the number of leads generated for each platform.
  const y1 = "Leads Generated";
  // The y2-axis of the chart will show the sales pipeline value for each platform.
  const y2 = "Sales Pipeline Value";

  // The ChartCard component takes the following props:
  // - title: The title of the chart.
  // - data: The data to be displayed in the chart.
  // - x: The x-axis label.
  // - y1: The y1-axis label.
  // - y2: The y2-axis label.
  return (
    <ChartCard title="Platform Wise Data" data={data} x={x} y1={y1} y2={y2} />
  );
}
