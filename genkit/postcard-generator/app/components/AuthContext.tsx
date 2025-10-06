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

import { ReactNode, createContext, useState, useEffect, useContext } from "react";
import { signInWithPopup, signOut, User, onAuthStateChanged, GoogleAuthProvider, onIdTokenChanged } from "firebase/auth";
import { firebaseAuth } from "@/libs/firebase/clientApp";

interface AuthProviderProps {
  children?: ReactNode;
  enabled?: boolean;
}

interface AuthContext {
  user: User | null;
  googleSignIn: () => Promise<void>;
  logOut: () => Promise<void>;
  enabled: boolean;
}

export async function googleSignIn() {
  const provider = new GoogleAuthProvider();
  await signInWithPopup(firebaseAuth, provider);
}

export async function logOut() {
  await signOut(firebaseAuth);
}

const AuthContext = createContext({} as AuthContext);

export const AuthContextProvider = ({
  children, enabled = false,
}: AuthProviderProps): JSX.Element => {
  const [user, setUser] = useState<User | null>(null);

  useEffect(() => {
    if (!enabled) {
      return;
    }
    const unsubscribe = onAuthStateChanged(firebaseAuth, (currentUser) => {
      setUser(currentUser);
    });
    return () => unsubscribe();
  }, [user, enabled]);

  useEffect(() => {
    if (!enabled) {
      return;
    }
    return onIdTokenChanged(firebaseAuth, async (currentUser) => {
      if (!currentUser) {
        setUser(null);
      }
      else {
        setUser(currentUser);
      }
    });
  }, [enabled]);

  return (
    <AuthContext.Provider
      value={{
        user: user,
        googleSignIn,
        logOut,
        enabled,
      }}
    >
      {children}
    </AuthContext.Provider>
  );
};

export const UserAuth = () => {
  return useContext(AuthContext);
};
