"use strict";
import {
  auth,
  signIn,
  signUp,
  signOutUser,
  onAuthStateChanged,
} from "./auth.js";

const modal = document.querySelector(".modal");
const overlay = document.querySelector(".overlay");
const btnCloseModal = document.querySelector(".btn--close-modal");
const btnsOpenModal = document.querySelectorAll(".btn--show-modal");
const btnCreateAcc = document.querySelector(".slide-button");

const loginBtn = document.getElementById("login_menu_btn");
const logoutBtn = document.getElementById("logout_menu_btn");

const header = document.querySelector(".header");
const message = document.createElement("div");
const footer_signup = document.querySelector(".section--sign-up");

const btnScrollTo = document.querySelector(".btn--scroll-to");
const section1 = document.querySelector("#section--1");

const operationsTabs = document.querySelectorAll(".operations__tab");
const operationsTabsContainer = document.querySelector(
  ".operations__tab-container",
);
const operationsTabsContent = document.querySelectorAll(".operations__content");

const authenticateTabs = document.querySelectorAll(".authenticate__tab");
const authenticateTabsContainer = document.querySelector(
  ".authenticate__tab-container",
);
const authenticateTabsContent = document.querySelectorAll(
  ".authenticate__content",
);

const nav = document.querySelector("nav");

const navHeight = nav.getBoundingClientRect().height;

let navbar = document.querySelector(".navbar");
// sidebar open close js code
let navLinks = document.querySelector(".nav-links");
let menuOpenBtn = document.querySelector(".navbar .bx-menu");
let menuCloseBtn = document.querySelector(".nav-links .bx-x");
menuOpenBtn.onclick = function () {
  navLinks.style.left = "0";
};
menuCloseBtn.onclick = function () {
  navLinks.style.left = "-100%";
};
// sidebar submenu open close js code
let payArrow = document.querySelector(".pay-arrow");
payArrow.onclick = function () {
  navLinks.classList.toggle("show4");
};
let moneytransferArrow = document.querySelector(".moneytransfer-arrow");
moneytransferArrow.onclick = function () {
  navLinks.classList.toggle("show9");
};
let billssArrow = document.querySelector(".bills-arrow");
billssArrow.onclick = function () {
  navLinks.classList.toggle("show11");
};

let saveArrow = document.querySelector(".save-arrow");
saveArrow.onclick = function () {
  navLinks.classList.toggle("show5");
};
let accountsArrow = document.querySelector(".accounts-arrow");
accountsArrow.onclick = function () {
  navLinks.classList.toggle("show12");
};
let depositsArrow = document.querySelector(".deposits-arrow");
depositsArrow.onclick = function () {
  navLinks.classList.toggle("show13");
};

let investArrow = document.querySelector(".invest-arrow");
investArrow.onclick = function () {
  navLinks.classList.toggle("show6");
};

let borrowArrow = document.querySelector(".borrow-arrow");
borrowArrow.onclick = function () {
  navLinks.classList.toggle("show8");
};

// Modal window
const openModal = function (e) {
  e.preventDefault();
  modal.classList.remove("hidden");
  overlay.classList.remove("hidden");
};

const openModalCreateAccount = function (e) {
  e.preventDefault();
  modal.classList.remove("hidden");
  overlay.classList.remove("hidden");

  // Get the "CREATE ACCOUNT" button element
  const createAccountButton = document.querySelector(".authenticate__tab--2");

  // Set the active class on the button and the corresponding content
  createAccountButton.classList.add("authenticate__tab--active");

  // Find the content with matching data-tab and activate it
  const createAccountContent = document.querySelector(
    ".authenticate__content--2",
  );
  createAccountContent.classList.add("authenticate__content--active");

  // Deactivate the currently active tab and content
  const activeTab = document.querySelector(".authenticate__tab--active");
  if (activeTab !== createAccountButton) {
    activeTab.classList.remove("authenticate__tab--active");
  }
  const activeContent = document.querySelector(
    ".authenticate__content--active",
  );
  if (activeContent !== createAccountContent) {
    activeContent.classList.remove("authenticate__content--active");
  }
};

const closeModal = function () {
  modal.classList.add("hidden");
  overlay.classList.add("hidden");
};

loginBtn.addEventListener("click", openModal);

if (btnCreateAcc) {
  btnCreateAcc.addEventListener("click", openModalCreateAccount);
}

if (logoutBtn) {
  logoutBtn.addEventListener("click", () => {
    signOutUser();
  });
}

btnCloseModal.addEventListener("click", closeModal);
overlay.addEventListener("click", closeModal);

document.addEventListener("keydown", function (e) {
  if (e.key === "Escape" && !modal.classList.contains("hidden")) {
    closeModal();
  }
});

// Cookie msg
message.classList.add("cookie-message");
message.innerHTML =
  'We use cookies for improved functionality and analytics. <button class="btn btn--close-cookie"> Got it!</button>';
message.style.backgroundColor = "#37383d";
message.style.width = "120%";
message.style.height =
  Number.parseFloat(getComputedStyle(message).height, 10) + 30 + "px";

// Button scrolling
if (btnScrollTo != null) {
  btnScrollTo.addEventListener("click", function () {
    section1.scrollIntoView({ behavior: "smooth" });
  });
}

// Page navigation - event delegation
document.querySelector(".nav-links").addEventListener("click", function (e) {
  e.preventDefault();

  // Matching strategy
  if (e.target.classList.contains("nav__link")) {
    const targetHref = e.target.getAttribute("href");

    if (targetHref != null) {
      if (targetHref.startsWith("#")) {
        const targetElement = document.querySelector(targetHref);
        if (targetElement) {
          targetElement.scrollIntoView({ behavior: "smooth" });
        }
      } else {
        window.location.href = targetHref;
      }
    }
  }
});

// Tabbed component
if (operationsTabsContainer != null) {
  operationsTabsContainer.addEventListener("click", function (e) {
    const clicked = e.target.closest(".operations__tab");

    // Guard clause
    if (!clicked) return;

    // Remove active classes
    operationsTabs.forEach((t) =>
      t.classList.remove("operations__tab--active"),
    );
    operationsTabsContent.forEach((t) =>
      t.classList.remove("operations__content--active"),
    );

    // Active tab
    clicked.classList.add("operations__tab--active");

    // Active content area
    document
      .querySelector(`.operations__content--${clicked.dataset.tab}`)
      .classList.add("operations__content--active");
  });
}

if (authenticateTabsContainer != null) {
  authenticateTabsContainer.addEventListener("click", function (e) {
    const clicked = e.target.closest(".authenticate__tab");

    // Guard clause
    if (!clicked) return;

    // Remove active classes
    authenticateTabs.forEach((t) =>
      t.classList.remove("authenticate__tab--active"),
    );
    authenticateTabsContent.forEach((t) =>
      t.classList.remove("authenticate__content--active"),
    );

    // Active tab
    clicked.classList.add("authenticate__tab--active");

    // Active content area
    document
      .querySelector(`.authenticate__content--${clicked.dataset.tab}`)
      .classList.add("authenticate__content--active");
  });
}

// Menu fade animation
const handleHover = function (e) {
  if (e.target.classList.contains("nav__link")) {
    const link = e.target;
    const siblings = link.closest("nav").querySelectorAll(".nav__link");
    const logo = link.closest("nav").querySelector("img");

    siblings.forEach((el) => {
      if (el !== link) el.style.opacity = this;
    });
    logo.style.opacity = this;
  }
};

nav.addEventListener("mouseover", handleHover.bind(0.5)); // mouseover instead of mousenter for bubble (delegation). bind() method to manually set the this keyword
nav.addEventListener("mouseout", handleHover.bind(1)); // mouseout = opposite of mouseover

// Sticky Nav: Intersection Observer API
const stickyNav = function (entries) {
  const [entry] = entries; // threshold

  if (!entry.isIntersecting) nav.classList.add("sticky");
  else nav.classList.remove("sticky");
};

const headerObserver = new IntersectionObserver(stickyNav, {
  root: null,
  threshold: 0,
  rootMargin: `-${navHeight}px`,
});
if (header != null) {
  headerObserver.observe(header);
}

// Reveal sections
const allSections = document.querySelectorAll(".section");

const revealSection = function (entries, observer) {
  const [entry] = entries;
  // console.log(entry);

  if (!entry.isIntersecting) return;

  entry.target.classList.remove("section--hidden");
  observer.unobserve(entry.target);
};

const sectionObserver = new IntersectionObserver(revealSection, {
  root: null,
  threshold: 0.15,
});

// observe each section w/same Observer, +programmatically add the hidden class
allSections.forEach(function (section) {
  sectionObserver.observe(section);
  section.classList.add("section--hidden");
});

// Lazy loading images
const imgTargets = document.querySelectorAll("img[data-src]");
// console.log(imgTargets);

const loadImg = function (entries, observer) {
  const [entry] = entries;
  // console.log(entry);

  if (!entry.isIntersecting) return;

  // Replace src with data-src
  entry.target.src = entry.target.dataset.src;
  // listen to load prior to removing blur for ux
  entry.target.addEventListener("load", function () {
    entry.target.classList.remove("lazy-img");
  });

  observer.unobserve(entry.target);
};

const imgObserver = new IntersectionObserver(loadImg, {
  root: null,
  threshold: 0,
  rootMargin: "200px", // for ux
});

imgTargets.forEach((img) => imgObserver.observe(img));

// Slider
const slider = function () {
  const slides = document.querySelectorAll(".slide");
  const btnLeft = document.querySelector(".slider__btn--left");
  const btnRight = document.querySelector(".slider__btn--right");

  let curSlide = 0;
  const maxSlide = slides.length;

  const dotContainer = document.querySelector(".dots");

  // Functions
  const goToSlide = function (slide) {
    slides.forEach(
      (s, i) => (s.style.transform = `translateX(${100 * (i - slide)}%)`),
    );
  };
  // goToSlide(0);

  // Next slide
  const nextSlide = function () {
    if (curSlide === maxSlide - 1) {
      curSlide = 0;
    } else {
      curSlide++;
    }

    goToSlide(curSlide);
    activateDot(curSlide);
  };

  const prevSlide = function () {
    if (curSlide === 0) {
      curSlide = maxSlide - 1;
    } else {
      curSlide--;
    }

    goToSlide(curSlide);
    activateDot(curSlide);
  };

  const createDots = function () {
    slides.forEach(function (_, i) {
      dotContainer.insertAdjacentHTML(
        "beforeend",
        `<button class="dots__dot" data-slide="${i}"></button>`,
      );
    });
  };
  // createDots();

  const activateDot = function (slide) {
    document
      .querySelectorAll(".dots__dot")
      .forEach((dot) => dot.classList.remove("dots__dot--active"));

    document
      .querySelector(`.dots__dot[data-slide="${slide}"]`)
      .classList.add("dots__dot--active");
  };
  // activateDot(0);

  const init = function () {
    goToSlide(0);
    createDots();
    activateDot(0);
  };
  init();

  // Event handlers
  btnRight.addEventListener("click", nextSlide);
  btnLeft.addEventListener("click", prevSlide);

  // using arrow keys -- s-c
  document.addEventListener("keydown", function (e) {
    // console.log(e);
    e.key === "ArrowLeft" && prevSlide();
    e.key === "ArrowRight" && nextSlide();
  });

  // using dots -- event delegation (efficiency)
  dotContainer.addEventListener("click", function (e) {
    if (e.target.classList.contains("dots__dot")) {
      const { slide } = e.target.dataset; // destructuring
      goToSlide(slide);
      activateDot(slide);
    }
  });
};
if (document.querySelector(".slide") != null) {
  slider(); // could pass in an options object to have the slider container work with options
}

const signinForm = document.querySelector(".modal__form");
const signinBtn = signinForm.querySelector(".btn");
const signupForm = document.getElementById("signup_form");
const signupBtn = signupForm.querySelector(".btn");
signinBtn.addEventListener("click", async (event) => {
  event.preventDefault(); // Prevent the default form submission behavior

  const email = signinForm.querySelector('input[type="email"]').value;
  const password = signinForm.querySelector('input[type="password"]').value;

  // Handle the form submission here
  console.log("Sigin");
  console.log("Email:", email);
  console.log("Password:", password);

  //   loadingAnimation.style.display = 'block';
  const signin = await signIn(email, password);
  //   loadingAnimation.style.display = 'none';
});

// const loadingAnimation = document.querySelector('.loading-animation');

signupBtn.addEventListener("click", async (event) => {
  event.preventDefault(); // Prevent the default form submission behavior

  const email = signupForm.querySelector('input[type="email"]').value;
  const password = signupForm.querySelector('input[type="password"]').value;

  // Handle the form submission here
  console.log("Signup");
  console.log("Email:", email);
  console.log("Password:", password);

  //   loadingAnimation.style.display = 'block';
  const signup = await signUp(email, password);
  //   loadingAnimation.style.display = 'none';
});

onAuthStateChanged(auth, (user) => {
  const dfMessenger = document.querySelector("df-messenger");
  const dfMessengerBubble = document.querySelector("df-messenger-chat-bubble");
  dfMessengerBubble.closeChat();
  dfMessenger.clearStorage();
  if (user) {
    const uid = user.uid;
    const email_id = user.email.toString();
    console.log("User is signed in");
    console.log(uid);
    loginBtn.style.display = "none";
    logoutBtn.style.display = "block";
    footer_signup.style.display = "none";

    const uri = "{{user_login_url}}";
    const body = JSON.stringify({ uid: uid.toString() });
    const initDetails = {
      method: "POST",
      mode: "cors",
      headers: {
        "Content-Type": "application/json",
      },
      referrerPolicy: "strict-origin-when-cross-origin",
      body: body,
    };

    fetch(uri, initDetails)
      .then((response) => {
        if (response.status !== 200) {
          console.log(
            "Looks like there was a problem. Status Code: " + response.status,
          );
          return;
        }
        console.log(response.headers.get("Content-Type"));
        return response.json();
      })
      .then((myJson) => {
        console.log(JSON.stringify(myJson));
        var obj = JSON.parse(JSON.stringify(myJson));
        var cust_id = obj.cust_id;
        var name = obj.name;
        console.log(name);
        console.log(cust_id);

        const queryParams = {
          parameters: {
            name: name,
            cust_id: cust_id,
            email_id: email_id,
          },
        };
        console.log(queryParams);
        dfMessenger.setQueryParameters(queryParams);
      })
      .catch((err) => {
        console.log("Fetch Error :-S", err);
      })
      .finally(() => {
        // Hide loading symbol
        // document.getElementById('loader').style.display = 'none';
      });
  } else {
    console.log("User is signed out");
    loginBtn.style.display = "block";
    logoutBtn.style.display = "none";
    footer_signup.style.display = "block";
  }
});

function submitSearch() {
  console.log("search");
  document.getElementById("loader").style.display = "block";

  var query = document.getElementById("search-query-input").value;

  const uri = "{{rag_qa_chain_url_translate}}";
  const body = JSON.stringify({ query: query });
  const initDetails = {
    method: "POST",
    mode: "cors",
    headers: {
      "Content-Type": "application/json",
    },
    referrerPolicy: "strict-origin-when-cross-origin",
    body: body,
  };

  fetch(uri, initDetails)
    .then((response) => {
      if (response.status !== 200) {
        console.log(
          "Looks like there was a problem. Status Code: " + response.status,
        );
        return;
      }
      console.log(response.headers.get("Content-Type"));
      return response.json();
    })
    .then((myJson) => {
      console.log(JSON.stringify(myJson));
      var obj = JSON.parse(JSON.stringify(myJson));

      sessionStorage.setItem("temp_result", JSON.stringify(obj));
      window.location.href = "/search";

      references = JSON.parse(
        obj.fulfillment_response.messages[0].text.text[1],
      );
      console.log(references);
      var str = "";
      var i = 0;
      var count = 0;
    })
    .catch((err) => {
      console.log("Fetch Error :-S", err);
    })
    .finally(() => {
      // Hide loading symbol
      document.getElementById("loader").style.display = "none";
    });
}

function searchKeyPress(e) {
  // look for window.event in case event isn't passed in
  e = e || window.event;

  if (e.keyCode == 13) {
    document.getElementById("search-icon").click();

    return false;
  }

  return true;
}
