import React, { useEffect, useState } from "react";
import socket from "../Socket";

export const MessageParser = ({ children, actions, state }) => {
  const [response, setResponse] = useState(null);
  useEffect(() => {
    console.log("backend response");
    socket.on("chat", (data) => {
      console.log("data", data);
      if (data[0] !== "Done") {
        if (data[0] !== "Generating...") {
          actions.handleResponse(data);
        } else {
          actions.handleResponse(data[0]);
        }
      }
    });
  }, []);
  const parse = (message) => {
    if (state.sendQuery) {
      let query = "";
      if (state.setParticipant) {
        query = `I want to schedule a meeting on ${state.date} at ${state.time} with ${message}.`;
      } else {
        query = message;
      }
      console.log("query", query);
      socket.emit("chat", { query: query, chat_history: state.messages });
    }
  };

  return (
    <div>
      {React.Children.map(children, (child) => {
        return React.cloneElement(child, {
          parse: parse,
          actions,
        });
      })}
    </div>
  );
};
