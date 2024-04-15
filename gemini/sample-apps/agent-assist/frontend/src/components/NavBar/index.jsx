import AppBar from "@mui/material/AppBar"; // Import the AppBar component from MUI
import Box from "@mui/material/Box"; // Import the Box component from MUI
import Button from "@mui/material/Button"; // Import the Button component from MUI
import Toolbar from "@mui/material/Toolbar"; // Import the Toolbar component from MUI
import Typography from "@mui/material/Typography"; // Import the Typography component from MUI
import * as React from "react"; // Import the React library

export default function NavBar() {
  // Define the NavBar component
  return (
    <Box>
      {/* Create an AppBar with a static position */}
      <AppBar position="static">
        {/* Create a Toolbar with a custom style */}
        <Toolbar
          style={{
            display: "flex",
            justifyContent: "space-between",
            backgroundColor: "#1976d2",
          }}
        >
          {/* Create a Typography component for the app title */}
          <Typography variant="h6" component="div" className="float-left">
            KAVACH INSURANCE
          </Typography>
          {/* Create a div to hold the buttons */}
          <div>
            {/* Create a Button component for the Workbench */}
            <Button color="inherit">Workbench</Button>
            {/* Create a Button component for the Analytics */}
            <Button color="inherit">Analytics</Button>
            {/* Create a Button component for the Etc. */}
            <Button color="inherit">Etc.</Button>
          </div>
        </Toolbar>
      </AppBar>
    </Box>
  );
}
