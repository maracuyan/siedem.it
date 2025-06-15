document.addEventListener('DOMContentLoaded', () => {
  const sidebar = document.getElementById('sidebar');
  const sidebarContent = document.getElementById('sidebar-content'); // Though not directly manipulated in this plan, good to have.
  const sidebarCloseBtn = document.getElementById('sidebar-close-btn');
  const sidebarOverlay = document.getElementById('sidebar-overlay');

  // Content sections
  const kategorieContent = document.getElementById('sidebar-kategorie-content');
  const szukajContent = document.getElementById('sidebar-szukaj-content');
  const ulubioneContent = document.getElementById('sidebar-ulubione-content');
  const udostepnijContent = document.getElementById('sidebar-udostepnij-content');

  const allSidebarSections = document.querySelectorAll('.sidebar-section-content');

  // Bottom navigation buttons (using anticipated IDs)
  const btnKategorie = document.getElementById('btn-kategorie');
  const btnSzukaj = document.getElementById('btn-szukaj'); // This is also the search icon in the header.
  const btnUlubione = document.getElementById('btn-ulubione');
  const btnUdostepnij = document.getElementById('btn-udostepnij');

  // Header search icon
  const headerSearchIcon = document.getElementById('header-search-icon');


  function openSidebar(contentType) {
    if (!sidebar) return;

    // Hide all sections first
    allSidebarSections.forEach(section => {
      section.style.display = 'none';
    });

    // Show the target section
    let targetSection;
    switch (contentType) {
      case 'kategorie':
        targetSection = kategorieContent;
        break;
      case 'szukaj':
        targetSection = szukajContent;
        break;
      case 'ulubione':
        targetSection = ulubioneContent;
        break;
      case 'udostepnij':
        targetSection = udostepnijContent;
        break;
      default:
        console.warn('Unknown content type:', contentType);
        return;
    }

    if (targetSection) {
      targetSection.style.display = 'block';
    }

    sidebar.classList.add('open');
    if (sidebarOverlay) {
      sidebarOverlay.classList.add('active'); // Using class for consistency with CSS
    }
  }

  function closeSidebar() {
    if (!sidebar) return;
    sidebar.classList.remove('open');
    if (sidebarOverlay) {
      sidebarOverlay.classList.remove('active'); // Using class
    }
  }

  // Event Listeners
  if (sidebarCloseBtn) {
    sidebarCloseBtn.addEventListener('click', closeSidebar);
  }

  if (sidebarOverlay) {
    sidebarOverlay.addEventListener('click', closeSidebar);
  }

  // Bottom navigation button listeners
  if (btnKategorie) {
    btnKategorie.addEventListener('click', (event) => {
      event.preventDefault();
      openSidebar('kategorie');
    });
  }

  if (btnSzukaj) {
    btnSzukaj.addEventListener('click', (event) => {
      event.preventDefault();
      openSidebar('szukaj');
    });
  }

  if (headerSearchIcon) {
    headerSearchIcon.addEventListener('click', (event) => {
      event.preventDefault();
      openSidebar('szukaj');
    });
  }

  if (btnUlubione) {
    btnUlubione.addEventListener('click', (event) => {
      event.preventDefault();
      openSidebar('ulubione');
    });
  }

  if (btnUdostepnij) {
    btnUdostepnij.addEventListener('click', (event) => {
      event.preventDefault();
      openSidebar('udostepnij');
    });
  }

});
