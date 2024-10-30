/**
 * @license
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

import type {GenerateContentResponse} from '@google-cloud/vertexai';

/**
 * Vertex AI location. Change this const if you want to use another location.
 */
const LOCATION = 'asia-northeast1';

/**
 * Default Gemini model to use.
 */
const DEFAULT_GEMINI_MODEL = 'gemini-1.5-flash';

/**
 * Default Imagen model to use.
 */
const DEFAULT_IMAGEN_MODEL = 'imagen-3.0-fast-generate-001';

/**
 * Preset OAuth Client ID. If null, users must enter it in the sidebar.
 */
const PRESET_OAUTH_CLIENT_ID = null;

/**
 * Preset OAuth Client Secret. If null, users must enter it in the sidebar.
 */
const PRESET_OAUTH_CLIENT_SECRET = null;

/**
 * Preset Google Drive Folder ID to store generated images.
 * If null, a new folder will be created.
 */
const PRESET_DRIVE_FOLDER_ID = null;

/**
 * Property service middleware.
 * - If the value is preset, always returns it. The value is not writable.
 * - Otherwise, reads from / write to GAS PropertiesService.
 */
class PropService {
  static OAUTH_CLIENT_ID_KEY = 'client_id';
  static OAUTH_CLIENT_SECRET_KEY = 'client_secret';
  static DRIVE_FOLDER_ID_KEY = 'folder_id';

  /** OAuth Client ID */
  static get clientID() {
    return PRESET_OAUTH_CLIENT_ID
      ? PRESET_OAUTH_CLIENT_ID
      : PropertiesService.getDocumentProperties().getProperty(
          PropService.OAUTH_CLIENT_ID_KEY,
        );
  }

  static set clientID(value) {
    if (PRESET_OAUTH_CLIENT_ID) return;
    if (!value) return;
    PropertiesService.getDocumentProperties().setProperty(
      PropService.OAUTH_CLIENT_ID_KEY,
      value,
    );
  }

  /** OAuth Client Secret */
  static get clientSecret() {
    return PRESET_OAUTH_CLIENT_SECRET
      ? PRESET_OAUTH_CLIENT_SECRET
      : PropertiesService.getDocumentProperties().getProperty(
          PropService.OAUTH_CLIENT_SECRET_KEY,
        );
  }

  static set clientSecret(value) {
    if (PRESET_OAUTH_CLIENT_SECRET) return;
    if (!value) return;
    PropertiesService.getDocumentProperties().setProperty(
      PropService.OAUTH_CLIENT_SECRET_KEY,
      value,
    );
  }

  /** Google Drive Folder ID to store generated images */
  static get driveFolderID() {
    return PRESET_DRIVE_FOLDER_ID
      ? PRESET_DRIVE_FOLDER_ID
      : PropertiesService.getDocumentProperties().getProperty(
          PropService.DRIVE_FOLDER_ID_KEY,
        );
  }

  static set driveFolderID(value) {
    if (PRESET_DRIVE_FOLDER_ID) return;
    if (!value) return;
    PropertiesService.getDocumentProperties().setProperty(
      PropService.DRIVE_FOLDER_ID_KEY,
      value,
    );
  }
}

// eslint-disable-next-line @typescript-eslint/no-unused-vars
function isOAuthClientPreset() {
  return PRESET_OAUTH_CLIENT_ID && PRESET_OAUTH_CLIENT_SECRET;
}

/**
 * Gets Google Cloud Project Number from OAuth Client ID stored in Document Properties.
 * @private
 * @returns Google Cloud Project Number.
 */
function getProjectNumber_() {
  return PropService.clientID?.split('-')[0];
}

/**
 * Generates a hash value for the given value.
 * @param value Source value
 * @returns Generated hash value
 */
function generateHashValue(value: string) {
  const hash = Utilities.computeDigest(
    Utilities.DigestAlgorithm.SHA_256,
    value,
  );
  return hash
    .map(byte => ((byte & 0xff) + 0x100).toString(16).slice(1))
    .join('');
}

/**
 * Runs when the document is opened, creating the add-on's menu.
 */
// eslint-disable-next-line @typescript-eslint/no-unused-vars
function onOpen() {
  SpreadsheetApp.getUi()
    .createAddonMenu()
    .addItem('Use in this spreadsheet', 'use')
    .addToUi();
}

/**
 * Enables the add-on on for the current spreadsheet with authorization.
 */
// eslint-disable-next-line @typescript-eslint/no-unused-vars
function use() {
  const template = HtmlService.createTemplateFromFile('sidebar.html');
  const page = template.evaluate();
  page.setTitle('HEY_LLM');
  return SpreadsheetApp.getUi().showSidebar(page);
}

/**
 * Gets authorization URL if OAuth Client ID / Secret is available in Script Properties.
 * @returns Authorization URL
 */
// eslint-disable-next-line @typescript-eslint/no-unused-vars
function getAuthorizationUrl() {
  const clientID = PropService.clientID;
  const clientSecret = PropService.clientSecret;
  if (!clientID || !clientSecret) return null;
  return getGoogleService_(clientID, clientSecret).getAuthorizationUrl();
}

/**
 * Callback function called after authorization.
 * @param request Request object
 * @returns HTML output for the new tab
 */
// eslint-disable-next-line @typescript-eslint/no-unused-vars
function authCallback(request: object) {
  const clientID = PropService.clientID;
  const clientSecret = PropService.clientSecret;
  if (!clientID || !clientSecret) {
    return HtmlService.createHtmlOutput('Client ID / Secret not set.');
  }
  const isAuthorized = getGoogleService_(clientID, clientSecret).handleCallback(
    request,
  );
  if (isAuthorized) {
    return HtmlService.createHtmlOutput('Success! You can close this tab.');
  } else {
    return HtmlService.createHtmlOutput('Denied. You can close this tab');
  }
}

/**
 * Sets OAuth Client ID to Document Properties.
 * @param val OAuth Client ID
 */
// eslint-disable-next-line @typescript-eslint/no-unused-vars
function setClientID(val: string) {
  PropService.clientID = val;
}

/**
 * Sets OAuth Client Secret to Document Properties.
 * @param val OAuth Client Secret
 */
// eslint-disable-next-line @typescript-eslint/no-unused-vars
function setClientSecret(val: string) {
  PropService.clientSecret = val;
}

/**
 * Asks Gemini for a response based on a provided context and input.
 * @param {string} instruction An instruction that describes the task.
 * @param {string} input The input data to process based on the instruction.
 * @param {string[][]} context Optional context that LLM should be aware of.
 *   You can specify a cell range that includes examples, reference data, etc.
 * @param {string} model The Gemini model version to use (default: gemini-1.5-flash).
 *   See https://cloud.google.com/vertex-ai/generative-ai/docs/learn/models for available models.
 * @return {string} The LLM's response, trimmed and ready for use in a spreadsheet cell.
 * @customFunction
 */
// eslint-disable-next-line @typescript-eslint/no-unused-vars
function HEY_LLM(
  instruction: string,
  input: string,
  context: string[][] = [],
  model = DEFAULT_GEMINI_MODEL,
) {
  const prompt = `
## Instruction
${instruction}

${context ? '## Context (CSV formatted)\n' + context.map(row => row.join(', ')).join('\n') : ''}

## Task
Input: ${input}
Output:`;

  const cache = CacheService.getDocumentCache();
  const cacheKey = `hey_llm:${generateHashValue(prompt)}:${model}`;
  const cached = cache?.get(cacheKey);
  if (cached) return cached;

  const clientID = PropService.clientID;
  const clientSecret = PropService.clientSecret;
  if (!clientID || !clientSecret) {
    throw new Error('OAuth client ID / Secret not set.');
  }
  const oauthService = getGoogleService_(clientID, clientSecret);
  const url = `https://${LOCATION}-aiplatform.googleapis.com/v1/projects/${getProjectNumber_()}/locations/${LOCATION}/publishers/google/models/${model}:generateContent`;

  const payload = JSON.stringify({
    contents: [
      {
        role: 'user',
        parts: [
          {
            text: prompt,
          },
        ],
      },
    ],
    systemInstruction: {
      parts: [
        {
          text: 'The response is to be used in side a spreadsheet cell and needs to be concise. Just show the answer only.',
        },
      ],
    },
  });
  const res = UrlFetchApp.fetch(url, {
    method: 'post',
    headers: {
      Authorization: 'Bearer ' + oauthService.getAccessToken(),
    },
    contentType: 'application/json',
    payload: payload,
    muteHttpExceptions: true,
  });
  const result: GenerateContentResponse = JSON.parse(res.getContentText());
  if (!(result.candidates && result.candidates[0].content.parts[0].text)) {
    Logger.log(result);
    throw new Error('Request to Gemini failed. ' + res.getContentText());
  }
  const out = result.candidates[0].content.parts[0].text.trim();
  cache?.put(cacheKey, out);
  return out;
}

/**
 * Removes invalid characters from the file name.
 * @param filename Source file name
 * @returns Sanitized file name
 */
function sanitizeFileName(filename: string) {
  return filename.replace(/[/\\?%*:|'"<>]/g, '_');
}

/**
 * Gets a thumbnail URL for the image file if available in the parent Drive folder.
 * @private
 * @param oauth OAuth2 Service
 * @param filename Image file name to check
 * @param parentFolderID Parent Drive folder to check
 * @returns Thumbnail URL if available
 */
function checkDriveImage_(
  oauth: GoogleAppsScriptOAuth2.OAuth2Service,
  filename: string,
  parentFolderID: string,
) {
  const q = encodeURI(
    `name = '${filename}' and '${parentFolderID}' in parents`,
  );
  const url = `https://www.googleapis.com/drive/v3/files?q=${q}&fields=files(id,name,thumbnailLink)`;
  const res = UrlFetchApp.fetch(url, {
    method: 'get',
    headers: {
      Authorization: 'Bearer ' + oauth.getAccessToken(),
    },
    muteHttpExceptions: true,
  });
  const response: {
    files?: {id: string; name: string; thumbnailLink: string}[];
  } = JSON.parse(res.getContentText());

  if (!response.files) {
    Logger.log(response);
    throw new Error(
      'No files included in the response. ' + res.getContentText(),
    );
  }

  if (response.files.length > 0) {
    return response.files[0].thumbnailLink;
  }
  return undefined;
}

/**
 * Uploads image to Drive.
 * @private
 * @param oauth OAuth2 Service
 * @param base64image Base 64 encoded image string
 * @param filename Image file name
 * @param mimeType Image MIME type
 * @param parentFolderID Parent Drive folder to upload the image
 * @returns Thumbnail URL for the uploaded image
 */
function uploadImageToDrive_(
  oauth: GoogleAppsScriptOAuth2.OAuth2Service,
  base64image: string,
  filename: string,
  mimeType: string,
  parentFolderID: string,
) {
  const metadata = {
    name: filename,
    mimeType: mimeType,
    parents: [parentFolderID],
  };
  const boundary = 'UploadImageRequestBoundary';
  const payload = `--${boundary}
Content-Type: application/json; charset=UTF-8

${JSON.stringify(metadata)}

--${boundary}
Content-Type: ${mimeType}
Content-Transfer-Encoding: base64

${base64image}

--${boundary}--`;
  const res = UrlFetchApp.fetch(
    'https://www.googleapis.com/upload/drive/v3/files?uploadType=multipart&fields=thumbnailLink',
    {
      method: 'post',
      headers: {
        Authorization: 'Bearer ' + oauth.getAccessToken(),
        'Content-Type': `multipart/related; boundary=${boundary}`,
      },
      payload: payload,
      muteHttpExceptions: true,
    },
  );
  const result: {thumbnailLink?: string} = JSON.parse(res.getContentText());
  if (!result.thumbnailLink) {
    Logger.log(payload, result);
    throw new Error(
      'Uploading image to Drive failed. Is Drive API enabled? ' +
        res.getContentText(),
    );
  }
  return result.thumbnailLink;
}

/**
 * Gets the current GAS script ID.
 * @returns The script ID
 */
// eslint-disable-next-line @typescript-eslint/no-unused-vars
function getScriptId() {
  return ScriptApp.getScriptId();
}

/**
 * Gets the GAS project name which this script belongs to.
 * @private
 * @param oauth OAuth2 Service
 * @returns The script name
 */
function getScriptName_(oauth: GoogleAppsScriptOAuth2.OAuth2Service) {
  const scriptId = ScriptApp.getScriptId();
  const url = `https://www.googleapis.com/drive/v3/files/${scriptId}?fields=name`;
  const res = UrlFetchApp.fetch(url, {
    headers: {
      Authorization: 'Bearer ' + oauth.getAccessToken(),
    },
  });
  const result: {name?: string} = JSON.parse(res.getContentText());
  if (!result.name) {
    Logger.log(result);
    throw new Error(
      'Request to Drive failed. Is Drive API enabled? ' + res.getContentText(),
    );
  }
  return result.name;
}

/**
 * Creates a Drive folder for the GAS project.
 * @private
 * @param oauth OAuth2 Service
 * @returns ID for the created Drive folder
 */
function createDriveFolder_(oauth: GoogleAppsScriptOAuth2.OAuth2Service) {
  const metadata = {
    name: `Generated images for: ${getScriptName_(oauth)}`,
    mimeType: 'application/vnd.google-apps.folder',
    parents: ['root'],
  };
  const payload = JSON.stringify(metadata);
  const res = UrlFetchApp.fetch('https://www.googleapis.com/drive/v3/files', {
    method: 'post',
    headers: {
      Authorization: 'Bearer ' + oauth.getAccessToken(),
      'Content-Type': 'application/json',
    },
    payload: payload,
    muteHttpExceptions: true,
  });
  const result: {id?: string} = JSON.parse(res.getContentText());
  if (!result.id) {
    Logger.log(payload, result);
    throw new Error(
      'Creating a Driver folder failed. Is Drive API enabled? ' +
        res.getContentText(),
    );
  }
  return result.id;
}

/**
 * Requests Vertex AI's Imagen to generate an image.
 * @private
 * @param oauth OAuth2 Service
 * @param prompt A prompt for image generation
 * @param seed A seed number
 * @param {string} model The Imagen model version to use
 * @returns Generated result
 */
function requestImagen_(
  oauth: GoogleAppsScriptOAuth2.OAuth2Service,
  prompt: string,
  seed: number,
  model: string,
) {
  const url = `https://${LOCATION}-aiplatform.googleapis.com/v1/projects/${getProjectNumber_()}/locations/${LOCATION}/publishers/google/models/${model}:predict`;

  const payload = JSON.stringify({
    instances: [
      {
        prompt: prompt,
      },
    ],
    parameters: {
      seed,
      sampleCount: 1,
      addWatermark: false,
      safetySetting: 'block_few',
      language: 'auto',
    },
  });
  const res = UrlFetchApp.fetch(url, {
    method: 'post',
    headers: {
      Authorization: 'Bearer ' + oauth.getAccessToken(),
    },
    contentType: 'application/json',
    payload: payload,
    muteHttpExceptions: true,
  });
  const result: {
    predictions?: {
      bytesBase64Encoded: string;
      mimeType: string;
    }[];
  } = JSON.parse(res.getContentText());
  if (!result.predictions) {
    Logger.log(payload, result);
    throw new Error('Request to Vertex AI failed. ' + res.getContentText());
  }
  return result.predictions[0];
}

/**
 * Generates an image out of a prompt using Vertex AI's Imagen.
 * @param {string} prompt A prompt for image generation
 * @param {number} seed A seed number
 * @param {string} model The Imagen model version to use (default: imagen-3.0-fast-generate-001).
 *   See https://cloud.google.com/vertex-ai/generative-ai/docs/image/generate-images for available models.
 * @return {string} Generated image's URL
 * @customFunction
 */
// eslint-disable-next-line @typescript-eslint/no-unused-vars
function IMAGEN(prompt: string, seed = 1, model = DEFAULT_IMAGEN_MODEL) {
  const cacheKey = generateHashValue(`imagen:${prompt}:${seed}:${model}`);
  const cache = CacheService.getDocumentCache();
  const cached = cache?.get(cacheKey);
  if (cached) {
    return cached;
  }
  const clientID = PropService.clientID;
  const clientSecret = PropService.clientSecret;
  if (!clientID || !clientSecret) {
    throw new Error('OAuth client ID / Secret not set.');
  }
  const oauthService = getGoogleService_(clientID, clientSecret);
  if (!PropService.driveFolderID) {
    PropService.driveFolderID = createDriveFolder_(oauthService);
  }
  const filename = sanitizeFileName(`${cacheKey}:${prompt.slice(0, 64)}.png`);
  const driveUrl = checkDriveImage_(
    oauthService,
    filename,
    PropService.driveFolderID,
  );
  if (driveUrl) {
    return driveUrl;
  }
  const pred = requestImagen_(oauthService, prompt, seed, model);
  const thumbnailLink = uploadImageToDrive_(
    oauthService,
    pred.bytesBase64Encoded,
    filename,
    pred.mimeType,
    PropService.driveFolderID,
  );

  // Trim resize parameters that comes after the equal mark.
  const url =
    thumbnailLink.indexOf('=') > -1
      ? thumbnailLink.split('=').slice(0, -1).join('')
      : thumbnailLink;
  cache?.put(cacheKey, url);
  return url;
}

/**
 * A utility function to generate OAuth2 service.
 * Copied from https://github.com/googleworkspace/apps-script-oauth2#1-create-the-oauth2-service
 * @private
 * @returns OAuth2 service
 */
function getGoogleService_(clientID: string, clientSecret: string) {
  // Create a new service with the given name. The name will be used when
  // persisting the authorized token, so ensure it is unique within the
  // scope of the property store.
  return (
    OAuth2.createService('google')

      // Set the endpoint URLs, which are the same for all Google services.
      .setAuthorizationBaseUrl('https://accounts.google.com/o/oauth2/auth')
      .setTokenUrl('https://accounts.google.com/o/oauth2/token')

      // Set the client ID and secret, from the Google Developers Console.
      .setClientId(clientID)
      .setClientSecret(clientSecret)

      // Set the name of the callback function in the script referenced
      // above that should be invoked to complete the OAuth flow.
      .setCallbackFunction('authCallback')

      // Set the property store where authorized tokens should be persisted.
      .setPropertyStore(PropertiesService.getDocumentProperties())
      .setCache(CacheService.getDocumentCache()!)
      .setLock(LockService.getDocumentLock())

      // Set the scopes to request (space-separated for Google services).
      .setScope([
        'https://www.googleapis.com/auth/drive',
        'https://www.googleapis.com/auth/cloud-platform',
      ])

      // Below are Google-specific OAuth2 parameters.

      // Sets the login hint, which will prevent the account chooser screen
      // from being shown to users logged in with multiple accounts.
      //.setParam('login_hint', Session.getEffectiveUser().getEmail())

      // Requests offline access.
      .setParam('access_type', 'offline')

      // Consent prompt is required to ensure a refresh token is always
      // returned when requesting offline access.
      .setParam('prompt', 'consent')
  );
}
