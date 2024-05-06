"use strict";
import {
  auth,
  signIn,
  signUp,
  signOutUser,
  onAuthStateChanged,
} from "./auth.js";
// Function to update input value based on slider
function updateInputValue(sliderId, inputId) {
  document.getElementById(inputId).value =
    document.getElementById(sliderId).value;
}

// Function to update slider value based on input
function updateSliderValue(sliderId, inputId) {
  document.getElementById(sliderId).value =
    document.getElementById(inputId).value;
}

// Function to calculate investment return
function calculateReturn() {
  var investmentAmount = parseFloat(
    document.getElementById("investmentAmount").value,
  );
  var investmentDuration = parseInt(
    document.getElementById("investmentDuration").value,
  );
  var interestRate = parseFloat(document.getElementById("interestRate").value);
  var n = 1; // Compounded annually
  var r = interestRate / 100;
  var futureValue =
    investmentAmount * Math.pow(1 + r / n, n * investmentDuration);

  document.getElementById("result").innerHTML =
    "After " +
    investmentDuration +
    " years, your investment will be worth: ₹" +
    futureValue.toFixed(2);
}

// Function to calculate required investment
function calculateRequiredInvestment() {
  var targetAmount = parseFloat(document.getElementById("targetAmount").value);
  var targetDuration = parseInt(
    document.getElementById("targetDuration").value,
  );
  var targetInterestRate = parseFloat(
    document.getElementById("targetInterestRate").value,
  );
  var n = 1; // Compounded annually
  var r = targetInterestRate / 100;
  var requiredInvestment =
    targetAmount / Math.pow(1 + r / n, n * targetDuration);

  document.getElementById("requiredInvestmentResult").innerHTML =
    "To reach a target amount of ₹" +
    targetAmount.toFixed(2) +
    " in " +
    targetDuration +
    " years, you need to invest: ₹" +
    requiredInvestment.toFixed(2);
}

// Event listeners for Investment Tab
document
  .getElementById("investmentAmount")
  .addEventListener("input", function () {
    updateInputValue("investmentAmount", "investmentAmountInput");
  });
document
  .getElementById("investmentDuration")
  .addEventListener("input", function () {
    updateInputValue("investmentDuration", "investmentDurationInput");
  });
document.getElementById("interestRate").addEventListener("input", function () {
  updateInputValue("interestRate", "interestRateInput");
});

// Event listeners for Target Amount Tab
document.getElementById("targetAmount").addEventListener("input", function () {
  updateInputValue("targetAmount", "targetAmountInput");
});
document
  .getElementById("targetDuration")
  .addEventListener("input", function () {
    updateInputValue("targetDuration", "targetDurationInput");
  });
document
  .getElementById("targetInterestRate")
  .addEventListener("input", function () {
    updateInputValue("targetInterestRate", "targetInterestRateInput");
  });

// Function to switch between tabs
function switchTabs(tab) {
  if (tab === "investment") {
    document.getElementById("investmentTab").style.display = "block";
    document.getElementById("targetAmountTab").style.display = "none";
  } else if (tab === "targetAmount") {
    document.getElementById("investmentTab").style.display = "none";
    document.getElementById("targetAmountTab").style.display = "block";
  }
}
