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

import "./logger.scss";

import { Part } from "@google/generative-ai";
import cn from "classnames";
import { ReactNode } from "react";
import { useLoggerStore } from "../../utils/store-logger";
import {
  ClientContentMessage,
  isClientContentMessage,
  isInterrupted,
  isModelTurn,
  isServerContenteMessage,
  isToolCallCancellationMessage,
  isToolCallMessage,
  isToolResponseMessage,
  isTurnComplete,
  ModelTurn,
  ServerContentMessage,
  StreamingLog,
  ToolCallCancellationMessage,
  ToolCallMessage,
  ToolResponseMessage,
} from "../../multimodal-live-types";

const formatTime = (d: Date) => d.toLocaleTimeString().slice(0, -3);

const LogEntry = ({
  log,
  MessageComponent,
}: {
  log: StreamingLog;
  MessageComponent: ({
    message,
  }: {
    message: StreamingLog["message"];
  }) => ReactNode;
}): JSX.Element => (
  <li
    className={cn(
      `plain-log`,
      `source-${log.type.slice(0, log.type.indexOf("."))}`,
      {
        receive: log.type.includes("receive"),
        send: log.type.includes("send"),
      },
    )}
  >
    <span className="timestamp">{formatTime(log.date)}</span>
    <span className="source">{log.type}</span>
    <span className="message">
      <MessageComponent message={log.message} />
    </span>
    {log.count && <span className="count">{log.count}</span>}
  </li>
);

const PlainTextMessage = ({
  message,
}: {
  message: StreamingLog["message"];
}) => <span>{message as string}</span>;

type Message = { message: StreamingLog["message"] };

const AnyMessage = ({ message }: Message) => (
  <pre>{JSON.stringify(message, null, "  ")}</pre>
);

const RenderPart = ({ part }: { part: Part }) =>
  part.text && part.text.length ? (
    <p className="part part-text">{part.text}</p>
  ) : (
    <div className="part part-inlinedata">
      <h5>Inline Data: {part.inlineData?.mimeType}</h5>
    </div>
  );

const ClientContentLog = ({ message }: Message) => {
  const { turns, turnComplete } = (message as ClientContentMessage)
    .clientContent;
  return (
    <div className="rich-log client-content user">
      <h4 className="roler-user">User</h4>
      {turns.map((turn, i) => (
        <div key={`message-turn-${i}`}>
          {turn.parts
            .filter((part) => !(part.text && part.text === "\n"))
            .map((part, j) => (
              <RenderPart part={part} key={`message-turh-${i}-part-${j}`} />
            ))}
        </div>
      ))}
      {!turnComplete ? <span>turnComplete: false</span> : ""}
    </div>
  );
};

const ToolCallLog = ({ message }: Message) => {
  const { toolCall } = message as ToolCallMessage;
  return (
    <div className={cn("rich-log tool-call")}>
      {toolCall.functionCalls.map((fc, i) => (
        <div key={fc.id} className="part part-functioncall">
          <h5>Function call: {fc.name}</h5>
          <pre>{JSON.stringify(fc, null, "  ")}</pre>
        </div>
      ))}
    </div>
  );
};

const ToolCallCancellationLog = ({ message }: Message): JSX.Element => (
  <div className={cn("rich-log tool-call-cancellation")}>
    <span>
      {" "}
      ids:{" "}
      {(message as ToolCallCancellationMessage).toolCallCancellation.ids.map(
        (id) => (
          <span className="inline-code" key={`cancel-${id}`}>
            "{id}"
          </span>
        ),
      )}
    </span>
  </div>
);

const ToolResponseLog = ({ message }: Message): JSX.Element => (
  <div className={cn("rich-log tool-response")}>
    {(message as ToolResponseMessage).toolResponse.functionResponses.map(
      (fc) => (
        <div key={`tool-response-${fc.id}`} className="part">
          <h5>Function Response: {fc.id}</h5>
          <pre>{JSON.stringify(fc.response, null, "  ")}</pre>
        </div>
      ),
    )}
  </div>
);

const ModelTurnLog = ({ message }: Message): JSX.Element => {
  const serverContent = (message as ServerContentMessage).serverContent;
  const { modelTurn } = serverContent as ModelTurn;
  const { parts } = modelTurn;

  return (
    <div className="rich-log model-turn model">
      <h4 className="role-model">Model</h4>
      {parts
        .filter((part) => !(part.text && part.text === "\n"))
        .map((part, j) => (
          <RenderPart part={part} key={`model-turn-part-${j}`} />
        ))}
    </div>
  );
};

const CustomPlainTextLog = (msg: string) => () => (
  <PlainTextMessage message={msg} />
);

export type LoggerFilterType = "conversations" | "tools" | "none";

export type LoggerProps = {
  filter: LoggerFilterType;
};

const filters: Record<LoggerFilterType, (log: StreamingLog) => boolean> = {
  tools: (log: StreamingLog) =>
    isToolCallMessage(log.message) ||
    isToolResponseMessage(log.message) ||
    isToolCallCancellationMessage(log.message),
  conversations: (log: StreamingLog) =>
    isClientContentMessage(log.message) || isServerContenteMessage(log.message),
  none: () => true,
};

const component = (log: StreamingLog) => {
  if (typeof log.message === "string") {
    return PlainTextMessage;
  }
  if (isClientContentMessage(log.message)) {
    return ClientContentLog;
  }
  if (isToolCallMessage(log.message)) {
    return ToolCallLog;
  }
  if (isToolCallCancellationMessage(log.message)) {
    return ToolCallCancellationLog;
  }
  if (isToolResponseMessage(log.message)) {
    return ToolResponseLog;
  }
  if (isServerContenteMessage(log.message)) {
    const { serverContent } = log.message;
    if (isInterrupted(serverContent)) {
      return CustomPlainTextLog("interrupted");
    }
    if (isTurnComplete(serverContent)) {
      return CustomPlainTextLog("turnComplete");
    }
    if (isModelTurn(serverContent)) {
      return ModelTurnLog;
    }
  }
  return AnyMessage;
};

export default function Logger({ filter = "none" }: LoggerProps) {
  const { logs } = useLoggerStore();

  const filterFn = filters[filter];

  return (
    <div className="logger">
      <ul className="logger-list">
        {logs.filter(filterFn).map((log, key) => {
          return (
            <LogEntry MessageComponent={component(log)} log={log} key={key} />
          );
        })}
      </ul>
    </div>
  );
}
