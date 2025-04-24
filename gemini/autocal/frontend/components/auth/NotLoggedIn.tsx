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

import Alert from "@mui/material/Alert";
import { useState } from "react";
import Box from "@mui/material/Box";
import GoogleSignInButton from "./GoogleSignInButton";
import AlertTitle from "@mui/material/AlertTitle";
import { useGoogleLogin } from "@react-oauth/google";
import { Auth } from "./AuthContext";

export default function NotLoggedIn() {
  const [loginError, setLoginError] = useState<string | null>(null);

  const { handleLogin, loading } = Auth();

  const handleSignIn = async () => {
    try {
      login();
      setLoginError(null);
    } catch (error) {
      setLoginError(`Login failed with error: ${error}`);
    }
  };

  const login = useGoogleLogin({
    scope: "https://www.googleapis.com/auth/calendar",
    onSuccess: (codeResponse) => handleLogin(codeResponse),
    onError: (error) => setLoginError(`${error}`),
    flow: "auth-code",
  });

  return (
    <Box
      sx={{
        width: "100%",
        maxWidth: "lg",
        p: 2,
        display: "flex",
        flexDirection: "column",
        margin: "auto",
        alignItems: "center",
        justifyContent: "center",
      }}
    >
      {loginError && (
        <Alert severity="error" sx={{ mb: 2 }}>
          <AlertTitle>Error</AlertTitle>
          <>{loginError}</>
        </Alert>
      )}
      <Alert severity="warning">Please login to view this page.</Alert>
      <GoogleSignInButton handleSignIn={handleSignIn} disabled={loading} />
    </Box>
  );
}
