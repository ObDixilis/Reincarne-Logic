"use strict";

(() => {
  const $ = (id) => document.getElementById(id);
  const ui = { bootstrap: null, session: null, selected: "M0", lineage: null, busy: false, loaded: false, previewChanged: false };
  const descriptions = {
    M0: "A steady light produced through a learned spell procedure. This ordinary practice deliberately requires neither named system.",
    T0: "Operate a lamp to produce a steady light. Device handling requires equipment and charge; it carries no Techfinity access requirement.",
    A1: "Guide a light through an explicit Affinity expression. Learned Light is its prerequisite; Affinity access is a separate present fact.",
    T1: "Shape an addressed signal through an explicit Techfinity expression. The learned procedure, interface access, and lamp remain separate requirements.",
    H1: "Weave guided light and an addressed pattern into one encoded beacon. Both live inputs are required; a lost input aborts the entire output."
  };
  const effectNames = {
    steady_spell_light: "Steady spell light",
    steady_lamp_light: "Steady lamp light",
    guided_light: "Guided light",
    addressed_signal: "Addressed signal",
    encoded_light_beacon: "Encoded light beacon"
  };
  const effectDescriptions = {
    steady_spell_light: "A stable magical light, emitted by the learned procedure.",
    steady_lamp_light: "A stable lamp light, emitted by the equipped ordinary device.",
    guided_light: "A directed path of light, emitted by the Affinity expression.",
    addressed_signal: "An addressed pulse pattern, emitted by the Techfinity expression.",
    encoded_light_beacon: "One beacon: guided magical light carries the technological signal pattern."
  };
  const channelNames = { biological: "Biological", resonant: "Resonant", cultural_mentorship: "Cultural / mentorship", fabricated_blueprint: "Fabricated / blueprint" };
  const reasonText = {
    NOT_LEARNED: "Learn this skill before activating it.",
    PREREQUISITE: "Learn every required prerequisite rank first.",
    POINTS: "There are not enough growth points for the next rank.",
    MAX_RANK: "All ranks in this skill contract are learned.",
    AXIS_UNAVAILABLE: "A required axis is unavailable. Change the scenario access fact to test it.",
    AXIS_UNKNOWN: "A required axis has unknown access. Supply an explicit access fact to test it.",
    UNRESOLVED: "The system mapping is unresolved; learning and activation are blocked.",
    EQUIPMENT: "Equip the required lamp before activation.",
    BUSY: "Advance the active action before learning or starting another action.",
    DEPLETED: "Insufficient activation resources. No partial cost is charged.",
    RECOVERING: "The action or one of its inputs is still recovering. Advance time to continue.",
    DEPENDENTS: "Learned skills depend on this node. Explicitly include dependents to refund the branch.",
    SUSPENDED: "A required access fact or item is missing. Learned ranks are preserved."
  };

  function text(tag, content, className) {
    const element = document.createElement(tag);
    if (content !== undefined && content !== null) element.textContent = String(content);
    if (className) element.className = className;
    return element;
  }

  function clear(element) { element.replaceChildren(); return element; }
  function readable(value) { return String(value ?? "—").replaceAll("_", " "); }
  function nodeById(id) { return ui.bootstrap?.graph?.nodes?.find((node) => node.id === id); }
  function traitById(id) { return ui.bootstrap?.lineage_catalog?.traits?.find((trait) => trait.id === id); }
  function profileById(id) { return ui.bootstrap?.lineage_catalog?.profiles?.find((profile) => profile.id === id); }
  function profileLabel(id) { return profileById(id)?.label || id; }
  function traitLabel(id) { return traitById(id)?.label || id; }
  function requestId() { return globalThis.crypto?.randomUUID?.() || `sw-${Date.now()}-${Math.random().toString(36).slice(2)}`; }
  function safeFilename(value) { return String(value).replace(/[^a-z0-9._-]/gi, "-").slice(0, 100); }

  function setStatus(message, kind = "") {
    $("status-message").textContent = message;
    document.querySelector(".status-strip").className = `status-strip ${kind}`.trim();
  }

  function connection(connected, label) {
    $("connection-dot").className = `connection-dot ${connected ? "connected" : "error"}`;
    $("connection-label").textContent = label || (connected ? "Local engine connected" : "Connection interrupted");
  }

  class ApiError extends Error {
    constructor(message, status, body) { super(message); this.name = "ApiError"; this.status = status; this.body = body; }
  }

  async function api(path, body) {
    const controller = new AbortController();
    const timeout = window.setTimeout(() => controller.abort(), 20000);
    try {
      const response = await fetch(path, {
        method: body === undefined ? "GET" : "POST",
        headers: body === undefined ? { Accept: "application/json" } : { Accept: "application/json", "Content-Type": "application/json" },
        body: body === undefined ? undefined : JSON.stringify(body),
        cache: "no-store", signal: controller.signal
      });
      let result;
      try { result = await response.json(); }
      catch { throw new ApiError("The local engine returned an unreadable response. Refresh to inspect its saved state.", response.status, null); }
      if (!response.ok) throw new ApiError(typeof result.error === "string" ? result.error : "The action was rejected.", response.status, result);
      connection(true);
      return result;
    } catch (error) {
      if (error instanceof ApiError) throw error;
      connection(false);
      throw new Error(body === undefined
        ? "The local engine could not be reached. Check that the launcher is running, then refresh."
        : "The connection ended before the result was confirmed. The action was not retried. Refresh to inspect the saved state before acting again.");
    } finally { window.clearTimeout(timeout); }
  }

  function showError(error) {
    if (error.status === 409 && error.body?.session) {
      ui.session = error.body.session;
      if (ui.session.last_lineage && !ui.lineage) ui.lineage = ui.session.last_lineage;
      render();
      setStatus("The session changed elsewhere. Its current state is loaded; choose your intended action again. Nothing was automatically retried.", "error");
    } else {
      setStatus(error.message || "The action failed. Your last confirmed state remains visible.", "error");
    }
  }

  async function runTask(label, task) {
    if (ui.busy) return;
    ui.busy = true;
    updateControls();
    setStatus(label, "busy");
    try { await task(); }
    catch (error) { showError(error); }
    finally { ui.busy = false; updateControls(); }
  }

  async function loadBootstrap() {
    await runTask("Reading the saved incarnation and source contracts…", async () => {
      const result = await api("/api/bootstrap");
      if (!result.graph?.nodes || !result.session?.state) throw new Error("The bootstrap contract is incomplete. The last confirmed view is preserved.");
      ui.bootstrap = result;
      ui.session = result.session;
      ui.loaded = true;
      if (!ui.lineage && result.session.last_lineage) ui.lineage = result.session.last_lineage;
      populateProfiles();
      renderSources();
      render();
      renderLineage();
      $("version-label").textContent = `Local engine ${result.version} / schema ${result.graph.schema_version}`;
      $("footer-version").textContent = `${result.graph.proposal_id} · v${result.version}`;
      setStatus(result.session.notice || "Session ready. Select a node, learn its contract, and make a capability visible.", "success");
    });
  }

  async function mutate(action, fields = {}) {
    const selectedLabel = fields.node ? nodeById(fields.node)?.label || fields.node : "scenario";
    await runTask(`Updating ${selectedLabel.toLowerCase()}…`, async () => {
      const result = await api("/api/action", { revision: ui.session.revision, action, request_id: requestId(), ...fields });
      ui.session = result.session;
      if (action === "reset") {
        ui.lineage = null;
        ui.previewChanged = false;
        // Reset also clears registered descendants; reload the authoritative catalog.
        const bootstrap = await api("/api/bootstrap");
        ui.bootstrap = bootstrap;
        ui.session = bootstrap.session;
        populateProfiles();
        renderSources();
        renderLineage();
      }
      render();
      const messages = {
        learn: `${selectedLabel} learned. Knowledge and present availability are tracked separately.`,
        activate: `${selectedLabel} activated. Costs committed once; advance time to complete the action.`,
        advance: `Advanced to tick ${ui.session.state.tick}. ${latestEventMessage()}`,
        set_axis: `${fields.axis} access is ${fields.access}. ${latestEventMessage()}`,
        set_lamp: `Lamp ${fields.equipped ? "equipped" : "removed"}. ${latestEventMessage()}`,
        respec: `${selectedLabel} refunded${fields.cascade ? " with learned dependents" : ""}. Recorded growth points returned.`,
        restore_resources: "Sandbox resources restored. Learned skills and recovery timers are preserved.",
        reset: "Practice scenario reset: six growth points, three focus, three charge, both access facts, and a lamp."
      };
      setStatus(messages[action] || readable(result.result), "success");
    });
  }

  function latestEventMessage() {
    const state = ui.session.state;
    const event = state.events?.at(-1);
    if (!event) return "No output has completed yet.";
    if (event.event === "ABORTED") return `${nodeById(event.node)?.label || event.node} aborted; no output was emitted.`;
    if (event.event === "COMPLETE") return `${nodeById(event.node)?.label || event.node} completed; one output was emitted.`;
    if (state.active) return `${nodeById(state.active.node)?.label || state.active.node} is still executing.`;
    return "The model is waiting for your next step.";
  }

  function render() {
    if (!ui.session || !ui.bootstrap) return;
    const state = ui.session.state;
    $("growth-points").textContent = state.growth_points;
    $("focus-value").textContent = state.resources.focus;
    $("charge-value").textContent = state.resources.charge;
    for (const resource of ["focus", "charge"]) {
      const max = ui.bootstrap.graph.scenario.resources[resource] || 3;
      $(`${resource}-meter`).style.width = `${Math.max(0, Math.min(100, state.resources[resource] / max * 100))}%`;
    }
    $("tick-value").textContent = String(state.tick).padStart(2, "0");
    $("revision-label").textContent = `revision ${ui.session.revision}`;
    $("incarnation-name").textContent = ui.session.last_lineage ? `Lineage ${ui.session.last_lineage.id.slice(-8)}` : "Practice scenario";
    $("axis-affinity").value = state.axis_access.Affinity;
    $("axis-techfinity").value = state.axis_access.Techfinity;
    $("lamp-equipped").checked = state.equipment.includes("lamp");
    for (const node of ui.bootstrap.graph.nodes) {
      const button = $(`node-${node.id}`);
      if (!button) continue;
      const meta = ui.session.nodes[node.id];
      const rank = state.ranks[node.id];
      button.classList.toggle("selected", node.id === ui.selected);
      button.classList.toggle("learned", rank > 0);
      button.dataset.availability = meta.availability;
      button.setAttribute("aria-pressed", String(node.id === ui.selected));
      button.querySelector("strong").textContent = node.label;
      button.querySelector(".node-rank").textContent = `${rank} / ${node.ranks.length}`;
      button.querySelector(".node-availability").textContent = readable(meta.availability);
      button.querySelector(".node-price").textContent = rank === node.ranks.length ? "LEARNED" : `${meta.next_growth_cost} GP`;
      button.setAttribute("aria-label", `${node.label}, ${node.id}, rank ${rank} of ${node.ranks.length}, ${readable(meta.availability)}. Select to inspect.`);
    }
    for (const edge of document.querySelectorAll("[data-edge]")) {
      const [from, to] = edge.dataset.edge.split("-");
      edge.classList.toggle("learned", state.ranks[from] > 0 && state.ranks[to] > 0);
    }
    renderDetails();
    renderEffect();
    renderEvents();
    updateControls();
  }

  function tag(label, type = "") { return text("span", label, `tag ${type}`.trim()); }

  function contractRow(dl, label, value) {
    const row = text("div", undefined, "contract-row");
    row.append(text("dt", label));
    const dd = text("dd");
    if (value instanceof Node) dd.append(value); else dd.textContent = value;
    row.append(dd);
    dl.append(row);
  }

  function renderDetails() {
    const node = nodeById(ui.selected);
    if (!node) return;
    const state = ui.session.state;
    const meta = ui.session.nodes[node.id];
    const rank = state.ranks[node.id];
    const spec = node.ranks[Math.max(0, rank - 1)];
    const action = spec.activation;
    $("detail-title").textContent = node.label;
    $("detail-kind").textContent = `${node.kind.toUpperCase()} / ${node.id}`;
    $("detail-availability").textContent = readable(meta.availability).toUpperCase();
    $("detail-availability").dataset.state = meta.availability;
    $("detail-description").textContent = descriptions[node.id] || "Inspect the explicit skill contract below.";
    const tags = clear($("detail-tags"));
    for (const method of node.methods) tags.append(tag(readable(method), method));
    const axes = node.mapping.axis_requires;
    if (axes === null) tags.append(tag("Mapping unresolved"));
    else if (axes.length === 0) tags.append(tag("No axis required"));
    else for (const axis of axes) tags.append(tag(axis, axis === "Affinity" ? "magic" : "technology"));
    const dl = text("dl");
    contractRow(dl, "Learned rank", `${rank} / ${node.ranks.length}`);
    contractRow(dl, "Learn prerequisites", spec.requires.map((req) => `${req.node} rank ${req.rank}`).join(" + ") || "None");
    const costs = text("span");
    const parts = [];
    if (action.cost.focus) parts.push(text("span", `${action.cost.focus} focus`, "focus-cost"));
    if (action.cost.charge) parts.push(text("span", `${action.cost.charge} charge`, "charge-cost"));
    parts.forEach((part, index) => { if (index) costs.append(document.createTextNode(" + ")); costs.append(part); });
    if (parts.length === 0) costs.textContent = "None";
    contractRow(dl, "Activation cost", costs);
    contractRow(dl, "Equipment", action.equipment.map(readable).join(", ") || "None");
    contractRow(dl, "Execution / recovery", `${action.duration_ticks} / ${action.recovery_ticks} ticks`);
    if (state.ready_at[node.id] > state.tick) contractRow(dl, "Recovery ends", `Tick ${state.ready_at[node.id]}`);
    contractRow(dl, "Capability", readable(action.output));
    clear($("detail-contract")).append(dl);
    const recipe = $("recipe-inputs");
    recipe.hidden = !node.recipe;
    clear(recipe);
    if (node.recipe) {
      recipe.append(text("strong", "COUPLED INPUT CONTRACT"));
      for (const input of node.recipe.inputs) {
        const line = text("p");
        const button = text("button", `${input.node} rank ${input.rank}`);
        button.type = "button";
        button.addEventListener("click", () => selectNode(input.node));
        line.append(button, document.createTextNode(` · ${readable(input.role)} → ${readable(input.capability)}`));
        recipe.append(line);
      }
      recipe.append(text("p", "Input lost → abort, no output, no activation refund. No automatic fallback."));
    }
    $("learn-node").textContent = meta.next_growth_cost === null || meta.next_growth_cost === undefined
      ? "All ranks learned" : `Learn ${rank > 0 ? `rank ${rank + 1}` : "skill"} · ${meta.next_growth_cost} GP`;
    $("activate-node").textContent = meta.availability === "ACTIVE" ? "Capability executing…" : "Activate capability";
    const reason = rank > 0 ? meta.reason : meta.learn_reason;
    if (state.active) $("learn-reason").textContent = `${nodeById(state.active.node)?.label || state.active.node} is active. Advance time, or interrupt through a scenario control.`;
    else if (meta.availability === "READY") $("learn-reason").textContent = "Ready to use. The full activation cost is committed once.";
    else if (reason) $("learn-reason").textContent = reasonText[reason] || readable(reason);
    else $("learn-reason").textContent = "Ready to learn. Learning never activates the capability automatically.";
  }

  function renderEffect() {
    const state = ui.session.state;
    const active = state.active;
    const output = state.outputs.at(-1);
    const event = state.events.at(-1);
    const chamber = $("effect-chamber");
    let effect = "idle", phase = "idle", title = "No capability emitted";
    let description = "Learn a skill, activate it, then advance the model to observe its output.";
    let badge = "IDLE";
    if (active) {
      const node = nodeById(active.node);
      effect = node.ranks[active.rank - 1].activation.output;
      phase = "active";
      title = `${effectNames[effect] || readable(effect)} · forming`;
      description = `${node.label} is executing. ${Math.max(0, active.ends_at - state.tick)} tick(s) remain; no output has completed yet.`;
      badge = "ACTIVE";
    } else if (event?.event === "ABORTED" && (!output || event.tick >= output.tick)) {
      phase = "aborted";
      title = `${nodeById(event.node)?.label || event.node} · interrupted`;
      description = "A required input was lost. No output was emitted; committed activation costs remain spent.";
      badge = "ABORTED";
    } else if (output) {
      effect = Object.hasOwn(effectNames, output.output) ? output.output : "idle";
      phase = "complete";
      title = effectNames[output.output] || readable(output.output);
      description = `${effectDescriptions[output.output] || "Confirmed capability output."} Emitted at tick ${output.tick}; displayed as the last recorded output.`;
      badge = "OUTPUT RECORDED";
    }
    chamber.dataset.effect = effect;
    chamber.dataset.phase = phase;
    $("chamber-state").textContent = badge;
    $("effect-name").textContent = title;
    $("effect-description").textContent = description;
    $("effect-svg-title").textContent = title;
    $("effect-svg-description").textContent = description;
    $("effect-tick").textContent = `T ${String(state.tick).padStart(3, "0")}`;
    $("output-count").textContent = `${state.outputs.length} output${state.outputs.length === 1 ? "" : "s"}`;
    $("active-action-label").textContent = active
      ? `${nodeById(active.node)?.label || active.node} completes at tick ${active.ends_at}.`
      : "The model waits for your next step.";
  }

  function renderEvents() {
    const events = ui.session.state.events;
    const outputs = ui.session.state.outputs;
    $("event-count").textContent = `${events.length} event${events.length === 1 ? "" : "s"}`;
    const list = clear($("event-log"));
    if (!events.length) { list.append(text("li", "No actions yet.")); return; }
    for (const event of events.slice(-30).reverse()) {
      const item = text("li");
      item.append(text("span", `T ${event.tick}`, "event-tick"), text("span", event.node, "event-node"), text("span", readable(event.event), `event-name ${event.event.toLowerCase()}`));
      const output = event.event === "COMPLETE" && outputs.findLast((entry) => entry.node === event.node && entry.tick === event.tick);
      if (output) item.append(text("span", readable(output.output), "event-output"));
      list.append(item);
    }
  }

  function updateControls() {
    const disabled = !ui.loaded || ui.busy;
    for (const id of ["axis-affinity", "axis-techfinity", "lamp-equipped", "restore-resources", "reset-session", "export-save", "import-save", "tick-forward", "tick-amount", "parent-a", "parent-b", "lineage-seed", "generate-lineage"]) $(id).disabled = disabled;
    $("refresh-session").disabled = ui.busy;
    const meta = ui.session?.nodes?.[ui.selected];
    const active = !!ui.session?.state?.active;
    $("learn-node").disabled = disabled || !meta?.learnable || active;
    $("activate-node").disabled = disabled || meta?.availability !== "READY" || active;
    $("respec-node").disabled = disabled || !ui.session?.state?.ranks?.[ui.selected] || active;
    $("cascade-refund").disabled = disabled || active;
    for (const id of ["apply-lineage", "export-lineage", "register-lineage"]) {
      const element = $(id);
      if (element) element.disabled = disabled || !ui.lineage;
    }
    if (ui.loaded && !ui.busy) {
      $("axis-affinity").value = ui.session.state.axis_access.Affinity;
      $("axis-techfinity").value = ui.session.state.axis_access.Techfinity;
      $("lamp-equipped").checked = ui.session.state.equipment.includes("lamp");
    }
  }

  function selectNode(id) {
    if (!nodeById(id)) return;
    ui.selected = id;
    $("cascade-refund").checked = false;
    render();
  }

  function switchTab(name, focus = false) {
    for (const tab of document.querySelectorAll('[role="tab"]')) {
      const selected = tab.id === `tab-${name}`;
      tab.classList.toggle("active", selected);
      tab.setAttribute("aria-selected", String(selected));
      tab.tabIndex = selected ? 0 : -1;
      $(tab.getAttribute("aria-controls")).hidden = !selected;
      if (selected && focus) tab.focus();
    }
  }

  function populateProfiles() {
    const profiles = ui.bootstrap?.lineage_catalog?.profiles || [];
    for (const [id, defaultIndex] of [["parent-a", 2], ["parent-b", 3]]) {
      const select = $(id);
      const previous = select.value;
      clear(select);
      for (const profile of profiles) {
        const suffix = profile.generation > 0 ? ` · generation ${profile.generation}` : "";
        const option = text("option", profile.label + suffix);
        option.value = profile.id;
        select.append(option);
      }
      select.value = profiles.some((profile) => profile.id === previous) ? previous : profiles[Math.min(defaultIndex, profiles.length - 1)]?.id || "";
      renderProfile(id);
    }
  }

  function renderProfile(id) {
    const profile = profileById($(id).value);
    $(`${id}-description`).textContent = profile?.description || "No contributor selected.";
    const traits = clear($(`${id}-traits`));
    for (const traitId of profile?.traits || []) {
      const trait = traitById(traitId);
      traits.append(tag(trait?.label || traitId, trait?.axis === "Affinity" ? "magic" : trait?.axis === "Techfinity" ? "technology" : ""));
    }
  }

  function markPreviewChanged() {
    if (!ui.lineage) return;
    ui.previewChanged = true;
    renderLineage();
  }

  async function generateLineage() {
    const seed = $("lineage-seed").value;
    if (!seed.trim()) { $("lineage-seed").focus(); setStatus("Enter an experiment seed before tracing a lineage.", "error"); return; }
    await runTask("Tracing contributor routes and candidate branches…", async () => {
      const result = await api("/api/lineage", { parent_a: $("parent-a").value, parent_b: $("parent-b").value, seed });
      ui.lineage = result.lineage;
      ui.previewChanged = false;
      renderLineage();
      setStatus("Lineage preview generated. Potential and pathway candidates are recorded; no incarnation state has changed.", "success");
    });
  }

  function potentialCard(axis, value) {
    const card = text("div", undefined, `potential-card ${axis === "Affinity" ? "magic" : "technology"}`);
    card.append(text("span", axis.toUpperCase(), "eyebrow"), text("strong", value ? "Potential recorded" : "No potential selected"), text("span", "Active access remains unavailable"));
    return card;
  }

  function renderLineage() {
    const container = $("lineage-result");
    const lineage = ui.lineage;
    if (!lineage) {
      // The initial empty state stays in the document until a lineage is generated.
      if (container.querySelector(".lineage-empty")) return;
      clear(container);
      const empty = text("section", undefined, "panel lineage-empty");
      empty.append(text("span", "02 / INSPECT THE PATHWAY", "eyebrow"), text("h2", "A new thread begins with its sources."), text("p", "Choose contributors and trace their routes. No preview is currently selected."));
      container.append(empty);
      return;
    }
    clear(container);
    if (ui.previewChanged) container.append(text("p", "The controls have changed. This is the last generated preview; trace again to use the new contributors or seed.", "lineage-stale-note"));
    const summary = text("section", undefined, "panel lineage-summary");
    const heading = text("div", undefined, "panel-heading");
    const titleGroup = text("div");
    titleGroup.append(text("span", "02 / GENERATED PREVIEW", "eyebrow"), text("h2", `Incarnation thread${lineage.generation ? ` · generation ${lineage.generation}` : ""}`));
    heading.append(titleGroup, text("span", lineage.status || "EXPERIMENTAL", "tiny-badge"));
    summary.append(heading, text("p", `${lineage.id} · seed: ${lineage.seed}`, "lineage-id"));
    summary.append(text("p", "Inherited potential, teaching routes, and blueprint routes are records to explore. Starting this incarnation keeps all ranks at zero, both axes unavailable, and no equipment installed.", "help-copy"));
    const potential = text("div", undefined, "potential-grid");
    for (const axis of ["Affinity", "Techfinity"]) potential.append(potentialCard(axis, !!lineage.axis_potential?.[axis]));
    summary.append(potential);
    const actions = text("div", undefined, "lineage-actions");
    const apply = text("button", "Start this incarnation →", "button button-primary");
    apply.id = "apply-lineage"; apply.type = "button"; apply.addEventListener("click", applyLineage);
    const register = text("button", "Keep as parent", "button button-secondary");
    register.id = "register-lineage"; register.type = "button"; register.addEventListener("click", registerLineage);
    const exportButton = text("button", "Export full lineage ↗", "text-button");
    exportButton.id = "export-lineage"; exportButton.type = "button"; exportButton.addEventListener("click", exportLineage);
    actions.append(apply, register, exportButton);
    summary.append(actions);
    container.append(summary, renderPathway(lineage), renderTraits(lineage), renderTrace(lineage));
    updateControls();
  }

  function renderPathway(lineage) {
    const panel = text("section", undefined, "panel pathway-panel");
    panel.append(text("span", "CONTRIBUTORS → SELECTED TRAITS → CANDIDATE BRANCHES", "eyebrow"), text("h2", "Pathways & interactions"));
    const map = text("div", undefined, "pathway-map");
    const parents = text("div", undefined, "pathway-contributors");
    (lineage.parent_ids || []).forEach((id, index) => {
      const card = text("div", undefined, "pathway-parent");
      card.append(text("span", `CONTRIBUTOR ${index === 0 ? "A" : "B"}`, "eyebrow"), text("strong", profileLabel(id)));
      parents.append(card);
    });
    map.append(parents, text("div", undefined, "pathway-join"), text("div", `${lineage.traits?.length || 0} selected trait records · no automatic grants`, "pathway-child"));
    panel.append(map);
    const list = text("ul", undefined, "branch-list");
    for (const branch of lineage.branches || []) {
      const item = text("li");
      if (typeof branch !== "object" || branch === null) { item.textContent = String(branch); list.append(item); continue; }
      item.append(text("strong", branch.label || branch.id || "Candidate branch"), document.createTextNode(" "), tag(branch.status === "CANDIDATE" ? "Candidate · no grant" : readable(branch.status || "Review")));
      if (branch.recipe_pattern) item.append(text("p", branch.recipe_pattern));
      if (branch.description) item.append(text("p", branch.description));
      if (branch.missing?.length) item.append(text("p", `Missing: ${branch.missing.map((entry) => typeof entry === "object" ? JSON.stringify(entry) : traitLabel(entry)).join("; ")}`));
      if (branch.skill_candidates?.length) item.append(text("p", `Skills to investigate: ${branch.skill_candidates.join(" → ")}. Each requires normal learning and access checks.`));
      if (!branch.label && !branch.description && !branch.id) item.append(text("pre", JSON.stringify(branch, null, 2), "raw-value"));
      list.append(item);
    }
    if (!list.childNodes.length) list.append(text("li", "No branch suggestions were produced by this experimental rule set."));
    panel.append(list);
    return panel;
  }

  function renderTraits(lineage) {
    const panel = text("section", undefined, "panel inherited-panel");
    panel.append(text("span", "PROVENANCE IS PRESERVED", "eyebrow"), text("h2", "Selected traits & transmission routes"));
    const list = text("div", undefined, "trait-list");
    for (const item of lineage.traits || []) {
      const trait = typeof item === "string" ? traitById(item) || { id: item, label: item } : item;
      const card = text("article", undefined, "trait-card");
      const heading = text("div", undefined, "trait-card-heading");
      heading.append(text("h3", trait.label || trait.id), tag(channelNames[trait.channel] || readable(trait.channel)));
      card.append(heading);
      if (trait.description) card.append(text("p", trait.description));
      const route = text("div", undefined, "trait-route");
      if (trait.axis) route.append(tag(`${trait.axis} potential`, trait.axis === "Affinity" ? "magic" : "technology"));
      if (trait.meaning && trait.meaning !== "potential") route.append(tag(readable(trait.meaning)));
      card.append(route);
      if (trait.provenance) {
        const provenance = trait.provenance;
        if (provenance.policy_id) card.append(text("div", `Policy: ${provenance.policy_id}`, "trait-provenance"));
        for (const reference of provenance.parent_references || []) {
          card.append(text("div", `${profileLabel(reference.profile_id)} → ${reference.trait_id} · generation ${reference.generation ?? 0}${reference.source_lineage_id ? ` · via ${reference.source_lineage_id}` : ""}`, "trait-provenance"));
        }
        if (provenance.founder_origins?.length) {
          const origins = provenance.founder_origins.map((origin) => typeof origin === "object" ? Object.entries(origin).map(([key, value]) => `${readable(key)}: ${typeof value === "object" ? JSON.stringify(value) : value}`).join(" / ") : origin);
          card.append(text("div", `Founder provenance: ${origins.join("; ")}`, "trait-provenance"));
        }
      }
      list.append(card);
    }
    if (!list.childNodes.length) list.append(text("p", "No eligible trait passed the gates for this seed. This is a valid zero-trait preview.", "empty-copy"));
    panel.append(list);
    return panel;
  }

  function renderTrace(lineage) {
    const panel = text("details", undefined, "panel lineage-trace");
    const summary = text("summary", `Deterministic trace · ${lineage.trace?.length || 0} decisions`);
    panel.append(summary);
    const list = text("ol", undefined, "trace-list");
    for (const step of lineage.trace || []) {
      const item = text("li");
      if (typeof step === "string") item.textContent = step;
      else if (step.trait_id) {
        item.append(text("strong", `${traitLabel(step.trait_id)} · ${step.inherited ? "selected" : "not selected"}`));
        if (step.reason) item.append(text("p", step.reason));
        item.append(text("p", `${channelNames[step.channel] || readable(step.channel)} · gate ${step.numerator}/${step.denominator} · draw ${step.draw}`));
        if (step.parent_ids?.length) item.append(text("p", `Sources: ${step.parent_ids.map(profileLabel).join(" + ")}`));
        item.append(text("p", `Policy: ${step.policy_id}`, "raw-value"));
      } else item.append(text("pre", JSON.stringify(step, null, 2), "raw-value"));
      list.append(item);
    }
    if (!list.childNodes.length) list.append(text("li", "No transmission candidates were present."));
    panel.append(list);
    return panel;
  }

  async function confirmChange(title, description, actionLabel) {
    if (ui.busy) return false;
    const dialog = $("confirm-dialog");
    $("confirm-title").textContent = title;
    $("confirm-description").textContent = description;
    $("confirm-action").textContent = actionLabel;
    dialog.returnValue = "cancel";
    return new Promise((resolve) => {
      dialog.addEventListener("close", () => resolve(dialog.returnValue === "confirm"), { once: true });
      dialog.showModal();
    });
  }

  async function applyLineage() {
    if (!ui.lineage || ui.busy) return;
    const lineage = ui.lineage;
    const confirmed = await confirmChange("Start this incarnation?", "This replaces current learned ranks, resources, action history, and equipment with a fresh incarnation. It keeps inherited potential as a provenance record; both axes start unavailable, no skills are learned, and no lamp is installed. Export the current save first if you want to keep it.", "Start new incarnation");
    if (!confirmed) return;
    await runTask("Starting an incarnation from the selected lineage…", async () => {
      const result = await api("/api/apply-lineage", { revision: ui.session.revision, lineage, request_id: requestId() });
      ui.session = result.session;
      ui.lineage = result.session.last_lineage || lineage;
      render();
      renderLineage();
      switchTab("skills", true);
      setStatus("New incarnation started. Potential is recorded; all learned ranks are zero, both axes unavailable, and equipment empty.", "success");
    });
  }

  async function registerLineage() {
    if (!ui.lineage) return;
    await runTask("Keeping the generated thread as a contributor for the next generation…", async () => {
      const result = await api("/api/register-lineage", { revision: ui.session.revision, lineage: ui.lineage, request_id: requestId() });
      ui.session = result.session;
      ui.bootstrap.lineage_catalog = result.lineage_catalog;
      populateProfiles();
      renderSources();
      render();
      setStatus("Thread kept as a parent. Select its generated profile in either contributor list to trace another generation. Current skills are unchanged.", "success");
    });
  }

  function downloadJson(value, filename) {
    const blob = new Blob([JSON.stringify(value, null, 2) + "\n"], { type: "application/json" });
    const url = URL.createObjectURL(blob);
    const link = document.createElement("a");
    link.href = url; link.download = filename;
    document.body.append(link); link.click(); link.remove();
    window.setTimeout(() => URL.revokeObjectURL(url), 1000);
  }

  function exportLineage() {
    if (!ui.lineage) return;
    downloadJson(ui.lineage, `${safeFilename(ui.lineage.id)}.json`);
    setStatus("Full lineage exported, including selected traits, source references, branches, and the deterministic trace.", "success");
  }

  async function exportSave() {
    await runTask("Preparing a portable save…", async () => {
      const save = await api("/api/export");
      downloadJson(save, `star-weaver-save-t${save.session.state.tick}-r${save.session.revision}.json`);
      setStatus("Save exported. It includes active-action timing, recovery, receipts, and registered lineage threads.", "success");
    });
  }

  async function importSave(event) {
    const file = event.target.files?.[0];
    event.target.value = "";
    if (!file || ui.busy) return;
    if (file.size > 510 * 1024) { setStatus("This save exceeds the 510 KiB workbench limit. The current session was preserved.", "error"); return; }
    let save;
    try { save = JSON.parse(await file.text()); }
    catch { setStatus("The selected file is not valid JSON. The current session was preserved.", "error"); return; }
    const confirmed = await confirmChange("Import this saved incarnation?", `Replace the current session with ${file.name}? The server validates the save and its mechanics before replacing anything. Export the current session first if you want to keep it.`, "Validate & import");
    if (!confirmed) return;
    await runTask("Validating the selected save before atomic replacement…", async () => {
      const result = await api("/api/import", { revision: ui.session.revision, save, request_id: requestId() });
      ui.session = result.session;
      const bootstrap = await api("/api/bootstrap");
      ui.bootstrap = bootstrap;
      ui.session = bootstrap.session;
      ui.lineage = ui.session.last_lineage;
      ui.previewChanged = false;
      populateProfiles();
      render(); renderSources(); renderLineage();
      setStatus("Save validated and restored. Active actions resume from their saved timing; no activation was repeated.", "success");
    });
  }

  function safeLink(label, url) {
    try {
      const parsed = new URL(url);
      if (!["https:", "http:"].includes(parsed.protocol)) return text("span", label);
      const link = text("a", `${label} ↗`, "source-link");
      link.href = parsed.href; link.target = "_blank"; link.rel = "noopener noreferrer";
      return link;
    } catch { return text("span", label); }
  }

  function decisionCard(eyebrow, title, state, description) {
    const card = text("section", undefined, "panel decision-card");
    card.append(text("span", eyebrow, "eyebrow"), text("h2", title), text("span", readable(state).toUpperCase(), "decision-state"));
    if (description) card.append(text("p", description));
    return card;
  }

  function renderSources() {
    if (!ui.bootstrap) return;
    const data = ui.bootstrap.decisions || {};
    const container = clear($("decisions-content"));
    const baseline = data.baseline || {};
    const approval = decisionCard("APPROVED MECHANICS", baseline.id || "SW-SKILL-001", baseline.status || "APPROVED_FOR_IMPLEMENTATION", baseline.scope || "The approved five-node implementation contract.");
    const dl = text("dl");
    for (const [label, value] of [["Approval date", baseline.approved_on], ["Authority", baseline.authority], ["Preserved source", baseline.source]]) {
      if (value) dl.append(text("dt", label), text("dd", value));
    }
    approval.append(dl);
    const extension = data.extension || {};
    const heredity = decisionCard("VERSIONED EXPERIMENT", extension.id || "Lineage policy", extension.status || "EXPERIMENTAL", extension.scope || ui.bootstrap.lineage_rules?.description);
    if (extension.boundary) heredity.append(text("p", extension.boundary));
    const canon = decisionCard("SYSTEM BOUNDARY", "Affinity / Techfinity", "Independent", "Finity remains Context Doubt with no runtime hierarchy or hereditary rule.");
    for (const system of data.systems || []) {
      const detail = text("p");
      detail.append(text("strong", `${system.id} · ${readable(system.status)}`), document.createTextNode(` — ${system.role}`));
      canon.append(detail);
      const source = ui.bootstrap.graph.canonical_systems[system.id]?.url || ui.bootstrap.graph.context_doubt[system.id]?.source_url;
      if (source) canon.append(safeLink(`${system.id} source record`, source));
    }
    container.append(approval, heredity, canon);
    const sources = data.sources || [];
    if (sources.length) {
      const card = decisionCard("RETRIEVED REFERENCES", "Source trail", "Read only", "These links identify the decision and scope records. The workbench does not write to Notion.");
      for (const source of sources) card.append(safeLink(source.label || source.url, source.url));
      container.append(card);
    }
    const methods = decisionCard("METHOD ≠ SYSTEM REQUIREMENT", "Explicit contracts", "Operational mapping", "Magic and technology are method tags. Axis requirements are separate gates; an empty requirement list is deliberate, while null stays unresolved.");
    methods.append(text("p", "Historical PROPOSED markers are retained in the baseline data. The approval above authorizes implementation without silently rewriting those source records."));
    container.append(methods);
    const limits = decisionCard("EVIDENCE LIMIT", "A local workbench", "Human checks remain", "Model ticks are discrete test steps. The observation chamber renders confirmed engine state and the last recorded output; it does not establish game balance, hereditary laws, or player enjoyment.");
    limits.append(text("p", "Full MAGECH kernel conformance remains outside this workbench until the complete frozen kernel and charter are available."));
    container.append(limits);
    renderRaw();
  }

  function renderRaw() {
    if (ui.bootstrap) $("raw-contract").textContent = JSON.stringify(ui.bootstrap[$("raw-contract-select").value], null, 2);
  }

  for (const button of document.querySelectorAll("[data-node]")) button.addEventListener("click", () => selectNode(button.dataset.node));
  for (const tab of document.querySelectorAll('[role="tab"]')) {
    tab.addEventListener("click", () => switchTab(tab.id.slice(4)));
    tab.addEventListener("keydown", (event) => {
      const tabs = Array.from(document.querySelectorAll('[role="tab"]'));
      const index = tabs.indexOf(tab);
      let next;
      if (event.key === "ArrowRight") next = tabs[(index + 1) % tabs.length];
      else if (event.key === "ArrowLeft") next = tabs[(index + tabs.length - 1) % tabs.length];
      else if (event.key === "Home") next = tabs[0];
      else if (event.key === "End") next = tabs.at(-1);
      if (next) { event.preventDefault(); switchTab(next.id.slice(4), true); }
    });
  }
  $("learn-node").addEventListener("click", () => mutate("learn", { node: ui.selected }));
  $("activate-node").addEventListener("click", () => mutate("activate", { node: ui.selected }));
  $("tick-forward").addEventListener("click", () => mutate("advance", { ticks: Number($("tick-amount").value) }));
  $("respec-node").addEventListener("click", () => mutate("respec", { node: ui.selected, cascade: $("cascade-refund").checked }));
  $("axis-affinity").addEventListener("change", (event) => mutate("set_axis", { axis: "Affinity", access: event.target.value }));
  $("axis-techfinity").addEventListener("change", (event) => mutate("set_axis", { axis: "Techfinity", access: event.target.value }));
  $("lamp-equipped").addEventListener("change", (event) => mutate("set_lamp", { equipped: event.target.checked }));
  $("restore-resources").addEventListener("click", () => mutate("restore_resources"));
  $("reset-session").addEventListener("click", async () => {
    const confirmed = await confirmChange("Reset the practice scenario?", "This clears learned ranks, outputs, action history, and registered lineage threads. It restores the approved five-node scenario with six growth points, three focus, three charge, both axes available, and a lamp. Export the current save first if you want to keep it.", "Reset scenario");
    if (confirmed) await mutate("reset");
  });
  $("export-save").addEventListener("click", exportSave);
  $("import-save").addEventListener("change", importSave);
  $("refresh-session").addEventListener("click", loadBootstrap);
  $("generate-lineage").addEventListener("click", generateLineage);
  for (const id of ["parent-a", "parent-b"]) $(id).addEventListener("change", () => { renderProfile(id); markPreviewChanged(); });
  $("lineage-seed").addEventListener("input", markPreviewChanged);
  $("lineage-seed").addEventListener("keydown", (event) => { if (event.key === "Enter") { event.preventDefault(); generateLineage(); } });
  $("raw-contract-select").addEventListener("change", renderRaw);
  document.querySelector(".brand").addEventListener("click", (event) => { event.preventDefault(); switchTab("skills", true); });
  loadBootstrap();
})();
