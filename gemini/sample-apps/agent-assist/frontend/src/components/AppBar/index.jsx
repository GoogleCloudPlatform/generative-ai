import * as React from "react";
import AppBar from "@mui/material/AppBar";
import Box from "@mui/material/Box";
import CssBaseline from "@mui/material/CssBaseline";
import Divider from "@mui/material/Divider";
import List from "@mui/material/List";
import ListItem from "@mui/material/ListItem";
import ListItemButton from "@mui/material/ListItemButton";
import ListItemText from "@mui/material/ListItemText";
import Toolbar from "@mui/material/Toolbar";
import Typography from "@mui/material/Typography";
import Button from "@mui/material/Button";
import { Link, useNavigate } from "react-router-dom";
import FactCheckIcon from "@mui/icons-material/FactCheck";
import QueryStatsIcon from "@mui/icons-material/QueryStats";

// This array contains the navigation items that will be displayed in the drawer.
const navItems = ["Client", "Claim Reviewer", "Analytics"];

// This function is responsible for rendering the drawer.
function DrawerAppBar(props) {
  // The `window` prop is used to determine the size of the screen.
  const { window } = props;
  // The `mobileOpen` state variable is used to control the visibility of the drawer on mobile devices.
  const [mobileOpen, setMobileOpen] = React.useState(false);
  // This function is used to toggle the visibility of the drawer on mobile devices.
  const handleDrawerToggle = () => {
    setMobileOpen((prevState) => !prevState);
  };

  // This is the content of the drawer.
  const drawer = (
    <Box onClick={handleDrawerToggle} sx={{ textAlign: "center" }}>
      <Typography variant="h6" sx={{ my: 2 }}>
        Kavach Insurance
      </Typography>
      <Divider />
      <List>
        {navItems.map((item) => (
          <ListItem key={item} disablePadding>
            <ListItemButton sx={{ textAlign: "center" }}>
              <ListItemText primary={item} />
            </ListItemButton>
          </ListItem>
        ))}
      </List>
    </Box>
  );

  // This is the container for the drawer.
  const container =
    window !== undefined ? () => window().document.body : undefined;
  // This is used to navigate to different pages.
  const navigate = useNavigate();

  return (
    <Box sx={{ display: "flex" }}>
      <CssBaseline />
      <AppBar component="nav">
        <Toolbar>
          <Typography
            variant="h6"
            component="div"
            sx={{
              flexGrow: 1,
              display: { xs: "none", sm: "block" },
              cursor: "pointer",
            }}
            onClick={() => navigate("/")}
          >
            Kavach Insurance
          </Typography>
          <Box sx={{ display: { xs: "none", sm: "block" } }}>
            <Button
              key={"Workbench"}
              sx={{ color: "#fff", paddingRight: "10px" }}
              component={Link}
              to="/workbench"
              startIcon={<QueryStatsIcon />}
            >
              {"Dashboard"}
            </Button>

            <Button
              key={"Agent Assist"}
              sx={{ color: "#fff", paddingLeft: "10px" }}
              component={Link}
              to="/agent_assist"
              startIcon={<FactCheckIcon />}
            >
              {"Workbench"}
            </Button>
          </Box>
        </Toolbar>
      </AppBar>

      <Box component="main" sx={{ p: 3 }}>
        <Toolbar />
      </Box>
    </Box>
  );
}

export default DrawerAppBar;
