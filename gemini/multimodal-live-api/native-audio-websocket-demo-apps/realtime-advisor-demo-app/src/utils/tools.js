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
