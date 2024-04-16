import React from "react"; // Import the React library
import Chatbot from "react-chatbot-kit"; // Import the Chatbot component from the react-chatbot-kit library
import "./App.css"; // Import the CSS file for styling the chatbot
import "./main.css"; // Import the main CSS file for styling the application

import CloseIcon from "@mui/icons-material/Close"; // Import the CloseIcon component from the @mui/icons-material library
import MinimizeIcon from "@mui/icons-material/Minimize"; // Import the MinimizeIcon component from the @mui/icons-material library
import { Dialog, IconButton } from "@mui/material"; // Import the Dialog and IconButton components from the @mui/material library
import { ActionProvider } from "./ActionProvider"; // Import the ActionProvider component from the ActionProvider.js file
import { MessageParser } from "./MessageParser"; // Import the MessageParser component from the MessageParser.js file
import config from "./config"; // Import the config object from the config.js file

function Bot({ open, setOpen }) {
  // Define a state variable to track whether the chatbot is minimized
  let minimize = false;

  // Define a function to change the minimize state
  const changeMinimize = (value) => {
    minimize = value;
  };

  // Define a function to handle closing the chatbot
  const handleClose = () => {
    console.log("handleClose");
    // Set the minimize state to false
    changeMinimize(false);
    // Remove the chat history from local storage
    localStorage.removeItem("chat_history");
    // Set the open state to false to close the chatbot
    setOpen(false);
  };

  // Define a function to handle minimizing the chatbot
  const handleMinimize = () => {
    console.log("handleMinimize");
    // Set the minimize state to true
    changeMinimize(true);
    // Set the open state to false to close the chatbot
    setOpen(false);
  };

  // Define a function to get the chatbot configuration
  const getConfig = () => {
    // Create a new config object based on the existing config object
    const newConfig = {
      ...config,
      // Override the customComponents property to add custom header component
      customComponents: {
        header: () => (
          <div
            style={{
              borderTopRightRadius: "5px",
              borderTopRightRadius: "5px",
              backgroundColor: "#efefef",
              fontFamily: "Arial",
              display: "flex",
              alignItems: "center",
              fontSize: "0.85rem",
              color: "#514f4f",
              padding: "12.5px",
              fontWeight: "bold",
            }}
          >
            GenAI Assistant
            {/* Add a minimize button to the header */}
            <IconButton
              sx={{ marginLeft: "auto" }}
              size="small"
              onClick={handleMinimize}
            >
              <MinimizeIcon fontSize="inherit" />
            </IconButton>
            {/* Add a close button to the header */}
            <IconButton size="small" onClick={handleClose}>
              <CloseIcon fontSize="inherit" />
            </IconButton>
          </div>
        ),
      },
    };
    // Return the new config object
    return newConfig;
  };

  // Define a function to save the chatbot messages to local storage
  const saveMessages = (messages, HTMLString) => {
    console.log("saveMessages", minimize);
    // If the chatbot is minimized, save the messages to local storage
    if (minimize) {
      localStorage.setItem("chat_history", JSON.stringify(messages));
    }
  };

  // Define a function to load the chatbot messages from local storage
  const loadMessages = () => {
    // Get the messages from local storage
    const messages = JSON.parse(localStorage.getItem("chat_history"));
    // Return the messages
    return messages;
  };

  return (
    <Dialog
      open={open}
      onClose={handleClose}
      maxWidth="md"
      fullWidth={true}
      PaperProps={{
        style: {
          position: "fixed",
          top: "45vh",
          bottom: "-40vh",
          right: "16px", // Adjust the right property as needed
          transform: "translateY(-50%)",
          zIndex: 1100,
          overflow: "hidden",
        },
      }}
    >
      <div className="app">
        <header className="app-header">
          {/* Render the Chatbot component with the appropriate props */}
          <Chatbot
            config={getConfig()}
            actionProvider={ActionProvider}
            messageParser={MessageParser}
            headerText="Chat"
            saveMessages={saveMessages}
            messageHistory={loadMessages()}
          />
        </header>
      </div>
    </Dialog>
  );
}
export default Bot;
