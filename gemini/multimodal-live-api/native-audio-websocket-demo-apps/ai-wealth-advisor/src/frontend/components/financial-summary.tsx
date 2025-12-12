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
          <span className="summary-section-value">$2.5M</span>
        </div>
        <div className="summary-section">
          <span className="summary-section-title">Liabilities</span>
          <span className="summary-section-value">$500K</span>
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
