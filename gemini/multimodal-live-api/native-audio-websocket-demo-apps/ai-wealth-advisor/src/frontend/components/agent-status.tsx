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
