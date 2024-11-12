/**
 * Copyright 2024 Google LLC
 *
 * Licensed under the Apache License, Version 2.0 (the "License");
 * you may not use this file except in compliance with the License.
 * You may obtain a copy of the License at
 *
 *     https://www.apache.org/licenses/LICENSE-2.0
 *
 * Unless required by applicable law or agreed to in writing, software
 * distributed under the License is distributed on an "AS IS" BASIS,
 * WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
 * See the License for the specific language governing permissions and
 * limitations under the License.
 */

const location = "us";
const datasetId = "genai_demo";
const connectionId = "genai-connection";
const modelId = "genai-model";
const tableName = "genai-data";
const modelName = "gemini-pro";

function setup() {
  projectId = setProjectId();
  if (projectId == null) {
    SpreadsheetApp.getUi().alert(
      "A valid project ID must be provided to set up the project.",
    );
    return;
  }

  dataset = createDataset(projectId);
  if (!dataset) {
    return;
  }

  table = createTable(projectId);
  if (!table) {
    return;
  }

  endpoint = createEndpoint(projectId);
  if (endpoint) {
    SpreadsheetApp.getActiveSpreadsheet().toast(
      "Setup completed successfully.",
    );
  }
}

function createDataset(projectId) {
  var query =
    `SELECT * FROM \`${projectId}\`.INFORMATION_SCHEMA.SCHEMATA ` +
    `WHERE schema_name = '${datasetId}'`;
  response = runQuery(query);

  if (response.totalRows == 1) {
    return response.queryId;
  }
  query =
    `CREATE SCHEMA \`${projectId}.${datasetId}\`\n` +
    `  OPTIONS ( location = '${location}' );`;
  try {
    return runQuery(query).queryId;
  } catch (error) {
    console.log(error.details.message);
    SpreadsheetApp.getUi().alert(error);
    return null;
  }
}

/**
 * Create BigQuery table if it doesn't exist already
 */
function createTable(projectId) {
  var query =
    `SELECT * FROM \`${projectId}.${datasetId}.INFORMATION_SCHEMA.TABLES\` ` +
    `WHERE table_name = '${tableName}'`;
  response = runQuery(query);

  if (response.totalRows == 1) {
    return response.queryId;
  }
  query =
    `CREATE TABLE \`${projectId}.${datasetId}.${tableName}\` ` +
    "(prompt STRING, response STRING);";
  try {
    return runQuery(query).queryId;
  } catch (error) {
    console.log(error.details.message);
    SpreadsheetApp.getUi().alert(error);
    return null;
  }
}

function createEndpoint(projectId) {
  try {
    model = BigQuery.Models.get(projectId, datasetId, modelId);
    return model;
  } catch {
    const query =
      `CREATE MODEL \`${projectId}.${datasetId}.${modelId}\`\n` +
      `REMOTE WITH CONNECTION \`${projectId}.${location}.${connectionId}\`\n` +
      `OPTIONS(ENDPOINT = "${modelName}")`;
    try {
      return runQuery(query).queryId;
    } catch (error) {
      console.log(error.details.message);
      SpreadsheetApp.getUi().alert(error);
      return null;
    }
  }
}

function query() {
  projectId = getProjectId();
  if (projectId == null) {
    SpreadsheetApp.getUi().alert(
      "A Google Cloud project must be selected using the Setup menu item.",
    );
  }
  const numColumns = SpreadsheetApp.getActiveRange().getNumColumns();
  if (numColumns != 1) {
    SpreadsheetApp.getUi().alert(
      "Exactly one column of prompts must be selected.",
    );
    return null;
  }

  // Populate temporary table in BigQuery with selected data from sheet
  const prompts = sanitizePrompts(SpreadsheetApp.getActiveRange().getValues());
  populateTable(prompts);

  const query =
    `SELECT * FROM ML.GENERATE_TEXT( MODEL \`${datasetId}.${modelId}\`, ` +
    `(SELECT * FROM \`${projectId}.${datasetId}.${tableName}\`), ` +
    `STRUCT(${getMaxOutputTokens()} AS max_output_tokens, ${getTemperature()} AS temperature));`;
  console.log(`Query: ${query}`);

  try {
    response = runQuery(query);
  } catch (error) {
    console.log(error.details.message);
    SpreadsheetApp.getUi().alert(error);
    return null;
  }

  const responseMap = {};
  invalidResponses = false;
  for (const row of response.rows) {
    returnedPrompt = row.f[2].v;
    console.log(`Prompt: ${returnedPrompt}`);

    jsonString = row.f[0].v;
    console.log(jsonString);
    const jsonData = JSON.parse(jsonString);
    console.log(jsonData);
    if (jsonData.candidates) {
      content = jsonData.candidates[0].content;
    }

    // Is it missing content, e.g. due to a finish reason of 4 (RECITATION)?
    var response = "";
    if (!jsonData.candidates || !content) {
      invalidResponses = true;
      SpreadsheetApp.getUi().alert(row);
    } else {
      response = jsonData.candidates[0].content.parts[0].text;
    }
    console.log(`Response: ${response}`);
    responseMap[returnedPrompt] = response;
  }

  if (invalidResponses) {
    SpreadsheetApp.getActiveSpreadsheet().toast(
      "Some prompts did not return a response. Check prompts and safety settings.",
    );
  }

  // Responses come back in any order.
  // Put these in the same order as the selected cells.
  responses = [];
  for (const prompt of prompts) {
    responses.push(responseMap[prompt]);
  }

  writeResponses(responses);
}

function sanitizePrompts(prompts) {
  // Sanitize each prompt in the array
  return prompts.map((row) =>
    row.map((prompt) => {
      if (typeof prompt !== "string") return prompt;

      // Keep only letters, numbers, and whitespace
      return prompt.replace(/[^a-zA-Z0-9\s]/g, "");
    }),
  );
}

/**
 * Given a set of responses, write them one cell to the right of the selected prompts.
 */
function writeResponses(responses) {
  const sheet = SpreadsheetApp.getActiveSheet();
  const activeRange = sheet.getActiveRange();

  // Get information about the active range
  const startRow = activeRange.getRow();
  const startColumn = activeRange.getColumn() + 1;
  const numRows = activeRange.getNumRows();
  const numColumns = activeRange.getNumColumns();

  if (responses.length !== numRows) {
    SpreadsheetApp.getUi().alert(
      "Number of columns selected does not match number of responses returned.",
    );
  }

  // Calculate the new range and write the values
  const newRange = sheet.getRange(startRow, startColumn, numRows, numColumns);
  newRange.setValues(responses.map((response) => [response]));
}

function getProjectId(name = "project ID", defaultValue = null) {
  return (
    PropertiesService.getUserProperties().getProperty(name) || defaultValue
  );
}

function setProjectId(name = "project ID") {
  newValue = setParameter(name, getProjectId());
  if (newValue != null) {
    PropertiesService.getUserProperties().setProperty(name, newValue);
  }
  return newValue;
}

function getTemperature(name = "temperature", defaultValue = 0) {
  return Number(
    PropertiesService.getUserProperties().getProperty(name) || defaultValue,
  );
}

function setTemperature(name = "temperature", min = 0, max = 1) {
  newValue = setParameter(name, getTemperature(), min, max);
  if (newValue != null) {
    PropertiesService.getUserProperties().setProperty(name, newValue);
  }
  return newValue;
}

function getMaxOutputTokens(name = "max output tokens", defaultValue = 128) {
  return Number(
    PropertiesService.getUserProperties().getProperty(name) || defaultValue,
  );
}

function setMaxOutputTokens(name = "max output tokens", min = 1, max = 8192) {
  newValue = setParameter(name, getMaxOutputTokens(), min, max);
  if (newValue != null) {
    PropertiesService.getUserProperties().setProperty(name, newValue);
  }
  return newValue;
}

function setParameter(name, value = null, min = null, max = null) {
  const ui = SpreadsheetApp.getUi();
  const isNumeric = min != null && max != null;

  let promptText = `Enter ${name}:`;
  if (isNumeric) {
    promptText = `Enter ${name} (between ${min} and ${max}):`;
  }

  let prompt = null;
  if (value != null) {
    prompt = ui.prompt(
      promptText,
      `Current value is ${value}.`,
      ui.ButtonSet.OK_CANCEL,
    );
  } else {
    prompt = ui.prompt(promptText, ui.ButtonSet.OK_CANCEL);
  }

  if (prompt.getSelectedButton() == ui.Button.OK) {
    const inputText = prompt.getResponseText().trim();
    const inputValue = isNumeric ? Number(inputText) : inputText;

    if (
      inputValue != null &&
      (!isNumeric || (inputValue >= min && inputValue <= max))
    ) {
      console.log(`User updated ${name} to ${inputValue}.`);
      return inputValue;
    } else {
      ui.alert("Please enter a valid input.");
      return setParameter(name, value, min, max);
    }
  } else {
    console.log("User canceled the dialog.");
  }

  return null; // Return null if cancelled or input is invalid after retry
}

/**
 * Runs a BigQuery query and logs the results in a spreadsheet.
 */
function runQuery(query) {
  const request = {
    query: query,
    useLegacySql: false,
  };

  let queryResults = BigQuery.Jobs.query(request, projectId);
  const jobId = queryResults.jobReference.jobId;

  // Check on status of the Query Job.
  let sleepTimeMs = 500;
  while (!queryResults.jobComplete) {
    Utilities.sleep(sleepTimeMs);
    sleepTimeMs *= 2;
    queryResults = BigQuery.Jobs.getQueryResults(projectId, jobId);
  }
  return queryResults;
}

/**
 * Insert data from sheet as records into BigQuery table, for use in BQML models
 */
function populateTable(prompts, responses) {
  // Delete existing rows from temporary table
  var query = `DELETE FROM \`${datasetId}.${tableName}\` WHERE TRUE`;
  response = runQuery(query);

  // Insert records in batches, to avoid exceeding resource constraints
  const BATCH_SIZE = 500;
  for (let i = 0, j = prompts.length; i < j; i += BATCH_SIZE) {
    const batch = prompts.slice(i, i + BATCH_SIZE);

    const values = getValuesStr(batch);
    query = `INSERT \`${datasetId}.${tableName}\` (prompt) VALUES ${values}`;
    runQuery(query);
  }
}

/**
 * Converts an array into comma-separated strings for use in SQL statement
 */
function getValuesStr(inputs) {
  const values = [];
  for (let i = 0; i < inputs.length; i++) {
    input = inputs[i];
    values.push("(" + inputs[i].map((x) => "'" + x + "'").join() + ")");
  }
  return values.join();
}

/**
 * Create menu items linked to functions
 */
function onOpen() {
  SpreadsheetApp.getUi()
    .createMenu("Gemini")
    .addItem("Query", "query")
    .addItem("Setup", "setup")
    .addSubMenu(
      SpreadsheetApp.getUi()
        .createMenu("Configure")
        .addItem("Temperature", "setTemperature")
        .addItem("Max Output Tokens", "setMaxOutputTokens"),
    )
    .addToUi();
}
