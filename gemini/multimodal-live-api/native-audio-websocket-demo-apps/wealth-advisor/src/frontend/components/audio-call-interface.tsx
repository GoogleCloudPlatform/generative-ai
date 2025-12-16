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

import * as React from "react"
import "./audio-call-interface.css"
import { useState, useEffect, useRef } from "react"
import Image from "next/image"
import {
  Mic,
  MicOff,
  Plus,
  Send,
} from "lucide-react"
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import { Card, CardContent } from "@/components/ui/card"
import {
  FinancialSummary,
  FinancialSummaryData,
} from "@/components/financial-summary"
import {
  CdOptionsDisplay,
  CdReinvestmentOptionsData,
} from "@/components/cd-options-display";
import {
  CurrentCdDisplay,
  CurrentCdDisplayData,
} from "@/components/current-cd-display";
import { StockPerformanceVisual, StockPerformanceData } from "./stock-performance-visual"
import { SoundWave } from "./sound-wave"

export interface Message {
  source: "user" | "agent";
  data: string;
  visual?: Visual;
}

export type Visual =
  | {
      type: "financial_summary_visual";
      data: FinancialSummaryData;
    }
  | {
      type: "cd_information";
      data: {
        current_cd_data: CurrentCdDisplayData;
        reinvestment_options_data: CdReinvestmentOptionsData;
      };
    }
  | {
      type: "current_cd_display";
      data: CurrentCdDisplayData;
    }
  | {
      type: "cd_options_display";
      data: CdReinvestmentOptionsData;
    }
  | {
      type: "rag_status";
      data: string;
    }
  | {
      type: "stock_performance_agent_status";
      data: string;
    }
  | {
      type: "appointment_scheduler_status";
      data: string;
    }
  | {
      type: "agent_execution_confirmation_notification_status";
      data: string;
    }
  | {
      type: "stock_performance_visual";
      data: StockPerformanceData;
    };

interface TranscriptMessage {
  id: string;
  text: string;
  disappearing?: boolean;
}

type VisualWithId = Visual & {
  id: string;
  disappearing?: boolean;
};

interface AudioCallInterfaceProps {
  messages: Message[];
  isAudio: boolean;
  isMuted: boolean;
  isFetching: boolean;
  toggleMute: () => void;
  sendTextMessage: (text: string) => void;
  sendFile: (file: File) => void;
  isTranscriptionVisible: boolean;
  isUserSpeaking: boolean;
}

export function AudioCallInterface({
  messages,
  isAudio,
  isMuted,
  isFetching,
  toggleMute,
  sendTextMessage,
  sendFile,
  isTranscriptionVisible,
  isUserSpeaking,
}: AudioCallInterfaceProps) {
  const [displayItems, setDisplayItems] = useState<(TranscriptMessage | VisualWithId)[]>([]);
  const [userMessageCount, setUserMessageCount] = useState(0);
  const prevUserText = useRef("");
  const prevAgentText = useRef("");
  const renderedVisualsRef = useRef<Set<string>>(new Set());

  const RagFetchingIndicator = () => (
    <div className="flex flex-col mb-2 items-start">
      <div className="rounded-3xl rounded-tl-sm agent-bubble px-3 py-3 bg-black/80 text-white transcription-tile">
        <div className="flex items-center space-x-3">
          <Image
            src="/figma/login-success-loader.png"
            alt="Loading"
            width={24}
            height={24}
            className="animate-spin"
          />
          <span className="font-sans-text text-base">
            Gathering information...
          </span>
        </div>
      </div>
    </div>
  );

  const fileInputRef = useRef<HTMLInputElement>(null)

  const handleFileChange = (event: React.ChangeEvent<HTMLInputElement>) => {
    const file = event.target.files?.[0]
    if (file) {
      sendFile(file)
    }
  }

  const handleAddAttachmentClick = () => {
    fileInputRef.current?.click()
  }

  const [textMessage, setTextMessage] = useState("")

  const handleSendTextMessage = () => {
    if (textMessage.trim()) {
      const text = textMessage.trim();
      sendTextMessage(text);
      setTextMessage("");

      const newMessage = { id: `user-${Date.now()}`, text: text, source: "user" };
      setDisplayItems(prev => [...prev, newMessage].slice(-5));
      setUserMessageCount(prev => prev + 1);
      prevUserText.current = prevUserText.current ? `${prevUserText.current} ${text}`: text;
    }
  };

  useEffect(() => {
    const userMessage = messages.find((m) => m.source === "user");
    const agentMessage = messages.find((m) => m.source === "agent");

    const newUserText = userMessage?.data || "";
    const newAgentText = agentMessage?.data || "";

    if (newUserText !== prevUserText.current) {
      const diff = newUserText.substring(prevUserText.current.length);
      if (diff) {
        const newMessage = { id: `user-${Date.now()}`, text: diff, source: "user" };
        setDisplayItems(prev => [...prev, newMessage].slice(-5));
        setUserMessageCount(prev => prev + 1);
      }
      prevUserText.current = newUserText;
    }

    if (newAgentText !== prevAgentText.current) {
      const diff = newAgentText.substring(prevAgentText.current.length);
      if (diff) {
        const newMessage = { id: `agent-${Date.now()}`, text: diff, source: "agent" };
        setDisplayItems(prev => [...prev, newMessage].slice(-5));
      }
      prevAgentText.current = newAgentText;
    }

    const agentVisual = agentMessage?.visual;
    if (agentVisual) {
      if (agentVisual.type === "cd_information") {
        const visualsToAdd: VisualWithId[] = [];
        if (!renderedVisualsRef.current.has("current_cd_display")) {
          visualsToAdd.push({ type: "current_cd_display" as const, data: agentVisual.data.current_cd_data, id: `visual-${Date.now()}-1` });
          renderedVisualsRef.current.add("current_cd_display");
        }
        if (!renderedVisualsRef.current.has("cd_options_display")) {
          visualsToAdd.push({ type: "cd_options_display" as const, data: agentVisual.data.reinvestment_options_data, id: `visual-${Date.now()}-2` });
          renderedVisualsRef.current.add("cd_options_display");
        }
        if (visualsToAdd.length > 0) {
          setDisplayItems(prev => [...prev, ...visualsToAdd].slice(-5));
        }
      } else if (!renderedVisualsRef.current.has(agentVisual.type)) {
        const newVisual = { ...agentVisual, id: `visual-${Date.now()}` };
        setDisplayItems(prev => [...prev, newVisual].slice(-5));
        renderedVisualsRef.current.add(agentVisual.type);
      }
    }
  }, [messages]);

  useEffect(() => {
    if (displayItems.length > 4) {
      const timeoutId = setTimeout(() => {
        setDisplayItems(prev =>
          prev.map((item, index) =>
            index === 0 ? { ...item, disappearing: true } : item
          )
        );
        setTimeout(() => {
          setDisplayItems(prev => prev.slice(1));
        }, 1000); // Corresponds to the animation duration
      }, 4000); // 5s total - 1s for animation
      return () => clearTimeout(timeoutId);
    }
  }, [displayItems]);

  return (
    <div className="h-full flex items-end justify-center">
      <Card className="w-full bg-transparent border-none relative max-w-2xl">
        <CardContent className="relative z-10 p-8">
          <div className="flex flex-col text-center space-y-6 relative h-full pt-12">
            {isAudio && isTranscriptionVisible && (
              <div className={`rounded-lg relative p-2 text-left mt-4 transcription-container w-full ${userMessageCount <= 1 ? "no-fade" : ""}`}>
                <div className="h-100 overflow-y-auto transcription-scroll-area" style={{ scrollBehavior: 'smooth' }}>
                  {displayItems.map((item) => {
                    if ("text" in item) {
                      const transcript = item as TranscriptMessage & { source: string };
                      const isUser = transcript.source === "user";
                      const bubbleClasses = isUser
                        ? "rounded-3xl rounded-tr-sm user-bubble"
                        : "rounded-3xl rounded-tl-sm agent-bubble";
                      return (
                        <div key={item.id} className={`flex flex-col mb-2 ${isUser ? "items-end" : "items-start"} ${item.disappearing ? "disappearing" : ""}`}>
                          <div className={`${bubbleClasses} px-2 py-2 bg-black/80 text-white transcription-tile`}>
                            <p className="text-base">{transcript.text}</p>
                          </div>
                        </div>
                      );
                    } else {
                      return (
                        <div key={item.id} className={`visual-item rounded-3xl rounded-tl-sm bg-black/80 border border-white/20 p-4 ${item.disappearing ? "disappearing" : ""}`}>
                          {(() => {
                            const visual = item as VisualWithId;
                            switch (visual.type) {
                              case "current_cd_display":
                                return visual.data ? <CurrentCdDisplay data={visual.data as CurrentCdDisplayData} /> : null;
                              case "cd_options_display":
                                return visual.data ? <CdOptionsDisplay data={visual.data as CdReinvestmentOptionsData} /> : null;
                              case "cd_information":
                                // This case should not be hit if the logic in useEffect is correct
                                return null;
                              case "financial_summary_visual":
                                return <FinancialSummary summary={visual.data as FinancialSummaryData} onClose={() => {}} />;
                              case "stock_performance_visual":
                                return <StockPerformanceVisual data={visual.data as StockPerformanceData} />;
                              default:
                                return null;
                            }
                          })()}
                        </div>
                      );
                    }
                  })}
                  {isFetching && <RagFetchingIndicator />}
                </div>
              </div>
            )}

            {/* Call Controls */}
              <div className="mt-auto call-controls">
                {isAudio && (
                  <div className="flex flex-col items-center px-6 pt-6 pb-0 gap-6 bg-black/80 border border-[#444444] rounded-[22px] w-full">
                    <div className="w-full flex items-center" style={{ height: "40px" }}>
                      {isUserSpeaking ? (
                        <div className="flex items-center justify-start w-full">
                          <div className="flex items-center">
                            <SoundWave />
                            <div className="text-white ml-2 font-normal !text-[17px]">Listening...</div>
                          </div>
                        </div>
                      ) : (
                        <div className="flex items-center justify-between w-full gap-3">
                          <Input
                            placeholder="Ask me Anything"
                            className="transparent-input placeholder-white/80 text-white font-normal !text-[17px] flex-grow border-none shadow-none focus-visible:ring-0 p-0 h-auto"
                            value={textMessage}
                            onChange={(e) => setTextMessage(e.target.value)}
                            onKeyDown={(e) => {
                              if (e.key === "Enter") {
                                handleSendTextMessage();
                              }
                            }}
                          />
                          <Button
                            variant="ghost"
                            size="icon"
                            onClick={handleSendTextMessage}
                            className="!h-6 !w-6 p-0 hover:bg-transparent mr-2"
                          >
                            <Send className="!h-6 !w-6" />
                          </Button>
                        </div>
                      )}
                    </div>
                    <div className="flex items-center justify-between w-full border-t border-[#444444] gap-[9px]">
                      {/* Add Attachment */}
                      <Button
                        variant="ghost"
                        className="flex flex-col justify-center items-center rounded-[22px] flex-grow p-3 h-[55px] hover:bg-transparent"
                        onClick={handleAddAttachmentClick}
                      >
                        <Plus className="!h-6 !w-6" />
                      </Button>
                      <input
                        type="file"
                        ref={fileInputRef}
                        onChange={handleFileChange}
                        className="hidden"
                      />

                      {/* Mute Toggle */}
                      <Button
                        variant="ghost"
                        className={`flex flex-col justify-center items-center rounded-[22px] flex-grow p-3 h-[55px] hover:bg-transparent ${
                          isMuted ? "text-red-500" : ""
                        }`}
                        onClick={toggleMute}
                        disabled={isUserSpeaking}
                      >
                        {!isMuted ? (
                          <Mic className="!h-6 !w-6" />
                        ) : (
                          <MicOff className="!h-6 !w-6" />
                        )}
                      </Button>


                    </div>
                  </div>
                )}
              </div>

          </div>
        </CardContent>
      </Card>
    </div>
  );
}