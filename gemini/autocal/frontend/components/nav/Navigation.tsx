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

"use strict";
"use client";

import AppBar from "@mui/material/AppBar";
import Box from "@mui/material/Box";
import Toolbar from "@mui/material/Toolbar";
import TopLoginLogout from "@/components/nav/TopLoginLogout";
import { styled } from "@mui/material/styles";
import Typography from "@mui/material/Typography";

const Offset = styled("div")(({ theme }) => theme.mixins.toolbar);

export default function Navigation() {
  return (
    <Box sx={{ flexGrow: 1, mb: 2 }}>
      <AppBar position="fixed">
        <Toolbar disableGutters>
          <Typography variant="h6" component="h1" sx={{ flexGrow: 1, ml: 1 }}>
            AutoCal
          </Typography>
          <Box sx={{ mr: 2 }}>
            <TopLoginLogout />
          </Box>
        </Toolbar>
      </AppBar>
      <Offset />
    </Box>
  );
}
