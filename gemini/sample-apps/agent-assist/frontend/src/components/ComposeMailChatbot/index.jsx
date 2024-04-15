import { Card, CardActions, CardContent, Typography } from "@mui/material";
import TextField from "@mui/material/TextField";
import * as React from "react";
import axios_workbench from "../../apis/workbench";
import CircularIntegration from "../CircularIntegration";

// This component is used to compose and send an email using the Workbench API.
export default function Email({ payload }) {
  // The state of the email content.
  const [mailContent, setMailContent] = React.useState(payload);
  // The state of the loading indicator.
  const [loading, setLoading] = React.useState(false);
  // The state of the success indicator.
  const [success, setSuccess] = React.useState(false);

  // This function is called when the user clicks the send button.
  const handleClick = () => {
    // Set the loading indicator to true.
    setLoading(true);
    // Send the email content to the Workbench API.
    axios_workbench["post"]("/mail", mailContent)
      .then((result) => {
        console.log(result);
        // Set the success indicator to true.
        setSuccess(true);
        // Set the loading indicator to false.
        setLoading(false);
      })
      .catch((err) => {
        console.log(err);
      });
  };

  return (
    <React.Fragment>
      <Card sx={{ maxWidth: 650, borderRadius: "20px" }}>
        <CardContent>
          <TextField
            autoFocus
            margin="dense"
            id="to"
            label="Recipient"
            type="email"
            fullWidth
            variant="outlined"
            value={mailContent.recipient}
            onChange={(e) =>
              setMailContent({ ...mailContent, recipient: e.target.value })
            }
            disabled={loading || success}
          />
          <TextField
            autoFocus
            margin="dense"
            id="subject"
            label="Subject"
            fullWidth
            variant="outlined"
            value={mailContent.subject}
            onChange={(e) =>
              setMailContent({ ...mailContent, subject: e.target.value })
            }
            disabled={loading || success}
          />
          <TextField
            autoFocus
            margin="dense"
            id="body"
            fullWidth
            multiline
            rows={15}
            variant="outlined"
            value={mailContent.body}
            onChange={(e) =>
              setMailContent({ ...mailContent, body: e.target.value })
            }
            disabled={loading || success}
          />
        </CardContent>
        <CardActions
          sx={{
            display: "flex",
            justifyContent: "flex-end",
          }}
        >
          <CircularIntegration
            loading={loading}
            success={success}
            setLoading={setLoading}
            setSuccess={setSuccess}
            handleClick={handleClick}
          >
            Send
          </CircularIntegration>
        </CardActions>
        {success && (
          <Typography color="green" align="right" marginRight={5}>
            Email Sent Successfully
          </Typography>
        )}
      </Card>
    </React.Fragment>
  );
}
