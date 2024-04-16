import ChartCard from "./ChartCard";

export default function CustomerManagementChart(props) {
  // Destructure the `data` prop from the props object.
  const { data } = props;

  // Define the property names for the x-axis and two y-axes.
  const x = "months";
  const y1 = "Active Customers";
  const y2 = "Satisfaction Score";

  // Return the `ChartCard` component, passing in the `data`, `x`, `y1`, and `y2` props.
  return <ChartCard data={data} x={x} y1={y1} y2={y2} />;
}
