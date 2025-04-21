/**
 * Copyright 2025 Google LLC
 * Licensed under the Apache License, Version 2.0 (the "License");
 * you may not use this file except in compliance with the License.
 * You may obtain a copy of the License at
 *
 * http://www.apache.org/licenses/LICENSE-2.0
 **/

/**
 * @module tabs
 * Handles the tab switching functionality for the UI.
 */

/**
 * Initializes the tab switching behavior.
 * Looks for elements with class 'tab-button' and 'tab-panel'.
 * Buttons should have a 'data-tab' attribute matching the ID of the panel they control.
 */
export function initTabs() {
  const tabButtons = document.querySelectorAll(".tab-button");
  const tabPanels = document.querySelectorAll(".tab-panel");

  if (!tabButtons.length || !tabPanels.length) {
    console.warn(
      "Tab elements (buttons or panels) not found. Skipping tab initialization.",
    );
    return;
  }

  tabButtons.forEach((button) => {
    button.addEventListener("click", () => {
      const targetPanelId = button.getAttribute("data-tab");
      if (!targetPanelId) {
        console.error("Tab button is missing 'data-tab' attribute:", button);
        return;
      }
      const targetPanel = document.getElementById(targetPanelId);

      // Deactivate all buttons and panels
      tabButtons.forEach((btn) => btn.classList.remove("active"));
      tabPanels.forEach((panel) => panel.classList.remove("active"));

      // Activate the clicked button and corresponding panel
      button.classList.add("active");
      if (targetPanel) {
        targetPanel.classList.add("active");
        console.log(`Switched to tab: ${targetPanelId}`);
      } else {
        console.error(`Target panel with ID '${targetPanelId}' not found.`);
      }
    });
  });

  // Set the initial active tab (optional, based on HTML having 'active' class)
  const initialActiveButton = document.querySelector(".tab-button.active");
  if (initialActiveButton) {
    const initialPanelId = initialActiveButton.getAttribute("data-tab");
    const initialPanel = document.getElementById(initialPanelId);
    if (initialPanel) initialPanel.classList.add("active");
    else console.warn(`Initial active panel '${initialPanelId}' not found.`);
  } else if (tabButtons.length > 0) {
    // Fallback: activate the first tab if none are marked active
    tabButtons[0].click();
    console.log("No initial active tab set, activating the first one.");
  }

  console.log("Tab switching logic initialized.");
}
