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

import { CodeResponse } from "@react-oauth/google";
import { createContext, ReactNode, useContext, useEffect, useState } from "react";
import { GoogleOAuthProvider } from "@react-oauth/google";
import { GoogleAuthProvider, signInWithCredential, signOut, UserCredential } from "firebase/auth";
import { firebaseAuth } from "@/libs/firebase/client/clientApp";
import { getSession, processSignin, removeSession } from "@/libs/auth/auth";

interface Props {
  children?: ReactNode;
}

interface AuthContext {
  firebaseUser: UserCredential | null;
  handleLogin(response: Omit<CodeResponse, "error" | "error_description" | "error_uri">): void;
  error: string;
  loading: boolean;
  logOut: () => void;
}

const AuthContext = createContext({} as AuthContext);

export default function AuthContextProvider({ children }: Props) {
  const [firebaseUser, setFirebaseUser] = useState<UserCredential | null>(null);
  const [error, setError] = useState<string>("");
  const [loading, setLoading] = useState<boolean>(true);

  useEffect(() => {
    async function loadSession() {
      try {
        const t = await getSession();
        if (t) {
          await loadFirebaseUser(t);
        }
      } finally {
        setLoading(false);
      }
    }
    loadSession();
  }, []);

  async function loadFirebaseUser(t: string) {
    const credential = GoogleAuthProvider.credential(t);
    const p = await signInWithCredential(firebaseAuth, credential);
    setFirebaseUser(p);
  }

  async function handleLogin(response: Omit<CodeResponse, "error" | "error_description" | "error_uri">) {
    if (response?.code) {
      try {
        // Verify tokens on server side:
        const t = await processSignin(response.code);
        loadFirebaseUser(t);
      } catch (error) {
        console.error(error);
        setError(`${error}`);
      }
    }
  }

  async function logOut() {
    const s = removeSession();
    setFirebaseUser(null);
    signOut(firebaseAuth);
    await s;
  }

  return (
    <GoogleOAuthProvider clientId={process.env.NEXT_PUBLIC_CLIENT_ID!}>
      <AuthContext.Provider
        value={{
          firebaseUser,
          handleLogin,
          error,
          loading,
          logOut,
        }}
      >
        {children}
      </AuthContext.Provider>
    </GoogleOAuthProvider>
  );
}

export function Auth(): AuthContext {
  return useContext(AuthContext);
}
