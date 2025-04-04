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

"use server";

import { OAuth2Client } from "google-auth-library";
import crypto from "crypto";
import { Firestore, Timestamp } from "firebase-admin/firestore";
import { cookies } from "next/headers";
import { GetAccessTokenResponse } from "google-auth-library/build/src/auth/oauth2client";

// Ensure we have appropriate environment variables for OAuth2
if (!process.env.NEXT_PUBLIC_CLIENT_ID) {
  throw new Error("Expected NEXT_PUBLIC_CLIENT_ID");
}

if (!process.env.CLIENT_SECRET) {
  throw new Error("Expected CLIENT_SECRET");
}

if (!process.env.ENCRYPTION_KEY) {
  throw new Error("Expected ENCRYPTION_KEY");
}

// Init Firestore
const db = new Firestore({
  databaseId: "(default)",
});

interface UserStore {
  refresh_token: string;
  access_token: string;
  expires: Date;
}

const oAuth2Client = new OAuth2Client(
  process.env.NEXT_PUBLIC_CLIENT_ID,
  process.env.CLIENT_SECRET,
  "postmessage",
);

/**
 * Handles user sign-in and sets a http only cookie for the user
 *
 * @param payload The token to be encrypted
 * @param encryptionKey A 32 character string used for encryption
 * @returns An encrypted string for safe storage in Firestore
 */
export async function processSignin(code: string): Promise<string> {
  const cookieStore = cookies();

  const { tokens } = await oAuth2Client.getToken(code);
  if (!tokens.id_token || !tokens.refresh_token || !tokens.access_token) {
    throw new Error("Invalid ID Token");
  }
  // Get the user details
  const ticket = await oAuth2Client.verifyIdToken({
    idToken: tokens.id_token,
  });
  const payload = ticket.getPayload();

  if (!payload || !payload.sub) {
    throw new Error("Unable to validate login token");
  }

  // Encrypt and store tokens in Firestore
  const [refresh, access] = await Promise.all([
    encrypt(tokens.refresh_token, process.env.ENCRYPTION_KEY!),
    encrypt(tokens.access_token, process.env.ENCRYPTION_KEY!),
  ]);

  const userRef = db.collection("users").doc(payload.sub);
  try {
    userRef.set(
      {
        refresh_token: refresh,
        access_token: access,
        expires: new Date(tokens.expiry_date || 0),
      },
      { merge: true },
    );
  } catch (e) {
    console.error(e);
    throw e;
  }

  // Store the ID token as a http only cookie (cannot be read by client-side JavaScript)
  (await cookieStore).set({
    name: "id_token",
    value: tokens.id_token,
    httpOnly: true,
    path: "/",
    secure: true,
    expires: new Date().setSeconds(payload.exp),
  });

  return tokens.id_token;
}

export async function getSession() {
  const cookieStore = await cookies();
  const idToken = cookieStore.get("id_token")?.value;
  if (!idToken) {
    return null;
  }
  return idToken;
}

export async function removeSession() {
  const cookieStore = await cookies();
  const idToken = cookieStore.get("id_token")?.value;
  // Delete login cookie
  cookieStore.delete("id_token");
  // Clean up Firestore
  if (idToken) {
    const ticket = await oAuth2Client.verifyIdToken({
      idToken: idToken,
    });
    const payload = ticket.getPayload();
    // No payload, user is already logged out
    if (!payload || !payload.sub) {
      return;
    }
    const userRef = db.collection("users").doc(payload.sub);
    try {
      await userRef.delete();
    } catch (e) {
      console.error(e);
    }
  }
}

export async function getAccessToken(): Promise<GetAccessTokenResponse | null> {
  const cookieStore = await cookies();
  const idToken = cookieStore.get("id_token")?.value;
  if (!idToken) {
    return null;
  }
  const ticket = await oAuth2Client.verifyIdToken({
    idToken: idToken,
  });
  const payload = ticket.getPayload();
  // No payload, user is already logged out
  if (!payload || !payload.sub) {
    return null;
  }
  const userRef = db.collection("users").doc(payload.sub);
  const user = await userRef.get();
  if (!user.exists) {
    return null;
  }
  const data = user.data() as UserStore;

  // Hydrate OAuth2 credentials
  oAuth2Client.setCredentials({
    refresh_token: decrypt(data.refresh_token, process.env.ENCRYPTION_KEY!),
    access_token: decrypt(data.access_token, process.env.ENCRYPTION_KEY!),
    expiry_date: (data.expires as unknown as Timestamp).toMillis(),
    id_token: idToken,
  });

  return oAuth2Client.getAccessToken();
}

/**
 * Handles encryption of tokens so they can be safely stored in Firestore
 *
 * @param payload The token to be encrypted
 * @param encryptionKey A 32 character string used for encryption
 * @returns An encrypted string for safe storage in Firestore
 */
async function encrypt(
  payload: string,
  encryptionKey: string,
): Promise<string> {
  // Create an initialization vector
  const iv = crypto.randomBytes(16);

  // Create a cipher object using AES-256-CBC algorithm
  const cipher = crypto.createCipheriv(
    "aes-256-cbc",
    Buffer.from(encryptionKey),
    iv,
  );

  // Encrypt the payload
  let encrypted = cipher.update(payload, "utf8", "hex");
  encrypted += cipher.final("hex");

  // Combine the IV and encrypted data
  return `${iv.toString("hex")}:${encrypted}`;
}
/**
 * Handles the decryption of tokens that has been stored in Firestore.
 *
 * @param encryptedData The data to be decrypted
 * @param encryptionKey A 32 character string used for encryption
 * @returns The unencrypted data
 */
function decrypt(encryptedData: string, encryptionKey: string): string {
  // Split the encrypted data into IV and ciphertext
  const [ivHex, ciphertext] = encryptedData.split(":");

  // Convert the IV from hexadecimal to Buffer
  const iv = Buffer.from(ivHex, "hex");

  // Create a decipher object
  const decipher = crypto.createDecipheriv(
    "aes-256-cbc",
    Buffer.from(encryptionKey),
    iv,
  );

  // Decrypt the ciphertext
  let decrypted = decipher.update(ciphertext, "hex", "utf8");
  decrypted += decipher.final("utf8");

  return decrypted;
}
