/**
 * @license
 * Copyright 2026 Google LLC
 * SPDX-License-Identifier: Apache-2.0
 */

import type { CaseResponse } from "./types";

const endpoints = {
  current: "/api/live-onboarding/current",
  start: "/api/live-onboarding/start",
  case: (id: string) => `/api/live-onboarding/cases/${encodeURIComponent(id)}`,
  sign: (id: string) => `/api/live-onboarding/cases/${encodeURIComponent(id)}/sign`,
  hardware: (id: string) =>
    `/api/live-onboarding/cases/${encodeURIComponent(id)}/deliver-hardware`,
};

async function requestJson<T>(url: string, init?: RequestInit): Promise<T> {
  const response = await fetch(url, {
    headers: { "Content-Type": "application/json" },
    ...init,
  });

  if (!response.ok) {
    throw new Error(`${response.status} ${response.statusText}`);
  }

  return response.json() as Promise<T>;
}

export function getCurrentCase() {
  return requestJson<CaseResponse>(endpoints.current);
}

export function startCase() {
  return requestJson<CaseResponse>(endpoints.start, { method: "POST" });
}

export function getCase(id: string) {
  return requestJson<CaseResponse>(endpoints.case(id));
}

export function signPacket(id: string) {
  return requestJson<CaseResponse>(endpoints.sign(id), { method: "POST" });
}

export function confirmHardware(id: string) {
  return requestJson<CaseResponse>(endpoints.hardware(id), { method: "POST" });
}
