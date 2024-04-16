import React from "react";

export const ActionProvider = ({
  createChatBotMessage,
  state,
  setState,
  children,
}) => {
  // Handle the "Hello" button click

  const updateBotMessage = (botMessage) => {
    // Update the state with the new bot message and set the setTime flag to false
    setState((prev) => {
      const updatedMessages = [...prev.messages];

      if (updatedMessages.length > 0) {
        updatedMessages[updatedMessages.length - 1] = botMessage;
      }

      return {
        ...prev,
        messages: updatedMessages,
        setTime: false,
      };
    });
  };
  const handleHello = () => {
    // Create a bot message with the text "Hello. Nice to meet you."
    const botMessage = createChatBotMessage("Hello. Nice to meet you.");
    // Update the state with the new bot message
    setState((prev) => ({
      ...prev,
      messages: [...prev.messages, botMessage],
    }));
  };

  // Handle the "Participant" button click
  const handleParticipant = (message) => {
    // Log the message to the console
    console.log("message", message);
    // Create a bot message with the text "Thank you. I have set up the meeting ." and a MeetCard widget
    const botMessage = createChatBotMessage(
      "Thank you. I have set up the meeting .",
      {
        widget: "MeetCard",
        payload: message.event,
      },
    );
    updateBotMessage(botMessage);
  };

  // Handle the "Message" button click
  const handleMessage = (message, intent) => {
    // Log the message to the console
    console.log("message", message);
    // Create a bot message with the text from the intent and a MarkdownWidget widget
    const botMessage = createChatBotMessage(intent, {
      widget: "MarkdownWidget",
      payload: message,
    });
    updateBotMessage(botMessage);
  };

  // Handle the "Response" button click
  const handleResponse = (responses) => {
    // Check if the responses are the placeholder message "Generating..."
    const PLACEHOLDERMESSAGE = "Generating...";
    if (responses === PLACEHOLDERMESSAGE) {
      // Log that a loader widget is being created
      console.log("creating loader widget");
      // Create a bot message with the placeholder message and a Loader widget
      const botMessage = createChatBotMessage(PLACEHOLDERMESSAGE, {
        widget: "Loader",
      });
      // Update the state with the new bot message and set the setTime flag to false
      setState((prev) => ({
        ...prev,
        messages: [...prev.messages, botMessage],
        setTime: false,
      }));
      // Log the state
      console.log(state);
    }
    // Check if the responses are not the placeholder message
    if (responses !== PLACEHOLDERMESSAGE) {
      // Iterate over the responses
      responses.forEach((response) => {
        // Check if the response intent is "calendar"
        if (response.intent === "calendar") {
          // Check if the response status is "invalid"
          if (response.status === "invalid") {
            // Handle the schedule event
            handleSchedule(response.data);
          } else {
            // Handle the participant event
            handleParticipant(response.data);
          }

          // Check if the response intent is "email"
        } else if (response.intent === "email") {
          // Handle the email event
          handleMail(response.data);
          // Check if the response intent is "get_calendar_events"
        } else if (response.intent === "get_calendar_events") {
          // Handle the calendar events event
          handleAppointments(response.data);
          // Check if the response intent is "Plan Graph"
        } else if (response.intent === "Plan Graph") {
          // Handle the plan graph event
          handlePlanGraph(response.data);
          // Check if the response intent is "Comparison"
        } else if (response.intent === "Comparison") {
          // Handle the comparison event
          handleComparison(response.data);
          // Otherwise, handle the message and intent
        } else {
          const message = Object.values(response.data)[0];
          const intent = response.intent;
          handleMessage(message, intent);
        }
      });
    }
  };

  // Handle the "Plan Graph" button click
  const handlePlanGraph = (data) => {
    // Create a bot message with the "Plan Graph" text and a PlanGraph widget
    const botMessage = createChatBotMessage("Plan Graph", {
      widget: "PlanGraph",
      payload: data,
    });

    updateBotMessage(botMessage);
  };

  // Handle the "Comparison" button click
  const handleComparison = (data) => {
    // Create a bot message with the "Comparison of policies" text and a Comparison widget
    const botMessage = createChatBotMessage("Comparison of policies", {
      widget: "Comparison",
      payload: data,
    });

    updateBotMessage(botMessage);
  };

  // Handle the "Appointments" button click
  const handleAppointments = (events) => {
    // Create a bot message with the "Here are your appointments." text and an AppointmentList widget
    const botMessage = createChatBotMessage("Here are your appointments.", {
      widget: "AppointmentList",
      payload: events,
    });

    updateBotMessage(botMessage);
  };
  // Handle the "Mail" button click
  const handleMail = (mailData) => {
    // Create a bot message with the "Please review the following mail." text and a ComposeMail widget
    const botMessage = createChatBotMessage(
      "Please review the following mail.",
      {
        widget: "ComposeMail",
        payload: mailData,
      },
    );
    updateBotMessage(botMessage);
  };

  // Handle the "Schedule" button click
  const handleSchedule = (eventData) => {
    // Create a bot message with the "Please review the following details" text and a ScheduleEvent widget
    const botMessage = createChatBotMessage(
      "Please review the following details",
      {
        widget: "ScheduleEvent",
        payload: eventData,
      },
    );
    updateBotMessage(botMessage);
  };

  return (
    <div>
      {React.Children.map(children, (child) => {
        return React.cloneElement(child, {
          actions: {
            handleHello,
            handleResponse,
            handleMail,
            handleParticipant,
          },
          state,
        });
      })}
    </div>
  );
};
