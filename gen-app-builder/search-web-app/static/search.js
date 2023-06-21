hljs.highlightAll();

mdc.autoInit();

const MDCRipple = mdc.ripple.MDCRipple;
const MDCTextField = mdc.textField.MDCTextField;
const MDCTabBar = mdc.tabBar.MDCTabBar;

MDCRipple.attachTo(document.querySelector(".search-button"));

const queryTextField = new MDCTextField(document.querySelector(".query-field"));

// const documentTypesField = document.querySelector('.mdc-text-field.types-field');

// const select = new MDCSelect(document.querySelector('.mdc-select'));

const jsonTabSelector = document.querySelector("#json-tab-selector");
const entitiesTabSelector = document.querySelector("#entities-tab-selector");

const tabContent = document.querySelector(".tab-content");
const jsonTab = document.querySelector("#json-tab");
const entitiesTab = document.querySelector("#entities-tab");

jsonTabSelector.onclick = () => {
  jsonTab.classList.replace("tab-hidden", "tab-visible");
  entitiesTab.classList.replace("tab-visible", "tab-hidden");
  entitiesTab.replaceWith(jsonTab);
};

entitiesTabSelector.onclick = () => {
  entitiesTab.classList.replace("tab-hidden", "tab-visible");
  jsonTab.classList.replace("tab-visible", "tab-hidden");
  jsonTab.replaceWith(entitiesTab);
};
const tabBar = new MDCTabBar(document.querySelector(".mdc-tab-bar"));
