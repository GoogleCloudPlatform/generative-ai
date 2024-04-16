'use strict';

const modal = document.querySelector('.modal');
const overlay = document.querySelector('.overlay');
const btnCloseModal = document.querySelector('.btn--close-modal');
const btnsOpenModal = document.querySelectorAll('.btn--show-modal');

const header = document.querySelector('.header');
const message = document.createElement('div');

const btnScrollTo = document.querySelector('.btn--scroll-to');
const section1 = document.querySelector('#section--1');

const tabs = document.querySelectorAll('.operations__tab');
const tabsContainer = document.querySelector('.operations__tab-container');
const tabsContent = document.querySelectorAll('.operations__content');

const nav = document.querySelector('.nav');

const navHeight = nav.getBoundingClientRect().height;

// Modal window
const openModal = function (e) {
    e.preventDefault();
    modal.classList.remove('hidden');
    overlay.classList.remove('hidden');
};

const closeModal = function () {
    modal.classList.add('hidden');
    overlay.classList.add('hidden');
};

btnsOpenModal.forEach(btn => btn.addEventListener('click', openModal));

btnCloseModal.addEventListener('click', closeModal);
overlay.addEventListener('click', closeModal);

document.addEventListener('keydown', function (e) {
    if (e.key === 'Escape' && !modal.classList.contains('hidden')) {
        closeModal();
    }
});

// Cookie msg
message.classList.add('cookie-message');
message.innerHTML =
    'We use cookies for improved functionality and analytics. <button class="btn btn--close-cookie"> Got it!</button>';
header.append(message);

document
    .querySelector('.btn--close-cookie')
    .addEventListener('click', function () {
        message.remove();
    });

message.style.backgroundColor = '#37383d';
message.style.width = '120%';
message.style.height =
    Number.parseFloat(getComputedStyle(message).height, 10) + 30 + 'px';

// Button scrolling
btnScrollTo.addEventListener('click', function () {
    section1.scrollIntoView({ behavior: 'smooth' });
});

// Page navigation - event delegation
document.querySelector('.nav__links').addEventListener('click', function (e) {
    e.preventDefault();

    // Matching strategy
    if (e.target.classList.contains('nav__link')) {
        const targetHref = e.target.getAttribute('href');

        if (targetHref.startsWith('#')) {
            const targetElement = document.querySelector(targetHref);
            if (targetElement) {
                targetElement.scrollIntoView({ behavior: 'smooth' });
            }
        } else {
            window.location.href = targetHref;
        }
    }
});

// Tabbed component
tabsContainer.addEventListener('click', function (e) {
    const clicked = e.target.closest('.operations__tab');

    // Guard clause
    if (!clicked) return;

    // Remove active classes
    tabs.forEach(t => t.classList.remove('operations__tab--active'));
    tabsContent.forEach(t => t.classList.remove('operations__content--active'));

    // Active tab
    clicked.classList.add('operations__tab--active');

    // Active content area
    document
        .querySelector(`.operations__content--${clicked.dataset.tab}`)
        .classList.add('operations__content--active');
});

// Menu fade animation
const handleHover = function (e) {
    if (e.target.classList.contains('nav__link')) {
        const link = e.target;
        const siblings = link.closest('.nav').querySelectorAll('.nav__link');
        const logo = link.closest('.nav').querySelector('img');

        siblings.forEach(el => {
            if (el !== link) el.style.opacity = this;
        });
        logo.style.opacity = this;
    }
};

nav.addEventListener('mouseover', handleHover.bind(0.5)); // mouseover instead of mousenter for bubble (delegation). bind() method to manually set the this keyword
nav.addEventListener('mouseout', handleHover.bind(1)); // mouseout = opposite of mouseover

// Sticky Nav: Intersection Observer API
const stickyNav = function (entries) {
    const [entry] = entries; // threshold

    if (!entry.isIntersecting) nav.classList.add('sticky');
    else nav.classList.remove('sticky');
};

const headerObserver = new IntersectionObserver(stickyNav, {
    root: null,
    threshold: 0,
    rootMargin: `-${navHeight}px`,
});
headerObserver.observe(header);

// Reveal sections
const allSections = document.querySelectorAll('.section');

const revealSection = function (entries, observer) {
    const [entry] = entries;
    // console.log(entry);

    if (!entry.isIntersecting) return;

    entry.target.classList.remove('section--hidden');
    observer.unobserve(entry.target);
};

const sectionObserver = new IntersectionObserver(revealSection, {
    root: null,
    threshold: 0.15,
});

// observe each section w/same Observer, +programmatically add the hidden class
allSections.forEach(function (section) {
    sectionObserver.observe(section);
    section.classList.add('section--hidden');
});

// Lazy loading images
const imgTargets = document.querySelectorAll('img[data-src]');
// console.log(imgTargets);

const loadImg = function (entries, observer) {
    const [entry] = entries;
    // console.log(entry);

    if (!entry.isIntersecting) return;

    // Replace src with data-src
    entry.target.src = entry.target.dataset.src;
    // listen to load prior to removing blur for ux
    entry.target.addEventListener('load', function () {
        entry.target.classList.remove('lazy-img');
    });

    observer.unobserve(entry.target);
};

const imgObserver = new IntersectionObserver(loadImg, {
    root: null,
    threshold: 0,
    rootMargin: '200px', // for ux
});

imgTargets.forEach(img => imgObserver.observe(img));

// Slider
const slider = function () {
    const slides = document.querySelectorAll('.slide');
    const btnLeft = document.querySelector('.slider__btn--left');
    const btnRight = document.querySelector('.slider__btn--right');

    let curSlide = 0;
    const maxSlide = slides.length;

    const dotContainer = document.querySelector('.dots');

    // Functions
    const goToSlide = function (slide) {
        slides.forEach(
            (s, i) => (s.style.transform = `translateX(${100 * (i - slide)}%)`)
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
                'beforeend',
                `<button class="dots__dot" data-slide="${i}"></button>`
            );
        });
    };
    // createDots();

    const activateDot = function (slide) {
        document
            .querySelectorAll('.dots__dot')
            .forEach(dot => dot.classList.remove('dots__dot--active'));

        document
            .querySelector(`.dots__dot[data-slide="${slide}"]`)
            .classList.add('dots__dot--active');
    };
    // activateDot(0);

    const init = function () {
        goToSlide(0);
        createDots();
        activateDot(0);
    };
    init();

    // Event handlers
    btnRight.addEventListener('click', nextSlide);
    btnLeft.addEventListener('click', prevSlide);

    // using arrow keys -- s-c
    document.addEventListener('keydown', function (e) {
        // console.log(e);
        e.key === 'ArrowLeft' && prevSlide();
        e.key === 'ArrowRight' && nextSlide();
    });

    // using dots -- event delegation (efficiency)
    dotContainer.addEventListener('click', function (e) {
        if (e.target.classList.contains('dots__dot')) {
            const { slide } = e.target.dataset; // destructuring
            goToSlide(slide);
            activateDot(slide);
        }
    });
};
slider(); // could pass in an options object to have the slider container work with options
