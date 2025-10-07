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

import { PlacePicker } from "@googlemaps/extended-component-library/react";
import Stack from "@mui/material/Stack";
import React from "react";

export interface PlaceAutoCompleteProps {
  description: string;
  value: string;
  id: string;
  handleChange: (e: Event) => void;
}

export default function PlaceAutoComplete({ description, value: defaultValue, id, handleChange }: PlaceAutoCompleteProps) {
  return (
    <Stack spacing={0} direction="column">
      <label htmlFor={id}>
        {description}
      </label>
      <PlacePicker id={id} placeholder={defaultValue} onPlaceChange={handleChange} />
    </Stack>
  );
}
