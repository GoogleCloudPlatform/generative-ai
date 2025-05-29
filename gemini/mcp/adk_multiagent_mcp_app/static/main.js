/**
 * Copyright 2025 Google LLC
 * Licensed under the Apache License, Version 2.0 (the "License");
 * you may not use this file except in compliance with the License.
 * You may obtain a copy of the License at
 *
 * http://www.apache.org/licenses/LICENSE-2.0
 **/

/**
 * @file main.js
 * Entry point for the application. Waits for the DOM to be ready,
 * then initializes all modules (Tabs, User Guide, WebSocket App).
 */

// Import initialization functions from other modules
import { initTabs } from "./tabs.js";
import { initUserGuide } from "./userGuide.js";
import { initWebSocketApp } from "./websocketApp.js";

// Wait for the DOM to be fully loaded before running initialization logic
document.addEventListener("DOMContentLoaded", () => {
  console.log(
    "DOM fully loaded and parsed. Initializing application modules...",
  );

  // Initialize Tab switching
  try {
    initTabs();
  } catch (e) {
    console.error("Error initializing tabs module:", e);
  }

  // Initialize User Guide loading
  try {
    initUserGuide();
  } catch (e) {
    console.error("Error initializing user guide module:", e);
  }

  // Initialize the core WebSocket application
  try {
    initWebSocketApp();
  } catch (e) {
    console.error("Error initializing WebSocket app module:", e);
  }

  console.log("All application modules initialized.");
});
