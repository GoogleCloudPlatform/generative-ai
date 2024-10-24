/**
 * Copyright 2024 Google LLC
 *
 * Licensed under the Apache License, Version 2.0 (the "License");
 * you may not use this file except in compliance with the License.
 * You may obtain a copy of the License at
 *
 *     http://www.apache.org/licenses/LICENSE-2.0
 *
 * Unless required by applicable law or agreed to in writing, software
 * distributed under the License is distributed on an "AS IS" BASIS,
 * WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
 * See the License for the specific language governing permissions and
 * limitations under the License.
 */

"use strict";
import LinearProgress from "@mui/material/LinearProgress";
import Card from "@mui/material/Card";
import CardMedia from "@mui/material/CardMedia";
import CardContent from "@mui/material/CardContent";
import Alert from "@mui/material/Alert";
import ExpandMoreIcon from "@mui/icons-material/ExpandMore";
import IconButton, { IconButtonProps } from "@mui/material/IconButton";
import { styled } from "@mui/material/styles";
import { useState } from "react";
import Typography from "@mui/material/Typography";
import Collapse from "@mui/material/Collapse";
import CardActions from "@mui/material/CardActions";
import Markdown from "react-markdown";
import DownloadIcon from "@mui/icons-material/Download";
import ShareIcon from "@mui/icons-material/Share";

export interface PostcardImageProps {
  postcardImage: string | null;
  generating: boolean;
  description: string;
  start: string | null;
  end: string | null;
  error: string | null;
  mapImage: string | null;
  story: string | null;
}
interface ExpandMoreProps extends IconButtonProps {
  expand: boolean;
}

const ExpandMore = styled((props: ExpandMoreProps) => {
  // eslint-disable-next-line @typescript-eslint/no-unused-vars
  const { expand, ...other } = props;
  return <IconButton {...other} />;
})(({ theme }) => ({
  marginLeft: "auto",
  transition: theme.transitions.create("transform", {
    duration: theme.transitions.duration.shortest,
  }),
  variants: [
    {
      props: ({ expand }) => !expand,
      style: {
        transform: "rotate(0deg)",
      },
    },
    {
      props: ({ expand }) => !!expand,
      style: {
        transform: "rotate(180deg)",
      },
    },
  ],
}));

export default function PostcardImage({ postcardImage, generating, error, mapImage, description, story }: PostcardImageProps) {
  const [expanded, setExpanded] = useState(false);

  const handleExpandClick = () => {
    setExpanded(!expanded);
  };

  async function download() {
    if (postcardImage) {
      // Use fetch to convert the image data URL into a blob
      const response = await fetch(postcardImage);
      // Create a download link
      const url = window.URL.createObjectURL(await response.blob());
      const link = document.createElement("a");
      link.href = url;
      link.setAttribute("download", "postcard.png");
      // Simulate a click on the link to trigger the download
      document.body.appendChild(link);
      link.click();
      link.parentNode?.removeChild(link);
    }
  }

  return (
    <div className="w-full flex justify-center">
      <Card sx={{ minWidth: 275, Height: 500 }}>
        {generating && (
          <CardContent sx={{ Height: 500 }}>
            <Alert severity="info" variant="filled">Generating Postcard</Alert>
            <LinearProgress />
          </CardContent>
        )}
        {postcardImage && story && mapImage && !generating && (
          <>
            <CardMedia
              component="img"
              image={postcardImage}
              alt="Generated Postcard Image"
              sx={{ padding: "1em 1em 0 1em", objectFit: "contain", maxHeight: 500 }}
            />
            <CardContent>
              <Typography sx={{ marginBottom: 2 }} component="span">
                <Markdown>
                  {story}
                </Markdown>
              </Typography>
            </CardContent>
            <CardActions disableSpacing>
              <IconButton aria-label="Download image" onClick={download}>
                <DownloadIcon />
              </IconButton>
              <IconButton aria-label="share">
                <ShareIcon />
              </IconButton>
              <ExpandMore
                expand={expanded}
                onClick={handleExpandClick}
                aria-expanded={expanded}
                aria-label="show more"
              >
                <ExpandMoreIcon />
              </ExpandMore>
            </CardActions>
            <Collapse in={expanded} timeout="auto" unmountOnExit>
              <CardContent>
                <Typography gutterBottom variant="h5" component="div">
                  Map
                </Typography>
                <Typography sx={{ marginBottom: 2 }}>
                  <CardMedia
                    component="img"
                    image={mapImage}
                    alt="Route Map"
                    sx={{ padding: "1em 1em 0 1em", objectFit: "contain", maxHeight: 500 }}
                  />
                </Typography>
                <Typography gutterBottom variant="h5" component="div">
                  Prompt
                </Typography>
                <Typography sx={{ marginBottom: 2 }} component="span">
                  <Markdown>
                    {description}
                  </Markdown>
                </Typography>
              </CardContent>
            </Collapse>
          </>
        )}
        {error && !generating && (
          <CardContent sx={{ Height: 500 }}>
            <Alert severity="error">{error}</Alert>
          </CardContent>
        )}
      </Card>
    </div>
  );
}
