import { Card, CardContent, Typography } from "@mui/material"; // Import the necessary components from Material UI
import { Fragment } from "react"; // Import the Fragment component from React
import Markdown from "react-markdown"; // Import the Markdown component from react-markdown

export default function MarkdownWidget({ payload }) {
  // This component renders a Markdown widget that displays the given payload as Markdown
  return (
    <Fragment>
      <Card sx={{ maxWidth: 650, borderRadius: "20px" }}>
        <CardContent>
          {/* The CardContent component is used to hold the Markdown content */}
          <Typography align="left">
            {/* The Typography component is used to display the Markdown content */}
            <Markdown>
              {/* The Markdown component is used to parse and render the Markdown content */}
              {payload}
            </Markdown>
          </Typography>
        </CardContent>
      </Card>
    </Fragment>
  );
}
