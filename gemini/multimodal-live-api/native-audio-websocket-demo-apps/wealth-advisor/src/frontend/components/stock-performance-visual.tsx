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

import React from 'react';
import './stock-performance-visual.css';

export interface StockPerformanceData {
    stockName: string;
    price: string;
    ytdReturn: string;
}

export const StockPerformanceVisual: React.FC<{ data: StockPerformanceData }> = ({ data }) => {
  return (
    <div className="stock-performance-visual">
      <div className="stock-performance-card">
        <div className="header">
          Today&apos;s {data.stockName} market price
        </div>
        <div className="metrics">
          <div className="metric">
            <div className="label">Price</div>
            <div className="value">{data.price}</div>
          </div>
          <div className="metric">
            <div className="label">YTD Return</div>
            <div className="value">{data.ytdReturn}</div>
          </div>
        </div>
      </div>
    </div>
  );
};