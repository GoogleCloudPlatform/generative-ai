import { initializeApp } from "https://www.gstatic.com/firebasejs/10.7.0/firebase-app.js";
import {
  getAuth,
  onAuthStateChanged,
  signOut,
  createUserWithEmailAndPassword,
  signInWithEmailAndPassword,
  // connectAuthEmulator
} from "https://www.gstatic.com/firebasejs/10.7.0/firebase-auth.js";

const firebaseConfig = {
  apiKey: "{{apiKey}}",
  authDomain: "{{authDomain}}",
  projectId: "{{projectId}}",
  storageBucket: "{{storageBucket}}",
  messagingSenderId: "{{messagingSenderId}}",
  appId: "{{appId}}",
  measurementId: "{{measurementId}}",
};
// Initialize Firebase
const app = initializeApp(firebaseConfig);

// Initialize Firebase Authentication and get a reference to the service
const auth = getAuth(app);

function handleError(error) {
  var errorCode = error.code;
  var errorMessage = error.message;
  console.log(errorCode, errorMessage);
  throw error;
  return false;
}
function currentUser() {
  const user = auth.currentUser;
  console.log(user);
  if (user) {
    return user;
  } else {
    return null;
  }
}

async function signUp(email, password) {
  console.log("signUp called");
  await createUserWithEmailAndPassword(auth, email, password)
    .then((userCredential) => {
      var user = userCredential.user;
      console.log("signup successful!");
      console.log(user);
      window.location.href = "/";
      return true;
    })
    .catch((error) => {
      handleError(error);
    });
}

async function signIn(email, password) {
  console.log("signIn called");
  await signInWithEmailAndPassword(auth, email, password)
    .then((userCredential) => {
      // Signed in

      var user = userCredential.user;
      console.log("signin successful!");
      console.log(user);
      window.location.href = "/";
      return true;
    })
    .catch((error) => {
      handleError(error);
    });
}

async function signOutUser() {
  await signOut(auth)
    .then(() => {
      console.log("signout successful!");
    })
    .catch((error) => {
      console.log(error);
      throw error;
    });
}

export { auth, currentUser, signUp, signIn, signOutUser, onAuthStateChanged };
