(() => {
  "use strict";

  const byId = (id) => document.getElementById(id);
  let notificationTimer;
  function notify(message) {
    const notification = byId("notification");
    notification.textContent = message;
    notification.hidden = false;
    clearTimeout(notificationTimer);
    notificationTimer = setTimeout(() => { notification.hidden = true; }, 6000);
  }

  document.querySelectorAll("[data-open-dialog]").forEach((button) => {
    button.addEventListener("click", () => byId(button.dataset.openDialog).showModal());
  });
  document.querySelectorAll("[data-close-dialog]").forEach((button) => {
    button.addEventListener("click", () => button.closest("dialog").close());
  });
  document.querySelectorAll("dialog").forEach((dialog) => {
    dialog.addEventListener("click", (event) => {
      if (event.target !== dialog) return;
      const bounds = dialog.getBoundingClientRect();
      if (event.clientX < bounds.left || event.clientX > bounds.right ||
          event.clientY < bounds.top || event.clientY > bounds.bottom) dialog.close();
    });
  });
  document.querySelectorAll("[data-illustration]").forEach((link) => {
    link.addEventListener("click", (event) => {
      if (event.ctrlKey || event.metaKey || event.shiftKey || event.altKey) return;
      event.preventDefault();
      byId("illustration-title").textContent = link.dataset.illustration;
      byId("illustration-image").src = link.href;
      byId("illustration-image").alt = link.querySelector("img").alt;
      byId("illustration-dialog").showModal();
    });
  });
  byId("copy-citation")?.addEventListener("click", async () => {
    try {
      await navigator.clipboard.writeText(byId("citation-text").textContent);
      byId("citation-status").textContent = "BibTeX copied to clipboard.";
    } catch {
      const range = document.createRange();
      range.selectNodeContents(byId("citation-text"));
      const selection = window.getSelection();
      selection.removeAllRanges();
      selection.addRange(range);
      byId("citation-status").textContent = "Select and copy the highlighted citation.";
    }
  });

  const form = byId("benchmark_form");
  if (!form) return;

  const circuits = Array.from(form.querySelectorAll("[data-circuit-group]"));
  const groups = Array.from(form.querySelectorAll("[data-group]"));
  const downloadButton = byId("download-button");
  const exportButton = byId("export-button");
  const collator = new Intl.Collator(undefined, { numeric: true, sensitivity: "base" });
  let records = [];
  let headers = [];
  let currentPage = 0;
  let sortColumn = 0;
  let sortDirection = 1;
  let activeCollection = "all";
  let requestController;
  let requestVersion = 0;
  let updateTimer;
  let pending = true;

  function checked(id) {
    return byId(id).checked && byId(id).matches(":enabled");
  }

  function syncFilters() {
    const gate = checked("gate");
    byId("library-options").disabled = !gate;
    byId("best-layout").disabled = !gate;
    const custom = gate && !checked("best-layout");
    const anyLibrary = !checked("one") && !checked("bestagon");
    const one = anyLibrary || checked("one");
    const bestagon = anyLibrary || checked("bestagon");
    byId("clock-options").disabled = !custom;
    ["twoddwave", "use", "res", "esr"].forEach((id) => { byId(id).disabled = !one; });
    byId("row").disabled = !bestagon;
    byId("algorithm-options").disabled = !custom;
    const clocks = ["twoddwave", "use", "res", "esr", "row"].filter(checked);
    const orthogonal = clocks.length === 0 || checked("twoddwave") || checked("row");
    byId("ortho").disabled = !orthogonal;
    byId("gold").disabled = !orthogonal;
    byId("optimization-options").disabled = !custom;
    byId("post-layout").disabled = !["ortho", "nanoplacer", "gold"].some(checked);
    byId("input-ordering").disabled = !checked("ortho");
    byId("cost-options").disabled = !checked("gold");
    byId("clock-help").textContent = checked("best-layout")
      ? "Smallest layouts include their chosen scheme and algorithm."
      : "Any scheme when none selected.";
  }

  function syncSelection() {
    const count = circuits.filter((input) => input.checked).length;
    const all = byId("all-benchmarks");
    all.checked = count === circuits.length;
    all.indeterminate = count > 0 && count < circuits.length;
    byId("selected-functions").textContent = count;
    groups.forEach((group) => {
      const members = circuits.filter((input) => input.dataset.circuitGroup === group.dataset.group);
      const selected = members.filter((input) => input.checked).length;
      group.checked = selected === members.length;
      group.indeterminate = selected > 0 && selected < members.length;
      group.closest(".collection").querySelector(".group-count").textContent = selected + " / " + members.length;
    });
  }

  function filterCircuits() {
    const query = byId("circuit-search").value.trim().toLowerCase();
    let visible = 0;
    form.querySelectorAll(".collection").forEach((collection) => {
      let matching = 0;
      collection.querySelectorAll(".circuit-chip").forEach((chip) => {
        chip.hidden = !chip.dataset.circuitName.includes(query);
        if (!chip.hidden) matching += 1;
      });
      collection.hidden = (activeCollection !== "all" && collection.dataset.collectionName !== activeCollection) || matching === 0;
      if (!collection.hidden) visible += matching;
    });
    byId("no-circuits").hidden = visible > 0;
  }

  function appendText(parent, tag, text, className = "") {
    const element = document.createElement(tag);
    element.textContent = text;
    if (className) element.className = className;
    parent.append(element);
    return element;
  }

  function inspectRecord(record) {
    byId("file-title").textContent = record[0];
    byId("file-name").textContent = record[13];
    const details = byId("file-details");
    details.replaceChildren();
    headers.slice(1, 13).forEach((header, index) => {
      const item = appendText(details, "div", "");
      appendText(item, "dt", header);
      appendText(item, "dd", record[index + 1] || "Not applicable");
    });
    byId("file-dialog").showModal();
  }

  function renderResults() {
    const pageSize = Number(byId("page-size").value);
    const pageCount = Math.max(1, Math.ceil(records.length / pageSize));
    currentPage = Math.max(0, Math.min(currentPage, pageCount - 1));
    const start = currentPage * pageSize;
    const body = byId("results-body");
    body.replaceChildren();
    for (const record of records.slice(start, start + pageSize)) {
      const row = document.createElement("tr");
      const name = appendText(row, "td", "");
      appendText(name, "span", record[0], "benchmark-name");
      appendText(name, "span", record[1] + (record[1] === "Network" ? " · .v" : " · .fgl"), "benchmark-type");
      const library = appendText(row, "td", "");
      appendText(library, "span", record[2] || "—", record[2] ? "library-label" + (record[2] === "Bestagon" ? " sidb" : "") : "muted");
      appendText(row, "td", record[3] === "best" ? "Best available" : record[3] || "—", "clock-label");
      const algorithm = appendText(row, "td", record[4] || "—");
      const variant = [
        record[7] && record[7] !== "✗" ? record[7].replace("Area-Crossing Product", "Area × crossings") : "",
        record[5] === "✓" ? "optimized" : "",
        record[6] === "✓" ? "ordered inputs" : "",
      ].filter(Boolean).join(" · ");
      if (variant) appendText(algorithm, "span", variant, "benchmark-type");
      appendText(row, "td", record[8] && record[9] ? record[8] + " × " + record[9] : "—", "dimensions");
      appendText(row, "td", record[12]);
      const action = appendText(row, "td", "");
      const inspect = appendText(action, "button", "↗", "icon-button");
      inspect.type = "button";
      inspect.setAttribute("aria-label", "Inspect " + record[13]);
      inspect.title = "View benchmark details";
      inspect.addEventListener("click", () => inspectRecord(record));
      body.append(row);
    }
    byId("page-status").textContent = records.length
      ? "Showing " + (start + 1) + "–" + Math.min(start + pageSize, records.length) + " of " + records.length.toLocaleString() + " benchmarks"
      : "No benchmarks to display";
    byId("page-number").textContent = (currentPage + 1) + " / " + pageCount;
    byId("previous-page").disabled = currentPage === 0;
    byId("next-page").disabled = currentPage >= pageCount - 1;
    byId("results-container").hidden = records.length === 0;
    byId("empty-results").hidden = records.length > 0;
  }

  function sortResults() {
    records.sort((a, b) => {
      const result = sortColumn === 10 ? Number(a[10] || 0) - Number(b[10] || 0)
        : sortColumn === 12 ? fileSize(a[12]) - fileSize(b[12])
        : collator.compare(a[sortColumn], b[sortColumn]);
      return result * sortDirection;
    });
    renderResults();
  }

  function fileSize(value) {
    const units = { byte: 1, bytes: 1, kB: 1000, MB: 1000000, GB: 1000000000, TB: 1000000000000 };
    const [number, unit] = value.split(" ");
    return Number(number) * (units[unit] || 1);
  }

  async function updateResults() {
    const version = requestVersion;
    requestController = new AbortController();
    try {
      const response = await fetch(form.dataset.summaryUrl, {
        method: "POST",
        body: new FormData(form),
        signal: requestController.signal,
      });
      if (!response.ok) throw new Error("Could not load benchmarks");
      const result = await response.json();
      if (version !== requestVersion) return;
      const table = new DOMParser().parseFromString(result.table, "text/html").querySelector("table");
      if (!table) throw new Error("Missing benchmark table");
      headers = Array.from(table.querySelectorAll("thead th"), (cell) => cell.textContent);
      records = Array.from(table.querySelectorAll("tbody tr"), (row) =>
        Array.from(row.querySelectorAll("td"), (cell) => cell.textContent));
      currentPage = 0;
      sortResults();
      byId("result-count").textContent = result.num_selected.toLocaleString();
      byId("results-status").textContent = result.num_selected.toLocaleString() + " matching benchmarks";
      byId("compressed-size").textContent = result.size_compressed;
      byId("uncompressed-size").textContent = result.size_uncompressed;
      pending = false;
      downloadButton.disabled = result.num_selected === 0;
      exportButton.disabled = result.num_selected === 0;
      byId("results-container").setAttribute("aria-busy", "false");
    } catch (error) {
      if (error.name === "AbortError" || version !== requestVersion) return;
      records = [];
      renderResults();
      byId("empty-results").hidden = true;
      byId("results-error").hidden = false;
      byId("results-status").textContent = "Unable to load results";
      byId("result-count").textContent = "—";
      byId("compressed-size").textContent = "—";
      byId("uncompressed-size").textContent = "—";
      byId("results-container").setAttribute("aria-busy", "false");
    }
  }

  function scheduleUpdate() {
    syncFilters();
    syncSelection();
    requestVersion += 1;
    requestController?.abort();
    clearTimeout(updateTimer);
    pending = true;
    downloadButton.disabled = true;
    exportButton.disabled = true;
    byId("results-status").textContent = "Updating your collection…";
    byId("results-container").setAttribute("aria-busy", "true");
    byId("results-error").hidden = true;
    updateTimer = setTimeout(updateResults, 160);
  }

  form.addEventListener("change", (event) => {
    const input = event.target;
    if (["format", "page-size", "circuit-search"].includes(input.id)) return;
    if (input.id === "all-benchmarks") circuits.forEach((circuit) => { circuit.checked = input.checked; });
    if (input.dataset.group) circuits.filter((circuit) => circuit.dataset.circuitGroup === input.dataset.group)
      .forEach((circuit) => { circuit.checked = input.checked; });
    scheduleUpdate();
  });
  form.addEventListener("reset", () => {
    setTimeout(() => {
      activeCollection = "all";
      form.querySelectorAll("[data-collection]").forEach((button) => {
        button.setAttribute("aria-pressed", String(button.dataset.collection === "all"));
      });
      filterCircuits();
      scheduleUpdate();
    }, 0);
  });
  form.addEventListener("submit", (event) => {
    if (pending || records.length === 0) {
      event.preventDefault();
      return;
    }
    if (!event.submitter) {
      event.preventDefault();
      return;
    }
    notify(event.submitter.value === "submit" ? "Preparing your archive. Your browser will handle the download." : "Preparing your table export.");
  });
  byId("clear-circuits").addEventListener("click", () => {
    circuits.forEach((input) => { input.checked = false; });
    scheduleUpdate();
  });
  form.querySelectorAll("[data-collection]").forEach((button) => {
    button.addEventListener("click", () => {
      activeCollection = button.dataset.collection;
      form.querySelectorAll("[data-collection]").forEach((tab) => tab.setAttribute("aria-pressed", String(tab === button)));
      filterCircuits();
    });
  });
  byId("circuit-search").addEventListener("input", filterCircuits);
  byId("circuit-search").addEventListener("keydown", (event) => {
    if (event.key === "Enter") event.preventDefault();
  });
  byId("page-size").addEventListener("change", () => { currentPage = 0; renderResults(); });
  byId("previous-page").addEventListener("click", () => { currentPage -= 1; renderResults(); });
  byId("next-page").addEventListener("click", () => { currentPage += 1; renderResults(); });
  byId("retry-results").addEventListener("click", scheduleUpdate);
  form.querySelectorAll("[data-sort]").forEach((button) => {
    button.addEventListener("click", () => {
      const column = Number(button.dataset.sort);
      sortDirection = sortColumn === column ? -sortDirection : 1;
      sortColumn = column;
      form.querySelectorAll("th[aria-sort]").forEach((cell) => cell.removeAttribute("aria-sort"));
      button.closest("th").setAttribute("aria-sort", sortDirection === 1 ? "ascending" : "descending");
      currentPage = 0;
      sortResults();
    });
  });
  const filterToggle = byId("toggle-filters");
  function setFiltersVisible(visible) {
    byId("filters-body").hidden = !visible;
    filterToggle.setAttribute("aria-expanded", String(visible));
    filterToggle.textContent = visible ? "Hide filters" : "Show filters";
  }
  const mobile = window.matchMedia("(max-width: 620px)");
  setFiltersVisible(!mobile.matches);
  mobile.addEventListener("change", () => setFiltersVisible(!mobile.matches));
  filterToggle.addEventListener("click", () => setFiltersVisible(byId("filters-body").hidden));
  scheduleUpdate();
})();
