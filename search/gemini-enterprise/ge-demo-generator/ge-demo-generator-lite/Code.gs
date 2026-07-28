// Copyright 2026 Google LLC
//
// Licensed under the Apache License, Version 2.0 (the "License");
// you may not use this file except in compliance with the License.
// You may obtain a copy of the License at
//
//     https://www.apache.org/licenses/LICENSE-2.0
//
// Unless required by applicable law or agreed to in writing, software
// distributed under the License is distributed on an "AS IS" BASIS,
// WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
// See the License for the specific language governing permissions and
// limitations under the License.
/**
 * GE Demo Generator Lite - Backend (Code.gs)
 *
 * Gemini Enterprise Business Edition (GEBE) does not support custom ADK agents.
 * Instead of generating a Cloud setup script, this app synthesizes demo content
 * as native Google Workspace files (Docs, Sheets, Slides, plus optional Office/PDF
 * exports and AI-generated images) directly into the ACCESSING user's My Drive,
 * organized under a single "My Demos" folder with a per-demo Guide Doc.
 *
 * Execution identity: the web app runs as USER_ACCESSING, so all files are created
 * in the accessing user's own Drive with their own authorization.
 *
 * Many helpers here are reused verbatim from the GE Demo Generator (Code.gs):
 * Vertex AI Agent Platform calls, image generation, JSON repair, and retry.
 */

// ===========================================
// Configuration
// ===========================================

const SCRIPT_PROPS = PropertiesService.getScriptProperties();
const CONFIG = {
  PROJECT_ID: SCRIPT_PROPS.getProperty('PROJECT_ID'),
  LOCATION: SCRIPT_PROPS.getProperty('LOCATION') || 'global',
  MODEL: SCRIPT_PROPS.getProperty('MODEL') || 'gemini-3.6-flash',
  MAX_RETRIES: 3,
  RETRY_DELAY_MS: 1000,
  APP_VERSION: 'v1.7-public',
  MY_DEMOS_FOLDER: 'My Demos'
};

// Office / PDF export MIME types.
const EXPORT_MIME = {
  pdf: 'application/pdf',
  docx: 'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
  xlsx: 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
  pptx: 'application/vnd.openxmlformats-officedocument.presentationml.presentation'
};

// ===========================================
// Web App Entry Point
// ===========================================

function doGet(e) {
  const configError = checkConfiguration();
  if (configError) {
    const template = HtmlService.createTemplateFromFile('SetupError');
    template.errorMessage = configError;
    return template.evaluate()
      .setTitle('Setup Required - GE Demo Generator Lite')
      .addMetaTag('viewport', 'width=device-width, initial-scale=1.0');
  }

  const template = HtmlService.createTemplateFromFile('index');
  template.appVersion = CONFIG.APP_VERSION;
  template.projectId = CONFIG.PROJECT_ID;
  template.userEmail = Session.getActiveUser().getEmail();
  template.generatorModel = CONFIG.MODEL || 'gemini-3.6-flash';

  let webAppUrl = '';
  try {
    webAppUrl = ScriptApp.getService().getUrl();
  } catch (err) {
    console.error('Failed to get Web App URL:', err.message);
  }
  template.webAppUrl = webAppUrl;

  return template.evaluate()
    .setTitle('GE Demo Generator Lite')
    .addMetaTag('viewport', 'width=device-width, initial-scale=1.0')
    .setXFrameOptionsMode(HtmlService.XFrameOptionsMode.ALLOWALL);
}

/**
 * Validates that all required script properties are set.
 * Returns an error message if missing, or null if valid.
 */
function checkConfiguration() {
  const missing = [];
  if (!CONFIG.PROJECT_ID) missing.push('PROJECT_ID');

  if (missing.length > 0) {
    return 'The following mandatory Script Properties are missing: ' + missing.join(', ') +
           '. Please run initializeProject() from the Apps Script editor or set them manually in Project Settings.';
  }
  return null;
}

/**
 * One-time initialization to set up Script Properties. Run from the editor.
 * @param {string} projectId - Google Cloud project hosting Vertex AI Agent Platform.
 */
function initializeProject(projectId) {
  const scriptProps = PropertiesService.getScriptProperties();
  const currentProps = scriptProps.getProperties();

  // Fall back to already-set properties so running this with no arguments
  // (e.g. from the editor when properties were set manually) does not error.
  projectId = projectId || currentProps.PROJECT_ID;
  if (!projectId) throw new Error('PROJECT_ID is mandatory: pass it as the first argument or set it in Script Properties.');

  const newProps = {
    PROJECT_ID: projectId,
    LOCATION: currentProps.LOCATION || 'global',
    MODEL: currentProps.MODEL || 'gemini-3.6-flash'
  };

  scriptProps.setProperties(newProps);
  return 'Initialization complete. Properties set/merged: ' + Object.keys(newProps).join(', ');
}

// ===========================================
// Vertex AI Agent Platform utilities (reused from GE Demo Generator)
// ===========================================

function callVertexAIWithRetry(prompt) { return executeWithRetry(function () { return callVertexAI(prompt); }); }

function callVertexAI(prompt) {
  const location = CONFIG.LOCATION || 'global';
  const host = location === 'global' ? 'aiplatform.googleapis.com' : location + '-aiplatform.googleapis.com';
  const url = 'https://' + host + '/v1/projects/' + CONFIG.PROJECT_ID + '/locations/' + location +
    '/publishers/google/models/' + CONFIG.MODEL + ':generateContent';

  const payload = { contents: [{ role: 'user', parts: [{ text: prompt }] }], generationConfig: { temperature: 0.4, maxOutputTokens: 65535 } };
  const response = UrlFetchApp.fetch(url, {
    method: 'POST', contentType: 'application/json',
    headers: { 'Authorization': 'Bearer ' + ScriptApp.getOAuthToken() },
    payload: JSON.stringify(payload), muteHttpExceptions: true
  });
  if (response.getResponseCode() !== 200) throw new Error('AI Error: ' + response.getContentText());
  return JSON.parse(response.getContentText()).candidates[0].content.parts[0].text;
}

/**
 * Calls Vertex AI Agent Platform gemini-3-pro-image in the global region to generate an image.
 * Returns { base64Data, mimeType }.
 */
function generateImageBase64WithRetry(prompt) { return executeWithRetry(function () { return generateImageBase64(prompt); }); }

/**
 * Deterministically injects the concrete table rows (spec.imageRows) into the
 * image prompt so the image model renders multiple distinct lines instead of
 * collapsing to a single row. Falls back to the raw imagePrompt when fewer than
 * 2 rows are supplied (e.g., non-tabular scene images).
 */
function buildImagePromptWithRows_(spec) {
  var rows = Array.isArray(spec.imageRows)
    ? spec.imageRows.map(function (r) { return String(r).trim(); }).filter(function (r) { return r.length > 0; })
    : [];
  if (rows.length < 2) {
    console.warn('[GEDemoLite-ImageGen] ' + (spec.fileName || 'image') + ' has fewer than 2 imageRows; using raw imagePrompt.');
    return spec.imagePrompt;
  }
  var columns = Array.isArray(spec.imageColumns)
    ? spec.imageColumns.map(function (c) { return String(c).trim(); }).filter(function (c) { return c.length > 0; })
    : [];
  var n = rows.length;
  var block = '\n\nMANDATORY TABLE CONTENT - Render EXACTLY these ' + n + ' rows inside the table grid, each as its own separate line. Do NOT merge, summarize, or omit any row. The table must visibly contain all ' + n + ' rows.';
  if (columns.length > 0) { block += '\nColumns: ' + columns.join(' | '); }
  rows.forEach(function (row, i) { block += '\n' + (i + 1) + ') ' + row; });
  block += '\nThe table has exactly ' + n + ' data rows.';
  return spec.imagePrompt + block;
}

function generateImageBase64(prompt) {
  const host = 'aiplatform.googleapis.com';
  const url = 'https://' + host + '/v1/projects/' + CONFIG.PROJECT_ID +
    '/locations/global/publishers/google/models/gemini-3-pro-image:generateContent';

  const payload = {
    contents: [{ role: 'user', parts: [{ text: prompt }] }],
    generationConfig: { responseModalities: ['IMAGE'] }
  };

  const response = UrlFetchApp.fetch(url, {
    method: 'POST', contentType: 'application/json',
    headers: { 'Authorization': 'Bearer ' + ScriptApp.getOAuthToken() },
    payload: JSON.stringify(payload), muteHttpExceptions: true
  });

  if (response.getResponseCode() !== 200) {
    throw new Error('Image Gen Error: ' + response.getContentText());
  }

  const json = JSON.parse(response.getContentText());
  if (!json.candidates || json.candidates.length === 0 || !json.candidates[0].content.parts) {
    throw new Error('No candidates or parts returned from Image Gen API.');
  }

  let base64Data = null;
  let mimeType = 'image/jpeg';
  const parts = json.candidates[0].content.parts;
  for (let i = 0; i < parts.length; i++) {
    if (parts[i].inlineData) {
      base64Data = parts[i].inlineData.data;
      mimeType = parts[i].inlineData.mimeType || mimeType;
      break;
    }
  }
  if (!base64Data) throw new Error('No inlineData found in the response parts.');
  return { base64Data: base64Data, mimeType: mimeType };
}

function executeWithRetry(fn) {
  let lastError;
  for (let attempt = 1; attempt <= CONFIG.MAX_RETRIES; attempt++) {
    try { return fn(); } catch (error) { lastError = error; Utilities.sleep(CONFIG.RETRY_DELAY_MS * attempt); }
  }
  throw lastError;
}

/**
 * Strips markdown code fences and parses JSON, repairing truncation if needed.
 */
function parseAiJson_(text) {
  let jsonStr = String(text).replace(/```json\n?/g, '').replace(/```\n?/g, '').trim();
  jsonStr = repairTruncatedJson(jsonStr);
  return JSON.parse(jsonStr);
}

function repairTruncatedJson(jsonStr) {
  try { JSON.parse(jsonStr); return jsonStr; } catch (e) {}

  let fixed = jsonStr;
  let openBraces = 0; let openBrackets = 0; let inString = false; let escaped = false;
  for (let i = 0; i < fixed.length; i++) {
    const char = fixed[i];
    if (escaped) { escaped = false; continue; }
    if (char === '\\') { escaped = true; continue; }
    if (char === '"') inString = !inString;
    else if (!inString) {
      if (char === '{') openBraces++; else if (char === '}') openBraces--;
      else if (char === '[') openBrackets++; else if (char === ']') openBrackets--;
    }
  }
  if (inString) fixed += '"';
  while (openBrackets > 0) { fixed += ']'; openBrackets--; }
  while (openBraces > 0) { fixed += '}'; openBraces--; }
  return fixed;
}

/**
 * Detects the language a business goal is WRITTEN in (not the language of the
 * countries/companies it mentions) with a fast gemini-3.5-flash-lite call, so the
 * planning prompt can enforce it as a hard constant instead of asking the planning
 * model to detect-and-follow (which drifts toward locale-associated languages on
 * long outputs). Returns an English language name (e.g. "English", "Indonesian")
 * or '' on failure, in which case the caller falls back to inline detection.
 */
function detectGoalLanguage_(userGoal) {
  const prompt =
    'Identify the language the following text is WRITTEN in, based ONLY on its actual words and script. ' +
    'Ignore the language of any countries, companies, places, or people it mentions (e.g. text written in ' +
    'English ABOUT an Indonesian company is English). If several languages are mixed, pick the dominant one. ' +
    'Respond with ONLY the English name of the language (e.g. "English", "Japanese", "Indonesian"), nothing else.\n\n' +
    'TEXT:\n"""\n' + String(userGoal).substring(0, 2000) + '\n"""';
  try {
    const location = CONFIG.LOCATION || 'global';
    const host = location === 'global' ? 'aiplatform.googleapis.com' : location + '-aiplatform.googleapis.com';
    const url = 'https://' + host + '/v1/projects/' + CONFIG.PROJECT_ID + '/locations/' + location + '/publishers/google/models/gemini-3.5-flash-lite:generateContent';
    const payload = { contents: [{ role: 'user', parts: [{ text: prompt }] }], generationConfig: { temperature: 0, maxOutputTokens: 512 } };
    const response = UrlFetchApp.fetch(url, {
      method: 'POST', contentType: 'application/json',
      headers: { 'Authorization': 'Bearer ' + ScriptApp.getOAuthToken() },
      payload: JSON.stringify(payload), muteHttpExceptions: true
    });
    if (response.getResponseCode() !== 200) throw new Error('HTTP ' + response.getResponseCode());
    const text = String(JSON.parse(response.getContentText()).candidates[0].content.parts[0].text).trim();
    // Accept only a plausible bare language name; anything chatty falls back.
    if (/^[A-Za-z][A-Za-z ()'\-]{1,40}$/.test(text)) return text;
    throw new Error('Unexpected detector output: ' + text.substring(0, 80));
  } catch (e) {
    console.warn('[LANG-DETECT] ' + e.message);
    return '';
  }
}

// ===========================================
// Phase A: Planning (planDemo)
// ===========================================

/**
 * Phase A. Calls Gemini to produce the full demo plan (folder name, demo prompts,
 * and the list of files with their content inlined). Returns the parsed plan.
 *
 * @param {string} userGoal - Business problem (any language).
 * @param {object} options - { domain, includeDocs, includeSheets, includeSlides,
 *                             includeImages, includePdf }
 */
function planDemo(userGoal, options) {
  options = options || {};
  if (!userGoal || !String(userGoal).trim()) throw new Error('A business goal is required.');

  const tz = Session.getScriptTimeZone() || 'Asia/Tokyo';
  const todayStr = Utilities.formatDate(new Date(), tz, 'yyyy-MM-dd');

  const wanted = [];
  if (options.includeDocs !== false) wanted.push('document');
  if (options.includeSheets !== false) wanted.push('spreadsheet');
  if (options.includeSlides !== false) wanted.push('presentation');
  if (options.includeImages) wanted.push('image');
  if (options.includePdf) wanted.push('pdf');
  if (wanted.length === 0) wanted.push('document');

  const pdfNote = options.includePdf
    ? 'PDF FILES ARE SPECIAL: a "pdf" file is NOT a copy of the other files. It is a standalone, professional ' +
      'EXTERNAL document authored by a THIRD PARTY (an industry analyst firm, consultancy, standards body, ' +
      'market-research publisher, trade association, or regulator) that the organization receives from outside - ' +
      'e.g. a whitepaper, analyst research report, market outlook, regulatory brief, or benchmark study. Include ' +
      '1-2 such pdf files. Make them long-form (5-8 sections, 2-4 substantial paragraphs each), authoritative and ' +
      'neutral in tone, attributed to a FICTIONAL publisher, with 1-2 charts of illustrative industry-level data. ' +
      'They give outside context the agent can ingest as reference knowledge; do NOT restate the customer-internal ' +
      'documents/sheets/slides.'
    : '';

  const domainHint = options.domain ? ('Target domain/industry: ' + options.domain + '.') : 'Auto-detect the domain from the goal.';

  // Pin the output language up front (fast flash-lite call) so the planning model
  // follows a stated constant instead of detect-and-follow, which drifts toward
  // languages associated with the countries/companies the goal mentions.
  const detectedLang = detectGoalLanguage_(userGoal);

  // v1.6: anchor persona - the wizard's Target Persona becomes the demo's
  // protagonist across files, agent prompt, and demo guide. Empty = unchanged.
  const personaDesc = sanitizePersonaText_(options.persona);
  const personaRule = personaDesc
    ? '11. ANCHOR PERSONA (MANDATORY): the demo creator selected the primary user of this demo: ' + personaDesc + '. ' +
      'This persona is the PROTAGONIST: frame the main document and the first demoGuide step around this ' +
      'persona\'s own business process; in agentDesignerPrompt, state that the agent primarily serves this ' +
      'role; keep the persona as the recurring protagonist across demoGuide steps and cast other roles as ' +
      'hand-off counterparts (the departments the process flows to or from), never replacing the protagonist. ' +
      'Even when the scenario suggests a different natural protagonist, the selected persona wins.\n'
    : '';
  // v1.6: cross-departmental fabric (light port of the internal cross-org pack).
  const crossDeptRule =
    '12. CROSS-DEPARTMENTAL FABRIC: design the demo as a slice of ONE company\'s shared operations, not a ' +
    'single team\'s folder. At least one spreadsheet must be shared operational data that TWO OR MORE ' +
    'departments use for different purposes (e.g. orders created by sales, fulfilled by logistics, invoiced ' +
    'by finance), and the demoGuide story must include at least one HAND-OFF between departments (one step\'s ' +
    'output becomes the input another department\'s role acts on in a later step). ESCAPE HATCH: where the ' +
    'goal plausibly involves only one department, use an adjacent supporting function instead and never force ' +
    'unnatural departments - the goal always wins.\n';
  // v1.6: quantitative grounding from domain research (port of P17-lite).
  let groundingBlock = '';
  if (options.quantFacts && options.quantFacts.facts && Object.keys(options.quantFacts.facts).length) {
    const bt = String.fromCharCode(96);
    const factsText = JSON.stringify(options.quantFacts.facts).split(bt).join('');
    const qfName = String(options.quantFacts.companyName || 'the company').split(bt).join('');
    groundingBlock = 'DATA GROUNDING (verified real-world scale): the following facts about ' + qfName +
      ' were gathered from public sources during domain research. Reflect them so the demo feels like THIS ' +
      'organization: spreadsheet scale, regional mixes, product categories, and document narratives should be ' +
      'plausible for an organization of this size (scaled down to the row ceilings). Apply ONLY if the ' +
      'BUSINESS GOAL is about this company.\n' + factsText + '\n\n';
  }

  const prompt =
    'You are a senior demo data architect. Design a realistic, RICH, self-consistent set of Google ' +
    'Workspace demo files for the business goal below, to be showcased in Gemini Enterprise. The output ' +
    'must look like real, production-grade business documents, not thin placeholders.\n\n' +
    'BUSINESS GOAL:\n' + userGoal + '\n\n' +
    domainHint + '\n' +
    'REFERENCE DATE (today): ' + todayStr + '\n\n' +
    groundingBlock +
    'HARD RULES:\n' +
    '1. CUSTOMER IDENTITY (ISOLATION ANCHOR): Identify a single specific customer/company name. If the ' +
    'BUSINESS GOAL already names a company, use it verbatim. Otherwise INVENT a DISTINCTIVE, brandable, ' +
    'unlikely-to-collide fictional company name appropriate to the domain and language - avoid generic names ' +
    'like "Acme", "Global Corp", or "Company XYZ". Use this SAME customer name consistently AND PROMINENTLY in ' +
    'EVERY file: in each document title and its opening sentence, in a spreadsheet title or header row, in ' +
    'slide titles and footers, in the PDF author/byline, and in email senders. Also invent a small ' +
    'demo-specific vocabulary of proper nouns tied to this customer (e.g. a product line, a project codename, ' +
    'a few key people) and reuse them across files. This dense, consistent self-identification keeps each ' +
    'demo strongly tied to its own company so that when many demos share one Drive, queries about this ' +
    'customer retrieve THIS demo\'s files and not another company\'s. Return the name as "customerName".\n' +
    '2. TEMPORAL ANCHOR: Use the reference date as "today". Historical records span backward (e.g. last 90 ' +
    'days) and future records (forecasts, schedules) span forward from it. Never use stale years.\n' +
    '3. LANGUAGE (TARGET LANGUAGE): ' +
    (detectedLang
      ? 'The BUSINESS GOAL is written in ' + detectedLang + ', so the target language of this demo is ' +
        detectedLang + '. '
      : 'The target language is the language the BUSINESS GOAL text itself is written in - detect it ONLY ' +
        'from its actual script/characters. ') +
    'Write ALL human-readable content in the target language. Do NOT switch to a language merely associated ' +
    'with the companies, brands, or locations mentioned (e.g. an English goal about an Indonesian or Japanese ' +
    'company still produces English content). Do NOT mix languages. File names may be ASCII.\n' +
    '4. DOMAIN ADAPTATION: Tailor every schema, field, and value to the specific industry and operational ' +
    'context. Use realistic names, numbers, currencies, and terminology. No generic placeholders like ' +
    '"Product A" or "Company XYZ".\n' +
    '5. DEPTH & QUALITY (IMPORTANT): Make the content substantial. Documents: 4-6 sections, each with 2-4 ' +
    'well-written paragraphs of real analysis (not one-liners). Spreadsheets: 15-25 data rows per sheet with ' +
    'internally consistent values that tell a story. Presentations: 6-8 slides with 3-5 substantive bullets ' +
    'each. Cross-reference the same entities/numbers across files so the demo is coherent.\n' +
    '6. CHARTS (realism): Documents and presentations SHOULD include charts where they add value. Add a ' +
    '"charts" array to a document, and a "chart" object to relevant slides. A chart is ' +
    '{ "title", "type": one of "column"|"bar"|"pie"|"line"|"area", "headers": ["Category","Series1",...], ' +
    '"data": [["Label", number, ...], ...] } with 4-8 rows of REAL numbers consistent with the spreadsheets. ' +
    'Include at least one chart in the main document and at least one chart slide when those types are requested.\n' +
    '7. IMAGES: For any image file, write "imagePrompt" in ENGLISH (the model renders text literally), but ' +
    'any text DEPICTED inside the image must be written in the target language. Make image prompts detailed ' +
    'and photorealistic or professional-infographic style. If the image depicts a TABLE, FORM, RECEIPT, ' +
    'ORDER SHEET, INVOICE or any document with line items, it MUST contain MULTIPLE rows (never a single ' +
    'item row): add "imageColumns" (array of column headers in the target language) and "imageRows" ' +
    '(array of 2-4 strings, each one full row with cell values joined by " | " in the same order as ' +
    'imageColumns, in the target language, consistent with the spreadsheet/document data in this demo). ' +
    'Describe ONLY the layout and style in "imagePrompt"; put the concrete line items in "imageRows" (the ' +
    'system injects them into the final prompt). Omit imageColumns/imageRows for non-tabular images (e.g. scenes).\n' +
    '8. SIZE CEILING: At most 6 files total. Spreadsheets: at most 3 sheets. Presentations: at most 8 slides. ' +
    'Documents: at most 6 sections. At most 2 charts per document and 1 chart per slide.\n' +
    '9. AGENT DESIGNER PROMPT (MARKDOWN): Gemini Enterprise has an "Agent Designer" that builds an AI agent ' +
    'from a natural-language description. Write "agentDesignerPrompt" as a single self-contained instruction ' +
    'in the target language, formatted in MARKDOWN (use ## section headings and - bullet lists). It must cover: ' +
    'a Role/Persona section for the customer named above; a Tasks section listing the concrete tasks it ' +
    'performs; a Data Sources section referencing the Workspace files generated in this demo by name and type; ' +
    'a Tone section; and an Example Requests section with 2-3 sample user prompts. In the Role/Persona section, ' +
    'state EXPLICITLY (naturally, the way a real single-company assistant is configured) that the agent is ' +
    'the internal assistant for the customer named above, that its ENTIRE knowledge base concerns ONLY that ' +
    'customer, and that it must treat any document or question about a DIFFERENT organization as out of scope ' +
    'and ignore it. This keeps the built agent grounded to this demo even when the connected Drive also holds ' +
    'other companies\' demo files. Aim for 150-250 words.\n' +
    '10. DEMO FLOW (demoGuide): Write "demoGuide" as an ORDERED array of 5-8 demo STEPS that together tell ' +
    'one coherent, self-sufficient demo story a presenter can follow top-to-bottom (overview -> drill-down -> ' +
    'action/insight). Each step is { "title": "Step N: <short title>", "role": "<who is asking - a specific ' +
    'job title>", "context": "<1-2 sentence setup of what this person wants and why>", "prompt": "<the primary ' +
    'ready-to-paste prompt for Gemini Enterprise. ISOLATION: frame EVERY prompt naturally around the customer/' +
    'brand or its products (e.g. start with the company name, or speak in the first person as that company\'s ' +
    'employee using \'our\') so retrieval is anchored to THIS company. Do NOT cite file names in prompts - real ' +
    'users do not know the file names; anchor on the company, brand, topic, period, or metric instead>", "expectedSources": ' +
    '["<exact fileName(s) from the generated files this step relies on>"], "expectedAnswer": "<concise but ' +
    'concrete description of the answer the agent should produce - name the actual tables/fields/numbers from ' +
    'the demo data, e.g. a ranked table or specific values>", "differentiators": [ { "title": "<short ' +
    'capability name>", "detail": "<one sentence on what makes Gemini Enterprise impressive for THIS step>" } ] }. ' +
    'Provide 2-3 differentiators per step a presenter can call out - draw from capabilities like: zero-setup ' +
    'search (Gemini finds and parses the right file from the connected Drive folder without manual targeting), ' +
    'domain-noise resilience (ignores irrelevant files in the folder), multi-turn context (remembers the entity ' +
    'across follow-ups), causal reasoning (connects drivers to outcomes), semantic mapping (understands ' +
    'differently-named or inverse fields), and dynamic synthesis (instant tables/charts from raw data). Tailor ' +
    'each differentiator to what the step actually does. expectedSources MUST use the real fileName values from ' +
    'the files you generate. All human-readable text in the target language.\n' +
    personaRule +
    crossDeptRule + '\n' +
    'FILE TYPES TO INCLUDE (only these): ' + wanted.join(', ') + '.\n' +
    pdfNote + '\n\n' +
    'FINAL LANGUAGE CHECK: every human-readable string value in the JSON below - titles, section headings, ' +
    'paragraphs, spreadsheet cells, slide bullets, chart titles/headers/labels, demoGuide fields, ' +
    'agentDesignerPrompt, oneSentenceSummary - MUST be in the target language' +
    (detectedLang ? ' (' + detectedLang + ')' : '') + '. Only "imagePrompt" is written in English; file ' +
    'names may be ASCII.\n\n' +
    'Return ONLY valid JSON (no markdown fences) with this exact shape:\n' +
    '{\n' +
    '  "folderName": "Demo - <customer name> - <short domain>",\n' +
    '  "referenceDate": "' + todayStr + '",\n' +
    '  "customerName": "<the customer/company name used everywhere>",\n' +
    '  "domainName": "<short domain name>",\n' +
    '  "oneSentenceSummary": "<one sentence describing the demo, in target language>",\n' +
    '  "agentDesignerPrompt": "<MARKDOWN prompt for Gemini Enterprise Agent Designer, target language>",\n' +
    '  "demoGuide": [ { "title": "Step 1: <title>", "role": "<job title>", "context": "<setup>", "prompt": "<primary prompt>", "expectedSources": ["<fileName>"], "expectedAnswer": "<what the agent returns>", "differentiators": [ { "title": "<capability>", "detail": "<why it impresses>" } ] } ],\n' +
    '  "files": [\n' +
    '    { "type": "document", "fileName": "Report.gdoc", "description": "<one line>",\n' +
    '      "title": "<title>", "sections": [ { "heading": "<heading>", "paragraphs": ["<para>", "<para>"] } ],\n' +
    '      "charts": [ { "title": "<t>", "type": "column", "headers": ["Month","Revenue"], "data": [["Jan",1200]] } ] },\n' +
    '    { "type": "spreadsheet", "fileName": "Data.gsheet", "description": "<one line>",\n' +
    '      "sheets": [ { "sheetName": "<name>", "data": [ ["Header A","Header B"], ["v1","v2"] ] } ] },\n' +
    '    { "type": "presentation", "fileName": "Pitch.gslides", "description": "<one line>",\n' +
    '      "slides": [ { "title": "<title>", "bullets": ["<point>"], "chart": { "title": "<t>", "type": "pie", "headers": ["Segment","Share"], "data": [["A",40]] } } ] },\n' +
    '    { "type": "pdf", "fileName": "Industry_Outlook_2026.pdf", "description": "<one line>",\n' +
    '      "title": "<external report title>", "publisher": "<fictional analyst/research firm>",\n' +
    '      "sections": [ { "heading": "<heading>", "paragraphs": ["<para>", "<para>"] } ],\n' +
    '      "charts": [ { "title": "<t>", "type": "bar", "headers": ["Year","Value"], "data": [["2024",10]] } ] },\n' +
    '    { "type": "image", "fileName": "scene.jpg", "description": "<one line>",\n' +
    '      "imagePrompt": "<detailed English prompt>",\n' +
    '      "imageColumns": ["<header>", "<header>"], "imageRows": ["<cell> | <cell>", "<cell> | <cell>"] }\n' +
    '  ]\n' +
    '}\n';

  const response = callVertexAIWithRetry(prompt);
  let plan;
  try {
    plan = parseAiJson_(response);
  } catch (e) {
    throw new Error('Failed to parse the AI plan. Try simplifying the goal or reducing requested formats.');
  }

  if (!plan.files || !plan.files.length) throw new Error('The AI plan contained no files.');

  // Normalize / clamp.
  plan.referenceDate = plan.referenceDate || todayStr;
  plan.customerName = plan.customerName ? String(plan.customerName) : '';
  plan.folderName = sanitizeFolderName_(plan.folderName || ('Demo - ' + (plan.customerName || plan.domainName || 'GE Demo')));
  plan.agentDesignerPrompt = plan.agentDesignerPrompt ? String(plan.agentDesignerPrompt) : '';
  plan.demoGuide = Array.isArray(plan.demoGuide) ? plan.demoGuide.slice(0, 5) : [];
  plan.files = plan.files.slice(0, 6).filter(function (f) { return wanted.indexOf(f.type) !== -1; });
  if (!plan.files.length) throw new Error('The AI plan did not include any of the requested file types.');

  return plan;
}

function sanitizeFolderName_(name) {
  return String(name).replace(/[\\/:*?"<>|]/g, '-').trim().substring(0, 120) || 'Demo';
}

/**
 * Normalizes a target-persona object sent from the client into a plain text
 * description safe for LLM prompt interpolation. Strips backticks, curly
 * braces, and backslashes, and caps the length. Returns '' when no persona
 * is selected, keeping every prompt identical to the pre-persona behavior.
 */
function sanitizePersonaText_(persona) {
  if (!persona || typeof persona !== 'object') return '';
  const raw = String(persona.description || persona.label || '');
  const stripRe = new RegExp('[' + String.fromCharCode(96) + '{}\\\\]', 'g');
  return raw.replace(stripRe, '').replace(/\s+/g, ' ').trim().substring(0, 300);
}

/**
 * Magic-wand goal optimizer. Expands a raw/loose business scenario (optionally
 * carrying selected research workflows) into a structured Markdown business
 * scenario in the SAME language. Reused from the GE Demo Generator, retargeted
 * for Workspace-file demos. Returns { success, optimizedGoal } or { success:false, error }.
 */
function optimizeGoalWithMagicWand(rawGoal, persona) {
  if (!rawGoal || !String(rawGoal).trim()) return { success: false, error: 'Nothing to optimize.' };
  const location = CONFIG.LOCATION || 'global';
  const host = location === 'global' ? 'aiplatform.googleapis.com' : location + '-aiplatform.googleapis.com';
  const model = 'gemini-3.5-flash-lite';
  const url = 'https://' + host + '/v1/projects/' + CONFIG.PROJECT_ID + '/locations/' + location + '/publishers/google/models/' + model + ':generateContent';

  const prompt =
    'You are an expert prompt engineer and business analyst. Take the raw or loosely defined business ' +
    'scenario below (it may already contain a company name and selected target workflows) and rewrite it ' +
    'into a perfectly structured, high-density professional Business Scenario in Markdown.\n\n' +
    'Input to optimize:\n"""\n' + rawGoal + '\n"""\n\n' +
    'MULTILINGUAL RULE (STRICT):\n' +
    '1. Detect the language ONLY from the actual script/characters of the input text above.\n' +
    '2. Write the ENTIRE Markdown output (every section, heading, sentence, company name, and currency) in ' +
    'that EXACT same language and script.\n' +
    '3. Even if the companies, brands, or locations mentioned in the input are culturally or geographically ' +
    'associated with another country or language, you MUST NOT switch to that associated language. Match the ' +
    'literal script of the input text only. For example, if the input is written in English, the output MUST ' +
    'be entirely in English even when it mentions a Japanese or German company.\n\n' +
    'Produce exactly four Markdown sections (headers translated to the detected input language):\n' +
    '1. Title: a realistic customer/company name + industry appropriate to the detected input language. Keep one if the input already has it.\n' +
    '2. Target Role: a specific professional job title.\n' +
    '3. Business Scenario: rich, realistic context with KPIs and background.\n' +
    '4. Operational Challenge: a clear, high-value workflow for an AI agent, with a trigger event, explicit ' +
    'business rules and numeric thresholds, what is automatic vs. what needs human approval, and the ' +
    'Workspace data sources involved (Docs, Sheets, Slides). The challenge MUST span at least two departments ' +
    'that share the same operational data, describing the hand-off between them that the agent supports ' +
    '(single-department problems get an adjacent supporting function instead). If the input lists target ' +
    'workflows, build the challenge specifically around them.\n\n' +
    (sanitizePersonaText_(persona)
      ? 'TARGET PERSONA OVERRIDE (MANDATORY): This demo targets a specific user: ' + sanitizePersonaText_(persona) + '. ' +
        'The Target Role section MUST be a single specific, professional job title matching this persona, translated ' +
        'naturally into the detected output language. The Business Scenario and Operational Challenge MUST be framed ' +
        'around this persona\'s own business process, daily decisions, and KPIs. If the input text implies a different ' +
        'role, the persona specified here takes precedence.\n\n'
      : '') +
    'Use realistic brand names and values, never generic placeholders. Return ONLY the raw Markdown (no code fences, no preamble).';

  const payload = { contents: [{ role: 'user', parts: [{ text: prompt }] }], generationConfig: { temperature: 0.4, maxOutputTokens: 8192 } };
  let lastError;
  let delayMs = 1000;
  for (let i = 0; i < 3; i++) {
    try {
      const response = UrlFetchApp.fetch(url, {
        method: 'POST', contentType: 'application/json',
        headers: { 'Authorization': 'Bearer ' + ScriptApp.getOAuthToken() },
        payload: JSON.stringify(payload), muteHttpExceptions: true
      });
      const code = response.getResponseCode();
      if (code === 200) {
        const result = JSON.parse(response.getContentText()).candidates[0].content.parts[0].text;
        return { success: true, optimizedGoal: result.trim() };
      }
      lastError = new Error('AI Optimization Error (HTTP ' + code + ')');
      if (code !== 429 && code < 500) break;
    } catch (e) { lastError = e; }
    if (i < 2) { Utilities.sleep(delayMs); delayMs *= 2; }
  }
  return { success: false, error: lastError ? lastError.message : 'AI Optimization failed after retries' };
}

/**
 * Translates Template Hub entries into a target language for display. Kept on the
 * backend so non-ASCII translations never live in the inline frontend JS (which
 * would break the GAS minifier). items: [{ label, text }]. Returns { success, items }
 * with the same length/order translated; falls back to the originals on failure.
 */
function translateTemplates(lang, items) {
  const LANGS = { es: 'Spanish', fr: 'French', pt: 'Portuguese', de: 'German', it: 'Italian', ja: 'Japanese', en: 'English' };
  const target = LANGS[lang];
  if (!target || lang === 'en') return { success: true, items: items || [] };
  if (!items || !items.length) return { success: true, items: [] };

  const prompt =
    'Translate the "label" and "text" of each entry below into ' + target + '. ' +
    'Keep it natural and professional (business demo scenario titles and descriptions). ' +
    'Return ONLY a JSON array of objects with "label" and "text", in the SAME order and SAME length as the input. ' +
    'Do not add or remove entries.\n\nINPUT:\n' + JSON.stringify(items.map(function (i) { return { label: i.label, text: i.text }; }));

  try {
    const location = CONFIG.LOCATION || 'global';
    const host = location === 'global' ? 'aiplatform.googleapis.com' : location + '-aiplatform.googleapis.com';
    const model = 'gemini-3.5-flash-lite';
    const url = 'https://' + host + '/v1/projects/' + CONFIG.PROJECT_ID + '/locations/' + location + '/publishers/google/models/' + model + ':generateContent';
    const payload = { contents: [{ role: 'user', parts: [{ text: prompt }] }], generationConfig: { temperature: 0.2, maxOutputTokens: 8192 } };
    const response = UrlFetchApp.fetch(url, {
      method: 'POST', contentType: 'application/json',
      headers: { 'Authorization': 'Bearer ' + ScriptApp.getOAuthToken() },
      payload: JSON.stringify(payload), muteHttpExceptions: true
    });
    if (response.getResponseCode() !== 200) throw new Error('Translate Error: ' + response.getContentText().substring(0, 200));
    const text = JSON.parse(response.getContentText()).candidates[0].content.parts[0].text;
    const arr = parseAiJson_(text);
    if (!Array.isArray(arr) || arr.length !== items.length) throw new Error('Length mismatch');
    return { success: true, items: arr };
  } catch (e) {
    console.warn('[TRANSLATE] ' + e.message);
    return { success: false, items: items, error: e.message };
  }
}

// ===========================================
// Customer Domain Research (Google Search grounding)
// ===========================================

/**
 * Researches the company behind a domain via Google Search grounding and proposes
 * a demo goal. Reused from the GE Demo Generator. Returns a structured object the
 * frontend uses to pre-fill the goal + show challenges and automatable workflows.
 * Optional persona ({ id, label, description }) frames the suggested goal around
 * that target user's business process.
 */
function researchCompanyByDomain(domain, persona) {
  if (!domain || typeof domain !== 'string') return { success: false, error: 'Domain is required.' };

  domain = domain.trim().toLowerCase().replace(/^(https?:\/\/)?(www\.)?/, '').replace(/\/.*$/, '');

  const tldLangMap = {
    '.co.jp': 'Japanese', '.jp': 'Japanese', '.ne.jp': 'Japanese', '.or.jp': 'Japanese', '.ac.jp': 'Japanese',
    '.de': 'German', '.fr': 'French', '.es': 'Spanish', '.it': 'Italian',
    '.cn': 'Chinese', '.tw': 'Chinese', '.kr': 'Korean', '.br': 'Portuguese',
    '.com': 'English', '.io': 'English', '.ai': 'English', '.org': 'English', '.net': 'English'
  };
  let responseLang = 'English';
  const sortedTlds = Object.keys(tldLangMap).sort(function (a, b) { return b.length - a.length; });
  for (let i = 0; i < sortedTlds.length; i++) { if (domain.endsWith(sortedTlds[i])) { responseLang = tldLangMap[sortedTlds[i]]; break; } }

  const prompt =
    'You are a business analyst researching a company for an AI agent demo.\n' +
    'Research the company behind the domain "' + domain + '" using the latest information from the internet.\n\n' +
    'RESPONSE LANGUAGE: Respond entirely in ' + responseLang + '.\n\n' +
    (sanitizePersonaText_(persona)
      ? 'TARGET PERSONA (MANDATORY): This demo is being prepared for a specific target user: ' + sanitizePersonaText_(persona) + '. ' +
        'Apply this throughout: when listing "workflows", prioritize workflows that this persona owns or directly depends on. ' +
        'The "suggestedGoal" MUST be written around this persona\'s own business process: name this role explicitly as the ' +
        'primary user of the AI agent, and frame the business problem, stakeholders, and KPIs from this persona\'s point of ' +
        'view. Render the role title naturally in the RESPONSE LANGUAGE.\n\n'
      : '') +
    'Provide a structured JSON object:\n' +
    '1. companyName: Official company name\n' +
    '2. companySummary: 2-3 sentence overview (industry, scale, main business, HQ)\n' +
    '3. industry: Primary industry classification\n' +
    '4. businessChallenges: array of 3-5 key challenges the company likely faces\n' +
    '5. workflows: array of 5-8 business workflows, each { "name", "automatable" (boolean), "reason" }\n' +
    '6. suggestedGoal: a detailed 3-5 sentence business scenario suitable as input for a Workspace demo ' +
    'generator. Reference the real company and industry, focus on the most automatable workflow(s), and ' +
    'describe a specific, actionable problem an AI agent could solve with realistic operational context. ' +
    'The scenario MUST span at least two departments that share the same operational data, describing the ' +
    'hand-off between them (if only one department plausibly applies, use an adjacent supporting function ' +
    'such as support-to-billing).\n' +
    '7. quantFacts: an object of verifiable QUANTITATIVE facts about the company (include ONLY facts clearly ' +
    'supported by search results - omit uncertain keys entirely; never estimate). String values with unit and ' +
    'as-of year. Optional keys: storeCount, siteCount, employeeCount, annualRevenue, mainRegions (array), ' +
    'productCategories (array), notableScale.\n\n' +
    'IMPORTANT: Use REAL, factual information. Do NOT invent details. If you cannot find enough information, ' +
    'set success to false with an error message.\n\n' +
    'Output pure JSON only (no code blocks):\n' +
    '{ "companyName": "...", "companySummary": "...", "industry": "...", ' +
    '"businessChallenges": ["..."], "workflows": [ {"name":"...","automatable":true,"reason":"..."} ], ' +
    '"suggestedGoal": "...", "quantFacts": { "storeCount": "...", "mainRegions": ["..."] } }';

  try {
    const location = CONFIG.LOCATION || 'global';
    const host = location === 'global' ? 'aiplatform.googleapis.com' : location + '-aiplatform.googleapis.com';
    const researchModel = 'gemini-3.5-flash-lite';
    const url = 'https://' + host + '/v1/projects/' + CONFIG.PROJECT_ID + '/locations/' + location +
      '/publishers/google/models/' + researchModel + ':generateContent';

    const payload = {
      contents: [{ role: 'user', parts: [{ text: prompt }] }],
      tools: [{ googleSearch: {} }],
      generationConfig: { temperature: 0.2, maxOutputTokens: 65535 }
    };
    const apiResponse = UrlFetchApp.fetch(url, {
      method: 'POST', contentType: 'application/json',
      headers: { 'Authorization': 'Bearer ' + ScriptApp.getOAuthToken() },
      payload: JSON.stringify(payload), muteHttpExceptions: true
    });
    if (apiResponse.getResponseCode() !== 200) throw new Error('AI Search Error: ' + apiResponse.getContentText().substring(0, 200));

    const candidate = JSON.parse(apiResponse.getContentText()).candidates[0];
    const allText = candidate.content.parts.filter(function (p) { return p.text; }).map(function (p) { return p.text; }).join('');

    let jsonStr = allText.replace(/```json\n?/g, '').replace(/```\n?/g, '').trim();
    let parsed;
    try {
      parsed = JSON.parse(jsonStr);
    } catch (parseErr) {
      const jsonMatch = jsonStr.match(/\{[\s\S]*\}/);
      if (jsonMatch) parsed = JSON.parse(jsonMatch[0]);
      else throw new Error('Failed to parse research results.');
    }

    if (!parsed.companyName || !parsed.suggestedGoal) return { success: false, error: 'Could not find sufficient information for domain: ' + domain };

    return {
      success: true,
      companyName: parsed.companyName,
      companySummary: parsed.companySummary || '',
      industry: parsed.industry || '',
      businessChallenges: parsed.businessChallenges || [],
      workflows: parsed.workflows || [],
      suggestedGoal: parsed.suggestedGoal,
      quantFacts: parsed.quantFacts || null
    };
  } catch (e) {
    console.error('[RESEARCH] Error for domain ' + domain + ':', e.message);
    return { success: false, error: 'Research failed: ' + e.message };
  }
}

// ===========================================
// Folder management
// ===========================================

/**
 * Finds (or creates) the "My Demos" folder in the accessing user's My Drive root.
 * Idempotent across runs.
 */
function getOrCreateMyDemosFolder() {
  const root = DriveApp.getRootFolder();
  const it = root.getFoldersByName(CONFIG.MY_DEMOS_FOLDER);
  if (it.hasNext()) return it.next();
  return root.createFolder(CONFIG.MY_DEMOS_FOLDER);
}

/**
 * Creates this demo's subfolder inside "My Demos". All artifacts (data files,
 * exports, images, and the Guide Doc) go directly into this single subfolder.
 * Returns { folderId, url, demoId }.
 */
function createDemoFolder(plan) {
  const parent = getOrCreateMyDemosFolder();
  const demoId = makeDemoId_(plan.customerName || plan.domainName || plan.folderName);
  // Append the demoId so folders stay uniquely identifiable when many demos coexist.
  const folderName = sanitizeFolderName_(plan.folderName) + ' [' + demoId + ']';
  const sub = parent.createFolder(folderName);
  return { folderId: sub.getId(), url: sub.getUrl(), demoId: demoId, folderName: folderName };
}

function makeDemoId_(seed) {
  const slug = String(seed || 'demo').toLowerCase().replace(/[^a-z0-9]+/g, '_').replace(/^_|_$/g, '').substring(0, 30) || 'demo';
  const rand = Utilities.getUuid().replace(/-/g, '').substring(0, 8);
  return 'demo_' + slug + '_' + rand;
}

// ===========================================
// Phase B: Per-file generation (generateOneFile)
// ===========================================

/**
 * Phase B. Creates a single file from its spec into the demo subfolder. Each call
 * is self-contained and stays well within the 6-minute limit (one image at most).
 * Returns { fileName, type, fileId, url, formats, error }.
 */
function generateOneFile(folderId, fileSpec) {
  const folder = DriveApp.getFolderById(folderId);
  try {
    let created;
    switch (fileSpec.type) {
      case 'document': created = createDocFile(folder, fileSpec); break;
      case 'spreadsheet': created = createSheetFile(folder, fileSpec); break;
      case 'presentation': created = createSlideFile(folder, fileSpec); break;
      case 'pdf': created = createPdfFile(folder, fileSpec); break;
      case 'image': created = createImageFile(folder, fileSpec); break;
      default: throw new Error('Unknown file type: ' + fileSpec.type);
    }

    const formats = ['native'];
    // Office/PDF exports apply only to native Google file types.
    if (created.sourceId && Array.isArray(fileSpec.exportFormats)) {
      fileSpec.exportFormats.forEach(function (fmt) {
        const mime = EXPORT_MIME[fmt];
        if (!mime) return;
        // Skip Office formats that do not match the file type.
        if (fmt === 'docx' && fileSpec.type !== 'document') return;
        if (fmt === 'xlsx' && fileSpec.type !== 'spreadsheet') return;
        if (fmt === 'pptx' && fileSpec.type !== 'presentation') return;
        try {
          exportNativeFile(created.sourceId, mime, folder, baseName_(fileSpec.fileName) + '.' + fmt);
          formats.push(fmt);
        } catch (exErr) {
          console.error('[EXPORT] ' + fmt + ' failed for ' + fileSpec.fileName + ': ' + exErr.message);
        }
      });
    }

    return { fileName: created.name, type: fileSpec.type, fileId: created.fileId, url: created.url, formats: formats };
  } catch (e) {
    console.error('[generateOneFile] ' + (fileSpec && fileSpec.fileName) + ': ' + e.message);
    return { fileName: (fileSpec && fileSpec.fileName) || 'unknown', type: fileSpec && fileSpec.type, error: e.message };
  }
}

function baseName_(fileName) {
  return String(fileName || 'file').replace(/\.[a-z0-9]+$/i, '');
}

function createDocFile(folder, spec) {
  const doc = DocumentApp.create(baseName_(spec.fileName));
  const body = doc.getBody();
  body.clear();
  if (spec.title) body.appendParagraph(spec.title).setHeading(DocumentApp.ParagraphHeading.TITLE);
  (spec.sections || []).forEach(function (section) {
    if (section.heading) body.appendParagraph(section.heading).setHeading(DocumentApp.ParagraphHeading.HEADING1);
    (section.paragraphs || []).forEach(function (p) { body.appendParagraph(String(p)); });
  });
  // Charts (rendered as inline images) for realistic reports/PDFs.
  (spec.charts || []).slice(0, 2).forEach(function (chartSpec) {
    if (!chartSpec || !chartSpec.data || !chartSpec.data.length) return;
    try {
      if (chartSpec.title) body.appendParagraph(String(chartSpec.title)).setHeading(DocumentApp.ParagraphHeading.HEADING2);
      const img = buildChartImage_(chartSpec);
      if (img) {
        const inserted = body.appendImage(img);
        inserted.setWidth(468); // fit page width
        inserted.setHeight(293);
      }
    } catch (chartErr) {
      console.error('[DOC CHART] ' + chartErr.message);
    }
  });
  doc.saveAndClose();
  const file = DriveApp.getFileById(doc.getId());
  folder.addFile(file);
  DriveApp.getRootFolder().removeFile(file);
  return { name: file.getName(), fileId: doc.getId(), sourceId: doc.getId(), url: doc.getUrl() };
}

/**
 * Creates a standalone professional EXTERNAL document as a real PDF (whitepaper /
 * analyst report / market outlook). Builds a temporary Doc, exports it to PDF into
 * the folder, then trashes the temp Doc so only the PDF remains.
 */
function createPdfFile(folder, spec) {
  const doc = DocumentApp.create(baseName_(spec.fileName));
  const body = doc.getBody();
  body.clear();
  if (spec.title) body.appendParagraph(spec.title).setHeading(DocumentApp.ParagraphHeading.TITLE);
  if (spec.publisher) {
    const pub = body.appendParagraph(spec.publisher);
    pub.setForegroundColor('#64748b');
    pub.editAsText().setItalic(true);
  }
  (spec.sections || []).forEach(function (section) {
    if (section.heading) body.appendParagraph(section.heading).setHeading(DocumentApp.ParagraphHeading.HEADING1);
    (section.paragraphs || []).forEach(function (p) { body.appendParagraph(String(p)); });
  });
  (spec.charts || []).slice(0, 2).forEach(function (chartSpec) {
    if (!chartSpec || !chartSpec.data || !chartSpec.data.length) return;
    try {
      if (chartSpec.title) body.appendParagraph(String(chartSpec.title)).setHeading(DocumentApp.ParagraphHeading.HEADING2);
      const img = buildChartImage_(chartSpec);
      if (img) { const ins = body.appendImage(img); ins.setWidth(468); ins.setHeight(293); }
    } catch (chartErr) {
      console.error('[PDF CHART] ' + chartErr.message);
    }
  });
  doc.saveAndClose();

  const pdfFile = exportNativeFile(doc.getId(), EXPORT_MIME.pdf, folder, baseName_(spec.fileName) + '.pdf');
  // Remove the temporary source Doc; only the PDF should remain in the demo folder.
  try { DriveApp.getFileById(doc.getId()).setTrashed(true); } catch (e) {}
  return { name: pdfFile.getName(), fileId: pdfFile.getId(), sourceId: null, url: pdfFile.getUrl() };
}

function createSheetFile(folder, spec) {
  const ss = SpreadsheetApp.create(baseName_(spec.fileName));
  const sheets = spec.sheets || [];
  sheets.forEach(function (sheetSpec, idx) {
    let sheet;
    if (idx === 0) { sheet = ss.getSheets()[0]; sheet.setName(sheetSpec.sheetName || 'Sheet1'); }
    else { sheet = ss.insertSheet(sheetSpec.sheetName || ('Sheet' + (idx + 1))); }
    const data = normalizeGrid_(sheetSpec.data || []);
    if (data.length && data[0].length) {
      sheet.getRange(1, 1, data.length, data[0].length).setValues(data);
      sheet.getRange(1, 1, 1, data[0].length).setFontWeight('bold');
    }
  });
  SpreadsheetApp.flush();
  const file = DriveApp.getFileById(ss.getId());
  folder.addFile(file);
  DriveApp.getRootFolder().removeFile(file);
  return { name: file.getName(), fileId: ss.getId(), sourceId: ss.getId(), url: ss.getUrl() };
}

/**
 * Pads a 2D array into a rectangular grid of strings (setValues requires uniform rows).
 */
function normalizeGrid_(rows) {
  if (!rows.length) return [];
  let maxCols = 0;
  rows.forEach(function (r) { if (Array.isArray(r) && r.length > maxCols) maxCols = r.length; });
  return rows.map(function (r) {
    const row = Array.isArray(r) ? r.slice() : [r];
    while (row.length < maxCols) row.push('');
    return row.map(function (c) { return (c === null || c === undefined) ? '' : c; });
  });
}

function createSlideFile(folder, spec) {
  const pres = SlidesApp.create(baseName_(spec.fileName));
  // Remove the default empty slide once we have real slides.
  const specSlides = spec.slides || [];
  specSlides.forEach(function (slideSpec) {
    const hasChart = slideSpec.chart && slideSpec.chart.data && slideSpec.chart.data.length;
    const slide = pres.appendSlide(SlidesApp.PredefinedLayout.TITLE_AND_BODY);
    try {
      const titlePh = slide.getPlaceholder(SlidesApp.PlaceholderType.TITLE) ||
        slide.getPlaceholder(SlidesApp.PlaceholderType.CENTERED_TITLE);
      if (titlePh && slideSpec.title) titlePh.asShape().getText().setText(slideSpec.title);
    } catch (e) {}
    try {
      const bodyPh = slide.getPlaceholder(SlidesApp.PlaceholderType.BODY);
      if (bodyPh) {
        const bullets = (slideSpec.bullets || []).map(function (b) { return String(b); }).join('\n');
        bodyPh.asShape().getText().setText(bullets);
      }
    } catch (e) {}
    // Insert a chart image on the right half of the slide when provided.
    if (hasChart) {
      try {
        const img = buildChartImage_(slideSpec.chart);
        if (img) slide.insertImage(img, 360, 90, 320, 200);
      } catch (chartErr) {
        console.error('[SLIDE CHART] ' + chartErr.message);
      }
    }
  });
  const slides = pres.getSlides();
  if (slides.length > specSlides.length && specSlides.length > 0) slides[0].remove();
  pres.saveAndClose();
  const file = DriveApp.getFileById(pres.getId());
  folder.addFile(file);
  DriveApp.getRootFolder().removeFile(file);
  return { name: file.getName(), fileId: pres.getId(), sourceId: pres.getId(), url: pres.getUrl() };
}

/**
 * Builds a chart from a chart spec and returns it as a PNG image blob. Uses a
 * scratch spreadsheet (trashed afterward). chartSpec:
 * { title, type: column|bar|pie|line|area, headers: [..], data: [[label, num, ..], ..] }
 */
function buildChartImage_(chartSpec) {
  const typeMap = {
    column: Charts.ChartType.COLUMN, bar: Charts.ChartType.BAR, pie: Charts.ChartType.PIE,
    line: Charts.ChartType.LINE, area: Charts.ChartType.AREA
  };
  const grid = normalizeGrid_([chartSpec.headers || []].concat(chartSpec.data || []));
  if (grid.length < 2 || grid[0].length < 2) return null;

  let ss = null;
  try {
    ss = SpreadsheetApp.create('__gedemo_chart_' + Utilities.getUuid().substring(0, 8));
    const sheet = ss.getSheets()[0];
    sheet.getRange(1, 1, grid.length, grid[0].length).setValues(grid);
    const builder = sheet.newChart()
      .setChartType(typeMap[chartSpec.type] || Charts.ChartType.COLUMN)
      .addRange(sheet.getRange(1, 1, grid.length, grid[0].length))
      .setPosition(1, grid[0].length + 2, 0, 0)
      .setOption('width', 640)
      .setOption('height', 400);
    if (chartSpec.title) builder.setOption('title', String(chartSpec.title));
    const chart = builder.build();
    sheet.insertChart(chart);
    SpreadsheetApp.flush();
    return sheet.getCharts()[0].getAs('image/png');
  } finally {
    if (ss) { try { DriveApp.getFileById(ss.getId()).setTrashed(true); } catch (e) {} }
  }
}

function createImageFile(folder, spec) {
  if (!spec.imagePrompt) throw new Error('Image file has no imagePrompt.');
  const gen = generateImageBase64WithRetry(buildImagePromptWithRows_(spec));
  const ext = (gen.mimeType && gen.mimeType.indexOf('png') !== -1) ? '.png' : '.jpg';
  const name = baseName_(spec.fileName) + ext;
  const blob = Utilities.newBlob(Utilities.base64Decode(gen.base64Data), gen.mimeType, name);
  const file = folder.createFile(blob);
  // Images are not Google-native: no Office/PDF export, so sourceId is omitted.
  return { name: file.getName(), fileId: file.getId(), sourceId: null, url: file.getUrl() };
}

// ===========================================
// Office / PDF export (Drive v3)
// ===========================================

/**
 * Exports a native Google file (Doc/Sheet/Slide) to an Office/PDF blob and saves
 * it into the target folder. Only works Google-native -> Office (one direction).
 * Primary path uses the Drive v3 advanced service; falls back to the export URL.
 */
function exportNativeFile(sourceFileId, targetMimeType, folder, fileName) {
  let blob;
  try {
    blob = Drive.Files.export(sourceFileId, targetMimeType);
  } catch (advErr) {
    blob = null;
  }
  if (!blob || typeof blob.setName !== 'function') {
    const url = 'https://www.googleapis.com/drive/v3/files/' + sourceFileId +
      '/export?mimeType=' + encodeURIComponent(targetMimeType);
    const resp = UrlFetchApp.fetch(url, {
      headers: { Authorization: 'Bearer ' + ScriptApp.getOAuthToken() },
      muteHttpExceptions: true
    });
    if (resp.getResponseCode() !== 200) throw new Error('Export failed (' + resp.getResponseCode() + '): ' + resp.getContentText().substring(0, 200));
    blob = resp.getBlob();
  }
  blob.setName(fileName);
  return folder.createFile(blob);
}

// ===========================================
// Phase C: Demo Guide Doc + finalize
// ===========================================

/**
 * Appends a paragraph "Label value" with ONLY the label bolded. Explicitly resets
 * bold/italic/color on the whole paragraph first so Google Docs formatting never
 * bleeds from a previously styled paragraph into the rest of the document.
 */
function guideLabeled_(body, label, value, color) {
  const para = body.appendParagraph(label + (value ? ' ' + value : ''));
  const t = para.editAsText();
  t.setBold(false); t.setItalic(false); t.setForegroundColor(color || '#1f2937');
  if (label) t.setBold(0, label.length - 1, true);
  return para;
}

/**
 * Creates the per-demo Guide Doc in the demo subfolder. Always generated,
 * regardless of selected formats. Named to sort first.
 */
function createDemoGuideDoc(folderId, plan, fileResults) {
  const folder = DriveApp.getFolderById(folderId);
  const docName = '00_Demo Guide - ' + (plan.domainName || baseName_(plan.folderName));
  const doc = DocumentApp.create(docName);
  const body = doc.getBody();
  body.clear();

  body.appendParagraph(docName).setHeading(DocumentApp.ParagraphHeading.TITLE);

  body.appendParagraph('Overview').setHeading(DocumentApp.ParagraphHeading.HEADING1);
  if (plan.oneSentenceSummary) body.appendParagraph(plan.oneSentenceSummary);
  body.appendParagraph('Domain: ' + (plan.domainName || 'N/A'));
  body.appendParagraph('Reference date: ' + (plan.referenceDate || 'N/A'));
  const tz = Session.getScriptTimeZone() || 'Asia/Tokyo';
  body.appendParagraph('Generated: ' + Utilities.formatDate(new Date(), tz, 'yyyy-MM-dd HH:mm'));

  body.appendParagraph('Prerequisite: Google Drive Setup & Connection').setHeading(DocumentApp.ParagraphHeading.HEADING1);
  body.appendParagraph('In the Gemini Enterprise interface (Business, Standard, or Plus edition), navigate to the Connectors settings page and ensure the Google Drive connector is toggled ON and authorized.');
  body.appendListItem('This lets the agent read the files in this demo folder as grounding sources.');
  body.appendListItem('Use the same Google account that owns this "My Demos" folder.');
  body.appendListItem('For the cleanest results, scope or limit the Drive connector to THIS demo folder when possible, so the agent grounds only on this demo and not on other demos stored in the same Drive.');

  body.appendParagraph('Files in this demo').setHeading(DocumentApp.ParagraphHeading.HEADING1);
  (fileResults || []).forEach(function (r) {
    if (!r || r.error) {
      body.appendListItem('[FAILED] ' + ((r && r.fileName) || 'unknown') + (r && r.error ? ' - ' + r.error : ''));
      return;
    }
    const fmts = (r.formats && r.formats.length > 1) ? (' (' + r.formats.join(', ') + ')') : '';
    body.appendListItem(r.fileName + fmts);
  });

  if (plan.agentDesignerPrompt) {
    body.appendParagraph('Agent Designer prompt').setHeading(DocumentApp.ParagraphHeading.HEADING1);
    body.appendParagraph('Paste this into the Gemini Enterprise Agent Designer ("What do you want your agent to do?") to build the agent for this demo:');
    const adp = body.appendParagraph(plan.agentDesignerPrompt);
    adp.editAsText().setBold(false).setItalic(false).setForegroundColor('#1f2937');
  }

  if (plan.demoGuide && plan.demoGuide.length) {
    body.appendParagraph('Demo flow').setHeading(DocumentApp.ParagraphHeading.HEADING1);
    body.appendParagraph('Follow these steps top-to-bottom in Gemini Enterprise to run the demo.');
    plan.demoGuide.forEach(function (s, i) {
      // Backward-compat: plain string, or old persona object with prompts[].
      if (typeof s === 'string') { body.appendListItem(s); return; }
      if (s.prompts && !s.prompt) {
        body.appendParagraph(s.persona || ('Step ' + (i + 1))).setHeading(DocumentApp.ParagraphHeading.HEADING2);
        if (s.role) guideLabeled_(body, 'Role:', s.role);
        if (s.objective) guideLabeled_(body, 'Objective:', s.objective);
        (s.prompts || []).forEach(function (q) { body.appendListItem(String(q)); });
        body.appendParagraph('');
        return;
      }
      body.appendParagraph(s.title || ('Step ' + (i + 1))).setHeading(DocumentApp.ParagraphHeading.HEADING2);
      if (s.role) guideLabeled_(body, 'Role:', s.role);
      if (s.context) { var cp = body.appendParagraph(String(s.context)); cp.editAsText().setBold(false).setItalic(false).setForegroundColor('#1f2937'); }
      if (s.prompt) guideLabeled_(body, 'Prompt:', String(s.prompt), '#1d4ed8'); // blue, easy to spot
      if (s.expectedSources && s.expectedSources.length) guideLabeled_(body, 'Expected sources:', (s.expectedSources || []).join(', '));
      if (s.expectedAnswer) guideLabeled_(body, 'Expected answer:', String(s.expectedAnswer));
      if (s.differentiators && s.differentiators.length) {
        guideLabeled_(body, 'Differentiation Highlights:', '');
        s.differentiators.forEach(function (d) {
          if (typeof d === 'string') { body.appendListItem(d).editAsText().setBold(false).setForegroundColor('#1f2937'); return; }
          var li = body.appendListItem((d.title ? d.title + ': ' : '') + (d.detail || ''));
          var lt = li.editAsText(); lt.setBold(false).setItalic(false).setForegroundColor('#1f2937');
          if (d.title) lt.setBold(0, d.title.length, true);
        });
      }
      body.appendParagraph(''); // spacer between steps
    });
  }

  body.appendParagraph('How to delete this demo').setHeading(DocumentApp.ParagraphHeading.HEADING1);
  body.appendListItem('Open GE Demo Generator Lite and click the trash icon on this demo in My Demos. This removes it from your history AND moves this entire demo folder (with all generated files) to your Google Drive Trash.');
  body.appendListItem('Trashed items are recoverable from Google Drive Trash for about 30 days, or empty the Trash to delete them permanently.');
  body.appendListItem('You can also delete it manually: move this folder to the Trash in Google Drive.');

  doc.saveAndClose();
  const file = DriveApp.getFileById(doc.getId());
  folder.addFile(file);
  DriveApp.getRootFolder().removeFile(file);
  return { fileId: doc.getId(), url: doc.getUrl(), name: docName };
}

/**
 * Phase C. Generates the Guide Doc, then records the demo to history (best-effort).
 * Returns { guideDoc, history }.
 */
function finalizeDemo(demoId, folderInfo, plan, options, timings, fileResults) {
  const result = {};

  try {
    result.guideDoc = createDemoGuideDoc(folderInfo.folderId, plan, fileResults);
  } catch (e) {
    console.error('[finalizeDemo] Guide doc failed: ' + e.message);
    result.guideDoc = { error: e.message };
  }

  return result;
}
