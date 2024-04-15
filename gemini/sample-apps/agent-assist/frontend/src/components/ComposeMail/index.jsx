import AutoFixHighIcon from "@mui/icons-material/AutoFixHigh";
import ExpandMoreIcon from "@mui/icons-material/ExpandMore";
import SendIcon from "@mui/icons-material/Send";
import Textarea from "@mui/joy/Textarea";
import LoadingButton from "@mui/lab/LoadingButton";
import {
  Accordion,
  AccordionDetails,
  AccordionSummary,
  FormControl,
  FormHelperText,
  FormLabel,
  Grid,
  TextField,
  Typography,
} from "@mui/material";
import { useState } from "react";
import axios_workbench from "../../apis/workbench";

const ComposeMail = (props) => {
  const { emailId } = props;

  const [loading, setLoading] = useState(false); // State to handle loading state of the generate button
  const [generateButtonText, setGenerateButtonText] = useState("Generate"); // State to handle the text of the generate button
  const [generateText, setGenerateText] = useState(""); // State to handle the input text for email generation
  const [generatedMail, setGeneratedMail] = useState(""); // State to handle the generated email
  const [isGenerated, setIsGenerated] = useState(false); // State to handle whether the email is generated
  const [mailSent, setMailSent] = useState(false); // State to handle whether the email is sent
  const [mailSending, setMailSending] = useState(false); // State to handle loading state of the send button

  const handleClick = () => {
    setGenerateButtonText("Generating"); // Update the generate button text to "Generating"
    setLoading(true); // Set the loading state to true
    axios_workbench["post"]("/agent-assist/generate_mail", {
      inputText: generateText,
    }) // Make a POST request to the API to generate email
      .then((result) => {
        setIsGenerated(true); // Set the isGenerated state to true
        setGeneratedMail(result.data.generatedMail); // Set the generatedMail state to the generated email
        setLoading(false); // Set the loading state to false
        setGenerateButtonText("Generate"); // Update the generate button text to "Generate"
      })
      .catch((err) => {
        console.log(err);
        setIsGenerated(true); // Set the isGenerated state to true
        setLoading(false); // Set the loading state to false
        setGenerateButtonText("Generate"); // Update the generate button text to "Generate"
      });
  };
  const sendEmail = () => {
    setMailSending(true); // Set the mailSending state to true
    console.log(emailId);
    axios_workbench["post"]("/agent-assist/send_mail", {
      generatedMail: generatedMail,
      emailId: emailId,
    }) // Make a POST request to the API to send email
      .then((result) => {
        console.log("Sending email");
        console.log(result.data.message);
        setMailSent(true); // Set the mailSent state to true
        setMailSending(false); // Set the mailSending state to false
      })
      .catch((err) => {
        console.log(err);
      });
  };
  return (
    <>
      <Accordion sx={{ marginTop: "16px", width: "100%" }} elevation={0}>
        <AccordionSummary
          expandIcon={<ExpandMoreIcon />}
          aria-controls="panel1a-content"
          id="panel1a-header"
        >
          <Typography variant="h6" color={"primary"} fontWeight={"normal"}>
            Compose Mail
          </Typography>
        </AccordionSummary>
        <AccordionDetails>
          <Grid container spacing={2} alignItems="center">
            <Grid item xs={10}>
              <TextField
                sx={{ width: "100%" }}
                id="outlined-basic"
                label="Write text to generate email"
                variant="outlined"
                value={generateText}
                onChange={(e) => setGenerateText(e.target.value)}
              />
            </Grid>
            <Grid item xs={2}>
              <LoadingButton
                onClick={handleClick}
                loading={loading}
                loadingPosition="end"
                variant="contained"
                disabled={generateText.length === 0}
                endIcon={<AutoFixHighIcon />}
              >
                <span>{generateButtonText}</span>
              </LoadingButton>
            </Grid>
          </Grid>
          {isGenerated && (
            <Grid container spacing={2} alignItems="flex-end">
              <Grid item xs={10.5}>
                <FormControl sx={{ width: "100%", marginTop: "16px" }}>
                  <FormLabel>Generated Email:</FormLabel>
                  <Textarea
                    label="Generated Email"
                    color="neutral"
                    minRows={2}
                    size="md"
                    variant="outlined"
                    value={generatedMail}
                    onChange={(e) => {
                      setGeneratedMail(e.target.value);
                      setMailSent(false);
                    }}
                    sx={{ width: "100%", marginTop: "8px" }}
                  />
                  <FormHelperText>
                    Edit the email and click on the send button to send the
                    email.
                  </FormHelperText>
                </FormControl>
              </Grid>
              <Grid item xs={1.5}>
                <LoadingButton
                  loading={mailSending}
                  loadingPosition="end"
                  variant="contained"
                  endIcon={<SendIcon />}
                  sx={{ marginBottom: "22px" }}
                  onClick={sendEmail}
                  disabled={mailSent}
                >
                  {mailSending ? "Sending" : mailSent ? "Sent" : "Send"}
                </LoadingButton>
              </Grid>
            </Grid>
          )}
        </AccordionDetails>
      </Accordion>
    </>
  );
};

ComposeMail.defaultProps = {
  emailId: "channitdak@gmail.com",
};

export default ComposeMail;
