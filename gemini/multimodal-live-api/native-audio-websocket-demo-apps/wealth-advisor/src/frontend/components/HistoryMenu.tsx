// Copyright 2025 Google LLC
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

import { useState } from "react"
import { Button } from "@/components/ui/button"
import { X } from "lucide-react"
import "./HistoryMenu.css"

export interface TranscriptItem {
  source: "user" | "agent";
  data: string;
}

interface ChatItem {
  id: number;
  name: string;
  description: string;
  time: string;
  tag: string;
  transcript: TranscriptItem[];
}

interface HistoryMenuProps {
  onRestore: (transcript: TranscriptItem[]) => void;
}

export function HistoryMenu({ onRestore }: HistoryMenuProps) {
  const [isOpen, setIsOpen] = useState(false);
  const [history] = useState<ChatItem[]>([
    {
      id: 1,
      name: "What is going on with the tariffs",
      description: "Here is a comprehensive update on what’s happening with the tariffs as of Aug 12th, 2025. Looking",
      time: "2h ago",
      tag: "Markets",
      transcript: [],
    },
    {
      id: 2,
      name: "Can you pull up Nvidia’s stock price",
      description: "As of this morning, Nvidia is currently at $125.76 which is around 2.5% more than yesterday. Might I suggest",
      time: "5 days ago",
      tag: "Portfolio",
      transcript: [],
    },
    {
      id: 3,
      name: "Show me how much time I have till I withdraw from my CD. And then tell me what I should invest in",
      description: "Looking at your CD accounts, you have $203,321 in total that would be maturing in 2 weeks time. I would suggest",
      time: "1 month ago",
      tag: "Retirement",
      transcript: [],
    },
  ]);

  return (
    <>
      {!isOpen && (
        <Button
          variant="outline"
          className="history-menu-button"
          onClick={() => setIsOpen(true)}
        >
          <svg
            viewBox="0 0 28 12"
            fill="none"
            xmlns="http://www.w3.org/2000/svg"
            className="!w-7 !h-7"
          >
            <path d="M0 1H24" stroke="white" strokeWidth="2" />
            <path d="M0 11H16" stroke="white" strokeWidth="2" />
          </svg>
        </Button>
      )}
      {isOpen && (
        <div className="absolute top-0 left-0 h-full w-full z-10">
          <div className="history-drawer absolute top-0 left-0 h-full">
            <div className="suggestion-prompt-box">
              <div className="text-area">
                <span className="text">Search</span>
              </div>
              <Button
                variant="ghost"
                size="icon"
                onClick={() => setIsOpen(false)}
              >
                <X className="h-7 w-7" />
              </Button>
            </div>
            <div className="history-items-container">
              {history.map((item) => (
                <div
                  key={item.id}
                  className="history-item-frame"
                  onClick={() => {
                    onRestore(item.transcript);
                    setIsOpen(false);
                  }}
                >
                  <div className="history-item-title">{item.name}</div>
                  <div className="history-item-description">{item.description}</div>
                  <div className="history-item-footer">
                    <div className="history-item-time">{item.time}</div>
                    <div className="history-item-tag-frame">
                      <div className="history-item-tag">{item.tag}</div>
                    </div>
                  </div>
                </div>
              ))}
            </div>
          </div>
        </div>
      )}
    </>
  );
}
