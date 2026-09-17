import { useState, useCallback } from 'react';
import { executeMCPTool } from '../api/tools';

export interface ToolCall {
  functionCall: {
    name: string;
    args: Record<string, unknown>;
    id: string;
  };
}

export interface IGeminiLiveClient {
  sendToolResponse: (name: string, id: string, result: unknown) => void;
}

export type ActiveVisual = {
  toolName: string;
  arguments?: Record<string, unknown>;
  data: unknown;
} | null;

export function useMCPExecution(
  apiRef: React.MutableRefObject<IGeminiLiveClient | null>, 
  connectionState: 'connected' | 'disconnected' | 'error' | 'connecting',
  sessionId?: string
) {
  const [isProcessingTool, setIsProcessingTool] = useState(false);
  const [activeVisual, setActiveVisual] = useState<ActiveVisual>(null);
  const [activeOverlay, setActiveOverlay] = useState<'cart' | 'checkout' | 'products' | null>(null);

  const clearActiveVisual = useCallback(() => {
    setActiveVisual(null);
    setActiveOverlay(null);
  }, []);

  const handleToolCall = useCallback(async (toolCall: ToolCall) => {
    const name = toolCall.functionCall.name;
    const args = toolCall.functionCall.args;
    setIsProcessingTool(true);

    try {
      // 1. Execute back-end task
      const response = await executeMCPTool(
        name,
        args,
        "default-shopper",
        sessionId
      );      

      // 2. Commit upstream tool response BEFORE unblocking client mic
      if (apiRef.current && connectionState === 'connected') {
        let finalResponse = response;
        if (finalResponse !== undefined && finalResponse !== null) {
          if (Array.isArray(finalResponse)) {
            finalResponse = { items: finalResponse };
          } else if (typeof finalResponse !== 'object') {
            finalResponse = { value: finalResponse };
          }
        }
        apiRef.current.sendToolResponse(name, toolCall.functionCall.id, finalResponse || {});
      }

      // 3. Coordinate UI trigger aligned with downstream audio start
      if (response !== undefined) {
        const triggerVisuals = () => {
          if (connectionState !== 'connected') return;

          setActiveVisual({
            toolName: name,
            arguments: args,
            data: response
          });

          if (name === 'search_products') {
            setActiveOverlay('products');
          } else if (['add_to_cart', 'update_cart_item', 'remove_from_cart', 'get_cart'].includes(name)) {
            setActiveOverlay('cart');
          } else if (name === 'checkout_cart') {
            setActiveOverlay('checkout');
          }
        };

        await new Promise<void>((resolve) => {
          let triggered = false;
          const syncHandler = () => {
            if (!triggered) {
              triggered = true;
              setIsProcessingTool(false);
              triggerVisuals();
              window.removeEventListener('audio-playback-started', syncHandler);
              window.removeEventListener('video-chunk-received', syncHandler);
              resolve();
            }
          };

          window.addEventListener('audio-playback-started', syncHandler);
          window.addEventListener('video-chunk-received', syncHandler);

          // Latency safety guard
          setTimeout(() => {
            if (!triggered) {
              triggered = true;
              setIsProcessingTool(false);
              triggerVisuals();
              window.removeEventListener('audio-playback-started', syncHandler);
              window.removeEventListener('video-chunk-received', syncHandler);
              resolve();
            }
          }, 3500);
        });
      } else {
        setIsProcessingTool(false);
      }
    } catch (error) {
      setIsProcessingTool(false);
      console.error(`Tool execution failed: ${name}`, error);
      if (apiRef.current && connectionState === 'connected') {
          apiRef.current.sendToolResponse(name, toolCall.functionCall.id, { 
              error: 'E-commerce tool execution failed', 
              status: 'ERROR' 
          });
      }
    }
  }, [apiRef, connectionState, sessionId]);

  return {
    isProcessingTool,
    activeVisual,
    activeOverlay,
    handleToolCall,
    clearActiveVisual
  };
}
