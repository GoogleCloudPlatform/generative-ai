/**
 * Copyright 2025 Google LLC
 *
 * Licensed under the Apache License, Version 2.0 (the "License");
 * you may not use this file except in compliance with the License.
 * You may obtain a copy of the License at
 *
 *     http://www.apache.org/licenses/LICENSE-2.0
 *
 * Unless required by applicable law or agreed to in writing, software
 * distributed under the License is distributed on an "AS IS" BASIS,
 * WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
 * See the License for the specific language governing permissions and
 * limitations under the License.
 */

export const environment = {
  firebase: {
    apiKey: '<your API Key>',
    authDomain: '<your Auth Domain>',
    projectId: '<your Project ID>',
    storageBucket: '<your storageBucket>',
    messagingSenderId: '<your messagingSenderId>',
    appId: '<your appId>',
    measurementId: '<your measurementId>',
  },
  requiredLogin: 'False',
  backendURL: 'http://localhost:8080/api',
  chatbotName: 'My New Agent',
  environment: 'development',
};
