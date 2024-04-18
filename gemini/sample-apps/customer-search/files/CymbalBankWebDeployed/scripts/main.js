import { currentUser } from "./auth.js";

window.onload = function () {
  const userProfileDiv = document.getElementById("userProfile");
  const user = auth.currentUser;
  console.log(user);
  if (user) {
    userProfileDiv.innerHTML = `
      <h1>Welcome, ${user.displayName}</h1>
      <p>Email: ${user.email}</p>
    `;
  } else {
    userProfileDiv.innerHTML = "<p>Please sign in.</p>";
  }
};
