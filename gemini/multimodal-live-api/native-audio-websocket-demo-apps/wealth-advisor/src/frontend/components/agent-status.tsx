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
import { SoundWave } from "./sound-wave"

interface AgentStatusProps {
  isSpeaking: boolean
  isListening: boolean
}

export function AgentStatus({ isSpeaking, isListening }: AgentStatusProps) {
  return (
    <div className="flex flex-col items-center justify-center h-full w-full">
      <div className="relative w-48 h-48 flex items-center justify-center rounded-full bg-neutral-900 border-2 border-neutral-700 shadow-2xl">
        {isSpeaking ? (
          <div className="flex flex-col items-center gap-4 animate-fade-in">
             <SoundWave />
             <span className="text-neutral-400 text-sm tracking-widest uppercase">Agent Speaking</span>
          </div>
        ) : isListening ? (
           <div className="flex flex-col items-center gap-4 animate-fade-in">
             <div className="w-4 h-4 rounded-full bg-red-500 animate-pulse shadow-[0_0_15px_rgba(239,68,68,0.5)]" />
             <span className="text-neutral-400 text-sm tracking-widest uppercase">Listening...</span>
           </div>
        ) : (
          <span className="text-neutral-500 text-sm">Connecting...</span>
        )}
      </div>
    </div>
  )
}