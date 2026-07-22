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
 * GE Demo Generator — Backend (Code.gs)
 *
 * End-to-end generator for production-ready AI agent demo environments.
 * Given a natural-language business goal, this Google Apps Script file
 * produces a self-contained bash setup script that provisions and deploys
 * a full-stack agent on Google Cloud in a single command.
 *
 * ── What Gets Generated ──────────────────────────────────────────────
 *   • Synthetic business data (BigQuery tables + optional Firestore docs)
 *   • Dual-model ADK agent (Gemini 3.5 Flash-Lite root → Pro analysis)
 *   • MCP toolsets — BigQuery, Maps, Firestore, Google Workspace (Gmail,
 *     Drive, Calendar, Chat, People), plus arbitrary GitHub MCP servers
 *   • A2A (Agent-to-Agent) server with A2UI interactive components
 *   • Imagen-powered image generation for executive-summary visuals
 *   • Agent Engine Sandbox for secure Python code execution
 *   • Firestore real-time Data Viewer web app (Cloud Run Functions)
 *   • Cloud Run deployment with Secret Manager integration
 *   • One-command cleanup (--cleanup) for all provisioned resources
 *
 * ── Architecture (Multi-Layer Code Generation) ───────────────────────
 *   Layer 1  Code.gs (JavaScript / GAS)
 *        ↓   JS template literals + string concatenation
 *   Layer 2  Bash setup script (setup-demo-xxx.sh)
 *        ↓   Quoted / unquoted heredocs
 *   Layer 3  Python source (agent.py, tools.py, fast_api_app.py, …)
 *        ↓   Runtime string operations
 *   Layer 4  LLM system instruction (consumed by Gemini models)
 *
 *   See AGENTS.md §2 for mandatory escaping rules across layers.
 *
 * ── Web UI (index.html) ──────────────────────────────────────────────
 *   Template gallery, company-research customization, MCP catalog,
 *   community history/social-proof feed, and Drive-backed persistence.
 */

// ===========================================
// Configuration
// ===========================================

/**
 * Explicitly triggers authorization for all required services.
 * Call this from the Google Apps Script IDE or a button to resolve permission issues.
 */
function forceAuthorize() {
  const root = DriveApp.getRootFolder();
  // Simple write test to ensure full Drive scope
  const dummy = root.createFile('ge_auth_success.txt', 'Verification complete.');
  dummy.setTrashed(true);
  
  console.log('✅ Drive Access: OK (' + root.getName() + ')');
  
  // Safe check for spreadsheet scope
  try {
    const ss = SpreadsheetApp.openByUrl(CONFIG.LOG_SHEET_URL);
    console.log('✅ Spreadsheet Access: OK (' + ss.getName() + ')');
  } catch (e) {
    console.warn('⚠️ Spreadsheet Access: Authorized but URL inaccessible.');
  }

  return '✅ Authorization verified. Refresh the browser and try generating a demo!';
}

const SCRIPT_PROPS = PropertiesService.getScriptProperties();
const CONFIG = {
  PROJECT_ID: SCRIPT_PROPS.getProperty('PROJECT_ID'),
  LOCATION: SCRIPT_PROPS.getProperty('LOCATION') || 'global',
  MODEL: SCRIPT_PROPS.getProperty('MODEL') || 'gemini-3.6-flash',
  GITHUB_TOKEN: SCRIPT_PROPS.getProperty('GITHUB_TOKEN'),
  MAX_RETRIES: 3,
  RETRY_DELAY_MS: 1000,
  APP_VERSION: 'v11.31-public',
  // Agent-template source: the generated setup script fetches the static
  // Python/JSON template files (agent_template/ in the repo) at run time.
  // TEMPLATE_REF may be a branch name (default 'main'): it is resolved to a
  // concrete commit SHA at script-GENERATION time and that SHA is baked into
  // each generated script, so scripts stay reproducible without this file
  // ever committing its own merge SHA. Set the TEMPLATE_REF Script Property
  // to a 40-hex SHA to hard-pin, or point TEMPLATE_REPO/TEMPLATE_REF at a
  // fork/branch for pre-merge testing.
  TEMPLATE_REPO: SCRIPT_PROPS.getProperty('TEMPLATE_REPO') || 'https://github.com/GoogleCloudPlatform/generative-ai.git',
  TEMPLATE_REF: SCRIPT_PROPS.getProperty('TEMPLATE_REF') || 'main',
  TEMPLATE_SUBDIR: SCRIPT_PROPS.getProperty('TEMPLATE_SUBDIR') || 'search/gemini-enterprise/ge-demo-generator/agent_template',
  LOG_SHEET_URL: SCRIPT_PROPS.getProperty('LOG_SHEET_URL')
};


// ===========================================
// Demo Taxonomy (controlled vocabulary)
// ===========================================

/**
 * Controlled vocabulary used to classify every generated demo so the
 * catalog can be faceted by industry / persona / use case.
 *
 * Values are ALWAYS recorded in English regardless of the user's input
 * language: a userGoal written in Japanese (or any language) still maps
 * to the English enum values below. `Other` is the hybrid fallback — when
 * none of the enum members fit, the closest free-form English label is
 * stored separately (in the Drive backup JSON only) as a candidate for
 * future promotion into these enums.
 *
 * NOTE: This list is mirrored in index.html (TAXONOMY) for the catalog
 * facet chips. Keep the two in sync when editing.
 */
const TAXONOMY = {
  industry: [
    'Retail', 'Finance', 'Healthcare', 'Manufacturing', 'Public Sector',
    'Media & Entertainment', 'Technology', 'Logistics & Supply Chain',
    'Energy & Utilities', 'Telecom', 'Education', 'Travel & Hospitality',
    'Automotive', 'Legal & Professional Services', 'Other'
  ],
  persona: [
    'Sales', 'Marketing', 'Operations', 'Finance', 'Customer Service',
    'Product', 'HR', 'IT / Engineering', 'Executive', 'Supply Chain',
    'Legal & Compliance', 'R&D / Research', 'Other'
  ],
  useCase: [
    'Analytics & Insights', 'Process Automation', 'Customer Engagement',
    'Forecasting & Planning', 'Document Processing', 'Knowledge Retrieval',
    'Risk & Anomaly Detection', 'Optimization', 'Compliance & Audit', 'Other'
  ]
};



// ===========================================
// Web App Entry Point
// ===========================================
function doGet() {
  const configError = checkConfiguration();
  if (configError) {
    const template = HtmlService.createTemplateFromFile('SetupError');
    template.errorMessage = configError;
    return template.evaluate()
      .setTitle('Setup Required - GE Demo Generator')
      .addMetaTag('viewport', 'width=device-width, initial-scale=1.0');
  }

  const template = HtmlService.createTemplateFromFile('index');
  
  template.appVersion = CONFIG.APP_VERSION;

  template.projectId = CONFIG.PROJECT_ID;
  template.userEmail = Session.getActiveUser().getEmail();
  template.generatorModel = CONFIG.MODEL || 'gemini-3.6-flash';
  
  return template.evaluate()
    .setTitle('GE Demo Generator')
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
  if (!CONFIG.LOG_SHEET_URL) missing.push('LOG_SHEET_URL');
  
  if (missing.length > 0) {
    return 'The following mandatory Script Properties are missing: ' + missing.join(', ') + 
           '. Please run initializeProject() from the Apps Script editor or set them manually in Project Settings.';
  }
  return null;
}

// ===========================================
// Performance & Logging
// ===========================================

/**
 * Ensures the Usage_Logs sheet has the correct header row.
 * Overwrites row 1 every time to keep headers in sync with code.
 */
function ensureLogSheetHeaders(sheet) {
  const HEADERS = [
    'Timestamp', 'User Email',
    'User Goal', 'AI Summary', 'Dataset ID',
    'MCP Servers', 'Generation Time (s)'
  ];
  sheet.getRange(1, 1, 1, HEADERS.length).setValues([HEADERS]);
  // Catalog taxonomy headers in N/O/P (columns 14-16). Columns J-M are left
  // untouched on purpose: J holds the location, and
  // K-M are reserved as a buffer.
  sheet.getRange(1, 14, 1, 3).setValues([['Industry', 'Persona', 'Use Case']]);
}

/**
 * Logs usage metadata to a central Google Sheet
 */
function logUsageToSheet(data) {
  try {
    const ss = SpreadsheetApp.openByUrl(CONFIG.LOG_SHEET_URL);
    const sheet = ss.getSheetByName('Usage_Logs');
    if (!sheet) return { success: false, error: 'Usage_Logs sheet not found' };

    ensureLogSheetHeaders(sheet);

    const userEmail = Session.getActiveUser().getEmail();
    sheet.appendRow([
      new Date(),
      userEmail,
      data.userGoal || 'N/A',
      data.aiSummary || 'N/A',
      data.datasetId || 'N/A',
      data.mcpServers || 'None',
      data.generationTimeSec || 'N/A'
    ]);

    // Write catalog taxonomy into N/O/P (columns 14-16) on the row we just
    // appended. Done as a separate write (not part of appendRow) so we never
    // overwrite the location formula in column J or the J-M buffer.
    const appendedRow = sheet.getLastRow();
    sheet.getRange(appendedRow, 14, 1, 3).setValues([[
      data.industry || 'Other',
      data.persona || 'Other',
      data.useCase || 'Other'
    ]]);

    // Auto-wrap the AI Summary column (D) for better readability
    sheet.getRange('D2:D').setWrap(true);
    SpreadsheetApp.flush();
    
    // Convert User Email cell to People Smart Chip using Advanced Service
    try {
      const lastRow = sheet.getLastRow();
      const sheetId = sheet.getSheetId();
      const spreadsheetId = ss.getId();
      
      const requests = [
        {
          updateCells: {
            range: {
              sheetId: sheetId,
              startRowIndex: lastRow - 1,
              endRowIndex: lastRow,
              startColumnIndex: 1,
              endColumnIndex: 2
            },
            rows: [
              {
                values: [
                  {
                    userEnteredValue: { stringValue: "@" },
                    chipRuns: [
                      {
                        startIndex: 0,
                        chip: {
                          personProperties: {
                            email: userEmail,
                            displayFormat: "EMAIL"
                          }
                        }
                      }
                    ]
                  }
                ]
              }
            ],
            fields: "userEnteredValue,chipRuns"
          }
        }
      ];
      
      Sheets.Spreadsheets.batchUpdate({ requests: requests }, spreadsheetId);
    } catch (chipErr) {
      console.warn('⚠️ Could not insert People Chip via Advanced Service:', chipErr.message);
    }
    
    return { success: true };
  } catch (e) {
    const errorMsg = 'Logging Spreadsheet Access Failed: ' + e.message;
    console.error(errorMsg);
    return { success: false, error: errorMsg };
  }
}

/**
 * Diagnostic function to check spreadsheet status
 */
function checkSpreadsheet() {
  console.log('checkSpreadsheet called');
  try {
    const ss = SpreadsheetApp.openByUrl(CONFIG.LOG_SHEET_URL);
    const sheets = ss.getSheets().map(s => s.getName());
    const mainSheet = ss.getSheetByName('Usage_Logs');
    const rowCount = mainSheet ? mainSheet.getLastRow() : 0;
    const dataRows = rowCount > 0 ? mainSheet.getRange(1, 1, Math.min(rowCount, 6), mainSheet.getLastColumn()).getValues() : [];
    
    return JSON.stringify({
      success: true,
      currentUser: Session.getActiveUser().getEmail(),
      sheets: sheets,
      usageLogsExist: !!mainSheet,
      rowCount: rowCount,
      headers: dataRows.length > 0 ? dataRows[0] : null,
      sampleRows: dataRows.length > 1 ? dataRows.slice(1) : [],
      url: CONFIG.LOG_SHEET_URL.substring(0, 30) + '...'
    });
  } catch (e) {
    console.error('checkSpreadsheet failed: ' + e.message);
    return JSON.stringify({ success: false, error: e.message });
  }
}


/**
 * One-time initialization function to set up Script Properties.
 * Run this from the Apps Script editor after setting your values.
 * 
 * @param {string} projectId - Your Google Cloud Project ID
 * @param {string} logSheetUrl - URL of your usage log spreadsheet (optional)
 */
function initializeProject(projectId, logSheetUrl) {
  if (!projectId) {
    throw new Error('PROJECT_ID is mandatory for initialization.');
  }

  const scriptProps = PropertiesService.getScriptProperties();
  const currentProps = scriptProps.getProperties();

  const newProps = {
    PROJECT_ID: projectId, 
    LOCATION: currentProps.LOCATION || 'global',
    MODEL: currentProps.MODEL || 'gemini-3.6-flash',
    LOG_SHEET_URL: logSheetUrl || currentProps.LOG_SHEET_URL || ''
  };
  
  // Scopes detection (SpreadsheetApp)
  // These are here so the IDE prompts for authorization.
  try { if (newProps.LOG_SHEET_URL) SpreadsheetApp.openByUrl(newProps.LOG_SHEET_URL); } catch(e) {}
  
  scriptProps.setProperties(newProps);
  console.log('Project initialized. Properties updated: ' + Object.keys(newProps).join(', '));
  return 'Initialization complete. Properties set/merged: ' + Object.keys(newProps).join(', ');
}



/**
 * Backfills catalog taxonomy (N/O/P) for existing Usage_Logs rows that
 * predate taxonomy. Run MANUALLY from the Apps Script editor; processes up
 * to BACKFILL_BATCH rows per invocation to stay under the 6-minute limit.
 * Re-run until "remaining" reaches 0. Idempotent: rows that already have any
 * taxonomy value are skipped.
 */
function backfillTaxonomy() {
  const BACKFILL_BATCH = 150;
  const ss = SpreadsheetApp.openByUrl(CONFIG.LOG_SHEET_URL);
  const sheet = ss.getSheetByName('Usage_Logs');
  if (!sheet) { console.error('[BACKFILL] Usage_Logs sheet not found'); return; }

  ensureLogSheetHeaders(sheet);

  const lastRow = sheet.getLastRow();
  if (lastRow <= 1) { console.log('[BACKFILL] No data rows.'); return; }

  // Read all data rows once: columns A-P (1-16) give us goal/summary plus the
  // current N/O/P taxonomy values.
  const data = sheet.getRange(2, 1, lastRow - 1, 16).getValues();

  let processed = 0;
  let remaining = 0;
  const otherCounts = { industry: 0, persona: 0, useCase: 0 };
  const otherLabels = [];

  for (let i = 0; i < data.length; i++) {
    const row = data[i];
    if (!row[0] || !row[1]) continue; // skip empty spreadsheet rows

    const alreadyClassified = String(row[13] || '').trim() ||
      String(row[14] || '').trim() || String(row[15] || '').trim();
    if (alreadyClassified) continue; // idempotent

    if (processed >= BACKFILL_BATCH) { remaining++; continue; }

    const rowNumber = i + 2; // +1 for header, +1 for 1-based rows
    // userGoal = column E (index 4), aiSummary = column F (index 5).
    const tax = classifyDemoTaxonomy_(row[4], row[5]);
    sheet.getRange(rowNumber, 14, 1, 3).setValues([[tax.industry, tax.persona, tax.useCase]]);

    if (tax.industry === 'Other') { otherCounts.industry++; if (tax.industryOther) otherLabels.push('industry:' + tax.industryOther); }
    if (tax.persona === 'Other') { otherCounts.persona++; if (tax.personaOther) otherLabels.push('persona:' + tax.personaOther); }
    if (tax.useCase === 'Other') { otherCounts.useCase++; if (tax.useCaseOther) otherLabels.push('useCase:' + tax.useCaseOther); }
    processed++;
  }

  SpreadsheetApp.flush();
  console.log('[BACKFILL] Processed ' + processed + ' row(s) this run. Remaining unclassified: ' + remaining);
  console.log('[BACKFILL] Other counts -> industry: ' + otherCounts.industry + ', persona: ' + otherCounts.persona + ', useCase: ' + otherCounts.useCase);
  if (otherLabels.length) console.log('[BACKFILL] Other free-form label candidates (review for enum promotion): ' + otherLabels.join(' | '));

  if (remaining > 0) {
    console.log('[BACKFILL] ' + remaining + ' rows left. Will auto-continue if trigger is active.');
  } else {
    console.log('[BACKFILL] All rows classified! Removing auto-trigger if present.');
    stopBackfillAuto_();
  }
}

/**
 * Starts an automatic backfill loop using a time-based trigger.
 * Runs backfillTaxonomy() every 5 minutes until all rows are classified,
 * then auto-deletes the trigger. Run this once from the editor.
 */
function startBackfillAuto() {
  stopBackfillAuto_();
  ScriptApp.newTrigger('backfillTaxonomy')
    .timeBased()
    .everyMinutes(5)
    .create();
  console.log('[BACKFILL-AUTO] Trigger created. backfillTaxonomy will run every 5 minutes until complete.');
  backfillTaxonomy();
}

/**
 * Manually stop the automatic backfill loop. Run from the editor to cancel.
 */
function stopBackfillAuto() {
  stopBackfillAuto_();
}

/**
 * Removes any existing backfillTaxonomy triggers. Called automatically
 * when backfill completes, or manually to stop early.
 */
function stopBackfillAuto_() {
  var triggers = ScriptApp.getProjectTriggers();
  for (var i = 0; i < triggers.length; i++) {
    if (triggers[i].getHandlerFunction() === 'backfillTaxonomy') {
      ScriptApp.deleteTrigger(triggers[i]);
      console.log('[BACKFILL-AUTO] Removed existing trigger.');
    }
  }
}

/**
 * Returns a Data Profile configuration that holistically controls
 * table count, row density, and column strategy.
 * @param {string} profileId - 'deep', 'standard', or 'wide'
 * @returns {Object} profile configuration
 * @private
 */
function getDataProfile_(profileId) {
  const profiles = {
    deep: {
      id: 'deep',
      label: 'Deep Analysis',
      tableCount: '3-4',
      masterRows: '15-25',
      masterCols: '5-7',
      txnRows: '120+',
      txnCols: '8-12',
      defaultRowCount: 150,
      txnRowTarget: 120,
      masterMinRows: 8,
      txnMinRows: 50,
      strategy: 'Fewer tables with MAXIMUM row density. Prioritize deep temporal coverage and statistical significance in transaction tables. Ideal for time-series analysis, anomaly detection, and trend analysis demos.'
    },
    standard: {
      id: 'standard',
      label: 'Standard',
      tableCount: '5',
      masterRows: '20-30',
      masterCols: '6-8',
      txnRows: '80+',
      txnCols: '8-12',
      defaultRowCount: 100,
      txnRowTarget: 80,
      masterMinRows: 10,
      txnMinRows: 30,
      strategy: 'Balanced star-schema with good relational depth and adequate transaction density. Suitable for most demo scenarios including cross-table joins and operational analytics.'
    },
    wide: {
      id: 'wide',
      label: 'Wide Schema',
      tableCount: '7-8',
      masterRows: '15-20',
      masterCols: '5-7',
      txnRows: '40-50',
      txnCols: '6-10',
      defaultRowCount: 50,
      txnRowTarget: 40,
      masterMinRows: 6,
      txnMinRows: 20,
      strategy: 'Many tables for complex ER diagrams and multi-hop JOIN demos. Row density is intentionally lower to fit within token limits. Best for showcasing relational modeling and schema complexity.'
    }
  };
  return profiles[profileId] || profiles['standard'];
}

/**
 * Main function to generate the demo artifacts
 */
function generateDemo(userGoal, options = {}) {
  const startTime = Date.now();
  const profile = getDataProfile_(options.dataProfile || 'standard');
  const defaultOptions = {
    rowCount: profile.defaultRowCount,
    dataProfile: 'standard',
    publicDatasetId: null,
    usePublicDataset: false,
    enableWorkspaceMcp: false,
    enableComputerUse: false,
    // Default ON since v11.1: the autonomous agent is the flagship demo
    // experience, provisioning is parallelized and fail-soft, and no
    // allowlist is required. The UI toggle allows opting out per demo.
    enableManagedAgent: true,
    enableWorkspaceAuth: false
  };
  options = { ...defaultOptions, ...options };
  
  if (!options.usePublicDataset) {
    options.publicDatasetId = null;
  }
  
  const result = {
    success: false,
    steps: [],
    error: null,
    datasetId: null,
    tableInfo: [],
    dataPreview: [],
    systemInstruction: null,
    setupScript: null,
    rawTables: [],
    suffix: null,
    domainName: null,
    referenceDate: null,
    appliedFactors: null
  };
  
  try {
    // Step 1: Planning and Data Generation
    result.steps.push({ step: 1, status: 'running', message: 'Planning & generating data...' });
    const planResult = planAndGenerateData(userGoal, options);
    result.steps[0] = { step: 1, status: 'completed', message: 'Planning complete' };
    
    // Step 2: Validation
    result.steps.push({ step: 2, status: 'running', message: 'Validating generated data...' });
    const maxRows = Math.min(options.rowCount || 100, 150);
    validateGeneratedData(planResult, maxRows);
    result.steps[1] = { step: 2, status: 'completed', message: 'Validation complete' };
    
    // Step 3: Suffix generation
    const suffix = Utilities.getUuid().replace(/-/g, '').substring(0, 8);
    const baseName = generateBaseName(userGoal, suffix);
    const dirName = "demo-" + baseName;
    const datasetId = ("demo_" + baseName).replace(/-/g, '_');
    
    result.datasetId = datasetId;
    result.userGoal = userGoal;
    // Persisted into the Drive backup so eval tooling and restores can see the
    // selected Target Persona (the history entry alone is not backed up).
    result.targetPersona = options.targetPersona || null;
    result.targetPersonaDesc = options.targetPersonaDesc || null;
    result.quantFacts = options.quantFacts || null;
    result.dataPreview = planResult.dataPreview;
    result.rawTables = planResult.tables;
    result.suffix = suffix;
    result.domainName = baseName.substring(0, baseName.lastIndexOf('-' + suffix));
    result.dirName = dirName;
    result.businessInstruction = planResult.businessInstruction;
    result.technicalInstruction = planResult.technicalInstruction;
    result.systemInstruction = planResult.systemInstruction;
    result.referenceDate = planResult.referenceDate;
    result.publicDatasetId = planResult.publicDatasetId;
    result.demoGuide = planResult.demoGuide;
    result.externalFiles = planResult.externalFiles || [];
    result.appliedFactors = planResult.appliedFactors || {};
    result.agentShortName = planResult.agentShortName || '';
    result.oneSentenceSummary = planResult.oneSentenceSummary || '';
    result.operatingModel = planResult.operatingModel || null;
    result.firestore = planResult.firestore || null;
    result.importedMcpList = options.importedMcpList || null;
    result.metadata = planResult.metadata || null;
    // M2 (v11.16): capability-coverage check (warns only, never blocks).
    // Detects a capability mandate that the demo guide silently dropped.
    try {
      const _guideStr = JSON.stringify(planResult.demoGuide || []).toLowerCase();
      const _covWarnings = [];
      if (options.enableWorkspaceMcp && !/(mail|メール|drive|ドライブ|calendar|カレンダー|chat|チャット)/.test(_guideStr)) _covWarnings.push('Workspace MCP');
      if (options.enableComputerUse && !/(http|browser|ブラウザ|website|サイト|web)/.test(_guideStr)) _covWarnings.push('Computer Use');
      if (options.enableManagedAgent && !/(資料|デッキ|deck|report|レポート|presentation|プレゼン|調査|research)/.test(_guideStr)) _covWarnings.push('Managed Agent');
      const _files = planResult.externalFiles || [];
      if (!_files.some(f => /\.pdf$/i.test(f.fileName || ''))) _covWarnings.push('PDF asset (planning mandates exactly one)');
      if (!_files.some(f => /\.xlsx$/i.test(f.fileName || ''))) _covWarnings.push('Excel asset (planning mandates exactly one)');
      if (_covWarnings.length) {
        console.warn('[COVERAGE] demoGuide may not showcase: ' + _covWarnings.join(', '));
        result.coverageWarnings = _covWarnings;
      }
    } catch (covErr) { /* best-effort only */ }
    // Persist feature flags so the Drive-backup restore path (see the
    // generateSetupScript regeneration block) can rebuild the same script.
    result.enableWorkspaceMcp = options.enableWorkspaceMcp || false;
    result.enableComputerUse = options.enableComputerUse || false;
    result.enableManagedAgent = options.enableManagedAgent || false;
    result.enableWorkspaceAuth = options.enableWorkspaceAuth || false;

    result.setupScript = generateSetupScript({
      datasetId: datasetId,
      systemInstruction: planResult.systemInstruction,
      businessInstruction: planResult.businessInstruction || '',
      referenceDate: planResult.referenceDate,
      publicDatasetId: planResult.publicDatasetId,
      suffix: suffix,
      dirName: dirName,
      tables: planResult.tables,
      firestore: planResult.firestore,
      userGoal: userGoal,
      agentShortName: planResult.agentShortName,
      oneSentenceSummary: planResult.oneSentenceSummary,
      operatingModel: planResult.operatingModel,
      importedMcpList: options.importedMcpList,
      enableWorkspaceMcp: options.enableWorkspaceMcp,
      enableComputerUse: options.enableComputerUse,
      enableManagedAgent: options.enableManagedAgent,
      enableWorkspaceAuth: options.enableWorkspaceAuth,
      metadata: planResult.metadata
    });
    result.steps.push({ step: 4, status: 'completed', message: 'Generation complete' });
    
    result.success = true;

    // Classify the demo into the catalog taxonomy (always English output,
    // even when userGoal was written in another language). Best-effort: a
    // failure here defaults to 'Other' and never blocks generation.
    const taxonomy = classifyDemoTaxonomy_(userGoal, planResult.oneSentenceSummary, planResult.businessInstruction);
    result.industry = taxonomy.industry;
    result.persona = taxonomy.persona;
    result.useCase = taxonomy.useCase;
    // Free-form English labels (only set when the value is 'Other') — persisted
    // in the Drive backup JSON only, as candidates for future enum promotion.
    result.industryOther = taxonomy.industryOther;
    result.personaOther = taxonomy.personaOther;
    result.useCaseOther = taxonomy.useCaseOther;

    // Unified Save Object
    const historyEntry = {
      timestamp: new Date().toISOString(),
      userEmail: Session.getActiveUser().getEmail(),
      userGoal: userGoal,
      aiSummary: planResult.oneSentenceSummary || result.domainName,
      datasetId: datasetId,
      mcpServers: (() => {
        const names = options.importedMcpList
          ? options.importedMcpList.map(m => m.name || (m.github_url ? m.github_url.split('/').pop().replace(/\.git$/, '') : 'Unknown MCP'))
          : [];
        if (options.enableWorkspaceMcp) names.push('Google Workspace MCP');
        return names.length > 0 ? names.join(', ') : 'None';
      })(),
      generationTimeSec: ((Date.now() - startTime) / 1000).toFixed(1),
      industry: taxonomy.industry,
      persona: taxonomy.persona,
      useCase: taxonomy.useCase,
      targetPersona: options.targetPersona || null,
      result: result
    };

    try {
      result.saveStatus = { logSheet: logUsageToSheet(historyEntry) };
    } catch (persistErr) {
      console.error('[PERSISTENCE-CRITICAL] Failed to trigger save logic:', persistErr.message);
      result.saveStatus = { logSheet: { success: false, error: persistErr.message } };
    }
    
  } catch (error) {
    result.error = error.message;
    const lastStep = result.steps[result.steps.length - 1];
    if (lastStep) {
      lastStep.status = 'error';
      lastStep.message = error.message;
    }
  }
  
  return result;
}

// ===========================================
// Step 1: Planning and Data Generation
// ===========================================

/**
 * Discovers a real BigQuery public dataset ID using Google Search grounding,
 * then verifies the table exists using the BigQuery API.
 * @param {string} userGoal - The user's business problem description.
 * @returns {string} A verified public dataset ID or a fallback.
 */
function discoverPublicDataset(userGoal) {
  const discoveryPrompt = `Find a real BigQuery public dataset that would provide EXTERNAL CONTEXT or ENRICHMENT for the following business problem:

"${userGoal}"

Requirements:
1. The dataset MUST exist under the project 'bigquery-public-data'.
2. Search Google to find the exact dataset and table names.
3. PRIORITIZE "External Context" data: weather, demographics, census, economic indicators, geographic features, or market statistics.
4. AVOID "Core Business" data: Do NOT select datasets that look like internal company records (e.g., avoid order histories, customer lists, or internal transactions) unless explicitly required for external benchmarking.
5. Return ONLY the fully qualified ID in the format: bigquery-public-data.dataset_name.table_name
6. If multiple tables exist, choose the most commonly used or primary one.
7. Do NOT invent or hallucinate dataset names.

Examples of preferred "External Context" datasets:
- bigquery-public-data.noaa_gsod.gsod2023 (Weather)
- bigquery-public-data.census_bureau_acs.zip_codes_2018_5yr (Demographics)
- bigquery-public-data.geo_open_streets.lines (Geographic)
- bigquery-public-data.google_trends.top_terms (Market Trends)

Return ONLY the dataset ID, nothing else.`;

  const FALLBACK = 'bigquery-public-data.thelook_ecommerce.orders';

  try {
    const result = callVertexAIWithSearch(discoveryPrompt);
    const cleanId = result.trim().replace(/[`'"]/g, '').split('\n')[0];
    
    if (!cleanId.startsWith('bigquery-public-data.') || cleanId.split('.').length < 3) {
      return FALLBACK;
    }
  
    const verifiedId = verifyAndResolveTable(cleanId);
    return verifiedId || FALLBACK;
  } catch (e) {
    return FALLBACK;
  }
}

/**
 * Verifies a table exists in BigQuery. If the exact table doesn't exist,
 * attempts to find a valid table in the same dataset.
 * @param {string} candidateId - Fully qualified ID (project.dataset.table)
 * @returns {string|null} Verified table ID or null if not found.
 */
function verifyAndResolveTable(candidateId) {
  const parts = candidateId.split('.');
  if (parts.length < 3) return null;
  
  const projectId = parts[0];
  const datasetId = parts[1];
  const tableId = parts.slice(2).join('.'); 
  
  try {
    BigQuery.Tables.get(projectId, datasetId, tableId);
    return candidateId;
  } catch (e) {}
  
  try {
    const tables = BigQuery.Tables.list(projectId, datasetId, { maxResults: 20 });
    if (tables.tables && tables.tables.length > 0) {
      const preferredPatterns = ['trips', 'orders', 'events', 'data', 'stats', 'records'];
      let match = null;
      for (const pattern of preferredPatterns) {
        match = tables.tables.find(t => t.tableReference.tableId.toLowerCase().includes(pattern));
        if (match) break;
      }
      if (!match) match = tables.tables[0];
      
      return `${projectId}.${datasetId}.${match.tableReference.tableId}`;
    }
  } catch (listError) {}
  
  return null;
}

/**
 * Resolves the final publicDatasetId from the planner output.
 * - Toggle OFF: always null (ignore any LLM-hallucinated ID).
 * - Planner echoed the provided ID (normal case): use it as-is (already verified/user-specified).
 * - Planner returned a DIFFERENT ID: trust it only after BigQuery API verification;
 *   otherwise fall back to the verified options ID.
 */
function resolvePlannedPublicDatasetId_(parsedId, options) {
  if (!options.usePublicDataset) return null;
  const plannedId = (typeof parsedId === 'string') ? parsedId.trim() : '';
  if (plannedId && plannedId !== options.publicDatasetId) {
    const verified = verifyAndResolveTable(plannedId);
    if (verified) return verified;
    console.warn('[PublicDataset] Planner returned unverifiable ID "' + plannedId + '". Falling back to "' + options.publicDatasetId + '"');
  }
  return options.publicDatasetId || null;
}


function planAndGenerateData(userGoal, options) {
  // Step 0: If using public dataset and no ID specified, discover one using search grounding
  if (options.usePublicDataset && !options.publicDatasetId) {
    options.publicDatasetId = discoverPublicDataset(userGoal);
  }
  
  let prompt = buildPlanningPrompt(userGoal, options);
  if (options.importedMcpList && options.importedMcpList.length > 0) {
    options.importedMcpList.forEach((mcp, idx) => {
      const caps = mcp.capabilities ? mcp.capabilities.join(', ') : 'External system integration';
      const repoName = mcp.github_url.split('/').pop().replace(/\.git$/, '');
      prompt += `\n- **🔌 CUSTOM MCP SERVER TOOL #${idx + 1} AVAILABLE (${repoName})**:
    - A custom external MCP server has been imported by the user.
    - **Capabilities**: ${caps}
    - You MUST leverage these capabilities when generating the 'businessInstruction' and 'demoGuide' (prompts).
    - In 'businessInstruction', mention that the agent has access to these capabilities via a custom MCP toolset.
    - You MUST design at least TWO prompts (out of the 7 required) in the 'demoGuide' that explicitly ask the agent to perform tasks using these capabilities. Formulate business scenario logic where the agent reaches out to this custom tool to complete its autonomous task.
\n`;
    });
  }
  if (options.enableWorkspaceMcp) {
    prompt += `\n- **🔌 GOOGLE WORKSPACE MCP TOOLS AVAILABLE**:
    - The official Google Workspace MCP servers are enabled (Gmail, Drive, Calendar, Chat, People).
    - You MUST leverage these capabilities when generating the 'businessInstruction' and 'demoGuide' (prompts).
    - In 'businessInstruction', mention that the agent has access to Google Workspace data via Workspace MCP toolsets.
    - You MUST design at least TWO prompts (out of the 7 required) in the 'demoGuide' that explicitly ask the agent to perform tasks using these Workspace capabilities (e.g., searching for info in Drive, checking Calendar events, drafting emails, listing chat messages).
\n`;
  }
  if (options.enableComputerUse) {
    prompt += `\n- **🖥️ COMPUTER USE (BROWSER AGENT) AVAILABLE**:
    - The agent can operate a real headless web browser (Gemini 3.5 Flash Computer Use) to navigate, click, type, fill forms and extract data from sites that have NO API: competitor public pages, supplier/partner portals, government/regulatory sites, public data sources, and internal web apps. Browser runs happen as autonomous background tasks and the user can watch the live session.
    - You MUST leverage this capability when generating the 'businessInstruction' and 'demoGuide' (prompts).
    - In 'businessInstruction', mention that the agent can autonomously browse external websites via a browser-automation background task to gather or act on data that has no API.
    - You MUST design at least TWO prompts (out of the 7 required) in the 'demoGuide' that explicitly ask the agent to browse an external website or portal to accomplish the goal.
    - 🎯 CRITICAL - CHOOSE TASKS ONLY THE BROWSER CAN DO (avoid native-tool overlap): the agent ALSO has native tools for weather (lookup_weather), places / points-of-interest (search_places), directions & routes (compute_routes), and geocoding, plus BigQuery/Firestore for the demo's own internal data. If a "browser" prompt is really about weather, a place/POI, directions, or data already in the demo database, the model will call those native tools INSTEAD of the browser, and Computer Use will NOT be demonstrated (this is a real failure we have observed - e.g. "check the weather on weather.com" silently used lookup_weather). Therefore the TWO browser prompts MUST target EXTERNAL web content that has NO native tool: e.g. a competitor's public pricing / product-spec page, a distributor catalog, a regulatory / government filing or portal, public statistics, a news or company-announcement page, standards or documentation pages. DO NOT write weather, maps, places, or directions scenarios as the browser prompts.
    - 🎯 MAKE THE BROWSER INTENT UNAMBIGUOUS: name a SPECIFIC real website in each browser prompt and phrase it as opening/reading that site (e.g. "Open <real site> and find ...", or "Use the browser to look up ... on <real site>"), so it clearly calls for the browser rather than a native tool or the internal database.
    - 🚨 CRITICAL - USE ONLY REAL, PUBLICLY REACHABLE WEBSITES: every URL you put in a demo prompt MUST be a real site that is live on the public internet and reachable by an anonymous headless browser RIGHT NOW (no login/paywall/allowlist). The browser tool actually visits these URLs, so a fake domain makes the demo fail.
      - ❌ NEVER invent placeholder or fictional domains. Do NOT use example.com, example-supplier.co.jp, acme-corp.com, yourcompany.com, *.internal, or any made-up brand/portal hostname. These do not resolve and will break the browse.
      - ✅ Instead target real public sites that fit the domain, e.g.: official manufacturer / product catalog pages (that publish specs, availability or price without login), major e-commerce or distributor sites (e.g. amazon.com, or a real industrial-parts distributor's public catalog), price-comparison sites, government / regulatory portals (e.g. sec.gov, fda.gov, or the relevant national agency), standards bodies, public data sources (e.g. Wikipedia, official statistics portals), central-bank / FX / news sites, and public documentation pages. (Do NOT pick weather sites - the agent has a native weather tool that will be used instead of the browser.)
      - Re-frame "supplier/partner portal" scenarios so they hit a REAL public target: instead of "check stock on our supplier's portal (parts.example-supplier.co.jp)", write "look up the current price and availability of part <X> on <a real distributor's public catalog, e.g. mcmaster.com / digikey.com / the manufacturer's public product page>". Keep the business framing, but point at a site the browser can actually open.
      - If you cannot name a specific real URL for a scenario, use a web-search framing instead (e.g. "search the web for the current market price of <X> and report the top source") rather than fabricating a domain.
    - When synthesizing sample data, if you include an external URL field (e.g. source_url, product_page_url, reference_url), it MUST also be a real, currently-reachable public URL under the same rules above - never a fabricated domain. Prefer omitting the field over inventing a fake URL.
\n`;
  }
  if (options.enableManagedAgent) {
    prompt += `\n- **🤖 MANAGED AUTONOMOUS AGENT (ANTIGRAVITY) AVAILABLE**:
    - The demo agent can delegate long-running, multi-step work to a fully autonomous cloud agent running in an isolated sandbox with: a bash terminal, a persistent filesystem, code execution, a preinstalled data-science stack (pandas, numpy, web-page parsing) plus persistent pip/npm installs, Google Search + web page reading, direct BigQuery/Firestore access to the demo data, and professional deliverable skills (presentation decks, business documents, PDFs, and self-contained web pages). It works autonomously for tens of minutes: it plans in phases, checkpoints intermediate results to its filesystem, verifies each deliverable against a quality checklist, and iterates until the bar is met. Finished files are returned to the user as downloadable links. Long tasks run in the background and the agent announces completion.
    - You MUST leverage this capability when generating the 'businessInstruction' and 'demoGuide' (prompts).
    - In 'businessInstruction', mention that the agent can hand off deep autonomous work (research, building deliverables, iterative code work) to a managed autonomous agent and deliver finished files back to the user.
    - You MUST design at least TWO prompts (out of the 7 required) in the 'demoGuide' that showcase the autonomous agent, following BOTH patterns below:
      - **Pattern A (WEB RESEARCH + INTERNAL DATA SYNTHESIS)**: one prompt MUST require researching CURRENT external information on the public web (industry trends, competitor moves, market prices, regulations) AND combining it with the demo's own BigQuery data into a substantial written analysis. Phrase it so the answer is impossible without live web research (e.g. "Research the latest <industry> trends online and produce a competitive analysis against our own sales data").${ options.enableComputerUse ? ` Because the browser agent is ALSO enabled, Pattern A MAY additionally name ONE specific external page or portal to check interactively (e.g. a competitor's public pricing page) - the assistant will then operate its real browser live in the chat BEFORE handing off to the autonomous agent, which makes a strong combined showcase. Keep it to a single, quickly checkable page; the deep multi-source research still belongs to the autonomous agent.` : ''}
      - **Pattern B (COMPLEX LONG-HORIZON DELIVERABLE)**: one prompt MUST ask for finished, downloadable business output whose production requires SEQUENTIALLY DEPENDENT phases (real quantitative analysis of the internal data -> charts built from that analysis -> professional assembly), so the request genuinely deserves tens of minutes of autonomous work. Make it one of these two shapes, whichever fits the scenario better: (1) TWO complementary formats built from the same analysis - e.g. a board presentation deck PLUS a 2-page summary PDF for the field team, or a formal proposal document PLUS a one-page web briefing; or (2) a WORKING INTERACTIVE TOOL - a self-contained web app the user opens in a browser (e.g. a pricing / capacity / what-if simulator) whose coefficients come from the actual data analysis, plus a short document explaining the model. The prompt should sound like a real executive request and SHOULD state 1-2 explicit quality conditions in natural business language (e.g. "lead with the conclusion on the first page", "every number must be sourced from our data or a cited reference") - these conditions make the agent's self-review-and-rebuild loop visible in the demo. Patterns A and B MUST use DIFFERENT deliverable formats so the demo shows variety.${ crossOrgEnabled_() ? '\n      - **CROSS-DEPARTMENTAL DELIVERABLE (MANDATORY)**: the delegated mission MUST synthesize data owned by at least two departments and address its deliverable to the department (or executive) that owns the decision - framed as the journey summary of the demo narrative: what happened in each department, where the process stalled, and what was resolved. Because the Pattern A prompt occupies the final core slot, ITS deliverable also carries the NARRATIVE ARC finale duty: it MUST close with the quantified process outcomes of the demo narrative (before/after cycle time or lead time, items resolved, hand-offs completed).' : '' }${ (options.enableWorkspaceMcp || options.enableWorkspaceAuth) ? `
      - **MANDATORY WORKSPACE COMBINATION**: Google Workspace access is ALSO enabled for this demo, and the autonomous agent can act on the user's Workspace (save files to Drive as native Google Slides/Docs/Sheets, draft Gmail messages, post to named Google Chat spaces, create Calendar events). At least ONE of the two autonomous prompts MUST chain a Workspace action onto the deliverable so the demo showcases BOTH capabilities together, e.g.: "Research the latest industry trends, build the executive deck, save it to my Drive as Google Slides, and draft an email to the leadership team summarizing it" or "...and post the summary with the document link to the <team> Chat space, then set up a 30-minute review meeting on my calendar". Keep the Workspace actions realistic for the persona, and prefer DRAFT email wording (the agent creates drafts, it does not send unless explicitly told).` : ''}
    - 🎯 SLOT ASSIGNMENT (overrides the base 7-prompt distribution): put Pattern B in the Prompt 5 slot, REPLACING the large-scope background workflow prompt (the autonomous delegation itself runs in the background and demonstrates background execution plus completion announcements, so that story is preserved). Weave Pattern A into the Prompt 7 slot (End-to-End Strategic Automation): its web research + internal data synthesis IS the end-to-end showcase${ (options.enableWorkspaceMcp || options.enableWorkspaceAuth) ? ', and the MANDATORY WORKSPACE COMBINATION chain belongs there' : ''}. Do NOT merge Patterns A and B into a single prompt - the demo needs TWO distinct autonomous moments. Because slots 5 and 7 are now autonomous, fold the MANDATORY INTERACTIVE DASHBOARD prompt into slot 1 or 2 (make one of the foundation prompts ask for the browser-openable interactive overview dashboard, keeping its explicit open-in-browser signal) - the dashboard prompt must NOT displace slot 5 or 7 and must NOT be dropped.
    - Write both prompts as natural business-user requests, in the same language as the 'userGoal', woven into the demo storyline with the KPIs, entities, and business terms you generated (NEVER raw table or column names - the base NO TABLES/COLUMNS rule still applies to these prompts).
    - 🎯 CRITICAL - AVOID OVERLAP WITH LIGHTER TOOLS: the agent ALSO has fast inline tools (SQL queries, quick analysis, in-chat dashboards). If a prompt can be fully answered by querying the demo database and summarizing, the model will answer it inline and the autonomous agent will NOT be demonstrated. Therefore the TWO autonomous prompts MUST require at least one of: live web research, producing a downloadable file, or building-and-running code - things the inline tools cannot do.
\n`;
  }
  // M2 (v11.16): slot-budget arbitration. Only appended when 2-prompt
  // capability mandates exist that could overflow the 7 core slots; encore
  // items are the explicit overflow destination so no capability gets
  // crammed into a shared prompt or silently dropped (analysis gap 8.5).
  if (crossOrgEnabled_()) {
    const _mandateSources = (options.enableWorkspaceMcp ? 1 : 0)
      + (options.enableComputerUse ? 1 : 0)
      + ((options.importedMcpList && options.importedMcpList.length) ? options.importedMcpList.length : 0);
    if (_mandateSources >= 1) {
      prompt += `\n- **🎛 SLOT BUDGET & ENCORE PROMPTS (MANDATORY ARBITRATION)**: The 7 core prompts keep the base distribution (and any SLOT ASSIGNMENT overrides above). If the capability mandates above cannot ALL fit into the 7 core slots without cramming multiple showcase missions into a single prompt, do NOT dilute or silently drop any of them - generate up to THREE additional ENCORE prompts (positions 8-10) instead:
    - Each encore prompt showcases exactly ONE overflow capability as an epilogue or alternate-angle scene of the SAME business narrative (an encore may build on the core story's state; the core story must NEVER depend on an encore).
    - Tag every encore prompt by including the string "encore" in its "tags" array. Core prompts must NOT carry that tag.
    - Total demoGuide length: exactly 7 core items plus 0 to 3 encore items.
\n`;
    }
  }
  const response = callVertexAIWithRetry(prompt);
  
  let parsed;
  try {
    let jsonStr = response.replace(/```json\n?/g, '').replace(/```\n?/g, '').trim();
    jsonStr = repairTruncatedJson(jsonStr);
    parsed = JSON.parse(jsonStr);
  } catch (e) {
    throw new Error('Failed to parse AI response. Try reducing the row/table count.');
  }
  
  // Extract preview
  const dataPreview = [];
  if (parsed.tables) {
    for (const table of parsed.tables) {
      if (table.csvData) {
        const lines = table.csvData.trim().split('\n');
        const headers = parseCSVLine(lines[0]);
        const previewRows = lines.slice(1).map(line => {
          const values = parseCSVLine(line);
          const row = {};
          headers.forEach((h, i) => { row[h.trim().replace(/^"|"$/g, '')] = values[i] || ''; });
          return row;
        });
        dataPreview.push({
          tableName: table.tableName,
          headers: headers.map(h => h.trim().replace(/^"|"$/g, '')),
          rows: previewRows,
          totalRows: lines.length - 1
        });
      }
    }
  }
  // Generate in-memory simulated images using Vertex AI Agent Platform gemini-3-pro-image
  if (parsed.externalFiles && parsed.externalFiles.length > 0) {
    console.log('[ImageGen-Pipeline] Scanning externalFiles for dynamic images...');
    for (let i = 0; i < parsed.externalFiles.length; i++) {
      const file = parsed.externalFiles[i];
      if (file.mimeType && file.mimeType.startsWith('image/') && file.imagePrompt) {
        try {
          console.log(`[ImageGen-Pipeline] Generating simulated image for [${file.fileName}]...`);
          const finalImagePrompt = buildImagePromptWithRows_(file);
          const genResult = generateImageBase64WithRetry(finalImagePrompt);
          
          // JSONオブジェクトを直接拡張（In-Memory保存）
          file.base64Data = genResult.base64Data;
          file.mimeType = genResult.mimeType || file.mimeType;
          
          console.log(`[ImageGen-Pipeline] SUCCESS! Bound base64 image data to file: ${file.fileName}`);
        } catch (imgErr) {
          console.error(`[ImageGen-Pipeline] FAILED to generate image for ${file.fileName}: ${imgErr.message}`);
        }
      }
    }
  }

  // Density repair BEFORE validation: cheaply top up an under-dense
  // transaction table instead of failing the whole run (v11.25).
  expandThinTables_(parsed, options);

  // Validation and Clean-up
  validateGeneratedData(parsed, options.rowCount, options.dataProfile);

  return {
    tables: parsed.tables,
    businessInstruction: parsed.businessInstruction || parsed.systemInstruction || '',
    technicalInstruction: getTechnicalInstruction_(),
    systemInstruction: `${parsed.businessInstruction || parsed.systemInstruction || ''}\n\n${getTechnicalInstruction_()}`,
    referenceDate: parsed.referenceDate || Utilities.formatDate(new Date(), 'Asia/Tokyo', 'yyyy-MM-dd'),
    publicDatasetId: resolvePlannedPublicDatasetId_(parsed.publicDatasetId, options),
    agentShortName: parsed.agentShortName || null,
    oneSentenceSummary: parsed.oneSentenceSummary || null,
    operatingModel: parsed.operatingModel || null,
    demoGuide: parsed.demoGuide,
    externalFiles: parsed.externalFiles || [],
    appliedFactors: parsed.appliedFactors || null,
    firestore: parsed.firestore || null,
    dataPreview: dataPreview
  };
}


/**
 * Returns the static technicalInstruction constant.
 * This was extracted from the LLM generation prompt to save ~5,400 output tokens.
 * The content is injected into the systemInstruction at planAndGenerateData() time.
 * @returns {string}
 * @private
 */
function getTechnicalInstruction_() {
  const bt = String.fromCharCode(96).repeat(3);
  
  let inst = "Technical instructions for the agent regarding tool usage and system behavior.\n\n" +
    "=== MOST IMPORTANT RULE: OUTPUT PLACEMENT ===\n" +
    "Any text you write in the SAME response as a function_call (tool call) is HIDDEN from the user. " +
    "It goes to 'thinking' and the user NEVER sees it. Therefore:\n" +
    "(1) When calling ANY tool, write ONLY a short progress line like '🔍 Analyzing...' — nothing else.\n" +
    "(2) Your full report, A2UI cards, images, and chips MUST go in a SEPARATE response that has ZERO tool calls.\n" +
    "=== END MOST IMPORTANT RULE ===\n\n" +
    
    "4. **VISUALIZATION**: Instruct the agent to use the 'generate_image' tool to create a visual representation of its findings. " +
    "This visual MUST be in the style of a professional business document or slide (e.g., an Executive Summary card, a high-level business infographic) " +
    "that summarizes the insights. " +
    "**NO IMAGE TOOL RAW RESPONSE OUTFALL (CRITICAL)**: When you call 'generate_image', the system automatically handles the image rendering. You MUST NEVER copy, reference, or output the tool's JSON return payload (e.g., `{'status': 'success', 'detail': '...'}`) in your conversational text response. Do NOT write statements like 'Image generated successfully' or repeat the status dictionary. Keep your text focused purely on business insights.\n" +
    "4b. **INTERACTIVE DASHBOARD**: Instruct the agent that it can publish a full interactive HTML dashboard (opened in a browser tab) via the 'publish_dashboard' tool whenever the user asks for a dashboard, an executive dashboard, or an interactive/clickable report. The agent first gathers aggregated numbers (e.g. via execute_sql), then authors ONE complete self-contained HTML document (inline CSS/JS, charts from a CDN, data embedded as a JSON snapshot, interactive tabs/filters/dark mode, all labels in the user's language), calls 'publish_dashboard', and presents the returned dashboard_url as a Markdown link like [Open Executive Dashboard](URL) — never a bare URL, never an A2UI/openUrl button. The dashboard is a point-in-time snapshot. As with images, NEVER output the tool's raw JSON return payload.\n" +
    "5. Instruct to wait for user input before acting, but be persistent in error recovery.\n" +
    "6. **TRANSPARENCY & GROUNDING (CRITICAL)**: Instruct the agent to be highly transparent about its reasoning, " +
    "explicitly mentioning which tables and files it is consulting and what specific values it found, " +
    "to ensure the user can trace its logic back to the source data.\n" +
    "6b. **KNOWLEDGE CATALOG / METADATA-DRIVEN ANALYSIS (CRITICAL)**: Instruct the agent that it has access to the Knowledge Catalog (Dataplex) MCP tools " +
    "and MUST ground its analysis in metadata before composing BigQuery queries. Mandatory workflow: " +
    "(a) for ANY exploratory or discovery question (e.g. 'what data do we have', 'what can you analyze', 'find data useful for X'), it MUST call 'search_entries' FIRST — before 'list_table_ids' / 'list_dataset_ids' — to discover and rank the relevant assets; " +
    "(b) it MUST use 'lookup_entry' / 'lookup_context' (NOT 'get_table_info') to read column meanings, units, allowed values, data classifications, and table relationships (join keys); " +
    "(c) only then build the BigQuery query, selecting the correct tables and join keys based on the catalog metadata. Use 'get_table_info' only to confirm exact column types right before writing SQL, or during SQL error recovery. " +
    "If a catalog call returns nothing right after provisioning (metadata harvest can lag a few minutes), fall back to inspecting tables directly and retry catalog discovery later.\n" +
    "7. **FIRESTORE INTEGRATION (CRITICAL)**: Explicitly instruct the agent that it has access to a live operational database via MCP " +
    "and that it should proactively write updates back to resolve issues.\n" +
    "8. **CONFIRMATION WORKFLOW (CRITICAL)**: Explicitly instruct the agent that whenever a user asks to insert, update, delete, or merge data in BigQuery or Firestore, " +
    "the agent MUST NEVER execute the operation immediately. Instead, the agent MUST ALWAYS present a clear summary of the proposed database action " +
    "and ask the human user for explicit confirmation using <a2ui-json> tags. " +
    "When the confirmation covers MULTIPLE independently-actionable items (e.g. a batch of draft orders), the card MUST let the user select WHICH items to approve " +
    "(MultipleChoice variant 'checkbox' or per-row CheckBox bound to /form paths, with the confirm Button carrying the selections) — all-or-nothing batch confirmations are forbidden.\n" +
    "9. **OUTPUT PLACEMENT (HIGHEST PRIORITY — RULE #0)**: When you call a tool, any text you include in the SAME response as the tool call will be hidden from the user. " +
    "All analytical dashboards, insights, and A2UI suggestion chips MUST appear in your FINAL response that contains NO tool calls.\n\n" +
    
    "10. **A2UI INTERACTIVE UI PATTERNS (MANDATORY — NEVER SKIP)**: You MUST ALWAYS use A2UI interactive components when presenting analytical results, " +
    "entity profiles, workflow plans, or structured data. Plain-text markdown tables and bullet lists are FORBIDDEN for these use cases. " +
    "If you find yourself writing a markdown table or a numbered list of data, STOP and convert it to an A2UI Card instead.\n\n" +
    
    "**ANALYTICAL RESULT CARD TEMPLATE (MANDATORY)**:\n" +
    "When presenting query results, KPIs, or entity summaries, wrap them in an A2UI Card. " +
    "Use surfaceId matching the analysis type (e.g. 'fleet-audit', 'cost-analysis', 'entity-profile'), and make it UNIQUE per card: " +
    "when rendering ANOTHER card of a type already shown earlier in the conversation, append a short distinguishing suffix " +
    "(entity or sequence, e.g. 'batch-editor-sakura', 'cost-analysis-2'). NEVER reuse a surfaceId from a previous turn unless you are " +
    "intentionally updating or deleting that exact card: the client anchors a surfaceId to the message where it FIRST rendered, so a " +
    "reused id silently overwrites the OLD card and renders NOTHING in the current turn. " +
    "Minimal structure:\n" +
    "[\n" +
    "  { \"id\": \"card_root\", \"component\": { \"Card\": { \"children\": { \"explicitList\": [\"card_title\", \"card_divider\", \"card_body\"] } } } },\n" +
    "  { \"id\": \"card_title\", \"component\": { \"Text\": { \"text\": { \"literalString\": \"[Title]\" }, \"usageHint\": \"title\" } } },\n" +
    "  { \"id\": \"card_divider\", \"component\": { \"Divider\": {} } },\n" +
    "  { \"id\": \"card_body\", \"component\": { \"Column\": { \"children\": { \"explicitList\": [\"kpi_row\", \"detail_list\"] } } } },\n" +
    "  { \"id\": \"kpi_row\", \"component\": { \"Row\": { \"children\": { \"explicitList\": [\"kpi_1\", \"kpi_2\", \"kpi_3\"] }, \"distribution\": \"spaceEvenly\" } } },\n" +
    "  { \"id\": \"kpi_1\", \"component\": { \"Column\": { \"children\": { \"explicitList\": [\"kpi_1_val\", \"kpi_1_lbl\"] } } } },\n" +
    "  { \"id\": \"kpi_1_val\", \"component\": { \"Text\": { \"text\": { \"literalString\": \"[Value]\" }, \"usageHint\": \"title\" } } },\n" +
    "  { \"id\": \"kpi_1_lbl\", \"component\": { \"Text\": { \"text\": { \"literalString\": \"[Label]\" }, \"usageHint\": \"caption\" } } }\n" +
    "]\n" +
    "Add more KPIs, Lists, and detail Rows as needed.\n" +
    "**TABS & MODAL THRESHOLDS (MANDATORY)**: A card with 3+ logical sections OR 8+ detail rows MUST use Tabs instead of one long scroll. " +
    "When showing Top-N of a larger result set, never cram the remainder into a footnote Text — put the full list in a Modal opened by a 'view all' button.\n" +
    "**NO PSEUDO-TABLES (CRITICAL)**: Never pack multiple metrics into ONE Text component using '|' or '/' separators. " +
    "One entity per Row, one metric per Column/Text, so values align visually.\n" +
    "**WHAT-IF SIMULATION CARD (WOW MOMENT)**: When an analysis result depends on a tunable parameter (threshold, budget, quantity), follow the result card with a what-if card: " +
    "a Slider (label, minValue/maxValue, value bound to a /form path) plus a primary Button whose action context carries the /form value to request recalculation. " +
    "Strongly recommended for critical-threshold findings (safety stock, alert thresholds).\n\n" +
    
    "**WHEN TO USE A2UI CARDS vs TEXT**:\n" +
    "- ALWAYS A2UI Card: Query results, KPI dashboards, entity profiles, data comparisons, workflow plans with action buttons, confirmation dialogs\n" +
    "- Text OK: Simple conversational replies, error messages, progress updates during tool calls, single-sentence answers\n\n" +
    
    "Decisions:\n" +
    "(I) Workflow Execution Plan: Use sequential number and status emojis (✅ Done, 🔄 Running, 🕒 Pending, 🚨 Action Required) for step timeline. " +
    "Replace technical tags like [AUTO] or [APPROVAL REQUIRED] with localized friendly text (e.g. System Automated or Requires Your Approval).\n\n" +
    
    "(J) Dynamic Multi-Entity Batch Editor (Side-by-Side Comparison Form):\n" +
    "Each row MUST be a Column containing (1) a main Row and (2) an annotation Text component (usageHint: 'caption') below it.\n" +
    "Inside the main Row: Show original raw product/entity name and raw quantity stacked in the Left Column.\n" +
    "Show a MultipleChoice component (variant: 'chips' or 'dropdown') in the Middle Column to select the AI-proposed mapping SKU/target.\n" +
    "Show the proposed quantity in the Far-right Column with a standard TextField.\n" +
    "Below the main Row: Show a brief annotation Text explaining the recommendation reason.\n\n" +
    
    "**BATCH EDITOR ROW JSON TEMPLATE (MANDATORY)**:\n" +
    "When rendering the Batch Editor, you MUST use the following component structure for each row `i` (replace `i` with the actual 0-based index). " +
    "Ensure all component IDs are completely unique (e.g., by appending `_i` to each ID). " +
    "You MUST wrap the entire A2UI JSON payload in <a2ui-json> tags. " +
    "Here is the mandatory layout structure for a single row `i`:\n" +
    "[\n" +
    "{\n" +
    "  \"id\": \"row_container_i\",\n" +
    "  \"component\": {\n" +
    "    \"Column\": {\n" +
    "      \"children\": { \"explicitList\": [\"main_row_i\", \"reason_text_i\"] }\n" +
    "    }\n" +
    "  }\n" +
    "},\n" +
    "{\n" +
    "  \"id\": \"main_row_i\",\n" +
    "  \"component\": {\n" +
    "    \"Row\": {\n" +
    "      \"children\": { \"explicitList\": [\"left_stack_i\", \"sku_select_i\", \"qty_field_i\"] },\n" +
    "      \"distribution\": \"spaceBetween\",\n" +
    "      \"alignment\": \"center\"\n" +
    "    }\n" +
    "  }\n" +
    "},\n" +
    "{\n" +
    "  \"id\": \"left_stack_i\",\n" +
    "  \"component\": {\n" +
    "    \"Column\": {\n" +
    "      \"children\": { \"explicitList\": [\"orig_name_i\", \"orig_qty_i\"] },\n" +
    "      \"distribution\": \"start\",\n" +
    "      \"alignment\": \"start\"\n" +
    "    }\n" +
    "  }\n" +
    "},\n" +
    "{\n" +
    "  \"id\": \"orig_name_i\",\n" +
    "  \"component\": {\n" +
    "    \"Text\": {\n" +
    "      \"text\": { \"literalString\": \"[Original Item Name, e.g., 'エアコン5馬力']\" },\n" +
    "      \"usageHint\": \"body\"\n" +
    "    }\n" +
    "  }\n" +
    "},\n" +
    "{\n" +
    "  \"id\": \"orig_qty_i\",\n" +
    "  \"component\": {\n" +
    "    \"Text\": {\n" +
    "      \"text\": { \"literalString\": \"[Original Qty, e.g., 'Qty: 2']\" },\n" +
    "      \"usageHint\": \"caption\"\n" +
    "    }\n" +
    "  }\n" +
    "},\n" +
    "{\n" +
    "  \"id\": \"sku_select_i\",\n" +
    "  \"component\": {\n" +
    "    \"MultipleChoice\": {\n" +
    "      \"label\": { \"literalString\": \"[Select SKU]\" },\n" +
    "      \"options\": [\n" +
    "        { \"value\": \"SKU_CODE_A\", \"label\": { \"literalString\": \"[SKU_CODE_A]\" } },\n" +
    "        { \"value\": \"SKU_CODE_B\", \"label\": { \"literalString\": \"[SKU_CODE_B]\" } }\n" +
    "      ],\n" +
    "      \"maxAllowedSelections\": 1,\n" +
    "      \"variant\": \"chips\",\n" +
    "      \"selections\": { \"path\": \"/form/item_i_selected_sku\" }\n" +
    "    }\n" +
    "  }\n" +
    "},\n" +
    "{\n" +
    "  \"id\": \"qty_field_i\",\n" +
    "  \"component\": {\n" +
    "    \"TextField\": {\n" +
    "      \"label\": { \"literalString\": \"[Qty]\" },\n" +
    "      \"text\": { \"path\": \"/form/item_i_qty\" },\n" +
    "      \"textFieldType\": \"shortText\"\n" +
    "    }\n" +
    "  }\n" +
    "},\n" +
    "{\n" +
    "  \"id\": \"reason_text_i\",\n" +
    "  \"component\": {\n" +
    "    \"Text\": {\n" +
    "      \"text\": { \"literalString\": \"💡 [Recommendation reason, e.g., 'Direct successor (95% match)']\" },\n" +
    "      \"usageHint\": \"caption\"\n" +
    "    }\n" +
    "  }\n" +
    "}\n" +
    "]\n\n" +
    
    "11. **SUGGESTION CHIPS (CRITICAL)**: At the END of EVERY response, you MUST append a lightweight A2UI suggestion chip bar using surfaceId 'suggestions' and root='root' containing a Row of 3-4 Buttons with sendText actions. The chip block MUST be COMPLETE: a single <a2ui-json> block containing BOTH the beginRendering message AND the surfaceUpdate message with all Button components — never emit beginRendering alone. NEVER write any plain text or markdown headers (like \"Next Actions\", \"💡 Next Actions\", or other localized header equivalent) before the suggestions block; the system will automatically render the appropriate header. " +
    "**BUTTON SCHEMA CONFORMANCE (CRITICAL)**: NEVER nest components inside a Button's 'child' property. 'child' MUST always be a flat string pointing to the ID of a separately defined Text component, and that Text component MUST be included in the SAME surfaceUpdate components array as its Button — a Button whose label Text component is missing renders as a BLANK button in the UI. Before finishing any A2UI block, verify every Button's child id has a matching Text component in the same block.\n" +
    "**A2UI CARD INTERACTION EXCEPTION (STRICT RULE)**: When your response already contains a major interactive A2UI card featuring its own control buttons " +
    "(such as the Welcome Card onboarding buttons, the Analysis Plan pre-flight card buttons like Run inline / Run in background / Adjust, or the Workflow Execution Plan mode selection buttons like Immediate/Background/Scheduled), " +
    "you **MUST NOT** output any suggestion chip bar at the bottom of your response. The card's own control buttons are sufficient. " +
    "If you output suggestion chips in these turns, they will duplicate the card buttons and fail to render the '💡 Next Actions' title. " +
    "Suggestion chips MUST only appear in normal conversational or analytical turns where no other interactive button-heavy cards are present.\n" +
    "**ANTI-DUPLICATION RULE (CRITICAL)**: Suggestion chips MUST never duplicate or mirror any button label in the same response turn. " +
    "Suggestion chips must always offer distinct, deep-dive analytical next steps.\n\n" +
    
    "12. **WELCOME CARD (FIRST INTERACTION)**: When the user sends an initial greeting (e.g., 'Hi', 'Hello'), you **MUST NOT** call any tools, databases, or BigQuery under any circumstances. " +
    "Calling tools on the first greeting turn completely hides and breaks the onboarding card rendering. " +
    "You MUST immediately respond in the very first turn by writing ONE short line of plain-text greeting in the user's language FIRST, and THEN the rich A2UI onboarding card using surfaceId 'welcome-card' and NO suggestion chips at the bottom (the card's own buttons are sufficient). " +
    "The one-line plain-text greeting is MANDATORY and must appear in addition to the card: a UI-only response (an A2UI card with NO accompanying plain text) is NOT rendered by the client and shows a blank turn. " +
    "Never execute queries or tool calls until the user explicitly requests analysis. The onboarding card must include your role title, a Divider, a List of key capabilities with Lucide icons, " +
    "a Divider, and exactly 3 action Buttons.\n" +
    "**BUTTON SCHEMA CONFORMANCE (CRITICAL)**: When generating A2UI JSON payloads, you MUST ALWAYS use strict standard JSON syntax. " +
    "Under no circumstances should you use single quotes or omit quotes for keys. Keys and string values MUST always be enclosed in standard double quotes. " +
    "Each Button component's action MUST strictly follow standard JSON structure:\n" +
    "{\n" +
    "  \"action\": {\n" +
    "    \"name\": \"sendText\",\n" +
    "    \"context\": [\n" +
    "      {\n" +
    "        \"key\": \"text\",\n" +
    "        \"value\": { \"literalString\": \"[Localized Button Label]\" }\n" +
    "      }\n" +
    "    ]\n" +
    "  }\n" +
    "}\n" +
    "Ensure all keys and string values are enclosed in standard double quotes to comply with strict standard JSON specifications. Use surfaceId 'welcome-card'.\n\n" +
    
    "**CODE EXECUTION MIX PREVENTION (CRITICAL)**: When you execute Python code inside a fenced code block (using " + bt + "python ... " + bt + "), " +
    "you **MUST NEVER** combine, mix, or output any other JSON tool calls (like execute_sql, get_table_info) in the SAME response turn. " +
    "Mixing python code blocks with JSON tool calls triggers a fatal MALFORMED_FUNCTION_CALL system crash. " +
    "You MUST run the Python code alone first, receive its result, and only then issue the next tool call in a separate turn. " +
    "After this initial card, do NOT show the welcome card again in the same session unless the user explicitly requests a reset.\n\n" +
    "**A2UI SCHEMA VALIDATION: usageHint CONSTRAINT (CRITICAL)**: The 'usageHint' property is ONLY allowed inside 'Text' components. You MUST NEVER place 'usageHint' inside any other component type (such as 'Button', 'Row', 'Column', 'Card', 'List', 'Divider', 'Icon', 'MultipleChoice', 'TextField'). Placing 'usageHint' in these non-Text components violates the schema and will cause the UI to crash and fail to render.\n\n" +
    "**A2UI ICON VALIDATION (CRITICAL)**: When using 'Icon' components or specifying 'icon' inside components like 'Button', you MUST ONLY use one of the following allowed icon names. Using any other name (such as 'analytics', 'dashboard', 'chart', 'database', 'check_circle', 'lucide:*') is STRICTLY FORBIDDEN and will cause a fatal validation crash. The allowed icon names are:\n" +
    "['accountCircle', 'add', 'arrowBack', 'arrowForward', 'attachFile', 'calendarToday', 'call', 'camera', 'check', 'close', 'delete', 'download', 'edit', 'event', 'error', 'favorite', 'favoriteOff', 'folder', 'help', 'home', 'info', 'locationOn', 'lock', 'lockOpen', 'mail', 'menu', 'moreVert', 'moreHoriz', 'notificationsOff', 'notifications', 'payment', 'person', 'phone', 'photo', 'print', 'refresh', 'search', 'send', 'settings', 'share', 'shoppingCart', 'star', 'starHalf', 'starOff', 'upload', 'visibility', 'visibilityOff', 'warning']\n\n" +
    "13. **VERTICAL SPACING / SPACER HACK (CRITICAL)**: The tab bar of a Tabs component and its content Column may render extremely close to each other with insufficient vertical space. " +
    "To insert an appropriate vertical gap below the tab bar, you MUST insert a dummy Text component acting as a spacer ONLY as the very first child of the tab content Column (the Column bound to the tab's child ID). " +
    "The spacer component MUST have a single space \" \" as its literalString text and usageHint 'body'. For example:\n" +
    "{\n" +
    "  \"id\": \"[Unique_Spacer_ID]\",\n" +
    "  \"component\": {\n" +
    "    \"Text\": {\n" +
    "      \"text\": { \"literalString\": \" \" },\n" +
    "      \"usageHint\": \"body\"\n" +
    "    }\n" +
    "  }\n" +
    "}\n" +
    "You MUST ONLY use this spacer hack as the first child of a tab content Column. Do NOT place this spacer in any other standard Column, Row, or Dashboard layout where standard spacing is already optimal, to avoid creating unnecessary blank gaps.";
    
  return inst;
}

/**
 * M2 cross-org pack kill switch. Setting Script Property
 * DISABLE_CROSSORG_PACK=1 blanks every cross-departmental prompt insertion at
 * once - an admin rollback lever (no redeploy), NOT a user-facing option.
 */
function crossOrgEnabled_() {
  return !SCRIPT_PROPS.getProperty('DISABLE_CROSSORG_PACK');
}

function buildPlanningPrompt(userGoal, options) {
  const profile = getDataProfile_(options.dataProfile || 'standard');
  const maxRows = Math.min(options.rowCount || profile.defaultRowCount, 150);
  const todayStr = Utilities.formatDate(new Date(), 'Asia/Tokyo', 'yyyy-MM-dd');
  const publicDatasetInfo = options.usePublicDataset && options.publicDatasetId 
    ? `- RELATED PUBLIC DATASET (ENRICHMENT ONLY): ${options.publicDatasetId}
       * ROLE: This dataset serves as EXTERNAL CONTEXT (e.g., weather, statistics) to enrich the core business data.
       * CONSTRAINT: DO NOT use this dataset as a replacement for core business operations (e.g., do not use public orders/customers if you are generating a retail demo).
       * JOIN STRATEGY: Link via common attributes like 'zip_code', 'category', 'region', or 'date' rather than internal system IDs.
       * OUTPUT FIELD (MANDATORY): In your JSON response, set "publicDatasetId" to EXACTLY this ID. Do NOT invent or substitute a different dataset.
       * DEMO GUIDE REQUIREMENT (MANDATORY): At least ONE prompt in 'demoGuide' MUST explicitly ask the agent to enrich the analysis by combining the synthetic tables with this external public dataset (e.g., correlate internal metrics with the external context it provides). Design the JOIN keys in the synthetic tables so this prompt produces meaningful results.`
    : `- IMPORTANT: NO public dataset should be used for this demo. Focus ONLY on synthetic tables below. Do NOT attempt to JOIN with external public-data. In your JSON response, set "publicDatasetId" to null.`;

  // v11.12 (P10): the Target Persona selected in the wizard becomes the demo's
  // protagonist across every generated artifact. Empty string = no persona
  // selected = the prompt is unchanged from pre-persona behavior.
  const anchorPersonaText = sanitizePersonaText_({
    label: options.targetPersona || '',
    description: options.targetPersonaDesc || ''
  });
  const anchorPersonaBlock = anchorPersonaText
    ? '\n## Anchor Persona (MANDATORY)\nThe demo creator selected the primary user of this agent: ' + anchorPersonaText + '. This persona is the PROTAGONIST of the demo: (a) the businessInstruction MUST define the agent as this persona\'s process operator; (b) demoGuide Prompt 1 MUST open from this persona\'s daily situation; (c) any autonomous delegation deliverable MUST be addressed to this persona\'s decision chain; (d) human-approval gates SHOULD be decisions this persona (or their direct manager) owns.\nPRECEDENCE: even when the scenario suggests a different natural protagonist (e.g., the manager or supervisor of the function), the SELECTED persona still wins - keep the selected persona as the protagonist and cast other roles as hand-off counterparts. Do NOT substitute a similar-but-different job title for the selected persona.\n'
    : '';
  const anchorRotationNote = anchorPersonaText
    ? ' If an Anchor Persona is defined above, keep that persona as the protagonist of ALL prompts and rotate other personas ONLY as hand-off counterparts (the roles the process flows to or from), never replacing the protagonist\'s thread.'
    : '';

  // M4 (P17-lite): ground synthetic data in the researched company's real
  // scale. Backticks stripped so runtime facts can never break the template
  // pipeline downstream. Absent facts = prompt unchanged.
  let quantFactsBlock = '';
  if (options.quantFacts && options.quantFacts.facts && Object.keys(options.quantFacts.facts).length) {
    const bt = String.fromCharCode(96);
    const factsText = JSON.stringify(options.quantFacts.facts, null, 1).split(bt).join('');
    const qfName = String(options.quantFacts.companyName || 'the company').split(bt).join('');
    quantFactsBlock = '\n## Data Grounding (verified real-world scale)\nThe following quantitative facts about ' + qfName + ' were gathered from public sources during domain research. Reflect them in the generated data so the demo feels like THIS organization: master-table sizes, regional distribution, product-category mix, and transaction volumes should be plausible for an organization of this scale, scaled down proportionally to the row-count budget (note the scaling ratio in table descriptions where helpful, e.g. "representative sample of ~1,050 stores"). Apply ONLY if the Business Problem is about this company; ignore otherwise.\n' + factsText + '\n';
  }

  // ---- M2 cross-org pack (v11.16) ----
  // Every block below is blanked by the DISABLE_CROSSORG_PACK kill switch.
  const CROSSORG = crossOrgEnabled_();
  const encoreNote = CROSSORG
    ? ' (7 CORE prompts; up to 3 additional prompts tagged "encore" are allowed ONLY under the SLOT BUDGET arbitration rule when capability mandates cannot fit the core slots)'
    : '';
  // P5: one process instance woven through the existing slot structure, with
  // a quantified-outcome finale (analysis issues 7 and critique 4).
  const narrativeArc = CROSSORG ? `
    0. **NARRATIVE ARC (MANDATORY)**: All 7 core prompts MUST follow ONE end-to-end business process instance (e.g., one problematic order, one flagged application) across the organization - each prompt builds on the state changes made by the previous one, while still fulfilling its slot's functional requirement below. The slot structure (including any SLOT ASSIGNMENT overrides) stays unchanged; the arc is WOVEN THROUGH the slots, never replaces them. The final core prompt MUST make the agent present the full journey with QUANTIFIED process outcomes (before/after cycle time, items resolved, hand-offs completed).` : '';
  // P9: autonomy backstage, decisions onstage (analysis critique 2).
  // v11.17: reworded - the first cut collided with the NO-EXPLICIT-HITL rule
  // (prompts may not contain approval wording), so the planner ignored it.
  // Decision beats must come from TASK DESIGN, not prompt wording.
  const hitlChoreo = CROSSORG ? `
    2c. **FOREGROUND/BACKGROUND CHOREOGRAPHY (MANDATORY)**: At least TWO core prompts must be DESIGNED so the agent's own confirmation flow fires on stage: give those prompts tasks whose data contains threshold-crossing or exception items (per the workflow's DECISION POINTS), so the agent - following its own rules - must present an approval card with options and evidence, wait for the one-click human decision, and visibly change the operational-database state. The NO-EXPLICIT-HITL rule above still applies: do NOT write approval requests into the prompt text; the decision beat comes from the agent's behavior on that data, never from the wording. Reserve background execution for (a) long autonomous delegations, (b) large batch runs, (c) scheduled jobs; everything else runs in the foreground showing reasoning and intermediate results.` : '';
  // P3: cross-departmental mandate for BOTH archetypes, with industry pattern
  // variety (critique 5) and a single-department escape hatch.
  const crossOrgMandate = CROSSORG ? `
- **🏢 CROSS-DEPARTMENTAL MANDATE (applies to BOTH archetypes)**: The agent is not a single team's assistant - frame it as the company's process operator working across departments on shared core-system data.
    - Type A queues MUST contain tasks whose resolution requires touching data owned by at least TWO different departments, with each hand-off represented as a state transition the agent performs on behalf of the sending department and visible to the receiving one.
    - Type B insights MUST quantify impact across at least TWO departments and route each proposal to the department that owns the decision.
    - Vary the organizational shape by industry instead of repeating one template - examples: manufacturing procurement -> production -> quality; banking sales-branch -> underwriting -> compliance; retail store -> supply chain -> finance; **approval pre-review** (the agent reviews a submission against the RECEIVING department's own rules BEFORE it is submitted); **multi-department plan refinement** (a draft plan is validated against other departments' actual data and thresholds, then routed to each owner for approval).
    - ESCAPE HATCH: where the business problem plausibly involves only ONE department, do NOT force departments into it - model the hand-off with an adjacent supporting function (e.g., support -> billing, support -> product quality), or keep it single-team if even that feels unnatural. The user's goal always wins.` : '';
  // P1: shared core-system data model + department-owned rules as data
  // (analysis issues 2/8; rules-as-data underpins the pre-review pattern).
  const crossOrgDataModel = CROSSORG ? `
- **SHARED CORE-SYSTEM DATA MODEL (MANDATORY)**: Model the tables as a slice of the company's core system of record (ERP/CRM/WMS-like), NOT as one team's private dataset.
    1. At least ONE transactional table MUST be read and written by two or more distinct departments for different purposes (e.g., orders: created by Sales, fulfilled by Logistics, invoiced by Finance). Add an "owning_department" or equivalent dimension where natural.
    2. **Department-owned rules as data**: generate at least ONE table (or clearly described catalog entry) holding rules/thresholds/checklists OWNED by one department that ANOTHER department's workflow must consult (e.g., procurement approval rules that sales submissions are pre-checked against; credit limits owned by Finance that order intake must respect). The rules table MUST still connect to the rest of the schema: include the key column(s) its rules apply to (e.g., category_id, product_id, customer_rank, department) named EXACTLY as in the tables they reference - the NO ISOLATED TABLES rule applies to rules tables too.
    3. At least ONE Audit Seed MUST be a **cross-departmental discrepancy**: a mismatch invisible inside any single department's view, detectable only by joining data across departmental usage contexts.
    (ESCAPE HATCH: for a genuinely single-department goal, scope all three to the department and its closest supporting function instead.)` : '';
  // P2: organizational actors inside the workflow definition (issue 4).
  const crossOrgWorkflow = CROSSORG ? `
- **ORGANIZATIONAL ACTORS (MANDATORY)**: Each STEP must name the department or role responsible in the real-world process (e.g., Procurement -> Warehouse -> Accounts Payable -> Treasury), and each DECISION POINT must state WHICH department's rule it enforces. The workflow MUST cross at least TWO departments, with each hand-off represented as a state transition performed on behalf of the sending department and visible to the receiving one. Align HITL GATES with these department boundaries (threshold breaches and exceptions are approved by the receiving department's owner). ESCAPE HATCH: for a genuinely single-department goal, use the adjacent supporting function instead.` : '';

  return `You are a versatile data analyst and BigQuery expert capable of generating realistic datasets for ANY industry or business function.
Design and generate a demo dataset based on the following business problem.

**CRITICAL LANGUAGE RULE (MANDATORY)**: Detect the language used in the "Business Problem" below. You MUST generate ALL outputs (including table descriptions, column descriptions, CSV data string values, person names, suggestedGoal, businessInstruction, appliedFactors, and demoGuide prompts) in that **EXACT SAME LANGUAGE**. If the Business Problem is in English, the entire JSON response MUST be in English. If in Japanese, the entire response MUST be in Japanese. Do NOT mix languages, and do NOT default to Japanese unless the input is in Japanese.

**DOMAIN ADAPTATION**: Carefully analyze the business problem below to identify the industry, job function, and operational context. Adapt ALL data generation (table structures, column names, values, relationships) to match that specific domain. Do not default to generic examples or assume a particular industry unless explicitly stated.

## AGENT ARCHETYPE & FIRESTORE STRATEGY (CRITICAL)
You MUST classify the demo scenario into one of the following two agent archetypes. **In both cases, Firestore is MANDATORY** and must be populated to represent a live operational console, but the schema must adapt:

### Type A: Automated Transactional Operator (Write-Heavy / Queue-Driven)
- **When to choose**: The workflow naturally involves resolving transactional discrepancies, auditing individual records (invoices, claims, disputes), managing status-based task queues, or processing non-structured inputs (e.g., hand-written order sheets, prescription images, inspection sheets) that require master/history DB lookup and human-in-the-loop review before database execution.
- **Firestore Strategy**: Define the collection as a **Workflow Task Queue / Transaction Queue** (e.g., 'order_tasks', 'prescription_queues', 'dispute_resolutions'). Documents MUST represent individual tasks with a status field (PENDING, IN_PROGRESS, RESOLVED, ESCALATED) and a workflow_state object tracking progress.
- **BigQuery DB Strategy (CRITICAL for Non-structured input scenarios)**: If the goal involves processing non-structured inputs (like images or PDFs), you MUST design and generate a linked set of tables: (1) Master Tables (e.g., products, customers), (2) History Tables (e.g., order_history) to serve as the 'grounding source' for AI reasoning and ambiguity resolution, (3) Inventory/Lead-time Tables (if applicable) to calculate dynamic parameters like delivery lead times, and (4) Transaction Tables (e.g., orders) as the final write destination.
- **Instruction Strategy**: 
  - Generate a step-by-step workflow pipeline: SCAN (OCR/Extraction) ➔ RESOLVE (Master/History DB lookup & ambiguity resolution) ➔ PRESENT (A2UI dynamic form) ➔ EXECUTE (DB write & allocation) ➔ REPORT.
  - Instruct the agent to proactively query the history tables to auto-complete and resolve un-clear or hand-written entity names/quantities.
  - Instruct the agent to present the resolved items using the **(J) Dynamic Multi-Entity Batch Editor** A2UI pattern.
    - **ITEM-LEVEL SKU DECOMPOSITION (ABSOLUTELY MANDATORY)**: The agent MUST NOT treat the entire handwritten order text as a single block. It MUST split/decompose the text into **individual SKU line items (separate rows for each product)**.
    - **AI-RECOMMENDED SKU/ENTITY SELECTION (STRICTLY REQUIRED)**: In the Middle Column of each row in the Batch Editor, the agent **MUST NOT use a raw \`TextField\` for mapping input**. The agent **MUST use a \`MultipleChoice\` component (variant: "chips" to render as horizontal selection buttons, or "dropdown" if there are more than 3 options, with maxAllowedSelections: 1)** bound to \`item_i_selected_sku\` (e.g. \`item_0_selected_sku\`) to allow the user to select the mapped SKU/entity.
    - **ANNOTATION & RECOMMENDATION REASON (MANDATORY)**: Below each row's main components (Original, Selection, Qty), the agent **MUST include a \`Text\` component (usageHint: "caption")** that dynamically displays the reason why the AI recommended these specific SKUs (e.g., "💡 SKU_A is the direct successor (95% match); SKU_B is a similar alternative").
    - **LOCALIZATION RULE (CRITICAL)**: All literalString values in A2UI component labels, headers, options, and buttons MUST be translated dynamically into the user's interaction language (or the language of the userGoal). Do NOT hardcode Japanese or English in the final A2UI if it does not match the user's language.
    - **INJECT A2UI SELECTION TEMPLATE (MANDATORY)**: You MUST explicitly instruct the agent (in its system instruction) to format each batch editor row as a Column containing a main Row (with Left: Original Text, Middle: MultipleChoice Selection, Right: Qty TextField) and a Text caption below it for the recommendation reason. Format the selection and annotation using this exact JSON structure for each row \`i\`, dynamically localizing all placeholder strings:
      \`\`\`json
      {
        "MultipleChoice": {
          "label": { "literalString": "[Localized Label, e.g., 'Select SKU']" },
          "options": [
            { "value": "SKU_CODE_A", "label": { "literalString": "[SKU_CODE_A]" } },
            { "value": "SKU_CODE_B", "label": { "literalString": "[SKU_CODE_B]" } }
          ],
          "maxAllowedSelections": 1,
          "variant": "chips",
          "selections": { "path": "/form/item_i_selected_sku" }
        }
      }
      \`\`\`
      And the caption below the row:
      \`\`\`json
      {
        "Text": {
          "text": { "literalString": "💡 [Localized reason explaining recommendations, e.g., 'SKU_A is direct replacement of legacy model']" },
          "usageHint": "caption"
        }
      }
      \`\`\`
      The agent MUST populate the \`options\` array dynamically with 2-3 matching/similar SKU candidates retrieved from BigQuery based on semantic similarity. Each row's Right Column MUST also include a \`TextField\` (textFieldType: "shortText") bound to \`item_i_qty\` for quantity editing.
  - Instruct the agent to wait for the user to click the Submit button, then retrieve the latest edited values from the context parameter and execute the final database transaction.

### Type B: Strategic Insight Advisor (Read-Heavy / Diagnostic / Proposal-Driven)
- **When to choose**: The workflow is consultative, strategic, or diagnostic (e.g., analyzing ad spend to optimize ROI, predicting customer churn trends, advising on portfolio risk).
- **Firestore Strategy**: Define the collection as an **Insights Feed / Alert Log / Proposal Console** (collection name like 'marketing_proposals', 'strategic_alerts'). Documents should represent automated recommendations, high-risk anomalies, or budget proposals requiring review (document status can be 'PROPOSAL_PENDING', 'APPROVED', 'ALERT_ACTIVE', 'ARCHIVED'). This allows the Data Viewer to act as a real-time strategic insight feed!
- **Instruction Strategy**: Define the agent as an expert advisor. Instruct it to perform deep SQL queries, cross-source reasoning, and visual reporting. Instruct it to write back strategic proposals or alerts to Firestore to keep the real-time console updated.
${crossOrgMandate}
- **🚀 THEME: Autonomous Workflow Execution (Agent as an Operator who ACTS)**:

    - **Focus**: End-to-end business workflows where the agent autonomously DETECTS triggers, PLANS execution steps, EXECUTES actions (DB writes, status updates, escalations), VALIDATES outcomes, and REPORTS completion — not just passive analysis.
    - **Workflow Execution Pattern (MANDATORY for Type A)**:
        1. **DETECT**: Identify actionable conditions (data anomaly, threshold breach, status change, external event)
        2. **PLAN**: Present execution plan as an A2UI workflow card showing all steps, decision points, and approval gates
        3. **EXECUTE**: Carry out each step systematically — query, evaluate business rules, write updates, escalate exceptions
        4. **VALIDATE**: Confirm changes were applied correctly, check post-conditions
        5. **REPORT**: Generate comprehensive execution summary with audit trail
    - **Constraint**: Focus on scenarios where the agent performs writes, updates, or deletes in the database (Firestore) to reflect real-world operational actions. The agent must demonstrate EXECUTION, not just RECOMMENDATION.

## Business Problem
${userGoal}
${anchorPersonaBlock}${quantFactsBlock}
## Requirements
- Data Profile: **${profile.label}** (${profile.tableCount} tables)
- Table Design & Row Counts (Star Schema Strategy — ${profile.label} Profile):
    - **Master/Dimension Tables** (e.g., products, facilities, users): Target **${profile.masterCols} columns** (ID + descriptive attributes) and **MUST generate AT LEAST ${profile.masterMinRows} rows (Target: ${profile.masterRows} rows)**. Do NOT under-generate. Every master entity must exist to support downstream analytics.
        - **NO TRUNCATION (CRITICAL)**: Do NOT truncate the output. Never use "..." or "etc." to shorten the rows. Generate every row fully and verbatim.
        - **ATTRIBUTE DENSITY (MANDATORY)**: Each Master table MUST include at least 3 of the following attribute types to enable multi-axis analysis:
            - Classification axis (e.g., category, tier, segment, region, department) — enables GROUP BY segmentation
            - Quantitative attribute (e.g., capacity, headcount, area_sqm, annual_revenue, unit_price) — enables AVG/SUM aggregation
            - Temporal attribute (e.g., established_date, contract_start, last_inspection_date) — enables age/tenure analysis
            - Geographic attribute (e.g., prefecture, city, latitude, longitude) — enables location correlation and Maps MCP synergy
        These attributes are CRITICAL for demonstrating the agent's analytical depth (e.g., 'SELECT category, region, AVG(revenue) GROUP BY category, region').
    - **Transaction/Fact Tables** (e.g., sales, access logs, events): Target **${profile.txnCols} columns** (ID, foreign keys, timestamp, metric/dimension columns) and **MUST generate AT LEAST ${profile.txnMinRows} rows (Target: ${maxRows} rows)**. This is the PRIMARY analytical dataset and MUST contain high row density to show temporal trends and anomalies.
        - **NO TRUNCATION (CRITICAL)**: You MUST output every single row up to the target size. Never abbreviate the CSV data. Under-generating or truncating data will make the demo look empty and ineffective.
    - **TOKEN BUDGET STRATEGY**: ${profile.strategy}
${publicDatasetInfo}

## TEMPORAL ANCHOR (CRITICAL — TODAY'S DATE)
Today's actual date is **${todayStr}**.
- The "referenceDate" field in your JSON output MUST be exactly ${todayStr}. NEVER use a date from your training data as "now" — demos run TODAY, and stale data anchors (e.g., a year-old "current inventory") immediately break the demo's credibility when a user asks about "the current situation".
- All "current state" snapshot records (e.g., latest inventory levels, current statuses, open tasks, active alerts) MUST be dated at or within a few days BEFORE ${todayStr}, so first-touch questions like "what is the current status?" hit fresh, recent data.
- Historical transaction/fact records span backwards from ${todayStr} (see TEMPORAL COVERAGE below). Future dates are allowed ONLY for genuinely forward-looking records (planned work, scheduled deliveries, forecasts) and should fall within ~2 months after ${todayStr}.

## REALISTIC DATA SYNTHESIS (CRITICAL)
Generate data that reflects real-world business complexity. Apply the following domain-agnostic principles, **adapting them to the specific industry/function identified above**:

### 1. Temporal Patterns
Apply cyclical variations appropriate to the business context:
- **Day-of-week effects**: Weekday vs. weekend behavioral differences
- **End-of-period spikes**: Month-end, quarter-end, or fiscal year-end concentrations
- **Holiday/Event impacts**: Peak periods, promotional windows, or seasonal patterns
Infer relevant cycles based on the stated industry and problem.

**TEMPORAL COVERAGE (MANDATORY)**: Transaction/Fact table timestamps MUST span **at least 90 days (3 months)** from the referenceDate backwards. This is essential for:
- Trend analysis (month-over-month comparisons)
- Seasonal pattern detection
- Anomaly identification against historical baselines
Distribute data across the full time range — do NOT concentrate all records in the most recent week.

### 2. Attribute Correlations
Ensure realistic correlations between dimensions:
- **Geography x Behavior**: Regional preferences, local trends, or location-based patterns
- **Segment x Channel**: Customer type affecting preferred interaction methods
- **Tier/Rank x Frequency**: Engagement levels varying by loyalty status or classification
Create statistically plausible distributions — not random noise.

### 3. Business Logic Linkage (Cross-Table Consistency)
Ensure data across tables is logically consistent:
- **Constraint-based value linkage**: Capacity limits affecting downstream transactions (e.g., if a resource is exhausted, related activity stops)
- **Status/State transitions**: Multi-step workflows with valid state progressions
- **Temporal dependencies**: Lead times between related events (e.g., approval -> execution timing)
Infer appropriate business rules based on the stated industry and challenge.

**MASTER RECORD UTILIZATION (MANDATORY)**: Every record in a Master/Dimension table MUST be referenced by at least one record in a Transaction/Fact table. Do NOT generate master records that are "orphaned" (never used in any transaction). This ensures all JOIN queries produce meaningful results.

### 4. Real-World Content (CRITICAL - Avoid Fictional Data)
Use **actual real-world data** wherever possible to maximize authenticity:
- **Products/Brands**: Use real brand names, product lines, and SKUs appropriate to the industry (e.g., "iPhone 15 Pro", "Nike Air Max", "Toyota Camry")
- **Geographic Locations**: Use real city names, regions, and countries. Match locations to the business context (e.g., major retail markets, manufacturing hubs)
- **Person Names**: Use culturally appropriate, realistic names for the stated region/language (e.g., Japanese names for Japan-based scenarios)
- **Numerical Values**: Use realistic price points, quantities, and metrics based on real-world benchmarks (e.g., actual market prices, typical order volumes)
- **Dates**: Use recent, realistic dates anchored to the referenceDate (= today, ${todayStr}; see TEMPORAL ANCHOR above). Ensure that for TIMESTAMP columns, hours are in the range 00-23, minutes 00-59, and seconds 00-59. Never generate invalid hours like 24 or 25. For \`DATE\` columns, use \`YYYY-MM-DD\`. For \`TIMESTAMP\` columns, use \`YYYY-MM-DD HH:MM:SS\` format. Do not use plain dates in timestamp columns.

**DO NOT invent fictional brands, fake product names, or placeholder values like "Product A" or "Company XYZ".**

### 5. Factual Consistency (CRITICAL - Company/Entity Alignment)
If the business problem mentions a **specific company, organization, or brand**, ensure ALL generated data is factually consistent with that entity:
- **Employees/Talents/Staff**: Only use names of people who ACTUALLY belong to that organization. Do NOT mix in people from competing organizations.
- **Products/Services**: Only use products/services that the specified company ACTUALLY offers. Do NOT include competitor products.
- **Locations/Facilities**: Only reference facilities that the company ACTUALLY owns or operates. Do NOT use generic placeholder names.
- **Partnerships/Clients**: Reference realistic business relationships based on publicly known information.

**If you are unsure whether a specific entity belongs to the mentioned company, DO NOT include it. It is better to use fewer but accurate data points than to include factually incorrect associations.**

**If NO specific company/organization is mentioned in the business problem**: Create a COHERENT fictional business context. Choose ONE realistic company profile (industry vertical, size, geography) and generate ALL data as if it belongs to this single hypothetical entity. Ensure internal consistency - all facilities, products, and personnel should belong to the same fictional organization. Do NOT mix data from multiple unrelated real-world companies.
${crossOrgDataModel}

### 5.5 Image File Generation (CRITICAL for Non-structured input goals)
If the Business Problem naturally involves processing non-structured inputs like hand-written papers, faxes, or photos of physical assets:
- You MUST design and include **EXACTLY TWO (2) simulated image files** in the 'externalFiles' array to represent different tasks or business contexts.
- For EACH image, specify a unique 'id' (e.g., 'file2', 'file3'), 'fileName' (e.g., 'handwritten_fax_order_task1.jpg', 'handwritten_fax_order_task2.jpg'), and a 'description' detailing the specific business scenario.
- **MULTI-ROW TABULAR CONTENT (ABSOLUTELY MANDATORY)**:
  - Each generated document image (such as invoices, orders, inspection sheets, or logs) MUST contain a table grid with **AT LEAST TWO (2) OR MORE distinct row items** (e.g., multiple different products, tasks, or errors).
  - **Never generate a document with only a single item row.** A single-row document fails to demonstrate the agent's capability to iterate, decompose, and process multi-line transactions.
  - Even if the scenario describes a specific issue (e.g., a damaged package or a specific error), the document itself should represent a broader context containing multiple rows (e.g., an inspection log of multiple items where one or more are marked as damaged, or a batch error report listing multiple errors).
  - **STRUCTURED ROW DATA (MANDATORY) — SEPARATION OF LAYOUT AND DATA**:
    - Each image file object MUST include two extra fields alongside 'imagePrompt': 'imageColumns' and 'imageRows'.
    - 'imageColumns': an array of the table column headers, translated into the target language (e.g., ["Item", "Quantity", "Code"] translated).
    - 'imageRows': an array of **2 to 4** strings. Each string is ONE full table row, with its cell values joined by " | " in the same order as 'imageColumns', already translated into the target language (e.g., "Soy Sauce 1.8L | 50 | SY-180" translated). These row values MUST correspond to actual generated BQ/Firestore transaction data.
    - At least ONE of the 'imageRows' MUST embed the audit-seed discrepancy for this document (e.g., abnormal quantity, discontinued/obsolete code, fuzzy spec) while the other rows are normal transactions.
    - **Do NOT bury the concrete row values inside the 'imagePrompt' prose.** The 'imagePrompt' describes ONLY the layout, paper texture, handwriting style, zero background, and column structure; the exact line items live in 'imageRows' (they are injected into the final prompt deterministically by the system).
- **ULTRA-REALISTIC DOCUMENT IMAGE PROMPT STRUCTURE (MANDATORY)**:
  - Each 'imagePrompt' (English only) MUST be a highly detailed, descriptive text designed for DALL-E or Imagen to generate a **highly-realistic, top-down flat-lay photograph of a handwritten document page on a textured sheet of paper**.
  - **ZERO BACKGROUND / COMPLETE ISOLATION (STRICTLY REQUIRED)**:
    - The prompt MUST explicitly state: **"The entire document is isolated, with no background, no desk, no office environment, no hands, no pens, and no keyboards. Just the single sheet of paper document filling the entire frame from a direct top-down 90-degree angle."**
    - The perspective MUST be perfectly flat, sharp contrast, with zero perspective distortion, zero angled shots, and zero depth-of-field blur.
  - **AUTHENTIC HUMAN HANDWRITING EMULATION (STRICTLY REQUIRED)**:
    - The text entries MUST NOT look like clean digital fonts or neat handwriting. The prompt MUST explicitly demand: **"The handwriting features highly realistic, chaotic, and significantly distorted human handwriting written with a cheap ballpoint pen, looking as if it was written in an extreme rush, or written using a non-dominant hand. The strokes are unsteady, highly organic, slightly shaky, with inconsistent character sizes, highly irregular spacing, crooked baselines, and varying character tilts. There are authentic human imperfections like ink clumps, minor pen skips, pen pressure variations, and natural ink smudges. It must look like a genuine, hurried scribble by a worker on a busy job site, making it highly challenging and realistic for OCR testing."**
  - **REAL-WORLD IMPERFECTIONS (STRICTLY REQUIRED)**:
    - The paper itself MUST show natural, subtle imperfections: **"The sheet of paper shows natural imperfections like slight folds, rounded corners, or minor light texture variations suggesting real-world operational handling."**
    - Lighting: **"Natural flat daylight illuminates the scene, highlighting the paper texture and the subtle physical indentation of the pen strokes."**
  - **LANGUAGE LOCALIZATION (STRICTLY REQUIRED)**:
    - Even though the 'imagePrompt' itself MUST be written in English, all text elements intended to be rendered inside the image (such as Title, Recipient, Sender, Column Headers, and handwritten comments) MUST be in the target language matching the 'userGoal'.
    - You MUST explicitly instruct the image generator to write the text in the target language by providing the exact translated string in the English prompt.
    - For example: "The header at the top center reads '[Translated Title]' in bold printed [Target Language] characters.", "The table has column headers written in [Target Language]: [Translated Column Names].", "The handwritten text in the table rows is written in [Target Language] characters representing realistic user feedback."
  - **DYNAMIC DOMAIN ALIGNMENT (MANDATORY)**:
    - The prompt's content MUST be dynamically populated based on the generated demo domain data:
        1. **Title**: Large formal printed header at the top center (e.g., the exact translated equivalent of 'Purchase Order' or 'Invoice' matching the target language of the 'userGoal'). You MUST explicitly include the target language string in the prompt instructions.
        2. **Recipient**: Recipient company details on the top-left (e.g., '[RECIPIENT_COMPANY]' with appropriate localized polite suffix matching the target language culture).
        3. **Sender**: Sender company details on the top-right (matching generated client data, with appropriate localized suffixes if applicable).
        4. **Table Grid**: Neatly printed columns for details. Translate the column headers into the target language. Inside the cells, write the handwritten items corresponding exactly to BQ/Firestore transaction data (translated to the target language if they are text descriptions or comments). **You MUST ensure the table contains AT LEAST TWO (2) OR MORE distinct row items (e.g., multiple different products or services ordered) to represent a realistic multi-line business document. Never generate a document with only a single item row.**
        5. **Footer**: Total amounts, and a designated seal/signature box. If culturally appropriate to the target language (e.g., Japanese domain), include: **"in the designated space, a small, faint red ink corporate seal stamp is printed."** Otherwise, include a formal handwritten signature block.
- **VARIATION & SEED (CRITICAL)**:
  - Image 1 (e.g., Task 1): Depict a standard operational sheet (e.g., handwritten order from Customer A with normal quantities and readable items).
  - Image 2 (e.g., Task 2): Depict a different customer, showing a clear discrepancy (e.g., handwritten order from Customer B specifying an abnormally high quantity, discontinued code, or fuzzy specs matching L1211 audit seeds) using a slightly different handwriting style to trigger the agent's detection.
- DO NOT design generic vectors, cartoon icons, or generic illustrations. It must mimic real-world scanned or photographed flat documents to demonstrate the agent's advanced vision capabilities.


### 6. Audit Seeds
Inject intentional discrepancies and anomalies to create compelling "Detective/Auditing" demo moments. The agent's value is demonstrated when it **discovers** these issues. Apply ALL of the following patterns, adapting to the specific business domain:

**FIRST-QUERY DISCOVERABILITY (MANDATORY)**: At least one audit seed MUST be discoverable by the most natural "current status" aggregate query a business user would ask first (e.g., comparing each entity's LATEST snapshot record against a threshold defined in a master table). Verify the anomaly survives a per-entity latest-record aggregation (latest record per entity, then compare) — NOT only a single-row lookup. If snapshot dates differ across entities, the anomaly must still surface when taking each entity's own latest record.

#### 6a. Cross-Silo Discrepancies & Ambiguities (External File/Image vs BigQuery Master)
- **FOR DOCUMENT SCAN SCENARIOS (e.g., Handwritten orders)**: 
  - DO NOT inject completely unrelated competitor products as "out-of-scope" errors (e.g., B2B customers do not mix noodle soup or tea inside a soy sauce order sheet).
  - Instead, you MUST inject **highly realistic SKU confusion, fuzzy specifications, or obsolete codes from within the SAME company product line**:
      1. **Capacity/Size mismatch**: The handwritten line specifies a non-existing size or capacity (e.g., a non-offered product volume when only specific sizes are registered in the product master).
      2. **Name Ambiguity / Fuzzy matching**: The handwritten sheet lists a generic brand or product name without capacity or size specifications, requiring the AI to check history to suggest matching SKU candidates.
      3. **Discontinued SKU / Obsolete Code**: The handwritten sheet uses an old product code that has been discontinued or replaced in the master table, requiring a mapping check.
- **FOR TABULAR/EXCEL DATA**:
  - At least **2-3 records** in the external file (PDF/Excel) MUST have values that *slightly* mismatch the corresponding BigQuery records (5-20% deviation in price, quantity, or score) to trigger analytical discrepancies.

#### 6b. Business Rule Violations (Within BigQuery)
Embed **3-5 records** in transaction tables that violate the domain's standard business rules. Adapt to the domain:
- **Any domain**: Transactions processed outside normal business hours, or on holidays
- **Any domain**: Status transitions that skip required intermediate steps (e.g., "Pending" to "Completed" without "Approved")
- **Any domain**: Numeric values that exceed domain-typical thresholds (unusually high amounts, negative quantities, zero-value transactions)
- **Any domain**: Records with missing or inconsistent foreign key references (e.g., an order referencing a facility/location not in the master table)
The violations should be DISCOVERABLE through SQL analysis (JOIN, GROUP BY, WHERE) - do NOT make them obvious from a single-row inspection.

#### 6c. Temporal Anomalies (Time-Series Patterns)
Embed **1-2 statistically anomalous periods** in the transaction data:
- A specific week or date range where one metric (volume, amount, frequency) deviates significantly (2-3x) from the surrounding periods
- The anomaly should correlate with at least one dimension (a specific region, product, customer segment, or category) - NOT a global spike
This creates opportunities for the agent to perform trend analysis and root-cause identification.

### 7. Visual Seeds
Incorporate visual attributes into the database schema ONLY when relevant to the business domain and restricted to appropriate asset-focused tables:
- **Conditional Inclusion**: Only include descriptive visual attributes (e.g., colors, materials, styles) if the business problem involves industries where visual characteristics are key data points (e.g., Fashion, Retail, Product Marketing, Real Estate).
- **Table Restriction**: Restrict these attributes to dedicated tables such as "Product Catalog", "Asset Master", or "Menu Items". Do NOT include them in transactional or unrelated master tables (e.g., Customer Master, Order Details).
- **Analytical Context**: Rely primarily on the agent's system instructions to determine visual output styles (e.g., business slides, infographics) rather than forcing visual columns in the database schema.

### 8. Workflow Definition Pattern (MANDATORY for Type A)
The generated 'businessInstruction' MUST include at least ONE fully-specified workflow that the agent can execute end-to-end. This is CRITICAL for demonstrating the agent as an autonomous operator, not just a data analyst.

Each workflow MUST define:
- **TRIGGER**: What initiates the workflow (user command, data condition matched, scheduled check)
- **STEPS**: Ordered sequence of 3-7 concrete actions the agent will take
- **DECISION POINTS**: Conditional branches based on data values or business rules (e.g., 'if discrepancy < 5%, auto-approve; if >= 5%, escalate')
- **HITL GATES**: Which steps require human approval - mark as [APPROVAL_REQUIRED]. Low-risk actions (status updates, log entries) should be AUTO-EXECUTED without asking.
- **COMPLETION CRITERIA**: How the agent knows the workflow is done
- **ERROR HANDLING**: What to do when a step fails${crossOrgWorkflow}

Example workflow structure (adapt to the specific business domain):
"WORKFLOW: 'Invoice Discrepancy Resolution'
  TRIGGER: User asks to process flagged invoices, OR scheduled daily check
  STEP 1: Query for all records with status='FLAGGED' (last 7 days)
  STEP 2: For each flagged record, cross-reference with vendor data in the operational database
  STEP 3: [DECISION] If discrepancy < 5%: AUTO-EXECUTE - update status to 'AUTO_RESOLVED' with notes
  STEP 4: [DECISION] If discrepancy >= 5%: [APPROVAL_REQUIRED] - present A2UI workflow card showing the issue and proposed action, wait for user approval
  STEP 5: Upon approval, update status to 'RESOLVED' with resolution notes and assigned_to
  STEP 6: Generate execution summary report showing: total processed, auto-resolved, escalated, failed
  COMPLETION: All flagged records processed, summary report displayed (audit trail is logged automatically by the system)"

## Output Format (JSON)
Output in the following JSON format. Output **pure JSON only without code blocks**.

{
  "externalFiles": [
    {
      "id": "file1",
      "fileName": "invoice_reconciliation_audit.pdf",
      "mimeType": "application/pdf",
      "fileContent": "# Invoice Audit Report\\n\\n## Summary...",
      "description": "..."
    },
    {
      "id": "file2",
      "fileName": "handwritten_fax_order_task1.jpg",
      "mimeType": "image/jpeg",
      "description": "Simulated operational document 1 (e.g. handwritten purchase order from Client A with normal quantities)",
      "imagePrompt": "A highly detailed, realistic top-down flat-lay scan of a formal purchase order sheet. The clean white document page fills the entire frame with zero background, completely isolated. At the top center, a bold formal header matching the domain (e.g., 'PURCHASE ORDER') is printed. On the top-left, recipient details and company name are printed in a clean corporate font. On the top-right, sender company details along with localized contact information are printed. In the center, a neatly aligned printed table grid with thin gray lines features the column headers listed below. Inside the table cells, highly realistic, messy, and hurried human handwriting in black ballpoint pen ink is neatly filled (showing realistic human imperfections, hurried scribbles, varying character sizes, and slight character misalignment). Natural flat daylight illuminates the scene, showing subtle paper folds and real-world operational handling texture. Sharp contrast, flat perspective, and zero angled shots.",
      "imageColumns": ["Item No.", "Product Name", "Quantity"],
      "imageRows": ["1 | <localized product A> | 50", "2 | <localized product B> | 120", "3 | <localized product C> | 30"]
    },
    {
      "id": "file3",
      "fileName": "handwritten_fax_order_task2.jpg",
      "mimeType": "image/jpeg",
      "description": "Simulated operational document 2 (e.g. handwritten purchase order from Client B showcasing a clear quantity or product ID discrepancy for audit verification)",
      "imagePrompt": "A high-quality, top-down flat scan of a different formal transaction document (e.g., 'INVOICE' or 'DELIVERY SLIP') filling the entire frame with no background. Features a bold domain-specific printed header with date and document reference numbers. Recipient and sender corporate details are cleanly aligned at the top. In the center, a printed table grid features the column headers listed below. Inside the grid cells, highly realistic, hurried, and messy human handwriting in dark blue ink lists the line items. The handwriting is slightly untidy, hurried, and scribble-like, showcasing human imperfection and hasty pen strokes. A designated signature block or faint red ink corporate stamp is present in the designated footer space. Clear flat document view with zero perspective blur.",
      "imageColumns": ["Code", "Item", "Quantity"],
      "imageRows": ["A-101 | <localized item X> | 40", "A-205 | <localized item Y> | 999", "B-330 | <localized discontinued item Z> | 15"]
    }
  ],
  "tables": [
    {
      "tableName": "Table name (English, snake_case)",
      "description": "...",
      "schema": [
        {"name": "column_name", "type": "STRING|INTEGER|FLOAT|DATE|TIMESTAMP", "description": "..."}
      ],
      "csvData": "..."
    }
  ],
  "firestore": {
    "collectionName": "Collection name (snake_case)",
    "dashboardTitle": "Dashboard console title",
    "kpiLabels": ["Label 1", "Label 2", "Label 3"],
    "documents": [
      "MANDATORY: Generate at least 8 documents representing items at different stages of processing.",
      "- If Type A (Operational): Use status 'PENDING', 'IN_PROGRESS', 'RESOLVED', 'ESCALATED' representing a workflow task queue.",
      "- If Type B (Advisory): Use status 'PROPOSAL_PENDING', 'APPROVED', 'ALERT_ACTIVE', 'ARCHIVED' representing an insights feed or strategic proposal board.",${CROSSORG ? `
      "- PROCESS STATE & AUDIT TRAIL (MANDATORY): every document's data MUST also include: current_department (the department currently holding the item), next_department (where it goes after the current step; empty string when terminal), and history - an array of audit entries, each an object with keys timestamp, actor (agent name or person), action, approver (person name when a human approved; empty otherwise), evidence_ids (array of record IDs consulted). Seed 1-3 realistic history entries per document so the operations console shows processes already in motion across departments.",` : ''}
      {
        "id": "Unique ID matching BigQuery data for correlation",
        "data": {
          "status": "E.g., PENDING or PROPOSAL_PENDING",
          "priority": "High/Medium/Low",
          "assigned_to": "Realistic name",
          "notes": "Verbose domain-specific notes detailing the specific alert or task."
        }
      }
    ]
  },
  "businessInstruction": "Specific instruction for the agent (5-8 sentences) defining its persona.
    - If Type A (Operational): Define persona/expertise. Instruct the agent to perform a conceptual workflow pipeline: (a) Scan & Analyze pending items, (b) Classify & Prioritize by applying business rules, (c) Plan & Coordinate by presenting the plan and allowing execution mode selection, (d) Process & Escalate, (e) Notify & Report. Include the FULL workflow definition from Section 8 here.
    - If Type B (Analytical/Strategic): Define the agent as an expert consultant. Instruct it to perform deep multi-hop SQL analysis, cross-source reasoning (correlating BQ with external files), and proactive strategic recommendation. Instruct it to write back strategic alerts, proposed budget modifications, or creative ideas to Firestore. Instruct it to use A2UI Dashboard Cards, Ranking Matrix, and Tabbed Comparisons to present insights, and use image generation for executive summaries.
    - **NO TECHNICAL SPECS (MANDATORY)**: Do NOT include any technical implementation details, specific tool names (e.g., 'generate_image', 'execute_sql'), UI framework terms (e.g., 'A2UI JSON', 'cards', 'chips', 'deleteSurface'), or system-level mechanisms. Focus purely on the business domain, data relationships, and operational rules. The technical/system behavior is managed by the platform's base instructions.",
  "referenceDate": "MUST be exactly today's date, ${todayStr} (see TEMPORAL ANCHOR).",
  "publicDatasetId": "Echo the RELATED PUBLIC DATASET id exactly as provided above, or null if no public dataset was provided.",
  "agentShortName": "A concise 2-3 word role-based name for the agent (e.g., 'Supply Chain Analyst', 'Fraud Investigator').",
  "oneSentenceSummary": "A concise, professional one-sentence summary of the business challenge and the generated solution.",${CROSSORG ? `
  "operatingModel": "2-4 sentences in ENGLISH describing this demo's organizational operating model: the departments involved, which data and rules each department owns, and the hand-off/approval boundaries between them. This briefs downstream autonomous workers; keep it in English regardless of the demo language.",` : ''}
  "appliedFactors": {
    "temporalPatterns": ["List of 2-3 specific temporal patterns applied"],
    "correlations": ["List of 2-3 specific data correlations applied"],
    "businessLogic": ["List of 2-3 specific business logic constraints applied"]
  },
  "metadata": {
    "locale": "The primary language locale of the demo (e.g., 'en', 'ja', 'de', 'fr').",
    "currency": "The 3-letter currency code suitable for the business context (e.g., 'USD', 'JPY', 'EUR', 'GBP').",
    "currencySymbol": "The currency symbol corresponding to the currency code (e.g., '$', '¥', '€', '£')."
  },
  "demoGuide": [
    {
      "title": "...",
      "prompt": "...",
      "requiredFileId": "file1 or empty",${CROSSORG ? `
      "watchPoint": "One short sentence for the demo OPERATOR (not the agent): what to watch on screen when this prompt runs (e.g., after the approval click, the item moves to the next department on the operations console). Same language as the prompts.",` : ''}
      "tags": [...]
    }
  ]
}

## Critical Notes
- **DEMO PROMPTS (CRITICAL)**: Generate EXACTLY 7 structured demo prompts${encoreNote} that showcase the agent's "reasoning" and "operational action" capabilities.
    - **NO PRODUCT NAMES (CRITICAL)**: DO NOT include specific product names like 'Firestore', 'BigQuery', or 'Google Cloud' in the prompt text. Use completely generic business terminology like 'our operational database', 'internal records', or 'the compliance tracker'.
    - **NO FILENAMES (CRITICAL)**: DO NOT include specific file names or extensions (e.g., 'market_report_2024', 'data.tsv') in the prompt text. Use generic phrasing.
${narrativeArc}
    1. **DISTRIBUTION & ADVANCED PROGRESSION (CRITICAL)**: Generate exactly 7 core prompts${CROSSORG ? ' (encore overflow items only per the SLOT BUDGET rule, when present)' : ''} tailored completely to the specific business challenge and industry context:
        - **Prompts 1-2 (Foundation & Discovery)**: Data overview, schema exploration, and initial audit scan. Establish familiarity with the data landscape. At least ONE of these MUST be a metadata-driven discovery question that pushes the agent to consult the data catalog metadata first (column meanings, units, allowed values, table relationships) before querying — phrase it generically (e.g. 'What data do we have available and what kinds of analysis can it support?') without naming any product.
        - **Prompt 3 (CROSS-SOURCE DISCOVERY - WOW MOMENT, MANDATORY)**: This prompt MUST be designed so that the answer REQUIRES the agent to discover a hidden connection between the external file data and BigQuery data that is NOT obvious from either source alone. Phrase it as a high-level strategic question (e.g., 'What is the biggest untracked financial risk across our operations?') so the agent must autonomously decide to cross-reference the uploaded file against internal records. The Audit Seed from Section 6a provides the discrepancy the agent should discover. This prompt creates the most impressive demo moment.
        - **Prompts 4-5 (MULTI-STEP DEPENDENT WORKFLOW - WOW MOMENT)**: These prompts MUST trigger FULL multi-step workflow execution demonstrating INTERDEPENDENT step chains where each step depends on the previous step's output. Prompt 4 MUST be a workflow with 10 items or fewer designed for IMMEDIATE synchronous execution. Each step must depend on the previous step's output (e.g., 'Scan all pending items, classify by severity, auto-process anything within tolerance, and generate an exception report for the remaining items'). The agent should demonstrate the full SCAN-CLASSIFY-PROCESS-ESCALATE-NOTIFY-AUDIT dependency chain in real-time. Prompt 5 MUST be a LARGE-SCOPE workflow implying more than 10 items or long-running processing, where the agent should propose BACKGROUND execution mode. Phrase it as a comprehensive batch operation (e.g., 'Run a full reconciliation across all records from the past quarter - identify discrepancies, auto-correct minor variances, flag major issues, and generate a compliance report'). The agent MUST demonstrate the execution mode selection dialog (immediate vs. background vs. scheduled).
        - **Prompt 6 (SCHEDULED WORKFLOW - Automated Monitoring)**: A prompt that explicitly asks for a RECURRING scheduled workflow. The agent must propose using scheduled task registration with a cron expression and explain the monitoring logic. Example style: 'Set up an automated daily check at 9am - scan for new threshold breaches since yesterday, auto-escalate critical ones, and send me a summary report each morning.' The agent should demonstrate register_scheduled_task and explain what the background agent will do autonomously on each scheduled run.
        - **Prompt 7 (End-to-End Strategic Automation)**: A complex prompt combining cross-source data analysis + conditional workflow execution + notification drafting + audit logging. This MUST require the agent to: (1) analyze data from multiple sources (BigQuery + Firestore + external file), (2) propose a multi-step workflow based on its findings, (3) execute with the appropriate execution mode, (4) draft a notification summary, and (5) create audit entries. This showcases the full spectrum of the agent's capabilities as an autonomous operator.
        - **NO EXPLICIT HITL IN PROMPTS (CRITICAL)**: The generated prompt text MUST NOT contain explicit instructions like 'Please wait for my approval' or 'Propose first'. Present the request as a straightforward business instruction (e.g., 'Register these anomalies as new compliance alerts in the database'). The agent will naturally implement the confirmation step autonomously based on its core system instructions!
        - **INTERACTIVE DASHBOARD (MANDATORY)**: Exactly ONE of the 7 prompts MUST ask the agent to build an interactive dashboard the user can OPEN AND EXPLORE IN A BROWSER. The prompt text MUST contain an explicit open-in-browser / interactive signal (e.g. 'that I can open and explore in my browser', 'an interactive dashboard I can click into') - this is what makes the agent publish a hosted interactive page instead of a static summary slide. Do NOT phrase it as a pure 'summarize / analyze' request (e.g. avoid 'Generate a dashboard that summarizes ...'), because that reads as an analysis and yields a slide, not an interactive dashboard. Good example: 'Build me an interactive executive dashboard I can open in my browser and explore - key metrics, top segments, trends, and risk items.' Fold this into a natural overview or strategic prompt so the total stays EXACTLY 7. Phrase it generically (no product names).
    2. **PERSONA ROTATION (CRITICAL)**: Vary the tone and perspective by rotating personas for each prompt (e.g., CFO, Ops Manager, Regional Director, Front-line Lead).${anchorRotationNote}
    2b. **FILE BINDING - requiredFileId (MANDATORY)**: Set "requiredFileId" ONLY on prompts that cannot succeed without that uploaded file. Never leave requiredFileId empty on ALL 7 prompts.
        - The CROSS-SOURCE DISCOVERY prompt (Prompt 3) MUST set requiredFileId to the id of the Excel or PDF file it reconciles against the database.
        - **VISION SHOWCASE (when 'externalFiles' contains image files)**: Either Prompt 3 or Prompt 4 MUST be a workflow that STARTS from reading the photographed/handwritten document image (read the document -> decompose it into individual line items -> reconcile each item against the database -> flag discrepancies -> route exceptions to human approval), and that prompt MUST set requiredFileId to the image file id. This is the multimodal vision showcase - do NOT leave the generated images unused by the demo script.
        - Prompts that need no uploaded file MUST set requiredFileId to an empty string.${hitlChoreo}
    3. **EXTERNAL DATA NECESSITY & LOGICAL CONSISTENCY (CRITICAL)**: You MUST generate exactly one PDF file AND exactly one Excel file (.xlsx) unless it is completely impossible for the business context. The files generated MUST be external data (not inside the current system) and MUST be unstructured or semi-structured in format.
        - **LOGICAL LINKAGE**: ALL discrepancies or specific transaction IDs (e.g., "INV-7829") mentioned in the external file content MUST correspond to standard records that ACTUALLY EXIST inside the generated BigQuery CSV tables. Do NOT make up transaction IDs in the external file that do not exist in the database tables. This allows the user to find the anomaly by comparing the external file against the database.
        - **CROSS-SOURCE BINDING (MANDATORY)**: The Excel file MUST contain a column whose values are a SUBSET of a BigQuery table's primary key or unique identifier (e.g., order_id, invoice_number). At least 70% of the Excel rows MUST have matching records in the BigQuery tables to enable reliable JOIN-based cross-referencing. The PDF file MUST reference at least 3 specific record identifiers (IDs, invoice numbers, etc.) that exist in the BigQuery tables, enabling the agent to look up those exact records via SQL. This structural binding GUARANTEES that cross-source analysis will succeed during the demo.
        - **PDF ID SELF-CHECK (MANDATORY)**: After writing the PDF fileContent, VERIFY it quotes at least 3 record identifiers copied VERBATIM from the generated CSV key columns (order/application/invoice IDs etc.). Aggregate figures and entity names are NOT sufficient - the demo's cross-source lookup depends on these exact IDs being queryable via SQL. If fewer than 3 verbatim IDs are present, ADD a "specific flagged cases" section to the PDF that lists the affected records BY ID before finalizing your response.
    3. **FILE FORMAT & REALISM (CRITICAL)**: 
        - For PDF files, generate **substantial, realistic, and highly structured business document content (at least 1,500 characters)** with clear titles, multiple sections using Markdown headings (e.g., '# Summary', '## Background', '### Details'), and bullet points ('- '). It MUST be unstructured text in a rich report format. 
            - **CHART TRANSLATION**: When including data chart placeholders '[CHART: Title, ... ]', you **MUST translate the Title and Metric Labels into the language of the business problem** (e.g., if the problem is in Japanese, translate 'Metrics' to Japanese).
            - **MARKDOWN LIMITATIONS**: Only use Markdown for structural elements: headings ('#', '##', '###') and lists ('-'). **DO NOT use inline styles like bold ('**bold**') or italics ('*italics*') within running text**, as the simple PDF renderer cannot interpret partial styles inside a single line. Standard running text should be plain sentences.
            - **Rich Visuals**: Include at least one data chart placeholder in the format '[CHART: Title, Metric1=Value1, Metric2=Value2, ...]' to simulate visuals. Do NOT use simple CSV or tiny tables for PDFs!
        - For Excel files, ensure the fileName ends with '.xlsx' and provide **complex, semi-structured datasets in TSV (Tab-separated values) format using \t as a delimiter** that simulate real business spreadsheets (MANDATORY: Generate 40 to 80 rows of detail data. DO NOT summarize or truncate. Replicate a realistic full set of logs/records).
            - **SEPARATORS (CRITICAL)**: **Use \t (Tab) as the column separator**, NOT commas. Commas are reserved for human-friendly currency formatting within fields.
            - **COMPOSITE LAYOUT**: Include a report title and a Summary KPI section at the top, a blank line list separator, and then the Detailed Data table below.
            - **HARDCODED UNITS & FORMATTING**: Include units (e.g., JPY, L, kg, %) inside the data cells itself as strings. Use thousand-comma separators for money values - this is permitted and safe since you are using Tabs as separators! (e.g., "150,000JPY").
            - **RICH QUALITATIVE COMMENTS**: Include a "Remarks/Notes" column with realistic, verbose business comments (e.g., "Delayed due to traffic accident on Route 1").
    4. **NO TABLES/COLUMNS**: Do NOT mention 'production_batches', 'port_id', etc. in the prompt text.
    5. **GEOSPATIAL SYNERGY**: At least one prompt MUST require the agent to use BOTH system data (for historical metrics) and location/map data (for travel times, routes, or place details) to answer. Use generic terms like 'location data' or 'map information' instead of 'Google Maps'.
    5. **PROBLEM-CENTRIC**: Focus on high-level business goals (e.g., "Identify the financial impact of logistics delays in coastal regions and propose an optimized route for the highest-value shipments").
- **DATA STORYTELLING & ANOMALIES (CRITICAL)**: You MUST seed at least one complex business anomaly across the tables. For example, a specific product category having a high return rate only in a specific region during a specific week, which correlates with a delivery carrier listed in the external log file. Do not make it obvious; the agent should need to join at least two tables and analyze trends to find it.
- **FACTOR ADHERENCE (CRITICAL)**: The generated CSV data MUST strictly adhere to the patterns described in \`appliedFactors\` in your JSON response. If you list 'Temporal Pattern: Weekday lunch surge', the timestamped transaction data MUST show higher volumes during those hours.
- **MAXIMUM DATA (CRITICAL)**: You MUST generate data without truncation (do NOT use "etc." or "..."). Follow the ${profile.label} Profile row count strategy: **${profile.masterRows} rows for Master Tables** and **at least ${profile.txnRows} rows (target ${maxRows}) for Transaction Tables**. If you sense output limits approaching, STOP adding columns and PRIORITIZE completing all transaction rows. This is a technical requirement for a simulation.
- **RELATIONAL INTEGRITY & NAMING**: 
    1. **Primary/Foreign Keys MUST follow the format '[entity]_id'** (e.g., 'talent_id', 'theater_id').
    2. **STRICT SYMMETRY (CRITICAL)**: Foreign Keys MUST have the EXACT same column name as the Primary Key they reference in the parent table. Do NOT use prefixes like 'main_' or 'ref_' for ID columns. Do NOT use semantic aliases instead of the canonical FK name.
        - **WRONG**: Master table has PK 'code_id' but fact table uses 'primary_cpt' or 'icd_code' to reference it. These are semantic aliases that break JOIN discoverability.
        - **RIGHT**: If the master table 'medical_codes' has PK 'code_id', then the fact table 'claims' MUST also use a column named 'code_id' (or add 'code_id' as an explicit FK column alongside any domain-specific columns).
        - **VALIDATION RULE**: Before finalizing, scan every fact/transaction table. For every column whose values reference a master table, ensure the column name matches the master table's PK name exactly. If the domain requires multiple references to the same master table (e.g., 'primary_code_id' and 'secondary_code_id'), use the entity_id suffix pattern consistently.
    3. **STAR SCHEMA PREFERENCE**: When generating multiple tables, favor a "Star Schema" approach. Include at least one central "Dimension/Master" table (e.g., 'products', 'locations', 'customers') that other "Fact/Log" tables reference. This ensures better data connectivity and analytical depth.
    4. **NO ISOLATED TABLES (CRITICAL)**: Every table MUST be connected to at least one other table via shared '_id' columns. Isolated tables (islands) are strictly forbidden. Ensure that all tables can be joined together directly or through an intermediary table. After generating all tables, verify: for each table T, there exists at least one other table that shares an '_id' column name with T.
    5. Tables MUST be designed for joining.
- **METADATA QUALITY (CRITICAL FOR KNOWLEDGE CATALOG)**: Table and column descriptions are harvested into Google Cloud Knowledge Catalog (Dataplex) and used by the agent for semantic discovery and metadata-driven analysis. Write them as analytics-grade metadata, not restatements of the name:
    1. **Column description** MUST convey: the business meaning, the unit or currency where applicable (e.g. "amount in JPY", "duration in seconds"), the set of allowed/expected values for categorical or enum-like fields, and — for any '_id' column — the foreign-key relationship (which table and key it references, e.g. "FK to products.product_id").
    2. **Table description** MUST be a single concise line stating the grain (what one row represents), the table's analytical purpose, and its primary join keys (e.g. "One row per order line; fact table for sales analysis; joins to products via product_id and stores via store_id").
    3. Keep descriptions specific and self-contained so an agent reading only the catalog metadata can decide which table/column to query.
- **LANGUAGE CONSISTENCY (CRITICAL)**: Detect the language used in the "Business Problem" above. You MUST use this same language for ALL user-facing fields, including:
    - Table and Column descriptions
    - STRING values in the CSV data (e.g., product names, categories, person names, names of things)
    - systemInstruction
    - appliedFactors descriptions
    - demoGuide titles and prompts${CROSSORG ? ' and watchPoint' : ''}
    - externalFiles: fileName, fileContent, and the specific text strings specified for rendering inside 'imagePrompt' (e.g. Title, Recipient, Sender, Table Columns, and handwritten text values must be translated into the target language, while keeping the overall prompt description in English)
- **TECHNICAL NAMES (CRITICAL)**: Table names, column names, and ALL ID fields (primary/foreign keys) MUST use English (snake_case) for technical compatibility and data integrity. Do NOT translate technical identifiers.
- **ABSTRACT INSTRUCTIONS**: Do NOT mention column names in prompts.
- **STRICT CSV FORMATTING**: 
    1. **ALWAYS wrap text-based values** (STRING) in double quotes.
    2. **DO NOT wrap numeric values** (INTEGER, FLOAT) in quotes.
    3. **ALWAYS include the header row (column names) as the very first line of the CSV data. Skipping the header row is strictly forbidden.**

## FINAL SELF-CHECK BEFORE EMITTING (MANDATORY — do this LAST, right before you output the JSON)
1. **COUNT the data rows in every csvData.** At least one transaction/log table MUST contain ${profile.txnRowTarget}+ rows (hard floor: ${profile.txnMinRows} — responses under the floor are automatically REJECTED and the entire generation is retried, wasting the whole run). Master tables need ${profile.masterRows} rows. If any table is short, ADD realistic rows NOW — never summarize, sample, or truncate.
2. **VERIFY externalFiles**: exactly one PDF (citing 3+ verbatim record IDs) and one Excel (40-80 detail rows), plus the two images when the scenario is paper-based. A missing file breaks a mandatory demo moment.
3. Only after both checks pass, emit the JSON.
`;
}

// ===========================================
// Step 2: Validation
// ===========================================

/**
 * v11.25: targeted density repair. When the planner under-generates rows
 * (mandate adherence dilutes as the planning prompt grows), regenerating the
 * WHOLE demo via the client retry loop is expensive and tends to re-fail the
 * same way for the same scenario. Instead, expand ONLY the largest
 * (transaction) table with a small follow-up LLM call that appends schema-
 * and FK-consistent CSV rows. Best-effort: on any failure the table is left
 * as-is and the hard floor in validateGeneratedData still decides.
 */
function expandThinTables_(parsed, options) {
  try {
    const profile = getDataProfile_(options.dataProfile || 'standard');
    if (!parsed.tables || !parsed.tables.length) return;
    const counts = parsed.tables.map(t => ({ t: t, rows: Math.max(0, String(t.csvData || '').trim().split('\n').length - 1) }));
    const maxEntry = counts.reduce((a, b) => (b.rows > a.rows ? b : a), counts[0]);
    if (maxEntry.rows >= profile.txnRowTarget) return; // dense enough
    const need = Math.min(profile.txnRowTarget, 120) - maxEntry.rows;
    if (need <= 0) return;
    const table = maxEntry.t;
    const lines = String(table.csvData).trim().split('\n');
    const header = parseCSVLine(lines[0]);
    // FK domains: appended rows must reuse key values that already exist in
    // the owning tables, so every JOIN keeps working.
    const fkDomains = [];
    for (const col of header) {
      if (!col.endsWith('_id')) continue;
      for (const other of parsed.tables) {
        if (other === table) continue;
        const oLines = String(other.csvData || '').trim().split('\n');
        const oHeader = parseCSVLine(oLines[0] || '');
        const idx = oHeader.indexOf(col);
        if (idx === -1) continue;
        const vals = [];
        for (let i = 1; i < oLines.length && vals.length < 40; i++) {
          const v = parseCSVLine(oLines[i])[idx];
          if (v && vals.indexOf(v) === -1) vals.push(v);
        }
        if (vals.length) fkDomains.push('- ' + col + ' MUST be one of: ' + vals.join(', '));
        break;
      }
    }
    const sampleRows = lines.slice(0, 6).join('\n');
    const prompt = 'You are extending a synthetic demo dataset. Append EXACTLY ' + need +
      ' additional CSV data rows to the table "' + table.tableName + '".\n\n' +
      'Schema (name:type): ' + (table.schema || []).map(function(c){ return c.name + ':' + c.type; }).join(', ') + '\n' +
      'Existing rows (header + first samples - match their style, language, value ranges, and temporal window):\n' + sampleRows + '\n\n' +
      (fkDomains.length ? 'FOREIGN KEY CONSTRAINTS (STRICT):\n' + fkDomains.join('\n') + '\n\n' : '') +
      'Rules: unique new primary-key values continuing the existing numbering pattern; realistic variety (no copy-paste repetition); keep the same language as the existing string values; wrap STRING values in double quotes, never numbers; NO header row; NO code fences; NO commentary. Output ONLY the ' + need + ' CSV lines.';
    const resp = callVertexAIWithRetry(prompt);
    const fenceRe = new RegExp(String.fromCharCode(96, 96, 96) + '[a-z]*\\n?', 'g');
    const newLines = String(resp).replace(fenceRe, '').split('\n')
      .map(function(s){ return s.trim(); })
      .filter(function(s){ return s && parseCSVLine(s).length >= Math.max(2, header.length - 2); });
    if (newLines.length >= Math.min(10, need)) {
      table.csvData = String(table.csvData).trim() + '\n' + newLines.join('\n');
      console.log('[DENSITY REPAIR] ' + table.tableName + ': +' + newLines.length + ' rows (was ' + maxEntry.rows + ')');
    } else {
      console.warn('[DENSITY REPAIR] insufficient rows returned (' + newLines.length + ') for ' + table.tableName);
    }
  } catch (e) {
    console.warn('[DENSITY REPAIR] skipped: ' + e.message);
  }
}

function validateGeneratedData(planResult, targetRows, dataProfileId) {
  const profile = getDataProfile_(dataProfileId || 'standard');
  if (!planResult.tables || planResult.tables.length === 0) {
    throw new Error('No table definitions generated');
  }

  // v11.24: hard row-count floor. Observed live (v11.23 pharma demo): the
  // planner emitted 8-row transaction tables (standard floor is 30) while
  // using only a fraction of the output token budget - row-mandate adherence
  // dilutes as the planning prompt grows. Throwing here routes the run into
  // the client's existing auto-retry, so an under-dense response is
  // regenerated instead of shipping a hollow demo.
  const _rowCounts = planResult.tables.map(t => ({
    name: t.tableName,
    rows: Math.max(0, String(t.csvData || '').trim().split('\n').length - 1)
  }));
  const _maxRows = Math.max.apply(null, _rowCounts.map(r => r.rows));
  if (_maxRows < profile.txnMinRows) {
    throw new Error('Data density below profile floor: largest table has ' + _maxRows +
      ' rows (< ' + profile.txnMinRows + ' required for the ' + profile.label + ' profile). Row counts: ' +
      _rowCounts.map(r => r.name + '=' + r.rows).join(', '));
  }
  
  for (const table of planResult.tables) {
    if (!table.schema || !table.csvData) throw new Error(`Incomplete table data for "${table.tableName}"`);
    
    // Validate and repair CSV/Schema column count mismatch
    const lines = table.csvData.trim().split('\n');
    if (lines.length === 0) throw new Error(`Empty CSV data for "${table.tableName}"`);
    
    const csvHeaders = parseCSVLine(lines[0]);
    const schemaColumnCount = table.schema.length;
    const csvColumnCount = csvHeaders.length;
    
    if (csvColumnCount !== schemaColumnCount) {
      // console.log(`Column mismatch for "${table.tableName}": CSV has ${csvColumnCount} columns, schema has ${schemaColumnCount}. Repairing...`);
      
      // Rebuild schema from CSV headers, inferring types from existing schema or defaulting to STRING
      const schemaMap = {};
      for (const field of table.schema) {
        schemaMap[field.name.toLowerCase()] = field;
      }
      
      const repairedSchema = csvHeaders.map(headerName => {
        const normalizedName = headerName.trim().toLowerCase();
        if (schemaMap[normalizedName]) {
          return schemaMap[normalizedName];
        }
        // Default to STRING for unknown columns
        return { name: headerName.trim(), type: 'STRING', description: 'Auto-generated field' };
      });
      
      table.schema = repairedSchema;
      // console.log(`Repaired schema for "${table.tableName}" to ${repairedSchema.length} columns.`);
    }

    const expectedColumnCount = table.schema.length;
    
    // --- Row count threshold check ---
    const dataRowCount = lines.length - 1; // Exclude header
    const hasTimestamp = table.schema.some(f => ['TIMESTAMP', 'DATE', 'DATETIME'].includes(f.type.toUpperCase()));
    const isMasterTable = !hasTimestamp && table.schema.length <= 8;
    const minExpectedRows = isMasterTable ? profile.masterMinRows : profile.txnMinRows;
    
    if (dataRowCount < minExpectedRows) {
      console.warn(`[CSV QUALITY] Table "${table.tableName}" has only ${dataRowCount} rows (expected at least ${minExpectedRows}). Data may be sparse.`);
    }

    // --- Per-row column validation and repair ---
    const repairedLines = [];
    let repairCount = 0;
    
    for (let lineIdx = 0; lineIdx < lines.length; lineIdx++) {
      const line = lines[lineIdx];
      let parts = parseCSVLine(line);
      
      // Repair rows with wrong column count
      if (parts.length !== expectedColumnCount) {
        if (lineIdx === 0) {
          // Header row mismatch - this shouldn't happen after schema repair, but handle it
          console.warn(`[CSV REPAIR] Header row has ${parts.length} columns, expected ${expectedColumnCount}. Skipping repair.`);
        } else {
          // Data row mismatch - repair by padding or truncating
          if (parts.length < expectedColumnCount) {
            // Pad with empty values
            while (parts.length < expectedColumnCount) {
              parts.push('');
            }
          } else {
            // Truncate excess columns
            parts = parts.slice(0, expectedColumnCount);
          }
          repairCount++;
        }
      }
      repairedLines.push(parts);
    }
    
    if (repairCount > 0) {
      console.warn(`[CSV REPAIR] Repaired ${repairCount} malformed rows in "${table.tableName}".`);
    }


    // --- Row Count Validation ---
    // Note: We intentionally do NOT pad with generated placeholder data.
    // It's better to have fewer realistic rows than many fake placeholder values
    // like "theater_name_13" or "location_prefecture_14".
    const currentDataRows = repairedLines.length - 1; // Exclude header
    if (currentDataRows < targetRows) {
      console.warn(`[ROW COUNT] Table "${table.tableName}" has ${currentDataRows} rows (target: ${targetRows}). AI did not generate enough rows.`);
    }

    // --- Robust Data Cleaning & Type Validation ---
    let typeRepairCount = 0;
    const cleanedLines = repairedLines.map((parts, lineIdx) => {
      // Skip header row for type validation
      if (lineIdx === 0) {
        return parts.map(v => v.replace(/^"|"$/g, '')).map((v, colIdx) => {
          const field = table.schema[colIdx];
          const type = field ? field.type.toUpperCase() : 'STRING';
          if (['INTEGER', 'FLOAT', 'DOUBLE', 'NUMBER', 'INT64', 'FLOAT64'].includes(type)) {
            return v;
          }
          return `"${v.replace(/"/g, '""')}"`;
        }).join(',');
      }
      
      // Data rows: validate and repair each cell
      return parts.map((val, colIdx) => {
        const field = table.schema[colIdx];
        const type = field ? field.type.toUpperCase() : 'STRING';
        const columnName = field ? field.name : `col${colIdx}`;
        
        // Use the new validation helper
        const result = validateAndRepairValue(val, type, columnName, lineIdx - 1);
        if (result.repaired) {
          typeRepairCount++;
        }
        return result.value;
      }).map((v, colIdx) => {
        // Final Re-quoting as per BigQuery requirements
        const field = table.schema[colIdx];
        const type = field ? field.type.toUpperCase() : 'STRING';
        
        if (['INTEGER', 'FLOAT', 'DOUBLE', 'NUMBER', 'INT64', 'FLOAT64'].includes(type)) {
          return v; // Numbers stay unquoted
        }
        // Strings, Dates, etc. get strictly quoted
        return `"${v.replace(/"/g, '""')}"`;
      }).join(',');
    });
    
    if (typeRepairCount > 0) {
      console.warn(`[TYPE REPAIR] Fixed ${typeRepairCount} type violations in "${table.tableName}".`);
    }
    
    table.csvData = cleanedLines.join('\n');
  }
}

/**
 * Validates and repairs a cell value based on its declared type.
 * Returns the repaired value and whether repair was needed.
 * @param {string} value - The raw value
 * @param {string} type - The column type (INTEGER, FLOAT, DATE, STRING, etc.)
 * @param {string} columnName - Column name for context-aware defaults
 * @param {number} rowIndex - Row index for generating sequential defaults
 * @returns {{value: string, repaired: boolean}}
 */
function validateAndRepairValue(value, type, columnName, rowIndex) {
  const upperType = type.toUpperCase();
  const trimmedVal = value.trim();
  
  // Empty values are allowed (NULL)
  if (trimmedVal === '') {
    return { value: '', repaired: false };
  }
  
  switch(upperType) {
    case 'INT64':
    case 'INTEGER':
      // Check for range expressions like "51-100"
      const rangeMatch = trimmedVal.match(/^(\d+)\s*[-–—]\s*\d+$/);
      if (rangeMatch) {
        return { value: rangeMatch[1], repaired: true };
      }
      // Check for valid integer
      if (/^-?\d+$/.test(trimmedVal)) {
        return { value: trimmedVal, repaired: false };
      }
      // Try to extract a number
      const intMatch = trimmedVal.match(/-?\d+/);
      if (intMatch) {
        return { value: intMatch[0], repaired: true };
      }
      // Generate fallback
      return { value: generateDefaultValue(upperType, columnName, rowIndex), repaired: true };
      
    case 'FLOAT64':
    case 'FLOAT':
    case 'DOUBLE':
    case 'NUMBER':
      // Check for valid float
      if (/^-?\d*\.?\d+$/.test(trimmedVal)) {
        return { value: trimmedVal, repaired: false };
      }
      // Try to extract a number
      const floatMatch = trimmedVal.match(/-?\d+\.?\d*/);
      if (floatMatch) {
        return { value: floatMatch[0], repaired: true };
      }
      // Generate fallback
      return { value: generateDefaultValue(upperType, columnName, rowIndex), repaired: true };
      
    case 'DATE':
      // Check for valid date format YYYY-MM-DD
      if (/^\d{4}-\d{2}-\d{2}$/.test(trimmedVal)) {
        return { value: trimmedVal, repaired: false };
      }
      // Try to extract a date pattern
      const dateMatch = trimmedVal.match(/\d{4}-\d{2}-\d{2}/);
      if (dateMatch) {
        return { value: dateMatch[0], repaired: true };
      }
      // Generate fallback
      return { value: generateDefaultValue(upperType, columnName, rowIndex), repaired: true };
      
    case 'TIMESTAMP':
    case 'DATETIME':
      // Accept ISO format or similar, then validate time ranges
      if (/^\d{4}-\d{2}-\d{2}[T ]\d{2}:\d{2}/.test(trimmedVal)) {
        // Validate hour/minute/second ranges (hour 0-23, min/sec 0-59)
        const tsTimeMatch = trimmedVal.match(/(\d{2}):(\d{2})(?::(\d{2}))?/);
        if (tsTimeMatch) {
          const h = parseInt(tsTimeMatch[1], 10);
          const m = parseInt(tsTimeMatch[2], 10);
          const s = tsTimeMatch[3] ? parseInt(tsTimeMatch[3], 10) : 0;
          if (h > 23 || m > 59 || s > 59) {
            // Clamp to valid range
            const fixedH = String(Math.min(h, 23)).padStart(2, '0');
            const fixedM = String(Math.min(m, 59)).padStart(2, '0');
            const fixedS = String(Math.min(s, 59)).padStart(2, '0');
            const fixedTs = trimmedVal.replace(/\d{2}:\d{2}(:\d{2})?/, `${fixedH}:${fixedM}:${fixedS}`);
            return { value: fixedTs, repaired: true };
          }
        }
        return { value: trimmedVal, repaired: false };
      }
      // If it's a date, convert to timestamp
      const tsDateMatch = trimmedVal.match(/^(\d{4}-\d{2}-\d{2})$/);
      if (tsDateMatch) {
        return { value: `${tsDateMatch[1]} 00:00:00 UTC`, repaired: true };
      }
      // Generate fallback as timestamp
      return { value: generateDefaultValue('TIMESTAMP', columnName, rowIndex), repaired: true };
      
    default:
      // STRING type - accept as-is
      return { value: trimmedVal, repaired: false };
  }
}

/**
 * Generates a sensible default value for a given type and column.
 * @param {string} type - The column type
 * @param {string} columnName - Column name for context-aware generation
 * @param {number} rowIndex - Row index for sequential IDs
 * @returns {string} A valid default value
 */
function generateDefaultValue(type, columnName, rowIndex) {
  const upperType = type.toUpperCase();
  const lowerColName = columnName.toLowerCase();
  
  switch(upperType) {
    case 'INT64':
    case 'INTEGER':
      // ID columns get sequential values
      if (lowerColName.endsWith('_id') || lowerColName === 'id') {
        return String(rowIndex + 1);
      }
      // Count/quantity columns
      if (lowerColName.includes('count') || lowerColName.includes('quantity') || lowerColName.includes('num')) {
        return String(Math.floor(Math.random() * 100) + 1);
      }
      // Default integer
      return String(Math.floor(Math.random() * 1000));
      
    case 'FLOAT64':
    case 'FLOAT':
    case 'DOUBLE':
    case 'NUMBER':
      // Price/amount columns
      if (lowerColName.includes('price') || lowerColName.includes('amount') || lowerColName.includes('cost')) {
        return (Math.random() * 1000 + 10).toFixed(2);
      }
      // Rating/score columns
      if (lowerColName.includes('rating') || lowerColName.includes('score')) {
        return (Math.random() * 4 + 1).toFixed(1);
      }
      // Default float
      return (Math.random() * 100).toFixed(2);
      
    case 'DATE':
      // Generate a date within the past year
      const d = new Date();
      d.setDate(d.getDate() - Math.floor(Math.random() * 365));
      return d.toISOString().split('T')[0];
      
    case 'TIMESTAMP':
    case 'DATETIME':
      const dt = new Date();
      dt.setDate(dt.getDate() - Math.floor(Math.random() * 365));
      return dt.toISOString();
      
    default:
      // STRING type
      return `${columnName}_${rowIndex + 1}`;
  }
}

function parseCSVLine(line) {
  const result = [];
  let current = '';
  let inQuotes = false;
  
  for (let i = 0; i < line.length; i++) {
    const char = line[i];
    const nextChar = line[i + 1];
    
    if (char === '"') {
      if (inQuotes && nextChar === '"') {
        // Handle escaped double quotes: ""
        current += '"';
        i++; // Skip the next quote
      } else {
        inQuotes = !inQuotes;
      }
    } else if (char === ',' && !inQuotes) {
      result.push(current.trim());
      current = '';
    } else {
      current += char;
    }
  }
  result.push(current.trim());
  return result;
}

function repairTruncatedJson(jsonStr) {
  try { JSON.parse(jsonStr); return jsonStr; } catch (e) {}
  
  let fixed = jsonStr;
  const csvDataMatch = fixed.match(/"csvData"\s*:\s*"([^"]*?)$/s);
  if (csvDataMatch) {
    const lastNewline = fixed.lastIndexOf('\\n');
    if (lastNewline > 0) fixed = fixed.substring(0, lastNewline) + '"';
  }
  
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

// ===========================================
// Step 4: Setup Script Generation (Portable version)
// ===========================================

/**
 * Generates a short, filesystem-safe base name from the user's goal.
 * @param {string} userGoal - The user's business problem description
 * @param {string} suffix - Unique suffix for collision avoidance
 * @returns {string} A short, descriptive base name (e.g. retail-inventory-abcd1234)
 */
function generateBaseName(userGoal, suffix) {
  // Use AI to generate a short English identifier
  const prompt = `Generate a short, filesystem-safe identifier (2-3 words, lowercase, hyphens only) that describes this business problem:

"${userGoal}"

Rules:
- Use ONLY lowercase letters and hyphens (no numbers, no special characters)
- Maximum 20 characters
- Must be descriptive of the business domain
- Examples: "retail-inventory", "bakery-sales", "hotel-booking", "logistics-fleet"

Return ONLY the name, nothing else.`;

  try {
    const result = callVertexAI(prompt);
    let cleanName = result.trim().toLowerCase()
      .replace(/[^a-z-]/g, '-')     // Replace non-alphabet/non-hyphen with hyphen
      .replace(/-+/g, '-')           // Collapse multiple hyphens
      .replace(/^-|-$/g, '')         // Remove leading/trailing hyphens
      .substring(0, 15)              // Limit length to 15 to stay under 26 total with suffix
      .replace(/-+$/g, '');          // Remove trailing hyphens after truncation
    
    if (cleanName.length < 3) cleanName = 'demo-env';
    return `${cleanName}-${suffix}`;
  } catch (e) {
    return `env-${suffix}`;
  }
}

// Builds the Managed Agent (Antigravity) system instruction at generation time.
// The returned string is emitted through a quoted heredoc into
// managed_agent_instruction.txt, so it passes verbatim (runtime value, never
// re-parsed as a JS template literal). English harness text only - the agent
// is instructed to match the language of each delegated task.
function buildManagedAgentInstruction_(businessInstruction, datasetId, fsCollection, hasSkills, workspaceActions, browserFindings, operatingModel) {
  const nl = '\n';
  const text =
    'You are an autonomous specialist agent working inside a secure cloud sandbox with a bash terminal, a persistent filesystem, code execution, pip/npm installs, Google Search, and web page reading.' + nl +
    'You receive delegated tasks from a front-line business assistant and must complete them END TO END without asking questions: make reasonable assumptions and state them in your final report.' + nl + nl +
    '--- BUSINESS CONTEXT ---' + nl +
    (businessInstruction || 'No additional business context provided.') + nl +
    '--- END BUSINESS CONTEXT ---' + nl + nl +
    (operatingModel ? (
    '--- OPERATING MODEL (organizational context) ---' + nl +
    operatingModel + nl +
    'Frame your deliverables within this operating model: attribute findings to the departments that own the data, address recommendations to the department that owns the decision, and describe hand-offs between departments explicitly.' + nl +
    '--- END OPERATING MODEL ---' + nl + nl) : '') +
    'SANDBOX SOFTWARE (use it - do not rediscover it)' + nl +
    '- Preinstalled Python 3.11 packages: pandas, numpy, beautifulsoup4, requests, pyyaml. Preinstalled Node.js 20: typescript, create-vite, create-next-app. Preinstalled UNIX tools: git, ripgrep (rg), fd, jq, curl, wget, rsync, tree, bc, unzip.' + nl +
    '- Additional pip/npm installs are allowed and PERSIST in this environment snapshot across tasks - try the import first (a warm-up usually preinstalled python-pptx, python-docx, reportlab, matplotlib, japanize-matplotlib, pypdf); install only what is actually missing, never reinstall.' + nl +
    '- You run as a NON-ROOT user: global npm installs need a user prefix (mkdir -p $HOME/.npm-global && npm config set prefix $HOME/.npm-global before npm install -g), and the resulting binaries live at $HOME/.npm-global/bin/<name> - invoke them by absolute path because PATH exports do not persist between commands. Plain npm install -g fails with EACCES; that is a permissions matter, not a system incompatibility.' + nl +
    '- Work data-first: load query results and CSV/TSV files into pandas for aggregation, joins, and statistics instead of hand-parsing text. Parse fetched web pages with beautifulsoup4. Use git to version multi-step work you may need to roll back.' + nl + nl +
    'LONG-HORIZON WORKING PRACTICES' + nl +
    '- For any multi-step task, FIRST write plan.md breaking the work into phases (research, data analysis, visuals, assembly, verification), then execute phase by phase and append progress notes to plan.md as you go - the filesystem is your checkpoint across the whole run.' + nl +
    '- Save every intermediate product to a file before moving on (query results as CSV, computed tables, chart PNGs, drafts): later phases and repeat runs must be able to reuse them without redoing the work.' + nl +
    '- When the task asks for MULTIPLE deliverables, gather data and build charts ONCE, then assemble each deliverable from the shared assets - never re-research per deliverable.' + nl + nl +
    'DATA ACCESS' + nl +
    '- BigQuery MCP tools give you direct read access to the demo dataset: ' + datasetId + '. Firestore MCP tools expose the operational collection: ' + fsCollection + '. Dataplex Knowledge Catalog MCP tools let you discover and understand these data assets semantically (treat the catalog as read-only).' + nl +
    '- Query internal data EARLY in the task: the data-tool credentials attached to each delegation expire after about an hour.' + nl + nl +
    (browserFindings ? (
    'BROWSER FINDINGS' + nl +
    '- When the task message contains a "BROWSER FINDINGS" block inside INPUT DATA, it is live web data gathered moments before delegation by the requesting assistant using its real interactive browser. Treat it as fresh and authoritative: build on it, cite its source URLs in your deliverables, and do NOT spend steps re-fetching the same pages.' + nl +
    '- You have NO interactive browser yourself. If additional web information is needed beyond the findings, use your read-only tools (Google Search, web page reading). If a page truly requires interaction (login, form entry, clicking through an app), state that limitation in your report instead of attempting it, and never claim you operated a browser.' + nl + nl) : '') +
    (hasSkills ? (
    'SKILLS' + nl +
    '- Skill packs are mounted at /.agent/skills. BEFORE building any deliverable (presentation deck, document, PDF, web page), list that directory, READ the matching SKILL.md, and follow its process, design system, and verification steps exactly.' + nl +
    '- If the modern-web-guidance skill is present and you are building web content, consult it for modern web-platform best practices. Export DISABLE_TELEMETRY=1 before using its CLI.' + nl + nl) : '') +
    (workspaceActions ? (
    'WORKSPACE ACTIONS' + nl +
    '- When the task message contains a WORKSPACE ACCESS section, you can act on the requesting user\'s Google Workspace via the gws CLI (Gmail drafts, Chat messages, Calendar events, Drive). Export the provided token as instructed, and consult the gws-* skills under /.agent/skills first.' + nl +
    '- INSTALLING gws: the warm-up usually pre-installs it at $HOME/bin/gws (invoke it by that absolute path - PATH exports do not persist between commands). If it is missing, install the static musl binary: mkdir -p $HOME/bin && curl -sL https://github.com/googleworkspace/cli/releases/latest/download/google-workspace-cli-x86_64-unknown-linux-musl.tar.gz | tar xz -C $HOME/bin ./gws && chmod +x $HOME/bin/gws. Do NOT install via npm: the npm-delivered Linux binary requires GLIBC 2.39, which this sandbox does not have, and plain npm -g also fails with EACCES (no root).' + nl +
    '- CHAT POSTING FAILURES: if a Chat post fails with a 403 / PERMISSION_DENIED / configuration error, the cause is almost always that the demo project has not completed the ONE-TIME Google Chat API app configuration (a console step in the setup tutorial). State EXACTLY that in your report, include this link for the admin: https://console.cloud.google.com/apis/api/chat.googleapis.com/hangouts-chat - and include the full message text you intended to post so the assistant can relay it. NEVER invent explanations like security restrictions or tenant policy.' + nl +
    '- DRIVE SAVES: when the task asks for a file saved to the user\'s Google Drive as Google Slides / Docs / Sheets, upload it with the gws CLI using Drive import-conversion (office file uploaded with the target Google mime type). Do it as soon as the file is ready, verify by reading the file metadata back, and put the returned webViewLink in your report. If the Drive upload fails, still deliver the file through the upload URLs and say the Drive save failed so the assistant can retry it.' + nl +
    '- DRIVE SAVES: when the task asks for a file in the user\'s Google Drive (or as Google Slides / Docs / Sheets), upload it yourself with the gws CLI using an import-conversion to the native Google format (pptx to Google Slides, docx to Google Docs, xlsx to Google Sheets), then include the returned Drive webViewLink in your report. ALSO upload the original office file to the matching deliverable upload URL as a backup.' + nl +
    '- Do Workspace operations EARLY in the task: the token expires after about an hour.' + nl +
    '- HARD GUARDRAILS: never SEND email (drafts only, unless the task explicitly says to send); never delete anything in Workspace; post Chat messages only to spaces the task explicitly names; never write the token into your report, logs, code, or files.' + nl +
    '- CHAT SPACES: when the task names a Chat space, search for it first; if no space with that name exists, CREATE the space with that exact name via the gws CLI and then post there (demo environments often lack the space - creating it is expected, not an error). State in your report that you created it. If creation fails (e.g. missing permission), report the failure instead of posting elsewhere.' + nl +
    '- EMAIL ENCODING: non-ASCII email headers (Subject, display names) MUST be RFC 2047 MIME-encoded (for example =?UTF-8?B?...?=). After creating a draft, read it back and verify the subject decodes correctly; delete and recreate it if it is garbled.' + nl +
    '- REPORTING DRAFTS: when you create a Gmail draft, your report must state it ALREADY EXISTS in the user Gmail Drafts folder, with the draft subject and this link: https://mail.google.com/mail/u/0/#drafts - never paste the full email body into the report for manual copying.' + nl +
    '- If no WORKSPACE ACCESS section is present, you have no Workspace access for this task - say so in the report instead of guessing.' + nl + nl) : (
    'WORKSPACE LIMITS' + nl +
    '- This environment has NO Google Workspace access: no WORKSPACE ACCESS section or credentials will ever be provided, and interactive OAuth flows CANNOT complete here. Do NOT install, authenticate, or wait on the gws CLI (or any Workspace / Admin SDK API) - authentication will block forever.' + nl +
    '- If a task asks for Workspace operations (Gmail, Chat, Calendar, Drive, or user directory / security group / permission audits), state this limitation prominently in your report, then complete every remaining part of the task that the provided data tools DO support (BigQuery, Firestore, web research, file deliverables) and deliver those results. Never stall on the missing access.' + nl + nl)) +
    'QUALITY GATE (before ANY upload)' + nl +
    '- Run the Verification checklist of the SKILL.md you followed against the finished file. If any check fails, fix and REBUILD - at least one review-and-revise pass is mandatory even when everything looks fine.' + nl +
    '- The bar is board-ready: real numbers from the actual data, sources with URLs for every external claim, assertion-style headings that state the finding, zero placeholder text or lorem ipsum, consistent fonts and colors, and no garbled non-ASCII text (open the built file and check rendered strings, not just your source).' + nl + nl +
    'DELIVERABLES' + nl +
    '- If the task message contains an upload URL, upload every deliverable file with: curl -sS -X PUT --upload-file <file> "<upload url>" (retry once on failure).' + nl +
    '- UPLOADING IS PART OF THE TASK, NOT OPTIONAL: a file that exists only in your workspace has NOT been delivered - the requester can only receive files through the upload URLs. Verify every upload succeeded by checking the HTTP status (append -w "%{http_code}" to the curl call and expect 200), and list each uploaded filename WITH its HTTP status in your final report. If an upload still fails after the retry, say so explicitly. NEVER report a file as delivered (in any language) unless its upload returned 200. A task that produced files but did not upload them is INCOMPLETE.' + nl +
    '- If the task text references tool names you do not have (for example publish_dashboard or save_deliverables_to_drive), IGNORE the tool reference and achieve the intended OUTCOME with your own tools: build the file yourself and deliver it through the provided upload URLs. Never stall or give up because a named tool does not exist here.' + nl +
    '- ALWAYS end with a complete, self-contained markdown report of everything you did, found, and produced: key numbers, sources with URLs for any web research, and the exact filenames you uploaded. This report is the only channel back to the requester besides uploaded files.' + nl + nl +
    'LANGUAGE' + nl +
    '- Write the final report and ALL deliverable content (slide text, document body, page copy) in the SAME language as the delegated task description. Code, filenames, and logs stay in English.' + nl + nl +
    'SAFETY' + nl +
    '- Operate only inside this sandbox and the provided data tools. Never attempt to reach systems or credentials beyond what the task provides.';
  // Defence: the text is emitted through a quoted heredoc in the setup script.
  return text.split('__MA_SYSINSTR_EOF__').join('MA_SYSINSTR_EOF');
}

function generateSetupScript(params) {
  const { datasetId, systemInstruction, businessInstruction, referenceDate, publicDatasetId, suffix, tables, firestore, userGoal, dirName, agentShortName, oneSentenceSummary, operatingModel, enableWorkspaceMcp, enableComputerUse, enableManagedAgent, enableWorkspaceAuth, metadata } = params;

  // Derived feature gates (see AGENTS.md section 14):
  // - workspaceAuthEnabled: the GE OAuth authorization (user token) exists.
  //   True for full Workspace MCP OR the lightweight auth-only toggle.
  // - driveHandoffEnabled: the Managed Agent can hand results into the user's
  //   Workspace (Drive save + gws CLI actions) - needs BOTH capabilities.
  const workspaceAuthEnabled = !!(enableWorkspaceMcp || enableWorkspaceAuth);
  const driveHandoffEnabled = !!(enableManagedAgent && workspaceAuthEnabled);
  // - preBrowseEnabled: composite tasks can be delegated with live browser
  //   findings gathered by the root agent BEFORE delegation (pre-browse) -
  //   needs BOTH the browser tooling and the autonomous agent.
  const preBrowseEnabled = !!(enableManagedAgent && enableComputerUse);

  // ── Deduplicate importedMcpList by github_url ──
  // When the same MCP repo appears multiple times (e.g. from catalog + URL import),
  // merge their required_env_vars (deduped by key) into a single entry to avoid
  // creating duplicate Secret Manager versions.
  if (params.importedMcpList && params.importedMcpList.length > 0) {
    const seen = new Map();
    params.importedMcpList.forEach(mcp => {
      const url = mcp.type === 'remote' ? mcp.endpoint_url : mcp.github_url;
      if (seen.has(url)) {
        // Merge env vars (add any new keys from the duplicate)
        const existing = seen.get(url);
        const existingKeys = new Set(existing.required_env_vars.map(v => v.key));
        (mcp.required_env_vars || []).forEach(v => {
          if (!existingKeys.has(v.key)) {
            existing.required_env_vars.push(v);
          }
        });
        // Merge capabilities
        if (mcp.capabilities) {
          const existingCaps = new Set(existing.capabilities || []);
          mcp.capabilities.forEach(c => existingCaps.add(c));
          existing.capabilities = [...existingCaps];
        }
      } else {
        seen.set(url, JSON.parse(JSON.stringify(mcp))); // deep clone
      }
    });
    params.importedMcpList = [...seen.values()];
  }

  const fsCollection = `${dirName}-data`;
  const currencySymbol = (metadata && metadata.currencySymbol) || '$';
  
  const bashEscape = (str) => str ? str.replace(/'/g, "'\\''") : '';
  const safeShortName = bashEscape(agentShortName) || 'Agent';
  const safeSummary = bashEscape(oneSentenceSummary) || 'A2A Agent';

  // Agent-template ref: generation-time resolution + reachability check.
  // A branch-name TEMPLATE_REF (the committed default is 'main') is resolved
  // HERE to a concrete commit SHA and that SHA is baked into the generated
  // script, keeping every script reproducible while the repo never has to
  // commit its own merge SHA. A 40-hex TEMPLATE_REF (Script Property)
  // hard-pins and skips resolution. On API failure the script falls back to
  // fetching the ref as written (a branch fetch still works - it just tracks
  // the tip), and a banner in the script preview explains what happened.
  let templateRef = CONFIG.TEMPLATE_REF;
  let templateRefBanner = '';
  try {
    const repoMatch = CONFIG.TEMPLATE_REPO.match(/github\.com[:\/]([^\/]+\/[^\/.]+)/);
    if (repoMatch) {
      const refIsSha = /^[0-9a-f]{40}$/i.test(templateRef);
      const refResp = UrlFetchApp.fetch(
        'https://api.github.com/repos/' + repoMatch[1] + '/commits/' + encodeURIComponent(templateRef),
        { muteHttpExceptions: true, headers: getGithubHeaders() });
      if (refResp.getResponseCode() === 200) {
        if (!refIsSha) {
          const resolvedSha = (JSON.parse(refResp.getContentText()) || {}).sha;
          if (/^[0-9a-f]{40}$/i.test(resolvedSha || '')) {
            templateRef = resolvedSha;
          }
        }
      } else if (refIsSha) {
        templateRefBanner = '# =========================================================\n' +
          '# WARNING (generation-time check): agent-template ref\n' +
          '#   ' + templateRef + '\n' +
          '# was NOT reachable in ' + CONFIG.TEMPLATE_REPO + '\n' +
          '# when this script was generated. The template fetch below will\n' +
          '# likely fail. Update the TEMPLATE_REF Script Property and regenerate.\n' +
          '# =========================================================\n\n';
      } else {
        templateRefBanner = '# =========================================================\n' +
          '# NOTE (generation-time check): the agent-template ref \'' + templateRef + '\'\n' +
          '# could not be resolved to a commit SHA when this script was\n' +
          '# generated (GitHub API unreachable or rate-limited). The fetch\n' +
          '# below will track the CURRENT TIP of that ref instead of a fixed\n' +
          '# commit. Regenerate later for a fully pinned script.\n' +
          '# =========================================================\n\n';
      }
    }
  } catch (e) { /* offline generation: the runtime fetch reports any problem */ }


  // == Pinned Dependency Versions ==
  // All dependency versions are managed here. Update this block when upgrading.
  // See AGENTS.md Section 13 for the update checklist.
  const PINNED_DEPS = {
    // Critical: A2UI SDK -- MUST use git+commit (PyPI 0.2.1 lacks version param)
    //   Tested: HEAD ade478f with version='0.8' -> application/json+a2ui (GE compatible)
    //   Constraint: a2ui@ade478f requires google-genai>=1.27.0, google-adk>=1.28.1
    a2ui: 'a2ui-agent-sdk @ git+https://github.com/google/A2UI.git@ade478faf8dcad611b5efb6b864dcbfbc4a51f68#subdirectory=agent_sdks/python',

    // Python SDKs -- floor-only (>=) to avoid pip resolution conflicts
    // Upper bounds are NOT set unless a package has caused a breaking change.
    adk: 'google-adk[a2a]>=1.31.1',
    mcp: 'mcp>=1.24.0',
    genai: 'google-genai>=1.27.0',
    a2a: 'a2a-sdk>=0.2.0,<1.0.0',

    // Google Cloud SDKs -- stable, floor-only
    aiplatform: 'google-cloud-aiplatform[agent_engines]>=1.112.0',
    storage: 'google-cloud-storage>=2.14.0',
    scheduler: 'google-cloud-scheduler>=2.0.0',
    pubsub: 'google-cloud-pubsub>=2.0.0',
    firestore: 'google-cloud-firestore>=2.16.0',
    logging: 'google-cloud-logging>=3.0.0',

    // Utilities -- floor-only
    dotenv: 'python-dotenv>=1.0.0',
    dbDtypes: 'db-dtypes>=1.0.0',
    otel: 'opentelemetry-api>=1.20.0',

    // Build tools -- exact pin (infrastructure, not pip-resolved)
    pythonImage: 'python:3.11.12-slim',
    uvImage: 'ghcr.io/astral-sh/uv:0.11.17',
    uvVersion: '0.11.17',
    supergateway: 'supergateway@3.4.3',

    // Viewer app -- floor-only
    viewerFunctionsFramework: 'functions-framework>=3.5.0',
    viewerFlask: 'flask>=3.0.3',
    viewerFirestore: 'google-cloud-firestore>=2.16.0',

    // Computer Use (browser agent) -- only added when enableComputerUse is set.
    // playwright pin matches the official reference impl
    // (github.com/google-gemini/computer-use-preview). The gen ai floor is bumped
    // to the version exposing types.ComputerUse/types.Environment for the
    // generate_content computer_use tool config.
    playwright: 'playwright==1.55.0',
    genaiComputerUse: 'google-genai>=2.7.0',
  };

  
  const escapedInstruction = systemInstruction
    .replace(/\\/g, '\\\\\\\\')
    .replace(/'/g, "'\\''")
    .replace(/\{/g, '{{')
    .replace(/\}/g, '}}')
    .replace(/\n/g, '\\n');

  // == Managed Autonomous Agent (Antigravity) generation-time assets ==
  // Craft skills come from this repo's demo-skills/ dir (main branch, fetched
  // at generation time; fail-soft) and are emitted as quoted heredocs. The
  // agent id must be 1-63 chars, lowercase letters/digits/hyphens, starting
  // with a letter and ending with a letter or digit (Agents API constraint).
  // Deliverable skills are real files in the fetched agent template
  // (agent_template/demo_skills/); the setup script copies them into skills/.
  const managedSkillsBash = enableManagedAgent
    ? 'mkdir -p skills\ncp -r "$GE_TPL"/demo_skills/professional-document "$GE_TPL"/demo_skills/professional-presentation "$GE_TPL"/demo_skills/web-report skills/\n'
    : '';
  const managedAgentId = (dirName + '-auto').toLowerCase().replace(/[^a-z0-9-]/g, '-').substring(0, 63).replace(/-+$/, '');
  const managedAgentInstruction = enableManagedAgent
    ? buildManagedAgentInstruction_(businessInstruction || '', datasetId, fsCollection, true, workspaceAuthEnabled, preBrowseEnabled, operatingModel || '')
    : '';

  // Build local BQ creation commands
  let bqCommands = `echo "🗄 Creating BigQuery Dataset: ${datasetId}..."\n`;
  bqCommands += `bq mk --dataset --location=US ${datasetId} 2>/dev/null || echo "    ✅ Dataset already exists."\n\n`;
  // Generate helper script
  bqCommands += `cat << 'EOF' > load_table.sh\n`;
  bqCommands += `#!/bin/bash\n`;
  bqCommands += `TABLE=\$1\n`;
  bqCommands += `CSV=\$2\n`;
  bqCommands += `SCHEMA=\$3\n`;
  bqCommands += `DATASET=\$4\n`;
  bqCommands += `echo "📥 Loading \$TABLE..."\n`;
  bqCommands += `if bq load --source_format=CSV --skip_leading_rows=1 --allow_quoted_newlines --null_marker="" --quote='"' --encoding=UTF-8 --max_bad_records=5 --location=US "\$DATASET.\$TABLE" "\$CSV" "\$SCHEMA"; then\n`;
  bqCommands += `  echo "    ✅ Loaded table: \$TABLE"\n`;
  bqCommands += `else\n`;
  bqCommands += `  echo "    ⚠️  ERROR: Failed to load table: \$TABLE"\n`;
  bqCommands += `  exit 1\n`;
  bqCommands += `fi\n`;
  bqCommands += `EOF\n`;
  bqCommands += `chmod +x load_table.sh\n\n`;

  // Write CSV files first
  for (const table of tables) {
    bqCommands += `cat <<'__CSV_EOF__' > ${table.tableName}.csv\n${table.csvData}\n__CSV_EOF__\n`;
  }

  bqCommands += `bq_fail=0\n`;
  bqCommands += `echo "📊 Loading tables in parallel..."\n`;
  bqCommands += `cat << 'EOF' | xargs -P 5 -n 4 ./load_table.sh\n`;
  for (const table of tables) {
    const schemaStr = table.schema.map(f => `${f.name}:${f.type}`).join(',');
    bqCommands += `${table.tableName} ${table.tableName}.csv ${schemaStr} ${datasetId}\n`;
  }
  bqCommands += `EOF\n`;
  bqCommands += `if [ \$? -ne 0 ]; then\n`;
  bqCommands += `  bq_fail=1\n`;
  bqCommands += `fi\n\n`;

  // Clean up helper script and CSV files
  bqCommands += `rm -f load_table.sh\n`;
  for (const table of tables) {
    bqCommands += `rm -f ${table.tableName}.csv\n`;
  }

  bqCommands += `if [ \$bq_fail -ne 0 ]; then\n`;
  bqCommands += `  echo "⚠️ Some BigQuery table loads failed. Please check above logs."\n`;
  bqCommands += `fi\n\n`;

  // --- Knowledge Catalog metadata injection ---
  // Write table/column descriptions into BigQuery so Knowledge Catalog (Dataplex)
  // auto-harvests rich, deterministic metadata that the agent can discover via the
  // Knowledge Catalog MCP server (search_entries / lookup_entry / lookup_context).
  // Descriptions are base64-encoded here (UTF-8) and decoded at runtime, so arbitrary
  // free text in any language never needs shell/JSON escaping.
  bqCommands += `echo "🏷  Applying Knowledge Catalog metadata (table & column descriptions)..."\n`;
  for (const table of tables) {
    const bqSchema = table.schema.map(f => ({
      name: f.name,
      type: f.type,
      description: (f.description || '').toString()
    }));
    const schemaB64 = Utilities.base64Encode(JSON.stringify(bqSchema), Utilities.Charset.UTF_8);
    bqCommands += `echo '${schemaB64}' | base64 -d > ${table.tableName}_schema.json\n`;
    bqCommands += `bq update ${datasetId}.${table.tableName} ${table.tableName}_schema.json >/dev/null 2>&1 && echo "    ✅ Column metadata: ${table.tableName}" || echo "    ⚠️  Column metadata skipped: ${table.tableName}"\n`;
    if (table.description) {
      const descB64 = Utilities.base64Encode(table.description.toString(), Utilities.Charset.UTF_8);
      bqCommands += `bq update --description "\$(echo '${descB64}' | base64 -d)" ${datasetId}.${table.tableName} >/dev/null 2>&1 || true\n`;
    }
    bqCommands += `rm -f ${table.tableName}_schema.json\n`;
  }
  bqCommands += `\n`;

  let firestoreCommands = '';
  if (firestore && firestore.collectionName && firestore.documents) {
    const fsDocsStr = JSON.stringify(firestore.documents).replace(/'/g, "\\'");

    firestoreCommands += `echo "🔥 Setting up Firestore database and collection: ${fsCollection}..."\n`;
    firestoreCommands += `gcloud firestore databases create --location=us-central1 2>/dev/null || echo "    ✅ Firestore Database already exists or initialized."\n\n`;
    
    firestoreCommands += `echo "    📥 Populating initial operational data via Python script..."\n`;
    firestoreCommands += `cat <<'__PY_EOF__' > setup_fs.py
import json
import os
from google.cloud import firestore

def init_data():
    db = firestore.Client()
    collection_name = "${fsCollection}"
    docs = json.loads('${fsDocsStr}')
    
    for doc in docs:
        doc_id = doc.get('id')
        data = doc.get('data', {})
        if doc_id:
            db.collection(collection_name).document(doc_id).set(data)
            print(f"      ✅ Inserted doc: {doc_id}")

if __name__ == '__main__':
    init_data()
__PY_EOF__\n`;

    firestoreCommands += `uv run --with google-cloud-firestore python setup_fs.py\n`;
    firestoreCommands += `rm setup_fs.py\n\n`;

    firestoreCommands += `echo "🌐 Deploying Real-time Data Viewer Web App (Cloud Run Functions)..."\n`;
    firestoreCommands += `mkdir -p ${dirName}/viewer_app\n`;
    // Generate system description dynamically based on the user's business goal.
    const systemDescPrompt = `You are an expert demo scenario writer.
Based on the provided business problem, generate a summary description (concise, 2-3 sentences) for an internal enterprise application that simulates a customer's operational console.

Business Problem: "${userGoal}"

Requirements:
1. Define what kind of system this is (e.g., "Enterprise Logistics Control Console").
2. Explain the business purpose of this system.
3. The output MUST be in the SAME LANGUAGE as the business problem provided above (e.g., Japanese if the problem is in Japanese).
4. Return ONLY the description text. Do not include greetings, explanations, or code blocks.`;

    let systemDescription = "";
    try {
      systemDescription = callVertexAI(systemDescPrompt).trim();
    } catch (e) {
      systemDescription = userGoal; // Fallback
    }

    const dashboardTitle = firestore.dashboardTitle || "Enterprise Operations Console";
    const kpi1Label = "Total Records";
    const kpi2Label = "Requires Action";
    const kpi3Label = "Resolved Actions";
    
    const btnAddText = "➕ Add Test Record";
    const btnUpdateText = "Update Status";
    const btnDeleteText = "Delete";
    
    const lblPolling = "Polling operational queue...";
    const lblTrail = "📜 Audit & Activity Trail";
    const lblChart = "📊 Status Distribution Summary";

    firestoreCommands += `cp "$GE_TPL/viewer_app/main.py" ${dirName}/viewer_app/main.py\n`;
    firestoreCommands += `mkdir -p ${dirName}/viewer_app/templates\n`;
    firestoreCommands += `cp "$GE_TPL"/viewer_app/templates/*.html ${dirName}/viewer_app/templates/\n`;
    // Per-demo values are substituted into the copied template files:
    // __GE_FS_COLLECTION__ lives in main.py; __GE_DASH_TITLE__ and
    // __GE_DASH_DESC__ live in templates/viewer.html.
    firestoreCommands += `GE_FS_COLLECTION='${fsCollection}' GE_DASH_TITLE='${bashEscape(dashboardTitle)}' GE_DASH_DESC='${bashEscape(userGoal)}' python3 - <<'__GE_VIEWER_SUB_EOF__'\n`;
    firestoreCommands += `import os\n`;
    firestoreCommands += `p = "${dirName}/viewer_app/main.py"\n`;
    firestoreCommands += `s = open(p, encoding="utf-8").read()\n`;
    firestoreCommands += `s = s.replace("__GE_FS_COLLECTION__", os.environ.get("GE_FS_COLLECTION", ""))\n`;
    firestoreCommands += `open(p, "w", encoding="utf-8").write(s)\n`;
    firestoreCommands += `h = "${dirName}/viewer_app/templates/viewer.html"\n`;
    firestoreCommands += `s = open(h, encoding="utf-8").read()\n`;
    firestoreCommands += `s = s.replace("__GE_DASH_TITLE__", os.environ.get("GE_DASH_TITLE", "Enterprise Operations Console"))\n`;
    firestoreCommands += `s = s.replace("__GE_DASH_DESC__", os.environ.get("GE_DASH_DESC", ""))\n`;
    firestoreCommands += `open(h, "w", encoding="utf-8").write(s)\n`;
    firestoreCommands += `__GE_VIEWER_SUB_EOF__\n`;

    firestoreCommands += `cp "$GE_TPL/viewer_app/requirements.txt" ${dirName}/viewer_app/requirements.txt\n`;

    firestoreCommands += `echo "🌐 Checking/Deploying Real-time Data Viewer Web App..."\n`;
    firestoreCommands += `if gcloud functions describe ${dirName}-viewer --gen2 --region=us-central1 --project="$PROJECT_ID" >/dev/null 2>&1; then\n`;
    firestoreCommands += `  echo "    ✅ Cloud Run Function already exists."\n`;
    firestoreCommands += `else\n`;
    firestoreCommands += `  VIEWER_LOG=\$(mktemp /tmp/viewer-deploy-XXXXXX.log)\n`;
    // v11.12: --no-allow-unauthenticated + IAP (see the IAP block below). Never
    // grants allUsers, so the deploy works under Domain Restricted Sharing org
    // policies and demo data is never exposed on a public URL.
    firestoreCommands += `  gcloud functions deploy ${dirName}-viewer --gen2 --runtime=python311 --region=us-central1 --source=${dirName}/viewer_app --entry-point=main --trigger-http --no-allow-unauthenticated --set-env-vars=DEMO_ID=${dirName} --project="$PROJECT_ID" > "\$VIEWER_LOG" 2>&1 &\n`;
    firestoreCommands += `  VIEWER_PID=\$!\n`;
    firestoreCommands += `  printf "    ⏳ Deploying Data Viewer"\n`;
    firestoreCommands += `  while kill -0 \$VIEWER_PID 2>/dev/null; do\n`;
    firestoreCommands += `    printf "."\n`;
    firestoreCommands += `    sleep 5\n`;
    firestoreCommands += `  done\n`;
    firestoreCommands += `  echo ""\n`;
    firestoreCommands += `  wait \$VIEWER_PID || true\n`;
    // NOTE: don't trust the exit code here — the deploy runs in the background and
    // `wait ... || true` always yields 0. Verify the function actually exists instead
    // (same source of truth as the final summary), so we never print a false success.
    firestoreCommands += `  if gcloud functions describe ${dirName}-viewer --gen2 --region=us-central1 --project="$PROJECT_ID" >/dev/null 2>&1; then\n`;
    firestoreCommands += `    echo "    ✅ Cloud Run Function deployed."\n`;
    firestoreCommands += `  else\n`;
    firestoreCommands += `    echo "    ⚠️ WARNING: Failed to deploy Firestore Data Viewer. Build log:"\n`;
    firestoreCommands += `    cat "\$VIEWER_LOG"\n`;
    // v11.14: orgs commonly restrict constraints/run.allowedIngress to
    // internal(-and-gclb), which rejects the CreateService call before IAP is
    // even relevant. NON-INTERACTIVE by design: most operators cannot change
    // org policies, and a mid-script prompt would stall unattended runs. We
    // only explain the cause and print the manual remedy for operators who
    // DO hold org-policy admin, then continue without the viewer.
    firestoreCommands += `    if grep -q "run.allowedIngress" "\$VIEWER_LOG"; then\n`;
    firestoreCommands += `      echo ""\n`;
    firestoreCommands += `      echo "    🚧 Cause: org policy 'constraints/run.allowedIngress' does not allow public ingress, which the browser-based Data Viewer needs."\n`;
    firestoreCommands += `      echo "       The Data Viewer is skipped in this environment. If you hold Organization Policy Administrator on this project"\n`;
    firestoreCommands += `      echo "       you can allow it and re-run this script:"\n`;
    firestoreCommands += `      echo "         gcloud resource-manager org-policies allow constraints/run.allowedIngress all --project=$PROJECT_ID"\n`;
    firestoreCommands += `      echo "       (Viewer access itself stays IAP-protected - it is never public even with ingress allowed.)"\n`;
    firestoreCommands += `    fi\n`;
    firestoreCommands += `    echo "    ℹ️  This is an optional component and does NOT affect the agent's functionality."\n`;
    firestoreCommands += `    echo "    ℹ️  The agent will work normally without the Data Viewer."\n`;
    firestoreCommands += `  fi\n`;
    firestoreCommands += `  rm -f "\$VIEWER_LOG"\n`;
    firestoreCommands += `fi\n`;
    // Capture viewer deployment result (needed for DATA_VIEWER_URL in .env)
    firestoreCommands += `if gcloud functions describe ${dirName}-viewer --gen2 --region=us-central1 --project="$PROJECT_ID" >/dev/null 2>&1; then\n`;
    firestoreCommands += `  VIEWER_DEPLOYED=true\n`;
    firestoreCommands += `  VIEWER_URL=$(gcloud functions describe ${dirName}-viewer --gen2 --region=us-central1 --format="value(serviceConfig.uri)" --project="$PROJECT_ID")\n`;
    firestoreCommands += `else\n`;
    firestoreCommands += `  VIEWER_DEPLOYED=false\n`;
    firestoreCommands += `fi\n`;
    // Always-on IAP (v11.12): the viewer is deployed WITHOUT public access, so
    // enable Cloud Run IAP and grant the deploying user. Runs for both fresh and
    // pre-existing deployments (idempotent). Fail-soft: if IAP cannot be enabled
    // the viewer stays unreachable, so we drop it (agent works without it).
    firestoreCommands += `if [ "$VIEWER_DEPLOYED" = "true" ]; then\n`;
    firestoreCommands += `  echo "    🔐 Enabling IAP on the Data Viewer (no public access)..."\n`;
    firestoreCommands += `  PROJECT_NUMBER=$(gcloud projects describe "$PROJECT_ID" --format="value(projectNumber)")\n`;
    firestoreCommands += `  gcloud beta services identity create --service=iap.googleapis.com --project="$PROJECT_ID" >/dev/null 2>&1 || true\n`;
    firestoreCommands += `  IAP_SA="service-$PROJECT_NUMBER@gcp-sa-iap.iam.gserviceaccount.com"\n`;
    firestoreCommands += `  gcloud run services add-iam-policy-binding ${dirName}-viewer --region=us-central1 --member="serviceAccount:$IAP_SA" --role="roles/run.invoker" --project="$PROJECT_ID" >/dev/null 2>&1 || true\n`;
    firestoreCommands += `  VIEWER_IAP_OK=false\n`;
    firestoreCommands += `  _IAP_ERR=""\n`;
    firestoreCommands += `  for _IAP_TRY in 1 2 3; do\n`;
    firestoreCommands += `    if _IAP_ERR=$(gcloud beta run services update ${dirName}-viewer --region=us-central1 --iap --project="$PROJECT_ID" 2>&1); then\n`;
    firestoreCommands += `      VIEWER_IAP_OK=true\n`;
    firestoreCommands += `      break\n`;
    firestoreCommands += `    fi\n`;
    firestoreCommands += `    sleep 10\n`;
    firestoreCommands += `  done\n`;
    firestoreCommands += `  DEPLOYER_EMAIL=$(gcloud config get-value account 2>/dev/null)\n`;
    firestoreCommands += `  if [ "$VIEWER_IAP_OK" = "true" ]; then\n`;
    firestoreCommands += `    if [ -n "$DEPLOYER_EMAIL" ]; then\n`;
    firestoreCommands += `      gcloud beta iap web add-iam-policy-binding --project="$PROJECT_ID" --resource-type=cloud-run --region=us-central1 --service=${dirName}-viewer --member="user:$DEPLOYER_EMAIL" --role="roles/iap.httpsResourceAccessor" >/dev/null 2>&1 || true\n`;
    firestoreCommands += `    fi\n`;
    firestoreCommands += `    echo "    ✅ IAP enabled. Viewer access granted to: $DEPLOYER_EMAIL"\n`;
    firestoreCommands += `    echo "    ℹ️  Open the viewer once in your browser before the demo to complete sign-in."\n`;
    firestoreCommands += `    echo "    ℹ️  Grant more viewers with:"\n`;
    firestoreCommands += `    echo "        gcloud beta iap web add-iam-policy-binding --project=$PROJECT_ID --resource-type=cloud-run --region=us-central1 --service=${dirName}-viewer --member=user:EMAIL --role=roles/iap.httpsResourceAccessor"\n`;
    firestoreCommands += `  else\n`;
    firestoreCommands += `    echo "    ⚠️ WARNING: Could not enable IAP on the Data Viewer; it would be unreachable, so it is disabled."\n`;
    firestoreCommands += `    echo "    ℹ️  Last gcloud error was:"\n`;
    firestoreCommands += `    echo "\$_IAP_ERR" | tail -n 3 | sed 's/^/       /'\n`;
    firestoreCommands += `    echo "    ℹ️  The agent works normally without the Data Viewer."\n`;
    firestoreCommands += `    VIEWER_DEPLOYED=false\n`;
    firestoreCommands += `  fi\n`;
    firestoreCommands += `fi\n\n`;
  }

  // Robustly escape instruction for an unquoted bash heredoc
  const rawInstruction = systemInstruction.replace(/[\\$`]/g, match => '\\' + match);

  // Per-demo MCP server config consumed by the static agent_template runtime
  // (tools.get_custom_mcp_toolsets / get_slack_mcp_toolset and the numbered
  // instruction sections in agent.py read this file at startup).
  const geLocalMcps = (params.importedMcpList || []).filter(m => m.type !== 'remote');
  const geMcpConfigJson = JSON.stringify({ mcpServers: (params.importedMcpList || []).map((mcp, geIdx) => {
    if (mcp.type === 'remote') {
      return { idx: geIdx, type: 'remote', name: mcp.name || '', auth_type: mcp.auth_type || '' };
    }
    const geLocalIdx = geLocals_indexOf(geLocalMcps, mcp);
    return {
      idx: geIdx, type: 'local', name: mcp.name || '',
      safe_name: (mcp.name || ('mcp' + geLocalIdx)).toLowerCase().replace(/[^a-z0-9]+/g, '_').replace(/^_|_$/g, ''),
      entrypoint: mcp.entrypoint || '',
      required_keys: (mcp.required_env_vars || []).filter(v => v.is_required).map(v => v.key).join(','),
      port: 9090 + geLocalIdx,
      local_idx: geLocalIdx,
      repo_name: (mcp.github_url || '').split('/').pop().replace(/\.git$/, '')
    };
  }) }, null, 2);
  function geLocals_indexOf(arr, item) { return arr.indexOf(item); }

  let mcpBanner = "";
  let mcpReads = "";
  let mcpCredentialSetup = "";
  if (params.importedMcpList && params.importedMcpList.length > 0) {
    params.importedMcpList.forEach((mcp, mcpIdx) => {
      // ── Remote Managed MCP (e.g. Slack): OAuth flow instead of env var prompts ──
      if (mcp.type === 'remote') {
        mcpBanner += `echo "🌐 Managed MCP: ${mcp.name || 'Remote'} (${mcp.endpoint_url})"\n`;
        if (mcp.auth_type === 'oauth2_slack') {
          mcpReads += `
echo ""
echo "════════════════════════════════════════════════════════════"
echo "  🔐 Slack MCP Server — Automated OAuth Setup"
echo "════════════════════════════════════════════════════════════"
echo ""
echo "  This will automatically create a Slack App and complete"
echo "  the OAuth authorization flow to obtain a User Token."
echo ""

SLACK_TOKEN_SECRET="${dirName}-slack-token"
SKIP_SLACK_OAUTH=false

# Defensive: this block reads/writes Secret Manager (existing-token check below
# and the token save at the end), so ensure the API is enabled even if this
# block ever runs before the main API-enable batch. Idempotent; no-op if already on.
gcloud services enable secretmanager.googleapis.com --project="$PROJECT_ID" 2>/dev/null || true

# Check if token already stored in Secret Manager
EXISTING_SLACK_TOKEN=""
if gcloud secrets describe $SLACK_TOKEN_SECRET --project="$PROJECT_ID" >/dev/null 2>&1; then
  EXISTING_SLACK_TOKEN=$(gcloud secrets versions access latest --secret="$SLACK_TOKEN_SECRET" --project="$PROJECT_ID" 2>/dev/null || echo "")
fi
if [ -n "$EXISTING_SLACK_TOKEN" ]; then
  echo "  ✅ Found existing Slack token in Secret Manager."
  read -p "  ▶ Use existing token? (Y/n): " USE_EXISTING
  if [[ ! "$USE_EXISTING" =~ ^[Nn]$ ]]; then
    SKIP_SLACK_OAUTH=true
    echo "  ✅ Using existing token."
  fi
fi

if [ "$SKIP_SLACK_OAUTH" = "false" ]; then

  SLACK_USER_SCOPES="search:read,channels:read,channels:history,groups:read,groups:history,im:read,im:history,mpim:read,mpim:history,chat:write,reactions:read,users:read,users:read.email,team:read,files:read,canvases:read,canvases:write"
  SLACK_REDIRECT_URL="https://localhost"

  # ── Step 1: Create Slack App via Manifest URL ──
  SLACK_MANIFEST='{"display_information":{"name":"${(`GE-${dirName}`).substring(0, 35)}"},"features":{},"oauth_config":{"redirect_urls":["'"$SLACK_REDIRECT_URL"'"],"scopes":{"user":["search:read","channels:read","channels:history","groups:read","groups:history","im:read","im:history","mpim:read","mpim:history","chat:write","reactions:read","users:read","users:read.email","team:read","files:read","canvases:read","canvases:write"]}},"settings":{"org_deploy_enabled":false,"socket_mode_enabled":false,"token_rotation_enabled":false}}'
  ENCODED_MANIFEST=$(python3 -c "import urllib.parse; print(urllib.parse.quote('''$SLACK_MANIFEST'''))")
  CREATE_URL="https://api.slack.com/apps?new_app=1&manifest_json=$ENCODED_MANIFEST"

  echo "  📦 Step 1: Create Slack App"
  echo ""
  echo "  Open the following URL to create a pre-configured Slack App:"
  echo ""
  echo "  $CREATE_URL"
  echo ""

  # Try to open browser automatically
  xdg-open "$CREATE_URL" 2>/dev/null || open "$CREATE_URL" 2>/dev/null || true

  echo "  After creating the app:"
  echo "    1. Select your workspace and click 'Next' → 'Create'"
  echo "    2. On the 'Basic Information' page, scroll to 'App Credentials'"
  echo "    3. Copy the Client ID and Client Secret below"
  echo ""

  while true; do
    read -p "▶ Paste Client ID: " SLACK_CLIENT_ID
    if [ -n "$SLACK_CLIENT_ID" ]; then break; fi
    echo "  ⚠️  Client ID is required."
  done
  while true; do
    read -s -p "▶ Paste Client Secret: " SLACK_CLIENT_SECRET
    echo ""
    if [ -n "$SLACK_CLIENT_SECRET" ]; then break; fi
    echo "  ⚠️  Client Secret is required."
  done
  echo "  ✅ Slack App credentials received!"

  # ── Step 2: Enable MCP (cannot be set via manifest) ──
  echo ""
  echo "  📦 Step 2: Enable Model Context Protocol (MCP)"
  echo ""
  echo "  ⚠️  This step is REQUIRED — MCP cannot be set automatically."
  echo ""
  echo "  In the Slack App settings page (should already be open):"
  echo "    1. Click 'Agents & AI Apps' in the left sidebar under Features"
  echo "    2. Toggle ON 'Model Context Protocol'"
  echo "    3. Click 'Save Changes' if prompted"
  echo ""
  read -p "▶ Press Enter once MCP is enabled... "
  echo "  ✅ MCP enabled!"

  # ── Step 3: OAuth Authorization Flow ──
  AUTH_URL="https://slack.com/oauth/v2/authorize?client_id=$SLACK_CLIENT_ID&user_scope=$SLACK_USER_SCOPES&redirect_uri=$SLACK_REDIRECT_URL"

  echo ""
  echo "  📦 Step 3: Authorize the Slack App"
  echo ""
  echo "  1. Open this URL in your browser:"
  echo ""
  echo "     $AUTH_URL"
  echo ""
  echo "  2. Click 'Allow' to authorize the app."
  echo ""
  echo "  3. Your browser will redirect to a page that says"
  echo "     'This site can't be reached' — this is expected!"
  echo ""
  echo "  4. Copy the FULL URL from the browser's address bar."
  echo "     It looks like: https://localhost/?code=XXXX..."
  echo ""

  while true; do
    read -p "▶ Paste the URL from your browser's address bar: " PASTE_INPUT
    SLACK_AUTH_CODE=$(echo "$PASTE_INPUT" | sed -n 's/.*code=\\([^&]*\\).*/\\1/p')
    if [ -n "$SLACK_AUTH_CODE" ]; then
      echo "  ✅ Authorization code extracted!"
      break
    fi
    echo "  ⚠️  Could not find 'code=' in the URL. Please paste the full URL."
  done

  # ── Step 3: Exchange code for tokens ──
  echo "🔑 Exchanging authorization code for tokens..."
  TOKEN_RESPONSE=$(curl -s -X POST https://slack.com/api/oauth.v2.access \
    -d "client_id=$SLACK_CLIENT_ID" \
    -d "client_secret=$SLACK_CLIENT_SECRET" \
    -d "code=$SLACK_AUTH_CODE" \
    -d "redirect_uri=$SLACK_REDIRECT_URL")

  TOKEN_OK=$(echo "$TOKEN_RESPONSE" | jq -r '.ok')
  if [ "$TOKEN_OK" = "true" ]; then
    SLACK_ACCESS_TOKEN=$(echo "$TOKEN_RESPONSE" | jq -r '.authed_user.access_token // empty')
    if [ -z "$SLACK_ACCESS_TOKEN" ]; then
      SLACK_ACCESS_TOKEN=$(echo "$TOKEN_RESPONSE" | jq -r '.access_token // empty')
      echo "  ⚠️  User token not available, using bot token."
    fi
    echo "  ✅ Token obtained!"
  else
    echo "  ❌ Token exchange failed."
    exit 1
  fi

  # ── Step 4: Store in Secret Manager ──
  echo "💾 Saving Slack token to Secret Manager..."
  if gcloud secrets describe $SLACK_TOKEN_SECRET --project="$PROJECT_ID" >/dev/null 2>&1; then
    echo -n "$SLACK_ACCESS_TOKEN" | gcloud secrets versions add $SLACK_TOKEN_SECRET --data-file=- --project="$PROJECT_ID"
  else
    echo -n "$SLACK_ACCESS_TOKEN" | gcloud secrets create $SLACK_TOKEN_SECRET --data-file=- --replication-policy="automatic" --project="$PROJECT_ID"
  fi
fi

echo "  ✅ Slack MCP OAuth configured!"
`;
        } else {
          // Generic remote MCP: prompt for env vars normally
          mcp.required_env_vars.forEach(v => {
            if (v.is_required) {
              if (v.is_secret) {
                mcpReads += `while true; do\n  read -s -p "▶ Enter ${v.key} (${v.description}): " ${v.key}\n  echo ""\n  if [ -n "$${v.key}" ]; then break; fi\n  echo "  ⚠️  ${v.key} is required. Please enter a value."\ndone\n`;
              } else {
                mcpReads += `while true; do\n  read -p "▶ Enter ${v.key} (${v.description}): " ${v.key}\n  if [ -n "$${v.key}" ]; then break; fi\n  echo "  ⚠️  ${v.key} is required. Please enter a value."\ndone\n`;
              }
            }
          });
        }
        return; // skip sidecar-specific credential_file handling
      }

      // ── Sidecar MCP: existing env var + credential file flow ──
      const repoName = mcp.github_url.split('/').pop().replace(/\.git$/, "");
      mcpBanner += `echo "🔌 Imported MCP #${mcpIdx + 1}:  ${repoName}"\n`;
      mcp.required_env_vars.forEach(v => {
        if (v.is_required) {
          // Required: loop until non-empty value is provided
          if (v.is_secret) {
            mcpReads += `while true; do\n  read -s -p "▶ Enter ${v.key} (${v.description}): " ${v.key}\n  echo ""\n  if [ -n "$${v.key}" ]; then break; fi\n  echo "  ⚠️  ${v.key} is required. Please enter a value."\ndone\n`;
          } else {
            mcpReads += `while true; do\n  read -p "▶ Enter ${v.key} (${v.description}): " ${v.key}\n  if [ -n "$${v.key}" ]; then break; fi\n  echo "  ⚠️  ${v.key} is required. Please enter a value."\ndone\n`;
          }
        } else {
          // Optional: single prompt, blank is fine
          const reqLabel = ' [OPTIONAL - press Enter to skip]';
          if (v.is_secret) {
             mcpReads += `read -s -p "▶ Enter ${v.key} (${v.description})${reqLabel}: " ${v.key}\necho ""\n`;
          } else {
               mcpReads += `read -p "▶ Enter ${v.key} (${v.description})${reqLabel}: " ${v.key}\n`;
          }
        }
      });

      // Credential file wizard
      if (mcp.credential_file) {
        const cf = mcp.credential_file;
        const escapedDesc = cf.file_description.replace(/"/g, '\\"');
        const credSecretSuffix = params.importedMcpList.length > 1 ? `-${mcpIdx}` : '';
        mcpCredentialSetup += `
echo ""
echo "════════════════════════════════════════════════════════════"
echo "  📄 Credential File Required (MCP #${mcpIdx + 1}: ${repoName})"
echo "════════════════════════════════════════════════════════════"
echo ""
echo "  ${escapedDesc}"
echo ""
echo "  After completing the steps above, copy the generated"
echo "  JSON file contents to your clipboard."
echo ""
read -p "  Press [Enter] when ready to paste the JSON content... " _WAIT_
echo ""
echo "  Paste the JSON below, then press Ctrl+D on a new line:"
echo "  ────────────────────────────────────────────────────────"
MCP_CRED_CONTENT_${mcpIdx}=$(cat)
echo ""
echo "  ────────────────────────────────────────────────────────"
echo "  ✅ Credential content captured."
echo ""

# Store credential in Secret Manager
MCP_CRED_SECRET_NAME="${dirName}-mcp-adc-json${credSecretSuffix}"
echo "  Storing credential in Secret Manager as $MCP_CRED_SECRET_NAME..."
if gcloud secrets describe $MCP_CRED_SECRET_NAME >/dev/null 2>&1; then
  echo -n "$MCP_CRED_CONTENT_${mcpIdx}" | gcloud secrets versions add $MCP_CRED_SECRET_NAME --data-file=-
else
  echo -n "$MCP_CRED_CONTENT_${mcpIdx}" | gcloud secrets create $MCP_CRED_SECRET_NAME --data-file=- --replication-policy="automatic"
fi
echo "  ✅ Credential stored in Secret Manager."
echo ""
`;
      }
    });
  }

  let apisToEnable = [
    "aiplatform.googleapis.com",
    "bigquery.googleapis.com",
    "apikeys.googleapis.com",
    "mapstools.googleapis.com",
    "discoveryengine.googleapis.com",
    "cloudresourcemanager.googleapis.com",
    "serviceusage.googleapis.com",
    "iam.googleapis.com",
    "cloudbilling.googleapis.com",
    "logging.googleapis.com",
    "monitoring.googleapis.com",
    "clouderrorreporting.googleapis.com",
    "telemetry.googleapis.com",
    "firestore.googleapis.com",
    "cloudfunctions.googleapis.com",
    "dataplex.googleapis.com"
  ];
  if (workspaceAuthEnabled) {
    // Needed for full Workspace MCP AND for the auth-only mode: the gws CLI /
    // Drive REST calls run with the user's OAuth token but bill their quota
    // to this project, so the plain Workspace APIs must be enabled here too.
    apisToEnable.push(
      "gmail.googleapis.com",
      "drive.googleapis.com",
      "calendar-json.googleapis.com",
      "chat.googleapis.com",
      "people.googleapis.com"
    );
  }
  // Secret Manager: always required. The Maps API key is stored as a secret for
  // every demo (plus any MCP/Slack/OAuth secrets). Must be enabled in this early
  // batch because the Maps key secret is created well before the deploy block.
  apisToEnable.push("secretmanager.googleapis.com");
  let apisChunks = [];
  for (let i = 0; i < apisToEnable.length; i += 20) {
    apisChunks.push(apisToEnable.slice(i, i + 20));
  }
  
  let enableCommands = "";
  apisChunks.forEach(chunk => {
    enableCommands += `echo "📡 Enabling APIs (batch)..."\n`;
    enableCommands += `gcloud services enable \\\n  ${chunk.join(" \\\n  ")} \\\n  --project="$PROJECT_ID"\n`;
  });

  let mcpServicesToEnable = "";
  if (enableWorkspaceMcp) {
    mcpServicesToEnable = `
gcloud services enable gmailmcp.googleapis.com --project="$PROJECT_ID"
gcloud services enable drivemcp.googleapis.com --project="$PROJECT_ID"
gcloud services enable calendarmcp.googleapis.com --project="$PROJECT_ID"
gcloud services enable chatmcp.googleapis.com --project="$PROJECT_ID"
gcloud services enable people.googleapis.com --project="$PROJECT_ID"
`;
  }

  let wsmcpInstructions = "";
  if (workspaceAuthEnabled) {
    wsmcpInstructions = `
echo ""
echo "========================================================="
echo "🛠️  ${enableWorkspaceMcp ? 'GOOGLE WORKSPACE MCP SETUP REQUIRED' : 'GOOGLE WORKSPACE AUTHORIZATION SETUP (no MCP servers)'}"
echo "========================================================="




TOKEN=\$(gcloud auth print-access-token)

CLIENT_ID_SECRET="ge-demo-oauth-client-id"
CLIENT_SECRET_SECRET="ge-demo-oauth-client-secret"

OAUTH_CLIENT_ID=""
OAUTH_CLIENT_SECRET=""

echo "🔍 Checking Secret Manager for stored OAuth credentials..."

if gcloud secrets describe \$CLIENT_ID_SECRET --project="\$PROJECT_ID" >/dev/null 2>&1; then
  OAUTH_CLIENT_ID=\$(gcloud secrets versions access latest --secret="\$CLIENT_ID_SECRET" --project="\$PROJECT_ID" 2>/dev/null || echo "")
fi

if gcloud secrets describe \$CLIENT_SECRET_SECRET --project="\$PROJECT_ID" >/dev/null 2>&1; then
  OAUTH_CLIENT_SECRET=\$(gcloud secrets versions access latest --secret="\$CLIENT_SECRET_SECRET" --project="\$PROJECT_ID" 2>/dev/null || echo "")
fi

if [ -z "\$OAUTH_CLIENT_ID" ] || [ -z "\$OAUTH_CLIENT_SECRET" ]; then
  echo "Stored credentials not found or incomplete."


echo "The following steps require manual interaction in the Google Cloud Console."
  echo "Please complete them before continuing."
  echo ""
  echo "1. Set up the OAuth consent screen (Branding):"
  echo "   URL: https://console.cloud.google.com/auth/branding?project=\$PROJECT_ID"
  echo "   - App name: 'GE Demo Agent' (any name works - end users see it on the consent screen)"
  echo "   - Support email: your own email address"
  echo "   - Audience: choose 'Internal' (recommended - only users in your org, no verification needed)."
  echo "     If 'Internal' is not available (no Workspace org), choose 'External' and then add your"
  echo "     demo user account(s) under 'Audience' -> 'Test users'."
  echo "   - Save."
  echo ""
  echo "2. Add the OAuth scopes (Data Access):"
  echo "   URL: https://console.cloud.google.com/auth/scopes?project=\$PROJECT_ID"
  echo "   - Click 'Add or remove scopes'. In the panel that opens, scroll down to the"
  echo "     'Manually add scopes' text box, PASTE ALL the scope lines below at once,"
  echo "     then click 'Add to table' -> 'Update' -> 'Save'."
  echo "   Scopes to paste:"
  echo "https://www.googleapis.com/auth/gmail.readonly"
  echo "https://www.googleapis.com/auth/gmail.compose"
  echo "https://www.googleapis.com/auth/gmail.modify"
  echo "https://www.googleapis.com/auth/drive.readonly"
  echo "https://www.googleapis.com/auth/drive.file"
  echo "https://www.googleapis.com/auth/calendar.calendarlist.readonly"
  echo "https://www.googleapis.com/auth/calendar.events.freebusy"
  echo "https://www.googleapis.com/auth/calendar.events.readonly"
  echo "https://www.googleapis.com/auth/calendar.events"
  echo "https://www.googleapis.com/auth/chat.spaces.readonly"
  echo "https://www.googleapis.com/auth/chat.memberships.readonly"
  echo "https://www.googleapis.com/auth/chat.messages.readonly"
  echo "https://www.googleapis.com/auth/chat.messages.create"
  echo "https://www.googleapis.com/auth/chat.users.readstate.readonly"
  echo "https://www.googleapis.com/auth/directory.readonly"
  echo "https://www.googleapis.com/auth/userinfo.profile"
  echo "https://www.googleapis.com/auth/contacts.readonly"
  echo ""
  echo "3. Create an OAuth 2.0 Client ID (Web application):"
  echo "   URL: https://console.cloud.google.com/auth/clients/create?project=\$PROJECT_ID"
  echo "   - Application type: 'Web application'"
  echo "   - Name: 'GE Demo Generator' (any name works - it is only shown in the console)"
  echo "   - Add the following Authorized Redirect URIs:"
  echo "     - https://vertexaisearch.cloud.google.com/oauth-redirect"
  echo "     - https://vertexaisearch.cloud.google.com/static/oauth/oauth.html"
  echo "   - Click 'Create', then copy the Client ID and Client Secret."
  echo ""
${ enableWorkspaceMcp ? `  echo "4. Configure the Chat app (required for Chat MCP):"
  echo "   Reference: https://developers.google.com/workspace/guides/configure-mcp-servers#configure-chat-app"
  echo "   URL: https://console.cloud.google.com/apis/api/chat.googleapis.com/hangouts-chat?project=\$PROJECT_ID"
  echo "   In 'Google Chat API' -> 'Manage' -> 'Configuration', set:"
  echo "     - App name: 'Chat MCP'"
  echo "     - Avatar URL: https://developers.google.com/chat/images/quickstart-app-avatar.png"
  echo "     - Description: 'Chat MCP server'"
  echo "     - Disable 'Enable interactive features'."
  echo "     - Under 'Visibility', make the app available to yourself (enter your email or your domain)."
  echo "     - Under 'Logs', select 'Log errors to Logging'."
  echo "     - Click 'Save'."
  echo ""
` : `  echo "4. Configure the Google Chat API app (one-time; required for the agent to post to Chat with your authorization):"
  echo "   URL: https://console.cloud.google.com/apis/api/chat.googleapis.com/hangouts-chat?project=\$PROJECT_ID"
  echo "   In 'Google Chat API' -> 'Manage' -> 'Configuration', set:"
  echo "     - App name: 'GE Demo Agent'"
  echo "     - Avatar URL: https://developers.google.com/chat/images/quickstart-app-avatar.png"
  echo "     - Description: 'GE Demo Agent Workspace actions'"
  echo "     - Disable 'Enable interactive features'."
  echo "     - Under 'Visibility', make the app available to yourself (enter your email or your domain)."
  echo "     - Under 'Logs', select 'Log errors to Logging'."
  echo "     - Click 'Save'."
  echo "   Without this one-time configuration, Chat API rejects message posting even with valid user authorization."
  echo ""
` }  read -p "Press [Enter] after you have completed these steps and copied your Client ID/Secret..."
  echo ""
  read -p "Enter your OAuth Client ID: " OAUTH_CLIENT_ID
  read -s -p "Enter your OAuth Client Secret: " OAUTH_CLIENT_SECRET
  echo ""
  
  echo "💾 Saving credentials to Secret Manager for future reuse..."
  gcloud secrets create \$CLIENT_ID_SECRET --project="\$PROJECT_ID" --replication-policy="automatic" 2>/dev/null || true
  gcloud secrets create \$CLIENT_SECRET_SECRET --project="\$PROJECT_ID" --replication-policy="automatic" 2>/dev/null || true
  
  echo -n "\$OAUTH_CLIENT_ID" | gcloud secrets versions add \$CLIENT_ID_SECRET --data-file=- --project="\$PROJECT_ID"
  echo -n "\$OAUTH_CLIENT_SECRET" | gcloud secrets versions add \$CLIENT_SECRET_SECRET --data-file=- --project="\$PROJECT_ID"
else
  echo "✅ Stored OAuth credentials found - skipping the console tutorial."
  echo "   Reminder: posting to Google Chat needs a ONE-TIME Google Chat API app configuration:"
  echo "   https://console.cloud.google.com/apis/api/chat.googleapis.com/hangouts-chat?project=\$PROJECT_ID"
  echo "   If Chat posts fail with a permission/configuration error, open 'Configuration' there and set it up (App name: '${enableWorkspaceMcp ? 'Chat MCP' : 'GE Demo Agent'}')."
fi

# Create authorization resource in Gemini Enterprise
AUTH_ID="${dirName}-auth"
echo "🔐 Creating authorization resource in Gemini Enterprise..."
curl -X POST \
  -H "Authorization: Bearer \$TOKEN" \
  -H "Content-Type: application/json" \
  -H "X-Goog-User-Project: \$PROJECT_ID" \
  "https://discoveryengine.googleapis.com/v1alpha/projects/\$PROJECT_ID/locations/global/authorizations?authorizationId=\$AUTH_ID" \
  -d '{ "name": "projects/'"\$PROJECT_ID"'/locations/global/authorizations/'"\$AUTH_ID"'", "serverSideOauth2": { "clientId": "'"\$OAUTH_CLIENT_ID"'", "clientSecret": "'"\$OAUTH_CLIENT_SECRET"'", "authorizationUri": "https://accounts.google.com/o/oauth2/v2/auth?access_type=offline&prompt=consent&response_type=code&scope=https%3A%2F%2Fwww.googleapis.com%2Fauth%2Fgmail.readonly%20https%3A%2F%2Fwww.googleapis.com%2Fauth%2Fgmail.compose%20https%3A%2F%2Fwww.googleapis.com%2Fauth%2Fgmail.modify%20https%3A%2F%2Fwww.googleapis.com%2Fauth%2Fdrive.readonly%20https%3A%2F%2Fwww.googleapis.com%2Fauth%2Fdrive.file%20https%3A%2F%2Fwww.googleapis.com%2Fauth%2Fcalendar.calendarlist.readonly%20https%3A%2F%2Fwww.googleapis.com%2Fauth%2Fcalendar.events.freebusy%20https%3A%2F%2Fwww.googleapis.com%2Fauth%2Fcalendar.events.readonly%20https%3A%2F%2Fwww.googleapis.com%2Fauth%2Fcalendar.events%20https%3A%2F%2Fwww.googleapis.com%2Fauth%2Fchat.spaces.readonly%20https%3A%2F%2Fwww.googleapis.com%2Fauth%2Fchat.memberships.readonly%20https%3A%2F%2Fwww.googleapis.com%2Fauth%2Fchat.messages.readonly%20https%3A%2F%2Fwww.googleapis.com%2Fauth%2Fchat.messages.create%20https%3A%2F%2Fwww.googleapis.com%2Fauth%2Fchat.users.readstate.readonly%20https%3A%2F%2Fwww.googleapis.com%2Fauth%2Fdirectory.readonly%20https%3A%2F%2Fwww.googleapis.com%2Fauth%2Fuserinfo.profile%20https%3A%2F%2Fwww.googleapis.com%2Fauth%2Fcontacts.readonly&client_id='"\$OAUTH_CLIENT_ID"'&redirect_uri=https%3A%2F%2Fvertexaisearch.cloud.google.com%2Foauth-redirect", "tokenUri": "https://oauth2.googleapis.com/token" } }'

`;
  }

  let fullScript = `#!/bin/bash
# ===========================================
# GE Demo Generator - Setup Script (${CONFIG.APP_VERSION})
# Generated: ${new Date().toISOString()}
# Demo: ${dirName}
# ===========================================

set -e
${templateRefBanner}
# --- Usage / Help ---
show_usage() {
  echo ""
  echo "Usage: bash $0 [OPTIONS]"
  echo ""
  echo "Options:"
  echo "  --model-analysis-agent, -m <MODEL>  Set the deep analysis agent model"
  echo "                                      (default: gemini-3.6-flash)"
  echo "  --model-root-agent <MODEL>          Set the root orchestration agent model"
  echo "                                      (default: gemini-3.6-flash)"
  echo "  --cleanup, -c                       Delete all provisioned demo resources"
  echo "  --yes, -y                           Skip confirmation prompts (non-interactive use)"
  echo "  --help, -h                          Show this help message and exit"
  echo ""
  echo "Examples:"
  echo "  bash $0                                  # Deploy with default models"
  echo "  bash $0 --model-analysis-agent gemini-3.1-pro-preview       # Use a different analysis model"
  echo "  bash $0 --model-root-agent gemini-3.5-flash-lite            # Use a different root model"
  echo "  bash $0 --cleanup                         # Remove all demo resources"
  echo "  bash $0 --cleanup --yes                   # Remove all demo resources without prompting"
  echo ""
}


# --- Argument Parsing ---
AGENT_MODEL="gemini-3.6-flash"
AGENT_MODEL_LITE="gemini-3.6-flash"
ROOT_MODEL_CLI_OVERRIDE=false
CLEANUP_MODE=false
AUTO_CONFIRM=false
while [[ $# -gt 0 ]]; do
  case "$1" in
    --help|-h)
      show_usage
      exit 0
      ;;
    --model-analysis-agent|-m)
      if [ -n "$2" ]; then
        AGENT_MODEL="$2"
        shift 2
      else
        echo "❌ Error: --model-analysis-agent requires a model name (e.g., --model-analysis-agent gemini-flash-latest)."
        exit 1
      fi
      ;;
    --model-root-agent)
      if [ -n "$2" ]; then
        AGENT_MODEL_LITE="$2"
        ROOT_MODEL_CLI_OVERRIDE=true
        shift 2
      else
        echo "❌ Error: --model-root-agent requires a model name (e.g., --model-root-agent gemini-flash-latest)."
        exit 1
      fi
      ;;
    --cleanup|-c)
      CLEANUP_MODE=true
      shift
      ;;
    --yes|-y)
      AUTO_CONFIRM=true
      shift
      ;;
    *)
      echo "⚠️  Unknown option: $1 (ignored)"
      shift
      ;;
  esac
done

# Disable gcloud prompts for full automation (env var only; does not mutate the
# user's persistent gcloud config like "gcloud config set" would)
export CLOUDSDK_CORE_DISABLE_PROMPTS=1

# --- Check for required tools ---
echo "⚙️  Checking for required tools..."
for tool in jq curl gcloud bq make uv git python3; do
  if ! command -v \$tool >/dev/null 2>&1; then
    echo "❌ Error: \$tool is not installed. Please install it and try again."
    exit 1
  fi
done

# --- Network resiliency for package installation ---
echo "⚙️  Configuring robust network timeouts for package resolution..."
export UV_HTTP_TIMEOUT=600
export UV_RETRIES=10

# --- Detect Project ID early ---
PROJECT_ID=$(gcloud config get-value project 2>/dev/null)
if [ -z "$PROJECT_ID" ]; then
  echo "❌ Error: No default project found in your environment."
  echo "Please run 'gcloud config set project [PROJECT_ID]' first."
  exit 1
fi

# --- Authentication & Permissions Check ---
echo "🔐 Checking authentication..."
if ! gcloud auth application-default print-access-token >/dev/null 2>&1 || ! gcloud auth print-access-token >/dev/null 2>&1; then
  echo "❌ Error: Google Cloud credentials have expired or are missing."
  echo "💡 Please run the following commands to re-authenticate:"
  echo "    gcloud auth login"
  echo "    gcloud auth application-default login"
  echo "Then re-run this setup script."
  exit 1
fi

PROJECT_NUMBER=$(gcloud projects describe "$PROJECT_ID" --format="value(projectNumber)" 2>/dev/null || echo "")
if [ -z "$PROJECT_NUMBER" ]; then
  echo "❌ Error: Could not retrieve project details. The project ID might be invalid or you lack permissions."
  exit 1
fi

# --- Runtime SA + dashboards bucket (defined early so --cleanup can reference them) ---
# COMPUTE_SA is the default Cloud Run runtime identity; DASH_BUCKET holds the
# interactive HTML dashboards the agent publishes (non-public, served via V4 signed URLs).
# Bucket name includes the demo name + suffix (like other resources); prefixed with the
# globally-unique PROJECT_ID for global bucket-name uniqueness, and the redundant leading
# "demo-" is stripped from dirName to stay within the 63-char GCS bucket-name limit.
COMPUTE_SA="\${PROJECT_NUMBER}-compute@developer.gserviceaccount.com"
DASH_BUCKET="\${PROJECT_ID}-${dirName.replace(/^demo-/, '')}-dash"

# --- Disk Space Check (Skip if in cleanup mode) ---
if [ "$CLEANUP_MODE" != "true" ]; then
  echo "💾 Checking disk space..."
  FREE_SPACE=$(df -k . | awk 'NR==2 {print $4}')
  if [ "$FREE_SPACE" -lt 1048576 ]; then
    echo "⚠️  CRITICAL: Low disk space detected ($((FREE_SPACE/1024)) MB left)."
    echo "    Deployment will likely fail (needs ~1GB free)."
    echo "    Use the cleanup command to free up space:"
    echo "    cd ~ && bash \$0 --cleanup"
    echo ""
    if [ "\$AUTO_CONFIRM" = "true" ]; then
      echo "Proceeding despite low disk space (--yes)."
    else
      read -p "Attempt to continue anyway? (y/n) " -n 1 -r
      echo
      if [[ ! $REPLY =~ ^[Yy]$ ]]; then exit 1; fi
    fi
  fi
fi

# --- Cleanup Mode Handler ---
  if [ "$CLEANUP_MODE" = "true" ]; then
    echo ""
    echo "========================================================="
    echo "🧹 DEMO CLEANUP MODE"
    echo "========================================================="
    echo ""
    echo "This will delete the following resources:"
    echo "  • BigQuery Dataset: ${datasetId}"
    echo "  • Maps API Key: MCP-Demo-Key-${suffix}"
    echo "  • Cloud Run Main Service: ${dirName} (if deployed)"
    echo "  • Cloud Run Live Viewer Function: ${dirName}-viewer"
    echo "  • Firestore Collection: ${fsCollection}"
    echo "  • Gemini Enterprise registration (App): ${dirName}"
    echo "  • Custom MCP Secrets in Secret Manager (if exist)"
    echo "  • Maps API Key Secret: ${dirName}-maps-key"
    echo "  • Agent Engine (Sandbox): ${dirName}-sandbox"
${ enableManagedAgent ? `    echo "  • Managed Agent (Antigravity): ${managedAgentId} (location: global; its sandbox environments expire automatically after 7 idle days)"
` : ''}    echo "  • Dashboards GCS Bucket: \$DASH_BUCKET (+ signBlob self-binding)"
    echo "  • Pub/Sub Topics: ${dirName}-sched-tasks, ${dirName}-task-results"
    echo "  • Pub/Sub Subscriptions: ${dirName}-sched-tasks-push, ${dirName}-task-results-push"
    echo "  • Cloud Scheduler Jobs: ${dirName}-sched-* (if any)"
    echo "  • Firestore Task Collections: ${dirName}_task_definitions, ${dirName}_task_executions"
    echo "  • Local Directory: ~/${dirName}"
    echo ""
    _HAS_SLACK=\$(gcloud secrets describe "${dirName}-slack-token" --project="\$PROJECT_ID" 2>/dev/null && echo "yes" || echo "no")
    if [ "\$_HAS_SLACK" = "yes" ]; then
      echo "⚠️  Manual cleanup required after deletion:"
      echo "  • Slack App: GE-${dirName}"
      echo "    → Delete manually at https://api.slack.com/apps"
      echo ""
    fi

    if [ "\$AUTO_CONFIRM" = "true" ]; then
      echo "Proceeding without confirmation (--yes)."
    else
      read -p "Are you sure you want to proceed? (y/n) " -n 1 -r
      echo
      if [[ ! \$REPLY =~ ^[Yy]$ ]]; then
        echo "Cleanup cancelled."
        exit 0
      fi
    fi
    
    TOKEN=$(gcloud auth print-access-token 2>/dev/null)
${ enableManagedAgent ? `
    echo ""
    echo "🤖 Deleting Managed Agent (Antigravity): ${managedAgentId}..."
    _MA_DEL_CODE=\$(curl -s -o /dev/null -w "%{http_code}" -X DELETE \\
      -H "Authorization: Bearer \$TOKEN" \\
      "https://aiplatform.googleapis.com/v1beta1/projects/\$PROJECT_ID/locations/global/agents/${managedAgentId}" 2>/dev/null)
    if [ "\$_MA_DEL_CODE" = "200" ]; then
      echo "   ✅ Managed Agent delete requested (long-running operation; sandbox environments also expire on their own after 7 idle days)."
    else
      echo "   ⚠️  Managed Agent not found or delete failed (HTTP \$_MA_DEL_CODE)."
    fi
` : ''}
    echo ""
    echo "🗑️  Deleting BigQuery Dataset: ${datasetId}..."
    bq rm -r -f -d \$PROJECT_ID:${datasetId} 2>/dev/null && echo "   ✅ Dataset deleted." || echo "   ⚠️  Dataset not found or already deleted."
    
    echo ""
    echo "🔑 Deleting Maps API Key: MCP-Demo-Key-${suffix}..."
    KEY_NAME=$(gcloud alpha services api-keys list --filter="displayName:MCP-Demo-Key-${suffix}" --format="value(name)" 2>/dev/null || echo "")
    if [ ! -z "\$KEY_NAME" ]; then
      DELETED_ALL=true
      for KN in \$KEY_NAME; do
        gcloud alpha services api-keys delete "\$KN" --quiet 2>/dev/null || DELETED_ALL=false
      done
      if \$DELETED_ALL; then
        echo "   ✅ API Key deleted."
      else
        echo "   ⚠️  Failed to delete one or more API Keys."
      fi
    else
      echo "   ⚠️  API Key not found or already deleted."
    fi

    echo ""
    echo "🚀 Deleting Cloud Run services and functions..."
    
    # Find region for main service
    MAIN_REGION=\$(gcloud run services list --filter="metadata.name:${dirName}" --format="value(region)" 2>/dev/null | head -n 1)
    if [ ! -z "\$MAIN_REGION" ]; then
      gcloud run services delete ${dirName} --region="\$MAIN_REGION" --quiet 2>/dev/null && echo "   ✅ Cloud Run main service deleted." || echo "   ⚠️  Failed to delete Main service."
    else
      echo "   ⚠️  Main service not found or already deleted."
    fi

    # Find region for viewer function (which is a Cloud Run service under the hood in Gen2)
    VIEWER_REGION=\$(gcloud run services list --filter="metadata.name:${dirName}-viewer" --format="value(region)" 2>/dev/null | head -n 1)
    if [ ! -z "\$VIEWER_REGION" ]; then
      gcloud functions delete ${dirName}-viewer --gen2 --region="\$VIEWER_REGION" --quiet 2>/dev/null && echo "   ✅ Live Viewer Cloud Run Function deleted." || echo "   ⚠️  Failed to delete Live Viewer Function."
    else
      echo "   ⚠️  Live Viewer Function not found or already deleted."
    fi

    # --- Dashboards bucket + signBlob self-binding ---
    echo "🪣 Deleting dashboards bucket: \$DASH_BUCKET ..."
    if gcloud storage buckets describe "gs://\$DASH_BUCKET" >/dev/null 2>&1; then
      gcloud storage rm --recursive "gs://\$DASH_BUCKET" --quiet 2>/dev/null && echo "   ✅ Dashboards bucket and objects deleted." || echo "   ⚠️  Failed to delete dashboards bucket."
    else
      echo "   ⚠️  Dashboards bucket not found or already deleted."
    fi

    echo "🔐 Removing signBlob (token-creator) self-binding on the runtime SA..."
    gcloud iam service-accounts remove-iam-policy-binding "\$COMPUTE_SA" \
      --member="serviceAccount:\$COMPUTE_SA" \
      --role="roles/iam.serviceAccountTokenCreator" \
      --project="$PROJECT_ID" --quiet >/dev/null 2>&1 && echo "   ✅ signBlob self-binding removed." || echo "   ⚠️  Self-binding not present or removal failed."






    echo ""
    echo "🔥 Deleting Firestore Collection: ${fsCollection}..."
    if command -v uv >/dev/null 2>&1; then
      GOOGLE_API_USE_CLIENT_CERTIFICATE=false uv run --with google-cloud-firestore python3 -c "from google.cloud import firestore; db=firestore.Client(); [d.reference.delete() for d in db.collection('${fsCollection}').stream()]" 2>/dev/null && echo "   ✅ Firestore documents in collection deleted." || echo "   ⚠️  Could not clear Firestore collection automatically."
    fi

    echo ""
    echo "🌍 Deleting Gemini Enterprise registration (App/Agent)..."
    # Phase 1: scan all common locations and collect EVERY matching agent
    # (setup re-runs can leave duplicate registrations; delete them all).
    _GE_TARGETS=""
    for LOC in "global" "us" "eu"; do
      if [ "\$LOC" = "global" ]; then
        ENDPOINT="discoveryengine.googleapis.com"
      else
        ENDPOINT="\${LOC}-discoveryengine.googleapis.com"
      fi

      ENGINES_JSON=$(curl -s -H "Authorization: Bearer \$TOKEN" -H "X-Goog-User-Project: \$PROJECT_ID" \
        "https://\$ENDPOINT/v1alpha/projects/\$PROJECT_ID/locations/\$LOC/collections/default_collection/engines" || true)

      # 2. If no engine match, scan for individual agents within EXISTING engines in this location
      for E_NAME in $(echo "\$ENGINES_JSON" | jq -r '.engines[]? | .name'); do
        ASSISTANTS=$(curl -s -H "Authorization: Bearer \$TOKEN" -H "X-Goog-User-Project: \$PROJECT_ID" "https://\$ENDPOINT/v1alpha/\${E_NAME}/assistants" || true)
        for A_NAME in $(echo "\$ASSISTANTS" | jq -r '.assistants[]? | .name'); do
          AGENTS_JSON=$(curl -s -H "Authorization: Bearer \$TOKEN" -H "X-Goog-User-Project: \$PROJECT_ID" "https://\$ENDPOINT/v1alpha/\${A_NAME}/agents?pageSize=100" || true)
          _GE_MATCHES=$(echo "\$AGENTS_JSON" | jq -r --arg dir "${dirName}" '.agents[]? | select(.a2aAgentDefinition.jsonAgentCard != null) | select((.a2aAgentDefinition.jsonAgentCard | try (fromjson | .name)) == $dir) | .name' 2>/dev/null || true)
          for _GE_N in \$_GE_MATCHES; do
            if [ "\$_GE_N" != "null" ]; then
              _GE_TARGETS="\$_GE_TARGETS https://\$ENDPOINT/v1alpha/\$_GE_N"
            fi
          done
        done
      done
    done

    # Phase 2: delete every collected registration (404 = already gone = OK).
    _GE_TARGETS=$(echo "\$_GE_TARGETS" | xargs -n1 2>/dev/null | sort -u || true)
    if [ -z "\$_GE_TARGETS" ]; then
      echo "   ⚠️  Gemini Enterprise Agent not found or already unlisted."
    else
      for _GE_URL in \$_GE_TARGETS; do
        echo "   🗑 Unregistering Gemini Enterprise Agent: \$_GE_URL..."
        _GE_CODE=$(curl -s -o /dev/null -w "%{http_code}" -X DELETE -H "Authorization: Bearer \$TOKEN" -H "X-Goog-User-Project: \$PROJECT_ID" "\$_GE_URL" 2>/dev/null || true)
        if [ "\$_GE_CODE" = "200" ] || [ "\$_GE_CODE" = "404" ]; then
          echo "   ✅ Gemini Enterprise Agent unlisted (HTTP \$_GE_CODE)."
        else
          echo "   ⚠️  Failed to unlist Gemini Enterprise Agent (HTTP \$_GE_CODE)."
        fi
      done
    fi
    


    # Authorization resource only exists when Google Workspace MCP was configured
    AUTH_PATH="projects/\$PROJECT_ID/locations/global/authorizations/${dirName}-auth"
    _AUTH_EXISTS=\$(curl -s -o /dev/null -w "%{http_code}" -H "Authorization: Bearer \$TOKEN" -H "X-Goog-User-Project: \$PROJECT_ID" "https://discoveryengine.googleapis.com/v1alpha/\$AUTH_PATH")
    if [ "\$_AUTH_EXISTS" = "200" ]; then
      echo ""
      echo "🔐 Deleting Gemini Enterprise Authorization Resource: ${dirName}-auth..."
      if curl -s --fail -X DELETE \
        -H "Authorization: Bearer \$TOKEN" \
        -H "X-Goog-User-Project: \$PROJECT_ID" \
        "https://discoveryengine.googleapis.com/v1alpha/\$AUTH_PATH" > /dev/null; then
        echo "   ✅ Authorization resource deleted."
      else
        echo "   ⚠️  Failed to delete Authorization resource."
      fi
    fi

    echo ""
    echo "🗑️  Deleting any custom MCP secrets from Secret Manager..."
    # Search for all secrets containing the suffix (includes Slack token secret)
    MCP_SECRETS=\$(gcloud secrets list --format="value(name)" 2>/dev/null | grep "${suffix}" || true)
    if [ ! -z "\$MCP_SECRETS" ]; then
      for SEC in \$MCP_SECRETS; do
         gcloud secrets delete "\$SEC" --quiet 2>/dev/null && echo "      ✅ Secret deleted: \$SEC" || echo "      ⚠️  Failed to delete Secret: \$SEC"
      done
    else
      echo "   ✅ No custom MCP secrets found."
    fi


    echo ""
    echo "🧪 Deleting Agent Engine (Sandbox) instances..."
    # Find ALL engines whose display name matches this demo, not just the one in
    # .env: setup re-runs can leave orphaned engines behind, and this also works
    # when the local demo directory (and its .env) was already deleted manually.
    # Pure REST (curl): no uv/SDK download needed just to issue a DELETE.
    _AE_API="https://us-central1-aiplatform.googleapis.com/v1beta1"
    _AE_PARENT="projects/\$PROJECT_ID/locations/us-central1"
    _AE_LIST=""
    _AE_PAGE=""
    while :; do
      _AE_URL="\$_AE_API/\$_AE_PARENT/reasoningEngines?pageSize=100"
      if [ -n "\$_AE_PAGE" ]; then _AE_URL="\$_AE_URL&pageToken=\$_AE_PAGE"; fi
      _AE_JSON=$(curl -s -H "Authorization: Bearer \$TOKEN" "\$_AE_URL" 2>/dev/null || true)
      _AE_MATCHES=$(echo "\$_AE_JSON" | jq -r --arg dn "${dirName}-sandbox" '.reasoningEngines[]? | select(.displayName == $dn) | .name' 2>/dev/null || true)
      _AE_LIST="\$_AE_LIST \$_AE_MATCHES"
      _AE_PAGE=$(echo "\$_AE_JSON" | jq -r '.nextPageToken // empty' 2>/dev/null || true)
      if [ -z "\$_AE_PAGE" ]; then break; fi
    done
    _AE_LIST=$(echo "\$_AE_LIST" | xargs -n1 2>/dev/null | sort -u || true)
    if [ -z "\$_AE_LIST" ]; then
      echo "   ⚠️  No Agent Engine named '${dirName}-sandbox' found (already deleted?)."
    else
      for _AE in \$_AE_LIST; do
        _AE_CODE=""
        for _AE_TRY in 1 2 3; do
          _AE_CODE=$(curl -s -o /dev/null -w "%{http_code}" -X DELETE -H "Authorization: Bearer \$TOKEN" "\$_AE_API/\$_AE?force=true" 2>/dev/null || true)
          if [ "\$_AE_CODE" = "429" ]; then sleep $((_AE_TRY * 10)); else break; fi
        done
        if [ "\$_AE_CODE" = "200" ] || [ "\$_AE_CODE" = "404" ]; then
          echo "   ✅ Delete requested: \$_AE (HTTP \$_AE_CODE)"
        else
          echo "   ⚠️  Failed to delete \$_AE (HTTP \$_AE_CODE). Delete it manually from the console."
        fi
      done
      # Deletion is async (long-running operation); verify with a re-list.
      sleep 5
      _AE_LEFT=$(curl -s -H "Authorization: Bearer \$TOKEN" "\$_AE_API/\$_AE_PARENT/reasoningEngines?pageSize=200" 2>/dev/null | jq -r --arg dn "${dirName}-sandbox" '[.reasoningEngines[]? | select(.displayName == $dn)] | length' 2>/dev/null || true)
      if [ -z "\$_AE_LEFT" ] || [ "\$_AE_LEFT" = "0" ]; then
        echo "   ✅ Agent Engine cleanup verified (none remaining)."
      else
        echo "   ⚠️  \$_AE_LEFT Agent Engine(s) still listed (async deletion may be in progress)."
        echo "       Re-run cleanup or check the Vertex AI Agent Platform console if they persist."
      fi
    fi

    echo ""
    echo "📨 Deleting Pub/Sub topics and subscriptions..."
    for SUB in "${dirName}-sched-tasks-push" "${dirName}-task-results-push"; do
      gcloud pubsub subscriptions delete "$SUB" --project="$PROJECT_ID" --quiet 2>/dev/null \\
        && echo "   ✅ Subscription deleted: $SUB" \\
        || echo "   ⚠️  Subscription not found: $SUB"
    done
    for TOP in "${dirName}-sched-tasks" "${dirName}-task-results"; do
      gcloud pubsub topics delete "$TOP" --project="$PROJECT_ID" --quiet 2>/dev/null \\
        && echo "   ✅ Topic deleted: $TOP" \\
        || echo "   ⚠️  Topic not found: $TOP"
    done

    echo ""
    echo "⏰ Deleting Cloud Scheduler jobs..."
    SCHED_JOBS=$(gcloud scheduler jobs list --location=us-central1 --project="$PROJECT_ID" \\
      --format="value(name)" 2>/dev/null | grep "${dirName}-sched-" || true)
    if [ -n "$SCHED_JOBS" ]; then
      for JOB in $SCHED_JOBS; do
        gcloud scheduler jobs delete "$JOB" --location=us-central1 \\
          --project="$PROJECT_ID" --quiet 2>/dev/null \\
          && echo "   ✅ Scheduler job deleted: $JOB" \\
          || echo "   ⚠️  Failed to delete: $JOB"
      done
    else
      echo "   ✅ No Cloud Scheduler jobs found."
    fi

    echo ""
    echo "📁 Deleting Firestore task collections..."
    GOOGLE_API_USE_CLIENT_CERTIFICATE=false uv run --no-project --with google-cloud-firestore python3 -c "
from google.cloud import firestore
db = firestore.Client()
for coll_name in ['${dirName}_task_definitions', '${dirName}_task_executions', '${dirName}_task_push_configs']:
    docs = list(db.collection(coll_name).stream())
    for doc in docs:
        doc.reference.delete()
    print('   ✅ Deleted ' + str(len(docs)) + ' docs from ' + coll_name)
" 2>/dev/null || echo "   ⚠️  Could not clear Firestore task collections."

    echo ""
    echo "📂 Deleting local directories and caches..."
    cd ~
    rm -rf ~/${dirName}
    # The uv cache is shared machine-wide and may be in use by other processes;
    # best-effort removal must never abort cleanup (set -e) before the banner.
    rm -rf ~/.cache/uv 2>/dev/null || true
    echo "   ✅ Local workspace directory, viewer code, and caches deleted."

    # Only show Slack cleanup if the Slack MCP server was configured
    if gcloud secrets describe "${dirName}-slack-token" --project="\$PROJECT_ID" >/dev/null 2>&1; then
      echo ""
      echo "📱 Slack App (manual cleanup required):"
      echo "   ⚠️  Please delete the Slack App manually at: https://api.slack.com/apps"
      echo "   Look for an app named 'GE-${dirName}' and delete it."
    fi

    echo ""
    echo "========================================================="
    echo "✅ CLEANUP COMPLETE"
    echo "========================================================="
    exit 0
  fi

# --- Agent display name (human-readable label shown in Gemini Enterprise). ---
# Only the human-readable part is customizable. The "(${dirName})" suffix is
# appended at registration and MUST stay fixed so --cleanup can reliably find
# and remove this demo's resources.
AGENT_DISPLAY_NAME='${safeShortName}' # ge:agent-display-name

# --- 1. Project Detection & Confirmation Loop ---
while true; do
  echo "========================================================="
  echo "⚡ GE Demo Generator - Setup Script"
  echo "   Version:      ${CONFIG.APP_VERSION}"
  echo "   Generated At: ${new Date().toISOString()}"
  echo "   Options:      --help | --cleanup | --model-analysis-agent | --model-root-agent"
  echo "========================================================="
  echo "🚀 Target Project: \$PROJECT_ID"
  echo "🤖 Agent Name:    \$AGENT_DISPLAY_NAME (${dirName})"
  echo '📝 Description:   ${safeSummary}'
  echo "📂 Demo Asset Directory: ~/${dirName}"
  echo "🧠 Agent Models:   root_agent: \$AGENT_MODEL_LITE / deep_analysis_agent: \$AGENT_MODEL"
  echo "🧪 Code Sandbox:   ✅ Enabled (Agent Runtime)"
  ${ enableComputerUse ? `echo "🖥️ Computer Use:   ✅ Enabled (Browser Agent)"\n` : ''}${ enableManagedAgent ? `echo "🤖 Managed Agent:  ✅ Enabled (Antigravity autonomous sandbox - provisioned in parallel with setup)"\n` : ''}${ enableWorkspaceMcp ? `echo "🔌 Google Workspace MCP: Enabled"\n` : ''}${ (enableWorkspaceAuth && !enableWorkspaceMcp) ? `echo "🔐 Workspace Auth: ✅ Enabled (user OAuth, no MCP servers)"\n` : ''}${mcpBanner}echo "========================================================="
  
  echo "Choose an option:"
  echo "  [Y] Yes, proceed with this project (Default)"
  echo "  [N] No, cancel deployment"
  echo "  [M] Modify the root agent model (Change to gemini-3.5-flash-lite)"
  echo ""
  read -p "▶ Enter choice [Y/n/m]: " REPLY
  echo
  
  # Clean up input
  REPLY=\$(echo "\$REPLY" | tr -d '\\r\\n\\t ')
  
  # Default to 'y' if user pressed enter
  if [ -z "\$REPLY" ]; then
    REPLY="y"
  fi
  
  if [[ "\$REPLY" =~ ^[Yy]$ ]]; then
    break
  elif [[ "\$REPLY" =~ ^[Nn]$ ]]; then
    echo "❌ Deployment cancelled by user."
    exit 1
  elif [[ "\$REPLY" =~ ^[Mm]$ ]]; then
    # --- Model Selection Flow ---
    echo ""
    echo "🧠 Configure Chat & Orchestration Model (root_agent):"
    echo "   - root_agent (Chat/UI): Uses 'gemini-3.6-flash' by default."
    echo "   - deep_analysis_agent (Reasoning): Uses 'gemini-3.6-flash'."
    echo ""
    echo "   You can choose 'gemini-3.5-flash-lite' for the root_agent."
    echo "   While it yields simpler and more concise responses, it provides"
    echo "   much faster and snappier interactions for routine chat."
    echo "   For complex tasks requiring deep analysis, the root_agent can"
    echo "   still delegate the work to the deep_analysis_agent (3.6-flash)."
    echo ""
    read -p "▶ Use lightweight gemini-3.5-flash-lite for root_agent? (Y/n): " CHOOSE_LITE
    CHOOSE_LITE=\$(echo "\$CHOOSE_LITE" | tr -d '\\r\\n\\t ')
    
    # Default to 'y' since they specifically selected 'M' to configure
    if [ -z "\$CHOOSE_LITE" ]; then
      CHOOSE_LITE="y"
    fi
    
    if [[ "\$CHOOSE_LITE" =~ ^[Yy]$ ]]; then
      AGENT_MODEL_LITE="gemini-3.5-flash-lite"
      echo "   ✅ Configured root_agent to use: gemini-3.5-flash-lite"
    else
      AGENT_MODEL_LITE="gemini-3.6-flash"
      echo "   ℹ️  Keeping default root_agent: gemini-3.6-flash"
    fi
    echo ""
    # Directly proceed to deployment steps after configuration is complete
    break
  else
    echo "⚠️  Invalid choice. Please enter Y, N, or M."
    echo ""
  fi
done



# --- 1.2 Gemini Enterprise Pre-Deployment Check ---
echo ""
echo "========================================================="
echo "🤖 GEMINI ENTERPRISE PRE-DEPLOYMENT CHECK"
echo "========================================================="
echo "This setup script will automatically deploy to Cloud Run and"
echo "register it to Gemini Enterprise."
echo ""
echo "🔍 Checking for an existing Gemini Enterprise app in this project..."

# Reuse the same Discovery Engine app-detection logic used later during agent
# registration: list engines across common locations and keep only real
# Gemini Enterprise apps (SUBSCRIPTION_TIER_SEARCH_AND_ASSISTANT).
GE_TOKEN=$(gcloud auth application-default print-access-token 2>/dev/null || gcloud auth print-access-token 2>/dev/null)
GE_APP_FOUND=0
GE_APP_LIST=()
if [ ! -z "\$GE_TOKEN" ]; then
  for LOC in "global" "us" "eu"; do
    if [ "\$LOC" = "global" ]; then
      ENDPOINT="discoveryengine.googleapis.com"
    else
      ENDPOINT="\${LOC}-discoveryengine.googleapis.com"
    fi
    GE_JSON=$(curl -s -H "Authorization: Bearer \$GE_TOKEN" -H "X-Goog-User-Project: \$PROJECT_ID" \
      "https://\$ENDPOINT/v1alpha/projects/\$PROJECT_ID/locations/\$LOC/collections/default_collection/engines")
    # Emit "displayName|appId" per real Gemini Enterprise app in this location.
    GE_APPS_INFO=$(echo "\$GE_JSON" | python3 -c '
import sys, json
try:
    data = json.load(sys.stdin)
    engines = [e for e in data.get("engines", []) if e.get("searchEngineConfig", {}).get("requiredSubscriptionTier") == "SUBSCRIPTION_TIER_SEARCH_AND_ASSISTANT"]
    for e in engines:
        print((e.get("displayName") or "(unnamed)") + "|" + e["name"].split("/")[-1])
except Exception:
    pass
')
    if [ ! -z "\$GE_APPS_INFO" ]; then
      while read -r line; do
        if [ ! -z "\$line" ]; then
          GE_DISPLAY_NAME=$(echo "\$line" | cut -d'|' -f1)
          GE_APP_ID=$(echo "\$line" | cut -d'|' -f2)
          GE_APP_LIST+=("\$GE_DISPLAY_NAME (id: \$GE_APP_ID, location: \$LOC)")
          GE_APP_FOUND=\$((GE_APP_FOUND + 1))
        fi
      done <<< "\$GE_APPS_INFO"
    fi
  done
fi

if [ "\$GE_APP_FOUND" -gt 0 ] 2>/dev/null; then
  echo "✅ Found \$GE_APP_FOUND Gemini Enterprise app(s) in this project:"
  for GE_APP in "\${GE_APP_LIST[@]}"; do
    echo "   • \$GE_APP"
  done
  echo "Proceeding automatically."
else
  echo ""
  echo "⚠️  Could not automatically detect a Gemini Enterprise app in 'global', 'us', or 'eu'."
  echo "   (This can also happen if the Discovery Engine API is not yet enabled, or if"
  echo "    your account lacks permission to list apps — in which case detection may be"
  echo "    a false negative.)"
  echo ""

  GE_APP_CREATED=""
  if [ ! -z "\$GE_TOKEN" ]; then
    # The bulk API-enable step runs later in this script, so make sure the
    # Discovery Engine API is on before probing subscriptions (fresh projects).
    gcloud services enable discoveryengine.googleapis.com --project "\$PROJECT_ID" >/dev/null 2>&1 || true
    # Check for an active Gemini Enterprise subscription (license config).
    GE_LICENSE_STATE=$(curl -s -H "Authorization: Bearer \$GE_TOKEN" -H "X-Goog-User-Project: \$PROJECT_ID" \
      "https://discoveryengine.googleapis.com/v1alpha/projects/\$PROJECT_ID/locations/global/licenseConfigs" \
      | python3 -c '
import sys, json
try:
    configs = json.load(sys.stdin).get("licenseConfigs", [])
    active = any(c.get("state") == "ACTIVE" and c.get("subscriptionTier") == "SUBSCRIPTION_TIER_SEARCH_AND_ASSISTANT" for c in configs)
    print("ACTIVE" if active else "INACTIVE")
except Exception:
    print("UNKNOWN")
' 2>/dev/null)

    # No active subscription: offer to start a free trial automatically.
    # Safety: the request always pins freeTrial=true and the result is only
    # accepted if the server confirms an ACTIVE free trial. A paid
    # subscription is NEVER purchased automatically.
    if [ "\$GE_LICENSE_STATE" != "ACTIVE" ]; then
      echo "ℹ️  No active Gemini Enterprise subscription was found in this project."
      echo "   The script can provision this project for Gemini Enterprise and start a"
      echo "   free trial subscription. Proceeding means you accept:"
      echo "   - the Terms for data use (https://cloud.google.com/retail/data-use-terms)"
      echo "   - the Gemini Enterprise (Agentspace) quality-of-service terms"
      read -p "   Start a free trial subscription automatically? (y/n) " -n 1 -r
      echo
      if [[ \$REPLY =~ ^[Yy]$ ]]; then
        TRIAL_OUT=$(python3 - "\$PROJECT_ID" "\$GE_TOKEN" << 'PYEOF'
import sys, json, time, datetime, urllib.request, urllib.error
project_id, token = sys.argv[1], sys.argv[2]
headers = {
    "Authorization": "Bearer " + token,
    "Content-Type": "application/json",
    "X-Goog-User-Project": project_id,
}
api = "https://discoveryengine.googleapis.com/v1alpha/"

# Step 1: provision the project for Discovery Engine / Gemini Enterprise.
# This creates the default user store required by license configs. Idempotent
# on already-provisioned projects. The user consented to the terms above.
prov_body = {
    "acceptDataUseTerms": True,
    "dataUseTermsVersion": "2022-11-23",
    "saasParams": {"acceptBizQos": True},
}
req = urllib.request.Request(api + "projects/" + project_id + ":provision",
                             data=json.dumps(prov_body).encode("utf-8"), headers=headers)
try:
    with urllib.request.urlopen(req) as resp:
        op = json.loads(resp.read().decode("utf-8"))
except urllib.error.HTTPError as e:
    print("TRIAL_FAIL: provisioning failed: HTTP " + str(e.code) + " " + e.read().decode("utf-8")[:300])
    sys.exit(1)
except Exception as e:
    print("TRIAL_FAIL: provisioning failed: " + str(e))
    sys.exit(1)
deadline = time.time() + 120
while not op.get("done") and op.get("name") and time.time() < deadline:
    time.sleep(5)
    try:
        with urllib.request.urlopen(urllib.request.Request(api + op["name"], headers=headers)) as resp:
            op = json.loads(resp.read().decode("utf-8"))
    except Exception:
        pass
if not op.get("done") or op.get("error"):
    print("TRIAL_FAIL: provisioning did not complete: " + json.dumps(op.get("error") or {})[:300])
    sys.exit(1)

# Step 2: create the free trial license config. freeTrial is pinned to True
# and the result is only accepted if the server confirms an ACTIVE free
# trial - a paid subscription is NEVER purchased automatically.
# The server validates startDate as "future" against Pacific time, so
# passing today's local date fails with 400 whenever local date == PT date.
# Always send tomorrow: the server still activates the trial immediately
# (state=ACTIVE) and normalizes the term to one month.
start = datetime.date.today() + datetime.timedelta(days=1)
end = start + datetime.timedelta(days=30)
body = {
    "subscriptionTier": "SUBSCRIPTION_TIER_SEARCH_AND_ASSISTANT",
    "licenseCount": "50",
    "subscriptionTerm": "SUBSCRIPTION_TERM_CUSTOM",
    "startDate": {"year": start.year, "month": start.month, "day": start.day},
    "endDate": {"year": end.year, "month": end.month, "day": end.day},
    "freeTrial": True,
}
url = (api + "projects/" + project_id
       + "/locations/global/licenseConfigs?licenseConfigId=free_trial_agent_space")
req = urllib.request.Request(url, data=json.dumps(body).encode("utf-8"), headers=headers)
try:
    with urllib.request.urlopen(req) as resp:
        data = json.loads(resp.read().decode("utf-8"))
except urllib.error.HTTPError as e:
    print("TRIAL_FAIL: HTTP " + str(e.code) + " " + e.read().decode("utf-8")[:300])
    sys.exit(1)
except Exception as e:
    print("TRIAL_FAIL: " + str(e))
    sys.exit(1)
if data.get("freeTrial") is True and data.get("state") == "ACTIVE":
    print("TRIAL_OK")
else:
    print("TRIAL_FAIL: the created config is not a confirmed active free trial"
          + " (state=" + str(data.get("state")) + ", freeTrial=" + str(data.get("freeTrial"))
          + "). Please check the Gemini Enterprise console.")
    sys.exit(1)
PYEOF
) || true
        if echo "\$TRIAL_OUT" | grep -q "^TRIAL_OK"; then
          echo "   ✅ Free trial subscription activated."
          GE_LICENSE_STATE="ACTIVE"
        else
          echo "   ⚠️  Could not start a free trial automatically:"
          echo "\$TRIAL_OUT" | sed 's/^/      /'
        fi
      fi
    fi

    # Active subscription: offer to create the Gemini Enterprise app automatically.
    if [ "\$GE_LICENSE_STATE" = "ACTIVE" ]; then
      read -p "   Create a Gemini Enterprise app in this project automatically now? (y/n) " -n 1 -r
      echo
      if [[ \$REPLY =~ ^[Yy]$ ]]; then
        echo "   ⏳ Creating Gemini Enterprise app (this can take a minute or two)..."
        CREATE_OUT=$(python3 - "\$PROJECT_ID" "\$GE_TOKEN" << 'PYEOF'
import sys, json, time, urllib.request, urllib.error
project_id, token = sys.argv[1], sys.argv[2]
headers = {
    "Authorization": "Bearer " + token,
    "Content-Type": "application/json",
    "X-Goog-User-Project": project_id,
}
engine_id = "gemini-enterprise-" + str(int(time.time()))
base = ("https://discoveryengine.googleapis.com/v1alpha/projects/" + project_id
        + "/locations/global/collections/default_collection/engines")
body = {
    "displayName": "Gemini Enterprise",
    "solutionType": "SOLUTION_TYPE_SEARCH",
    "appType": "APP_TYPE_INTRANET",
    "industryVertical": "GENERIC",
    "searchEngineConfig": {
        "searchTier": "SEARCH_TIER_ENTERPRISE",
        "searchAddOns": ["SEARCH_ADD_ON_LLM"],
        "requiredSubscriptionTier": "SUBSCRIPTION_TIER_SEARCH_AND_ASSISTANT",
    },
}
req = urllib.request.Request(base + "?engineId=" + engine_id,
                             data=json.dumps(body).encode("utf-8"), headers=headers)
try:
    with urllib.request.urlopen(req) as resp:
        op = json.loads(resp.read().decode("utf-8"))
except urllib.error.HTTPError as e:
    print("CREATE_FAIL: HTTP " + str(e.code) + " " + e.read().decode("utf-8")[:300])
    sys.exit(1)
except Exception as e:
    print("CREATE_FAIL: " + str(e))
    sys.exit(1)
op_name = op.get("name", "")
deadline = time.time() + 180
while op_name and not op.get("done") and time.time() < deadline:
    time.sleep(5)
    try:
        poll = urllib.request.Request("https://discoveryengine.googleapis.com/v1alpha/" + op_name, headers=headers)
        with urllib.request.urlopen(poll) as resp:
            op = json.loads(resp.read().decode("utf-8"))
    except Exception:
        pass
if op.get("error"):
    print("CREATE_FAIL: " + json.dumps(op["error"])[:300])
    sys.exit(1)
# Wait until the new app is visible in the engines list (later steps re-list it).
while time.time() < deadline:
    try:
        lst = urllib.request.Request(base, headers=headers)
        with urllib.request.urlopen(lst) as resp:
            engines = json.loads(resp.read().decode("utf-8")).get("engines", [])
        if any(e.get("name", "").endswith("/" + engine_id) for e in engines):
            print("GE_APP_CREATED:" + engine_id)
            sys.exit(0)
    except Exception:
        pass
    time.sleep(5)
print("CREATE_FAIL: the app did not appear in the engines list within the timeout")
sys.exit(1)
PYEOF
) || true
        GE_APP_CREATED=$(echo "\$CREATE_OUT" | grep "^GE_APP_CREATED:" | cut -d':' -f2)
        if [ ! -z "\$GE_APP_CREATED" ]; then
          echo "   ✅ Created Gemini Enterprise app: \$GE_APP_CREATED (location: global)"
          echo "Proceeding automatically."
        else
          echo "   ⚠️  Automatic app creation failed:"
          echo "\$CREATE_OUT" | sed 's/^/      /'
        fi
      fi
    fi
  fi

  if [ -z "\$GE_APP_CREATED" ]; then
    echo ""
    echo "   You MUST have a Gemini Enterprise instance already created in this project."
    echo "   If you haven't, please create one here first:"
    echo "   https://console.cloud.google.com/gemini-enterprise/products?project=$PROJECT_ID"
    echo ""
    read -p "Have you confirmed the instance exists? (y/n) " -n 1 -r
    echo
    if [[ ! \$REPLY =~ ^[Yy]$ ]]; then
        echo "Exiting. Please create the instance and run the script again."
        exit 1
    fi
  fi
fi

${wsmcpInstructions}

# --- 1.3 IAM Permission Check ---
echo "🔐 Checking for IAM permissions..."
if ! gcloud projects get-iam-policy "$PROJECT_ID" >/dev/null 2>&1; then
  echo "⚠️  WARNING: Cannot read IAM policy. You might not have permission to grant roles."
  echo "    If the deployment fails later, please check your permissions."
  echo "    (Needs Project IAM Admin or Owner role)"
fi

# --- 2. IAM & API Checks ---
${enableCommands}

# MCP credential collection (Slack OAuth, sidecar env vars) must run AFTER the
# API-enable batch above: these blocks write to Secret Manager, so
# secretmanager.googleapis.com has to be enabled first. Running them here also
# lets the (minutes-long) interactive OAuth steps double as propagation buffer.
${mcpReads}
${mcpCredentialSetup}

echo "📡 Enabling Cloud Run specific APIs..."
gcloud services enable \
  run.googleapis.com \
  cloudbuild.googleapis.com \
  artifactregistry.googleapis.com \
  --project="$PROJECT_ID"

# Fast IAM role granting: pre-checks existing roles, skips already-granted, no verification delay
grant_roles_fast() {
  local project=$1
  local member_prefix=$2
  local member=$3
  shift 3
  local roles_to_grant=("$@")

  echo "  📋 Fetching existing IAM bindings for $member..."
  local existing_roles
  existing_roles=$(gcloud projects get-iam-policy "$project" \
    --flatten="bindings[].members" \
    --format="value(bindings.role)" \
    --filter="bindings.members:$member_prefix:$member" 2>/dev/null || echo "")

  local skipped=0
  local granted=0

  for role in "\${roles_to_grant[@]}"; do
    if echo "$existing_roles" | grep -q "$role"; then
      echo "    ⏭ Already granted: $role"
      skipped=$((skipped + 1))
    else
      if gcloud projects add-iam-policy-binding "$project" \
        --member="$member_prefix:$member" \
        --role="$role" --condition=None >/dev/null 2>&1; then
        echo "    ✅ Granted: $role"
        granted=$((granted + 1))
      else
        echo "    ⚠️  WARNING: Failed to grant $role. Grant manually:"
        echo "       gcloud projects add-iam-policy-binding \"$project\" --member=\"$member_prefix:$member\" --role=\"$role\" --condition=None"
      fi
    fi
  done

  echo "  📊 IAM Summary: $granted newly granted, $skipped already existed"
}

# Ensure the default compute service account has required permissions
echo "🔐 Configuring IAM permissions for Cloud Run Service Account..."
PROJECT_NUMBER=$(gcloud projects describe "$PROJECT_ID" --format="value(projectNumber)")
COMPUTE_SA="\${PROJECT_NUMBER}-compute@developer.gserviceaccount.com"
grant_roles_fast "$PROJECT_ID" "serviceAccount" "\$COMPUTE_SA" \
  "roles/mcp.toolUser" "roles/bigquery.jobUser" "roles/bigquery.dataEditor" \
  "roles/serviceusage.serviceUsageConsumer" "roles/aiplatform.user" "roles/logging.logWriter" \
  "roles/datastore.user" "roles/storage.objectViewer" "roles/storage.objectAdmin" "roles/artifactregistry.admin" "roles/run.invoker" \
  "roles/pubsub.publisher" "roles/cloudscheduler.admin" "roles/dataplex.catalogViewer"

# Background task infra: Cloud Scheduler SA needs pubsub.publisher
echo "🔐 Configuring IAM for Cloud Scheduler Service Agent..."
SCHED_SA="service-\${PROJECT_NUMBER}@gcp-sa-cloudscheduler.iam.gserviceaccount.com"
grant_roles_fast "$PROJECT_ID" "serviceAccount" "\$SCHED_SA" "roles/pubsub.publisher"

echo "🔐 Configuring IAM permissions for Discovery Engine Service Agent..."
DISCOVERY_ENGINE_SA="service-\${PROJECT_NUMBER}@gcp-sa-discoveryengine.iam.gserviceaccount.com"
grant_roles_fast "$PROJECT_ID" "serviceAccount" "\$DISCOVERY_ENGINE_SA" "roles/run.invoker"

# --- Dashboards: signBlob self-binding + non-public bucket for interactive HTML dashboards ---
# The runtime SA has no key file, so V4 signed URLs are minted via the IAM signBlob API.
# That requires the SA to hold token-creator on ITSELF (a resource-level binding on the
# SA, not a project-level role -- so it cannot go through grant_roles_fast).
echo "🔐 Granting signBlob (token-creator) on the runtime SA to itself..."
if gcloud iam service-accounts add-iam-policy-binding "\$COMPUTE_SA" \
    --member="serviceAccount:\$COMPUTE_SA" \
    --role="roles/iam.serviceAccountTokenCreator" \
    --project="$PROJECT_ID" --quiet >/dev/null 2>&1; then
  echo "  ✅ signBlob self-binding granted."
else
  echo "  ⚠️  Failed to grant signBlob self-binding (V4 signed URLs may fail)."
fi

echo "🪣 Creating non-public dashboards bucket: \$DASH_BUCKET ..."
if gcloud storage buckets describe "gs://\$DASH_BUCKET" >/dev/null 2>&1; then
  echo "  ⏭ Bucket already exists."
else
  if _DASH_CREATE_ERR=\$(gcloud storage buckets create "gs://\$DASH_BUCKET" \
      --project="$PROJECT_ID" \
      --location=us-central1 \
      --uniform-bucket-level-access \
      --public-access-prevention 2>&1); then
    echo "  ✅ Bucket created (uniform access; public access prevention enforced)."
  else
    echo "  ⚠️  Bucket create failed. gcloud reported:"
    echo "\$_DASH_CREATE_ERR" | sed 's/^/       /'
    echo "       (Dashboards will not work until this bucket exists. Re-run after resolving,"
    echo "        or create it manually with the same name: \$DASH_BUCKET)"
  fi
fi

# No object lifecycle rule: published dashboards persist so they stay viewable from the
# Cloud Console (and re-signable) after the signed URL expires. The whole bucket is
# removed on --cleanup.

# --- Agent Template Fetch (pinned) ---
# Static Python/JSON files (ADK agent runtime, A2UI examples, data viewer) are
# fetched from the repo at a pinned ref instead of being embedded here.
echo "📥 Fetching agent template (ref ${templateRef})..."
GE_TPL_ROOT="$(pwd)/_ge_template"
rm -rf "$GE_TPL_ROOT"
git init -q "$GE_TPL_ROOT"
git -C "$GE_TPL_ROOT" remote add origin "${CONFIG.TEMPLATE_REPO}"
git -C "$GE_TPL_ROOT" sparse-checkout set --cone "${CONFIG.TEMPLATE_SUBDIR}" 2>/dev/null || true
if ! git -C "$GE_TPL_ROOT" fetch -q --depth 1 --filter=blob:none origin "${templateRef}"; then
  echo "❌ Could not fetch agent template ref '${templateRef}'"
  echo "   from ${CONFIG.TEMPLATE_REPO}."
  echo "   The pinned template version is unreachable. Ask the demo creator to"
  echo "   regenerate this script (the app's TEMPLATE_REF may need updating)."
  exit 1
fi
git -C "$GE_TPL_ROOT" -c advice.detachedHead=false checkout -q FETCH_HEAD
GE_TPL="$GE_TPL_ROOT/${CONFIG.TEMPLATE_SUBDIR}"
if [ ! -f "$GE_TPL/adk_agent/app/fast_api_app.py" ]; then
  echo "❌ Agent template incomplete under $GE_TPL"
  exit 1
fi
echo "    ✅ Agent template ready."
${ enableManagedAgent ? `
# --- Managed Autonomous Agent (Antigravity, Pre-GA Preview) - PHASE A: start ---
# Creation takes ~8-10 min, so it is STARTED here (right after the dashboards
# bucket exists) and awaited in PHASE B after the Cloud Run deployment +
# Gemini Enterprise registration, hiding most of the wait behind the rest of
# the setup. No allowlist is needed - just the Vertex AI Agent Platform API + standard IAM.
# VERIFIED live (2026-07-12): the create LRO never reports done:true, so
# readiness is detected in PHASE B by polling GET on the agent itself.
echo "🤖 Starting Managed Autonomous Agent provisioning (Antigravity, Preview)..."
MANAGED_AGENT_ID=""
# PHASE A runs BEFORE the demo asset directory is created/entered, while
# PHASE B runs inside it - so all helper files are addressed absolutely.
MA_TOOLS_DIR="$(pwd)"

# 1) Craft skills: self-authored packs (embedded at generation time from the
#    generator repo) + the Google Chrome modern-web-guidance skill (public,
#    Apache-2.0/CC-BY, cloned fresh at setup time).
rm -rf skills _mwg_tmp && mkdir -p skills
${managedSkillsBash}if git clone --depth 1 --quiet https://github.com/GoogleChrome/modern-web-guidance.git _mwg_tmp >/dev/null 2>&1; then
  rm -rf _mwg_tmp/.git
  # Publish-repo layout (verified 2026-07-12): skill packs live under skills/
  # (skills/modern-web-guidance/SKILL.md). Fallbacks cover a root-level
  # SKILL.md or first-level skill dirs in case the layout changes.
  MA_MWG_COPIED=""
  if [ -f _mwg_tmp/skills/modern-web-guidance/SKILL.md ]; then
    cp -r _mwg_tmp/skills/modern-web-guidance skills/
    MA_MWG_COPIED="yes"
  elif [ -f _mwg_tmp/SKILL.md ]; then
    mkdir -p skills/modern-web-guidance
    cp -r _mwg_tmp/. skills/modern-web-guidance/
    MA_MWG_COPIED="yes"
  else
    for d in _mwg_tmp/*/ _mwg_tmp/skills/*/; do
      if [ -f "\${d}SKILL.md" ]; then cp -r "$d" skills/; MA_MWG_COPIED="yes"; fi
    done
  fi
  rm -rf _mwg_tmp
  if [ -n "$MA_MWG_COPIED" ]; then
    echo "  ✅ modern-web-guidance skill added (GoogleChrome, latest)."
  else
    echo "  ⚠️  modern-web-guidance layout not recognized (continuing without it)."
  fi
else
  echo "  ⚠️  Could not clone modern-web-guidance (continuing without it)."
fi
${ workspaceAuthEnabled ? `
# gws (Google Workspace CLI, Apache-2.0) skills: let the sandbox act on the
# user's Workspace via direct REST with the user OAuth token (no MCP servers).
# Curated subset only - the full 100+ skill set would drown skill discovery.
rm -rf _gws_tmp
if git clone --depth 1 --quiet https://github.com/googleworkspace/cli.git _gws_tmp >/dev/null 2>&1; then
  MA_GWS_COPIED=""
  for s in gws-shared gws-drive gws-gmail gws-calendar gws-chat gws-docs gws-sheets; do
    if [ -f "_gws_tmp/skills/\$s/SKILL.md" ]; then
      cp -r "_gws_tmp/skills/\$s" skills/
      MA_GWS_COPIED="yes"
    fi
  done
  rm -rf _gws_tmp
  if [ -n "$MA_GWS_COPIED" ]; then
    echo "  ✅ gws Workspace CLI skills added (googleworkspace/cli, latest)."
  else
    echo "  ⚠️  gws skills layout not recognized (continuing without Workspace actions)."
  fi
else
  echo "  ⚠️  Could not clone googleworkspace/cli (continuing without Workspace actions)."
fi
` : ''}

MA_SKILLS_SOURCE=""
if [ -n "$(ls -A skills 2>/dev/null)" ]; then
  echo "  📤 Uploading skill packs to gs://$DASH_BUCKET/skills/ ..."
  if gcloud storage cp -r skills/* "gs://$DASH_BUCKET/skills/" >/dev/null 2>&1; then
    MA_SKILLS_SOURCE="gs://$DASH_BUCKET/skills"
    echo "  ✅ Skills uploaded ($(find skills -name 'SKILL.md' | wc -l) skill packs)."
  else
    echo "  ⚠️  Skill upload failed (agent will run without mounted skills)."
  fi
else
  echo "  ⚠️  No skill packs available (agent will run without mounted skills)."
fi
rm -rf skills

# 2) System instruction (quoted heredoc -> file; avoids argv-length limits).
cat <<'__MA_SYSINSTR_EOF__' > managed_agent_instruction.txt
${managedAgentInstruction}
__MA_SYSINSTR_EOF__

# 3) Provisioning helper (raw REST via stdlib urllib). Two modes:
#    start = fire the create (or update an existing agent in place) and
#            return immediately; wait = poll GET until the agent is ready.
cp "$GE_TPL/managed_agent/create_managed_agent.py" create_managed_agent.py

# 4) Warm-up helper (used in PHASE B): one trivial interaction pre-provisions
#    the sandbox container; the resulting environment id is stored in the
#    demo's Firestore state doc, where the runtime reads it (so it does not
#    need to exist before the Cloud Run deployment).
cp "$GE_TPL/managed_agent/warmup_managed_agent.py" warmup_managed_agent.py

MA_TOKEN=$(gcloud auth print-access-token)
export MA_OUT="/tmp/ma_start_$$.txt"
PROJECT_ID="$PROJECT_ID" python3 "$MA_TOOLS_DIR/create_managed_agent.py" start "${managedAgentId}" "$MA_TOKEN" "$MA_SKILLS_SOURCE" 2>&1 | sed 's/^/  /'
MA_START_STATE=$(cat "$MA_OUT" 2>/dev/null)
rm -f "$MA_OUT"
unset MA_OUT
if [ -n "$MA_START_STATE" ]; then
  # Optimistic: the id is deterministic and the Cloud Run env var is set now;
  # PHASE B verifies readiness and clears the env var if provisioning failed.
  MANAGED_AGENT_ID="${managedAgentId}"
  echo "  ✅ Provisioning started ($MA_START_STATE) - continuing setup in parallel."
else
  echo "  ⚠️  Managed Agent could not be started - the demo deploys WITHOUT autonomous delegation."
fi
` : ''}
# Enable MCP services (parallel for speed)
echo "🔧 Enabling MCP services (parallel)..."
gcloud beta services mcp enable bigquery.googleapis.com --project="$PROJECT_ID" 2>/dev/null &
gcloud beta services mcp enable mapstools.googleapis.com --project="$PROJECT_ID" 2>/dev/null &
gcloud beta services mcp enable firestore.googleapis.com --project="$PROJECT_ID" 2>/dev/null &
gcloud beta services mcp enable dataplex.googleapis.com --project="$PROJECT_ID" 2>/dev/null &
gcloud services enable aiplatform.googleapis.com --project="$PROJECT_ID" 2>/dev/null &
gcloud services enable cloudscheduler.googleapis.com --project="$PROJECT_ID" 2>/dev/null &
gcloud services enable pubsub.googleapis.com --project="$PROJECT_ID" 2>/dev/null &
wait
echo "  ✅ MCP services enabled"
${mcpServicesToEnable}

# --- 2.2 User-level IAM Configuration ---
  echo "🔐 Configuring user permissions..."
  USER_ACCOUNT=$(gcloud config get-value account 2>/dev/null)
  grant_roles_fast "$PROJECT_ID" "user" "\$USER_ACCOUNT" \
    "roles/mcp.toolUser" "roles/serviceusage.serviceUsageConsumer" "roles/storage.admin" \
    "roles/datastore.user" "roles/iam.serviceAccountUser" "roles/bigquery.jobUser" "roles/bigquery.dataEditor"

# Check for BQ permissions (with timeout to prevent hanging on new projects)
echo "🛡 Checking BigQuery permissions..."
CAN_MK_BQ=$(timeout 30 bq ls --project_id="$PROJECT_ID" 2>&1 || echo "timeout_or_error")
if [[ $CAN_MK_BQ == *"Access Denied"* ]]; then
  echo "❌ Error: Your account doesn't have BigQuery access in this project."
  exit 1
fi
echo "✅ BigQuery Permissions OK"


# --- 4. Project Setup (Flat Structure) ---
if [ -d "${dirName}" ]; then
  echo "📂 Removing existing directory ${dirName} for a clean setup..."
  rm -rf "${dirName}"
fi
# --- 3. Data Provisioning ---
${bqCommands}
${firestoreCommands}

echo "📦 Setting up project directory..."
mkdir -p ${dirName}/adk_agent/app
cd ${dirName}

# Generate requirements.txt
cat <<'__REQ_EOF__' > requirements.txt
${PINNED_DEPS.adk}
${PINNED_DEPS.mcp}
${PINNED_DEPS.genai}
${PINNED_DEPS.dotenv}
${PINNED_DEPS.aiplatform}
${PINNED_DEPS.dbDtypes}
${PINNED_DEPS.storage}
${PINNED_DEPS.a2ui}
${PINNED_DEPS.a2a}
${PINNED_DEPS.scheduler}
${PINNED_DEPS.pubsub}
${PINNED_DEPS.firestore}
${PINNED_DEPS.logging}
${PINNED_DEPS.otel}
${ enableComputerUse ? `${PINNED_DEPS.playwright}\n${PINNED_DEPS.genaiComputerUse}` : '' }
__REQ_EOF__

# Generate pyproject.toml required for adk project type
cp "$GE_TPL/pyproject.toml" pyproject.toml

# Generate .dockerignore to prevent copying local .venv
cp "$GE_TPL/.dockerignore" .dockerignore

# Generate .python-version for Buildpacks
cp "$GE_TPL/python-version.txt" .python-version

# Generate Dockerfile using uv for performance (PoC v9 style)
cat <<'__DOCKER_EOF__' > Dockerfile
FROM ${PINNED_DEPS.pythonImage}
COPY --from=${PINNED_DEPS.uvImage} /uv /uvx /bin/
RUN apt-get update && apt-get install -y git && rm -rf /var/lib/apt/lists/*
WORKDIR /app
COPY requirements.txt pyproject.toml ./
RUN uv pip install --system -r requirements.txt
__DOCKER_EOF__

${ enableComputerUse ? `
# -- Computer Use: install Chromium + OS libs for headless Playwright browsing --
cat <<'__DOCKER_CU_EOF__' >> Dockerfile
RUN playwright install --with-deps chromium
ENV PLAYWRIGHT_HEADLESS=1
__DOCKER_CU_EOF__
` : '' }

${ (params.importedMcpList && params.importedMcpList.filter(m => m.type !== 'remote').length > 0) ? `
# ── Custom MCP servers: language-aware Dockerfile layers ──
cat <<'__DOCKER_MCP_EOF__' >> Dockerfile
# Install Node.js (required for supergateway stdio→HTTP bridge and Node.js MCP servers)
RUN apt-get update && apt-get install -y curl && \
    curl -fsSL https://deb.nodesource.com/setup_20.x | bash - && \
    apt-get install -y nodejs && \
    rm -rf /var/lib/apt/lists/*
# Pre-install supergateway globally (stdio→StreamableHTTP bridge, works with any language)
RUN npm install -g ${PINNED_DEPS.supergateway}
__DOCKER_MCP_EOF__

${(() => {
  let dockerSteps = '';
  // --- Docker build layers for custom MCP servers ---
  params.importedMcpList.filter(m => m.type !== 'remote').forEach((mcp, idx) => {
    const mcpDir = `/app/custom_mcp_${idx}`;
    const lang = (mcp.language || '').toLowerCase();
    const isNodejs = (lang === 'nodejs');
    dockerSteps += `
cat <<'__DOCKER_MCP_CLONE_${idx}_EOF__' >> Dockerfile
RUN git clone ${mcp.github_url} ${mcpDir}
__DOCKER_MCP_CLONE_${idx}_EOF__
`;
    let installStep;
    const pipCmd = `(if [ -f pyproject.toml ] || [ -f setup.py ]; then uv pip install --system . 2>/dev/null || true; elif [ -f requirements.txt ]; then uv pip install --system -r requirements.txt; fi)`;
    const npmCmd = `(npm install && npm run build 2>/dev/null || true)`;
    const ign = mcp.npm_ignore_scripts ? 'ENV NPM_CONFIG_IGNORE_SCRIPTS=true\n' : '';
    if (isNodejs) {
      // Primary: Node.js install. Fallback: Python install if npm fails.
      installStep = `${ign}RUN cd ${mcpDir} && ${npmCmd} && ${pipCmd}`;
    } else {
      // Primary: Python install. Fallback: Node.js install if pip fails.
      installStep = `RUN cd ${mcpDir} && ${pipCmd} || ${npmCmd}`;
    }
    dockerSteps += `
cat <<'__DOCKER_MCP_INSTALL_${idx}_EOF__' >> Dockerfile
${installStep}
__DOCKER_MCP_INSTALL_${idx}_EOF__
`;
  });

  // --- Parallel sidecar startup strategy ---
  // Phase 1: Launch ALL sidecars as background processes (no waiting)
  // Phase 2: Single unified health-check loop polls all ports concurrently
  // Result: Total startup = max(individual) ~15-30s instead of sum ~270s
  const localMcps = params.importedMcpList.filter(m => m.type !== 'remote');
  let startScript = '#!/bin/bash\n\n';
  startScript += `TOTAL_SIDECARS=${localMcps.length}\n`;
  startScript += 'echo "🔌 Starting $TOTAL_SIDECARS MCP sidecars in parallel..."\n\n';

  // Phase 1: Generate launcher scripts for FastMCP servers, then launch all sidecars
  // CRITICAL: We generate _run.py files instead of python -c "..." because
  // bash double-quotes do NOT interpret \n as newlines, causing SyntaxError.
  startScript += '# Phase 1: Launch all sidecars in parallel\n';
  localMcps.forEach((mcp, idx) => {
    const ep = mcp.entrypoint || '';
    const isFastMcp = ep.includes(':') && !ep.includes(' ');
    const mcpDir = `/app/custom_mcp_${idx}`;
    const port = 9090 + idx;
    let stdioCmd;
    if (isFastMcp) {
      const [mp, on] = ep.split(':');
      // Generate _run.py locally in build context, then COPY into Docker image.
      // Previous printf approach broke: multi-layer escaping turned newlines into literal chars.
      dockerSteps += `
cat <<'__RUN_PY_${idx}_EOF__' > _run_${idx}.py
import asyncio
import sys
import logging
logging.basicConfig(level=logging.INFO, stream=sys.stderr)
from ${mp} import ${on}
try:
    ${on}.run(transport="stdio")
except TypeError:
    from mcp.server.stdio import stdio_server
    async def _r():
        async with stdio_server() as (r, w):
            await ${on}.run(r, w, ${on}.create_initialization_options())
    asyncio.run(_r())
__RUN_PY_${idx}_EOF__

cat <<'__DOCKER_COPY_RUN_PY_${idx}_EOF__' >> Dockerfile
COPY _run_${idx}.py ${mcpDir}/_run.py
__DOCKER_COPY_RUN_PY_${idx}_EOF__
`;
      stdioCmd = `python _run.py`;
    } else { stdioCmd = ep; }
    startScript += `cd ${mcpDir} && supergateway --stdio "${stdioCmd}" --outputTransport streamableHttp --port ${port} --sessionStateless &\n`;
    startScript += `PID_${idx}=$!\n`;
  });

  // Phase 2: Build port list and do a single batch health-check
  const portList = localMcps.map((_, idx) => 9090 + idx).join(' ');
  startScript += '\n# Phase 2: Unified health-check (max 30s for ALL sidecars)\n';
  startScript += `PORTS="${portList}"\n`;
  startScript += 'READY=""\n';
  startScript += 'for _attempt in $(seq 1 30); do\n';
  startScript += '  ALL_READY=true\n';
  startScript += '  for P in $PORTS; do\n';
  startScript += '    case " $READY " in *" $P "*) continue ;; esac\n';
  startScript += '    if curl -s -m 2 -o /dev/null -w \"\" http://127.0.0.1:$P/mcp 2>/dev/null; then\n';
  startScript += '      echo "  ✅ Port $P ready (${_attempt}s)"\n';
  startScript += '      READY="$READY $P"\n';
  startScript += '    else\n';
  startScript += '      ALL_READY=false\n';
  startScript += '    fi\n';
  startScript += '  done\n';
  startScript += '  if $ALL_READY; then break; fi\n';
  startScript += '  sleep 1\n';
  startScript += 'done\n';
  startScript += '\n# Report results\n';
  startScript += 'READY_COUNT=$(echo $READY | wc -w | tr -d " ")\n';
  startScript += 'echo "✅ $READY_COUNT/$TOTAL_SIDECARS MCP sidecars ready"\n';
  startScript += 'for P in $PORTS; do\n';
  startScript += '  case " $READY " in *" $P "*) ;; *) echo "  ⚠️ Port $P did not become ready in time" ;; esac\n';
  startScript += 'done\n';
  startScript += '\necho "🚀 Starting ADK agent..."\n';
  startScript += 'cd /app\n';
  startScript += 'exec uvicorn adk_agent.app.fast_api_app:app --host 0.0.0.0 --port 8080\n';

  return dockerSteps + `
cat <<'__START_SH_EOF__' > start_mcp.sh
${startScript}__START_SH_EOF__
chmod +x start_mcp.sh
cat <<'__DOCKER_START_EOF__' >> Dockerfile
COPY start_mcp.sh /app/start_mcp.sh
__DOCKER_START_EOF__`;
})()}
` : '' }

cat <<'__DOCKER_TAIL_EOF__' >> Dockerfile
COPY . .
# Dependency smoke test: fail build if critical interface missing
RUN python -c "from a2ui.a2a.parts import create_a2ui_part; import inspect; assert 'version' in inspect.signature(create_a2ui_part).parameters, 'FAIL: a2ui version param missing'; print('Dep smoke test OK')"
# Record installed versions for debugging
RUN uv pip freeze | grep -iE "^(google-adk|a2ui|mcp|google-genai|a2a-sdk)" | tee /app/.dep-versions
ENV PORT 8080
ENV GOOGLE_GENAI_USE_VERTEXAI=1
ENV PYTHONUNBUFFERED=1
ENV ADK_ENABLE_MCP_GRACEFUL_ERROR_HANDLING=1
# ADK 2.x: JSON_SCHEMA_FOR_FUNC_DECL (default ON) sends raw MCP JSON Schemas
# via parameters_json_schema, bypassing _to_gemini_schema and the
# _safe_dereference_schema patch. Recursive custom-MCP schemas (e.g. LINE
# flex messages) then hit Vertex's server-side flattener limit: deterministic
# 500 "Limits exceeded while trying to flatten schema" on EVERY call.
# Disabling restores the sanitized legacy conversion path.
ENV ADK_DISABLE_JSON_SCHEMA_FOR_FUNC_DECL=1
ENV OTEL_SDK_DISABLED=true
__DOCKER_TAIL_EOF__
${ (params.importedMcpList && params.importedMcpList.filter(m => m.type !== 'remote').length > 0) ? `echo 'CMD ["/bin/bash", "/app/start_mcp.sh"]' >> Dockerfile` : `echo 'CMD ["uvicorn", "adk_agent.app.fast_api_app:app", "--host", "0.0.0.0", "--port", "8080"]' >> Dockerfile` }

# --- 5. Environment Setup ---
if ! command -v uv >/dev/null 2>&1; then
    echo "    installing uv via astral.sh..."
    curl -LsSf https://astral.sh/uv/${PINNED_DEPS.uvVersion}/install.sh | sh >/dev/null 2>&1 || true
    # Add to current PATH for the rest of the script
    export PATH="\$HOME/.cargo/bin:\$PATH"
fi
# Set UV to copy mode to prevent cross-filesystem hardlink failures (os error 28)
export UV_LINK_MODE=copy

echo "📦 Dependencies will be installed in Docker build..."

# --- 6. Generate Maps API Key ---
echo "🔑 Generating Maps API key..."
API_KEY_JSON=$(gcloud alpha services api-keys create --display-name="MCP-Demo-Key-${suffix}" \
    --api-target=service=mapstools.googleapis.com \
    --format=json 2>/dev/null || echo "")

if [ ! -z "$API_KEY_JSON" ]; then
    API_KEY=$(echo "$API_KEY_JSON" | grep -oP '"keyString": "\K[^"]+' 2>/dev/null || echo "$API_KEY_JSON" | grep '"keyString":' | cut -d '"' -f 4)
else
    API_KEY=$(gcloud alpha services api-keys list --filter="displayName:MCP-Demo-Key-${suffix}" --format="value(keyString)" 2>/dev/null || echo "")
fi

if [ -z "$API_KEY" ]; then
    echo "⚠️ Failed to auto-generate API key. Set it manually in .env."
    API_KEY="REPLACE_ME"
fi

# --- Store Maps API key in Secret Manager for Cloud Run (--update-secrets) ---
# The deployed service reads MAPS_API_KEY from this secret instead of a plaintext
# --set-env-vars value, so the key is not exposed in the service config. The local
# .env keeps the plaintext value (local runs read os.getenv directly). Named with
# the demo dirName so the --cleanup suffix grep removes it automatically.
echo "🔐 Storing Maps API key in Secret Manager: ${dirName}-maps-key..."
if gcloud secrets describe ${dirName}-maps-key >/dev/null 2>&1; then
    echo -n "$API_KEY" | gcloud secrets versions add ${dirName}-maps-key --data-file=-
else
    echo -n "$API_KEY" | gcloud secrets create ${dirName}-maps-key --data-file=- --replication-policy="automatic"
fi

# --- Sandbox Provisioning for Code Execution ---
echo "🧪 Provisioning Agent Sandbox for Code Execution..."
export SANDBOX_OUT="/tmp/sandbox_result_$$.txt"
# CRITICAL: Run from a clean temp directory, NOT the project directory.
# agent_engines.create(config=...) packages the CWD for container build.
# If Dockerfile/MCP files exist in CWD, the SDK tries to build them → hang.
SANDBOX_TMPDIR=$(mktemp -d)
pushd "$SANDBOX_TMPDIR" > /dev/null
GOOGLE_API_USE_CLIENT_CERTIFICATE=false uv run --no-project --with "google-cloud-aiplatform[agent_engines]>=1.112.0" python3 << '__SANDBOX_PROVISION_EOF__'
import sys, os, warnings, time, vertexai
from vertexai import types

# Suppress harmless "STATE_RUNNING is not a valid State" warning from google-genai SDK
warnings.filterwarnings('ignore', message='STATE_RUNNING is not a valid', category=UserWarning, module='google.genai')

_MAX_RETRIES = 5

print('  📦 Step 1/3: Initializing Vertex AI Agent Platform client (us-central1)...')
sys.stdout.flush()
client = vertexai.Client(project=os.environ.get('PROJECT_ID', ''), location='us-central1')

print('  📦 Step 2/3: Creating Agent Engine...')
sys.stdout.flush()
agent_engine = None
for _attempt in range(_MAX_RETRIES):
    try:
        agent_engine = client.agent_engines.create(
            config={'display_name': '${dirName}-sandbox'},
        )
        break
    except Exception as _e:
        if _attempt < _MAX_RETRIES - 1:
            _wait = 15 * (_attempt + 1)
            print('  ⚠️  Attempt ' + str(_attempt + 1) + '/' + str(_MAX_RETRIES) + ' failed: ' + str(_e)[:200])
            print('  ⏳ Retrying in ' + str(_wait) + 's...')
            sys.stdout.flush()
            time.sleep(_wait)
        else:
            raise
agent_engine_name = agent_engine.api_resource.name
print('  ✅ Agent Engine: ' + agent_engine_name)
sys.stdout.flush()

print('  📦 Step 3/3: Creating Sandbox (this may take a few minutes)...')
sys.stdout.flush()
sandbox_operation = None
for _attempt in range(_MAX_RETRIES):
    try:
        sandbox_operation = client.agent_engines.sandboxes.create(
            name=agent_engine_name,
            config=types.CreateAgentEngineSandboxConfig(display_name='code-sandbox'),
            spec={'code_execution_environment': {}},
        )
        break
    except Exception as _e:
        if _attempt < _MAX_RETRIES - 1:
            _wait = 15 * (_attempt + 1)
            print('  ⚠️  Attempt ' + str(_attempt + 1) + '/' + str(_MAX_RETRIES) + ' failed: ' + str(_e)[:200])
            print('  ⏳ Retrying in ' + str(_wait) + 's...')
            sys.stdout.flush()
            time.sleep(_wait)
        else:
            raise
sandbox_resource_name = sandbox_operation.response.name
print('  ✅ Sandbox: ' + sandbox_resource_name)

with open(os.environ.get('SANDBOX_OUT', '/tmp/sandbox_result.txt'), 'w') as f:
    f.write(agent_engine_name + '|' + sandbox_resource_name)
__SANDBOX_PROVISION_EOF__
popd > /dev/null
rm -rf "$SANDBOX_TMPDIR"

if [ -f "$SANDBOX_OUT" ]; then
    SANDBOX_RESULT=$(cat "$SANDBOX_OUT")
    rm -f "$SANDBOX_OUT"
    AGENT_ENGINE_NAME=$(echo "$SANDBOX_RESULT" | cut -d'|' -f1)
    SANDBOX_RESOURCE_NAME=$(echo "$SANDBOX_RESULT" | cut -d'|' -f2)
else
    echo "  ❌ Sandbox provisioning failed. See error output above."
    echo "     Ensure aiplatform.googleapis.com is enabled and roles/aiplatform.user is granted."
    exit 1
fi
# Create .env in the root
cat <<__ENV_EOF__ > .env
GOOGLE_GENAI_USE_VERTEXAI=1
GOOGLE_CLOUD_PROJECT="$PROJECT_ID"
GOOGLE_API_USE_CLIENT_CERTIFICATE=false
GOOGLE_CLOUD_LOCATION="global"
DEMO_DATASET="${datasetId}"
FS_COLLECTION="${fsCollection}"
REFERENCE_DATE="${referenceDate}"
PUBLIC_DATASET_ID="${publicDatasetId || ''}"
ENABLE_WORKSPACE_MCP=${enableWorkspaceMcp ? '1' : '0'}
ENABLE_COMPUTER_USE=${enableComputerUse ? '1' : '0'}
ENABLE_MANAGED_AGENT=${enableManagedAgent ? '1' : '0'}
ENABLE_WORKSPACE_AUTH=${enableWorkspaceAuth ? '1' : '0'}
MAPS_API_KEY="$API_KEY"
PYTHONUNBUFFERED=1
GRPC_ENABLE_FORK_SUPPORT=1
ADK_ENABLE_MCP_GRACEFUL_ERROR_HANDLING=1
ADK_DISABLE_JSON_SCHEMA_FOR_FUNC_DECL=1
AGENT_MODEL="$AGENT_MODEL"
AGENT_MODEL_LITE="$AGENT_MODEL_LITE"
DASHBOARDS_BUCKET="$DASH_BUCKET"
RUNTIME_SA_EMAIL="$COMPUTE_SA"
__ENV_EOF__

# Conditionally add Data Viewer URL if deployed
if [ "$VIEWER_DEPLOYED" = "true" ]; then
  echo "DATA_VIEWER_URL=\"$VIEWER_URL\"" >> .env
fi

# Add Sandbox resource name for code execution (always present at this point)
echo "SANDBOX_RESOURCE_NAME=\"$SANDBOX_RESOURCE_NAME\"" >> .env
echo "AGENT_ENGINE_NAME=\"$AGENT_ENGINE_NAME\"" >> .env
${ enableManagedAgent ? `
# Managed Autonomous Agent id (optimistic - creation started in PHASE A and
# is verified in PHASE B after deployment; empty when the start was rejected).
# The skills source is needed at RUNTIME because the Interactions API does not
# inherit the agent's base_environment: every fresh sandbox spec must restate
# network + sources (verified live 2026-07-12).
echo "MANAGED_AGENT_ID=\"$MANAGED_AGENT_ID\"" >> .env
echo "MANAGED_AGENT_SKILLS_SOURCE=\"$MA_SKILLS_SOURCE\"" >> .env
` : ''}

# Symlink .env to packages for visibility
ln -sf ../.env adk_agent/.env
ln -sf ../../.env adk_agent/app/.env

# Ignore large directories to prevent Reason Engine payload bloating
cp "$GE_TPL/adk_agent/.gitignore" adk_agent/.gitignore

# Create __init__.py files for proper Python package structure
touch adk_agent/__init__.py
cp "$GE_TPL/adk_agent/app/__init__.py" adk_agent/app/__init__.py


# --- 7. Customizing Agent ---
echo "🔧 Configuring agent..."



cp "$GE_TPL/adk_agent/app/tools.py" adk_agent/app/tools.py

mkdir -p adk_agent/app/examples/0.8
# --- A2UI example JSONs (copied from the pinned agent template) ---
cp "$GE_TPL"/adk_agent/app/examples/0.8/*.json adk_agent/app/examples/0.8/
GE_CURRENCY='${bashEscape(currencySymbol)}' python3 - <<'__GE_CURR_SUB_EOF__'
import glob, os
sym = os.environ.get("GE_CURRENCY") or "$"
for p in glob.glob("adk_agent/app/examples/0.8/*.json"):
    s = open(p, encoding="utf-8").read()
    if "[CURRENCY]" in s:
        open(p, "w", encoding="utf-8").write(s.replace("[CURRENCY]", sym))
__GE_CURR_SUB_EOF__

cp "$GE_TPL/adk_agent/app/agent.py" adk_agent/app/agent.py

# --- Per-demo agent configuration (consumed by the static agent template) ---
cat <<'__GE_INSTRUCTION_EOF__' > adk_agent/app/generated_instruction.md
${rawInstruction}
__GE_INSTRUCTION_EOF__

cat <<'__GE_MCP_CONFIG_EOF__' > adk_agent/app/mcp_config.json
${geMcpConfigJson}
__GE_MCP_CONFIG_EOF__

cp "$GE_TPL/adk_agent/app/part_converters.py" adk_agent/app/part_converters.py


# --- 8. Cloud Run & Gemini Enterprise Infrastructure ---
  echo ""
  echo "🔧 Initializing Cloud Run infrastructure..."
  cd adk_agent

  # Overwrite fast_api_app.py to use custom executor
  cp "$GE_TPL/adk_agent/app/fast_api_app.py" app/fast_api_app.py
  perl -pi -e "s/tmp-ref-run/${dirName}/g" app/fast_api_app.py 2>/dev/null || true

  cd ..

# --- 9. Final Launch & Tips ---


  echo ""
  echo "========================================================="
  echo "🚀 DEPLOYING TO GEMINI ENTERPRISE"
  echo "========================================================="
  
  echo "🤖 Step 1/2: Deploying Main Agent to Cloud Run..."
  cd adk_agent
  
  
  ${ (() => {
    if (!params.importedMcpList || params.importedMcpList.length === 0) return "";
    
    let script = `
# Enable Secret Manager API
echo "Enabling Secret Manager API..."
gcloud services enable secretmanager.googleapis.com
`;

    params.importedMcpList.forEach((mcp, mcpIdx) => {
      // -- Remote Managed MCP (Slack): token already in Secret Manager from provisioning --
      if (mcp.type === 'remote' && mcp.auth_type === 'oauth2_slack') {
        // Slack token stored in Secret Manager during provisioning step
        return;
      }
      // ── Sidecar MCP ──
      const githubUrl = mcp.github_url;
      let repoName = "mcp-server";
      if (githubUrl) {
        const parts = githubUrl.split("/");
        let lastPart = parts[parts.length - 1] || parts[parts.length - 2];
        repoName = lastPart.replace(/\.git$/, "").toLowerCase().replace(/[^a-z0-9-]/g, "-");
      }
      const serviceName = `${dirName}-mcp-${repoName}`;
      // Only show "Provisioning Secrets" message if this MCP actually has secret env vars
      const hasSecrets = mcp.required_env_vars && mcp.required_env_vars.some(v => v.is_secret);
      if (!hasSecrets) return;
      script += `\necho "🔑 Provisioning Secrets for MCP #${mcpIdx + 1} (${repoName})..."\n`;

      mcp.required_env_vars.forEach(v => {
      const rawKey = v.key.toLowerCase().replace(/_/g, "-");
      let secretName = `${serviceName}-${rawKey}`;
      // Uniquify words
      secretName = secretName.split("-").filter((word, pos, arr) => arr.indexOf(word) === pos).join("-");

      if (v.is_secret && v.is_required) {
        // Required secrets: fallback to "UNDEFINED" if not provided
        script += `if [ -z "\$${v.key}" ]; then\n  ${v.key}="UNDEFINED"\nfi\n`;
        script += `if gcloud secrets describe ${secretName} >/dev/null 2>&1; then\n`;
        script += `  echo -n "\$${v.key}" | gcloud secrets versions add ${secretName} --data-file=-\n`;
        script += `else\n`;
        script += `  echo -n "\$${v.key}" | gcloud secrets create ${secretName} --data-file=- --replication-policy="automatic"\n`;
        script += `fi\n`;
      } else if (v.is_secret && !v.is_required) {
        // Optional secrets: only create if user provided a value
        script += `if [ -n "\$${v.key}" ]; then\n`;
        script += `  if gcloud secrets describe ${secretName} >/dev/null 2>&1; then\n`;
        script += `    echo -n "\$${v.key}" | gcloud secrets versions add ${secretName} --data-file=-\n`;
        script += `  else\n`;
        script += `    echo -n "\$${v.key}" | gcloud secrets create ${secretName} --data-file=- --replication-policy="automatic"\n`;
        script += `  fi\n`;
        script += `else\n`;
        script += `  echo "  ⏭️  Skipping optional secret: ${v.key}"\n`;
        script += `fi\n`;
      }
      });
    });
    return script;
  })() }

  # Grant Secret Manager access to default Compute Engine SA (required for --update-secrets)
  COMPUTE_NUM=$(gcloud projects describe "$PROJECT_ID" --format='value(projectNumber)')
  COMPUTE_SA="\${COMPUTE_NUM}-compute@developer.gserviceaccount.com"
  echo "🔐 Granting Secret Accessor role to Cloud Run service account..."
  gcloud projects add-iam-policy-binding "$PROJECT_ID" \\
    --member="serviceAccount:$COMPUTE_SA" \\
    --role="roles/secretmanager.secretAccessor" \\
    --condition=None --quiet >/dev/null 2>&1 || true

  SERVICE_NAME="${dirName}"

  # --- Pre-create Pub/Sub topics in background (no dependency on SERVICE_URL) ---
  SCHED_TOPIC="${dirName}-sched-tasks"
  RESULT_TOPIC="${dirName}-task-results"
  echo "📨 Pre-creating Pub/Sub topics (parallel with deploy)..."
  gcloud pubsub topics create "$SCHED_TOPIC" --project="$PROJECT_ID" 2>/dev/null &
  gcloud pubsub topics create "$RESULT_TOPIC" --project="$PROJECT_ID" 2>/dev/null &

  DEPLOY_LOG=$(mktemp /tmp/deploy-XXXXXX.log)
  trap "rm -f \$DEPLOY_LOG" EXIT
  echo "🤖 Deploying Main Agent to Cloud Run via Source..."
  
  ${ (() => {
    let envVars = [
      "GOOGLE_CLOUD_PROJECT=\$PROJECT_ID",
      "GOOGLE_CLOUD_LOCATION=global",
      "GEMINI_AUTHORIZATION_ID=\$AUTH_ID",
      "ADK_ENABLE_MCP_GRACEFUL_ERROR_HANDLING=1",
      "ADK_DISABLE_JSON_SCHEMA_FOR_FUNC_DECL=1",
      `DEMO_ID=${dirName}`,
      `DEMO_DATASET=${datasetId}`,
      `FS_COLLECTION=${fsCollection}`,
      `REFERENCE_DATE=${referenceDate}`,
      `PUBLIC_DATASET_ID=${publicDatasetId || ''}`,
      `ENABLE_WORKSPACE_MCP=${enableWorkspaceMcp ? '1' : '0'}`,
      `ENABLE_COMPUTER_USE=${enableComputerUse ? '1' : '0'}`,
      `ENABLE_MANAGED_AGENT=${enableManagedAgent ? '1' : '0'}`,
      `ENABLE_WORKSPACE_AUTH=${enableWorkspaceAuth ? '1' : '0'}`,
      "DASHBOARDS_BUCKET=\$DASH_BUCKET",
      "RUNTIME_SA_EMAIL=\$COMPUTE_SA"
    ];
    let secrets = [];
    let optionalSecrets = [];

    // Maps API key: bound from Secret Manager (provisioned during setup) instead
    // of a plaintext --set-env-vars value, so it is not exposed in the service config.
    secrets.push(`MAPS_API_KEY=${dirName}-maps-key:latest`);

    if (params.enableWorkspaceMcp) {
      secrets.push(`OAUTH_CLIENT_ID=ge-demo-oauth-client-id:latest`);
      secrets.push(`OAUTH_CLIENT_SECRET=ge-demo-oauth-client-secret:latest`);
    }
    
    if (params.importedMcpList && params.importedMcpList.length > 0) {
      params.importedMcpList.forEach((mcp, mcpIdx) => {
        // ── Remote Managed MCP (Slack) ──
        if (mcp.type === 'remote' && mcp.auth_type === 'oauth2_slack') {
          // Slack MCP: static token from Secret Manager
          secrets.push(`SLACK_ACCESS_TOKEN=${dirName}-slack-token:latest`);
          return;
        }
        // ── Sidecar MCP ──
        const githubUrl = mcp.github_url;
        let repoName = "mcp-server";
        if (githubUrl) {
          const parts = githubUrl.split("/");
          let lastPart = parts[parts.length - 1] || parts[parts.length - 2];
          repoName = lastPart.replace(/\.git$/, "").toLowerCase().replace(/[^a-z0-9-]/g, "-");
        }
        const serviceName = `${dirName}-mcp-${repoName}`;

        mcp.required_env_vars.forEach(v => {
          const rawKey = v.key.toLowerCase().replace(/_/g, "-");
          let secretName = `${serviceName}-${rawKey}`;
          secretName = secretName.split("-").filter((word, pos, arr) => arr.indexOf(word) === pos).join("-");

          if (v.is_secret && v.is_required) {
            // Required secrets: always bind to Cloud Run
            secrets.push(`${v.key}=${secretName}:latest`);
          } else if (v.is_secret && !v.is_required) {
            // Optional secrets: bind only if the secret exists (provisioned above)
            optionalSecrets.push({ key: v.key, secretName: secretName });
          } else {
            envVars.push(`${v.key}=\$${v.key}`);
          }
        });

        // Credential file mount support
        if (mcp.credential_file) {
          const credSuffix = params.importedMcpList.length > 1 ? `-${mcpIdx}` : '';
          envVars.push(`CREDENTIAL_SECRET_NAME_${mcpIdx}=${dirName}-mcp-adc-json${credSuffix}`);
          envVars.push(`CREDENTIAL_ENV_VAR_${mcpIdx}=${mcp.credential_file.env_var_name}`);
        }
      });
    }
    
    let deployCmd = '';

    if (optionalSecrets.length > 0) {
      deployCmd += `\n# Discover provisioned optional secrets\nOPTIONAL_SECRETS=""\n`;
      optionalSecrets.forEach(os => {
        deployCmd += `if gcloud secrets describe ${os.secretName} >/dev/null 2>&1; then\n`;
        deployCmd += `  OPTIONAL_SECRETS="\${OPTIONAL_SECRETS:+\$OPTIONAL_SECRETS,}${os.key}=${os.secretName}:latest"\n`;
        deployCmd += `fi\n`;
      });
      const baseSecrets = secrets.length > 0 ? secrets.join(',') : '';
      deployCmd += `\n# Build final secrets flag\n`;
      if (baseSecrets) {
        deployCmd += `ALL_SECRETS="${baseSecrets}"\n`;
        deployCmd += `if [ -n "\$OPTIONAL_SECRETS" ]; then\n`;
        deployCmd += `  ALL_SECRETS="\$ALL_SECRETS,\$OPTIONAL_SECRETS"\n`;
        deployCmd += `fi\n`;
      } else {
        deployCmd += `ALL_SECRETS="\$OPTIONAL_SECRETS"\n`;
      }
      deployCmd += `\nSECRETS_FLAG=""\nif [ -n "\$ALL_SECRETS" ]; then\n  SECRETS_FLAG="--update-secrets=\$ALL_SECRETS"\nfi\n`;
      deployCmd += `\nCR_ENV_VARS="${envVars.join(",")}"\nif [ "\$VIEWER_DEPLOYED" = "true" ]; then\n  CR_ENV_VARS="\$CR_ENV_VARS,DATA_VIEWER_URL=\$VIEWER_URL"\nfi\nCR_ENV_VARS="\$CR_ENV_VARS,SANDBOX_RESOURCE_NAME=\$SANDBOX_RESOURCE_NAME"\n${enableManagedAgent ? `CR_ENV_VARS="\$CR_ENV_VARS,MANAGED_AGENT_ID=\$MANAGED_AGENT_ID,MANAGED_AGENT_SKILLS_SOURCE=\$MA_SKILLS_SOURCE"\n` : ''}`;
      deployCmd += `\ngcloud run deploy "\$SERVICE_NAME" \
    --source .. \
    --memory "8Gi" \
    --cpu 2 \
    --no-cpu-throttling \
    --cpu-boost \
    --min-instances 0 \
    --timeout 1800 \
    --no-allow-unauthenticated \
    --ingress internal \
    --labels "created-by=adk" \
    --set-env-vars="\$CR_ENV_VARS" \
    \$SECRETS_FLAG \
    --region us-central1 \
    --quiet > "\$DEPLOY_LOG" 2>&1 &`;
    } else {
      deployCmd = `CR_ENV_VARS="${envVars.join(",")}"\nif [ "\$VIEWER_DEPLOYED" = "true" ]; then\n  CR_ENV_VARS="\$CR_ENV_VARS,DATA_VIEWER_URL=\$VIEWER_URL"\nfi\nCR_ENV_VARS="\$CR_ENV_VARS,SANDBOX_RESOURCE_NAME=\$SANDBOX_RESOURCE_NAME"\n${enableManagedAgent ? `CR_ENV_VARS="\$CR_ENV_VARS,MANAGED_AGENT_ID=\$MANAGED_AGENT_ID,MANAGED_AGENT_SKILLS_SOURCE=\$MA_SKILLS_SOURCE"\n` : ''}gcloud run deploy "\$SERVICE_NAME" \
    --source .. \
    --memory "8Gi" \
    --cpu 2 \
    --no-cpu-throttling \
    --cpu-boost \
    --min-instances 0 \
    --timeout 1800 \
    --no-allow-unauthenticated \
    --ingress internal \
    --labels "created-by=adk" \
    --set-env-vars="\$CR_ENV_VARS"`;
      if (secrets.length > 0) {
        deployCmd += ` \\\n    --update-secrets="${secrets.join(",")}"`;
      }
      deployCmd += ` \\\n    --region us-central1 \\\n    --quiet > "\$DEPLOY_LOG" 2>&1 &`;
    }

    return deployCmd;
  })() }
  DEPLOY_PID=$!
  printf "   ⏳ Deploying"
  while kill -0 $DEPLOY_PID 2>/dev/null; do
    printf "."
    sleep 5
  done
  echo ""
  wait $DEPLOY_PID
  DEPLOY_EXIT=$?
  if [ $DEPLOY_EXIT -ne 0 ]; then
    echo "   ❌ Cloud Run deployment failed. Build log:"
    echo "---------------------------------------------------------"
    cat "$DEPLOY_LOG"
    echo "---------------------------------------------------------"
    rm -f "$DEPLOY_LOG"
    exit 1
  fi
  echo "   ✅ Cloud Run deployment succeeded."
  rm -f "$DEPLOY_LOG"
  SERVICE_URL=$(gcloud run services list --filter="metadata.name:$SERVICE_NAME" --format="value(status.url)" | head -n 1)

  # --- Background Task Infrastructure: Pub/Sub subscriptions + SELF_URL (parallel) ---
  echo ""
  echo "📨 Finalizing background task infrastructure..."
  # Wait for topic pre-creation to finish before creating subscriptions
  wait 2>/dev/null || true
  echo "  ✅ Pub/Sub topics ready"

  # Create subscriptions and update SELF_URL in parallel (all depend on SERVICE_URL, but not on each other)
  gcloud pubsub subscriptions create "\${SCHED_TOPIC}-push" \\
    --topic="$SCHED_TOPIC" \\
    --push-endpoint="$SERVICE_URL/execute_task" \\
    --push-auth-service-account="$COMPUTE_SA" \\
    --ack-deadline=600 \\
    --project="$PROJECT_ID" 2>/dev/null &
  # NOTE: Result topic push subscription intentionally NOT created here.
  # The result topic is for downstream consumers (e.g. external notifications),
  # NOT for re-triggering /execute_task (which causes session collision).
  gcloud run services update "$SERVICE_NAME" \\
    --update-env-vars="SELF_URL=$SERVICE_URL" \\
    --region us-central1 \\
    --quiet 2>/dev/null &
  wait || true
  echo "  ✅ Pub/Sub push subscriptions created"
  echo "  ✅ SELF_URL env var set"

  # Project-level IAM binding for Discovery Engine SA is assumed to be active.
  # No resource-level binding needed.
  echo ""
  echo "🤖 Step 2/2: Registering Agent to Gemini Enterprise..."
  # Get a fresh access token — use application-default (cloud-platform scope) first, fallback to user credentials
  TOKEN=$(gcloud auth application-default print-access-token 2>/dev/null || gcloud auth print-access-token)
  APP_COUNT=0
  APP_NAMES=()
  APP_DISPLAY_NAMES=()
  APP_LOCS=()
  
  for LOC in "global" "us" "eu"; do
    if [ "$LOC" = "global" ]; then
      ENDPOINT="discoveryengine.googleapis.com"
    else
      ENDPOINT="$LOC-discoveryengine.googleapis.com"
    fi
    JSON=$(curl -s -H "Authorization: Bearer $TOKEN" -H "X-Goog-User-Project: $PROJECT_ID" \
        "https://$ENDPOINT/v1alpha/projects/$PROJECT_ID/locations/$LOC/collections/default_collection/engines")
    
    # Collect names and displayNames of Gemini Enterprise apps
    APPS_INFO=$(echo "$JSON" | python3 -c '
import sys, json
try:
    data = json.load(sys.stdin)
    engines = [e for e in data.get("engines", []) if e.get("searchEngineConfig", {}).get("requiredSubscriptionTier") == "SUBSCRIPTION_TIER_SEARCH_AND_ASSISTANT"]
    for e in engines:
        print(e["name"] + "|" + e["displayName"])
except Exception as e:
    print(f"Python error: {e}", file=sys.stderr)
')
    
    if [ ! -z "$APPS_INFO" ]; then
      while read -r line; do
        if [ ! -z "$line" ]; then
          NAME=$(echo "$line" | cut -d'|' -f1)
          DISPLAY_NAME=$(echo "$line" | cut -d'|' -f2)
          APP_NAMES+=("$NAME")
          APP_DISPLAY_NAMES+=("$DISPLAY_NAME")
          APP_LOCS+=("$LOC")
          APP_COUNT=$((APP_COUNT + 1))
        fi
      done <<< "$APPS_INFO"
    fi
  done
  
  # Create Python script for registration to avoid bash escaping hell
  cat << 'EOF' > register_agent.py
import sys
import json
import urllib.request
import urllib.error

endpoint_loc = sys.argv[1]
project_id = sys.argv[2]
location = sys.argv[3]
app_id = sys.argv[4]
token = sys.argv[5]
agent_name = sys.argv[6]
agent_url = sys.argv[7]
agent_short_name = sys.argv[8]
one_sentence_summary = sys.argv[9]
auth_id = sys.argv[10] if len(sys.argv) > 10 else ""

endpoint = "discoveryengine.googleapis.com" if endpoint_loc == "global" else f"{endpoint_loc}-discoveryengine.googleapis.com"
url = f"https://{endpoint}/v1alpha/projects/{project_id}/locations/{location}/collections/default_collection/engines/{app_id}/assistants/default_assistant/agents"

headers = {
    "Authorization": f"Bearer {token}",
    "Content-Type": "application/json",
    "X-Goog-User-Project": project_id,
}

data = {
    "name": agent_name,
    "displayName": f"{agent_short_name} ({agent_name})",
    "description": one_sentence_summary,
    "a2aAgentDefinition": {
        "jsonAgentCard": json.dumps({
            "protocolVersion": "1.0",
            "name": agent_name,
            "description": one_sentence_summary,
            "url": agent_url,
            "version": "1.0.0",
            "defaultInputModes": ["text/plain"],
            "defaultOutputModes": ["text/plain", "application/json"],
            "capabilities": {
                "streaming": True,
                "extensions": [
                    {
                        "uri": "https://a2ui.org/a2a-extension/a2ui/v0.8"
                    }
                ]
            },
            "preferredTransport": "JSONRPC",
            "skills": [
                {
                    "id": "general",
                    "name": "General Skill",
                    "description": "Handles general queries",
                    "tags": []
                }
            ]
        })
    }
}

if auth_id:
    if auth_id.startswith("projects/"):
        data["authorizationConfig"] = { "agentAuthorization": auth_id }
    else:
        data["authorizationConfig"] = { "agentAuthorization": f"projects/{project_id}/locations/{location}/authorizations/{auth_id}" }

req = urllib.request.Request(url, data=json.dumps(data).encode("utf-8"), headers=headers)
try:
    with urllib.request.urlopen(req) as response:
        resp_data = json.loads(response.read().decode("utf-8"))
        print("Successfully registered agent:")
        print(json.dumps(resp_data, indent=2))
        agent_name = resp_data.get("name", "")
        agent_id = agent_name.split("/")[-1]
        print(f"AGENT_ID:{agent_id}")



except urllib.error.HTTPError as e:
    print(f"Error registering agent: {e}", file=sys.stderr)
    print(e.read().decode("utf-8"), file=sys.stderr)
    sys.exit(1)
except Exception as e:
    print(f"Unexpected error: {e}", file=sys.stderr)
    sys.exit(1)
EOF

  if [ "$APP_COUNT" = "1" ]; then
    SELECTED_APP_ID=$(echo "\${APP_NAMES[0]}" | awk -F'/' '{print \$NF}')
    SELECTED_LOC="\${APP_LOCS[0]}"
    echo "✅ Found exactly one Gemini Enterprise app ($SELECTED_APP_ID). Automating registration..."

    REG_OUTPUT=$(python3 register_agent.py "$SELECTED_LOC" "$PROJECT_NUMBER" "$SELECTED_LOC" "$SELECTED_APP_ID" "$TOKEN" "${dirName}" "$SERVICE_URL/a2a/app" "\$AGENT_DISPLAY_NAME" '${safeSummary}' "$AUTH_ID")
    echo "$REG_OUTPUT"
    AGENT_ID=$(echo "$REG_OUTPUT" | grep "AGENT_ID:" | cut -d':' -f2)
    rm register_agent.py
    
  else
    if [ "$APP_COUNT" = "0" ]; then
      echo "⚠️ No Gemini Enterprise apps found in 'global', 'us', or 'eu'. You might need to create one first."
      echo "After creating an app, you can register the agent manually or re-run the script."
    else
      echo "💡 Found \$APP_COUNT Gemini Enterprise apps across regions:"
      for i in "\${!APP_DISPLAY_NAMES[@]}"; do
        echo "[\$i] \${APP_DISPLAY_NAMES[\$i]} (\${APP_LOCS[\$i]})"
      done
      
      CHOICE=""
      while true; do
        read -p "Select which app to register the agent to (0-\$((APP_COUNT-1))): " CHOICE
        if [[ "\$CHOICE" =~ ^[0-9]+$ ]] && [ "\$CHOICE" -ge 0 ] && [ "\$CHOICE" -lt "\$APP_COUNT" ]; then
          break
        fi
        echo "Invalid selection. Please enter a number between 0 and \$((APP_COUNT-1))."
      done
      
      SELECTED_APP_ID=$(echo "\${APP_NAMES[\$CHOICE]}" | awk -F'/' '{print \$NF}')
      SELECTED_LOC="\${APP_LOCS[\$CHOICE]}"
      
      echo "✅ Selected app: \${APP_DISPLAY_NAMES[\$CHOICE]}. Automating registration..."
      
      REG_OUTPUT=$(python3 register_agent.py "\$SELECTED_LOC" "\$PROJECT_NUMBER" "\$SELECTED_LOC" "\$SELECTED_APP_ID" "\$TOKEN" "${dirName}" "\$SERVICE_URL/a2a/app" "\$AGENT_DISPLAY_NAME" '${safeSummary}' "\$AUTH_ID")
      echo "\$REG_OUTPUT"
      AGENT_ID=$(echo "\$REG_OUTPUT" | grep "AGENT_ID:" | cut -d':' -f2)
      rm register_agent.py
    fi
  fi


  
  cd ..
${ enableManagedAgent ? `
  # --- Managed Autonomous Agent - PHASE B: await readiness + warm-up ---
  # Creation was started in PHASE A (before data load / sandbox / deploy), so
  # by now most or all of its ~8-10 min has elapsed in parallel.
  if [ -n "$MANAGED_AGENT_ID" ]; then
    echo ""
    echo "🤖 Finalizing Managed Autonomous Agent (started earlier in parallel)..."
    MA_TOKEN=$(gcloud auth print-access-token)
    export MA_OUT="/tmp/ma_ready_$$.txt"
    PROJECT_ID="$PROJECT_ID" python3 "$MA_TOOLS_DIR/create_managed_agent.py" wait "$MANAGED_AGENT_ID" "$MA_TOKEN" 2>&1 | sed 's/^/  /'
    MA_READY=$(cat "$MA_OUT" 2>/dev/null)
    rm -f "$MA_OUT"
    if [ -n "$MA_READY" ]; then
      echo "  ✅ Managed Agent ready: $MANAGED_AGENT_ID (location: global)"
      echo "  🔥 Warming up the autonomous sandbox (pre-provisioning the environment${ workspaceAuthEnabled ? ` + pre-installing the Workspace CLI, typically 1-3 min` : ``})..."
      export MA_OUT="/tmp/ma_env_$$.txt"
      PROJECT_ID="$PROJECT_ID" MA_STATE_COLL="${dirName}_managed_agent_state" python3 "$MA_TOOLS_DIR/warmup_managed_agent.py" "$MANAGED_AGENT_ID" "$MA_TOKEN" "$MA_SKILLS_SOURCE" 2>&1 | sed 's/^/  /' || true
      MANAGED_AGENT_ENV_ID=$(cat "$MA_OUT" 2>/dev/null)
      rm -f "$MA_OUT"
      if [ -n "$MANAGED_AGENT_ENV_ID" ]; then
        echo "  ✅ Sandbox environment pre-provisioned: $MANAGED_AGENT_ENV_ID (runtime reads it from Firestore)"
      else
        echo "  ⚠️  Warm-up returned no environment id (first delegation will provision on demand)."
      fi
    else
      echo "  ⚠️  Managed Agent is not ready - disabling autonomous delegation on the deployed service."
      MANAGED_AGENT_ID=""
      gcloud run services update "\$SERVICE_NAME" --region us-central1 --remove-env-vars MANAGED_AGENT_ID --quiet >/dev/null 2>&1 \\
        && echo "  ✅ MANAGED_AGENT_ID removed from the Cloud Run service (re-run this script later to retry)." \\
        || echo "  ⚠️  Could not update the Cloud Run service env vars - delegation may fail at runtime."
    fi
    unset MA_OUT
    rm -f "$MA_TOOLS_DIR/create_managed_agent.py" "$MA_TOOLS_DIR/warmup_managed_agent.py" "$MA_TOOLS_DIR/managed_agent_instruction.txt"
  fi
` : ''}
  echo "========================================================="
  if [ ! -z "\$AGENT_ID" ]; then
    echo "🎉 Gemini Enterprise Deployment & Registration Complete!"
  else
    echo "⚠️ Gemini Enterprise Deployment Complete (Manual Registration Required)"
  fi
  echo "========================================================="
  echo ""
  echo "🌟 Agent Profile"
  echo "---------------------------------------------------------"
  echo "🤖 Agent Name:   \$AGENT_DISPLAY_NAME (${dirName})"
  echo '📝 Description:  ${safeSummary}'
  echo ""
  echo "🗄️ Data Resources"
  echo "---------------------------------------------------------"
  echo "📂 Demo Asset Directory: ~/${dirName}"
  echo "📊 BigQuery Dataset:    ${datasetId}"
  echo "🔥 Firestore:           ${fsCollection}"
  ${ (params.importedMcpList && params.importedMcpList.length > 0) ? `
  echo ""
  echo "🔌 Custom MCP Servers (${params.importedMcpList.length})"
  echo "---------------------------------------------------------"
${params.importedMcpList.map((mcp, idx) => {
  if (mcp.type === 'remote') {
    return `  echo "  #${idx + 1}: ${mcp.name || 'Remote MCP'} (managed: ${mcp.endpoint_url})"`;
  }
  const rn = mcp.github_url.split('/').pop().replace(/\.git$/, '');
  return `  echo "  #${idx + 1}: ${rn} (port ${9090 + idx})"`;
}).join('\n')}` : '' }
  echo ""
  echo "🔗 Quick Access Links"
  echo "---------------------------------------------------------"
  if [ ! -z "\$AGENT_ID" ]; then
    # Resolve the web app config id (cid) so the link opens the agent directly.
    LINK_TOKEN=$(gcloud auth application-default print-access-token 2>/dev/null || gcloud auth print-access-token)
    if [ "\$SELECTED_LOC" = "global" ]; then
      WC_ENDPOINT="discoveryengine.googleapis.com"
    else
      WC_ENDPOINT="\${SELECTED_LOC}-discoveryengine.googleapis.com"
    fi
    CONFIG_ID=$(curl -s -H "Authorization: Bearer \$LINK_TOKEN" -H "X-Goog-User-Project: \$PROJECT_ID" \
      "https://\$WC_ENDPOINT/v1alpha/projects/\$PROJECT_ID/locations/\$SELECTED_LOC/collections/default_collection/engines/\$SELECTED_APP_ID/widgetConfigs/default_search_widget_config" \
      | python3 -c 'import sys, json; print(json.load(sys.stdin).get("configId", ""))' 2>/dev/null) || true
    if [ ! -z "\$CONFIG_ID" ]; then
      echo "💬 Start Chatting with Your Agent:"
      echo "   👉 https://vertexaisearch.cloud.google.com/home/cid/\$CONFIG_ID/r/agent/\$AGENT_ID/session/-"
    else
      echo "💬 Start Chatting in Gemini Enterprise:"
      echo "   👉 https://console.cloud.google.com/gemini-enterprise/locations/\$SELECTED_LOC/engines/\$SELECTED_APP_ID/overview/dashboard?project=\$PROJECT_ID"
      echo "   💡 Click the 'Preview' button at the top to launch Gemini Enterprise, then select 'Agents' from the left menu to start chatting with your deployed agent."
    fi
    echo ""
  else
    echo "💻 Gemini Enterprise Console:"
    echo "   👉 https://console.cloud.google.com/gemini-enterprise/overview?project=\$PROJECT_ID"
    echo ""
  fi
  
  if [ "\$VIEWER_DEPLOYED" = "true" ]; then
    echo "📊 Firestore Data Viewer:"
    echo "   👉 \$VIEWER_URL"
    echo ""
  else
    echo "📊 Firestore Data Viewer: Not Deployed (Skipped or restricted by Org Policy)"
    echo ""
  fi

  echo "🔎 BigQuery Console:"
  echo "   👉 https://console.cloud.google.com/bigquery?referrer=search&project=\$PROJECT_ID&ws=!1m4!1m3!3m2!1s\$PROJECT_ID!2s${datasetId}"
  echo ""
  echo "========================================================="
  echo ""
  echo "💡 Next Steps:"
  echo "• Copy the demo prompts from the Web UI and try them in the Chat URL!"
  echo "• To clean up all resources, run:"
  echo "  \$ cd ~ && bash setup-${dirName}.sh --cleanup"
  echo "========================================================="
  exit 0


`;

  return fullScript;
}

// ===========================================
// Domain Research (Company Lookup)
// ===========================================

/**
 * Normalizes a target-persona object sent from the client into a plain text
 * description safe for interpolation into LLM prompt template literals.
 * Strips backticks, curly braces, and backslashes (see AGENTS.md rules 7/13)
 * and caps the length. Returns '' when no persona is selected, which keeps
 * every prompt byte-identical to the pre-persona behavior.
 * @param {Object|null} persona - { id, label, description, custom? } or null
 * @returns {string} Sanitized description text, or '' when absent
 */
// Languages offered by the research language selector in the UI. Exact
// membership check doubles as sanitization: only these strings are ever
// interpolated into prompts.
const SUPPORTED_RESEARCH_LANGS_ = ['日本語', 'English', 'Deutsch', 'Français', 'Español', 'Italiano', '中文', '한국어', 'Português', 'Русский', 'Nederlands', 'Svenska', 'Suomi'];

function sanitizePersonaText_(persona) {
  if (!persona || typeof persona !== 'object') return '';
  const raw = String(persona.description || persona.label || '');
  const stripRe = new RegExp('[' + String.fromCharCode(96) + '{}\\\\]', 'g');
  return raw.replace(stripRe, '').replace(/\s+/g, ' ').trim().substring(0, 300);
}

/**
 * Researches a company by its domain name using Gemini + Google Search grounding.
 * Returns company info, business challenges, workflows, and a suggested agent goal.
 * @param {string} domain - Customer domain (e.g., "toyota.co.jp")
 * @param {Object|null} persona - Optional target persona { id, label, description }
 * @returns {Object} Structured company research results
 */
function researchCompanyByDomain(domain, persona, langOverride) {
  if (!domain || typeof domain !== 'string') {
    return { success: false, error: 'Domain is required.' };
  }

  // Normalize domain
  domain = domain.trim().toLowerCase().replace(/^(https?:\/\/)?(www\.)?/, '').replace(/\/.*$/, '');

  // Optional manual override from the UI language selector ('Auto' sends null).
  const overrideLang = (typeof langOverride === 'string' && SUPPORTED_RESEARCH_LANGS_.indexOf(langOverride.trim()) !== -1)
    ? langOverride.trim() : null;

  // TLD map is no longer the decision mechanism (a Japanese company on a .com
  // domain used to get English). It only seeds the fallback used when the
  // model omits detectedLanguage in auto mode; the actual choice is made by
  // the model from the grounded search results (HQ country / official site).
  const tldLangMap = {
    '.co.jp': '日本語', '.jp': '日本語', '.ne.jp': '日本語', '.or.jp': '日本語', '.ac.jp': '日本語',
    '.de': 'Deutsch', '.fr': 'Français', '.es': 'Español', '.it': 'Italiano',
    '.cn': '中文', '.tw': '中文', '.kr': '한국어', '.br': 'Português',
    '.ru': 'Русский', '.nl': 'Nederlands', '.se': 'Svenska', '.fi': 'Suomi',
    '.in': 'English', '.co.uk': 'English', '.com.au': 'English',
    '.com': 'English', '.io': 'English', '.ai': 'English', '.org': 'English', '.net': 'English'
  };

  let fallbackLang = 'English';
  // Match longest TLD first (e.g., .co.jp before .jp)
  const sortedTlds = Object.keys(tldLangMap).sort((a, b) => b.length - a.length);
  for (const tld of sortedTlds) {
    if (domain.endsWith(tld)) {
      fallbackLang = tldLangMap[tld];
      break;
    }
  }

  const langBlock = overrideLang
    ? '**RESPONSE LANGUAGE**: Respond entirely in ' + overrideLang + '. Set "detectedLanguage" to exactly "' + overrideLang + '".'
    : '**RESPONSE LANGUAGE (AUTO-DETECT)**: Determine the company\'s primary business language and write ALL text values in that language.\n' +
      '- Country-code TLDs are decisive: e.g. .jp/.co.jp -> 日本語, .de -> Deutsch, .fr -> Français, .es -> Español, .it -> Italiano, .cn/.tw -> 中文, .kr -> 한국어, .br -> Português.\n' +
      '- For generic TLDs (.com, .io, .ai, .org, .net, ...), decide from your search results: use the primary language of the company\'s headquarters country and official website. Example: a Japanese company using a .com domain MUST still be answered in 日本語.\n' +
      '- Report your final choice in the "detectedLanguage" JSON field, picking the closest match from: ' + SUPPORTED_RESEARCH_LANGS_.join(', ') + '.';

  const personaDesc = sanitizePersonaText_(persona);
  const personaBlock = personaDesc
    ? '\n**TARGET PERSONA (MANDATORY)**: This demo is being prepared for a specific target user: ' + personaDesc + '. Apply this throughout: when listing "workflows", prioritize workflows that this persona owns or directly depends on. The "suggestedGoal" MUST be written around this persona\'s own business process: name this role explicitly as the primary user of the AI agent, and frame the business problem, stakeholders, and KPIs from this persona\'s point of view. Render the role title naturally in the RESPONSE LANGUAGE.\n'
    : '';

  const prompt = `You are a business analyst researching a company for an AI agent demo preparation.
Research the company behind the domain "${domain}" using the latest available information from the internet.

${langBlock}
${personaBlock}
Provide the following information in a structured JSON format:
1. **companyName**: Official company name
2. **companySummary**: Brief company overview (industry, scale, main business areas, headquarters location) in 2-3 sentences
3. **industry**: Primary industry classification (e.g., "Manufacturing", "Retail", "Financial Services")
4. **businessChallenges**: Array of 3-5 key business challenges the company is likely facing based on their industry, recent news, and market position
5. **workflows**: Array of 5-8 key business workflows/processes, each with:
   - "name": Workflow name
   - "automatable": boolean — whether this workflow is a good candidate for AI agent automation
   - "reason": Brief reason why it is or isn't suitable for agent automation
6. **suggestedGoal**: A detailed business scenario description (3-5 sentences) suitable as input for an AI agent demo generator. This should:
   - Reference the actual company name and industry
   - Focus on the MOST automatable workflow(s) identified above
   - Describe a specific, actionable business problem that an AI agent could solve
   - Include realistic operational context (data sources, stakeholders, KPIs)
   - Follow the theme of "Autonomous Action and Core System Optimization" — the agent should detect events, analyze data, and actively update core systems
   - Span at least two departments that share the same core-system data, and describe the hand-off between them that the agent automates. Where the business problem plausibly involves only one department, model the hand-off with an adjacent supporting function (e.g., support -> billing, support -> product quality)
7. **quantFacts**: An object of verifiable QUANTITATIVE facts about the company for grounding synthetic demo data in real-world scale. Include ONLY facts clearly supported by your search results - omit any key you are not confident about (an empty object is fine; NEVER estimate or invent numbers). All values are strings that include the unit and, when known, the as-of year. Possible keys (all optional): "storeCount", "siteCount", "employeeCount", "annualRevenue", "mainRegions" (array of region/prefecture names ordered by weight), "productCategories" (array of the main product/service categories), "notableScale" (one free-form fact like daily shipments or member count).
8. **detectedLanguage**: The language ALL text values in this response are written in (see RESPONSE LANGUAGE above).

**IMPORTANT**:
- Use REAL, factual information about this company. Do NOT hallucinate or invent details.
- If you cannot find sufficient information about the company, set "success" to false and provide an error message.
- Focus on workflows where AI agents can provide the most business value through automation.

Output pure JSON only (no code blocks, no markdown):
{
  "companyName": "...",
  "companySummary": "...",
  "industry": "...",
  "businessChallenges": ["...", "..."],
  "workflows": [
    {"name": "...", "automatable": true, "reason": "..."},
    {"name": "...", "automatable": false, "reason": "..."}
  ],
  "suggestedGoal": "...",
  "quantFacts": { "storeCount": "...", "mainRegions": ["..."] },
  "detectedLanguage": "..."
}`;

  try {
    // Direct API call with flash-lite model for speed + higher token limit
    let location = CONFIG.LOCATION || 'global';
    const host = location === 'global' ? 'aiplatform.googleapis.com' : `${location}-aiplatform.googleapis.com`;
    const researchModel = 'gemini-3.5-flash-lite';
    const url = `https://${host}/v1/projects/${CONFIG.PROJECT_ID}/locations/${location}/publishers/google/models/${researchModel}:generateContent`;
    
    const payload = {
      contents: [{ role: 'user', parts: [{ text: prompt }] }],
      tools: [{ googleSearch: {} }],
      generationConfig: { temperature: 0.2, maxOutputTokens: 65535 }
    };
    const apiResponse = UrlFetchApp.fetch(url, {
      method: 'POST',
      contentType: 'application/json',
      headers: { 'Authorization': 'Bearer ' + ScriptApp.getOAuthToken() },
      payload: JSON.stringify(payload),
      muteHttpExceptions: true
    });
    if (apiResponse.getResponseCode() !== 200) {
      throw new Error('AI Search Error: ' + apiResponse.getContentText().substring(0, 200));
    }
    
    // Google Search grounding can return text across multiple parts — concatenate all
    const candidate = JSON.parse(apiResponse.getContentText()).candidates[0];
    const allText = candidate.content.parts
      .filter(p => p.text)
      .map(p => p.text)
      .join('');
    
    console.log('[RESEARCH] Raw response length: ' + allText.length);
    
    let jsonStr = allText.replace(/```json\n?/g, '').replace(/```\n?/g, '').trim();

    let parsed;
    try {
      parsed = JSON.parse(jsonStr);
    } catch (parseErr) {
      // Attempt to extract JSON from response
      const jsonMatch = jsonStr.match(/\{[\s\S]*\}/);
      if (jsonMatch) {
        parsed = JSON.parse(jsonMatch[0]);
      } else {
        console.error('[RESEARCH] Failed to parse. Raw text: ' + jsonStr.substring(0, 500));
        throw new Error('Failed to parse research results. The AI response did not contain valid JSON.');
      }
    }

    // Validate required fields
    if (!parsed.companyName || !parsed.suggestedGoal) {
      return { success: false, error: 'Could not find sufficient information for domain: ' + domain };
    }

    return {
      success: true,
      companyName: parsed.companyName,
      companySummary: parsed.companySummary || '',
      industry: parsed.industry || '',
      businessChallenges: parsed.businessChallenges || [],
      workflows: parsed.workflows || [],
      suggestedGoal: parsed.suggestedGoal,
      quantFacts: parsed.quantFacts || null,
      detectedLanguage: (typeof parsed.detectedLanguage === 'string' && parsed.detectedLanguage.trim())
        ? parsed.detectedLanguage.trim()
        : (overrideLang || fallbackLang)
    };
  } catch (e) {
    console.error('[RESEARCH] Error for domain ' + domain + ':', e.message);
    return { success: false, error: 'Research failed: ' + e.message };
  }
}

/**
 * Regenerates a business scenario (suggestedGoal) based on user-selected workflows.
 * Called when the user customizes the workflow selection after domain research,
 * ensuring the Business Scenario section stays consistent with the selected workflows.
 * @param {Object} companyInfo - { companyName, industry, companySummary }
 * @param {Array} selectedWorkflows - [{ name, reason }, ...]
 * @param {Object|null} persona - Optional target persona { id, label, description }
 * @param {string|null} language - Explicit output language (from research detectedLanguage or the UI override)
 * @returns {Object} { success: boolean, goal: string, error?: string }
 */
function regenerateGoalForWorkflows(companyInfo, selectedWorkflows, persona, language) {
  if (!companyInfo || !selectedWorkflows || selectedWorkflows.length === 0) {
    return { success: false, error: 'Company info and at least one workflow are required.' };
  }

  // Prefer the explicit language carried over from the research step; the CJK
  // regex is only a JP/EN fallback for old callers (it loses e.g. German).
  const responseLang = (typeof language === 'string' && SUPPORTED_RESEARCH_LANGS_.indexOf(language.trim()) !== -1)
    ? language.trim()
    : (/[\u3000-\u9fff\uff00-\uffef]/.test(companyInfo.companySummary) ? '日本語' : 'English');

  const personaDesc = sanitizePersonaText_(persona);
  const personaSection = personaDesc
    ? '\n## Target Persona\nThe demo user is ' + personaDesc + '.\n'
    : '';
  const personaRule = personaDesc
    ? '\n- Write the scenario from the Target Persona\'s point of view: the business problem, stakeholders, and KPIs must belong to this persona\'s own business process, and this persona must be the primary user of the AI agent. Render the role title naturally in the output language.'
    : '';

  const prompt = `You are a business analyst creating an AI agent demo scenario.

Given the company and selected workflows below, write a detailed business scenario (3-5 sentences) suitable as input for an AI agent demo generator.

## Company
- Name: ${companyInfo.companyName}
- Industry: ${companyInfo.industry}
- Overview: ${companyInfo.companySummary}
${personaSection}
## Selected Workflows for AI Agent Automation
${selectedWorkflows.map(w => `- ${w.name}: ${w.reason}`).join('\n')}

## Instructions
- Reference the actual company name and industry
- Focus ONLY on the selected workflows above — do NOT introduce unrelated workflows
- Describe a specific, actionable business problem that an AI agent could solve
- Include realistic operational context (data sources, stakeholders, KPIs)
- Theme: "Autonomous Action and Core System Optimization" — the agent should detect events, analyze data, and actively update core systems
- Span at least two departments that share the same core-system data, and describe the hand-off between them that the agent automates (if only one department plausibly applies, use an adjacent supporting function such as support -> billing)
- Write entirely in ${responseLang}${personaRule}

Output ONLY the scenario text. No JSON, no code blocks, no explanations.`;

  try {
    let location = CONFIG.LOCATION || 'global';
    const host = location === 'global' ? 'aiplatform.googleapis.com' : `${location}-aiplatform.googleapis.com`;
    const model = 'gemini-3.5-flash-lite';
    const url = `https://${host}/v1/projects/${CONFIG.PROJECT_ID}/locations/${location}/publishers/google/models/${model}:generateContent`;

    const payload = {
      contents: [{ role: 'user', parts: [{ text: prompt }] }],
      generationConfig: { temperature: 0.3, maxOutputTokens: 1024 }
    };
    const response = UrlFetchApp.fetch(url, {
      method: 'POST',
      contentType: 'application/json',
      headers: { 'Authorization': 'Bearer ' + ScriptApp.getOAuthToken() },
      payload: JSON.stringify(payload),
      muteHttpExceptions: true
    });

    if (response.getResponseCode() !== 200) {
      throw new Error('AI Error: ' + response.getContentText().substring(0, 200));
    }

    const text = JSON.parse(response.getContentText()).candidates[0].content.parts[0].text.trim();
    return { success: true, goal: text };
  } catch (e) {
    console.error('[REGEN-GOAL] Error:', e.message);
    return { success: false, error: e.message };
  }
}

// ===========================================
// Vertex AI Agent Platform & Utilities
// ===========================================

function callVertexAIWithRetry(prompt) { return executeWithRetry(() => callVertexAI(prompt)); }

function callVertexAI(prompt) {
  let location = CONFIG.LOCATION || 'global';
  const host = location === 'global' ? 'aiplatform.googleapis.com' : `${location}-aiplatform.googleapis.com`;
  const url = `https://${host}/v1/projects/${CONFIG.PROJECT_ID}/locations/${location}/publishers/google/models/${CONFIG.MODEL}:generateContent`;
  
  const payload = { contents: [{ role: 'user', parts: [{ text: prompt }] }], generationConfig: { temperature: 0.4, maxOutputTokens: 65535 } };
  const response = UrlFetchApp.fetch(url, { method: 'POST', contentType: 'application/json', headers: { 'Authorization': 'Bearer ' + ScriptApp.getOAuthToken() }, payload: JSON.stringify(payload), muteHttpExceptions: true });
  if (response.getResponseCode() !== 200) throw new Error(`AI Error: ${response.getContentText()}`);
  return JSON.parse(response.getContentText()).candidates[0].content.parts[0].text;
}

/**
 * Calls Vertex AI Agent Platform with Google Search grounding enabled.
 * Used for discovering real BigQuery public dataset IDs.
 */
function callVertexAIWithSearch(prompt) {
  let location = CONFIG.LOCATION || 'global';
  const host = location === 'global' ? 'aiplatform.googleapis.com' : `${location}-aiplatform.googleapis.com`;
  const searchModel = 'gemini-3.5-flash-lite';
  const url = `https://${host}/v1/projects/${CONFIG.PROJECT_ID}/locations/${location}/publishers/google/models/${searchModel}:generateContent`;
  
  const payload = {
    contents: [{ role: 'user', parts: [{ text: prompt }] }],
    tools: [{ googleSearch: {} }],
    generationConfig: { temperature: 0.2, maxOutputTokens: 2048 }
  };
  const response = UrlFetchApp.fetch(url, {
    method: 'POST',
    contentType: 'application/json',
    headers: { 'Authorization': 'Bearer ' + ScriptApp.getOAuthToken() },
    payload: JSON.stringify(payload),
    muteHttpExceptions: true
  });
  if (response.getResponseCode() !== 200) throw new Error(`AI Search Error: ${response.getContentText()}`);
  return JSON.parse(response.getContentText()).candidates[0].content.parts[0].text;
}


/**
 * Calls Vertex AI Agent Platform gemini-3-pro-image-preview model in global region to generate an image.
 * Returns an object containing base64Data and mimeType.
 * @param {string} prompt Highly detailed image generation prompt in English.
 * @returns {object} { base64Data: string, mimeType: string }
 */
function generateImageBase64WithRetry(prompt) {
  return executeWithRetry(() => generateImageBase64(prompt));
}

/**
 * Deterministically injects the concrete table rows (file.imageRows) into the
 * image prompt so the image model renders multiple distinct handwritten lines
 * instead of collapsing to a single row. Falls back to the raw imagePrompt when
 * fewer than 2 rows are supplied (e.g., non-tabular images).
 * @param {object} file Image file spec with imagePrompt and optional imageColumns/imageRows.
 * @returns {string} Final prompt to send to the image model.
 */
function buildImagePromptWithRows_(file) {
  const rows = Array.isArray(file.imageRows)
    ? file.imageRows.map(r => String(r).trim()).filter(r => r.length > 0)
    : [];
  if (rows.length < 2) {
    console.warn(`[ImageGen-Pipeline] '${file.fileName}' has fewer than 2 imageRows; using raw imagePrompt (single-row risk).`);
    return file.imagePrompt;
  }
  const columns = Array.isArray(file.imageColumns)
    ? file.imageColumns.map(c => String(c).trim()).filter(c => c.length > 0)
    : [];
  const n = rows.length;
  let block = `\n\nMANDATORY TABLE CONTENT - Render EXACTLY these ${n} handwritten rows inside the table grid, each as its own separate line. Do NOT merge, summarize, or omit any row. The table must visibly contain all ${n} rows.`;
  if (columns.length > 0) {
    block += `\nColumns: ${columns.join(' | ')}`;
  }
  rows.forEach((row, i) => { block += `\n${i + 1}) ${row}`; });
  block += `\nThe table has exactly ${n} data rows.`;
  return file.imagePrompt + block;
}

function generateImageBase64(prompt) {
  const host = 'aiplatform.googleapis.com';
  const url = `https://${host}/v1/projects/${CONFIG.PROJECT_ID}/locations/global/publishers/google/models/gemini-3-pro-image:generateContent`;
  
  const payload = {
    contents: [
      {
        role: 'user',
        parts: [
          { text: prompt }
        ]
      }
    ],
    generationConfig: {
      responseModalities: ["IMAGE"]
    }
  };
  
  console.log('[ImageGen] Calling global gemini-3-pro-image. Prompt length: ' + prompt.length);
  
  const response = UrlFetchApp.fetch(url, {
    method: 'POST',
    contentType: 'application/json',
    headers: { 'Authorization': 'Bearer ' + ScriptApp.getOAuthToken() },
    payload: JSON.stringify(payload),
    muteHttpExceptions: true
  });
  
  if (response.getResponseCode() !== 200) {
    console.error(`[ImageGen Error] Code: ${response.getResponseCode()}, Body: ${response.getContentText()}`);
    throw new Error(`Image Gen Error: ${response.getContentText()}`);
  }
  
  const json = JSON.parse(response.getContentText());
  if (!json.candidates || json.candidates.length === 0 || !json.candidates[0].content.parts) {
    throw new Error("No candidates or parts returned from Image Gen API.");
  }
  
  let base64Data = null;
  let mimeType = 'image/jpeg';
  
  for (const part of json.candidates[0].content.parts) {
    if (part.inlineData) {
      base64Data = part.inlineData.data;
      mimeType = part.inlineData.mimeType || mimeType;
      break;
    }
  }
  
  if (!base64Data) {
    throw new Error("No inlineData found in the response parts.");
  }
  
  console.log('[ImageGen] SUCCESS! Got base64 data, length: ' + base64Data.length + ', mimeType: ' + mimeType);
  return { base64Data: base64Data, mimeType: mimeType };
}


function executeWithRetry(fn) {
  let lastError;
  for (let attempt = 1; attempt <= CONFIG.MAX_RETRIES; attempt++) {
    try { return fn(); } catch (error) { lastError = error; Utilities.sleep(CONFIG.RETRY_DELAY_MS * attempt); }
  }
  throw lastError;
}


// ===========================================
// Demo Taxonomy Classification
// ===========================================

/**
 * Classifies a demo into the controlled TAXONOMY (industry / persona / useCase).
 *
 * Single source of truth for classification — used both by generateDemo
 * (at creation time) and by backfillTaxonomy (for existing rows).
 *
 * Guarantees:
 *  - Output is ALWAYS English, regardless of the input language. A Japanese
 *    userGoal still yields English enum values (and an English free-form
 *    label when the result is 'Other').
 *  - 'Other' is minimized: any field that comes back 'Other' on the first
 *    pass is re-classified with a forced-choice prompt that removes 'Other'
 *    from the allowed values, so 'Other' only survives when nothing fits
 *    even under forced choice.
 *
 * @param {string} userGoal - The business goal (any language).
 * @param {string} aiSummary - One-sentence summary of the demo (any language).
 * @param {string} [businessInstruction] - Extra context to improve accuracy.
 * @returns {{industry:string, persona:string, useCase:string,
 *            industryOther:string, personaOther:string, useCaseOther:string}}
 */
function classifyDemoTaxonomy_(userGoal, aiSummary, businessInstruction) {
  const fallback = {
    industry: 'Other', persona: 'Other', useCase: 'Other',
    industryOther: '', personaOther: '', useCaseOther: ''
  };

  try {
    // Pass 1: full enums (Other allowed).
    const first = callTaxonomyModel_(userGoal, aiSummary, businessInstruction, {
      industry: TAXONOMY.industry,
      persona: TAXONOMY.persona,
      useCase: TAXONOMY.useCase
    });

    // Pass 2 (forced choice): re-run only the fields that landed on 'Other',
    // this time with 'Other' removed from the allowed values.
    const forceAllowed = {};
    ['industry', 'persona', 'useCase'].forEach(function (k) {
      if (first[k] === 'Other') {
        forceAllowed[k] = TAXONOMY[k].filter(function (v) { return v !== 'Other'; });
      }
    });

    if (Object.keys(forceAllowed).length > 0) {
      const forced = callTaxonomyModel_(userGoal, aiSummary, businessInstruction, forceAllowed);
      Object.keys(forceAllowed).forEach(function (k) {
        if (forced[k] && forced[k] !== 'Other') first[k] = forced[k];
      });
    }

    return {
      industry: first.industry || 'Other',
      persona: first.persona || 'Other',
      useCase: first.useCase || 'Other',
      // Keep the English free-form label only when the value is still 'Other'.
      industryOther: first.industry === 'Other' ? (first.industryOther || '') : '',
      personaOther: first.persona === 'Other' ? (first.personaOther || '') : '',
      useCaseOther: first.useCase === 'Other' ? (first.useCaseOther || '') : ''
    };
  } catch (e) {
    console.warn('[TAXONOMY] Classification failed, defaulting to Other:', e.message);
    return fallback;
  }
}

/**
 * One structured Gemini call that maps a demo to a set of allowed values.
 *
 * @param {string} userGoal
 * @param {string} aiSummary
 * @param {string} businessInstruction
 * @param {Object} allowed - Map of field name -> array of allowed enum values.
 *                           Only the keys present are requested and returned.
 * @returns {Object} Parsed JSON keyed by the requested fields (+ *Other when
 *                   'Other' is among the allowed values for that field).
 * @private
 */
function callTaxonomyModel_(userGoal, aiSummary, businessInstruction, allowed) {
  const location = CONFIG.LOCATION || 'global';
  const host = location === 'global' ? 'aiplatform.googleapis.com' : `${location}-aiplatform.googleapis.com`;
  const model = 'gemini-3.5-flash-lite';
  const url = `https://${host}/v1/projects/${CONFIG.PROJECT_ID}/locations/${location}/publishers/google/models/${model}:generateContent`;

  const fields = Object.keys(allowed); // subset of ['industry','persona','useCase']
  const allowsOther = fields.some(function (k) { return allowed[k].indexOf('Other') !== -1; });

  // English definitions + mapping hints to steer the model toward a real value.
  const DEFINITIONS = {
    industry: 'The customer industry/sector the demo targets. Hints: bank/insurance/credit/accounting platform -> Finance; hospital/clinic/pharma -> Healthcare; factory/production line -> Manufacturing; government/municipal/public services -> Public Sector; shipping/warehouse/3PL -> Logistics & Supply Chain; software/SaaS/cloud -> Technology; car/vehicle/dealer/OEM -> Automotive; law firm/legal office/consulting/tax accountant/CPA -> Legal & Professional Services.',
    persona: 'The primary job function the agent is built for (its end user). Hints: store manager/floor ops/plant ops -> Operations; credit/accounting/treasury -> Finance; support/contact center/helpdesk -> Customer Service; CxO/leadership reporting -> Executive; demand/inventory/procurement -> Supply Chain; lawyer/paralegal/compliance officer/regulatory -> Legal & Compliance; scientist/researcher/lab/R&D engineer -> R&D / Research.',
    useCase: 'The core capability the agent demonstrates. Hints: dashboards/KPIs/reporting -> Analytics & Insights; automating a multi-step workflow -> Process Automation; chatbots/personalization/outreach -> Customer Engagement; demand or sales forecasting/planning -> Forecasting & Planning; OCR/parsing forms or invoices -> Document Processing; RAG/search over documents -> Knowledge Retrieval; fraud/defect/outlier detection -> Risk & Anomaly Detection; routing/scheduling/allocation -> Optimization; regulatory compliance checking/audit trail/policy enforcement -> Compliance & Audit.'
  };
  const LABELS = { industry: 'INDUSTRY', persona: 'PERSONA', useCase: 'USE CASE' };

  const criteria = fields.map(function (k) {
    return `- ${LABELS[k]}: ${DEFINITIONS[k]}\n  Allowed values (choose EXACTLY one, verbatim): ${allowed[k].join(' | ')}`;
  }).join('\n');

  const otherRule = allowsOther
    ? 'Use "Other" ONLY when none of the allowed values reasonably fit — this must be extremely rare. When in doubt, pick the single closest value.'
    : 'You MUST pick the single closest allowed value. "Other" is NOT permitted.';

  const prompt =
`You are a precise classifier for a catalog of AI agent demos.
Classify the demo described below into the requested dimensions.

CRITICAL OUTPUT RULES:
1. The input may be written in ANY language (e.g. Japanese). Your output values MUST ALWAYS be in ENGLISH.
2. For each dimension, return one of the allowed values EXACTLY as written.
3. ${otherRule}
${allowsOther ? '4. When (and only when) you return "Other" for a dimension, also provide a short English free-form label for it in the matching *Other field (e.g. industryOther). Otherwise leave the *Other field empty.' : ''}

DIMENSIONS:
${criteria}

DEMO:
- Goal: ${userGoal || 'N/A'}
- Summary: ${aiSummary || 'N/A'}
${businessInstruction ? '- Business context: ' + String(businessInstruction).substring(0, 1500) : ''}`;

  // Build a responseSchema limited to the requested fields.
  const props = {};
  fields.forEach(function (k) {
    props[k] = { type: 'STRING', enum: allowed[k] };
    if (allowed[k].indexOf('Other') !== -1) props[k + 'Other'] = { type: 'STRING' };
  });

  const requestBody = {
    contents: [{ role: 'user', parts: [{ text: prompt }] }],
    generationConfig: {
      temperature: 0.1,
      responseMimeType: 'application/json',
      responseSchema: { type: 'OBJECT', properties: props, required: fields }
    }
  };

  return executeWithRetry(function () {
    const response = UrlFetchApp.fetch(url, {
      method: 'post',
      contentType: 'application/json',
      headers: { Authorization: 'Bearer ' + ScriptApp.getOAuthToken() },
      payload: JSON.stringify(requestBody),
      muteHttpExceptions: true
    });
    if (response.getResponseCode() !== 200) throw new Error('Taxonomy AI Error: ' + response.getContentText());
    const text = JSON.parse(response.getContentText()).candidates[0].content.parts[0].text;
    return JSON.parse(text);
  });
}






function updateSystemInstruction(setupScript, newBusinessInstruction, technicalInstruction) {
  const fullInstruction = `${newBusinessInstruction}\n\n${technicalInstruction}`;
  const escaped = fullInstruction.replace(/\\/g, '\\\\').replace(/'/g, "'\\''").replace(/\n/g, '\\n');
  return setupScript.replace(/(1\.\s+\*\*BigQuery toolset:\*\*.*?\n)([\s\S]*?)(\n\s+2\.\s+\*\*Maps Toolset:\*\*)/, `$1${escaped}$3`);
}

function include(filename) {
  return HtmlService.createHtmlOutputFromFile(filename).getContent();
}

/**
 * Generates a text-based PDF from content using DocumentApp.
 * @param {string} content - The content to written into the PDF.
 * @param {string} fileName - The name of the generated PDF file.
 * @returns {object} { success: boolean, base64: string, error?: string }
 */
function generatePdfFromServer(content, fileName) {
  try {
    const doc = DocumentApp.create('Temp PDF Generation');
    const body = doc.getBody();
    
    function applyBold(element, text) {
      if (!text) return;
      const parts = text.split('**');
      if (parts.length <= 1) return;
      
      let newText = '';
      const boldRanges = [];
      
      for (let i = 0; i < parts.length; i++) {
        if (i % 2 === 1) { // It's a bold part
          const start = newText.length;
          newText += parts[i];
          const end = newText.length - 1;
          boldRanges.push({start, end});
        } else {
          newText += parts[i];
        }
      }
      
      element.setText(newText);
      const textElement = element.editAsText();
      boldRanges.forEach(range => {
        textElement.setBold(range.start, range.end, true);
      });
    }
    
    const lines = content.split('\n');
    lines.forEach(line => {
      const trimmed = line.trim();
      if (!trimmed) {
        body.appendParagraph('');
        return;
      }
      
      if (trimmed.startsWith('# ')) {
        const p = body.appendParagraph(trimmed.substring(2)).setHeading(DocumentApp.ParagraphHeading.HEADING1);
        applyBold(p, trimmed.substring(2));
      } else if (trimmed.startsWith('## ')) {
        const p = body.appendParagraph(trimmed.substring(3)).setHeading(DocumentApp.ParagraphHeading.HEADING2);
        applyBold(p, trimmed.substring(3));
      } else if (trimmed.startsWith('### ')) {
        const p = body.appendParagraph(trimmed.substring(4)).setHeading(DocumentApp.ParagraphHeading.HEADING3);
        applyBold(p, trimmed.substring(4));
      } else if (trimmed.startsWith('- ')) {
        const li = body.appendListItem(trimmed.substring(2));
        applyBold(li, trimmed.substring(2));
      } else if (trimmed.startsWith('[CHART:')) {
        const match = trimmed.match(/\[CHART:\s*(BAR|PIE|LINE)?,?\s*([^,\]]+),\s*([^\]]+)\]/i);
        if (match) {
          const type = (match[1] || 'BAR').toUpperCase();
          const title = match[2].trim();
          const dataStr = match[3].trim();
          const pairs = dataStr.split(',').map(p => p.trim());
          
          const dataTable = Charts.newDataTable();
          dataTable.addColumn(Charts.ColumnType.STRING, "Item");
          dataTable.addColumn(Charts.ColumnType.NUMBER, "Value");
          
          pairs.forEach(p => {
             const parts = p.split('=');
             if (parts.length === 2) {
               dataTable.addRow([parts[0].trim(), parseFloat(parts[1].trim()) || 0]);
             }
          });
          
          let builder;
          if (type === 'PIE') {
             builder = Charts.newPieChart();
          } else if (type === 'LINE') {
             builder = Charts.newLineChart();
          } else {
             builder = Charts.newBarChart();
          }
          
          const chart = builder
               .setDataTable(dataTable.build())
               .setTitle(title)
               .setDimensions(600, 300)
               .build();
          
          const imageBlob = chart.getAs('image/png');
          body.appendImage(imageBlob);
        } else {
           const p = body.appendParagraph(trimmed);
           applyBold(p, trimmed);
        }
      } else {
        const p = body.appendParagraph(trimmed);
        applyBold(p, trimmed);
      }
    });
    
    doc.saveAndClose();
    
    const pdfBlob = doc.getAs('application/pdf');
    pdfBlob.setName(fileName);
    
    const base64 = Utilities.base64Encode(pdfBlob.getBytes());
    
    DriveApp.getFileById(doc.getId()).setTrashed(true);
    
    return { success: true, base64: base64 };
  } catch (e) {
    console.error('PDF generation failed:', e.message);
    return { success: false, error: e.message };
  }
}

// =============================================================================
// MCP Server Importer Backend
// =============================================================================

function analyzeMcpRepository(repoUrl) {
  try {
    console.log("1. Starting GitHub repository retrieval: " + repoUrl);
    const repoData = parseGithubUrl(repoUrl);
    
    const defaultBranch = getDefaultBranch(repoData.owner, repoData.repo);
    
    const tree = getRepositoryFiles(repoData.owner, repoData.repo, defaultBranch);
    const filesToLoad = [];
    const priorityFiles = ["readme.md", "package.json", "pyproject.toml", "requirements.txt", ".env.example"];
    
    tree.forEach(item => {
      if (item.type === "blob") {
        const lowerPath = item.path.toLowerCase();
        const baseName = lowerPath.split('/').pop();
        if (priorityFiles.includes(baseName) || baseName === "readme" || baseName.endsWith("readme.md")) {
          filesToLoad.push(item.path);
        }
      }
    });

    const entrypointCandidates = ["main.py", "server.py", "app.py", "index.js", "index.ts", "index.py", "run.py"];
    
    // First pass: Look for obvious entrypoint files
    tree.forEach(item => {
      if (item.type === "blob") {
        const lowerPath = item.path.toLowerCase();
        const baseName = lowerPath.split('/').pop();
        if (entrypointCandidates.includes(baseName) && !lowerPath.includes("test") && !lowerPath.includes("node_modules")) {
          if (!filesToLoad.includes(item.path)) {
            filesToLoad.push(item.path);
          }
        }
      }
    });

    // Second pass: Fill up to 8 source files if needed
    let sourceLoaded = filesToLoad.filter(p => p.endsWith(".py") || p.endsWith(".js") || p.endsWith(".ts")).length;
    for (const item of tree) {
      if (item.type === "blob" && sourceLoaded < 8) {
        const path = item.path;
        if ((path.endsWith(".py") || path.endsWith(".ts") || path.endsWith(".js")) && 
            !path.includes("test") && !path.includes("node_modules") && !path.includes(".venv")) {
          if (!filesToLoad.includes(path)) {
            filesToLoad.push(path);
            sourceLoaded++;
          }
        }
      }
    }

    if (filesToLoad.length === 0) {
      filesToLoad.push("README.md", "package.json", "pyproject.toml", "requirements.txt", ".env.example");
      filesToLoad.push("main.py", "server.py", "app.py", "src/main.py", "src/server.py");
      let pkgName = repoData.repo.replace(/-/g, "_");
      filesToLoad.push(`${pkgName}/main.py`, `src/${pkgName}/main.py`, `src/${pkgName}/server.py`);
    }

    let combinedContent = "";
    for (const filename of filesToLoad) {
      const fileText = fetchFileFromGithub(repoData.owner, repoData.repo, defaultBranch, filename);
      if (fileText) {
        combinedContent += `\n\n--- FILE: ${filename} ---\n${fileText}`;
      }
    }

    if (!combinedContent) {
      throw new Error("Necessary configuration files were not found in the repository.");
    }

    console.log("2. Starting analysis by Gemini...");
    const analysisResult = callGeminiApi(combinedContent, repoUrl);
    
    const parsed = JSON.parse(analysisResult);
    if (!parsed.is_supported) {
       parsed.unsupported_reason += " [Context len: " + combinedContent.length + ", Head: " + combinedContent.substring(0, 200).replace(/\n/g, " ") + "]";
    }
    return {
      success: true,
      data: parsed
    };

  } catch (error) {
    console.error(error);
    return {
      success: false,
      message: error.toString()
    };
  }
}

function parseGithubUrl(url) {
  const match = url.match(/github\.com\/([^/]+)\/([^/]+)/);
  if (!match) throw new Error("Invalid GitHub URL");
  return { owner: match[1], repo: match[2].replace(/\.git$/, "") };
}

function getGithubHeaders() {
  const headers = {};
  if (CONFIG.GITHUB_TOKEN) {
    headers['Authorization'] = `token ${CONFIG.GITHUB_TOKEN}`;
  }
  return headers;
}

function getRepositoryFiles(owner, repo, branch) {
  const apiUrl = `https://api.github.com/repos/${owner}/${repo}/git/trees/${branch}?recursive=1`;
  try {
    const response = UrlFetchApp.fetch(apiUrl, { 
      muteHttpExceptions: true,
      headers: getGithubHeaders()
    });
    if (response.getResponseCode() === 200) {
      const json = JSON.parse(response.getContentText());
      return json.tree || [];
    }
  } catch (e) {}
  return [];
}

function getDefaultBranch(owner, repo) {
  const apiUrl = `https://api.github.com/repos/${owner}/${repo}`;
  try {
    const response = UrlFetchApp.fetch(apiUrl, { 
      muteHttpExceptions: true,
      headers: getGithubHeaders()
    });
    if (response.getResponseCode() === 200) {
      const json = JSON.parse(response.getContentText());
      return json.default_branch || "main";
    }
  } catch (e) {}
  return "main";
}

function fetchFileFromGithub(owner, repo, defaultBranch, path) {
  const branches = [defaultBranch, "main", "master", "HEAD"];
  for (const branch of branches) {
    const apiUrl = `https://raw.githubusercontent.com/${owner}/${repo}/${branch}/${path}`;
    try {
      const response = UrlFetchApp.fetch(apiUrl, {
        muteHttpExceptions: true,
        headers: getGithubHeaders()
      });
      if (response.getResponseCode() === 200) {
        return response.getContentText();
      }
    } catch (e) {
      // Continue to next branch
    }
  }
  return null;
}

// == Managed Agent craft skills (demo-skills/) ==
// Skills are authored as plain files in the repo's demo-skills/ directory and
// compiled into DemoSkills.gs (the DEMO_SKILLS_FILES constant) by
// build_skills.js at clasp-push time. This repo is PRIVATE, so no GitHub /
// network access is involved at generation time - the data ships inside the
// Apps Script project itself. Fail-soft: any problem returns null and the
// demo is generated without craft skills.

function callGeminiApi(contextContent, url) {
  const token = ScriptApp.getOAuthToken(); 
  const projectId = CONFIG.PROJECT_ID;
  const region = CONFIG.LOCATION || 'global';

  const host = region === 'global' ? 'aiplatform.googleapis.com' : `${region}-aiplatform.googleapis.com`;
  const endpoint = `https://${host}/v1/projects/${projectId}/locations/${region}/publishers/google/models/gemini-3.5-flash-lite:generateContent`;

  const prompt = `You are an AI expert determining if custom MCP Servers can be safely provisioned on standard Cloud Run.
Review the collected files enclosed in the <REPOSITORY_CONTEXT> tag below.

Based ONLY on those files, answer:
1. MUST be written in Python or Node.js/TypeScript.
2. MUST NOT require complex OAuth browser validations (unless refresh-token variable is valid).
3. Native binary dependencies rule:
   - If the server FUNDAMENTALLY requires heavy native binaries for ALL core functionality (e.g., FFmpeg, ImageMagick), set is_supported to false.
   - If the server has dependencies that download heavy native binaries during install (e.g., puppeteer, sharp, node-sass) but the core functionality works WITHOUT them (only some optional tools are affected), set is_supported to true, set npm_ignore_scripts to true, and list the affected tools in degraded_tools with a brief reason.

If valid:
- Set is_supported to true.
- Set 'language' based on the PRIMARY dependency/build file:
    - pyproject.toml, setup.py, or requirements.txt (as the main dependency source) → "python"
    - package.json with JS/TS source files → "nodejs"
    - If BOTH exist, determine by the server's main entrypoint file extension (.py → "python", .js/.ts → "nodejs").
    Must be exactly one of: "python" or "nodejs" (lowercase, no other values).
- Specify the correct 'entrypoint' — a shell command that starts the MCP server in STDIO mode when run from the repository root directory (/app/custom_mcp/).
  
  ENTRYPOINT RULES BY LANGUAGE:
  
  [Python with FastMCP library]:
  - FastMCP is identified by import statements: 'from mcp.server.fastmcp import FastMCP' or 'from fastmcp import FastMCP', and the server object is created with 'FastMCP(...)' (e.g., 'mcp = FastMCP("my-server")').
  - CRITICAL: If you see 'from mcp.server import Server' or 'Server(name=...)', this is a PLAIN mcp.Server, NOT FastMCP. You MUST use the [Python without FastMCP] rules below instead.
  - You MUST NOT use the CLI entrypoint (e.g. 'redmine-mcp-server').
  - Output ONLY the Python module path and object name in the format '<module_path>:<mcp_object>' (e.g., 'redmine_mcp_server.redmine_handler:mcp').
  - Our system will automatically wrap this as: python -c "from <module_path> import <mcp_object>; <mcp_object>.run(transport='stdio')"
  - Analyze the Python code to find the FastMCP object. If you cannot find the exact instantiation but see it imported (e.g., 'from .redmine_handler import mcp'), DEDUCE the module path from the package name in pyproject.toml and the import statement.
  - NEVER output the CLI command if it is a FastMCP project.
  
  [Python without FastMCP (plain mcp.Server)]:
  - This applies when the server uses 'from mcp.server import Server' or similar non-FastMCP patterns.
  - Output the standard python command (e.g., 'python -m my_server' or 'python src/main.py').
  - NEVER output the '<module_path>:<object>' format for plain mcp.Server projects.
  
  [Node.js / TypeScript]:
  - Check package.json for: 1) "bin" field → the binary name, 2) "main" field → the entry file, 3) "scripts.start" → how to run.
  - If a "bin" field exists (e.g., {"mcp-server-redmine": "dist/index.js"}), output: 'node dist/index.js'
  - If no "bin" but dist/build directory has index.js, output: 'node dist/index.js' or 'node build/index.js'
  - The command must be a direct 'node <file>' command, NOT 'npx' or 'npm start' (these may not work in the container).
  - The TypeScript source MUST be compiled first (npm run build). Our system handles the build step separately.

- Set transport_mode to "stdio" (our system handles protocol bridging automatically).
- List ONLY the ESSENTIAL environment variables needed for a basic, functional deployment in required_env_vars. Ignore advanced configurations, fine-tuning parameters (e.g., cleanup intervals, SSL paths, port binds), and alternative authentication methods if a primary/recommended one (like an API Key) is available. Focus on getting the server running at a basic level. For each variable, determine if it is REQUIRED or OPTIONAL for that basic function.
- Predict the key capabilities or tools provided by this server based on the code and README (e.g., 'Create Redmine tickets', 'Search issues').
- credential_file: Set ONLY when file-based authentication is the SOLE or PRIMARY method to make the server functional. Examples where credential_file SHOULD be set:
  - Google service account JSON via GOOGLE_APPLICATION_CREDENTIALS (the only way to authenticate)
  - SSH private key file required for Git operations (no alternative)
  Examples where credential_file should be null:
  - Client certificate (PFX/P12) that is an OPTIONAL alternative to username/password auth
  - TLS/SSL certificates used only in specific network configurations
  - Any file-based auth that is conditional (e.g., only used when a specific env var is set, guarded by "if" checks in code)
  Rule: If the server can authenticate and function normally with ONLY environment variable values (API keys, tokens, username/password), set credential_file to null — even if the code also supports optional file-based auth.
  When credential_file is set, provide:
  - env_var_name: The environment variable that points to the file path (e.g., "GOOGLE_APPLICATION_CREDENTIALS")
  - file_description: A concise explanation of what the file contains and step-by-step instructions for obtaining it

If invalid or files are definitely missing context to specify an entrypoint, set is_supported to false and state why under unsupported_reason.

<REPOSITORY_CONTEXT>
${contextContent}
</REPOSITORY_CONTEXT>
`;

  const requestBody = {
    contents: [{ role: 'user', parts: [{ text: prompt }] }],
    generationConfig: {
      responseMimeType: "application/json",
      responseSchema: {
        type: "OBJECT",
        properties: {
          is_supported: { type: "BOOLEAN" },
          unsupported_reason: { type: "STRING" },
          language: { type: "STRING", enum: ["python", "nodejs"] },
          entrypoint: { type: "STRING" },
          transport_mode: { type: "STRING" },
          required_env_vars: {
            type: "ARRAY",
            items: {
              type: "OBJECT",
              properties: {
                key: { type: "STRING" },
                description: { type: "STRING" },
                is_secret: { type: "BOOLEAN" },
                is_required: { type: "BOOLEAN" }
              },
              required: ["key", "description", "is_secret", "is_required"]
            }
          },
          capabilities: {
            type: "ARRAY",
            items: { type: "STRING" }
          },
          npm_ignore_scripts: { type: "BOOLEAN" },
          degraded_tools: {
            type: "ARRAY",
            items: { type: "STRING" }
          },
          credential_file: {
            type: "OBJECT",
            nullable: true,
            properties: {
              env_var_name: { type: "STRING" },
              file_description: { type: "STRING" }
            },
            required: ["env_var_name", "file_description"]
          }
        },
        required: ["is_supported", "unsupported_reason", "language", "entrypoint", "transport_mode", "required_env_vars", "capabilities", "npm_ignore_scripts", "degraded_tools"]
      }
    }
  };

  const options = {
    method: "post",
    contentType: "application/json",
    headers: { Authorization: "Bearer " + token },
    payload: JSON.stringify(requestBody),
    muteHttpExceptions: false
  };

  const response = UrlFetchApp.fetch(endpoint, options);
  const resJson = JSON.parse(response.getContentText());
  
  return resJson.candidates[0].content.parts[0].text;
}

/**
 * Service endpoint for Magic Wand. Expands and refines scenario statement using gemini-3.5-flash-lite.
 * Robustly handles raw inputs, templates, and edited Markdown scenarios from domain research.
 * Features 3-retry loop with exponential backoff to handle transient rate limits (429) and server errors (5xx).
 * @param {string} rawGoal - The user's current scenario text.
 * @returns {Object} Optimized result containing the structured Markdown.
 */
function optimizeGoalWithMagicWand(rawGoal, capabilityOpts) {
  let location = CONFIG.LOCATION || 'global';
  const host = location === 'global' ? 'aiplatform.googleapis.com' : `${location}-aiplatform.googleapis.com`;
  const model = 'gemini-3.5-flash-lite';
  const url = `https://${host}/v1/projects/${CONFIG.PROJECT_ID}/locations/${location}/publishers/google/models/${model}:generateContent`;

  // Capability-aware optimization: when the Managed Agent toggle is on, the
  // optimized scenario must also seed an autonomous long-horizon mission so
  // the downstream planning call has material to build delegation-class demo
  // prompts from. Older callers pass no opts - default to managed ON (the
  // generator default since v11.2).
  const _caps = capabilityOpts || {};
  const _capManaged = _caps.enableManagedAgent !== false;
  const _capWorkspace = !!(_caps.enableWorkspaceMcp || _caps.enableWorkspaceAuth);
  const managedAgentRequirement = _capManaged ? `
4.  **Autonomous Strategic Initiative (MANDATORY)**: The Operational Challenge MUST additionally define ONE standing long-horizon mission suited to a fully autonomous agent working for tens of minutes: live external research (industry trends, competitor moves, market prices, regulations) combined with the company's own data through real quantitative analysis, culminating in an executive-grade deliverable (a board presentation, a formal proposal document, a PDF report, or an interactive briefing page${ _capWorkspace ? ', delivered into the team workspace - saved to shared drives, summarized in a draft email, or posted to the team chat' : ''}). State the business question it answers, the expected deliverable and its audience, and the quality bar (real numbers, cited sources, decision-ready structure). Keep it in business language - no tool or product names.` : '';

  // Optional target-persona override: when the demo creator picked a persona in
  // the UI, the optimized scenario must be framed around that role instead of
  // letting the model invent one. Empty string = prompt unchanged.
  const _personaDesc = sanitizePersonaText_(_caps.persona);
  const personaRequirement = _personaDesc
    ? '\n' + (_capManaged ? '5' : '4') + '.  **Target Persona Override (MANDATORY)**: This demo targets a specific user: ' + _personaDesc + '. Header 2 (Target Role) MUST be a single specific, professional job title matching this persona, translated naturally into the detected output language. The Business Scenario (Header 3) and the Operational Challenge (Header 4) MUST be framed around this persona\'s own business process, daily decisions, and KPIs. If the input text implies or already states a different role (including an existing Target Role header from prior research or a template), the persona specified here takes precedence: REPLACE that role and reframe the scenario around this persona. Before returning, verify the Target Role matches this persona; if it does not, rewrite it.'
    : '';

  // Persona must also win inside Requirement 1 itself: the generic Header 2
  // instruction ("identify a job title") otherwise competes with the trailing
  // override and flash-lite sometimes follows the earlier instruction or keeps
  // a role already present in the input.
  const header2Instruction = _personaDesc
    ? '**Header 2 (Role)**: MUST be a single specific, professional job title matching this target persona: ' + _personaDesc + '. Do NOT keep or invent a different role, even if the input already names one.'
    : '**Header 2 (Role)**: Identify a specific, professional job title appropriate to the role.';

  const prompt = `You are an expert prompt engineer and business analyst.
Your task is to take a raw, simple, or loosely defined business scenario, OR a partially structured business scenario (which might contain company details and selected target workflows from prior research), and optimize/expand it into a **perfectly structured, high-density professional Business Scenario prompt** in Markdown format.

Input to Optimize:
\"\"\"
${rawGoal}
\"\"\"

**CRITICAL MULTILINGUAL RULE (MANDATORY)**: 
1. **Language Detection**: Analyze the \"Input to Optimize\" above and detect its primary language (e.g., English, Japanese, German, French, Spanish, Chinese, Korean, etc.).
2. **Output Language Consistency**: You MUST generate the entire optimized Markdown output in the EXACT SAME language and script as the input. Even if the companies, brands, or locations mentioned in the input are culturally or geographically associated with a specific country or language, you MUST NOT output in that associated language unless the actual input text itself is written using that language's script. Always strictly match the literal language and script of the input text.
3. **Header Translation**: You MUST translate the four standard section headers (Title, Target Role, Business Scenario, Operational Challenge) to match the detected language naturally and professionally. Do NOT leave headers in English if the input is in another language, and do NOT translate them to Japanese/English if the input is in a third language.
4. **Examples Localization**: Locally adapt all names, currency units, and business terminology in the instructions to match the detected language's cultural context (e.g., use JPY/Japanese names for Japanese, EUR/European names for German/French, USD/English names for English).

Requirements for the Structured Output:
1.  **Structure Integrity**: Ensure the output contains exactly the four translated Markdown headers defined above.
    - **Header 1 (Title)**: If the input already has a company name and industry (e.g., '# SMCC (Finance)'), KEEP and preserve it. If not, create a realistic company name and vertical appropriate to the language context.
    - ${header2Instruction}
    - **Header 3 (Scenario)**: Provide a rich, realistic business context. If the input already has a scenario, expand it with realistic domain details, KPIs, and background.
    - **Header 4 (Challenge)**: Describe a clear, high-value operational challenge for an autonomous AI agent. It MUST specify:
        - A clear trigger event.
        - Explicit business rules and numeric thresholds appropriate to the domain (e.g., CPA limit, price discrepancy threshold).
        - Clear conditional paths (what is auto-process vs. what requires human approval).
        - Data systems involved (BigQuery/external files, Firestore operational database, Google Sheets).
        - **Cross-Departmental Span (MANDATORY)**: The operational challenge MUST span at least two departments that share the same core-system data, and describe the hand-off between them that the agent automates. Where the business problem plausibly involves only one department, model the hand-off with an adjacent supporting function (e.g., support -> billing, support -> product quality).
        - **High-fidelity Assets & Multi-modal Integration**: Intelligently design the challenge to utilize the platform's asset generation capabilities:
            1. **Visual/HITL Triggers**: If the workflow involves any paper forms, manual applications, receipts, shipping box damages, visual inspection anomalies, or legacy physical processes, explicitly mandate a **JPEG image asset** (e.g. handwritten fax order, scanned invoice, damaged package photograph) as the primary trigger, requiring the agent to use multimodal vision before routing to Firestore for Human-in-the-Loop (HITL) manager approval.
            2. **Structured Ledgers**: Integrate transactional logs, excel data dumps, or raw CSV exports as **Excel/CSV/TSV files** that the agent must parse (using TSV/CSV delimiter logic) and reconcile against the DB.
            3. **Executive Reports & Interactive Cards**: Design the workflow to output professional, structured reports (saved to the operational database/Firestore) and rich interactive UI cards (using A2UI) as the final outcome or human review package.
        *NOTE*: If the input already lists target workflows or specific steps, respect them and build the operational challenge specifically around those workflows.
2.  **Operational/Database Focus**: ALWAYS frame the scenario as a database-driven workflow where the agent reads from analytical sources (BigQuery/external files) and **writes back status updates, high-risk alerts, or proposed changes to the operational database (Firestore)** to keep the real-time console updated.
3.  **No Fictional Placeholders**: Use realistic brand names, locations, and values appropriate to the language context. Do NOT use generic placeholders like \"Product A\", \"Company XYZ\", etc.${managedAgentRequirement}${personaRequirement}

Return ONLY the raw Markdown text in the detected language. Do not include any code block wrappers (triple backticks), code fences, or preamble.`;

  const payload = {
    contents: [{ role: 'user', parts: [{ text: prompt }] }],
    generationConfig: { temperature: 0.4, maxOutputTokens: 8192 }
  };

  const fetchOptions = {
    method: 'POST',
    contentType: 'application/json',
    headers: { 'Authorization': 'Bearer ' + ScriptApp.getOAuthToken() },
    payload: JSON.stringify(payload),
    muteHttpExceptions: true
  };

  let response;
  let lastError;
  const maxRetries = 3;
  let delayMs = 1000;

  for (let i = 0; i < maxRetries; i++) {
    try {
      response = UrlFetchApp.fetch(url, fetchOptions);
      const code = response.getResponseCode();
      if (code === 200) {
        const result = JSON.parse(response.getContentText()).candidates[0].content.parts[0].text;
        return { success: true, optimizedGoal: result.trim() };
      }
      
      lastError = new Error(`AI Optimization API Error (HTTP ${code}): ${response.getContentText()}`);
      
      // Only retry on transient errors (429 Rate Limit, 5xx Server Errors)
      if (code !== 429 && code < 500) {
        break; // Fatal error (400, 403, etc.), don't retry
      }
    } catch (e) {
      lastError = e;
    }
    
    if (i < maxRetries - 1) {
      Utilities.sleep(delayMs);
      delayMs *= 2; // Exponential backoff
    }
  }

  return { success: false, error: lastError ? lastError.message : "AI Optimization failed after retries" };
}


/**
 * Translates Template Hub entries into a target language for display.
 * Ported from GE Demo Generator Lite: the frontend ships English-only data
 * and asks the backend for translations on demand, so non-ASCII translations
 * never live in the inline frontend JS (which would break the GAS minifier).
 * Entries with an empty "text" are category labels (industries/job functions).
 * @param {string} lang - Target language code (en/ja/de/fr/es/it/zh/ko/pt/ru/nl/sv/fi)
 * @param {Array} items - [{ label, text }]
 * @returns {Object} { success, items } same length/order translated; originals on failure.
 */
function translateTemplates(lang, items) {
  const LANGS = {
    en: 'English', ja: 'Japanese', de: 'German', fr: 'French', es: 'Spanish',
    it: 'Italian', zh: 'Simplified Chinese', ko: 'Korean', pt: 'Portuguese',
    ru: 'Russian', nl: 'Dutch', sv: 'Swedish', fi: 'Finnish'
  };
  const target = LANGS[lang];
  if (!target || lang === 'en') return { success: true, items: items || [] };
  if (!items || !items.length) return { success: true, items: [] };

  const prompt =
    'Translate the "label" and "text" of each entry below into ' + target + '. ' +
    'Keep it natural and professional (business demo scenario titles, descriptions, and category names). ' +
    'Entries with an empty "text" are category labels - translate only their "label" and keep "text" as an empty string. ' +
    'Return ONLY a JSON array of objects with "label" and "text", in the SAME order and SAME length as the input. ' +
    'Do not add or remove entries.\n\nINPUT:\n' +
    JSON.stringify(items.map(function (i) { return { label: String(i.label || ''), text: String(i.text || '') }; }));

  try {
    const location = CONFIG.LOCATION || 'global';
    const host = location === 'global' ? 'aiplatform.googleapis.com' : location + '-aiplatform.googleapis.com';
    const model = 'gemini-3.5-flash-lite';
    const url = 'https://' + host + '/v1/projects/' + CONFIG.PROJECT_ID + '/locations/' + location + '/publishers/google/models/' + model + ':generateContent';
    const payload = {
      contents: [{ role: 'user', parts: [{ text: prompt }] }],
      generationConfig: { temperature: 0.2, maxOutputTokens: 65535 }
    };
    const response = UrlFetchApp.fetch(url, {
      method: 'POST', contentType: 'application/json',
      headers: { 'Authorization': 'Bearer ' + ScriptApp.getOAuthToken() },
      payload: JSON.stringify(payload), muteHttpExceptions: true
    });
    if (response.getResponseCode() !== 200) throw new Error('Translate Error: ' + response.getContentText().substring(0, 200));
    const candidate = JSON.parse(response.getContentText()).candidates[0];
    const text = candidate.content.parts.filter(function (p) { return p.text; }).map(function (p) { return p.text; }).join('');
    let jsonStr = text.replace(/```json\n?/g, '').replace(/```\n?/g, '').trim();
    let arr;
    try {
      arr = JSON.parse(jsonStr);
    } catch (parseErr) {
      const m = jsonStr.match(/\[[\s\S]*\]/);
      if (!m) throw new Error('No JSON array in translation response');
      arr = JSON.parse(m[0]);
    }
    if (!Array.isArray(arr) || arr.length !== items.length) throw new Error('Length mismatch: got ' + (arr && arr.length));
    return { success: true, items: arr };
  } catch (e) {
    console.warn('[TRANSLATE] ' + e.message);
    return { success: false, items: items, error: e.message };
  }
}
