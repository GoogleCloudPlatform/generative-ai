import CommentIcon from "@mui/icons-material/Comment";
import { Box, Grid, IconButton } from "@mui/material";
import { Fragment, useState } from "react";
import { Outlet } from "react-router-dom";
import AppBar from "../../components/AppBar";
import Bot from "../../components/Chatbot";
import Copyright from "../../components/Copyright";

export default function Layout() {
  // State to control the visibility of the chatbot
  const [open, setOpen] = useState(false);

  // Styles for the second item in the footer
  const secondItemStyle = {
    height: "10px",
  };

  // Function to open the chatbot
  const onClick = () => {
    setOpen(true);
  };

  return (
    <Fragment>
      <Box
        sx={{
          display: "flex",
          flexDirection: "column",
          minHeight: "100vh",
        }}
      >
        <AppBar />
        <Outlet />
        <Bot open={open} setOpen={setOpen} />
        <Box
          component="footer"
          sx={{
            py: 3,
            px: 2,
            mt: "auto",
            backgroundColor: (theme) =>
              theme.palette.mode === "light"
                ? theme.palette.grey[200]
                : theme.palette.grey[800],
            position: "relative",
            bottom: 0,
            width: "100%",
          }}
        >
          <Grid container justifyContent="center">
            <Copyright />
          </Grid>
        </Box>
        {/* Floating action button to open the chatbot */}
        <IconButton
          style={{
            position: "fixed",
            bottom: "16px",
            right: "16px",
            zIndex: 1000,
          }}
          color="primary"
          aria-label="Chat"
          size="large"
          onClick={onClick}
        >
          <CommentIcon fontSize="large" />
        </IconButton>
      </Box>
    </Fragment>
  );
}
