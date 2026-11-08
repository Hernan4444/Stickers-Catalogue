const state = {
    pending: [],
    processed: [],
    jpgs: [],
    illustrators: [],
    tags: [],
    mode: "pending",
    index: 0,
    current: null,
    selectedTags: [],
    filterTags: [],
    tagMatch: "all",
    rotation: 0,
    busy: false,
};

const elements = {
    pendingCount: document.querySelector("#pending-count"),
    processedCount: document.querySelector("#processed-count"),
    jpgCount: document.querySelector("#jpg-count"),
    sourceMode: document.querySelector("#source-mode"),
    modeHelp: document.querySelector("#mode-help"),
    jpgSearch: document.querySelector("#jpg-search"),
    jpgSearchCount: document.querySelector("#jpg-search-count"),
    jpgIllustratorFilter: document.querySelector("#jpg-illustrator-filter"),
    jpgIllustratorSuggestions: document.querySelector("#jpg-illustrator-suggestions"),
    jpgTagFilter: document.querySelector("#jpg-tag-filter"),
    jpgFilterPills: document.querySelector("#jpg-filter-pills"),
    clearJpgFilters: document.querySelector("#clear-jpg-filters"),
    previous: document.querySelector("#previous"),
    next: document.querySelector("#next"),
    position: document.querySelector("#position"),
    preview: document.querySelector("#preview"),
    rotateLeft: document.querySelector("#rotate-left"),
    rotateRight: document.querySelector("#rotate-right"),
    rotationStatus: document.querySelector("#rotation-status"),
    emptyMessage: document.querySelector("#empty-message"),
    sourceName: document.querySelector("#source-name"),
    form: document.querySelector("#image-form"),
    name: document.querySelector("#new-name"),
    nameSuffix: document.querySelector("#name-suffix"),
    nameHelp: document.querySelector("#name-help"),
    illustrator: document.querySelector("#illustrator"),
    illustratorSuggestions: document.querySelector("#illustrator-suggestions"),
    tagInput: document.querySelector("#tag-input"),
    tagSuggestions: document.querySelector("#tag-suggestions"),
    tagPills: document.querySelector("#tag-pills"),
    save: document.querySelector("#save-button"),
    message: document.querySelector("#message"),
    upload: document.querySelector("#upload-button"),
    compress: document.querySelector("#compress-button"),
    output: document.querySelector("#job-output"),
};

async function request(url, options = {}) {
    const response = await fetch(url, options);
    const result = await response.json();
    if (!response.ok) {
        throw new Error(result.error || `Error HTTP ${response.status}`);
    }
    return result;
}

function showMessage(text, isError = false) {
    elements.message.textContent = text;
    elements.message.classList.toggle("error", isError);
}

function setBusy(isBusy) {
    state.busy = isBusy;
    elements.sourceMode.disabled = isBusy;
    elements.save.disabled = isBusy || !state.current;
    elements.previous.disabled = isBusy || state.index <= 0;
    elements.next.disabled = isBusy || state.index >= currentItems().length - 1;
    elements.upload.disabled = isBusy;
    elements.compress.disabled = isBusy;
    elements.rotateLeft.disabled = isBusy || !state.current;
    elements.rotateRight.disabled = isBusy || !state.current;
}

function fillSuggestions(list, values) {
    list.replaceChildren(...values.map((value) => {
        const option = document.createElement("option");
        option.value = value;
        return option;
    }));
}

function renderTags() {
    elements.tagPills.replaceChildren();
    state.selectedTags.forEach((tag, index) => {
        const pill = document.createElement("span");
        pill.className = "tag-pill";
        const text = document.createElement("span");
        text.textContent = tag;
        const remove = document.createElement("button");
        remove.type = "button";
        remove.setAttribute("aria-label", `Quitar tag ${tag}`);
        remove.textContent = "×";
        remove.addEventListener("click", () => {
            state.selectedTags.splice(index, 1);
            renderTags();
        });
        pill.append(text, remove);
        elements.tagPills.append(pill);
    });
}

function addTag(rawTag) {
    const tag = rawTag.trim().replace(/,$/, "").trim();
    if (!tag || /^ilustrador_/i.test(tag)) {
        return;
    }
    if (state.selectedTags.some((current) => current.toLocaleLowerCase() === tag.toLocaleLowerCase())) {
        return;
    }
    state.selectedTags.push(tag);
    renderTags();
}

function addInputTags() {
    const values = elements.tagInput.value.split(",");
    values.forEach(addTag);
    elements.tagInput.value = "";
}

function currentItems() {
    if (state.mode === "pending") {
        return state.pending.map((filename) => ({
            filename,
            illustrator: "",
            tags: [],
        }));
    }
    if (state.mode === "processed") {
        return state.processed;
    }

    const illustratorQuery = elements.jpgIllustratorFilter.value.trim().toLocaleLowerCase();
    return state.jpgs.filter((item) => {
        if (illustratorQuery
                && !item.illustrator.toLocaleLowerCase().includes(illustratorQuery)) {
            return false;
        }
        if (state.filterTags.length === 0) {
            return true;
        }
        const itemTags = new Set(item.tags.map((tag) => tag.toLocaleLowerCase()));
        const matches = state.filterTags.map((tag) => itemTags.has(tag.toLocaleLowerCase()));
        return state.tagMatch === "all" ? matches.every(Boolean) : matches.some(Boolean);
    });
}

function currentModeText() {
    if (state.mode === "processed") {
        return {
            singular: "PNG procesada",
            suffix: ".png",
            help: "Al guardar, se actualizan el PNG, su JPG asociado (si existe) y data.csv. No se sube a Cloudinary.",
        };
    }
    if (state.mode === "jpg") {
        return {
            singular: "JPG del catálogo",
            suffix: ".jpg",
            help: "Al guardar, se actualizan el JPG, el registro de data.csv y el PNG asociado en procesadas si existe. No se sube a Cloudinary.",
        };
    }
    return {
        singular: "imagen pendiente",
        suffix: ".png",
        help: "Al guardar, la imagen pasa a procesadas y se agrega a data.csv.",
    };
}

function renderCurrent() {
    const items = currentItems();
    const item = items[state.index];
    state.current = item || null;
    const modeText = currentModeText();
    elements.jpgSearch.hidden = state.mode !== "jpg";
    elements.jpgSearchCount.textContent = `${items.length} de ${state.jpgs.length} imágenes`;
    elements.nameSuffix.textContent = modeText.suffix;
    elements.modeHelp.textContent = modeText.help;
    elements.save.textContent = state.mode === "pending" ? "Guardar y siguiente" : "Guardar cambios";
    elements.upload.hidden = state.mode !== "processed";
    state.rotation = 0;
    renderRotation();
    if (!item) {
        elements.preview.removeAttribute("src");
        elements.preview.hidden = true;
        elements.emptyMessage.hidden = false;
        elements.sourceName.textContent = "";
        elements.position.textContent = state.mode === "jpg"
            ? "No hay JPG que coincidan con los filtros"
            : `No hay ${modeText.singular} disponibles`;
        elements.name.value = "";
        elements.illustrator.value = "";
        state.selectedTags = [];
        renderTags();
        setBusy(false);
        return;
    }
    elements.preview.hidden = false;
    elements.emptyMessage.hidden = true;
    elements.preview.src = `/api/image?mode=${state.mode}&name=${encodeURIComponent(item.filename)}`;
    elements.sourceName.textContent = item.filename;
    elements.position.textContent = state.mode === "jpg"
        ? `${state.index + 1} de ${items.length} resultados`
        : `${state.index + 1} de ${items.length}`;
    elements.name.value = item.filename.replace(/\.(png|jpe?g)$/i, "");
    elements.illustrator.value = item.illustrator;
    state.selectedTags = [...item.tags];
    renderTags();
    showMessage("");
    elements.nameHelp.textContent = state.mode === "pending"
        ? "Si el nombre ya existe en procesadas o procesadas_jpg, se agrega automáticamente _número."
        : "Puedes conservar el nombre o cambiarlo. Si el nuevo nombre ya existe, se agrega automáticamente _número.";
    setBusy(false);
}

function renderRotation() {
    elements.preview.style.transform = `rotate(${state.rotation}deg)`;
    elements.rotationStatus.textContent = `Rotación: ${state.rotation}°`;
}

function rotatePreview(degrees) {
    if (!state.current || state.busy) {
        return;
    }
    state.rotation = (state.rotation + degrees + 360) % 360;
    renderRotation();
}

function renderFilterTags() {
    elements.jpgFilterPills.replaceChildren();
    state.filterTags.forEach((tag, index) => {
        const pill = document.createElement("span");
        pill.className = "tag-pill";
        const text = document.createElement("span");
        text.textContent = tag;
        const remove = document.createElement("button");
        remove.type = "button";
        remove.setAttribute("aria-label", `Quitar filtro ${tag}`);
        remove.textContent = "×";
        remove.addEventListener("click", () => {
            const currentName = state.current?.filename;
            state.filterTags.splice(index, 1);
            renderFilterTags();
            refreshJpgResults(currentName);
        });
        pill.append(text, remove);
        elements.jpgFilterPills.append(pill);
    });
}

function addFilterTag() {
    const tag = elements.jpgTagFilter.value.trim();
    elements.jpgTagFilter.value = "";
    if (!tag || /^ilustrador_/i.test(tag)) {
        return;
    }
    if (state.filterTags.some((current) => current.toLocaleLowerCase() === tag.toLocaleLowerCase())) {
        return;
    }
    const currentName = state.current?.filename;
    state.filterTags.push(tag);
    renderFilterTags();
    refreshJpgResults(currentName);
}

function refreshJpgResults(preferredName = state.current?.filename) {
    if (state.mode !== "jpg") {
        return;
    }
    const items = currentItems();
    const preferredIndex = items.findIndex((item) => item.filename === preferredName);
    state.index = preferredIndex >= 0 ? preferredIndex : 0;
    renderCurrent();
}

async function loadState(preferredName = null) {
    const result = await request("/api/state");
    state.pending = result.pending;
    state.processed = result.processed;
    state.jpgs = result.jpgs;
    state.illustrators = result.illustrators;
    state.tags = result.tags;
    elements.pendingCount.textContent = `Pendientes: ${result.pendingCount}`;
    elements.processedCount.textContent = `PNG procesadas: ${result.processedCount}`;
    elements.jpgCount.textContent = `JPG del catálogo: ${result.jpgCount}`;
    fillSuggestions(
        elements.illustratorSuggestions,
        state.illustrators.map((tag) => tag.replace(/^ilustrador_/i, "")),
    );
    fillSuggestions(
        elements.jpgIllustratorSuggestions,
        state.illustrators.map((tag) => tag.replace(/^ilustrador_/i, "")),
    );
    fillSuggestions(elements.tagSuggestions, state.tags);
    const items = currentItems();
    if (preferredName) {
        const preferredIndex = items.findIndex((item) => item.filename === preferredName);
        if (preferredIndex >= 0) {
            state.index = preferredIndex;
        }
    }
    state.index = Math.min(state.index, Math.max(items.length - 1, 0));
    renderCurrent();
}

async function saveCurrent() {
    if (!state.current || state.busy) {
        return;
    }
    const mode = state.mode;
    const source = state.current.filename;
    setBusy(true);
    showMessage(mode === "pending"
        ? "Guardando imagen y actualizando data.csv…"
        : "Guardando cambios…");
    try {
        const result = await request("/api/update", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({
                mode,
                source,
                name: elements.name.value,
                illustrator: elements.illustrator.value,
                tags: state.selectedTags,
                rotation: state.rotation,
            }),
        });
        const nextFilename = mode === "processed"
            ? result.name.replace(/\.jpg$/i, ".png")
            : result.name;
        if (mode === "pending") {
            await loadState();
        } else {
            await loadState(nextFilename);
        }
        const warning = result.warnings.length ? ` ${result.warnings.join(" ")}` : "";
        showMessage(`Guardada correctamente: ${result.name}.${warning}`, Boolean(warning));
    } catch (error) {
        showMessage(error.message, true);
        setBusy(false);
    }
}

async function runScript(action, label) {
    if (state.busy) {
        return;
    }
    if (action === "upload" && !window.confirm("¿Subir las imágenes de procesadas a Cloudinary usando los tags de data.csv?")) {
        return;
    }
    if (action === "compress" && !window.confirm("¿Generar/actualizar las imágenes JPG de procesadas_jpg?")) {
        return;
    }
    setBusy(true);
    elements.output.textContent = `${label}…`;
    try {
        const job = await request("/api/run", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ action }),
        });
        await pollJob(job.id, label);
    } catch (error) {
        elements.output.textContent = error.message;
    } finally {
        setBusy(false);
    }
}

async function pollJob(jobId, label) {
    while (true) {
        const job = await request(`/api/jobs/${encodeURIComponent(jobId)}`);
        elements.output.textContent = job.status === "running"
            ? `${label} en curso…\n\n${job.output || ""}`
            : `${job.status === "completed" ? "Tarea completada" : "La tarea falló"} (código ${job.exitCode})\n\n${job.output || "El script no produjo salida."}`;
        if (job.status !== "running") {
            return;
        }
        await new Promise((resolve) => window.setTimeout(resolve, 1000));
    }
}

elements.form.addEventListener("submit", (event) => {
    event.preventDefault();
    addInputTags();
    saveCurrent();
});
elements.tagInput.addEventListener("keydown", (event) => {
    if (event.key === "Enter" || event.key === ",") {
        event.preventDefault();
        addInputTags();
    }
});
elements.tagInput.addEventListener("change", addInputTags);
elements.previous.addEventListener("click", () => {
    if (state.index > 0) {
        state.index -= 1;
        renderCurrent();
    }
});
elements.next.addEventListener("click", () => {
    if (state.index < currentItems().length - 1) {
        state.index += 1;
        renderCurrent();
    }
});
elements.sourceMode.addEventListener("change", () => {
    state.mode = elements.sourceMode.value;
    state.index = 0;
    loadState().catch((error) => showMessage(error.message, true));
});
elements.jpgIllustratorFilter.addEventListener("input", () => refreshJpgResults());
elements.jpgTagFilter.addEventListener("keydown", (event) => {
    if (event.key === "Enter" || event.key === ",") {
        event.preventDefault();
        addFilterTag();
    }
});
elements.jpgTagFilter.addEventListener("change", addFilterTag);
document.querySelectorAll('input[name="tag-match"]').forEach((input) => {
    input.addEventListener("change", () => {
        state.tagMatch = input.value;
        refreshJpgResults();
    });
});
elements.clearJpgFilters.addEventListener("click", () => {
    elements.jpgIllustratorFilter.value = "";
    state.filterTags = [];
    state.tagMatch = "all";
    document.querySelector('input[name="tag-match"][value="all"]').checked = true;
    renderFilterTags();
    refreshJpgResults();
});
elements.rotateLeft.addEventListener("click", () => rotatePreview(-90));
elements.rotateRight.addEventListener("click", () => rotatePreview(90));
elements.upload.addEventListener("click", () => runScript("upload", "Subida a Cloudinary"));
elements.compress.addEventListener("click", () => runScript("compress", "Compresión JPG"));

loadState().catch((error) => {
    showMessage(error.message, true);
    elements.output.textContent = "No se pudo cargar el catálogo.";
});
