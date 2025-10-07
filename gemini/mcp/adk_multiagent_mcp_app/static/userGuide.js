/**
 * Copyright 2025 Google LLC
 * Licensed under the Apache License, Version 2.0 (the "License");
 * you may not use this file except in compliance with the License.
 * You may obtain a copy of the License at
 *
 * http://www.apache.org/licenses/LICENSE-2.0
 **/

/* global marked */ // Inform linting tools that 'marked' is a global variable

/**
 * @module userGuide
 * Handles fetching and rendering the user guide from a Markdown file.
 * Requires the 'marked' library to be loaded globally.
 */

const USER_GUIDE_CONTAINER_ID = "user-guide-markdown-content";
const MARKDOWN_FILE_PATH = "user_guide.md"; // <<<--- MAKE SURE THIS FILE EXISTS!

/**
 * Fetches the Markdown file and renders it into the designated container.
 * @param {HTMLElement} contentDiv - The container element to render into.
 */
function loadAndRenderMarkdown(contentDiv) {
  if (typeof marked === "undefined") {
    console.error("Marked library not loaded. Cannot render markdown.");
    contentDiv.innerHTML =
      "<p class='error-text'>Error: Markdown library (marked.js) not available. Make sure it's linked in the HTML.</p>";
    return;
  }

  contentDiv.innerHTML = "<p><i>Loading guide content...</i></p>";

  fetch(MARKDOWN_FILE_PATH)
    .then((response) => {
      if (!response.ok) {
        throw new Error(
          `HTTP error ${response.status} - Could not fetch '${MARKDOWN_FILE_PATH}'. Make sure the file exists and the page is served via HTTP(S).`,
        );
      }
      return response.text();
    })
    .then((markdownText) => {
      try {
        // Use marked.parse() which is standard for v4+
        contentDiv.innerHTML = marked.parse(markdownText);
        console.log(
          "User guide markdown loaded and rendered from file:",
          MARKDOWN_FILE_PATH,
        );
      } catch (parseError) {
        console.error("Error parsing Markdown:", parseError);
        // Sanitize raw text before displaying in HTML
        const sanitizedText = markdownText
          .replace(/</g, "&lt;")
          .replace(/>/g, "&gt;");
        contentDiv.innerHTML = `<p class='error-text'>Error rendering guide content.</p><p>Raw content:</p><pre>${sanitizedText}</pre>`;
        throw parseError; // Rethrow to be caught by the outer catch
      }
    })
    .catch((error) => {
      console.error("Error loading or rendering user guide:", error);
      contentDiv.innerHTML = `<p class='error-text'>Failed to load user guide: ${error.message}.</p>`;
    });
}

/**
 * Initializes the user guide loading process.
 * Finds the container element and starts the fetch/render process.
 */
export function initUserGuide() {
  const userGuideContentDiv = document.getElementById(USER_GUIDE_CONTAINER_ID);

  if (!userGuideContentDiv) {
    console.error(
      `User guide container div with ID '${USER_GUIDE_CONTAINER_ID}' not found. Cannot load guide.`,
    );
    return;
  }

  loadAndRenderMarkdown(userGuideContentDiv);
  console.log("User guide module initialized.");
}
