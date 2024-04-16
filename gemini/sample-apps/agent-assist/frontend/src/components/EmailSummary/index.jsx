import ExpandMoreIcon from "@mui/icons-material/ExpandMore";
import {
  Accordion,
  AccordionDetails,
  AccordionSummary,
  Typography,
} from "@mui/material";
import Markdown from "react-markdown";
import axios from "../../apis/mail_summary";
import useAxios from "../../hooks/useAxios";
import Loader from "../Loader";

// This component displays a summary of an email.
const EmailSummary = (props) => {
  // The email ID of the email to summarize.
  const { emailId } = props;

  // The email content, error, loading state, and reload function.
  const [emailContent, error, loading, setReload] = useAxios({
    // The axios instance to use.
    axiosInstance: axios,
    // The HTTP method to use.
    method: "GET",
    // The URL to send the request to.
    url: "/mail_summary/" + emailId,
  });

  return (
    <>
      {/* The accordion that contains the email summary. */}
      <Accordion sx={{ marginTop: "16px", width: "100%" }} elevation={0}>
        {/* The accordion summary that contains the title and expand icon. */}
        <AccordionSummary
          expandIcon={<ExpandMoreIcon />}
          aria-controls="panel1a-content"
          id="panel1a-header"
        >
          {/* The title of the accordion. */}
          <Typography variant="h6" color={"primary"} fontWeight={"normal"}>
            Communication Summary
          </Typography>
        </AccordionSummary>
        {/* The accordion details that contain the email summary. */}
        <AccordionDetails>
          {/* If the email content is empty, display a loading indicator. */}
          {Object.keys(emailContent).length === 0 ? (
            <Loader>Generating...</Loader>
          ) : (
            // Otherwise, display the email summary.
            <Markdown>{emailContent[0]}</Markdown>
          )}
        </AccordionDetails>
      </Accordion>
    </>
  );
};

export default EmailSummary;
