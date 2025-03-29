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

import { CalendarEvent } from "@/libs/schema/schema";
import { getAccessToken } from "../auth/auth";

interface CalendarResponse {
  ok: boolean;
  error?: string;
}

export async function addEvent(
  event: CalendarEvent,
): Promise<CalendarResponse> {
  // Get access token from session
  const token = await getAccessToken();

  if (!token) {
    return {
      ok: false,
      error: "Access token error - check if you are logged in",
    };
  }

  const response = await fetch(
    "https://www.googleapis.com/calendar/v3/calendars/primary/events",
    {
      method: "POST",
      headers: {
        Authorization: `Bearer ${token.token}`,
        "Content-Type": "application/json",
      },
      body: JSON.stringify({
        summary: event.summary,
        start: {
          dateTime: new Date(event.start).toISOString(),
        },
        end: {
          dateTime: new Date(event.end).toISOString(),
        },
        location: event.location,
        description: event.description,
      }),
    },
  );

  if (!response.ok) {
    const errorData = await response.json();
    console.error("Error fetching calendar list:", errorData);
    console.error(errorData["error"]);
    return {
      ok: false,
      error: `${errorData["error"]["message"]}`,
    };
  }

  return {
    ok: true,
  };
}
