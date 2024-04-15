import { createChatBotMessage } from "react-chatbot-kit"; // Import the function to create chatbot messages
import AppointmentList from "../AppointmentList"; // Import the AppointmentList component
import Comparison from "../Comparison"; // Import the Comparison component
import Email from "../ComposeMailChatbot"; // Import the Email component
import Loader from "../Loader"; // Import the Loader component
import MarkdownWidget from "../MarkdownWidget"; // Import the MarkdownWidget component
import MeetCard from "../MeetCard"; // Import the MeetCard component
import PlanGraph from "../PlanGraph"; // Import the PlanGraph component
import ScheduleEventChatbot from "../ScheduleEventChatbot"; // Import the ScheduleEventChatbot component

const botName = "Agent Assist"; // Define the bot's name

const config = {
  botName: botName, // Set the bot's name
  initialMessages: [
    createChatBotMessage(
      `Hi I'm a Gen-Ai powered bot tailored to assist you with your tasks and make your life easy. I am trained to help you with managing calendar events, drafting sales pitches, composing emails, fetching your appointments, searching in the docs and the database and much more. Please let me know how can I help you today?`,
    ), // Set the initial message from the bot
  ],
  state: {
    setTime: false, // State variable to track if the time has been set
    setDate: false, // State variable to track if the date has been set
    setParticipant: false, // State variable to track if the participant has been set
    chatHistory: [], // State variable to store the chat history
    sendQuery: true, // State variable to track if the query should be sent
    date: null, // State variable to store the date
    time: null, // State variable to store the time
  },
  widgets: [
    {
      widgetName: "MeetCard", // Name of the widget
      widgetFunc: (props) => <MeetCard {...props} />, // Function to render the widget
      props: {}, // Props to pass to the widget
    },

    {
      widgetName: "ComposeMail", // Name of the widget
      widgetFunc: (props) => <Email {...props} />, // Function to render the widget
    },

    {
      widgetName: "ScheduleEvent", // Name of the widget
      widgetFunc: (props) => <ScheduleEventChatbot {...props} />, // Function to render the widget
    },
    {
      widgetName: "Loader", // Name of the widget
      widgetFunc: (props) => <Loader {...props} />, // Function to render the widget
    },
    {
      widgetName: "AppointmentList", // Name of the widget
      widgetFunc: (props) => <AppointmentList {...props} />, // Function to render the widget
    },
    {
      widgetName: "MarkdownWidget", // Name of the widget
      widgetFunc: (props) => <MarkdownWidget {...props} />, // Function to render the widget
    },
    {
      widgetName: "PlanGraph", // Name of the widget
      widgetFunc: (props) => <PlanGraph {...props} />, // Function to render the widget
    },
    {
      widgetName: "Comparison", // Name of the widget
      widgetFunc: (props) => <Comparison {...props} />, // Function to render the widget
    },
  ],
};

export default config; // Export the config object
