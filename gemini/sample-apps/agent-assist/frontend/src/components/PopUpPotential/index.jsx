import {
  Dialog,
  DialogContent,
  DialogTitle,
  Grid,
  Typography,
} from "@mui/material";
import ComposeMail from "../ComposeMail";
import PopUpContactedDetails from "../PopUpContactedDetails";
import SalesPitch from "../SalesPitch";

const PopUpPotential = (props) => {
  const { row, openPopUp, setOpenPopUp, isReviewer } = props;

  // Function to close the dialog
  const handleClose = () => {
    setOpenPopUp(false);
  };

  return (
    <Dialog open={openPopUp} onClose={handleClose} fullWidth maxWidth="md">
      <DialogTitle>
        <Typography color="primary" variant="h5" display="inline-block">
          CUSTOMER DETAILS
        </Typography>
      </DialogTitle>
      <DialogContent>
        <Grid container spacing={2} columns={12}>
          {/* Display the customer's contact details */}
          <PopUpContactedDetails
            Name={row.Name}
            Email={row.Email}
            PhoneNumber={row.PhoneNumber}
            City={row.City}
          />
          {/* Display the sales pitch */}
          <SalesPitch />
          {/* Display the compose mail component */}
          <ComposeMail emailId={row.Email} />
        </Grid>
      </DialogContent>
    </Dialog>
  );
};

// default props
PopUpPotential.defaultProps = {
  row: {
    Name: "Channit Dak",
    Email: "channitdak@gmail.com",
    Phone: "9876543210",
    City: "Hyderabad",
    EmailSummary:
      "Lorem Ipsum is simply dummy text of the printing and typesetting industry. Lorem Ipsum has been the industry's standard dummy text ever since the 1500s",
    LastContactedDate: "2022-01-01",
  },
  isReviewer: false,
  openPopUp: false,
  setOpenPopUp: () => {},
};

export default PopUpPotential;
