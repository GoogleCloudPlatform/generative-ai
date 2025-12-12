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
