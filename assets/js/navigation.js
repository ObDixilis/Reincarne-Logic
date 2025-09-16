(function () {
  const navToggle = document.querySelector('.nav-toggle');
  const navList = document.getElementById('primary-nav-list');
  const dropdownItems = document.querySelectorAll('.has-dropdown');

  const isMobileViewport = () => window.matchMedia('(max-width: 720px)').matches;

  const closeNav = () => {
    if (!navList || !navToggle) return;
    navList.dataset.open = 'false';
    navToggle.setAttribute('aria-expanded', 'false');
  };

  const closeOtherDropdowns = (currentItem) => {
    dropdownItems.forEach((item) => {
      if (item !== currentItem) {
        item.dataset.open = 'false';
        const trigger = item.querySelector('.dropdown-toggle');
        if (trigger) {
          trigger.setAttribute('aria-expanded', 'false');
        }
      }
    });
  };

  if (navList) {
    navList.dataset.open = 'false';
  }

  if (navToggle && navList) {
    navToggle.setAttribute('aria-expanded', 'false');
    navToggle.addEventListener('click', () => {
      const currentlyOpen = navList.dataset.open === 'true';
      navList.dataset.open = currentlyOpen ? 'false' : 'true';
      navToggle.setAttribute('aria-expanded', String(!currentlyOpen));

      if (currentlyOpen) {
        closeOtherDropdowns();
      }
    });
  }

  dropdownItems.forEach((item, index) => {
    const toggle = item.querySelector('.dropdown-toggle');
    const menu = item.querySelector('.dropdown-menu');
    if (!toggle || !menu) return;

    if (!menu.id) {
      menu.id = `dropdown-menu-${index}`;
    }

    toggle.setAttribute('aria-controls', menu.id);
    toggle.setAttribute('aria-haspopup', 'true');

    item.dataset.open = 'false';
    toggle.setAttribute('aria-expanded', 'false');

    toggle.addEventListener('click', (event) => {
      const mobile = isMobileViewport();
      const isOpen = item.dataset.open === 'true';
      if (mobile) {
        event.preventDefault();
        item.dataset.open = isOpen ? 'false' : 'true';
        toggle.setAttribute('aria-expanded', (!isOpen).toString());
        if (!isOpen) {
          closeOtherDropdowns(item);
        }
      } else {
        closeOtherDropdowns(item);
        item.dataset.open = 'true';
        toggle.setAttribute('aria-expanded', 'true');
      }
    });

    item.addEventListener('mouseenter', () => {
      if (!isMobileViewport()) {
        closeOtherDropdowns(item);
        item.dataset.open = 'true';
        toggle.setAttribute('aria-expanded', 'true');
      }
    });

    item.addEventListener('mouseleave', () => {
      if (!isMobileViewport()) {
        item.dataset.open = 'false';
        toggle.setAttribute('aria-expanded', 'false');
      }
    });
  });

  document.addEventListener('click', (event) => {
    if (!event.target.closest('.primary-nav')) {
      closeOtherDropdowns();
      if (isMobileViewport()) {
        closeNav();
      }
    }
  });

  document.addEventListener('keydown', (event) => {
    if (event.key === 'Escape') {
      closeOtherDropdowns();
      closeNav();
    }
  });

  if (navList) {
    navList.querySelectorAll('a').forEach((link) => {
      link.addEventListener('click', () => {
        if (isMobileViewport()) {
          closeNav();
          closeOtherDropdowns();
        }
      });
    });
  }

  let mobileState = isMobileViewport();
  window.addEventListener('resize', () => {
    const nowMobile = isMobileViewport();
    if (nowMobile !== mobileState) {
      closeNav();
      closeOtherDropdowns();
    }
    mobileState = nowMobile;
  });
})();
