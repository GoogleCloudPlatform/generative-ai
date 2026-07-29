/**
 * @license
 * Copyright 2026 Google LLC
 * SPDX-License-Identifier: Apache-2.0
 */

export type Artifact = {
  id: string;
  title: string;
  kind: string;
  filename: string;
  href: string;
  created_at: string;
};

export type CaseEvent = {
  kind: string;
  title: string;
  detail: string;
  time: string;
};

export type Employee = {
  name: string;
  email: string;
  start_date: string;
  role: string;
  team: string;
  manager: string;
  corporate_email: string;
  tracking_id: string;
  photo_url: string;
};

export type LiveCase = {
  id: string;
  session_id: string;
  user_id: string;
  employee: Employee;
  current_step: string;
  pending_signals: string[];
  status: string;
  document_signed: boolean;
  hardware_delivered: boolean;
  adk_status: string;
  events: CaseEvent[];
  artifacts: Artifact[];
  updated_at: number;
};

export type CaseResponse =
  | {
    active: true;
    case: LiveCase;
  }
  | {
    active: false;
    message: string;
  };
