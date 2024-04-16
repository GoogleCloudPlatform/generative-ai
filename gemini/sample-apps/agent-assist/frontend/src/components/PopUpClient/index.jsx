import { Dialog, DialogContent, DialogTitle, Typography } from "@mui/material";

export default function PopUpClient(props) {
  // Destructure props
  const { row, openPopUp, setOpenPopUp, isReviewer } = props;

  // Function to handle closing the pop up
  const handleClose = () => {
    setOpenPopUp(false);
  };

  return (
    // Dialog component for pop up
    <Dialog open={openPopUp} onClose={handleClose} fullWidth maxWidth="md">
      {/* Dialog title */}
      <DialogTitle>
        <Typography color="primary" variant="h5" display="inline-block">
          CLAIM DETAILS
        </Typography>
      </DialogTitle>
      {/* Dialog content */}
      <DialogContent>
        <h1>Hello pop up</h1>
      </DialogContent>
    </Dialog>
  );
}
