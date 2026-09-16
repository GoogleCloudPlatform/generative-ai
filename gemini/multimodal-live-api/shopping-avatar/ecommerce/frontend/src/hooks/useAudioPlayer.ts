import { useRef, useCallback, useState, useEffect } from 'react';
import workletUrl from './playbackWorklet?worker&url';

export interface UseAudioPlayerOptions {
  onAudioChunk?: (base64Audio: string) => void;
  muteLocalPlayback?: boolean;
}

export function useAudioPlayer({ onAudioChunk, muteLocalPlayback = false }: UseAudioPlayerOptions = {}) {
  const audioContextRef = useRef<AudioContext | null>(null);
  const mediaStreamDestinationRef = useRef<MediaStreamAudioDestinationNode | null>(null);
  const workletNodeRef = useRef<AudioWorkletNode | null>(null);
  const [geminiStream, setGeminiStream] = useState<MediaStream | null>(null);
  const isWorkletLoadedRef = useRef<boolean>(false);
  const chunksReceivedRef = useRef<number>(0);
  const initPromiseRef = useRef<Promise<void> | null>(null);

  const initAudio = useCallback(async () => {
    if (initPromiseRef.current) return initPromiseRef.current;
    
    initPromiseRef.current = (async () => {
      if (!audioContextRef.current) {
        const AudioContextClass = window.AudioContext || (window as unknown as { webkitAudioContext: typeof window.AudioContext }).webkitAudioContext;
        // Output format requires 24kHz sample rate matching Gemini speech synthesis
        const ctx = new AudioContextClass({ sampleRate: 24000 });
        audioContextRef.current = ctx;
        
        const dest = ctx.createMediaStreamDestination();
        mediaStreamDestinationRef.current = dest;
        setGeminiStream(dest.stream);
      }
      
      const ctx = audioContextRef.current;
      if (ctx.state === 'suspended') {
        await ctx.resume();
      }
      
      if (!isWorkletLoadedRef.current) {
          await ctx.audioWorklet.addModule(workletUrl);
          isWorkletLoadedRef.current = true;
          
          const workletNode = new AudioWorkletNode(ctx, 'playback-processor');
          workletNodeRef.current = workletNode;
          
          if (!muteLocalPlayback) {
              workletNode.connect(ctx.destination);
          }
          if (mediaStreamDestinationRef.current) {
              workletNode.connect(mediaStreamDestinationRef.current);
          }
      }
    })();
    
    return initPromiseRef.current;
  }, [muteLocalPlayback]);

  useEffect(() => {
    if (workletNodeRef.current && audioContextRef.current) {
      const workletNode = workletNodeRef.current;
      const ctx = audioContextRef.current;
      if (!muteLocalPlayback) {
        try {
          workletNode.connect(ctx.destination);
        } catch { /* empty */ }
      } else {
        try {
          workletNode.disconnect(ctx.destination);
        } catch { /* empty */ }
      }
    }
  }, [muteLocalPlayback]);

  const playAudioChunk = useCallback(async (floatBuffer: ArrayBuffer, base64Audio?: string) => {
    try {
      if (onAudioChunk && base64Audio) {
        onAudioChunk(base64Audio);
      }

      if (!isWorkletLoadedRef.current || !workletNodeRef.current) {
        await initAudio();
      }
      
      if (!workletNodeRef.current) return;

      // Transfer ownership of array buffer
      workletNodeRef.current.port.postMessage({ type: 'AUDIO', payload: floatBuffer }, [floatBuffer]);
      
      chunksReceivedRef.current += 1;
      if (chunksReceivedRef.current === 1) { 
        window.dispatchEvent(new CustomEvent('audio-playback-started'));
      }
    } catch (e) {
      console.error('Failed to play audio chunk:', e);
    }
  }, [onAudioChunk, initAudio]);

  const stopAudioPlayback = useCallback(() => {
    if (workletNodeRef.current) {
        workletNodeRef.current.port.postMessage({ type: 'FLUSH' });
    }
    chunksReceivedRef.current = 0;
  }, []);

  const suspendAudioContext = useCallback(async () => {
      if (audioContextRef.current && audioContextRef.current.state === 'running') {
          await audioContextRef.current.suspend();
      }
  }, []);

  const resumeAudioContext = useCallback(async () => {
      await initAudio();
      if (audioContextRef.current && audioContextRef.current.state === 'suspended') {
          await audioContextRef.current.resume();
      }
  }, [initAudio]);

  useEffect(() => {
    return () => {
      if (audioContextRef.current) {
        audioContextRef.current.close().catch(e => console.warn('[useAudioPlayer] Close error:', e));
        audioContextRef.current = null;
        isWorkletLoadedRef.current = false;
        initPromiseRef.current = null;
      }
    };
  }, []);

  return {
    geminiStream,
    playAudioChunk,
    stopAudioPlayback,
    suspendAudioContext,
    resumeAudioContext
  };
}
