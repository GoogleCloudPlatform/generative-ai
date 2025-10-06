/**
 * Copyright 2025 Google LLC
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
"use client";
import { createTheme, Theme } from "@mui/material/styles";

const theme: Theme = createTheme({
  colorSchemes: {
    dark: {
      palette: {
        mode: 'dark',
      },
    },
    light: {
      palette: {
        mode: 'light',
      },
    },
  },
  cssVariables: true,
  typography: {
    fontFamily: "var(--font-roboto)",
    h1: {
      fontSize: "2rem",
    },
    h2: {
      fontSize: "1.5rem",
    },
    h3: {
      fontSize: "1.2rem",
    },
    h4: {
      fontSize: "1.1rem",
    },
  },
});

export default theme;
