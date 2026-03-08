const accountBtn = document.getElementById("accountBtn");
const accountMenu = document.getElementById("accountMenu");
const searchInput = document.getElementById("searchInput");
const suggestionBox = document.getElementById("suggestions");

function escapeHtml(value) {
  return String(value || "")
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;")
    .replaceAll("'", "&#39;");
}

if (accountBtn && accountMenu) {
  accountBtn.addEventListener("click", () => {
    accountMenu.classList.toggle("open");
  });
  document.addEventListener("click", (e) => {
    if (!accountMenu.contains(e.target) && e.target !== accountBtn) {
      accountMenu.classList.remove("open");
    }
  });
}

async function loadSuggestions() {
  if (!searchInput || !suggestionBox) return;
  const q = encodeURIComponent(searchInput.value.trim());
  const res = await fetch(`/api/suggestions?q=${q}`);
  if (!res.ok) return;
  const data = await res.json();

  suggestionBox.innerHTML = "";
  (data.items || []).slice(0, 5).forEach((item) => {
    const li = document.createElement("li");
    li.textContent = item;
    li.addEventListener("mousedown", () => {
      searchInput.value = item;
    });
    suggestionBox.appendChild(li);
  });
}

if (searchInput && suggestionBox) {
  const show = async () => {
    await loadSuggestions();
    suggestionBox.classList.add("open");
  };
  const hide = () => suggestionBox.classList.remove("open");

  searchInput.addEventListener("mouseenter", show);
  searchInput.addEventListener("focus", show);
  searchInput.addEventListener("input", show);
  searchInput.addEventListener("blur", hide);
}

document.querySelectorAll(".project-card").forEach((card) => {
  const avatarLink = card.querySelector(".designer-avatar-link");
  const popup = card.querySelector(".popup");
  if (!avatarLink || !popup) return;

  const designerId = avatarLink.dataset.designerId;
  if (!designerId) return;

  const coverImage = card.querySelector(".thumb");
  const coverSrc = coverImage ? coverImage.src : "";

  let loaded = false;
  let timer = null;

  const renderPreview = async () => {
    if (loaded) return;
    const res = await fetch(`/api/designer/${designerId}/preview`);
    if (!res.ok) return;
    const data = await res.json();

    const name = escapeHtml(data.name);
    const projects = Number(data.projects || 0);
    const followers = Number(data.followers || 0);
    const email = String(data.email || "").trim();
    const emailHref = email ? `mailto:${email}` : "#";
    const emailAttrs = email ? "" : ' aria-disabled="true"';

    popup.innerHTML = `
      <div class="popup-cover" style="background-image:url('${coverSrc}')"></div>
      <div class="popup-body popup-body-ref">
        <div class="popup-avatar-stack popup-avatar-stack-ref">
          <img class="popup-avatar popup-avatar-ref" src="${data.profile_image}" alt="${name}">
        </div>

        <h4 class="popup-name popup-name-ref">${name}</h4>

        <div class="popup-stats popup-stats-ref">
          <div><strong>${followers}</strong><span>Followers</span></div>
          <div><strong>${projects}</strong><span>Projects</span></div>
        </div>

        <a class="popup-follow-btn popup-follow-btn-ref" href="${data.profile_url}">+ Follow</a>
        <a class="popup-email-icon" href="${emailHref}" title="Email"${emailAttrs}>&#9993;</a>
      </div>
    `;
    loaded = true;
  };

  const show = async () => {
    clearTimeout(timer);
    await renderPreview();
    popup.classList.add("show");
  };

  const hide = () => {
    timer = setTimeout(() => popup.classList.remove("show"), 130);
  };

  avatarLink.addEventListener("mouseenter", show);
  avatarLink.addEventListener("mouseleave", hide);
  popup.addEventListener("mouseenter", show);
  popup.addEventListener("mouseleave", hide);
});

function setupImageViewer() {
  const viewer = document.getElementById("imageViewer");
  const viewerImage = document.getElementById("viewerImage");
  const closeBtn = document.querySelector(".viewer-close");
  const thumbs = Array.from(document.querySelectorAll(".thumbnail"));

  if (!viewer || !viewerImage || !closeBtn || !thumbs.length) return;

  const openViewer = (src, alt) => {
    viewerImage.src = src;
    viewerImage.alt = alt || "Fullscreen preview";
    viewerImage.classList.remove("zoomed");
    viewer.classList.add("active");
    document.body.classList.add("no-scroll");
  };

  const closeViewer = () => {
    viewer.classList.remove("active");
    viewerImage.classList.remove("zoomed");
    viewerImage.src = "";
    document.body.classList.remove("no-scroll");
  };

  thumbs.forEach((thumb) => {
    thumb.addEventListener("click", () => {
      const img = thumb.querySelector("img");
      if (!img) return;
      openViewer(img.src, img.alt);
    });
  });

  closeBtn.addEventListener("click", closeViewer);

  viewerImage.addEventListener("click", () => {
    viewerImage.classList.toggle("zoomed");
  });
}

setupImageViewer();

// Camera icon upload actions (cover/profile)
document.querySelectorAll("[data-open-picker]").forEach((btn) => {
  btn.addEventListener("click", () => {
    const inputId = btn.getAttribute("data-open-picker");
    const input = inputId ? document.getElementById(inputId) : null;
    if (input) input.click();
  });
});

document.querySelectorAll(".js-image-picker").forEach((input) => {
  input.addEventListener("change", () => {
    if (input.files && input.files.length > 0 && input.form) {
      input.form.submit();
    }
  });
});





// ===== Lazy Smooth Vibe (non-breaking additive layer) =====
(function () {
  function markLazyMedia() {
    var media = document.querySelectorAll('img, iframe, video');
    if (!media.length) return;

    media.forEach(function (el) {
      if (el.tagName === 'IMG') {
        if (!el.hasAttribute('loading')) el.setAttribute('loading', 'lazy');
        if (!el.hasAttribute('decoding')) el.setAttribute('decoding', 'async');
      }

      if (el.tagName === 'IFRAME') {
        if (!el.hasAttribute('loading')) el.setAttribute('loading', 'lazy');
      }

      if (el.tagName === 'VIDEO') {
        if (!el.hasAttribute('preload')) el.setAttribute('preload', 'none');
      }

      el.classList.add('vibe-lazy');
    });

    if (!('IntersectionObserver' in window)) {
      media.forEach(function (el) {
        el.classList.add('is-loaded');
      });
      return;
    }

    var loadObserver = new IntersectionObserver(function (entries, obs) {
      entries.forEach(function (entry) {
        if (!entry.isIntersecting) return;
        var target = entry.target;

        if (target.tagName === 'IMG') {
          if (target.complete) {
            target.classList.add('is-loaded');
          } else {
            target.addEventListener('load', function () {
              target.classList.add('is-loaded');
            }, { once: true });
          }
        } else {
          target.classList.add('is-loaded');
        }

        obs.unobserve(target);
      });
    }, { rootMargin: '180px 0px' });

    media.forEach(function (el) { loadObserver.observe(el); });
  }

  function setupSmoothAnchorScroll() {
    document.querySelectorAll('a[href^="#"]').forEach(function (anchor) {
      anchor.addEventListener('click', function (e) {
        var href = anchor.getAttribute('href') || '';
        if (href.length <= 1) return;

        var target = null;
        var id = href.slice(1);

        if (id) {
          target = document.getElementById(id);
        }

        if (!target) {
          try {
            target = document.querySelector(href);
          } catch (_) {
            target = null;
          }
        }

        if (!target) return;

        e.preventDefault();
        target.scrollIntoView({ behavior: 'smooth', block: 'start' });
      });
    });
  }

  function setupScrollReveal() {
    var candidates = document.querySelectorAll(
      '.premium-card, .project-card, .dashboard-v2-project-card, .profile-restore-card, .card, .table-wrap, .glass-card'
    );

    if (!candidates.length) return;

    candidates.forEach(function (el) {
      if (!el.classList.contains('vibe-reveal')) {
        el.classList.add('vibe-reveal');
      }
    });

    if (!('IntersectionObserver' in window)) {
      document.querySelectorAll('.vibe-reveal').forEach(function (el) {
        el.classList.add('in-view');
      });
      return;
    }

    var revealObserver = new IntersectionObserver(function (entries, obs) {
      entries.forEach(function (entry) {
        if (!entry.isIntersecting) return;
        entry.target.classList.add('in-view');
        obs.unobserve(entry.target);
      });
    }, { threshold: 0.14, rootMargin: '0px 0px -40px 0px' });

    document.querySelectorAll('.vibe-reveal').forEach(function (el) {
      revealObserver.observe(el);
    });
  }

  function setupMicroPress() {
    document.querySelectorAll('button, .chip').forEach(function (el) {
      el.addEventListener('pointerdown', function () {
        el.style.transform = 'translateY(0) scale(0.985)';
      });

      var reset = function () { el.style.transform = ''; };
      el.addEventListener('pointerup', reset);
      el.addEventListener('pointerleave', reset);
      el.addEventListener('blur', reset);
    });
  }

  document.addEventListener('DOMContentLoaded', function () {
    markLazyMedia();
    setupSmoothAnchorScroll();
    setupScrollReveal();
    setupMicroPress();
  });
})();
