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

"use client"

import * as React from "react"

import "./financial-summary.css"


export interface FinancialSummaryData {
  totalBalance: {
    currency: string
  }
  InvestmentPortfolio: {
    ytd_return: number
    positions: {
      symbol: string
      marketValue: {
        amount: number
      }
    }[]
  }
}

export function FinancialSummary({
  summary,
}: {
  summary: FinancialSummaryData | null
}) {
  const formatCompactCurrency = (amount: number, currency: string) => {
    const value = new Intl.NumberFormat("en-US", {
      style: "currency",
      currency: currency,
      notation: "compact",
      compactDisplay: "short",
      minimumFractionDigits: 0,
      maximumFractionDigits: 1,
    }).format(amount)
    // remove .0 from end
    return value.replace(/\.0([A-Z])$/, (match, p1) => p1)
  }

  if (!summary) {
    return <div>Loading...</div>
  }

  return (
    <div className="financial-summary-container h-auto">
      <div className="summary-content">
        <div className="summary-header">
        <h4 className="summary-section-title text-left">Portfolio Summary</h4>
      </div>
      <div className="summary-details">
        <div className="summary-section">
          <span className="summary-section-title">Assets</span>
          <span className="summary-section-value">$2.75M</span>
        </div>
        <div className="summary-section">
          <span className="summary-section-title">Liabilities</span>
          <span className="summary-section-value">$600</span>
        </div>
        {summary.InvestmentPortfolio.ytd_return && (
          <div className="summary-section">
            <span className="summary-section-title">YTD Return</span>
            <span className="summary-section-value">
              {`${(summary.InvestmentPortfolio.ytd_return * 100).toFixed(1)}%`}
            </span>
          </div>
        )}
      </div>
      <div className="horizontal-line"></div>
      <div className="summary-content">
        <div className="summary-header">
            <h4 className="summary-section-title text-left">
            Investment Portfolio
            </h4>
        </div>
      </div>      
      <div className="summary-details">
        {summary.InvestmentPortfolio.positions.map((pos) => (
          <div key={pos.symbol} className="summary-section">
            <p className="summary-section-title">{pos.symbol}</p>
            <p className="summary-section-value">
              {formatCompactCurrency(
                pos.marketValue.amount,
                summary.totalBalance.currency,
              )}
            </p>
          </div>
        ))}
      </div>
      </div>
    </div>
  )
}