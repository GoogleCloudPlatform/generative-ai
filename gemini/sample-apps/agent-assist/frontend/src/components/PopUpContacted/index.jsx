import {
  Dialog,
  DialogContent,
  DialogTitle,
  Grid,
  Typography,
} from "@mui/material";
import ComposeMail from "../ComposeMail";
import EmailSummary from "../EmailSummary";
import EventTimeInput from "../EventTimeInput";
import PopUpContactedDetails from "../PopUpContactedDetails";

const PopUpContacted = (props) => {
  const { row, openPopUp, setOpenPopUp, isReviewer } = props;

  // Function to close the dialog
  const handleClose = () => {
    setOpenPopUp(false);
  };

  // Function to get the details of the customer
  const getDetails = () => {};
  return (
    <Dialog open={openPopUp} onClose={handleClose} fullWidth maxWidth="md">
      <DialogTitle>
        <Typography color="primary" variant="h5" display="inline-block">
          CUSTOMER DETAILS
        </Typography>
      </DialogTitle>
      <DialogContent>
        <Grid container spacing={2} columns={12}>
          {/* Display the customer details */}
          <PopUpContactedDetails
            Name={row.Name}
            Email={row.Email}
            PhoneNumber={row.PhoneNumber}
            City={row.City}
          />
          {/* Display the email summary */}
          <EmailSummary emailId={"channitdak@gmail.com"} />
          {/* Display the compose mail component */}
          <ComposeMail emailId={row.Email} />
          {/* Display the event time input component */}
          <EventTimeInput />
        </Grid>
      </DialogContent>
    </Dialog>
  );
};

// default props
PopUpContacted.defaultProps = {
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

export default PopUpContacted;
