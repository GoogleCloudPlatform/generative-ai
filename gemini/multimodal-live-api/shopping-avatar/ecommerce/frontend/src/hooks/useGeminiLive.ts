import { useState, useCallback, useRef } from 'react';
import { useAudioRecorder } from './useAudioRecorder';
import { useAudioPlayer } from './useAudioPlayer';
import { useMCPExecution } from './useMCPExecution';
import { fetchMCPTools } from '../api/tools';
import { GeminiLiveApi } from '../services/geminiLiveApi';

export interface Message {
  text: string;
  sender: 'user' | 'model';
  id: string;
}

export function useGeminiLive(mode: 'none' | 'google_1p' = 'none', sessionId?: string, avatar: string = 'Vera') {
  const [connectionState, setConnectionState] = useState<'connected' | 'disconnected' | 'error' | 'connecting'>('disconnected');
  const [messages, setMessages] = useState<Message[]>([]);
  const [isThinking, setIsThinking] = useState(false);
  const [isModelSpeaking, setIsModelSpeaking] = useState(false);

  const apiRef = useRef<GeminiLiveApi | null>(null);
  const mcpToolsRef = useRef<any[]>([]);
  const configRef = useRef<any>(null);


  const appendOrUpdateMessage = useCallback((text: string, sender: 'user' | 'model') => {
    setMessages(prev => {
      // Find if we have an active temporary message from this sender
      const last = prev[prev.length - 1];
      if (last && last.sender === sender) {
        return [...prev.slice(0, prev.length - 1), { ...last, text: last.text + text }];
      }
      return [...prev, { text, sender, id: `msg_${Date.now()}` }];
    });
  }, []);

  const {
    isProcessingTool,
    activeVisual,
    activeOverlay,
    handleToolCall,
    clearActiveVisual
  } = useMCPExecution(apiRef as any, connectionState, sessionId);

  const handleToolCallRef = useRef(handleToolCall);
  handleToolCallRef.current = handleToolCall;

  const { playAudioChunk, stopAudioPlayback, suspendAudioContext, resumeAudioContext } = useAudioPlayer({
    onAudioChunk: () => {}
  });

  const handleAudioChunk = useCallback((data: ArrayBuffer) => {
    if (isProcessingTool) return;
    if (apiRef.current && connectionState === 'connected') {
      apiRef.current.sendAudioChunk(data);
    }
  }, [isProcessingTool, connectionState]);

  const handleVADStateChange = useCallback((isSpeaking: boolean) => {
    if (isSpeaking) {
      setIsThinking(false);
    } else {
      setIsThinking(true);
    }
  }, []);

  const { isRecording, startRecording, stopRecording } = useAudioRecorder(handleAudioChunk, handleVADStateChange);

  const connect = useCallback(async () => {
    if (connectionState !== 'disconnected') return;
    setConnectionState('connecting');

    try {
      // Resume AudioContext immediately within user gesture frame for mobile browsers
      await resumeAudioContext();

      // 1. Fetch dynamic config
      const res = await fetch(`/api/config?mode=${mode}&avatar=${encodeURIComponent(avatar)}`);
      const config = await res.json();

      configRef.current = config;

      // 2. Fetch allowed tools
      const tools = await fetchMCPTools("default-shopper");
      mcpToolsRef.current = tools;

      // 3. Spawn API and worker thread
      const api = new GeminiLiveApi({
        apiKey: config.apiKey,
        modelName: config.modelName,
        systemPrompt: config.systemPrompt,
        mcpTools: tools,
        useVertexAI: config.useVertexAI,
        vertexProject: config.vertexProjectID,
        vertexLocation: config.vertexLocation,
        avatarMode: config.avatarMode,
        google1PAvatarName: config.google1PAvatarName,
        google1PVoiceName: config.google1PVoiceName,
        onStateChange: (state) => {
          setConnectionState(state);
          if (state === 'disconnected') {
            stopRecording();
            setIsModelSpeaking(false);
            setIsThinking(false);
          }
        },
        onAudioReceived: (payload) => {
          playAudioChunk(payload.buffer, payload.base64);
          setIsThinking(false);
          setIsModelSpeaking(true);
        },
        onVideoReceived: (base64Video) => {
          // Dispatched directly to custom events for the AvatarDisplay1P element
          const event = new CustomEvent('video-chunk-received', { detail: base64Video });
          window.dispatchEvent(event);
        },
        onToolCall: (tc) => {
          stopAudioPlayback();
          handleToolCallRef.current(tc);
        },
        onTranscription: (tr) => {
          if (tr.type === 'input') {
            appendOrUpdateMessage(tr.text, 'user');
          } else {
            appendOrUpdateMessage(tr.text, 'model');
          }
        },
        onInterrupted: () => {
          stopAudioPlayback();
          setIsModelSpeaking(false);
          setIsThinking(false);
        },
        onTurnComplete: () => {
          setIsModelSpeaking(false);
        }
      });

      apiRef.current = api;
      await api.connect();
      await startRecording();

    } catch (e) {
      console.error('Failed to start Live session:', e);
      setConnectionState('error');
    }
  }, [mode, avatar, connectionState, resumeAudioContext, playAudioChunk, stopAudioPlayback, startRecording, stopRecording, handleToolCall, appendOrUpdateMessage]);

  const disconnect = useCallback(() => {
    if (apiRef.current) {
      apiRef.current.disconnect();
      apiRef.current = null;
    }
    setConnectionState('disconnected');
    stopRecording();
    stopAudioPlayback();
    setIsModelSpeaking(false);
    setIsThinking(false);
    clearActiveVisual();
    suspendAudioContext();
  }, [stopRecording, stopAudioPlayback, suspendAudioContext, clearActiveVisual]);

  const sendTextMessage = useCallback((text: string) => {
    if (apiRef.current && connectionState === 'connected') {
      appendOrUpdateMessage(text, 'user');
      setIsThinking(true);
      apiRef.current.sendTextMessage(text);
    }
  }, [connectionState, appendOrUpdateMessage]);

  const sendVideoFrame = useCallback((base64Image: string) => {
    if (apiRef.current && connectionState === 'connected') {
      apiRef.current.sendVideoFrame(base64Image);
    }
  }, [connectionState]);

  return {
    connectionState,
    isRecording,
    isProcessingTool,
    messages,
    activeVisual,
    activeOverlay,
    isThinking,
    isModelSpeaking,
    connect,
    disconnect,
    sendTextMessage,
    sendVideoFrame,
    config: configRef.current
  };
}

