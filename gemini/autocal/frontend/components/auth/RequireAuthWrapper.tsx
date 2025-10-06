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
"use strict";

import { ReactNode } from "react";
import NotLoggedIn from "@/components/auth/NotLoggedIn";
import Alert from "@mui/material/Alert";
import AlertTitle from "@mui/material/AlertTitle";
import { Auth } from "./AuthContext";

interface RequireAuthWrapperProps {
  children?: ReactNode;
}

export default function RequireAuthWrapper({ children }: Readonly<RequireAuthWrapperProps>): ReactNode {
  // This page requires authentication, check we have that
  const { firebaseUser, error, loading } = Auth();

  if (error) {
    return (
      <Alert severity="error" sx={{ mb: 2 }}>
        <AlertTitle>Auth Error</AlertTitle>
        <>{error}</>
      </Alert>
    );
  }

  if (!loading) {
    if (firebaseUser) {
      return <>{children}</>;
    }
    return <NotLoggedIn />;
  }
  return null;
}
