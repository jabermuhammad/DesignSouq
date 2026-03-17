const accountBtn = document.getElementById("accountBtn");
const accountMenu = document.getElementById("accountMenu");
const searchInput = document.getElementById("searchInput");
const suggestionBox = document.getElementById("suggestions");
const searchClear = document.querySelector(".search-clear");

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

if (searchInput && searchClear) {
  const syncClear = () => {
    if (searchInput.value.trim().length > 0) {
      searchClear.classList.add("show");
    } else {
      searchClear.classList.remove("show");
    }
  };
  syncClear();
  searchInput.addEventListener("input", syncClear);
  searchClear.addEventListener("click", () => {
    searchInput.value = "";
    syncClear();
    suggestionBox?.classList.remove("open");
    searchInput.focus();
  });
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

// skeleton loading for gallery thumbnails
document.querySelectorAll(".thumbnail, .thumb-wrap").forEach((wrap) => {
  const img = wrap.querySelector("img");
  if (!img) return;
  wrap.classList.add("is-loading");
  const done = () => wrap.classList.remove("is-loading");
  if (img.complete) {
    done();
  } else {
    img.addEventListener("load", done, { once: true });
    img.addEventListener("error", done, { once: true });
  }
});

function setupImageViewer() {
  const viewer = document.getElementById("imageViewer");
  const viewerImage = document.getElementById("viewerImage");
  const viewerTitle = document.getElementById("viewerTitle");
  const viewerDesigner = document.getElementById("viewerDesigner");
  const closeBtn = document.querySelector(".viewer-close");
  const thumbs = Array.from(document.querySelectorAll(".thumbnail"));

  if (!viewer || !viewerImage || !closeBtn || !thumbs.length) return;

  const openViewer = (src, alt, title, designer) => {
    viewerImage.src = src;
    viewerImage.alt = alt || "Fullscreen preview";
    viewerImage.classList.remove("zoomed");
    if (viewerTitle) viewerTitle.textContent = title || "";
    if (viewerDesigner) viewerDesigner.textContent = designer ? `by ${designer}` : "";
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
      const title = thumb.dataset.title || "";
      const designer = thumb.dataset.designer || "";
      openViewer(img.src, img.alt, title, designer);
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

// wishlist handled by server toggle (form submit)

// no wishlist JS needed

// micro-animations for action buttons
document.querySelectorAll(".action-btn").forEach((btn) => {
  btn.addEventListener("click", () => {
    btn.classList.remove("is-anim");
    void btn.offsetWidth;
    btn.classList.add("is-anim");
  });
  btn.addEventListener("animationend", () => {
    btn.classList.remove("is-anim");
  });
});

