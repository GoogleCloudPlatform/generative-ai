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

import { ProcessedScreenshot } from "@/libs/schema/schema";
import { createContext, ReactNode, useContext, useState } from "react";
import { v4 as uuidv4 } from "uuid";

interface Props {
  children?: ReactNode;
}

const defaultStatus: ProcessedScreenshot = {
  error: false,
  processed: false,
  active: false,
};

interface Screenshot {
  base64: string;
  name: string;
  type: string;
}

interface StatusContext {
  status: ProcessedScreenshot;
  setStatus: (status: ProcessedScreenshot) => void;
  updateStatus: (field: string, state: string | Date | undefined) => void;
  updateEvent: (field: string, state: any) => void;
  error: string;
  setError: (error: string) => void;
  screenshot?: Screenshot;
  setScreenshot: (screenshot: Screenshot) => void;
  id: string;
  reset: () => void;
}

const StatusContext = createContext({} as StatusContext);

export default function StatusContextProvider({ children }: Props) {
  const [error, setError] = useState<string>("");
  const [status, setStatus] = useState<ProcessedScreenshot>(defaultStatus);
  const [screenshot, setScreenshot] = useState<Screenshot | undefined>(undefined);
  const [id, setId] = useState<string>(uuidv4());

  function reset() {
    const id = uuidv4();
    setId(id);
    setError("");
    setScreenshot(undefined);
    const status = defaultStatus;
    status.ID = id;
    setStatus(status);
  }

  // Update an item in the input schema
  function updateStatus(field: string, state: string | Date | undefined) {
    if (status) {
      const newStatus: ProcessedScreenshot = {
        [field]: state,
        ...status,
      };
      setStatus(newStatus);
    }
  }

  function updateEvent(field: string, state: any) {
    if (status && status.event) {
      status.event[field as keyof typeof status.event] = state;
      const newStatus: ProcessedScreenshot = {
        event: {
          [field]: state,
          ...status?.event,
        },
        ...status,
      };
      setStatus(newStatus);
    }
  }

  return (
    <StatusContext.Provider
      value={{
        status,
        setStatus,
        updateStatus,
        updateEvent,
        error,
        setError,
        screenshot,
        setScreenshot,
        id,
        reset,
      }}
    >
      {children}
    </StatusContext.Provider>
  );
}

export function Status(): StatusContext {
  return useContext(StatusContext);
}
