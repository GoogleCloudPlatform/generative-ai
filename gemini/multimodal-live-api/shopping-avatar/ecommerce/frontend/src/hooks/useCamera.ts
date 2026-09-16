import { useState, useRef, useCallback, useEffect } from 'react';

export function useCamera(onFrame: (base64Image: string) => void) {
  const [isActive, setIsActive] = useState(false);
  const videoRef = useRef<HTMLVideoElement | null>(null);
  const canvasRef = useRef<HTMLCanvasElement | null>(null);
  const streamRef = useRef<MediaStream | null>(null);
  const intervalRef = useRef<any>(null);
  const onFrameRef = useRef(onFrame);

  useEffect(() => {
    onFrameRef.current = onFrame;
  }, [onFrame]);

  const stopCamera = useCallback(() => {
    if (intervalRef.current) {
      clearInterval(intervalRef.current);
      intervalRef.current = null;
    }
    if (streamRef.current) {
      streamRef.current.getTracks().forEach((track) => track.stop());
      streamRef.current = null;
    }
    if (videoRef.current) {
      videoRef.current.srcObject = null;
    }
    setIsActive(false);
  }, []);

  const startCamera = useCallback(async () => {
    try {
      const stream = await navigator.mediaDevices.getUserMedia({
        video: {
          width: { ideal: 512 },
          height: { ideal: 512 },
          facingMode: 'user',
        },
        audio: false,
      });

      streamRef.current = stream;
      setIsActive(true);

      if (!canvasRef.current) {
        canvasRef.current = document.createElement('canvas');
      }
      const canvas = canvasRef.current;
      canvas.width = 512;
      canvas.height = 512;
      const ctx = canvas.getContext('2d');

      intervalRef.current = setInterval(() => {
        if (!videoRef.current || !ctx || videoRef.current.paused || videoRef.current.ended) {
          return;
        }

        const video = videoRef.current;
        const videoWidth = video.videoWidth;
        const videoHeight = video.videoHeight;
        if (videoWidth === 0 || videoHeight === 0) return;

        const size = Math.min(videoWidth, videoHeight);
        const sourceX = (videoWidth - size) / 2;
        const sourceY = (videoHeight - size) / 2;

        ctx.drawImage(
          video,
          sourceX,
          sourceY,
          size,
          size,
          0,
          0,
          512,
          512
        );

        const dataUrl = canvas.toDataURL('image/jpeg', 0.85);
        const base64 = dataUrl.split(',')[1];
        if (base64) {
          onFrameRef.current(base64);
        }
      }, 1000);

    } catch (err) {
      console.error('[useCamera] Failed to access camera:', err);
      stopCamera();
      throw err;
    }
  }, [stopCamera]);

  useEffect(() => {
    if (isActive && streamRef.current && videoRef.current) {
      const video = videoRef.current;
      video.srcObject = streamRef.current;
      video.onloadedmetadata = () => {
        video.play().catch((err) => console.error('[useCamera] Video play failed:', err));
      };
    }
  }, [isActive]);

  useEffect(() => {
    return () => {
      if (intervalRef.current) {
        clearInterval(intervalRef.current);
      }
      if (streamRef.current) {
        streamRef.current.getTracks().forEach((track) => track.stop());
      }
    };
  }, []);

  return {
    isActive,
    videoRef,
    startCamera,
    stopCamera,
  };
}
