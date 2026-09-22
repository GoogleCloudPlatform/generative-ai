import { useEffect, useRef, memo, useState } from 'react';
import { Box, CircularProgress, Typography } from '@mui/material';

interface AvatarDisplay1PProps {
  status: 'idle' | 'initializing' | 'ready' | 'error';
  useVertexAI?: boolean;
  avatarName?: string;
}

export const AvatarDisplay1P = memo(({ status, useVertexAI = true, avatarName = 'Vera' }: AvatarDisplay1PProps) => {
  const videoRef = useRef<HTMLVideoElement>(null);
  const [hasFirstFrame, setHasFirstFrame] = useState(false);
  const [frameUrl, setFrameUrl] = useState<string | null>(null);

  useEffect(() => {
    if (status !== 'ready') {
      setHasFirstFrame(false);
      setFrameUrl(null);
    }
  }, [status]);

  useEffect(() => {
    if (!useVertexAI || !videoRef.current) return;

    const mediaSource = new MediaSource();
    videoRef.current.src = URL.createObjectURL(mediaSource);

    let sourceBuffer: SourceBuffer | null = null;
    const queue: ArrayBuffer[] = [];

    const processQueue = () => {
      if (!sourceBuffer || sourceBuffer.updating || queue.length === 0) return;
      try {
        const chunk = queue.shift();
        if (chunk) {
          sourceBuffer.appendBuffer(chunk);
        }
      } catch (e) {
        console.warn('[AvatarDisplay1P] appendBuffer error:', e);
      }
    };

    const handleSourceOpen = () => {
      try {
        const mimeCodec = [
          'video/mp4; codecs="avc1.42c020, mp4a.40.2"',
          'video/mp4; codecs="avc1.42e01e, mp4a.40.2"',
          'video/mp4; codecs="avc1.4d401f, mp4a.40.2"',
          'video/mp4'
        ].find(mime => MediaSource.isTypeSupported(mime)) || 'video/mp4';

        sourceBuffer = mediaSource.addSourceBuffer(mimeCodec);
        sourceBuffer.mode = 'sequence';

        sourceBuffer.addEventListener('updateend', () => {
          processQueue();
        });

        processQueue();
      } catch (err) {
        console.error('[AvatarDisplay1P] Failed to create SourceBuffer:', err);
      }
    };

    mediaSource.addEventListener('sourceopen', handleSourceOpen);

    const handleVideoChunk = (event: Event) => {
      const base64Data = (event as CustomEvent).detail;
      if (!base64Data) return;

      try {
        if (base64Data.startsWith('/9j/') || base64Data.startsWith('iVBORw')) {
          setFrameUrl(`data:image/jpeg;base64,${base64Data}`);
          setHasFirstFrame(true);
          return;
        }

        const binaryString = atob(base64Data);
        const uint8Array = new Uint8Array(binaryString.length);
        for (let i = 0; i < binaryString.length; i++) {
          uint8Array[i] = binaryString.charCodeAt(i);
        }

        queue.push(uint8Array.buffer);
        processQueue();

        if (videoRef.current?.paused && status === 'ready') {
          videoRef.current.play().catch(e => {
            if (e.name !== 'AbortError') {
              console.warn('[AvatarDisplay1P] Autoplay failed:', e);
            }
          });
        }
      } catch (err) {
        console.error('[AvatarDisplay1P] Error processing video segment:', err);
      }
    };

    window.addEventListener('video-chunk-received', handleVideoChunk);

    return () => {
      window.removeEventListener('video-chunk-received', handleVideoChunk);
      mediaSource.removeEventListener('sourceopen', handleSourceOpen);
      if (videoRef.current) {
        videoRef.current.removeAttribute('src');
        videoRef.current.load();
      }
    };
  }, [status, useVertexAI]);


  useEffect(() => {
    if (!useVertexAI) return;
    
    const video = videoRef.current;
    if (!video) return;

    const handlePlaying = () => {
       setHasFirstFrame(true);
    };

    video.addEventListener('playing', handlePlaying);
    return () => video.removeEventListener('playing', handlePlaying);
  }, [useVertexAI]);

  return (
    <Box sx={{
      position: 'relative',
      width: '100%',
      height: '100%',
      display: 'flex',
      alignItems: 'center',
      justifyContent: 'center',
      bgcolor: 'rgba(0,0,0,0.02)',
      borderRadius: 4,
      overflow: 'hidden'
    }}>
      {!useVertexAI && status === 'ready' ? (
        <Box sx={{
          display: 'flex',
          flexDirection: 'column',
          alignItems: 'center',
          gap: 2,
          p: 3
        }}>
          {/* Pulsing Avatar Container */}
          <Box sx={{
            position: 'relative',
            width: 140,
            height: 140,
            borderRadius: '50%',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            boxShadow: '0 8px 30px rgba(0,0,0,0.08)',
            '&::after': {
              content: '""',
              position: 'absolute',
              width: '100%',
              height: '100%',
              borderRadius: '50%',
              border: '3px solid #1976d2',
              animation: 'ripple 1.6s infinite ease-in-out',
            },
            '@keyframes ripple': {
              '0%': {
                transform: 'scale(0.96)',
                opacity: 0.8,
              },
              '100%': {
                transform: 'scale(1.25)',
                opacity: 0,
              },
            },
          }}>
            <Box
              component="img"
              src="/assistant_avatar.png"
              alt="Assistant Avatar"
              sx={{
                width: 130,
                height: 130,
                borderRadius: '50%',
                objectFit: 'cover',
                border: '3px solid #fff',
              }}
            />
          </Box>
          <Typography variant="body2" sx={{ fontWeight: 'bold', color: 'primary.main', mt: 1 }}>
            {avatarName} is listening...
          </Typography>
        </Box>
      ) : frameUrl ? (
        <Box
          component="img"
          src={frameUrl}
          alt="Speaking Avatar"
          sx={{
            width: '100%',
            height: '100%',
            objectFit: 'cover',
            objectPosition: 'center',
            display: 'block'
          }}
        />
      ) : (
        <video
          ref={videoRef}
          style={{
            width: '100%',
            height: '100%',
            objectFit: 'cover',
            objectPosition: 'center',
            display: (status === 'ready' && useVertexAI) ? 'block' : 'none'
          }}
          playsInline
        />
      )}
      
      {(status === 'initializing' || (status === 'ready' && useVertexAI && !hasFirstFrame)) && (
        <Box sx={{ 
          position: 'absolute',
          display: 'flex',
          flexDirection: 'column',
          alignItems: 'center',
          gap: 2
        }}>
          <CircularProgress size={40} />
          <Typography variant="body2" color="text.secondary">
            Connecting shopping assistant...
          </Typography>
        </Box>
      )}

      {status === 'error' && (
        <Typography color="error">
          Failed to load shopping avatar
        </Typography>
      )}
    </Box>
  );
});

AvatarDisplay1P.displayName = 'AvatarDisplay1P';
