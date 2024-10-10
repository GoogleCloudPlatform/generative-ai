/**
 * Copyright 2024 Google LLC
 *
 * Licensed under the Apache License, Version 2.0 (the "License");
 * you may not use this file except in compliance with the License.
 * You may obtain a copy of the License at
 *
 *     http://www.apache.org/licenses/LICENSE-2.0
 *
 * Unless required by applicable law or agreed to in writing, software
 * distributed under the License is distributed on an "AS IS" BASIS,
 * WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
 * See the License for the specific language governing permissions and
 * limitations under the License.
 */

'use client';

import React, { useState, useRef, useEffect } from 'react';
import { usePathname } from 'next/navigation';
import { Send, Trash2, Search } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import Icon, { IconSpinner, IconGemini } from '@/components/ui/icons';
import PageSidebar from '@/components/ui/page-sidebar';
import AboutPageContent from '@/components/ui/about-page-content';
import { Card, CardContent } from '@/components/ui/card';
import { ScrollArea } from '@/components/ui/scroll-area';
import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import { cn } from '@/lib/utils';
import GroundedTextBlock from '@/components/ui/grounded-text-block';
import { makeExampleQuestions } from '@/lib/grounding_option_utils';
import ExampleQuestionGreeting from '@/components/ui/example-question-greeting';

interface Message {
  role: 'user' | 'model';
  content: string;
  searchEntryPoint?: string;
  groundingSupport?: GroundingSupport[];
  supportChunks?: SupportChunk[];
}

interface ResponseData {
  text: string;
  groundingSupport?: GroundingSupport[];
  supportChunks?: SupportChunk[];
  searchEntryPoint?: string;
}
interface GroundingSupport {
  claimText: string;
  supportChunkIndices: number[];
}

interface SupportChunk {
  index: number;
  chunkText: string;
  source: string;
  sourceMetadata: {
    title: string;
    page_identifier: string;
    uri: string;
    document_id: string;
  };
}

interface ExampleQuestion {
  text: string;
  icon?: string;
}

export default function AppPage() {
  const [sidebarOpen, setSidebarOpen] = useState(false);
  const [exampleQuestions, setExampleQuestions] =
    useState<ExampleQuestion[]>(makeExampleQuestions());
  const [googleGrounding, setGoogleGrounding] = useState(true);
  const [vertexGrounding, setVertexGrounding] = useState(false);
  const [groundingOptions, setGroundingOptionsState] = useState<string[]>([]);
  const [vertexConfigId, setVertexConfigId] = useState(
    'projects/503991587623/locations/global/collections/default_collection/engines/test-gg_1724941548160/servingConfigs/default_search',
  );
  const [messages, setMessages] = useState<Message[]>([]);
  const [inputMessage, setInputMessage] = useState('');
  const [isStreaming, setIsStreaming] = useState(false);
  const [selectedModel, setSelectedModel] = useState('gemini-1.5-flash-001');
  const [temperature, setTemperature] = useState(0.2);
  const [retrievalThreshold, setRetrievalThreshold] = useState(0.5);
  const [activeTab, setActiveTab] = useState('chat');
  const [activeAboutTab, setActiveAboutTab] = useState('javascript');
  const [responses, setResponses] = useState<{
    grounded: ResponseData;
    ungrounded: ResponseData;
  }>({
    grounded: {
      text: '',
      groundingSupport: [],
      supportChunks: [],
      searchEntryPoint: '',
    },
    ungrounded: { text: '', groundingSupport: [], supportChunks: [] },
  });
  const [showResponses, setShowResponses] = useState(false);

  const messagesEndRef = useRef<HTMLDivElement>(null);
  const pathname = usePathname();

  const toggleSidebar = () => setSidebarOpen(!sidebarOpen);

  useEffect(() => {
    if (messagesEndRef.current) {
      messagesEndRef.current.scrollIntoView({ behavior: 'smooth' });
    }
  }, [messages]);

  const handleMessageFormSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!inputMessage.trim() || isStreaming) return;
    sendMessage(inputMessage);
  };

  const sendMessage = async (inputMessage: string) => {
    const newUserMessage: Message = { role: 'user', content: inputMessage };
    setMessages((prevMessages) => [...prevMessages, newUserMessage]);
    setInputMessage('');
    setIsStreaming(true);

    try {
      const response = await fetch('/api/chat', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          messages: [...messages, newUserMessage],
          model: selectedModel,
          groundingOptions,
          googleGrounding,
          vertexGrounding,
          vertexConfigId: vertexGrounding ? vertexConfigId : undefined,
          temperature,
          retrievalThreshold,
        }),
      });

      if (!response.body) {
        throw new Error('Response body is null');
      }

      const reader = response.body.getReader();
      const decoder = new TextDecoder();
      let accumulatedResponse = '';
      let currentMessage: Message = { role: 'model', content: '' };

      while (true) {
        const { done, value } = await reader.read();
        if (done) break;

        const chunk = decoder.decode(value, { stream: true });
        accumulatedResponse += chunk;

        let jsonChunk;
        while (accumulatedResponse.includes('\n')) {
          const newlineIndex = accumulatedResponse.indexOf('\n');
          const jsonString = accumulatedResponse.slice(0, newlineIndex);
          accumulatedResponse = accumulatedResponse.slice(newlineIndex + 1);

          try {
            jsonChunk = JSON.parse(jsonString);
            if (jsonChunk.text) {
              currentMessage.content += jsonChunk.text;
            }
            if (jsonChunk.searchEntryPoint) {
              currentMessage.searchEntryPoint = jsonChunk.searchEntryPoint;
            }
            if (jsonChunk.groundingSupport) {
              currentMessage.groundingSupport = jsonChunk.groundingSupport;
            }
            if (jsonChunk.supportChunks) {
              currentMessage.supportChunks = jsonChunk.supportChunks;
            }
            setMessages((prevMessages) => {
              const lastMessage = prevMessages[prevMessages.length - 1];
              if (lastMessage.role === 'model') {
                return [...prevMessages.slice(0, -1), { ...currentMessage }];
              } else {
                return [...prevMessages, { ...currentMessage }];
              }
            });
          } catch (error) {
            console.error('Error parsing JSON:', error);
          }
        }
      }

      // Handle any remaining response
      if (accumulatedResponse) {
        try {
          const jsonChunk = JSON.parse(accumulatedResponse);
          if (jsonChunk.text) {
            currentMessage.content += jsonChunk.text;
          }
          if (jsonChunk.searchEntryPoint) {
            currentMessage.searchEntryPoint = jsonChunk.searchEntryPoint;
          }
          if (jsonChunk.groundingSupport) {
            currentMessage.groundingSupport = jsonChunk.groundingSupport;
          }
          if (jsonChunk.supportChunks) {
            currentMessage.supportChunks = jsonChunk.supportChunks;
          }
          setMessages((prevMessages) => {
            const lastMessage = prevMessages[prevMessages.length - 1];
            if (lastMessage.role === 'model') {
              return [...prevMessages.slice(0, -1), { ...currentMessage }];
            } else {
              return [...prevMessages, { ...currentMessage }];
            }
          });
        } catch (error) {
          console.error('Error parsing JSON:', error);
        }
      }
    } catch (error) {
      console.error('Error in chat request:', error);
    } finally {
      console.log('setting isStreaming false');
      setIsStreaming(false);
    }
  };

  const clearChat = () => {
    setMessages([]);
  };

  const handleSearch = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!inputMessage.trim()) return;
    setIsStreaming(true);
    setResponses({
      grounded: {
        text: '',
        groundingSupport: [],
        supportChunks: [],
        searchEntryPoint: '',
      },
      ungrounded: { text: '', groundingSupport: [], supportChunks: [] },
    });
    setShowResponses(true);

    const fetchGroundedStream = async () => {
      const response = await fetch('/api/grounded', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          query: inputMessage,
          model: selectedModel,
          groundingOptions,
          googleGrounding,
          vertexGrounding,
          vertexConfigId: vertexGrounding ? vertexConfigId : undefined,
          retrievalThreshold,
        }),
      });

      if (!response.body) {
        console.error('Response body is null');
        return {
          text: '',
          groundingSupport: [],
          supportChunks: [],
          searchEntryPoint: '',
        };
      }

      const reader = response.body.getReader();
      const decoder = new TextDecoder();
      let buffer = '';
      let result: ResponseData = {
        text: '',
        groundingSupport: [],
        supportChunks: [],
        searchEntryPoint: '',
      };

      while (true) {
        const { done, value } = await reader.read();
        if (done) break;

        buffer += decoder.decode(value, { stream: true });

        let newlineIndex;
        while ((newlineIndex = buffer.indexOf('\n')) !== -1) {
          const jsonString = buffer.slice(0, newlineIndex);
          buffer = buffer.slice(newlineIndex + 1);

          try {
            const jsonObject = JSON.parse(jsonString);
            if (jsonObject.text) {
              result.text += jsonObject.text;
            }
            if (jsonObject.searchEntryPoint) {
              result.searchEntryPoint = jsonObject.searchEntryPoint;
            }
            if (jsonObject.groundingSupport) {
              result.groundingSupport = [
                ...(result.groundingSupport || []),
                ...(jsonObject.groundingSupport as GroundingSupport[]),
              ];
            }
            if (jsonObject.supportChunks) {
              result.supportChunks = [
                ...(result.supportChunks || []),
                ...(jsonObject.supportChunks as SupportChunk[]),
              ];
            }
          } catch (error) {
            console.error('Error parsing JSON:', error);
          }
        }

        setResponses((prev) => ({
          ...prev,
          grounded: result,
        }));
      }

      // Process any remaining data in the buffer
      if (buffer.trim()) {
        try {
          const jsonObject = JSON.parse(buffer);
          if (jsonObject.text) {
            result.text += jsonObject.text;
          }
          if (jsonObject.searchEntryPoint) {
            result.searchEntryPoint = jsonObject.searchEntryPoint;
          }
          if (jsonObject.groundingSupport) {
            result.groundingSupport = [
              ...(result.groundingSupport || []),
              ...(jsonObject.groundingSupport as GroundingSupport[]),
            ];
          }
          if (jsonObject.supportChunks) {
            result.supportChunks = [
              ...(result.supportChunks || []),
              ...(jsonObject.supportChunks as SupportChunk[]),
            ];
          }
        } catch (error) {
          console.error('Error parsing JSON in remaining buffer:', error);
        }
      }

      return result;
    };

    const fetchUngroundedStream = async () => {
      const response = await fetch('/api/ungrounded', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          query: inputMessage,
          model: selectedModel,
        }),
      });

      if (!response.body) {
        console.error('Response body is null');
        return { text: '', groundingSupport: [], supportChunks: [] };
      }

      const reader = response.body.getReader();
      const decoder = new TextDecoder();
      let result: ResponseData = {
        text: '',
        groundingSupport: [],
        supportChunks: [],
      };

      while (true) {
        const { done, value } = await reader.read();
        if (done) break;

        const chunk = decoder.decode(value, { stream: true });
        result.text += chunk;

        setResponses((prev) => ({
          ...prev,
          ungrounded: result,
        }));
      }

      return result;
    };

    await Promise.all([fetchGroundedStream(), fetchUngroundedStream()]);

    setIsStreaming(false);
  };

  return (
    <div className="flex h-screen bg-black text-white font-sans">
      <PageSidebar
        toggleSidebar={toggleSidebar}
        sidebarOpen={sidebarOpen}
        selectedModel={selectedModel}
        setSelectedModel={setSelectedModel}
        googleGrounding={googleGrounding}
        setGoogleGrounding={setGoogleGrounding}
        retrievalThreshold={retrievalThreshold}
        setRetrievalThreshold={setRetrievalThreshold}
        vertexGrounding={vertexGrounding}
        setVertexGrounding={setVertexGrounding}
        vertexConfigId={vertexConfigId}
        setVertexConfigId={setVertexConfigId}
        // groundingOptions={groundingOptions}
        // setGroundingOptions={setGroundingOptions}
      />

      {/* Main content */}
      <div className="flex-1 flex flex-col overflow-hidden">
        <header className="bg-zinc-900 shadow-md">
          <div className="max-w-7xl mx-auto py-4 px-4 sm:px-6 lg:px-8">
            <div className="flex items-center justify-between">
              <h1
                className="text-2xl font-semibold text-transparent bg-clip-text"
                style={{
                  backgroundImage:
                    'linear-gradient(72.83deg, #4285F4 11.63%, #9b72cb 40.43%, #d96570 68.07%)',
                }}
              >
                Vertex AI Search Grounded Generation Playground
              </h1>
            </div>
          </div>
        </header>
        <div className="flex-1 flex flex-col overflow-hidden">
          <main className="flex-1 overflow-x-hidden overflow-y-auto bg-black">
            <div className="max-w-7xl mx-auto py-6 sm:px-6 lg:px-8">
              <Tabs value={activeTab} onValueChange={setActiveTab} className="w-full">
                <TabsList className="grid w-full grid-cols-3 mb-6 bg-zinc-800">
                  <TabsTrigger
                    value="chat"
                    className="data-[state=active]:bg-zinc-700 data-[state=active]:text-white text-white"
                  >
                    Chat
                  </TabsTrigger>
                  <TabsTrigger
                    value="comparison"
                    className="data-[state=active]:bg-zinc-700 data-[state=active]:text-white text-white"
                  >
                    Comparison
                  </TabsTrigger>
                  <TabsTrigger
                    value="about"
                    className="data-[state=active]:bg-zinc-700 data-[state=active]:text-white text-white"
                  >
                    About
                  </TabsTrigger>
                </TabsList>
                <TabsContent value="chat">
                  {/* Chat Interface */}
                  <ScrollArea className="h-[calc(100vh-300px)]">
                    {messages.map((message, index) => (
                      <div
                        key={index}
                        className={cn(
                          'flex mb-4',
                          message.role === 'user' ? 'justify-end' : 'justify-start',
                        )}
                      >
                        <div
                          className={cn(
                            'flex on-hover-show items-start max-w-[80%]',
                            message.role === 'user' ? 'flex-row-reverse' : 'flex-row',
                          )}
                        >
                          <div
                            className={cn(
                              'min-w-8 w-8 h-8 rounded-full flex items-center justify-center',
                              message.role === 'user'
                                ? 'bg-white ml-2'
                                : 'bg-zinc-700 mr-2',
                            )}
                          >
                            <Icon type={message.role} className="h-7 w-7 text-black" />
                          </div>
                          <Card
                            className={cn(
                              'rounded-2xl',
                              message.role === 'user'
                                ? 'bg-zinc-200 text-black'
                                : 'bg-zinc-800 text-white',
                            )}
                          >
                            <CardContent className="p-3">
                              {message.role === 'user' ? (
                                <ReactMarkdown
                                  remarkPlugins={[remarkGfm]}
                                  className="prose max-w-none text-sm text-black"
                                >
                                  {message.content}
                                </ReactMarkdown>
                              ) : (
                                <GroundedTextBlock
                                  role={message.role}
                                  content={message.content}
                                  groundingSupport={message.groundingSupport}
                                  supportChunks={message.supportChunks}
                                  searchEntryPoint={message.searchEntryPoint}
                                />
                              )}
                            </CardContent>
                          </Card>
                          {message.role === 'user' && (
                            <div className="m-2 on-hover-show-this">
                              <Button
                                className="p-2 bg-zinc-700 rounded-full"
                                onClick={() => setInputMessage(message.content)}
                              >
                                Resend
                                <Send className="h-4 w-4 ml-2" />
                              </Button>
                            </div>
                          )}
                        </div>
                      </div>
                    ))}
                    {messages.length === 0 ? (
                      <ExampleQuestionGreeting
                        greeting="Start a conversation by asking a question about grounding sources."
                        exampleQuestions={exampleQuestions}
                        onClick={sendMessage}
                      />
                    ) : (
                      ''
                    )}
                    {isStreaming && (
                      <div className="flex items-center justify-center">
                        <div className="flex items-center space-x-2 bg-zinc-800 rounded-full px-4 py-2">
                          <IconGemini className="h-5 w-5 text-white" />
                          <IconSpinner className="h-4 w-4 text-white" />
                          <span className="text-sm text-white">Thinking...</span>
                        </div>
                      </div>
                    )}

                    <div ref={messagesEndRef} />
                  </ScrollArea>
                  <div className="mt-4">
                    <form onSubmit={handleMessageFormSubmit} className="flex space-x-2">
                      <Input
                        type="text"
                        placeholder="Type your message..."
                        value={inputMessage}
                        onChange={(e) => setInputMessage(e.target.value)}
                        className="flex-1 h-10 bg-zinc-800 text-white border-zinc-500 focus:border-blue-500 focus:ring-2 focus:ring-blue-500"
                      />
                      <Button
                        type="submit"
                        disabled={isStreaming || !inputMessage.trim()}
                        className={` h-10 bg-blue-600 text-white hover:bg-blue-700 ${
                          isStreaming || !inputMessage.trim()
                            ? 'opacity-50 cursor-not-allowed'
                            : ''
                        }`}
                      >
                        <Send className="h-4 w-4" />
                      </Button>
                      <Button
                        type="button"
                        onClick={clearChat}
                        className="h-10 bg-red-600 text-white hover:bg-red-700"
                      >
                        <Trash2 className="h-4 w-4" />
                      </Button>
                    </form>
                  </div>
                </TabsContent>
                <TabsContent value="comparison">
                  {/* Comparison Interface */}
                  <div className="space-y-6">
                    {/* Greeting and Example Queries */}
                    <ExampleQuestionGreeting
                      greeting="SxS comparison of Grounded vs Ungrounded Answers for a search"
                      exampleQuestions={exampleQuestions}
                      onClick={setInputMessage}
                    />
                    {/* Search bar */}
                    <form onSubmit={handleSearch} className="mb-6">
                      <div className="flex space-x-2">
                        <Input
                          type="text"
                          placeholder="Enter your query..."
                          value={inputMessage}
                          onChange={(e) => setInputMessage(e.target.value)}
                          className="flex-1 h-10 bg-zinc-800 text-white border-zinc-500 focus:border-blue-500 focus:ring-2 focus:ring-blue-500"
                        />
                        <Button
                          type="submit"
                          disabled={isStreaming || !inputMessage.trim()}
                          className={`h-10 bg-blue-600 text-white hover:bg-blue-700 ${
                            isStreaming || !inputMessage.trim()
                              ? 'opacity-50 cursor-not-allowed'
                              : ''
                          }`}
                        >
                          {isStreaming ? (
                            <div className="flex items-center">
                              <IconSpinner className="mr-2" />
                              Searching...
                            </div>
                          ) : (
                            <>
                              <Search className="h-4 w-4 mr-2" />
                              Search
                            </>
                          )}
                        </Button>
                      </div>
                    </form>

                    {/* Response containers */}
                    {showResponses && (
                      <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                        <div className="bg-zinc-800 shadow rounded-lg p-6 h-full">
                          <h2 className="text-lg font-semibold mb-4 text-white">
                            Grounded Response
                          </h2>
                          <div className="prose prose-invert max-w-none overflow-auto min-h-[60vh]">
                            {responses.grounded.text ? (
                              <GroundedTextBlock
                                role="model"
                                content={responses.grounded.text}
                                groundingSupport={responses.grounded.groundingSupport}
                                supportChunks={responses.grounded.supportChunks}
                                searchEntryPoint={responses.grounded.searchEntryPoint}
                              />
                            ) : (
                              <div className="flex items-center justify-center space-x-2">
                                <IconGemini className="h-5 w-5 text-white" />
                                <IconSpinner className="h-4 w-4 text-white" />
                                <span className="text-sm text-white">Thinking...</span>
                              </div>
                            )}
                          </div>
                        </div>
                        <div className="bg-zinc-800 shadow rounded-lg p-6 h-full">
                          <h2 className="text-lg font-semibold mb-4 text-white">
                            Ungrounded Response
                          </h2>
                          <div className="prose prose-invert max-w-none overflow-auto min-h-[60vh]">
                            {responses.ungrounded.text ? (
                              <ReactMarkdown remarkPlugins={[remarkGfm]}>
                                {responses.ungrounded.text}
                              </ReactMarkdown>
                            ) : (
                              <div className="flex items-center justify-center space-x-2">
                                <IconGemini className="h-5 w-5 text-white" />
                                <IconSpinner className="h-4 w-4 text-white" />
                                <span className="text-sm text-white">Thinking...</span>
                              </div>
                            )}
                          </div>
                        </div>
                      </div>
                    )}
                  </div>
                </TabsContent>
                <TabsContent value="about">
                  {/* About Interface */}
                  <div className="space-y-6">
                    <div className="text-left mb-8">
                      <p className="text-xl text-gray-300 mb-6">
                        API reference & Infromation about selected grounding sources.
                        <a
                          href="https://cloud.google.com/generative-ai-app-builder/docs/grounded-gen"
                          target="_blank"
                          className="text-md text-blue-500 italic ml-2"
                        >
                          learn more
                        </a>
                      </p>
                    </div>
                  </div>
                  <div className="bg-zinc-800 shadow rounded-lg p-6 h-full">
                    <div className="prose prose-invert max-w-none overflow-auto min-h-[60vh]">
                      <AboutPageContent
                        selectedModel={selectedModel}
                        // groundingOptions={groundingOptions}
                        googleGrounding={googleGrounding}
                        vertexGrounding={vertexGrounding}
                        vertexConfigId={vertexConfigId}
                        temperature={temperature}
                        activeAboutTab={activeAboutTab}
                        setActiveAboutTab={setActiveAboutTab}
                      />
                    </div>
                  </div>
                </TabsContent>
              </Tabs>
            </div>
          </main>
        </div>
      </div>
    </div>
  );
}

export type { GroundingSupport, SupportChunk };
