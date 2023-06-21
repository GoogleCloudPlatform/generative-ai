mdc.autoInit();

const MDCTabBar = mdc.tabBar.MDCTabBar;
const MDCTextField = mdc.textField.MDCTextField;

const tabBar = new MDCTabBar(document.querySelector(".mdc-tab-bar"));
const queryTextField = new MDCTextField(
  document.querySelector(".mdc-text-field.query-field")
);
