import { FunctionCallDefinition } from "./gemini-api";

/**
 * Show Modal Dialog Tool
 * Displays a large modal dialog with a custom message
 */
export class ShowModalDialogTool extends FunctionCallDefinition {
  constructor(onShowModal) {
    super(
      "show_modal",
      "Displays a large modal dialog with a message to the user",
      {
        type: "object",
        properties: {
          message: {
            type: "string",
            description: "The message to display in the modal",
          },
          title: {
            type: "string",
            description: "Optional title for the modal",
          },
        },
      },
      ["message"]
    );
    this.onShowModal = onShowModal;
  }

  functionToCall(parameters) {
    const message = parameters.message || "Alert!";
    const title = parameters.title;

    if (this.onShowModal) {
      this.onShowModal(message, title);
    }

    console.log(` Modal requested: ${title}: ${message}`);
  }
}

/**
 * Add CSS Style Tool
 * Injects CSS styles into the current page with !important flag
 */
export class AddCSSStyleTool extends FunctionCallDefinition {
  constructor() {
    super(
      "add_css_style",
      "Injects CSS styles into the current page with !important flag",
      {
        type: "object",
        properties: {
          selector: {
            type: "string",
            description:
              "CSS selector to target elements (e.g., 'body', '.class', '#id')",
          },
          property: {
            type: "string",
            description:
              "CSS property to set (e.g., 'background-color', 'font-size', 'display')",
          },
          value: {
            type: "string",
            description:
              "Value for the CSS property (e.g., 'red', '20px', 'none')",
          },
          styleId: {
            type: "string",
            description:
              "Optional ID for the style element (for updating existing styles)",
          },
        },
      },
      ["selector", "property", "value"]
    );
  }

  functionToCall(parameters) {
    const { selector, property, value, styleId } = parameters;

    // Create or find the style element
    let styleElement;
    if (styleId) {
      styleElement = document.getElementById(styleId);
      if (!styleElement) {
        styleElement = document.createElement("style");
        styleElement.id = styleId;
        document.head.appendChild(styleElement);
      }
    } else {
      styleElement = document.createElement("style");
      document.head.appendChild(styleElement);
    }

    // Create the CSS rule with !important
    const cssRule = `${selector} { ${property}: ${value} !important; }`;

    // Add the CSS rule to the style element
    if (styleId) {
      // If using an ID, replace the content
      styleElement.textContent = cssRule;
    } else {
      // Otherwise append to any existing content
      styleElement.textContent += cssRule;
    }

    console.log(`🎨 CSS style injected: ${cssRule}`);
    console.log(
      `   Applied to ${document.querySelectorAll(selector).length} element(s)`
    );
  }
}

/**
 * Connect To Human Tool
 * Simulates connecting the user to a human agent
 */
export class ConnectToHumanTool extends FunctionCallDefinition {
  constructor(onConnect) {
    super(
      "connect_to_human",
      "Connects the user to a human customer service agent",
      {
        type: "object",
        properties: {
          reason: {
            type: "string",
            description: "The reason for connecting to a human",
          },
        },
      },
      ["reason"]
    );
    this.onConnect = onConnect;
  }

  functionToCall(parameters) {
    const reason = parameters.reason || "No reason provided";
    if (this.onConnect) {
      this.onConnect(reason);
    }
    console.log(`📞 Connecting to human: ${reason}`);
  }
}

/**
 * Process Refund Tool
 * Simulates processing a refund for a customer
 */
export class ProcessRefundTool extends FunctionCallDefinition {
  constructor(onRefund) {
    super(
      "process_refund",
      "Processes a refund for a transaction",
      {
        type: "object",
        properties: {
          transactionId: {
            type: "string",
            description: "The ID of the transaction to refund",
          },
          reason: {
            type: "string",
            description: "The reason for the refund",
          },
        },
      },
      ["transactionId"]
    );
    this.onRefund = onRefund;
  }

  functionToCall(parameters) {
    if (this.onRefund) {
      this.onRefund(parameters);
    }
    console.log(`💸 Processing refund: ${JSON.stringify(parameters)}`);
  }
}

/**
 * End Conversation Tool
 * Ends the current customer support session
 */
export class EndConversationTool extends FunctionCallDefinition {
  constructor(onEnd) {
    super(
      "end_conversation",
      "Ends the current customer support conversation",
      {
        type: "object",
        properties: {
          summary: {
            type: "string",
            description: "A brief summary of the conversation",
          },
        },
      },
      []
    );
    this.onEnd = onEnd;
  }

  functionToCall(parameters) {
    if (this.onEnd) {
      this.onEnd(parameters.summary);
    }
    console.log(`👋 Ending conversation. Summary: ${parameters.summary}`);
  }
}

/**
 * Point To Location Tool
 * Points to a specific location on the user's screen/video feed
 */
export class PointToLocationTool extends FunctionCallDefinition {
  constructor(onPoint) {
    super(
      "point_to_location",
      "Points to a specific location on the user's screen or video feed to highlight something.",
      {
        type: "object",
        properties: {
          x: {
            type: "number",
            description: "The x coordinate (0-1000) from the left edge",
          },
          y: {
            type: "number",
            description: "The y coordinate (0-1000) from the top edge",
          },
          label: {
            type: "string",
            description: "Optional label to display at the location",
          },
        },
      },
      ["x", "y"]
    );
    this.onPoint = onPoint;
  }

  // ...existing code...
  functionToCall(parameters) {
    if (this.onEnd) {
      this.onEnd(parameters.summary);
    }
    console.log(`👋 Ending conversation. Summary: ${parameters.summary}`);
  }
}
