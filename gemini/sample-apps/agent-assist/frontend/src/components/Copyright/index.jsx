import { Link, Typography } from "@mui/material";

// This component displays the copyright notice at the bottom of the page.
export default function Copyright() {
  return (
    <Typography variant="body2" color="text.secondary" align="center">
      {"Copyright © "}
      <Link color="inherit" href="https://mui.com/">
        Kavach Insurance
      </Link>{" "}
      {new Date().getFullYear()}
      {"."}
    </Typography>
  );
}
