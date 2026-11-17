/**
 * MOCTALE — Premium Editorial Movie Recommendation Frontend
 * Vanilla JavaScript (ES6+)
 * Features: Cinematic Intro Experience, Poster-First Paginated Archive,
 * Real ML Search Autocomplete with Keyboard Navigation, and Detail Modals.
 */

document.addEventListener('DOMContentLoaded', () => {
  // Intro Elements
  const cinematicIntro = document.getElementById('cinematicIntro');
  const introScrollTrigger = document.getElementById('introScrollTrigger');
  const skipIntroBtn = document.getElementById('skipIntroBtn');

  // DOM Elements
  const searchInput = document.getElementById('searchInput');
  const searchClearBtn = document.getElementById('searchClearBtn');
  const searchForm = document.getElementById('searchForm');
  const autocompleteDropdown = document.getElementById('autocompleteDropdown');
  const resultsSection = document.getElementById('resultsSection');
  const spotlightContainer = document.getElementById('spotlightContainer');
  const recommendationsGrid = document.getElementById('recommendationsGrid');
  const searchStatusMessage = document.getElementById('searchStatusMessage');
  const featuredGrid = document.getElementById('featuredGrid');
  const loadMoreArchiveBtn = document.getElementById('loadMoreArchiveBtn');
  const archiveStatusMessage = document.getElementById('archiveStatusMessage');
  
  // Modal Elements
  const movieModal = document.getElementById('movieModal');
  const modalCloseBtn = document.getElementById('modalCloseBtn');
  const modalBackdrop = document.getElementById('modalBackdrop');
  const modalPoster = document.getElementById('modalPoster');
  const modalTitle = document.getElementById('modalTitle');
  const modalTagline = document.getElementById('modalTagline');
  const modalYear = document.getElementById('modalYear');
  const modalRuntime = document.getElementById('modalRuntime');
  const modalRating = document.getElementById('modalRating');
  const modalDirector = document.getElementById('modalDirector');
  const modalGenres = document.getElementById('modalGenres');
  const modalOverview = document.getElementById('modalOverview');
  const modalCast = document.getElementById('modalCast');
  const modalTmdbLink = document.getElementById('modalTmdbLink');
  const modalExploreBtn = document.getElementById('modalExploreBtn');

  // State Variables
  let debounceTimer = null;
  let activeSelectedMovieId = null;
  let archivePage = 1;
  const archiveLimit = 8;
  let isArchiveLoading = false;
  let autocompleteSelectedIndex = -1;

  // Initialize
  initApp();

  function initApp() {
    setupCinematicIntro();
    if (featuredGrid && featuredGrid.children.length > 0) {
      attachCardListeners(featuredGrid);
      archivePage = 1;
    } else {
      loadArchivePage(1, false);
    }
    setupEventListeners();
  }

  // =========================================================================
  // 1. CINEMATIC INTRO SEQUENCE
  // =========================================================================
  function setupCinematicIntro() {
    if (!cinematicIntro) return;

    // Check if user already entered during this session or prefers reduced motion
    const alreadySeen = sessionStorage.getItem('moctale_intro_passed');
    const prefersReducedMotion = window.matchMedia('(prefers-reduced-motion: reduce)').matches;

    if (alreadySeen === 'true' || prefersReducedMotion) {
      cinematicIntro.classList.add('dismissed');
      return;
    }

    // Scroll trigger click
    if (introScrollTrigger) {
      introScrollTrigger.addEventListener('click', dismissIntro);
      introScrollTrigger.addEventListener('keydown', (e) => {
        if (e.key === 'Enter' || e.key === ' ') {
          e.preventDefault();
          dismissIntro();
        }
      });
    }

    // Skip button click
    if (skipIntroBtn) {
      skipIntroBtn.addEventListener('click', (e) => {
        e.stopPropagation();
        dismissIntro();
      });
    }

    // Wheel or touch scroll triggers natural entrance
    let wheelDelta = 0;
    const handleIntroWheel = (e) => {
      wheelDelta += e.deltaY;
      if (Math.abs(wheelDelta) > 40) {
        window.removeEventListener('wheel', handleIntroWheel);
        dismissIntro();
      }
    };
    window.addEventListener('wheel', handleIntroWheel, { passive: true });

    // Touch scroll for mobile
    let touchStartY = 0;
    window.addEventListener('touchstart', (e) => {
      touchStartY = e.touches[0].clientY;
    }, { passive: true });

    window.addEventListener('touchmove', (e) => {
      const touchY = e.touches[0].clientY;
      if (touchStartY - touchY > 50) {
        dismissIntro();
      }
    }, { passive: true });
  }

  function dismissIntro() {
    if (!cinematicIntro || cinematicIntro.classList.contains('dismissed')) return;

    cinematicIntro.classList.add('dismissed');
    sessionStorage.setItem('moctale_intro_passed', 'true');

    // Smooth scroll to the main search hero
    const hero = document.getElementById('search');
    if (hero) {
      setTimeout(() => {
        hero.scrollIntoView({ behavior: 'smooth', block: 'start' });
      }, 200);
    }
  }

  // =========================================================================
  // 2. ARCHIVE WITH LOAD MORE & POSTER-FIRST FILTERING
  // =========================================================================
  async function loadArchivePage(page, append = false) {
    if (isArchiveLoading) return;
    isArchiveLoading = true;

    if (loadMoreArchiveBtn) {
      loadMoreArchiveBtn.disabled = true;
      const btnText = loadMoreArchiveBtn.querySelector('.btn-text');
      const btnSpinner = loadMoreArchiveBtn.querySelector('.btn-spinner');
      if (btnText) btnText.textContent = 'Loading Films...';
      if (btnSpinner) btnSpinner.style.display = 'inline-block';
    }

    try {
      const response = await fetch(`/api/archive?page=${page}&limit=${archiveLimit}`);
      const data = await response.json();

      if (data.success && data.movies && data.movies.length > 0) {
        renderArchiveCards(data.movies, append);

        // Update load more button visibility
        if (loadMoreArchiveBtn) {
          if (data.has_more) {
            loadMoreArchiveBtn.style.display = 'inline-flex';
            loadMoreArchiveBtn.disabled = false;
            const btnText = loadMoreArchiveBtn.querySelector('.btn-text');
            const btnSpinner = loadMoreArchiveBtn.querySelector('.btn-spinner');
            if (btnText) btnText.textContent = 'Load More Films';
            if (btnSpinner) btnSpinner.style.display = 'none';
          } else {
            loadMoreArchiveBtn.style.display = 'none';
            if (archiveStatusMessage) {
              archiveStatusMessage.textContent = 'All curated masterpieces loaded from the archive.';
              archiveStatusMessage.style.display = 'block';
            }
          }
        }
      } else {
        if (!append && featuredGrid) {
          featuredGrid.innerHTML = `
            <div class="empty-state" style="grid-column: 1 / -1;">
              <h3>Archive Empty</h3>
              <p>No verified poster films currently available in this partition.</p>
            </div>
          `;
        }
        if (loadMoreArchiveBtn) loadMoreArchiveBtn.style.display = 'none';
      }
    } catch (err) {
      console.error('Failed to load archive page:', err);
      if (loadMoreArchiveBtn) {
        loadMoreArchiveBtn.disabled = false;
        const btnText = loadMoreArchiveBtn.querySelector('.btn-text');
        const btnSpinner = loadMoreArchiveBtn.querySelector('.btn-spinner');
        if (btnText) btnText.textContent = 'Retry Loading';
        if (btnSpinner) btnSpinner.style.display = 'none';
      }
    } finally {
      isArchiveLoading = false;
    }
  }

  function renderArchiveCards(movies, append = false) {
    if (!featuredGrid) return;

    const cardsHtml = movies.map(m => createMovieCardHtml(m, false)).join('');

    if (append) {
      const tempDiv = document.createElement('div');
      tempDiv.innerHTML = cardsHtml;
      Array.from(tempDiv.children).forEach(card => {
        card.classList.add('card-fade-in');
        featuredGrid.appendChild(card);
      });
    } else {
      featuredGrid.innerHTML = cardsHtml;
    }

    attachCardListeners(featuredGrid);
  }

  // =========================================================================
  // 3. SEARCH & RECOMMENDATIONS LOGIC
  // =========================================================================
  function setupEventListeners() {
    // Autocomplete with debouncing
    searchInput.addEventListener('input', (e) => {
      const query = e.target.value.trim();
      autocompleteSelectedIndex = -1;
      if (query.length > 0) {
        searchClearBtn.style.display = 'flex';
      } else {
        searchClearBtn.style.display = 'none';
        hideAutocomplete();
        return;
      }

      clearTimeout(debounceTimer);
      debounceTimer = setTimeout(() => {
        fetchAutocompleteSuggestions(query);
      }, 250);
    });

    // Keyboard navigation in search input
    searchInput.addEventListener('keydown', (e) => {
      const items = autocompleteDropdown.querySelectorAll('.autocomplete-item:not([style*="cursor: default"])');
      if (!items.length) return;

      if (e.key === 'ArrowDown') {
        e.preventDefault();
        autocompleteSelectedIndex = (autocompleteSelectedIndex + 1) % items.length;
        updateAutocompleteSelection(items);
      } else if (e.key === 'ArrowUp') {
        e.preventDefault();
        autocompleteSelectedIndex = (autocompleteSelectedIndex - 1 + items.length) % items.length;
        updateAutocompleteSelection(items);
      } else if (e.key === 'Enter') {
        if (autocompleteSelectedIndex >= 0 && items[autocompleteSelectedIndex]) {
          e.preventDefault();
          const selectedTitle = items[autocompleteSelectedIndex].getAttribute('data-title');
          if (selectedTitle) {
            searchInput.value = selectedTitle;
            hideAutocomplete();
            fetchRecommendations(selectedTitle);
          }
        }
      } else if (e.key === 'Escape') {
        hideAutocomplete();
      }
    });

    // Clear search button
    searchClearBtn.addEventListener('click', () => {
      searchInput.value = '';
      searchClearBtn.style.display = 'none';
      hideAutocomplete();
      searchInput.focus();
    });

    // Search form submit
    searchForm.addEventListener('submit', (e) => {
      e.preventDefault();
      const query = searchInput.value.trim();
      if (query) {
        hideAutocomplete();
        fetchRecommendations(query);
      }
    });

    // Close autocomplete on click outside
    document.addEventListener('click', (e) => {
      if (!searchForm.contains(e.target)) {
        hideAutocomplete();
      }
    });

    // Quick tag chips
    document.querySelectorAll('.chip-btn').forEach((chip) => {
      chip.addEventListener('click', () => {
        const title = chip.getAttribute('data-title');
        searchInput.value = title;
        searchClearBtn.style.display = 'flex';
        fetchRecommendations(title);
      });
    });

    // Load More Archive Button
    if (loadMoreArchiveBtn) {
      loadMoreArchiveBtn.addEventListener('click', () => {
        archivePage += 1;
        loadArchivePage(archivePage, true);
      });
    }

    // Modal close listeners
    modalCloseBtn.addEventListener('click', closeModal);
    movieModal.addEventListener('click', (e) => {
      if (e.target === movieModal) {
        closeModal();
      }
    });
    document.addEventListener('keydown', (e) => {
      if (e.key === 'Escape' && movieModal.classList.contains('active')) {
        closeModal();
      }
    });
  }

  function updateAutocompleteSelection(items) {
    items.forEach((item, idx) => {
      if (idx === autocompleteSelectedIndex) {
        item.classList.add('selected');
        item.scrollIntoView({ block: 'nearest' });
      } else {
        item.classList.remove('selected');
      }
    });
  }

  async function fetchAutocompleteSuggestions(query) {
    try {
      const response = await fetch(`/api/search?q=${encodeURIComponent(query)}&limit=6`);
      if (!response.ok) return;
      const data = await response.json();
      renderAutocomplete(data.results);
    } catch (err) {
      console.error('Autocomplete error:', err);
    }
  }

  async function fetchRecommendations(query) {
    showLoading();
    resultsSection.classList.add('active');
    resultsSection.scrollIntoView({ behavior: 'smooth', block: 'start' });

    try {
      const response = await fetch(`/api/recommend?movie=${encodeURIComponent(query)}&top_k=5`);
      const data = await response.json();

      if (data.success) {
        renderSpotlight(data.selected_movie);
        renderRecommendations(data.recommendations, data.selected_movie.title);
      } else {
        renderErrorState(data.message, data.suggestions);
      }
    } catch (err) {
      console.error('Recommendation fetch error:', err);
      renderErrorState('An unexpected network error occurred while generating recommendations.');
    }
  }

  async function openMovieDetails(movieId) {
    try {
      const response = await fetch(`/api/movie/${movieId}`);
      if (!response.ok) return;
      const data = await response.json();
      if (data.success && data.movie) {
        populateAndShowModal(data.movie);
      }
    } catch (err) {
      console.error('Failed to load movie details:', err);
    }
  }

  // =========================================================================
  // 4. RENDERING FUNCTIONS
  // =========================================================================
  function renderAutocomplete(results) {
    if (!results || results.length === 0) {
      autocompleteDropdown.innerHTML = `
        <li class="autocomplete-item" style="cursor: default; color: var(--text-muted);">
          <span>No matching films found in catalog.</span>
        </li>
      `;
      autocompleteDropdown.classList.add('show');
      return;
    }

    autocompleteDropdown.innerHTML = results.map(m => `
      <li class="autocomplete-item" data-title="${escapeHtml(m.title)}">
        <div class="item-main-info">
          <span class="item-title">${escapeHtml(m.title)}</span>
          <span class="item-meta">${m.release_year || 'N/A'} • Dir. ${escapeHtml(m.director || 'Unknown')}</span>
        </div>
        ${m.genres && m.genres.length > 0 ? `<span class="item-genres-badge">${escapeHtml(m.genres[0])}</span>` : ''}
      </li>
    `).join('');

    autocompleteDropdown.classList.add('show');

    autocompleteDropdown.querySelectorAll('.autocomplete-item').forEach(item => {
      item.addEventListener('click', () => {
        const title = item.getAttribute('data-title');
        if (title) {
          searchInput.value = title;
          hideAutocomplete();
          fetchRecommendations(title);
        }
      });
    });
  }

  function hideAutocomplete() {
    autocompleteDropdown.classList.remove('show');
    autocompleteDropdown.innerHTML = '';
    autocompleteSelectedIndex = -1;
  }

  function renderSpotlight(movie) {
    activeSelectedMovieId = movie.movie_id;
    const backdropStyle = movie.backdrop_url 
      ? `style="background-image: url('${movie.backdrop_url}');"` 
      : '';

    const genresHtml = (movie.genres || [])
      .map(g => `<span class="tag-pill">${escapeHtml(g)}</span>`)
      .join('');

    spotlightContainer.innerHTML = `
      <div class="spotlight-banner">
        <div class="spotlight-backdrop" ${backdropStyle}></div>
        <div class="spotlight-inner">
          <img 
            src="${movie.poster_url}" 
            alt="${escapeHtml(movie.title)}" 
            class="spotlight-poster"
            loading="lazy"
            onerror="this.src='/static/images/poster_placeholder.svg';"
          />
          <div class="spotlight-details">
            <span class="spotlight-badge">Queried Film Profile</span>
            <h2 class="spotlight-title">${escapeHtml(movie.title)}</h2>
            ${movie.tagline ? `<div class="spotlight-tagline">“${escapeHtml(movie.tagline)}”</div>` : ''}
            
            <div class="spotlight-meta-row">
              <span class="meta-item">📅 ${movie.release_year || 'N/A'}</span>
              <span class="meta-item"><span class="meta-star">★</span> ${movie.vote_average ? movie.vote_average.toFixed(1) : 'N/A'} / 10</span>
              <span class="meta-item">🎬 Dir. ${escapeHtml(movie.director || 'Unknown')}</span>
              ${movie.runtime ? `<span class="meta-item">⏱️ ${movie.runtime} min</span>` : ''}
            </div>
            
            <p class="spotlight-overview">${escapeHtml(movie.overview || 'No synopsis available.')}</p>
            
            <div class="spotlight-chips-row">
              ${genresHtml}
            </div>
          </div>
        </div>
      </div>
    `;
  }

  function renderRecommendations(recommendations, queryTitle) {
    searchStatusMessage.innerHTML = `
      <div class="section-headline-row">
        <div>
          <h2 class="section-title">Deep Similarities</h2>
          <span class="section-subtitle">Recommended because you explored "${escapeHtml(queryTitle)}"</span>
        </div>
      </div>
    `;

    if (!recommendations || recommendations.length === 0) {
      recommendationsGrid.innerHTML = `
        <div class="empty-state" style="grid-column: 1 / -1;">
          <h3>No direct matches found.</h3>
          <p>Try searching for a different movie title.</p>
        </div>
      `;
      return;
    }

    recommendationsGrid.innerHTML = recommendations.map(rec => createMovieCardHtml(rec)).join('');
    attachCardListeners(recommendationsGrid);
  }

  function createMovieCardHtml(movie, showMatch = true) {
    const genresHtml = (movie.genres || []).slice(0, 2)
      .map(g => `<span class="genre-chip">${escapeHtml(g)}</span>`)
      .join('');

    const matchBadge = showMatch && movie.match_percentage
      ? `<div class="card-similarity-badge">${movie.match_percentage}% Match</div>`
      : '';

    const ratingBadge = movie.vote_average && movie.vote_average > 0
      ? `<div class="card-rating-badge">★ ${Number(movie.vote_average).toFixed(1)}</div>`
      : '';

    const runtimeHtml = movie.runtime ? `<span>• ${escapeHtml(movie.runtime)}m</span>` : '';

    return `
      <div class="movie-card" data-id="${movie.movie_id}" data-title="${escapeHtml(movie.title)}">
        <div class="card-poster-wrapper">
          <img 
            src="${movie.poster_url || '/static/images/poster_placeholder.svg'}" 
            alt="${escapeHtml(movie.title)}" 
            class="card-poster-img"
            loading="lazy"
            onerror="this.src='/static/images/poster_placeholder.svg';"
          />
          ${ratingBadge}
          ${matchBadge}
        </div>
        <div class="card-body">
          <h3 class="card-title" title="${escapeHtml(movie.title)}">${escapeHtml(movie.title)}</h3>
          <div class="card-meta-line">
            <span>${movie.release_year || 'N/A'}</span>
            ${runtimeHtml}
            <span class="card-director">Dir. ${escapeHtml(movie.director || 'Unknown')}</span>
          </div>
          <div class="card-genres">
            ${genresHtml}
          </div>
          <div class="card-actions">
            <button class="btn-secondary btn-explore" data-title="${escapeHtml(movie.title)}">
              Explore Similar
            </button>
            <button class="btn-secondary btn-details" data-id="${movie.movie_id}">
              Details
            </button>
          </div>
        </div>
      </div>
    `;
  }

  function attachCardListeners(container) {
    container.querySelectorAll('.movie-card').forEach(card => {
      card.addEventListener('click', (e) => {
        if (e.target.closest('button')) return;
        const movieId = card.getAttribute('data-id');
        if (movieId) openMovieDetails(movieId);
      });
    });

    container.querySelectorAll('.btn-explore').forEach(btn => {
      btn.addEventListener('click', (e) => {
        e.stopPropagation();
        const title = btn.getAttribute('data-title');
        if (title) {
          searchInput.value = title;
          searchClearBtn.style.display = 'flex';
          fetchRecommendations(title);
        }
      });
    });

    container.querySelectorAll('.btn-details').forEach(btn => {
      btn.addEventListener('click', (e) => {
        e.stopPropagation();
        const movieId = btn.getAttribute('data-id');
        if (movieId) openMovieDetails(movieId);
      });
    });
  }

  function showLoading() {
    spotlightContainer.innerHTML = '';
    searchStatusMessage.innerHTML = '';
    recommendationsGrid.innerHTML = `
      <div style="grid-column: 1 / -1; text-align: center; padding: 4rem 0;">
        <div class="spinner"></div>
        <p style="color: var(--text-secondary); letter-spacing: 0.1em; text-transform: uppercase; font-size: 0.85rem;">
          Querying high-dimensional cosine vector space...
        </p>
      </div>
    `;
  }

  function renderErrorState(message, suggestions = []) {
    spotlightContainer.innerHTML = '';
    let suggestionsHtml = '';
    if (suggestions && suggestions.length > 0) {
      suggestionsHtml = `
        <div style="margin-top: 1.5rem;">
          <p style="color: var(--text-muted); font-size: 0.85rem; margin-bottom: 0.75rem;">Did you mean one of these?</p>
          <div class="quick-tags-wrapper" style="justify-content: center;">
            ${suggestions.map(s => `<button class="chip-btn suggestion-chip" data-title="${escapeHtml(s)}">${escapeHtml(s)}</button>`).join('')}
          </div>
        </div>
      `;
    }

    recommendationsGrid.innerHTML = `
      <div class="empty-state" style="grid-column: 1 / -1;">
        <h3>Film Not Found</h3>
        <p>${escapeHtml(message)}</p>
        ${suggestionsHtml}
      </div>
    `;

    recommendationsGrid.querySelectorAll('.suggestion-chip').forEach(chip => {
      chip.addEventListener('click', () => {
        const title = chip.getAttribute('data-title');
        searchInput.value = title;
        fetchRecommendations(title);
      });
    });
  }

  // =========================================================================
  // 5. MODAL LOGIC
  // =========================================================================
  function populateAndShowModal(movie) {
    modalPoster.src = movie.poster_url || '/static/images/poster_placeholder.svg';
    modalPoster.alt = movie.title;
    
    if (movie.backdrop_url) {
      modalBackdrop.style.backgroundImage = `url('${movie.backdrop_url}')`;
    } else {
      modalBackdrop.style.backgroundImage = 'none';
      modalBackdrop.style.backgroundColor = '#181818';
    }

    modalTitle.textContent = movie.title;
    modalTagline.textContent = movie.tagline ? `“${movie.tagline}”` : '';
    modalYear.textContent = `📅 ${movie.release_year || 'N/A'}`;
    modalRuntime.textContent = movie.runtime ? `⏱️ ${movie.runtime} min` : '⏱️ N/A';
    modalRating.textContent = `★ ${movie.vote_average ? movie.vote_average.toFixed(1) : 'N/A'} / 10`;
    modalDirector.textContent = `🎬 Dir. ${movie.director || 'Unknown'}`;
    modalOverview.textContent = movie.overview || 'No synopsis available.';

    modalGenres.innerHTML = (movie.genres || [])
      .map(g => `<span class="tag-pill">${escapeHtml(g)}</span>`)
      .join('');

    if (movie.cast && movie.cast.length > 0) {
      modalCast.innerHTML = movie.cast
        .map(c => `<span class="tag-pill" style="border-color: rgba(197, 167, 123, 0.2);">${escapeHtml(c)}</span>`)
        .join('');
    } else {
      modalCast.innerHTML = `<span style="color: var(--text-muted); font-size: 0.85rem;">Cast data unavailable</span>`;
    }

    if (movie.tmdb_url) {
      modalTmdbLink.href = movie.tmdb_url;
      modalTmdbLink.style.display = 'inline-block';
    } else {
      modalTmdbLink.style.display = 'none';
    }

    modalExploreBtn.onclick = () => {
      closeModal();
      searchInput.value = movie.title;
      searchClearBtn.style.display = 'flex';
      fetchRecommendations(movie.title);
    };

    movieModal.classList.add('active');
    document.body.style.overflow = 'hidden';
  }

  function closeModal() {
    movieModal.classList.remove('active');
    document.body.style.overflow = 'auto';
  }

  function escapeHtml(str) {
    if (!str) return '';
    return String(str)
      .replace(/&/g, '&amp;')
      .replace(/</g, '&lt;')
      .replace(/>/g, '&gt;')
      .replace(/"/g, '&quot;')
      .replace(/'/g, '&#039;');
  }
});
