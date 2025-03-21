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
/**
 * Authz Blocking Function
 * Runs each time a user signs in or attempts to create an account.
 *
 * Checks their email address against a static allowList and returns either
 * a http 200 OK if all's good, or throws a HttpsError if not.
 *
 * See here for more details:
 * https://firebase.google.com/docs/auth/extend-with-blocking-functions?gen=2nd
 *
 * Author: mattsday@google.com
 */

import {
  beforeUserCreated,
  beforeUserSignedIn,
  HttpsError,
  AuthUserRecord,
  AuthBlockingEvent,
} from "firebase-functions/v2/identity";
import { logger } from "firebase-functions/v2";
import { allowList } from "./allow-list";

// Entry points for both functions - they both call the same validation code
export const beforeCreate = beforeUserCreated(
  (event: AuthBlockingEvent): Promise<object> => {
    return validate(event.data!);
  },
);

export const beforeSignIn = beforeUserSignedIn(
  (event: AuthBlockingEvent): Promise<object> => {
    return validate(event.data!);
  },
);

/**
 * Validates if the user's email address is allow-listed.
 * Will throw an exception if the user is not valid
 * @param {AuthUserRecord} user
 */
async function validate(user: AuthUserRecord): Promise<object> {
  const email = user.email;

  // We need an email address to perform validation
  if (!email) {
    logger.warn("Email not provided in session token");
    throw new HttpsError("invalid-argument", "User not found");
  }

  // Assume user is not permitted
  let allowed = false;

  // Loop through allowlist and check if the user matches
  for (const e of allowList) {
    const r = new RegExp(e);
    if (r.test(email)) {
      allowed = true;
      break;
    }
  }

  // Send a client error if the user is not found
  if (!allowed) {
    logger.warn(`${email} not found in allowlist`);
    throw new HttpsError("permission-denied", `${email} not allowlisted`);
  }
  // Return empty object with no claims
  return {};
}
