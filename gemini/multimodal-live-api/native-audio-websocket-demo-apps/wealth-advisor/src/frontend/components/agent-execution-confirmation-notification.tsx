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

import React, { useState, useRef } from "react"
import SignatureCanvas from "react-signature-canvas"
import "./agent-execution-confirmation-notification.css"

export interface MobileNotificationData {
  type: "agent_execution_confirmation_notification"
  title: string
  allocation: string
  to: string
  estimated_outcome: string
}

interface MobileNotificationProps {
  data: MobileNotificationData
  onConfirm: () => void
  onCancel: () => void
}

export const MobileNotification: React.FC<MobileNotificationProps> = ({
  data,
  onConfirm,
  onCancel,
}) => {
  const sigCanvas = useRef<SignatureCanvas>(null)
  const [activeTab, setActiveTab] = useState("Draw")

  const clearSignature = () => {
    sigCanvas.current?.clear()
  }

  const handleConfirm = () => {
    onConfirm()
  }

  return (
    <div className="confirmation-overlay">
      <div className="confirmation-card sweep-in">
        <div className="confirmation-header">
          <h2 className="confirmation-title">{data.title}</h2>
          <button onClick={onCancel} className="edit-icon">
            <svg width="20" height="19" viewBox="0 0 20 19" fill="none" xmlns="http://www.w3.org/2000/svg">
                <path d="M0.927734 17.5C0.927734 18.0523 1.37545 18.5 1.92773 18.5L10.9277 18.5C11.48 18.5 
                    11.9277 18.0523 11.9277 17.5C11.9277 16.9477 11.48 16.5 10.9277 16.5L2.92773 16.5L2.92773
                    8.5C2.92773 7.94771 2.48002 7.5 1.92773 7.5C1.37545 7.5 0.927734 7.94771 0.927734 8.5V17.5ZM18.4277 
                    1L17.7206 0.292892L1.22063 16.7929L1.92773 17.5L2.63484 18.2071L19.1348 1.70711L18.4277 1Z" fill="white"/>
            </svg>
          </button>
        </div>

        <div className="confirmation-body">
          <div className="allocation-section">
            <div className="allocation-arrow">
              <svg
                width="2"
                height="100%"
                viewBox="0 0 2 105"
                fill="none"
                xmlns="http://www.w3.org/2000/svg"
              >
                <path d="M1 0V105" stroke="#424242" strokeWidth="1.5" />
                <path
                  d="M1 95L6 90M1 95L-4 90"
                  stroke="#424242"
                  strokeWidth="1.5"
                  strokeLinecap="round"
                />
              </svg>
            </div>
            <div>
              <p className="label">ALLOCATION</p>
              <p className="value">{data.allocation}</p>
              <div className="divider-horizontal" />
              <p className="label">TO</p>
              <p className="value">{data.to}</p>
            </div>
          </div>

          <div className="outcome-section">
            <p className="label">ESTIMATED OUTCOME</p>
            <p className="value">{data.estimated_outcome}</p>
          </div>

        </div>

        <div className="confirmation-footer">
          <div className="signature-section">
            <div className="signature-tabs">
              {["Draw", "Type", "Upload"].map((tab) => (
                <button
                  key={tab}
                  className={`signature-tab ${activeTab === tab ? "active" : ""}`}
                  onClick={() => setActiveTab(tab)}
                >
                  {tab}
                </button>
              ))}
              <button onClick={clearSignature} className="refresh-icon">
                <svg width="16" height="17" viewBox="0 0 16 17" fill="none" xmlns="http://www.w3.org/2000/svg">
                <path fill-rule="evenodd" clip-rule="evenodd" d="M8 1.52454C6.19 1.52454 4.52 2.25054 3.292 3.4832L2 
                    2.1912V6.1912H6L4.234 4.4252C5.216 3.43854 6.552 2.85787 8 2.85787C10.9407 2.85787 13.3333 5.25054 
                    13.3333 8.1912C13.3333 11.1319 10.9407 13.5245 8 13.5245V14.8579C11.676 14.8579 14.6667 11.8672 
                    14.6667 8.1912C14.6667 4.5152 11.676 1.52454 8 1.52454Z" fill="white"/>
                </svg>
              </button>
            </div>
            <div className="signature-canvas-container">
              {activeTab === "Draw" && (
                <SignatureCanvas
                  ref={sigCanvas}
                  penColor="black"
                  canvasProps={{
                    className: "signature-canvas",
                  }}
                />
              )}
              {activeTab === "Type" && (
                <div className="type-signature">
                  <input
                    type="text"
                    placeholder="Type your name"
                    className="type-signature-input"
                  />
                </div>
              )}
              {activeTab === "Upload" && (
                <div className="upload-signature">
                  <p>Upload your signature</p>
                </div>
              )}
            </div>
          </div>
          <div className="button-container">
            <button className="submit-btn" onClick={handleConfirm}>
              Submit
            </button>
            <button className="dismiss-btn" onClick={onCancel}>
              Dismiss
            </button>
          </div>
        </div>
      </div>
    </div>
  )
}
