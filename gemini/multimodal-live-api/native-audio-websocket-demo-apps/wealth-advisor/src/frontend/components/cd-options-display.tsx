// Copyright 2026 Google LLC
//
// Licensed under the Apache License, Version 2.0 (the "License");
// you may not use this file except in compliance with the License.
// You may obtain a copy of the License at
//
//     https://www.apache.org/licenses/LICENSE-2.0
//
// Unless required by applicable law or agreed to in writing, software
// distributed under the License is distributed on an "AS IS" BASIS,
// WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
// See the License for the specific language governing permissions and
// limitations under the License.

import React from "react";
import "./cd-options-display.css";

export interface CdOption {
  term: string;
  apy: string;
}

export interface CdReinvestmentOptionsData {
  title: string;
  options: CdOption[];
}

interface CdOptionsDisplayProps {
  data: CdReinvestmentOptionsData;
}

export const CdOptionsDisplay: React.FC<CdOptionsDisplayProps> = ({
  data,
}) => {
  return (
    <div className="cd-options-container">
      <div className="cd-options-header">
        <h2>{data.title}</h2>
      </div>
      <div className="cd-options-body">
        <div className="reinvestment-options">
          {data.options.map((option, index) => (
            <div key={index} className="cd-option-card">
              <span>{option.term}</span>
              <span>{option.apy} APY</span>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
};
