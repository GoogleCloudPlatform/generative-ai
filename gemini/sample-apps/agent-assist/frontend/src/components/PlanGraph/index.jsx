import { Card, CardContent } from "@mui/material"; // Import the necessary components from Material UI
import { Fragment } from "react"; // Import the Fragment component from React

export default function PlanGraph({ payload }) {
  // This component displays a graph based on the payload received as a prop
  return (
    <Fragment>
      <Card sx={{ maxWidth: 650, borderRadius: "20px" }}>
        {/* The Card component is used to display the graph */}
        <CardContent>
          {/* The CardContent component is used to contain the graph */}
          <img src={`data:image/png;base64,${payload}`} alt="Matplotlib Plot" />
          {/* The image tag is used to display the graph */}
        </CardContent>
      </Card>
    </Fragment>
  );
}
