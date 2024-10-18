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

const LOCATION = 'asia-northeast1';
const IMAGEN_MODEL = 'imagen-3.0-fast-generate-001';
const GEMINI_MODEL = 'gemini-1.5-flash';

const PROP_KEY = {
  OAUTH_CLIENT_ID: 'client_id',
  OAUTH_CLIENT_SECRET: 'client_secret',
  DRIVE_FOLDER_ID: 'folder_id',
};

/**
 * Gets Google Cloud Project Number from OAuth Client ID stored in Document Properties.
 * @private
 * @returns Google Cloud Project Number.
 */
function getProjectNumber_() {
  return PropertiesService.getDocumentProperties()
    .getProperty(PROP_KEY.OAUTH_CLIENT_ID)
    ?.split('-')[0];
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
  const clientID = PropertiesService.getDocumentProperties().getProperty(
    PROP_KEY.OAUTH_CLIENT_ID,
  );
  const clientSecret = PropertiesService.getDocumentProperties().getProperty(
    PROP_KEY.OAUTH_CLIENT_SECRET,
  );
  if (clientID && clientSecret) {
    return getGoogleService_().getAuthorizationUrl();
  }
  return undefined;
}

/**
 * Callback function called after authorization.
 * @param request Request object
 * @returns HTML output for the new tab
 */
// eslint-disable-next-line @typescript-eslint/no-unused-vars
function authCallback(request: object) {
  const isAuthorized = getGoogleService_().handleCallback(request);
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
  PropertiesService.getDocumentProperties().setProperty(
    PROP_KEY.OAUTH_CLIENT_ID,
    val,
  );
}

/**
 * Sets OAuth Client Secret to Document Properties.
 * @param val OAuth Client Secret
 */
// eslint-disable-next-line @typescript-eslint/no-unused-vars
function setClientSecret(val: string) {
  PropertiesService.getDocumentProperties().setProperty(
    PROP_KEY.OAUTH_CLIENT_SECRET,
    val,
  );
}

/**
 * Asks Gemini for a response based on a provided context and input.
 * @param {string} instruction An instruction that describes the task.
 * @param {string} input The input data to process based on the instruction.
 * @param {string[][]} context The context that LLM should be aware of.
 * @return {string} The LLM's response, trimmed and ready for use in a spreadsheet cell.
 * @customFunction
 */
// eslint-disable-next-line @typescript-eslint/no-unused-vars
function HEY_LLM(instruction: string, input: string, context: string[][] = []) {
  const prompt = `
## Instruction
${instruction}

## Context (CSV formatted)
${context ? context.map(row => row.join(', ')).join('\n') : ''}

## Task
Input: ${input}
Output:`;

  const cache = CacheService.getDocumentCache();
  const cacheKey = `hey_llm:${generateHashValue(prompt)}`;
  const cached = cache?.get(cacheKey);
  if (cached) return cached;

  const oauthService = getGoogleService_();
  const url = `https://${LOCATION}-aiplatform.googleapis.com/v1/projects/${getProjectNumber_()}/locations/${LOCATION}/publishers/google/models/${GEMINI_MODEL}:generateContent`;

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
    throw new Error('no files included in the response');
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
  const uploadRes = UrlFetchApp.fetch(
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
  const uploadResult: {thumbnailLink: string} = JSON.parse(
    uploadRes.getContentText(),
  );
  return uploadResult.thumbnailLink;
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
  const response = UrlFetchApp.fetch(url, {
    headers: {
      Authorization: 'Bearer ' + oauth.getAccessToken(),
    },
  });
  const data: {name: string} = JSON.parse(response.getContentText());
  return data.name;
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
  const response: {id: string} = JSON.parse(res.getContentText());
  return response.id;
}

/**
 * Requests Vertex AI's Imagen to generate an image.
 * @private
 * @param oauth OAuth2 Service
 * @param prompt A prompt for image generation
 * @param seed A seed number
 * @returns Generated result
 */
function requestImagen_(
  oauth: GoogleAppsScriptOAuth2.OAuth2Service,
  prompt: string,
  seed: number,
) {
  const url = `https://${LOCATION}-aiplatform.googleapis.com/v1/projects/${getProjectNumber_()}/locations/${LOCATION}/publishers/google/models/${IMAGEN_MODEL}:predict`;

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
    throw new Error('Request to Imagen failed.');
  }
  return result.predictions[0];
}

/**
 * Generates an image out of a prompt using Vertex AI's Imagen.
 * @param {string} prompt A prompt for image generation
 * @param {number} seed A seed number
 * @return {string} Generated image's URL
 * @customFunction
 */
// eslint-disable-next-line @typescript-eslint/no-unused-vars
function IMAGEN(prompt: string, seed = 1) {
  const cacheKey = generateHashValue(`imagen:${prompt}:${seed}`);
  const cache = CacheService.getDocumentCache();
  const cached = cache?.get(cacheKey);
  if (cached) {
    return cached;
  }
  const oauthService = getGoogleService_();
  let parentFolderID = PropertiesService.getDocumentProperties().getProperty(
    PROP_KEY.DRIVE_FOLDER_ID,
  );
  if (!parentFolderID) {
    parentFolderID = createDriveFolder_(oauthService);
    PropertiesService.getDocumentProperties().setProperty(
      PROP_KEY.DRIVE_FOLDER_ID,
      parentFolderID,
    );
  }
  const filename = sanitizeFileName(`${cacheKey}:${prompt.slice(0, 64)}.png`);
  const driveUrl = checkDriveImage_(oauthService, filename, parentFolderID);
  if (driveUrl) {
    return driveUrl;
  }
  const pred = requestImagen_(oauthService, prompt, seed);
  const thumbnailLink = uploadImageToDrive_(
    oauthService,
    pred.bytesBase64Encoded,
    filename,
    pred.mimeType,
    parentFolderID,
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
function getGoogleService_() {
  const clientID = PropertiesService.getDocumentProperties().getProperty(
    PROP_KEY.OAUTH_CLIENT_ID,
  );
  const clientSecret = PropertiesService.getDocumentProperties().getProperty(
    PROP_KEY.OAUTH_CLIENT_SECRET,
  );
  if (!clientID || !clientSecret) {
    throw new Error(
      'OAuth info is missing. Complete authorization from the "Extensions" menu',
    );
  }

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
