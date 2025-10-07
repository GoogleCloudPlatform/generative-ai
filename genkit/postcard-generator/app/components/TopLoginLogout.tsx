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
"use client";

import * as React from "react";
import Button from "@mui/material/Button";
import { UserAuth } from "./AuthContext";
import { useEffect, useState } from "react";

export default function TopLoginLogout() {
  const { user, googleSignIn, logOut, enabled } = UserAuth();
  const [loading, setLoading] = useState(true);

  const handleSignIn = async () => {
    try {
      googleSignIn();
    }
    catch (error) {
      console.log(error);
    }
  };

  const handleSignOut = async () => {
    try {
      logOut();
    }
    catch (error) {
      console.log(error);
    }
  };

  useEffect(() => {
    const checkAuthentication = async () => {
      await new Promise(resolve => setTimeout(resolve, 50));
      setLoading(false);
    };
    checkAuthentication();
  }, [user]);

  if (loading || !enabled) {
    return null;
  }

  if (user) {
    return (
      <Button color="inherit" type="submit" onClick={handleSignOut}>
        {user?.displayName}
        {" "}
        / Logout
      </Button>
    );
  }

  return (
    <Button color="inherit" onClick={handleSignIn}>
      Login
    </Button>
  );
}
