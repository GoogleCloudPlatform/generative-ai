import TextField from "@mui/material/TextField";
import React from "react";
import ReactMarkdown from "react-markdown";

const MarkdownTextField = ({
  mailContent,
  setMailContent,
  loading,
  success,
}) => {
  return (
    <TextField
      autoFocus
      margin="dense"
      id="body"
      fullWidth
      label="Markdown Input"
      multiline
      rows={4}
      variant="outlined"
      onChange={(e) => setMailContent({ ...mailContent, body: e.target.value })}
      disabled={loading || success}
      InputLabelProps={{
        shrink: true,
      }}
      helperText={<ReactMarkdown>{mailContent.body}</ReactMarkdown>}
    />
  );
};

export default MarkdownTextField;
