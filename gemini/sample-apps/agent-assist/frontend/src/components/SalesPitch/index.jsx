import AutoFixHighIcon from "@mui/icons-material/AutoFixHigh"; // Icon for the generate button
import ExpandMoreIcon from "@mui/icons-material/ExpandMore"; // Icon for the accordion
import Textarea from "@mui/joy/Textarea"; // Textarea for the generated email
import LoadingButton from "@mui/lab/LoadingButton"; // Loading button for the generate button
import {
  Accordion,
  AccordionDetails,
  AccordionSummary,
  Grid,
  TextField,
  Typography,
} from "@mui/material"; // Material UI components
import { useState } from "react"; // React hook for state management

const SalesPitch = () => {
  const [loading, setLoading] = useState(false); // State for the loading button
  const [generateButtonText, setGenerateButtonText] = useState("Generate"); // State for the generate button text
  const [generateText, setGenerateText] = useState(""); // State for the text to generate the email
  const [generatedMail, setGeneratedMail] = useState(""); // State for the generated email
  const [isGenerated, setIsGenerated] = useState(false); // State for whether the email has been generated

  const handleClick = () => {
    setIsGenerated(true); // Set the isGenerated state to true
    setGenerateButtonText("Generating"); // Set the generate button text to "Generating"
    console.log(generateText); // Log the text to generate the email
    setLoading(true); // Set the loading state to true
    setGeneratedMail(generateText); // Set the generated email state to the text to generate the email
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
            Generate Sales Pitch
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
            <>
              <h7 style={{ marginTop: "30px" }}>Generated Email:</h7>
              <Textarea
                color="neutral"
                minRows={3}
                size="md"
                variant="outlined"
                value={generatedMail}
                onChange={(e) => setGeneratedMail(e.target.value)}
                sx={{ width: "100%", marginTop: "8px" }}
              />
            </>
          )}
        </AccordionDetails>
      </Accordion>
    </>
  );
};

export default SalesPitch;
