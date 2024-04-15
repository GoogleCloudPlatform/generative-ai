import { Grid, Typography } from "@mui/material"; // Import the necessary components from Material UI
import PropTypes from "prop-types"; // Import PropTypes for type checking

const PopUpContactedDetails = (props) => {
  // This component displays the contacted details in a pop-up window.
  return (
    <>
      <Grid item xs={6}>
        <Typography
          variant="h6"
          display="inline-block"
          sx={{ marginRight: "8px" }}
        >
          Name:
        </Typography>
        <Typography variant="h6" display="inline-block" fontWeight={"normal"}>
          &nbsp; {props.Name}
        </Typography>
      </Grid>
      <Grid item xs={6}>
        <Typography
          variant="h6"
          display="inline-block"
          sx={{ marginRight: "8px" }}
        >
          City:
        </Typography>
        <Typography variant="h6" display="inline-block" fontWeight={"normal"}>
          &nbsp; {props.City}
        </Typography>
      </Grid>

      <Grid item xs={6}>
        <Typography variant="h6" display="inline-block">
          Contact Number:
        </Typography>
        <Typography variant="h6" display="inline-block" fontWeight={"normal"}>
          &nbsp; {props.PhoneNumber}
        </Typography>
      </Grid>
      <Grid item xs={6}>
        <Typography variant="h6" display="inline-block">
          Email:
        </Typography>
        <Typography variant="h6" display="inline-block" fontWeight={"normal"}>
          &nbsp; {props.Email}
        </Typography>
      </Grid>
    </>
  );
};

// Define the propTypes for the component
PopUpContactedDetails.propTypes = {
  Name: PropTypes.string,
  City: PropTypes.string,
  PhoneNumber: PropTypes.string,
  Email: PropTypes.string,
};

// Define the defaultProps for the component
PopUpContactedDetails.defaultProps = {
  Name: "Channit Dak",
  City: "Bangalore",
  PhoneNumber: "+91 9876543210",
  Email: "channitdak@gmail.com",
};

export default PopUpContactedDetails;
