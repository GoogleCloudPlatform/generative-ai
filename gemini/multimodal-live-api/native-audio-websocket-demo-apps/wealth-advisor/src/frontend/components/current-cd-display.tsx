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
import "./current-cd-display.css";

export interface CdOption {
  term: string;
  apy: string;
  balance?: string;
}

export interface CurrentCdDisplayData {
  title: string;
  current_cd: CdOption;
}

interface CurrentCdDisplayProps {
  data: CurrentCdDisplayData;
}

export const CurrentCdDisplay: React.FC<CurrentCdDisplayProps> = ({
  data,
}) => {
  return (
    <div className="current-cd-container">
      <div className="current-cd-header">
        <h2>{data.title}</h2>
      </div>
      <div className="current-cd-body">
        <div className="info-column">
          <span className="info-label">Balance</span>
          <span className="info-value">{data.current_cd.balance}</span>
        </div>
        <div className="info-column">
          <span className="info-label">APY</span>
          <span className="info-value">
            {data.current_cd.apy} over {data.current_cd.term}
          </span>
        </div>
      </div>
    </div>
  );
};
