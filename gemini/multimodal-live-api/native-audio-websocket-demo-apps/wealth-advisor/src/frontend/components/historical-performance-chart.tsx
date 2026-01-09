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

import * as React from "react";
import "./historical-performance-chart.css";

export function HistoricalPerformanceChart() {
  return (
    <div className="chart-wrapper">
      <div className="chart-title">Managed Portfolio</div>
      <div className="chart-content">
        <div className="y-labels">
          <div>$1M</div>
          <div>$750K</div>
          <div>$500K</div>
          <div>$250K</div>
        </div>
        <div className="chart-area">
          <svg
            width="100%"
            height="100%"
            viewBox="0 0 310 230"
            preserveAspectRatio="xMidYMid meet"
            xmlns="http://www.w3.org/2000/svg"
          >
            <defs>
              <linearGradient id="line-gradient" x1="0%" y1="0%" x2="0%" y2="100%">
                <stop offset="0%" style={{ stopColor: "#99FFB8", stopOpacity: 0.5 }} />
                <stop offset="100%" style={{ stopColor: '#000000', stopOpacity: 0.1 }} />
              </linearGradient>
            </defs>
            <path d="M 0 150 C 40 120, 60 140, 100 100 S 160 110, 200 90 S 260 100, 310 80" stroke="#99FFB8" strokeWidth="2" fill="url(#line-gradient)" />
            <line x1="0" y1="57.5" x2="310" y2="57.5" stroke="#5C6974" strokeWidth="1"/>
            <line x1="0" y1="115" x2="310" y2="115" stroke="#5C6974" strokeWidth="1"/>
            <line x1="0" y1="172.5" x2="310" y2="172.5" stroke="#5C6974" strokeWidth="1"/>
            <line x1="0" y1="230" x2="310" y2="230" stroke="#5C6974" strokeWidth="1"/>
          </svg>
        </div>
      </div>
      <div className="x-labels">
        <div>2000</div>
        <div>2010</div>
        <div>2020</div>
        <div>2030</div>
        <div>2040</div>
        <div>2050</div>
        <div>2060</div>
      </div>
    </div>
  );
}