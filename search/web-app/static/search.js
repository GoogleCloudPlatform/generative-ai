/**
 * Copyright 2023 Google LLC
 * Licensed under the Apache License, Version 2.0 (the "License");
 * you may not use this file except in compliance with the License.
 * You may obtain a copy of the License at
 *
 *    http://www.apache.org/licenses/LICENSE-2.0
 *
 * Unless required by applicable law or agreed to in writing, software
 * distributed under the License is distributed on an "AS IS" BASIS,
 * WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
 * See the License for the specific language governing permissions and
 * limitations under the License.
 */

hljs.highlightAll();
hljs.addPlugin(new CopyButtonPlugin());

mdc.autoInit();

const MDCRipple = mdc.ripple.MDCRipple;
const MDCTextField = mdc.textField.MDCTextField;
const MDCTabBar = mdc.tabBar.MDCTabBar;

MDCRipple.attachTo(document.querySelector(".search-button"));

const queryTextField = new MDCTextField(document.querySelector(".query-field"));
const summaryPreambleTextField = new MDCTextField(document.querySelector(".summary-preamble-field"));
// const documentTypesField = document.querySelector('.mdc-text-field.types-field');

// const select = new MDCSelect(document.querySelector('.mdc-select'));

const jsonTabSelector = document.querySelector("#json-tab-selector");
const entitiesTabSelector = document.querySelector("#entities-tab-selector");

const tabContent = document.querySelector(".tab-content");
const jsonTab = document.querySelector("#json-tab");
const entitiesTab = document.querySelector("#entities-tab");

if (jsonTabSelector) {
  jsonTabSelector.onclick = () => {
    jsonTab.classList.replace("tab-hidden", "tab-visible");
    entitiesTab.classList.replace("tab-visible", "tab-hidden");
    entitiesTab.replaceWith(jsonTab);
  };
}

if (entitiesTabSelector) {
  entitiesTabSelector.onclick = () => {
    entitiesTab.classList.replace("tab-hidden", "tab-visible");
    jsonTab.classList.replace("tab-visible", "tab-hidden");
    jsonTab.replaceWith(entitiesTab);
  };
}

const imageInput = document.getElementById("image-input");

if (imageInput) {
  imageInput.addEventListener("change", function (e) {
    const fileInput = e.target;
    const fileUploadLabel = document.getElementById("file-upload-label");
    if (fileInput.files.length > 0) {
      fileUploadLabel.textContent = fileInput.files[0].name;
    } else {
      fileUploadLabel.textContent = "No file selected";
    }
  });
}

const searchEngine0Radio = document.getElementById("search-engine-0");
// Default - Uses Advanced Indexing
const searchEngine1Radio = document.getElementById("search-engine-1");

const summaryModelRadioSelector = document.querySelector(".summary-model-radio");
const summaryPreambleSelector = document.querySelector(".summary-preamble-field");

function toggleElement(element, show) {
  if (show) {
    element.style.display = "block";
  } else {
    element.style.display = "none";
  }
}

// Add event listeners to radio buttons
searchEngine0Radio.addEventListener("change", function () {
  if (searchEngine0Radio.checked) {
    toggleElement(summaryModelRadioSelector, false);
    toggleElement(summaryPreambleSelector, false);
  }
});

searchEngine1Radio.addEventListener("change", function () {
  if (searchEngine1Radio.checked) {
    toggleElement(summaryModelRadioSelector, true);
    toggleElement(summaryPreambleSelector, true);
  }
});
