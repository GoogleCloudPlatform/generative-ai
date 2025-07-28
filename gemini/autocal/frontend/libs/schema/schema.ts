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

import {
  Timestamp,
  serverTimestamp,
  QueryDocumentSnapshot,
  DocumentData,
} from "firebase/firestore";

export interface ScreenshotUpload {
  image: string; // Path to original screenshot in GCS
  ID: string; // UUID for this transaction
  type: string; // MIME type (e.g., image/png)
  timestamp?: Date; // Date/time of image upload
}

export interface ProcessedScreenshot {
  processed: boolean; // Whether the image has been processed
  error: boolean; // Whether there's been an error
  active: boolean; // Whether the screenshot is active in the UI
  image?: string; // Path to original screenshot in GCS
  ID?: string; // UUID for this transaction
  message?: string; // Any messages (e.g., an error message)
  event?: CalendarEvent; // The main fields of a calendar event
  timestamp?: Date; // Date/time of last event update
}

export interface CalendarEvent {
  summary: string; // Event title
  start: Date | string; // Event start date/time
  end: Date | string; // Event end date/time
  location: string; // Event location
  description: string; // Event description
}

// Firestore Converter for ScreenshotUpload
export const screenshotUploadConverter = {
  toFirestore(data: ScreenshotUpload): DocumentData {
    return {
      image: data.image,
      ID: data.ID,
      type: data.type,
      timestamp: Timestamp.fromDate(data.timestamp || new Date()),
    };
  },
  fromFirestore(snapshot: QueryDocumentSnapshot): ScreenshotUpload {
    const data = snapshot.data();
    return {
      image: data.image,
      ID: data.ID,
      type: data.type,
      timestamp: (data.timestamp as Timestamp).toDate(),
    };
  },
};

// Firestore Converter for ProcessedScreenshot
export const processedScreenshotConverter = {
  toFirestore(data: ProcessedScreenshot): DocumentData {
    return {
      image: data.image || "",
      ID: data.ID || "",
      processed: data.processed || false,
      error: data.error || false,
      active: data.active || false,
      message: data.message || "",
      event: {
        summary: data.event?.summary || "",
        start: data.event?.start || new Date(),
        end: data.event?.end || new Date(),
        location: data.event?.location || "",
        description: data.event?.description || "",
      },
      timestamp: serverTimestamp() as unknown as Date,
    };
  },
  fromFirestore(snapshot: QueryDocumentSnapshot): ProcessedScreenshot {
    const data = snapshot.data();

    return {
      image: data.image,
      ID: data.ID,
      processed: data.processed,
      error: data.error,
      message: data.message,
      active: data.active,
      event: {
        summary: data?.event?.summary || "",
        // start: new Date(data?.event?.start),
        // end: new Date(data?.event?.end),
        start: data?.event?.start,
        end: data?.event?.end,
        location: data?.event?.location || "",
        description: data?.event?.description || "",
      },
      timestamp: data.timestamp.toDate() || new Date(),
    };
  },
};
