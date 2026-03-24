const searchInput = document.getElementById("heroSearchInput");
const suggestionBox = document.getElementById("heroSuggestions");
const searchClear = document.querySelector(".hero-search-clear");
const designData = window.DESIGN_DATA || { categories: [], titles: [] };

function escapeHtml(value) {
  return String(value || "")
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;")
    .replaceAll("'", "&#39;");
}

const menuPairs = [];
document.querySelectorAll(".menu-toggle").forEach((btn) => {
  const wrap = btn.closest(".menu-wrap");
  const menu = wrap ? wrap.querySelector(".menu") : null;
  if (!menu) return;
  menuPairs.push({ btn, menu });

  btn.addEventListener("click", (e) => {
    e.stopPropagation();
    menuPairs.forEach(({ btn: otherBtn, menu: otherMenu }) => {
      if (otherMenu !== menu) {
        otherMenu.classList.remove("open");
        otherBtn.setAttribute("aria-expanded", "false");
      }
    });
    menu.classList.toggle("open");
    btn.setAttribute("aria-expanded", menu.classList.contains("open") ? "true" : "false");
  });
});

if (menuPairs.length > 0) {
  document.addEventListener("click", (e) => {
    menuPairs.forEach(({ btn, menu }) => {
      if (!menu.contains(e.target) && e.target !== btn) {
        menu.classList.remove("open");
        btn.setAttribute("aria-expanded", "false");
      }
    });
  });
}

function normalizeValue(value) {
  return String(value || "").trim().toLowerCase();
}

function bigrams(input) {
  const value = normalizeValue(input).replace(/\s+/g, " ");
  const pairs = [];
  for (let i = 0; i < value.length - 1; i += 1) {
    pairs.push(value.slice(i, i + 2));
  }
  return pairs;
}

function similarityScore(a, b) {
  const x = normalizeValue(a);
  const y = normalizeValue(b);
  if (!x || !y) return 0;
  if (x === y) return 1;
  if (y.includes(x)) return 0.92;
  const bx = bigrams(x);
  const by = bigrams(y);
  if (!bx.length || !by.length) return 0;
  let matches = 0;
  const byCopy = [...by];
  bx.forEach((pair) => {
    const idx = byCopy.indexOf(pair);
    if (idx !== -1) {
      matches += 1;
      byCopy.splice(idx, 1);
    }
  });
  return (2 * matches) / (bx.length + by.length);
}

function buildMatches(items, query, typeLabel) {
  return (items || [])
    .map((item) => ({
      label: item,
      type: typeLabel,
      score: similarityScore(query, item),
    }))
    .filter((item) => item.score >= 0.32)
    .sort((a, b) => b.score - a.score);
}

function uniqueByLabel(list) {
  const seen = new Set();
  return list.filter((item) => {
    const key = item.label.toLowerCase();
    if (seen.has(key)) return false;
    seen.add(key);
    return true;
  });
}

function loadSuggestions() {
  if (!searchInput || !suggestionBox) return;
  const query = searchInput.value.trim();
  if (!query) {
    suggestionBox.innerHTML = "";
    suggestionBox.classList.remove("open");
    return;
  }

  const categoryMatches = buildMatches(designData.categories, query, "Category");
  const titleMatches = buildMatches(designData.titles, query, "Project");
  const combined = uniqueByLabel([...categoryMatches, ...titleMatches]).slice(0, 8);

  suggestionBox.innerHTML = "";
  combined.forEach((item) => {
    const li = document.createElement("li");
    const label = document.createElement("span");
    label.textContent = item.label;
    const tag = document.createElement("span");
    tag.className = "suggestion-type";
    tag.textContent = item.type;
    li.appendChild(label);
    li.appendChild(tag);
    li.addEventListener("mousedown", () => {
      searchInput.value = item.label;
    });
    suggestionBox.appendChild(li);
  });

  if (combined.length > 0) {
    suggestionBox.classList.add("open");
  } else {
    suggestionBox.classList.remove("open");
  }
}

if (searchInput && suggestionBox) {
  const show = () => loadSuggestions();
  const hide = () => {
    setTimeout(() => suggestionBox.classList.remove("open"), 120);
  };

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

function initProjectCard(card) {
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
}

document.querySelectorAll(".project-card").forEach((card) => initProjectCard(card));

// skeleton loading for gallery thumbnails
function setupThumbnailLoading(wrap) {
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
}

document.querySelectorAll(".thumbnail, .thumb-wrap").forEach((wrap) => {
  setupThumbnailLoading(wrap);
});

function setupImageViewer() {
  const viewer = document.getElementById("imageViewer");
  const viewerImage = document.getElementById("viewerImage");
  const viewerTitle = document.getElementById("viewerTitle");
  const viewerDesigner = document.getElementById("viewerDesigner");
  const closeBtn = document.querySelector(".viewer-close");

  if (!viewer || !viewerImage || !closeBtn) return;

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

  document.addEventListener("click", (event) => {
    const thumb = event.target.closest(".thumbnail");
    if (!thumb) return;
    const img = thumb.querySelector("img");
    if (!img) return;
    const title = thumb.dataset.title || "";
    const designer = thumb.dataset.designer || "";
    openViewer(img.src, img.alt, title, designer);
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
document.addEventListener("click", (event) => {
  const btn = event.target.closest(".action-btn");
  if (!btn) return;
  btn.classList.remove("is-anim");
  void btn.offsetWidth;
  btn.classList.add("is-anim");
});

document.addEventListener("animationend", (event) => {
  const btn = event.target;
  if (!(btn instanceof HTMLElement)) return;
  if (!btn.classList.contains("action-btn")) return;
  btn.classList.remove("is-anim");
});

function getCookieValue(name) {
  const cookies = document.cookie ? document.cookie.split(";") : [];
  for (let i = 0; i < cookies.length; i += 1) {
    const cookie = cookies[i].trim();
    if (cookie.startsWith(`${name}=`)) {
      return decodeURIComponent(cookie.slice(name.length + 1));
    }
  }
  return "";
}

function getCsrfToken(form) {
  const formToken =
    form?.querySelector('input[name="csrf_token"]') ||
    form?.querySelector('input[name="csrfmiddlewaretoken"]');
  if (formToken?.value) return formToken.value;

  const metaToken =
    document.querySelector('meta[name="csrf-token"]') ||
    document.querySelector('meta[name="csrfmiddlewaretoken"]');
  if (metaToken?.getAttribute("content")) return metaToken.getAttribute("content");

  return (
    getCookieValue("csrf_token") ||
    getCookieValue("csrftoken") ||
    getCookieValue("csrf")
  );
}

function resolveActionType(actionUrl, button) {
  if (button?.classList.contains("action-follow-btn") || button?.classList.contains("designer-follow-btn")) {
    return "follow";
  }
  if (button?.classList.contains("action-like-btn")) return "like";
  if (button?.classList.contains("action-wishlist-btn")) return "wishlist";
  if (actionUrl.includes("/follow/")) return "follow";
  if (actionUrl.includes("/like/")) return "like";
  if (actionUrl.includes("/wishlist/")) return "wishlist";
  return "";
}

function resolveActiveState(actionType, data) {
  if (!data || typeof data !== "object") return null;
  if (typeof data.active === "boolean") return data.active;
  if (typeof data.is_active === "boolean") return data.is_active;

  const map = {
    follow: ["following", "is_following", "followed"],
    like: ["liked", "is_liked"],
    wishlist: ["wishlisted", "is_wishlisted", "starred"],
  };
  const keys = map[actionType] || [];
  for (let i = 0; i < keys.length; i += 1) {
    const value = data[keys[i]];
    if (typeof value === "boolean") return value;
  }
  return null;
}

function resolveCount(actionType, data) {
  if (!data || typeof data !== "object") return null;
  if (typeof data.count === "number") return data.count;
  const map = {
    follow: ["followers_count", "follower_count"],
    like: ["likes_count", "like_count"],
    wishlist: ["wishlist_count", "stars_count", "star_count", "saves_count"],
  };
  const keys = map[actionType] || [];
  for (let i = 0; i < keys.length; i += 1) {
    const value = data[keys[i]];
    if (typeof value === "number") return value;
  }
  return null;
}

function updateActionButtonState(button, actionType, isActive, payload) {
  if (!button || typeof isActive !== "boolean") return;

  if (button.classList.contains("action-btn")) {
    button.classList.toggle("is-active", isActive);
    button.classList.toggle("is-filled", !isActive);
    button.setAttribute("aria-pressed", isActive ? "true" : "false");
  }

  if (button.classList.contains("designer-follow-btn")) {
    button.classList.toggle("is-following", isActive);
    if (payload && typeof payload.label === "string") {
      button.textContent = payload.label;
    }
  }
}

function updateActionCount(button, actionType, count) {
  if (typeof count !== "number") return;
  const explicitTarget = button?.getAttribute("data-count-target");
  const scope = button?.closest(".project-card") || button?.closest(".profile-restore-sidebar") || document;
  const target = explicitTarget ? document.querySelector(explicitTarget) : null;
  const fallback = scope.querySelector(
    actionType === "follow"
      ? "[data-followers-count]"
      : actionType === "like"
      ? "[data-likes-count]"
      : "[data-wishlist-count]"
  );
  const el = target || fallback;
  if (el) {
    el.textContent = `${count}`;
  }
}

function getCurrentActiveState(button) {
  if (!button) return false;
  if (button.classList.contains("designer-follow-btn")) {
    return button.classList.contains("is-following");
  }
  if (button.classList.contains("action-btn")) {
    return button.classList.contains("is-active");
  }
  const pressed = button.getAttribute("aria-pressed");
  return pressed === "true";
}

async function handleActionSubmit(event) {
  const form = event.target;
  if (!(form instanceof HTMLFormElement)) return;

  const button = form.querySelector("button[type='submit']");
  if (!button) return;

  const isSupported =
    button.classList.contains("action-follow-btn") ||
    button.classList.contains("action-like-btn") ||
    button.classList.contains("action-wishlist-btn") ||
    button.classList.contains("designer-follow-btn");

  if (!isSupported) return;

  event.preventDefault();

  if (button.disabled || button.getAttribute("data-ajax-pending") === "true") {
    return;
  }

  const actionUrl = form.getAttribute("action") || "";
  const method = (form.getAttribute("method") || "post").toUpperCase();
  const actionType = resolveActionType(actionUrl, button);
  const csrfToken = getCsrfToken(form);

  button.disabled = true;
  button.setAttribute("data-ajax-pending", "true");

  try {
    const fetchOptions = {
      method,
      headers: {
        "X-Requested-With": "XMLHttpRequest",
      },
      credentials: "same-origin",
    };

    if (csrfToken) {
      fetchOptions.headers["X-CSRF-Token"] = csrfToken;
    }

    if (method !== "GET") {
      const formData = new FormData(form);
      if (csrfToken && !formData.has("csrf_token") && !formData.has("csrfmiddlewaretoken")) {
        formData.append("csrf_token", csrfToken);
      }
      fetchOptions.body = formData;
    }

    const response = await fetch(actionUrl, fetchOptions);
    if (!response.ok) {
      if (response.redirected && response.url) {
        window.location.assign(response.url);
      } else {
        form.submit();
      }
      return;
    }

    const contentType = response.headers.get("content-type") || "";
    if (!contentType.includes("application/json")) {
      const current = getCurrentActiveState(button);
      updateActionButtonState(button, actionType, !current, null);
      return;
    }

    const data = await response.json();
    const nextActive = resolveActiveState(actionType, data);
    const nextCount = resolveCount(actionType, data);
    updateActionButtonState(button, actionType, nextActive, data);
    updateActionCount(button, actionType, nextCount);
  } catch (err) {
    if (form) form.submit();
  } finally {
    button.disabled = false;
    button.removeAttribute("data-ajax-pending");
  }
}

document.addEventListener("submit", (event) => {
  const form = event.target;
  if (!(form instanceof HTMLFormElement)) return;
  if (!form.matches("form.action-form, form.designer-follow-form")) return;
  handleActionSubmit(event);
});

function buildProjectCard(item, auth) {
  const title = escapeHtml(item.title);
  const designerName = escapeHtml(item.designer.name);
  const profileUrl = item.designer.profile_url;
  const avatarUrl = item.designer.avatar_url;
  const imageUrl = item.image_url;
  const isFollowing = Boolean(item.is_following);
  const isLiked = Boolean(item.is_liked);
  const isWishlisted = Boolean(item.is_wishlisted);
  const canShowFollow = Boolean(item.can_show_follow);
  const loggedIn = Boolean(auth?.is_logged_in);

  const followButton = canShowFollow
    ? `
      <form method="post" action="/action/follow/${item.designer.id}" class="action-form">
        <button type="submit" class="action-btn action-follow-btn ${isFollowing ? "is-active" : "is-filled"}" aria-pressed="${
          isFollowing ? "true" : "false"
        }">
          <svg class="action-icon icon-solid" viewBox="0 0 24 24" aria-hidden="true">
            <path d="M10 12a4 4 0 1 0-4-4 4 4 0 0 0 4 4z"></path>
            <path d="M3.5 20.5c0-3.1 2.6-5.6 5.8-5.6h1.4c3.2 0 5.8 2.5 5.8 5.6v1H3.5z"></path>
            <path d="M19 4.5v3h-3v2h3v3h2v-3h3v-2h-3v-3z"></path>
          </svg>
          <svg class="action-icon icon-outline" viewBox="0 0 24 24" aria-hidden="true">
            <circle cx="9" cy="7" r="3"></circle>
            <path d="M3 20c0-3.1 2.6-5.6 5.8-5.6h1.4C13.4 14.4 16 16.9 16 20v1H3z"></path>
            <path d="M19 4.5v3h-3v2h3v3h2v-3h3v-2h-3v-3z"></path>
          </svg>
          <span class="sr-only">Follow</span>
        </button>
      </form>
    `
    : "";

  const likeForm = `
    <form method="post" action="/action/like/${item.id}" class="action-form">
      <button type="submit" class="action-btn action-like-btn ${isLiked ? "is-active" : "is-filled"}" aria-pressed="${
        isLiked ? "true" : "false"
      }">
        <svg class="action-icon icon-solid" viewBox="0 0 24 24" aria-hidden="true">
          <path d="M2 10h4v12H2z"></path>
          <path d="M22 10.5v7.5a2.5 2.5 0 0 1-2.5 2.5H9.2a2 2 0 0 1-2-2v-8.7l3.7-6.4a2 2 0 0 1 1.7-.9h1.4a1.5 1.5 0 0 1 1.5 1.8l-.7 4.2h5.2A2.5 2.5 0 0 1 22 10.5z"></path>
        </svg>
        <svg class="action-icon icon-outline" viewBox="0 0 24 24" aria-hidden="true">
          <path d="M2 10h4v12H2z"></path>
          <path d="M22 10.5v7.5a2.5 2.5 0 0 1-2.5 2.5H9.2a2 2 0 0 1-2-2v-8.7l3.7-6.4a2 2 0 0 1 1.7-.9h1.4a1.5 1.5 0 0 1 1.5 1.8l-.7 4.2h5.2A2.5 2.5 0 0 1 22 10.5z"></path>
        </svg>
        <span class="sr-only">Like</span>
      </button>
    </form>
  `;

  const wishlistForm = `
    <div class="wishlist-control">
      <form method="post" action="/action/wishlist/${item.id}" class="action-form wishlist-form">
        <input type="hidden" name="rating" value="1">
        <button type="submit" class="action-btn action-wishlist-btn ${isWishlisted ? "is-active" : "is-filled"}" aria-pressed="${
          isWishlisted ? "true" : "false"
        }">
          <svg class="action-icon icon-solid" viewBox="0 0 24 24" aria-hidden="true">
            <path d="M12 2.5l2.9 5.9 6.5.9-4.7 4.5 1.1 6.4-5.8-3.1-5.8 3.1 1.1-6.4-4.7-4.5 6.5-.9z"></path>
          </svg>
          <svg class="action-icon icon-outline" viewBox="0 0 24 24" aria-hidden="true">
            <path d="M12 3.2l2.6 5.4 6 .9-4.3 4.1 1 5.8-5.3-2.8-5.3 2.8 1-5.8-4.3-4.1 6-.9z"></path>
          </svg>
          <span class="sr-only">Wishlist</span>
        </button>
      </form>
    </div>
  `;

  const guestButtons = `
    ${canShowFollow ? `
      <a href="/login" class="action-btn action-follow-btn is-filled" aria-label="Login to follow">
        <svg class="action-icon icon-solid" viewBox="0 0 24 24" aria-hidden="true">
          <path d="M10 12a4 4 0 1 0-4-4 4 4 0 0 0 4 4z"></path>
          <path d="M3.5 20.5c0-3.1 2.6-5.6 5.8-5.6h1.4c3.2 0 5.8 2.5 5.8 5.6v1H3.5z"></path>
          <path d="M19 4.5v3h-3v2h3v3h2v-3h3v-2h-3v-3z"></path>
        </svg>
        <svg class="action-icon icon-outline" viewBox="0 0 24 24" aria-hidden="true">
          <circle cx="9" cy="7" r="3"></circle>
          <path d="M3 20c0-3.1 2.6-5.6 5.8-5.6h1.4C13.4 14.4 16 16.9 16 20v1H3z"></path>
          <path d="M19 4.5v3h-3v2h3v3h2v-3h3v-2h-3v-3z"></path>
        </svg>
        <span class="sr-only">Follow</span>
      </a>
    ` : ""}
    <a href="/login" class="action-btn action-like-btn is-filled" aria-label="Login to like">
      <svg class="action-icon icon-solid" viewBox="0 0 24 24" aria-hidden="true">
        <path d="M2 10h4v12H2z"></path>
        <path d="M22 10.5v7.5a2.5 2.5 0 0 1-2.5 2.5H9.2a2 2 0 0 1-2-2v-8.7l3.7-6.4a2 2 0 0 1 1.7-.9h1.4a1.5 1.5 0 0 1 1.5 1.8l-.7 4.2h5.2A2.5 2.5 0 0 1 22 10.5z"></path>
      </svg>
      <svg class="action-icon icon-outline" viewBox="0 0 24 24" aria-hidden="true">
        <path d="M2 10h4v12H2z"></path>
        <path d="M22 10.5v7.5a2.5 2.5 0 0 1-2.5 2.5H9.2a2 2 0 0 1-2-2v-8.7l3.7-6.4a2 2 0 0 1 1.7-.9h1.4a1.5 1.5 0 0 1 1.5 1.8l-.7 4.2h5.2A2.5 2.5 0 0 1 22 10.5z"></path>
      </svg>
      <span class="sr-only">Like</span>
    </a>
    <div class="wishlist-control">
      <a href="/login" class="action-btn action-wishlist-btn is-filled" aria-label="Login to wishlist">
        <svg class="action-icon icon-solid" viewBox="0 0 24 24" aria-hidden="true">
          <path d="M12 2.5l2.9 5.9 6.5.9-4.7 4.5 1.1 6.4-5.8-3.1-5.8 3.1 1.1-6.4-4.7-4.5 6.5-.9z"></path>
        </svg>
        <svg class="action-icon icon-outline" viewBox="0 0 24 24" aria-hidden="true">
          <path d="M12 3.2l2.6 5.4 6 .9-4.3 4.1 1 5.8-5.3-2.8-5.3 2.8 1-5.8-4.3-4.1 6-.9z"></path>
        </svg>
        <span class="sr-only">Wishlist</span>
      </a>
    </div>
  `;

  const actions = loggedIn
    ? `
      ${followButton}
      ${likeForm}
      ${wishlistForm}
    `
    : guestButtons;

  const wrapper = document.createElement("article");
  wrapper.className = "card project-card";
  wrapper.innerHTML = `
    <div class="thumb-wrap thumbnail" data-title="${title}" data-designer="${designerName}">
      <img src="${imageUrl}" alt="${title}" class="thumb">
      <div class="thumb-title project-title-overlay">${title}</div>
    </div>

    <div class="designer-row">
      <div class="designer-info">
        <a href="${profileUrl}" class="designer-link designer-name">${designerName}</a>
        <a href="${profileUrl}" class="designer-avatar-link" data-designer-id="${item.designer.id}" aria-label="${designerName} profile">
          <img class="designer-avatar" src="${avatarUrl}" alt="${designerName}">
        </a>
        <div class="popup designer-popup"></div>
      </div>

      <div class="card-actions action-cluster">
        <div class="action-grid">
          ${actions}
        </div>
      </div>
    </div>
  `;
  return wrapper;
}

function setupInfiniteScroll() {
  const grid = document.querySelector(".gallery-grid");
  if (!grid) return;

  const observerTarget = document.createElement("div");
  observerTarget.setAttribute("data-infinite-sentinel", "true");
  grid.parentElement?.appendChild(observerTarget);

  const endNote = document.createElement("p");
  endNote.className = "muted";
  endNote.textContent = "No more designs.";
  endNote.hidden = true;
  grid.parentElement?.appendChild(endNote);

  let page = 2;
  let loading = false;
  let hasMore = true;
  let activeSkeletons = [];

  const params = new URLSearchParams(window.location.search);
  const baseParams = new URLSearchParams();
  if (params.get("q")) baseParams.set("q", params.get("q"));
  if (params.get("category")) baseParams.set("category", params.get("category"));

  const perAttr = Number(grid.getAttribute("data-infinite-per") || window.INFINITE_SCROLL_PER);
  const perQuery = Number(params.get("per"));
  const per = Number.isFinite(perAttr) && perAttr > 0 ? perAttr : Number.isFinite(perQuery) && perQuery > 0 ? perQuery : 12;
  const skeletonCount = Math.min(per, 6);
  baseParams.set("per", `${per}`);

  const showSkeletons = () => {
    if (activeSkeletons.length > 0) return;
    const fragment = document.createDocumentFragment();
    for (let i = 0; i < skeletonCount; i += 1) {
      const card = document.createElement("article");
      card.className = "card project-card";
      card.setAttribute("data-skeleton", "true");
      card.innerHTML = `
        <div class="thumb-wrap thumbnail is-loading">
          <img class="thumb" alt="" src="data:image/gif;base64,R0lGODlhAQABAIAAAAAAAP///ywAAAAAAQABAAACAUwAOw==">
        </div>
        <div class="designer-row">
          <div class="designer-info">
            <span class="designer-link designer-name">&nbsp;</span>
          </div>
        </div>
      `;
      activeSkeletons.push(card);
      fragment.appendChild(card);
    }
    grid.appendChild(fragment);
  };

  const clearSkeletons = () => {
    activeSkeletons.forEach((card) => card.remove());
    activeSkeletons = [];
  };

  const loadNext = async () => {
    if (loading || !hasMore) return;
    loading = true;
    showSkeletons();
    baseParams.set("page", `${page}`);

    try {
      const res = await fetch(`/api/projects?${baseParams.toString()}`, {
        headers: { "X-Requested-With": "XMLHttpRequest" },
        credentials: "same-origin",
      });
      if (!res.ok) {
        clearSkeletons();
        loading = false;
        return;
      }
      const data = await res.json();
      const items = Array.isArray(data.items) ? data.items : [];
      const auth = data.auth || {};

      if (items.length === 0) {
        clearSkeletons();
        hasMore = false;
        endNote.hidden = false;
        loading = false;
        return;
      }

      clearSkeletons();
      items.forEach((item) => {
        const card = buildProjectCard(item, auth);
        grid.appendChild(card);
        initProjectCard(card);
        const wrap = card.querySelector(".thumbnail, .thumb-wrap");
        if (wrap) setupThumbnailLoading(wrap);
      });

      hasMore = Boolean(data.has_more);
      if (!hasMore) {
        endNote.hidden = false;
      }
      page += 1;
      loading = false;
    } catch (err) {
      clearSkeletons();
      loading = false;
    }
  };

  const observer = new IntersectionObserver(
    (entries) => {
      entries.forEach((entry) => {
        if (entry.isIntersecting) {
          loadNext();
        }
      });
    },
    { rootMargin: "300px 0px", threshold: 0.01 }
  );

  observer.observe(observerTarget);
}

setupInfiniteScroll();

function setupProfileCropper() {
  const inputs = [
    document.getElementById("profileImageInput"),
    document.getElementById("viewerImageInput"),
  ].filter(Boolean);

  if (!inputs.length) return;

  const modal = document.createElement("div");
  modal.className = "profile-cropper-modal";
  modal.innerHTML = `
    <div class="cropper-backdrop"></div>
    <div class="cropper-panel" role="dialog" aria-modal="true" aria-label="Crop profile photo">
      <div class="cropper-header">
        <button type="button" class="cropper-close" aria-label="Close">&times;</button>
        <div class="cropper-title">Drag the image to adjust</div>
        <div class="cropper-header-actions">
          <button type="button" class="cropper-undo" aria-label="Undo">↺</button>
          <button type="button" class="cropper-upload">Upload</button>
        </div>
      </div>
      <div class="cropper-body">
        <div class="cropper-viewport">
          <img class="cropper-image" alt="Crop preview">
        </div>
        <div class="cropper-zoom-fab">
          <button type="button" class="cropper-zoom-btn" data-zoom="in" aria-label="Zoom in">+</button>
          <button type="button" class="cropper-zoom-btn" data-zoom="out" aria-label="Zoom out">−</button>
        </div>
      </div>
      <div class="cropper-footer">
        <button type="button" class="cropper-save" aria-label="Save">
          ✓
        </button>
      </div>
    </div>
  `;
  document.body.appendChild(modal);

  const backdrop = modal.querySelector(".cropper-backdrop");
  const closeBtn = modal.querySelector(".cropper-close");
  const undoBtn = modal.querySelector(".cropper-undo");
  const uploadBtn = modal.querySelector(".cropper-upload");
  const saveBtn = modal.querySelector(".cropper-save");
  const zoomButtons = modal.querySelectorAll(".cropper-zoom-btn");
  const image = modal.querySelector(".cropper-image");

  let activeInput = null;
  let activeForm = null;
  let cropper = null;

  const openModal = () => {
    modal.classList.add("show");
    document.body.classList.add("no-scroll");
  };

  const closeModal = () => {
    modal.classList.remove("show");
    document.body.classList.remove("no-scroll");
    if (cropper) {
      cropper.destroy();
      cropper = null;
    }
    if (image) image.src = "";
    activeInput = null;
    activeForm = null;
  };

  const ensureCropper = () => {
    if (typeof Cropper === "undefined") {
      return null;
    }
    if (cropper) {
      cropper.destroy();
      cropper = null;
    }
    cropper = new Cropper(image, {
      aspectRatio: 1,
      viewMode: 1,
      dragMode: "move",
      cropBoxMovable: false,
      cropBoxResizable: false,
      guides: false,
      center: false,
      highlight: false,
      background: false,
      autoCropArea: 1,
      zoomOnWheel: true,
      toggleDragModeOnDblclick: false,
      ready() {
        const container = cropper.getContainerData();
        const padding = 84;
        const size = Math.min(container.width, container.height) - padding * 2;
        const offsetY = 480;
        cropper.setCropBoxData({
          width: size,
          height: size,
          left: (container.width - size) / 2,
          top: Math.max(0, (container.height - size) / 2 - offsetY),
        });
      },
    });
    return cropper;
  };

  const handleFile = (input, file) => {
    if (!file) return;
    activeInput = input;
    activeForm = input.form;
    const reader = new FileReader();
    reader.onload = () => {
      image.src = reader.result;
    };
    reader.readAsDataURL(file);
  };

  image.addEventListener("load", () => {
    openModal();
    const instance = ensureCropper();
    if (!instance) {
      closeModal();
      if (activeForm) activeForm.submit();
    }
  });

  const cancel = () => {
    if (activeInput) activeInput.value = "";
    closeModal();
  };

  const save = async () => {
    if (!activeInput || !activeForm || !cropper) return;
    const canvas = cropper.getCroppedCanvas({ width: 512, height: 512 });
    if (!canvas) return;
    canvas.toBlob(async (blob) => {
      if (!blob) return;
      const file = new File([blob], "profile.png", { type: "image/png" });
      const formData = new FormData();
      formData.append(activeInput.name || "profile_image", file);

      try {
        const response = await fetch(activeForm.action, {
          method: activeForm.method || "POST",
          body: formData,
        });
        if (response.redirected) {
          window.location.href = response.url;
          return;
        }
        if (response.ok) {
          window.location.reload();
          return;
        }
        throw new Error("Upload failed");
      } catch (err) {
        const dt = new DataTransfer();
        dt.items.add(file);
        activeInput.files = dt.files;
        activeForm.submit();
      }
    }, "image/png");
    closeModal();
  };

  const triggerUpload = () => {
    if (activeInput) activeInput.click();
  };

  zoomButtons.forEach((btn) => {
    btn.addEventListener("click", () => {
      if (!cropper) return;
      const direction = btn.getAttribute("data-zoom");
      const step = 0.12;
      cropper.zoom(direction === "in" ? step : -step);
    });
  });

  backdrop.addEventListener("click", cancel);
  closeBtn.addEventListener("click", cancel);
  if (undoBtn) undoBtn.addEventListener("click", () => cropper && cropper.reset());
  if (uploadBtn) uploadBtn.addEventListener("click", triggerUpload);
  saveBtn.addEventListener("click", save);
  document.addEventListener("keydown", (event) => {
    if (modal.classList.contains("show") && event.key === "Escape") {
      cancel();
    }
  });

  inputs.forEach((input) => {
    input.onchange = null;
    input.removeAttribute("onchange");
    input.addEventListener("change", () => {
      const file = input.files && input.files[0];
      if (!file) return;
      handleFile(input, file);
    });
  });
}

setupProfileCropper();


