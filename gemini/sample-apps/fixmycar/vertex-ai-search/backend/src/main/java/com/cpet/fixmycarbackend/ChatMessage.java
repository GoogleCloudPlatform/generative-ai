package com.cpet.fixmycarbackend;

// This object is used for both the request and response for POST /chat
// (Represents a single call and response. Currently, multi turn is not supported on the backend,
// although we pass the chat history as context from the frontend.)
public class ChatMessage {
  private String prompt;
  private String response;

  public String getPrompt() {
    return prompt;
  }

  public void setPrompt(String prompt) {
    this.prompt = prompt;
  }

  public String getResponse() {
    return response;
  }

  public void setResponse(String response) {
    this.response = response;
  }
}
