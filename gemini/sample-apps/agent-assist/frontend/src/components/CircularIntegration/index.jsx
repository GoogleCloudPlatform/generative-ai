import Box from "@mui/material/Box";
import Button from "@mui/material/Button";
import CircularProgress from "@mui/material/CircularProgress";
import { green } from "@mui/material/colors";
import * as React from "react";

// This component is a button that shows a circular progress indicator when loading is true.
// When the button is clicked, the handleClick function is called.
function CircularIntegration({
  loading,
  setLoading,
  success,
  setSuccess,
  handleClick,
  disabled,
  children,
}) {
  // The buttonSx object is used to style the button.
  // If success is true, the button will have a green background and a green hover color.
  const buttonSx = {
    ...(success && {
      bgcolor: green[500],
      "&:hover": {
        bgcolor: green[700],
      },
    }),
  };

  // The handleButtonClick function is called when the button is clicked.
  // If loading is false, it sets success to false, sets loading to true, and calls the handleClick function.
  const handleButtonClick = () => {
    if (!loading) {
      setSuccess(false);
      setLoading(true);
      handleClick();
    }
  };

  // The component returns a Box with a Button and a CircularProgress.
  // The Button is disabled if loading or success is true.
  // The CircularProgress is shown if loading is true.
  return (
    <Box sx={{ display: "flex", alignItems: "center" }}>
      <Box sx={{ m: 1, position: "relative" }}>
        <Button
          variant="contained"
          sx={buttonSx}
          disabled={loading || success}
          onClick={handleButtonClick}
        >
          {children}
        </Button>
        {loading && (
          <CircularProgress
            size={24}
            sx={{
              color: green[500],
              position: "absolute",
              top: "50%",
              left: "50%",
              marginTop: "-12px",
              marginLeft: "-12px",
            }}
          />
        )}
      </Box>
    </Box>
  );
}

// The defaultProps object sets the default values for the props.
CircularIntegration.defaultProps = {
  disabled: false,
};

export default CircularIntegration;
