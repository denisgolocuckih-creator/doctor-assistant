/* =========================================================================
   СОСТОЯНИЕ И НАСТРОЙКИ ПРИЛОЖЕНИЯ
========================================================================= */
const appConfig = {
  lang: "ru",
  displayMode: "light",
  glare: true,
  blur: true,
  particles: true,
  particlesCount: 24,
  showInn: true,
  paperSize: "A4",
  useRxPrefix: true,
  printBorder: true,
  currentHue: 216
};

let activeCategory = "Все";
let selectedDisease = "";
let activeAnalogInn = null;
let pendingDrugIdForPreset = null;
let openedPresetId = null;
let presetIdToDelete = null;
let presetsViewMode = "grid";
let innerPresetViewMode = "list";

let userPresets = [
  {
    id: "preset-1",
    name: "ОРВИ и температура",
    items: [{ ...DRUGS_DB[0] }, { ...DRUGS_DB[20] }, { ...DRUGS_DB[70] }]
  },
  {
    id: "preset-2",
    name: "Гастрит и спазмы ЖКТ",
    items: [{ ...DRUGS_DB[30] }, { ...DRUGS_DB[43] }]
  }
];

function t(key) {
  return (I18N[appConfig.lang] && I18N[appConfig.lang][key]) || I18N.ru[key] || key;
}

/* Собираем все уникальные болезни из базы Минздрава РФ для автодополнения */
const ALL_DISEASES = (() => {
  const map = new Map();
  DRUGS_DB.forEach(drug => {
    drug.diseases.split(",").forEach(raw => {
      const clean = raw.trim();
      if (!clean) return;
      const formatted = clean.charAt(0).toUpperCase() + clean.slice(1);
      const key = formatted.toLowerCase();
      if (!map.has(key)) map.set(key, { name: formatted, count: 0 });
      map.get(key).count++;
    });
  });
  return Array.from(map.values()).sort((a, b) => a.name.localeCompare(b.name, "ru"));
})();

/* =========================================================================
   ЛЕТАЮЩИЕ ШАРИКИ НА ФОНЕ
========================================================================= */
let particlesArray = [];
let mousePos = { x: -1000, y: -1000 };

function createParticles(count) {
  particlesArray = [];
  const w = window.innerWidth || 1280;
  const h = window.innerHeight || 800;
  for (let i = 0; i < count; i++) {
    particlesArray.push({
      x: Math.random() * w,
      y: Math.random() * h,
      r: 20 + Math.random() * 48,
      vx: (Math.random() - 0.5) * 0.55,
      vy: (Math.random() - 0.5) * 0.55,
      alpha: 0.14 + Math.random() * 0.18
    });
  }
}

function initBackgroundParticles() {
  const canvas = document.getElementById("bgParticles");
  if (!canvas) return;
  const ctx = canvas.getContext("2d");

  const resize = () => {
    canvas.width = window.innerWidth;
    canvas.height = window.innerHeight;
  };
  resize();
  window.addEventListener("resize", resize);
  window.addEventListener("mousemove", (e) => {
    mousePos.x = e.clientX;
    mousePos.y = e.clientY;
  });

  createParticles(appConfig.particlesCount);

  function animate() {
    ctx.clearRect(0, 0, canvas.width, canvas.height);
    if (appConfig.particles && appConfig.displayMode !== "a11y") {
      for (const p of particlesArray) {
        p.x += p.vx;
        p.y += p.vy;
        if (p.x - p.r > canvas.width) p.x = -p.r;
        if (p.x + p.r < 0) p.x = canvas.width + p.r;
        if (p.y - p.r > canvas.height) p.y = -p.r;
        if (p.y + p.r < 0) p.y = canvas.height + p.r;

        const dx = p.x - mousePos.x;
        const dy = p.y - mousePos.y;
        const dist = Math.sqrt(dx * dx + dy * dy);
        if (dist < 130 && dist > 0) {
          p.x += (dx / dist) * 0.7;
          p.y += (dy / dist) * 0.7;
        }

        const g = ctx.createRadialGradient(p.x, p.y, p.r * 0.1, p.x, p.y, p.r);
        g.addColorStop(0, `rgba(255, 255, 255, ${p.alpha + 0.14})`);
        g.addColorStop(0.55, `hsla(${appConfig.currentHue}, 55%, 66%, ${p.alpha})`);
        g.addColorStop(1, "rgba(120, 148, 220, 0)");

        ctx.beginPath();
        ctx.arc(p.x, p.y, p.r, 0, Math.PI * 2);
        ctx.fillStyle = g;
        ctx.fill();
      }
    }
    requestAnimationFrame(animate);
  }
  animate();
}

function toggleBackgroundParticles(enabled) {
  appConfig.particles = enabled;
}

function updateParticlesCount(val) {
  appConfig.particlesCount = Number(val);
  createParticles(appConfig.particlesCount);
}

/* =========================================================================
   ПОИСК СТРОГО ПО БОЛЕЗНЯМ ЧЕРЕЗ ВЫПАДАЮЩИЙ ПРЯМОУГОЛЬНИК СОВПАДЕНИЙ
========================================================================= */
function getDrugSVG(drug) {
  return `
    <svg viewBox="0 0 180 140" xmlns="http://www.w3.org/2000/svg">
      <rect x="16" y="20" width="118" height="82" rx="14" fill="#ffffff" stroke="#334155" stroke-width="1.6"/>
      <rect x="16" y="20" width="118" height="24" rx="12" fill="${drug.color}"/>
      <circle cx="34" cy="32" r="5.5" fill="#fff" opacity="0.9"/>
      <rect x="46" y="29" width="66" height="6" rx="3" fill="#fff" opacity="0.9"/>
      <text x="28" y="65" font-size="12.5" font-weight="bold" fill="#1e293b">${drug.name.slice(0, 15)}</text>
      <text x="28" y="82" font-size="9.5" fill="#475569">${drug.subtitle.slice(0, 20)}</text>
      <rect x="106" y="54" width="56" height="68" rx="12" fill="#f8fafc" stroke="#64748b" stroke-width="1.5"/>
      <circle cx="122" cy="73" r="8" fill="${drug.color}" opacity="0.9"/>
      <circle cx="145" cy="73" r="8" fill="${drug.color}" opacity="0.9"/>
      <circle cx="122" cy="100" r="8" fill="${drug.color}" opacity="0.9"/>
      <circle cx="145" cy="100" r="8" fill="${drug.color}" opacity="0.9"/>
    </svg>`;
}

function renderDiseaseSuggestions(queryText) {
  const box = document.getElementById("diseaseSuggestionsBox");
  const q = queryText.trim().toLowerCase();

  if (!q) {
    box.classList.remove("open");
    return;
  }

  // Сначала болезни, начинающиеся на введенные буквы, затем содержащие их
  const startsWith = ALL_DISEASES.filter(d => d.name.toLowerCase().startsWith(q));
  const includes = ALL_DISEASES.filter(d => !d.name.toLowerCase().startsWith(q) && d.name.toLowerCase().includes(q));
  const matches = [...startsWith, ...includes].slice(0, 10);

  if (matches.length === 0) {
    box.innerHTML = `<div style="padding:10px 16px; font-size:13.5px; color:var(--text-muted);">Совпадений по болезням не найдено</div>`;
    box.classList.add("open");
    return;
  }

  box.innerHTML = matches.map(item => `
    <button class="disease-suggest-item" type="button" onclick="selectDiseaseFromList('${item.name.replace(/'/g, "\\'")}')">
      <span>${item.name}</span>
      <span class="disease-suggest-count">Препаратов: ${item.count}</span>
    </button>
  `).join("");

  box.classList.add("open");
}

function selectDiseaseFromList(diseaseName) {
  selectedDisease = diseaseName;
  activeCategory = "Все";
  activeAnalogInn = null;
  document.getElementById("searchInput").value = diseaseName;
  document.getElementById("filterBtn").textContent = t("filter_btn");
  document.getElementById("diseaseSuggestionsBox").classList.remove("open");
  document.getElementById("resetAnalogBtn").style.display = "none";
  initFilterOptions();
  openResultsView();
}

function initFilterOptions() {
  const categories = ["Все", ...new Set(DRUGS_DB.map(d => d.category))];
  document.getElementById("filterDropdown").innerHTML = categories.map(cat => `
    <button class="filter-option ${cat === activeCategory ? 'active' : ''}" onclick="applyCategory('${cat}')">
      ${cat === 'Все' ? 'Все группы' : cat}
    </button>
  `).join("");
}

function applyCategory(cat) {
  activeCategory = cat;
  selectedDisease = "";
  activeAnalogInn = null;
  document.getElementById("searchInput").value = "";
  document.getElementById("resetAnalogBtn").style.display = "none";
  document.getElementById("filterBtn").textContent = cat === "Все" ? t("filter_btn") : cat;
  document.getElementById("filterDropdown").classList.remove("open");
  document.getElementById("diseaseSuggestionsBox").classList.remove("open");
  initFilterOptions();
  openResultsView();
}

function openResultsView() {
  document.getElementById("heroSection").classList.add("compact");
  document.getElementById("resultsContainer").classList.add("visible");
  renderCards();
}

function resetToHero() {
  selectedDisease = "";
  activeAnalogInn = null;
  document.getElementById("searchInput").value = "";
  document.getElementById("heroSection").classList.remove("compact");
  document.getElementById("resultsContainer").classList.remove("visible");
  document.getElementById("filterDropdown").classList.remove("open");
  document.getElementById("diseaseSuggestionsBox").classList.remove("open");
}

function renderCards() {
  const sortEl = document.getElementById("sortSelect");
  const sortMode = sortEl ? sortEl.value : "id";
  const diseaseLower = selectedDisease.trim().toLowerCase();

  let list = DRUGS_DB.filter(d => {
    if (activeAnalogInn) return d.inn === activeAnalogInn;
    const matchCat = activeCategory === "Все" || d.category === activeCategory;
    if (!diseaseLower) return matchCat;
    return matchCat && d.diseases.toLowerCase().includes(diseaseLower);
  });

  if (sortMode === "alpha") list.sort((a, b) => a.name.localeCompare(b.name, "ru"));
  else if (sortMode === "category") list.sort((a, b) => a.category.localeCompare(b.category, "ru"));

  const titlePrefix = activeAnalogInn
    ? `Аналоги (${activeAnalogInn})`
    : selectedDisease
      ? `Болезнь: ${selectedDisease}`
      : activeCategory !== "Все"
        ? activeCategory
        : t("results_prefix");

  document.getElementById("resultsLabel").textContent = `${titlePrefix} — найдено: ${list.length}`;

  const grid = document.getElementById("cardsGrid");
  if (list.length === 0) {
    grid.innerHTML = `<div style="grid-column:1/-1; text-align:center; padding:36px;">Препараты по данному заболеванию не найдены.</div>`;
    return;
  }

  grid.innerHTML = list.map(drug => `
    <article class="drug-card ${appConfig.glare ? 'glare-active' : ''}" onclick="openDetailModal(${drug.id})" onmousemove="handleGlare(event, this)">
      <div class="card-thumb">${getDrugSVG(drug)}</div>
      <div class="card-body">
        <span class="card-category">${drug.category}</span>
        <h3 class="card-title">${drug.name}</h3>
        ${appConfig.showInn ? `<span class="card-inn">МНН: ${drug.inn}</span>` : ''}
        <div class="card-diseases">Болезни: ${drug.diseases}</div>
      </div>
      <button class="card-preset-btn" onclick="event.stopPropagation(); openPresetPicker(${drug.id})">
        ${t("btn_add_to_preset")}
      </button>
    </article>
  `).join("");
}

function handleGlare(e, card) {
  const r = card.getBoundingClientRect();
  card.style.setProperty("--mouse-x", `${e.clientX - r.left}px`);
  card.style.setProperty("--mouse-y", `${e.clientY - r.top}px`);
}

function setCatalogView(mode, iconChar) {
  document.getElementById("cardsGrid").classList.toggle("list-view", mode === "list");
  document.getElementById("grid3Btn").classList.toggle("active", mode === "grid");
  document.getElementById("grid1Btn").classList.toggle("active", mode === "list");
  if (iconChar) document.getElementById("catalogViewIcon").textContent = iconChar;
}

/* =========================================================================
   МОДАЛЬНОЕ ОКНО КАРТОЧКИ И ОТДЕЛЬНЫЙ ОВАЛ АНАЛОГОВ НИЖЕ ОКНА
========================================================================= */
function openDetailModal(drugId) {
  const drug = DRUGS_DB.find(d => d.id === drugId);
  if (!drug) return;

  document.getElementById("modalAnalogsDrawer").style.display = "none";
  document.getElementById("modalDescriptionBox").innerHTML = `
    <span class="detail-badge">${drug.category}</span>
    <h2>${drug.name}</h2>
    <p style="opacity:0.75; font-size:13.5px;">${drug.subtitle} | МНН: ${drug.inn}</p>
    <div class="detail-section"><strong>Заболевания и симптомы:</strong>${drug.diseases}</div>
    <div class="detail-section"><strong>Клинические указания:</strong>${drug.indications}</div>
    <div class="detail-section"><strong>Схема приема:</strong>${drug.dosage}</div>
    <div class="detail-section"><strong>Противопоказания:</strong>${drug.contraindications}</div>
  `;

  document.getElementById("modalPhotoBox").innerHTML = getDrugSVG(drug);
  document.getElementById("modalActionBox").innerHTML = `
    <button class="elongated-oval-btn accent-fill" onclick="openPresetPicker(${drug.id})">${t("btn_add_to_preset")}</button>
    <button class="elongated-oval-btn" onclick="showAnalogs(${drug.id})">${t("btn_find_analogs")}</button>
  `;

  openModal("detailModal");
}

function showAnalogs(drugId) {
  const drug = DRUGS_DB.find(d => d.id === drugId);
  const exact = DRUGS_DB.filter(d => d.inn === drug.inn && d.id !== drug.id);
  const group = DRUGS_DB.filter(d => d.category === drug.category && d.inn !== drug.inn).slice(0, 5);
  const all = [...exact, ...group];

  const drawer = document.getElementById("modalAnalogsDrawer");
  drawer.style.display = "flex";
  drawer.innerHTML = `
    <div style="display:flex; align-items:center; flex-wrap:wrap; gap:6px;">
      <strong style="font-size:13px; margin-right:6px;">Аналоги (${drug.inn}):</strong>
      ${all.map(a => `<button class="analog-chip" onclick="openDetailModal(${a.id})">${a.name}</button>`).join("")}
    </div>
    <button class="oval-subtle-btn" style="height:30px; font-size:12px;" onclick="filterByAnalogInn('${drug.inn}')">
      Вывести в каталог
    </button>
  `;
}

function filterByAnalogInn(inn) {
  activeAnalogInn = inn;
  closeModal("detailModal");
  document.getElementById("resetAnalogBtn").style.display = "inline-flex";
  openResultsView();
}

function clearAnalogFilter() {
  activeAnalogInn = null;
  document.getElementById("resetAnalogBtn").style.display = "none";
  renderCards();
}

/* =========================================================================
   ПРЕСЕТЫ, ПОДТВЕРЖДЕНИЕ УДАЛЕНИЯ И ПЕЧАТЬ
========================================================================= */
function openPresetPicker(drugId) {
  pendingDrugIdForPreset = drugId;
  toggleCreatePresetInput(false);
  renderPickerList();
  openModal("presetPickerModal");
}

function openCreatePresetModal() {
  pendingDrugIdForPreset = null;
  renderPickerList();
  toggleCreatePresetInput(true);
  openModal("presetPickerModal");
}

function renderPickerList() {
  const box = document.getElementById("existingPresetsList");
  if (userPresets.length === 0) {
    box.innerHTML = `<div style="text-align:center; opacity:0.7; padding:10px;">Пресеты еще не созданы</div>`;
    return;
  }
  box.innerHTML = userPresets.map(p => `
    <div class="picker-preset-row" onclick="addDrugToPreset('${p.id}')">
      <span>${p.name}</span>
      <span style="font-size:12.5px; opacity:0.75;">Препаратов: ${p.items.length}</span>
    </div>
  `).join("");
}

function toggleCreatePresetInput(show) {
  document.getElementById("createPresetForm").style.display = show ? "flex" : "none";
  document.getElementById("showCreateInputBtn").style.display = show ? "none" : "inline-flex";
  if (show) document.getElementById("newPresetNameInput").focus();
}

function confirmCreatePreset() {
  const input = document.getElementById("newPresetNameInput");
  const name = input.value.trim();
  if (!name) return;

  const newPreset = { id: "preset-" + Date.now(), name, items: [] };
  if (pendingDrugIdForPreset) {
    const drug = DRUGS_DB.find(d => d.id === pendingDrugIdForPreset);
    if (drug) newPreset.items.push({ ...drug });
  }
  userPresets.push(newPreset);
  input.value = "";
  closeModal("presetPickerModal");
  renderPresetsOverview();
  showToast(`Пресет «${name}» создан`);
}

function addDrugToPreset(presetId) {
  const preset = userPresets.find(p => p.id === presetId);
  if (!preset) return;

  if (pendingDrugIdForPreset) {
    const drug = DRUGS_DB.find(d => d.id === pendingDrugIdForPreset);
    if (drug && !preset.items.some(i => i.id === drug.id)) {
      preset.items.push({ ...drug });
    }
    closeModal("presetPickerModal");
    showToast(`Добавлено в «${preset.name}»`);
  } else {
    closeModal("presetPickerModal");
    switchPage("presets");
    openPresetDetail(presetId);
  }
  renderPresetsOverview();
}

function renderPresetsOverview() {
  const grid = document.getElementById("presetsGridContainer");
  grid.className = "presets-grid" + (presetsViewMode === "list" ? " list-mode" : presetsViewMode === "compact" ? " compact-mode" : "");

  if (userPresets.length === 0) {
    grid.innerHTML = `<div style="grid-column:1/-1; text-align:center; padding:30px;">Нет созданных пресетов</div>`;
    return;
  }

  grid.innerHTML = userPresets.map(p => `
    <div class="preset-folder-card" onclick="openPresetDetail('${p.id}')">
      <button class="preset-delete-btn" onclick="event.stopPropagation(); askDeletePreset('${p.id}')" title="Удалить пресет">&times;</button>
      <div class="preset-folder-title">${p.name}</div>
      <div class="preset-folder-count">Лекарств: ${p.items.length}</div>
    </div>
  `).join("");
}

function askDeletePreset(id) {
  if (!id) return;
  presetIdToDelete = id;
  openModal("confirmDeleteModal");
}

function confirmDeletePresetAction() {
  if (!presetIdToDelete) return;
  userPresets = userPresets.filter(p => p.id !== presetIdToDelete);
  presetIdToDelete = null;
  closeModal("confirmDeleteModal");
  closePresetDetail();
  renderPresetsOverview();
  showToast("Пресет удален");
}

function setPresetsViewMode(mode, iconChar) {
  presetsViewMode = mode;
  document.getElementById("presetViewGridBtn").classList.toggle("active", mode === "grid");
  document.getElementById("presetViewListBtn").classList.toggle("active", mode === "list");
  document.getElementById("presetViewCompactBtn").classList.toggle("active", mode === "compact");
  if (iconChar) document.getElementById("presetsViewIcon").textContent = iconChar;
  renderPresetsOverview();
}

function openPresetDetail(id) {
  openedPresetId = id;
  const preset = userPresets.find(p => p.id === id);
  if (!preset) return;

  document.getElementById("presetsOverview").style.display = "none";
  document.getElementById("presetDetailView").style.display = "block";
  document.getElementById("openedPresetTitle").textContent = preset.name;
  renderOpenedPresetDrugs();
}

function closePresetDetail() {
  openedPresetId = null;
  document.getElementById("presetsOverview").style.display = "block";
  document.getElementById("presetDetailView").style.display = "none";
  renderPresetsOverview();
}

function setInnerPresetView(mode, iconChar) {
  innerPresetViewMode = mode;
  document.getElementById("presetDrugsContainer").classList.toggle("grid-2", mode === "grid");
  document.getElementById("innerView1Btn").classList.toggle("active", mode === "list");
  document.getElementById("innerView2Btn").classList.toggle("active", mode === "grid");
  if (iconChar) document.getElementById("innerPresetViewIcon").textContent = iconChar;
}

function renderOpenedPresetDrugs() {
  const preset = userPresets.find(p => p.id === openedPresetId);
  const box = document.getElementById("presetDrugsContainer");
  if (!preset || preset.items.length === 0) {
    box.innerHTML = `<div style="text-align:center; padding:30px;">В этом пресете пока нет препаратов</div>`;
    return;
  }

  box.innerHTML = preset.items.map((item, idx) => `
    <div class="prescription-item">
      <div class="prescription-item-top">
        <h4>${idx + 1}. ${item.name} <span style="font-weight:400; font-size:13px; opacity:0.7;">${item.subtitle}</span></h4>
        <button class="circle-close-btn" style="width:30px; height:30px; font-size:18px;" onclick="removeDrugFromActivePreset(${idx})" title="Убрать препарат">&times;</button>
      </div>
      <div class="dosage-fields">
        <div class="field-box">
          <label>Разовая доза</label>
          <input type="text" class="oval-input" value="${item.defaultDose}" oninput="updatePresetDrugField(${idx}, 'defaultDose', this.value)" />
        </div>
        <div class="field-box">
          <label>Приемов в день</label>
          <input type="text" class="oval-input" value="${item.defaultFreq}" oninput="updatePresetDrugField(${idx}, 'defaultFreq', this.value)" />
        </div>
        <div class="field-box">
          <label>Порядок приема</label>
          <input type="text" class="oval-input" value="${item.defaultRule}" oninput="updatePresetDrugField(${idx}, 'defaultRule', this.value)" />
        </div>
        <div class="field-box">
          <label>Длительность курса</label>
          <input type="text" class="oval-input" value="${item.defaultDays}" oninput="updatePresetDrugField(${idx}, 'defaultDays', this.value)" />
        </div>
      </div>
    </div>
  `).join("");
}

function updatePresetDrugField(idx, field, val) {
  const preset = userPresets.find(p => p.id === openedPresetId);
  if (preset && preset.items[idx]) preset.items[idx][field] = val;
}

function removeDrugFromActivePreset(idx) {
  const preset = userPresets.find(p => p.id === openedPresetId);
  if (!preset) return;
  preset.items.splice(idx, 1);
  renderOpenedPresetDrugs();
}

function printActivePreset() {
  const preset = userPresets.find(p => p.id === openedPresetId);
  if (!preset || preset.items.length === 0) {
    showToast("Пресет пуст");
    return;
  }

  const borderCss = appConfig.printBorder ? "2px solid #000" : "none";
  const maxW = appConfig.paperSize === "A5" ? "520px" : "760px";

  document.getElementById("print-area").innerHTML = `
    <div style="border:${borderCss}; padding:28px; max-width:${maxW}; margin:0 auto;">
      <div style="display:flex; justify-content:space-between; border-bottom:1.5px solid #000; padding-bottom:10px; margin-bottom:20px;">
        <strong>ЛИСТ НАЗНАЧЕНИЙ: ${preset.name.toUpperCase()}</strong>
        <span>Дата: ${new Date().toLocaleDateString("ru-RU")}</span>
      </div>
      ${preset.items.map((item, idx) => `
        <div style="margin-bottom:16px; padding-bottom:10px; border-bottom:1px dashed #888;">
          <p style="font-size:16px;"><strong>${idx + 1}. ${appConfig.useRxPrefix ? 'Rp.: ' : ''}${item.name} (${item.subtitle})</strong></p>
          <p style="font-size:14.5px; margin-left:18px; margin-top:4px;">
            ${appConfig.useRxPrefix ? '<strong>S.:</strong> ' : ''}По <b>${item.defaultDose}</b> — <b>${item.defaultFreq}</b> (${item.defaultRule}). Курс: <b>${item.defaultDays}</b>.
          </p>
        </div>
      `).join("")}
    </div>
  `;
  window.print();
}

/* =========================================================================
   НАВИГАЦИЯ, ТЕМЫ (СВЕТЛАЯ / ТЕМНАЯ / СЛАБОВИДЯЩИЕ) И RGB-КРУГ
========================================================================= */
function toggleMenuClick() {
  document.getElementById("topHoverMenu").classList.toggle("force-open");
}

function switchPage(pageId) {
  document.getElementById("topHoverMenu").classList.remove("force-open");
  document.querySelectorAll(".page-section").forEach(sec => {
    sec.classList.toggle("active", sec.id === `page-${pageId}`);
  });
  if (pageId === "presets") {
    closePresetDetail();
    renderPresetsOverview();
  }
}

function switchSettingsTab(tabId) {
  document.querySelectorAll(".settings-cat-btn").forEach(b => b.classList.toggle("active", b.dataset.tab === tabId));
  document.querySelectorAll(".settings-pane").forEach(p => p.classList.toggle("active", p.id === `tab-${tabId}`));
}

function setDisplayMode(mode, btnEl) {
  appConfig.displayMode = mode;
  document.body.classList.remove("dark-mode", "a11y-mode");
  if (mode === "dark") document.body.classList.add("dark-mode");
  else if (mode === "a11y") document.body.classList.add("a11y-mode");

  if (btnEl) {
    document.querySelectorAll(".theme-pill[onclick*='setDisplayMode']").forEach(b => b.classList.remove("active-mode"));
    btnEl.classList.add("active-mode");
  }
}

function openModal(id) {
  document.getElementById(id).classList.add("open");
  if (appConfig.blur) document.getElementById("app-wrapper").classList.add("blurred");
}

function closeModal(id) {
  document.getElementById(id).classList.remove("open");
  const anyOpen = document.querySelectorAll(".modal-overlay.open").length > 0;
  if (!anyOpen) document.getElementById("app-wrapper").classList.remove("blurred");
}

function handleBackdropClose(e, id) {
  if (e.target.id === id) closeModal(id);
}

function setLanguage(lang) {
  appConfig.lang = lang;
  document.querySelectorAll("[data-lang]").forEach(b => b.classList.toggle("active-lang", b.dataset.lang === lang));
  document.querySelectorAll("[data-i18n]").forEach(el => {
    const key = el.getAttribute("data-i18n");
    if (I18N[lang] && I18N[lang][key]) el.textContent = I18N[lang][key];
  });
  document.querySelectorAll("[data-i18n-placeholder]").forEach(el => {
    const key = el.getAttribute("data-i18n-placeholder");
    if (I18N[lang] && I18N[lang][key]) el.placeholder = I18N[lang][key];
  });
  renderCards();
}

function updateRoundness(val) {
  document.documentElement.style.setProperty("--radius-main", val);
}

function toggleGlareSetting(enabled) {
  appConfig.glare = enabled;
  renderCards();
}

function updateCardContrast(val) {
  document.documentElement.style.setProperty("--card-bg", `hsl(${appConfig.currentHue}, 32%, ${val}%)`);
}

function applyCustomHue(h, bgSat, cardSat) {
  appConfig.currentHue = h;
  const r = document.documentElement;
  r.style.setProperty("--bg-center", `hsl(${h}, ${bgSat}%, 95%)`);
  r.style.setProperty("--bg-edge", `hsl(${h}, ${bgSat}%, 78%)`);
  r.style.setProperty("--surface-dark", `hsl(${h}, ${cardSat}%, 20%)`);
  r.style.setProperty("--surface-darker", `hsl(${h}, ${cardSat}%, 13%)`);
  r.style.setProperty("--card-bg", `hsl(${h}, ${cardSat}%, 30%)`);
  r.style.setProperty("--modal-outer", `hsl(${h}, ${bgSat}%, 66%)`);
  r.style.setProperty("--accent", `hsl(${h}, ${cardSat + 25}%, 42%)`);
  r.style.setProperty("--accent-soft", `hsl(${h}, ${bgSat + 20}%, 88%)`);
}

function applyPresetTheme(name, btnEl) {
  if (btnEl) {
    document.querySelectorAll(".theme-pill[onclick*='applyPresetTheme']").forEach(b => b.classList.remove("active-theme"));
    btnEl.classList.add("active-theme");
  }
  if (name === "gemini") applyCustomHue(216, 28, 28);
  else if (name === "medical") applyCustomHue(202, 34, 34);
  else if (name === "emerald") applyCustomHue(154, 24, 28);
  else if (name === "warm") applyCustomHue(28, 24, 24);
  else if (name === "graphite") applyCustomHue(225, 10, 16);
}

function initColorWheel() {
  const canvas = document.getElementById("rgbWheel");
  if (!canvas) return;
  const ctx = canvas.getContext("2d");
  const radius = canvas.width / 2;

  for (let a = 0; a < 360; a++) {
    ctx.beginPath();
    ctx.moveTo(radius, radius);
    ctx.arc(radius, radius, radius, (a - 1) * Math.PI / 180, (a + 1) * Math.PI / 180);
    ctx.closePath();
    const g = ctx.createRadialGradient(radius, radius, 0, radius, radius, radius);
    g.addColorStop(0, `hsl(${a}, 15%, 95%)`);
    g.addColorStop(0.7, `hsl(${a}, 75%, 58%)`);
    g.addColorStop(1, `hsl(${a}, 85%, 42%)`);
    ctx.fillStyle = g;
    ctx.fill();
  }

  let drag = false;
  const pick = (e) => {
    const rect = canvas.getBoundingClientRect();
    const x = e.clientX - rect.left - radius;
    const y = e.clientY - rect.top - radius;
    const d = Math.sqrt(x * x + y * y);
    if (d > radius) return;
    let hue = Math.atan2(y, x) * (180 / Math.PI);
    if (hue < 0) hue += 360;
    const sat = Math.min(d / radius, 1);
    applyCustomHue(Math.round(hue), Math.round(14 + sat * 22), Math.round(18 + sat * 26));
  };

  canvas.addEventListener("mousedown", (e) => { drag = true; pick(e); });
  window.addEventListener("mousemove", (e) => { if (drag) pick(e); });
  window.addEventListener("mouseup", () => { drag = false; });
}

let toastTimer;
function showToast(msg) {
  const el = document.getElementById("toast");
  el.textContent = msg;
  el.classList.add("show");
  clearTimeout(toastTimer);
  toastTimer = setTimeout(() => el.classList.remove("show"), 2400);
}

/* =========================================================================
   ИНИЦИАЛИЗАЦИЯ ПРИ ЗАПУСКЕ
========================================================================= */
window.addEventListener("DOMContentLoaded", () => {
  initFilterOptions();
  initBackgroundParticles();
  initColorWheel();
  renderPresetsOverview();

  const searchInput = document.getElementById("searchInput");

  // При вводе текста показываем прямоугольник совпадений болезней
  searchInput.addEventListener("input", (e) => {
    document.getElementById("filterDropdown").classList.remove("open");
    renderDiseaseSuggestions(e.target.value);
  });

  searchInput.addEventListener("focus", (e) => {
    if (e.target.value.trim()) renderDiseaseSuggestions(e.target.value);
  });

  searchInput.addEventListener("keydown", (e) => {
    if (e.key === "Enter") {
      const firstBtn = document.querySelector("#diseaseSuggestionsBox .disease-suggest-item");
      if (firstBtn) firstBtn.click();
    }
  });

  document.getElementById("filterBtn").addEventListener("click", (e) => {
    e.stopPropagation();
    document.getElementById("diseaseSuggestionsBox").classList.remove("open");
    document.getElementById("filterDropdown").classList.toggle("open");
  });

  document.addEventListener("click", (e) => {
    const dd = document.getElementById("filterDropdown");
    const sb = document.getElementById("diseaseSuggestionsBox");
    const wrap = document.getElementById("searchWrapper");
    if (dd && !dd.contains(e.target) && e.target.id !== "filterBtn") {
      dd.classList.remove("open");
    }
    if (sb && wrap && !wrap.contains(e.target)) {
      sb.classList.remove("open");
    }
  });
});