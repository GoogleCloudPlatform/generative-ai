import {
  Dialog,
  DialogContent,
  DialogTitle,
  Grid,
  Typography,
} from "@mui/material";
import PopUpContactedDetails from "../PopUpContactedDetails";

const PopUpKanban = (props) => {
  // Destructure props
  const { row, openPopUp, setOpenPopUp } = props;

  // Function to close the dialog
  const handleClose = () => {
    setOpenPopUp(false);
  };

  // Log the row data to the console for debugging
  console.log(row);

  return (
    <Dialog open={openPopUp} onClose={handleClose} fullWidth maxWidth="md">
      <DialogTitle>
        <Typography color="primary" variant="h4" display="inline-block">
          USER DETAILS
        </Typography>
      </DialogTitle>
      <DialogContent>
        <Grid container spacing={2} columns={12}>
          {/* Pass the row data to the PopUpContactedDetails component */}
          <PopUpContactedDetails
            Name={row.Name}
            Email={row.Email}
            PhoneNumber={row.PhoneNumber}
            City={row.City}
          />
        </Grid>
      </DialogContent>
    </Dialog>
  );
};

// default props
PopUpKanban.defaultProps = {
  row: {
    Name: "Channit Dak",
    Email: "channitdak@gmail.com",
    Phone: "9876543210",
    City: "Hyderabad",
    EmailSummary:
      "Lorem Ipsum is simply dummy text of the printing and typesetting industry. Lorem Ipsum has been the industry's standard dummy text ever since the 1500s",
    LastContactedDate: "2022-01-01",
  },
  openPopUp: false,
  setOpenPopUp: () => {},
};

export default PopUpKanban;
