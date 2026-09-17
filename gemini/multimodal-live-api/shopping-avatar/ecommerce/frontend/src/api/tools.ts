import { apiClient } from './client';

export interface MCPTool {
  name: string;
  description: string;
  inputSchema: unknown;
}

export const fetchMCPTools = async (personaId: string): Promise<MCPTool[]> => {
  const request = {
    jsonrpc: '2.0',
    id: 1,
    method: 'tools/list',
  };
  const { data } = await apiClient.post(`/mcp?persona=${encodeURIComponent(personaId)}`, request);
  if (data.error) {
    throw new Error(`MCP Error: ${data.error.message}`);
  }
  return data.result.tools;
};

export const executeMCPTool = async (
  name: string, 
  args: Record<string, unknown>, 
  personaId: string, 
  sessionId?: string
): Promise<unknown> => {
  const enrichedArgs = {
    ...args,
    ...(sessionId ? { session_id: sessionId } : {})
  };

  const request = {
    jsonrpc: '2.0',
    id: Date.now(),
    method: 'tools/call',
    params: {
      name: name,
      arguments: enrichedArgs,
    }
  };
  
  const { data } = await apiClient.post(`/mcp?persona=${encodeURIComponent(personaId)}`, request);
  
  if (data.error) {
    throw new Error(`MCP Error: ${data.error.message}`);
  }
  
  if (data.result.isError) {
      throw new Error(data.result.content[0]?.text || "Unknown tool error");
  }

  const content = data.result.content[0]?.text;
  if (content) {
    try {
        return JSON.parse(content);
    } catch {
        return content;
    }
  }
  return null;
};
