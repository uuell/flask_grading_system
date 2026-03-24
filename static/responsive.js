/**
 * Acadify — Responsive Sidebar Controller
 * Place this file at: static/responsive.js
 * Add <script src="{{ url_for('static', filename='responsive.js') }}"></script>
 * just before the closing </body> tag in every template.
 */

(function () {
  'use strict';

  /* ── Only run on mobile-ish widths ── */
  function isMobile() {
    return window.innerWidth <= 768;
  }

  /* ── Create hamburger button ── */
  function createHamburger() {
    if (document.querySelector('.hamburger-btn')) return;

    const btn = document.createElement('button');
    btn.className = 'hamburger-btn';
    btn.setAttribute('aria-label', 'Toggle navigation');
    btn.innerHTML = `<span></span><span></span><span></span>`;
    document.body.prepend(btn);
    return btn;
  }

  /* ── Create overlay ── */
  function createOverlay() {
    if (document.querySelector('.sidebar-overlay')) return;

    const overlay = document.createElement('div');
    overlay.className = 'sidebar-overlay';
    document.body.appendChild(overlay);
    return overlay;
  }

  /* ── Get the sidebar element (works for both <nav> and <div> sidebars) ── */
  function getSidebar() {
    return (
      document.querySelector('nav.sidebar') ||
      document.querySelector('.sidebar')
    );
  }

  /* ── Open sidebar ── */
  function openSidebar(btn, sidebar, overlay) {
    sidebar.classList.add('sidebar-open');
    overlay.classList.add('visible');
    btn.classList.add('open');
    btn.setAttribute('aria-expanded', 'true');
    document.body.style.overflow = 'hidden';
  }

  /* ── Close sidebar ── */
  function closeSidebar(btn, sidebar, overlay) {
    sidebar.classList.remove('sidebar-open');
    overlay.classList.remove('visible');
    btn.classList.remove('open');
    btn.setAttribute('aria-expanded', 'false');
    document.body.style.overflow = '';
  }

  /* ── Init ── */
  function init() {
    const sidebar = getSidebar();
    if (!sidebar) return;

    const btn = createHamburger();
    const overlay = createOverlay();

    if (!btn || !overlay) return;

    let isOpen = false;

    btn.addEventListener('click', function () {
      isOpen = !isOpen;
      if (isOpen) {
        openSidebar(btn, sidebar, overlay);
      } else {
        closeSidebar(btn, sidebar, overlay);
      }
    });

    /* Close on overlay click */
    overlay.addEventListener('click', function () {
      isOpen = false;
      closeSidebar(btn, sidebar, overlay);
    });

    /* Close on Escape key */
    document.addEventListener('keydown', function (e) {
      if (e.key === 'Escape' && isOpen) {
        isOpen = false;
        closeSidebar(btn, sidebar, overlay);
      }
    });

    /* Close sidebar when a nav link is clicked (for in-page navigation) */
    sidebar.querySelectorAll('.nav-item').forEach(function (link) {
      link.addEventListener('click', function () {
        if (isMobile()) {
          isOpen = false;
          closeSidebar(btn, sidebar, overlay);
        }
      });
    });

    /* On resize: if going back to desktop, reset everything */
    let resizeTimer;
    window.addEventListener('resize', function () {
      clearTimeout(resizeTimer);
      resizeTimer = setTimeout(function () {
        if (!isMobile()) {
          sidebar.classList.remove('sidebar-open');
          overlay.classList.remove('visible');
          btn.classList.remove('open');
          btn.setAttribute('aria-expanded', 'false');
          document.body.style.overflow = '';
          isOpen = false;
        }
      }, 150);
    });
  }

  /* ── Run after DOM is ready ── */
  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', init);
  } else {
    init();
  }
})();