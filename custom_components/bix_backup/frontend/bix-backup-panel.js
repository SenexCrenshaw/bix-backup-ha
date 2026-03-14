const HOST_KEYS = ["connected", "running", "last_seen"];
const HOST_LABEL_SUFFIX = {
  connected: " Connected",
  running: " Running",
  last_seen: " Last Seen",
};
const JOB_KEYS = [
  "enabled",
  "running",
  "last_execution_status",
  "last_execution_time",
  "last_success_time",
  "last_failure_time",
  "last_duration_ms",
  "last_backup_total_files",
  "last_backup_total_bytes",
  "last_backup_data_added_bytes",
  "open_alert_count",
];
const JOB_LABEL_SUFFIX = {
  enabled: " Enabled",
  running: " Running",
  last_execution_status: " Last Execution Status",
  last_execution_time: " Last Execution Time",
  last_success_time: " Last Success Time",
  last_failure_time: " Last Failure Time",
  last_duration_ms: " Last Duration (ms)",
  last_backup_total_files: " Last Backup Total Files",
  last_backup_total_bytes: " Last Backup Total Bytes",
  last_backup_data_added_bytes: " Last Backup Data Added",
  open_alert_count: " Open Alert Count",
};
const SUMMARY_ORDER = [
  "sensor.bix_connected_hosts",
  "sensor.bix_running_jobs",
  "sensor.bix_failed_jobs_24h",
  "sensor.bix_jobs_failed_24h",
  "sensor.bix_open_alerts",
  "sensor.bix_open_alerts_total",
  "sensor.bix_open_critical_alerts",
  "sensor.bix_open_alerts_critical",
  "sensor.bix_open_warning_alerts",
  "sensor.bix_open_alerts_warning",
  "sensor.bix_open_info_alerts",
  "sensor.bix_open_alerts_info",
];
const CARD_TAG_BY_TYPE = {
  button: "hui-button-card",
  entities: "hui-entities-card",
  glance: "hui-glance-card",
  grid: "hui-grid-card",
};
const STATUS_ACCENT = {
  success: "var(--success-color)",
  succeeded: "var(--success-color)",
  running: "var(--warning-color)",
  failed: "var(--error-color)",
  error: "var(--error-color)",
  unknown: "var(--secondary-text-color)",
};

class BixBackupPanel extends HTMLElement {
  constructor() {
    super();
    this.attachShadow({ mode: "open" });
    this._hass = undefined;
    this._panel = undefined;
    this._route = undefined;
    this._narrow = false;
    this._selectedJobId = undefined;
    this._renderToken = 0;
    this._helpersPromise = undefined;
  }

  set hass(value) {
    this._hass = value;
    this._render();
  }

  set panel(value) {
    this._panel = value;
    this._render();
  }

  set route(value) {
    this._route = value;
    this._render();
  }

  set narrow(value) {
    this._narrow = Boolean(value);
    this._render();
  }

  _allBixStates() {
    if (!this._hass?.states) {
      return [];
    }
    return Object.entries(this._hass.states)
      .map(([entityId, stateObj]) => ({ entityId, stateObj }))
      .filter(({ entityId }) => entityId.includes(".bix_"));
  }

  _summaryEntities(states) {
    const items = states
      .filter(({ entityId }) => {
        return (
          entityId.startsWith("sensor.bix_") &&
          !entityId.startsWith("sensor.bix_host_") &&
          !entityId.startsWith("sensor.bix_job_")
        );
      })
      .map(({ entityId }) => entityId);
    const order = new Map(SUMMARY_ORDER.map((entityId, index) => [entityId, index]));
    return items.sort((left, right) => {
      const leftRank = order.has(left) ? order.get(left) : SUMMARY_ORDER.length;
      const rightRank = order.has(right) ? order.get(right) : SUMMARY_ORDER.length;
      if (leftRank !== rightRank) {
        return leftRank - rightRank;
      }
      return left.localeCompare(right);
    });
  }

  _stateValue(entityId) {
    return this._hass?.states?.[entityId];
  }

  _entityStateText(entityId, fallback = "Unknown") {
    const stateObj = this._stateValue(entityId);
    const value = String(stateObj?.state || "").trim();
    return value || fallback;
  }

  _parseGroupedEntity(entityId, prefix, knownKeys) {
    if (!entityId.startsWith(`sensor.bix_${prefix}_`) && !entityId.startsWith(`binary_sensor.bix_${prefix}_`)) {
      return undefined;
    }
    const domainSplit = entityId.split(".", 2);
    if (domainSplit.length !== 2) {
      return undefined;
    }
    const raw = domainSplit[1].slice(`bix_${prefix}_`.length);
    const sortedKeys = [...knownKeys].sort((left, right) => right.length - left.length);
    for (const key of sortedKeys) {
      const suffix = `_${key}`;
      if (raw.endsWith(suffix)) {
        return {
          groupId: raw.slice(0, -suffix.length),
          key,
        };
      }
    }
    return undefined;
  }

  _groupLabel(prefix, groupId, key, friendlyName) {
    const normalized = String(friendlyName || "").trim();
    const suffixes = prefix === "host" ? HOST_LABEL_SUFFIX : JOB_LABEL_SUFFIX;
    const expectedSuffix = suffixes[key];
    if (normalized && expectedSuffix && normalized.endsWith(expectedSuffix)) {
      return normalized.slice(0, -expectedSuffix.length).replace(/^BIX Host /, "").replace(/^BIX Job /, "").trim();
    }
    return groupId.replaceAll("_", " ");
  }

  _groupEntities(states, prefix, knownKeys) {
    const groups = new Map();
    for (const { entityId, stateObj } of states) {
      const parsed = this._parseGroupedEntity(entityId, prefix, knownKeys);
      if (!parsed) {
        continue;
      }
      if (!groups.has(parsed.groupId)) {
        groups.set(parsed.groupId, { label: undefined, entities: new Map() });
      }
      const group = groups.get(parsed.groupId);
      group.entities.set(parsed.key, entityId);
      if (!group.label) {
        const friendlyName = String(stateObj?.attributes?.friendly_name || "").trim();
        group.label = this._groupLabel(prefix, parsed.groupId, parsed.key, friendlyName);
      }
    }
    return [...groups.entries()]
      .map(([groupId, group]) => ({ groupId, label: group.label || groupId, entities: group.entities }))
      .sort((left, right) => left.label.localeCompare(right.label));
  }

  _groupEntityId(group, key) {
    return group?.entities?.get(key);
  }

  _parseTimestamp(raw) {
    const value = String(raw || "").trim();
    if (!value || value === "unknown" || value === "unavailable") {
      return undefined;
    }
    const timestamp = Date.parse(value);
    return Number.isFinite(timestamp) ? timestamp : undefined;
  }

  _countSuccessfulJobs24h(jobGroups) {
    const cutoff = Date.now() - 24 * 60 * 60 * 1000;
    let count = 0;
    for (const group of jobGroups) {
      const status = this._entityStateText(this._groupEntityId(group, "last_execution_status"), "").toLowerCase();
      const successTs =
        this._parseTimestamp(this._entityStateText(this._groupEntityId(group, "last_success_time"), "")) ??
        this._parseTimestamp(this._entityStateText(this._groupEntityId(group, "last_execution_time"), ""));
      if ((status === "success" || status === "succeeded") && successTs && successTs >= cutoff) {
        count += 1;
      }
    }
    return count;
  }

  _formatBytes(raw) {
    const value = Number(raw);
    if (!Number.isFinite(value) || value < 0) {
      return "Unknown";
    }
    if (value < 1024) {
      return `${value} B`;
    }
    const units = ["KB", "MB", "GB", "TB", "PB"];
    let size = value;
    let index = -1;
    while (size >= 1024 && index < units.length - 1) {
      size /= 1024;
      index += 1;
    }
    return `${size.toFixed(size >= 10 || index === 0 ? 0 : 1)} ${units[index]}`;
  }

  _formatDurationMs(raw) {
    const value = Number(raw);
    if (!Number.isFinite(value) || value <= 0) {
      return "Unknown";
    }
    const totalSeconds = Math.round(value / 1000);
    const hours = Math.floor(totalSeconds / 3600);
    const minutes = Math.floor((totalSeconds % 3600) / 60);
    const seconds = totalSeconds % 60;
    if (hours > 0) {
      return `${hours}h ${minutes}m`;
    }
    if (minutes > 0) {
      return `${minutes}m ${seconds}s`;
    }
    return `${seconds}s`;
  }

  _formatWhen(raw) {
    const timestamp = this._parseTimestamp(raw);
    if (!timestamp) {
      return "Unknown";
    }
    return new Intl.DateTimeFormat(undefined, {
      month: "short",
      day: "numeric",
      hour: "numeric",
      minute: "2-digit",
    }).format(new Date(timestamp));
  }

  _jobButtons(states) {
    return states
      .filter(({ entityId }) => entityId.startsWith("button.bix_job_") && entityId.endsWith("_run_backup"))
      .map(({ entityId, stateObj }) => ({
        entityId,
        label: String(stateObj?.attributes?.friendly_name || entityId),
        available: String(stateObj?.state || "") !== "unavailable",
      }))
      .sort((left, right) => left.label.localeCompare(right.label));
  }

  _alertButtons(states) {
    return states
      .filter(({ entityId }) => {
        return (
          entityId.startsWith("button.bix_alert_") &&
          (entityId.endsWith("_ack") || entityId.endsWith("_resolve"))
        );
      })
      .map(({ entityId, stateObj }) => ({
        entityId,
        label: String(stateObj?.attributes?.friendly_name || entityId),
        available: String(stateObj?.state || "") !== "unavailable",
      }))
      .sort((left, right) => left.label.localeCompare(right.label));
  }

  _alertsForJob(alertButtons, group) {
    const alerts = new Map();
    for (const button of alertButtons) {
      const stateObj = this._stateValue(button.entityId);
      const attrs = stateObj?.attributes || {};
      const jobId = String(attrs.job_id || "").trim();
      const alertId = String(attrs.alert_id || "").trim();
      if (!jobId || !alertId || jobId !== group.groupId) {
        continue;
      }
      if (!alerts.has(alertId)) {
        alerts.set(alertId, {
          id: alertId,
          severity: String(attrs.severity || "info").trim(),
          message: String(attrs.message || "No message").trim(),
          count: Number(attrs.count || 0),
          firstSeenAt: String(attrs.first_seen_at || "").trim(),
          lastSeenAt: String(attrs.last_seen_at || "").trim(),
          ackEntityId: undefined,
          resolveEntityId: undefined,
        });
      }
      const entry = alerts.get(alertId);
      if (String(attrs.action || "").trim() === "ack") {
        entry.ackEntityId = button.entityId;
      }
      if (String(attrs.action || "").trim() === "resolve") {
        entry.resolveEntityId = button.entityId;
      }
    }
    return [...alerts.values()].sort((left, right) => {
      const leftTs = this._parseTimestamp(left.lastSeenAt) || 0;
      const rightTs = this._parseTimestamp(right.lastSeenAt) || 0;
      return rightTs - leftTs;
    });
  }

  _emptyCard(message) {
    const card = document.createElement("ha-card");
    const content = document.createElement("div");
    content.className = "empty-card";
    content.textContent = message;
    card.appendChild(content);
    return card;
  }

  _overviewCard(jobGroups) {
    const tiles = [
      {
        label: "Connected Hosts",
        value: this._entityStateText("sensor.bix_connected_hosts", "0"),
      },
      {
        label: "Running Jobs",
        value: this._entityStateText("sensor.bix_running_jobs", "0"),
      },
      {
        label: "Successful Jobs (24h)",
        value: String(this._countSuccessfulJobs24h(jobGroups)),
      },
      {
        label: "Failed Jobs (24h)",
        value:
          this._entityStateText("sensor.bix_failed_jobs_24h", "") ||
          this._entityStateText("sensor.bix_jobs_failed_24h", "0"),
      },
      {
        label: "Open Alerts",
        value:
          this._entityStateText("sensor.bix_open_alerts", "") ||
          this._entityStateText("sensor.bix_open_alerts_total", "0"),
      },
    ];

    const card = document.createElement("ha-card");
    card.innerHTML = `
      <div class="overview-card">
        <div class="card-title">Backup Overview</div>
        <div class="metric-grid">
          ${tiles
            .map(
              (tile) => `
                <div class="metric">
                  <div class="metric-label">${tile.label}</div>
                  <div class="metric-value">${tile.value}</div>
                </div>
              `
            )
            .join("")}
        </div>
      </div>
    `;
    return card;
  }

  _jobSummaryCard(group) {
    const status = this._entityStateText(this._groupEntityId(group, "last_execution_status"));
    const running = this._entityStateText(this._groupEntityId(group, "running"), "").toLowerCase() === "on";
    const effectiveStatus = running ? "running" : status;
    const duration = this._formatDurationMs(this._entityStateText(this._groupEntityId(group, "last_duration_ms"), ""));
    const totalBytes = this._formatBytes(
      this._entityStateText(this._groupEntityId(group, "last_backup_total_bytes"), "")
    );
    const lastRun = this._formatWhen(this._entityStateText(this._groupEntityId(group, "last_execution_time"), ""));
    const alerts = this._entityStateText(this._groupEntityId(group, "open_alert_count"), "0");
    const statusColor = STATUS_ACCENT[String(effectiveStatus).toLowerCase()] || "var(--secondary-text-color)";
    const selected = this._selectedJobId === group.groupId;

    const card = document.createElement("ha-card");
    card.classList.toggle("job-summary-card", true);
    card.classList.toggle("selected", selected);
    card.setAttribute("role", "button");
    card.setAttribute("tabindex", "0");
    card.dataset.jobId = group.groupId;
    card.setAttribute("aria-pressed", selected ? "true" : "false");
    card.innerHTML = `
      <div class="job-card">
        <div class="job-top">
          <div>
            <div class="card-title">${group.label}</div>
            <div class="job-subtitle">Last run ${lastRun} · Click for details</div>
          </div>
          <div class="status-pill" style="--status-color:${statusColor}">${effectiveStatus}</div>
        </div>
        <div class="metric-grid compact">
          <div class="metric">
            <div class="metric-label">Duration</div>
            <div class="metric-value small">${duration}</div>
          </div>
          <div class="metric">
            <div class="metric-label">Total Bytes</div>
            <div class="metric-value small">${totalBytes}</div>
          </div>
          <div class="metric">
            <div class="metric-label">Open Alerts</div>
            <div class="metric-value small">${alerts}</div>
          </div>
        </div>
      </div>
    `;
    return card;
  }

  _alertDetailCard(alert) {
    const severity = String(alert.severity || "info").toLowerCase();
    const severityColor = STATUS_ACCENT[severity] || "var(--primary-color)";
    const countLabel = Number.isFinite(alert.count) && alert.count > 1 ? `${alert.count} hits` : "1 hit";

    const card = document.createElement("ha-card");
    card.innerHTML = `
      <div class="alert-card">
        <div class="alert-top">
          <div class="status-pill" style="--status-color:${severityColor}">${severity}</div>
          <div class="job-subtitle">Last seen ${this._formatWhen(alert.lastSeenAt)}</div>
        </div>
        <div class="alert-message">${alert.message || "No message"}</div>
        <div class="alert-meta">
          <span>${countLabel}</span>
          <span>First seen ${this._formatWhen(alert.firstSeenAt)}</span>
        </div>
        <div class="alert-actions" data-alert-id="${alert.id}"></div>
      </div>
    `;
    return card;
  }

  _syncSelectedJob(jobGroups) {
    if (!jobGroups.length) {
      this._selectedJobId = undefined;
      return undefined;
    }
    if (!this._selectedJobId || !jobGroups.some((group) => group.groupId === this._selectedJobId)) {
      this._selectedJobId = jobGroups[0].groupId;
    }
    return jobGroups.find((group) => group.groupId === this._selectedJobId) || jobGroups[0];
  }

  _selectJob(jobId) {
    if (!jobId || this._selectedJobId === jobId) {
      return;
    }
    this._selectedJobId = jobId;
    this._render();
  }

  _jobButtonForGroup(jobButtons, group) {
    return jobButtons.find((item) => item.entityId.startsWith(`button.bix_job_${group.groupId}_`));
  }

  _selectedJobHostGroup(group, jobButtons, hostGroups) {
    const runButton = this._jobButtonForGroup(jobButtons, group);
    const buttonAttrs = this._stateValue(runButton?.entityId)?.attributes || {};
    const hostId = String(buttonAttrs.host_id || "").trim();
    if (hostId) {
      return hostGroups.find((hostGroup) => hostGroup.groupId === hostId);
    }
    return undefined;
  }

  _hostHealthCard(hostGroup, group) {
    if (!hostGroup) {
      return this._emptyCard(`No host details available for ${group.label}.`);
    }

    const connected = this._entityStateText(this._groupEntityId(hostGroup, "connected"), "unknown");
    const running = this._entityStateText(this._groupEntityId(hostGroup, "running"), "unknown");
    const lastSeen = this._formatWhen(this._entityStateText(this._groupEntityId(hostGroup, "last_seen"), ""));
    const jobStatus = this._entityStateText(this._groupEntityId(group, "last_execution_status"), "").toLowerCase();

    let hint = "Host looks healthy.";
    if (connected !== "on") {
      hint = "Likely host-side: the assigned host is not connected.";
    } else if (running === "on") {
      hint = "Host-side activity detected: this plan or another task is currently running on the host.";
    } else if (jobStatus === "failed" || jobStatus === "error") {
      hint = "Host is connected, so the failure is more likely controller-side, storage-side, or job config related.";
    }

    const card = document.createElement("ha-card");
    card.innerHTML = `
      <div class="overview-card">
        <div class="card-title">Host Health</div>
        <div class="metric-grid compact">
          <div class="metric">
            <div class="metric-label">Host</div>
            <div class="metric-value small">${hostGroup.label}</div>
          </div>
          <div class="metric">
            <div class="metric-label">Connected</div>
            <div class="metric-value small">${connected}</div>
          </div>
          <div class="metric">
            <div class="metric-label">Running</div>
            <div class="metric-value small">${running}</div>
          </div>
          <div class="metric">
            <div class="metric-label">Last Seen</div>
            <div class="metric-value small">${lastSeen}</div>
          </div>
        </div>
        <div class="job-subtitle" style="margin-top:12px;">${hint}</div>
      </div>
    `;
    return card;
  }

  async _selectedJobCards(group, jobButtons, hostGroups) {
    if (!group) {
      return [this._emptyCard("Select a BIX job to inspect its latest execution details.")];
    }

    const executionEntities = [
      this._groupEntityId(group, "last_execution_status"),
      this._groupEntityId(group, "last_execution_time"),
      this._groupEntityId(group, "last_success_time"),
      this._groupEntityId(group, "last_failure_time"),
      this._groupEntityId(group, "last_duration_ms"),
      this._groupEntityId(group, "running"),
      this._groupEntityId(group, "enabled"),
    ].filter(Boolean);
    const metricEntities = [
      this._groupEntityId(group, "last_backup_total_files"),
      this._groupEntityId(group, "last_backup_total_bytes"),
      this._groupEntityId(group, "last_backup_data_added_bytes"),
      this._groupEntityId(group, "open_alert_count"),
    ].filter(Boolean);

    const cards = [
      this._hostHealthCard(this._selectedJobHostGroup(group, jobButtons, hostGroups), group),
      await this._entitiesCard(`${group.label} Execution`, executionEntities),
      await this._entitiesCard(`${group.label} Metrics`, metricEntities),
    ];

    const runButton = this._jobButtonForGroup(jobButtons, group);
    if (runButton) {
      cards.push(
        await this._createCard({
          type: "button",
          entity: runButton.entityId,
          name: `Run ${group.label}`,
          show_state: false,
          tap_action: {
            action: "call-service",
            service: "button.press",
            target: { entity_id: runButton.entityId },
          },
        })
      );
    }

    return cards;
  }

  async _selectedJobAlertCards(group, alertButtons) {
    if (!group) {
      return [this._emptyCard("Select a BIX job to inspect recent alerts.")];
    }

    const alerts = this._alertsForJob(alertButtons, group);
    if (!alerts.length) {
      return [this._emptyCard(`No recent alerts for ${group.label}.`)];
    }

    const cards = alerts.map((alert) => this._alertDetailCard(alert));
    for (let index = 0; index < alerts.length; index += 1) {
      const alert = alerts[index];
      const actionEntities = [alert.ackEntityId, alert.resolveEntityId].filter(Boolean);
      if (!actionEntities.length) {
        continue;
      }
      const actionsCard = await this._createCard({
        type: "grid",
        square: false,
        columns: this._narrow ? 1 : 2,
        cards: actionEntities.map((entityId) => ({
          type: "button",
          entity: entityId,
          show_state: false,
          tap_action: {
            action: "call-service",
            service: "button.press",
            target: { entity_id: entityId },
          },
        })),
      });
      if (actionsCard && typeof actionsCard === "object" && "hass" in actionsCard) {
        actionsCard.hass = this._hass;
      }
      const mount = cards[index].querySelector(".alert-actions");
      if (mount) {
        mount.replaceChildren(actionsCard);
      }
    }
    return cards;
  }

  async _createCard(config) {
    if (!this._helpersPromise) {
      const loadHelpers = window.loadCardHelpers;
      this._helpersPromise =
        typeof loadHelpers === "function" ? loadHelpers() : Promise.resolve(undefined);
    }
    const helpers = await this._helpersPromise;
    if (helpers?.createCardElement) {
      return helpers.createCardElement(config);
    }
    const tagName = CARD_TAG_BY_TYPE[config?.type];
    if (tagName) {
      await customElements.whenDefined(tagName);
      const card = document.createElement(tagName);
      if (typeof card.setConfig === "function") {
        card.setConfig(config);
      }
      return card;
    }
    const fallback = document.createElement("ha-card");
    const pre = document.createElement("pre");
    pre.textContent = JSON.stringify(config, null, 2);
    fallback.appendChild(pre);
    return fallback;
  }

  _buttonGrid(title, items, columns) {
    if (!items.length) {
      return this._emptyCard(`No ${title.toLowerCase()} available.`);
    }
    return this._createCard({
      type: "grid",
        title,
        square: false,
        columns,
        cards: items.map((item) => ({
          type: "button",
          entity: item.entityId,
          name: item.label,
          tap_action: { action: "call-service", service: "button.press", target: { entity_id: item.entityId } },
          show_state: false,
          icon_height: "22px",
        })),
      });
  }

  _entitiesCard(title, entities) {
    if (!entities.length) {
      return this._emptyCard(`No ${title.toLowerCase()} available.`);
    }
    return this._createCard({
      type: "entities",
      title,
      show_header_toggle: false,
      state_color: true,
      entities,
    });
  }

  async _render() {
    if (!this.shadowRoot) {
      return;
    }

    const token = ++this._renderToken;
    const title = this._panel?.config?.title || "BIX Backup";

    this.shadowRoot.innerHTML = `
      <style>
        :host {
          display: block;
          min-height: 100%;
          background: var(--lovelace-background, var(--primary-background-color));
          color: var(--primary-text-color);
        }
        .page {
          max-width: 1440px;
          margin: 0 auto;
          padding: 24px 16px 40px;
        }
        .hero {
          margin-bottom: 20px;
        }
        .eyebrow {
          color: var(--secondary-text-color);
          font-size: 12px;
          font-weight: 600;
          letter-spacing: 0.08em;
          text-transform: uppercase;
          margin-bottom: 8px;
        }
        h1 {
          margin: 0;
          font-size: 32px;
          line-height: 1.1;
          font-weight: 700;
        }
        .lede {
          margin-top: 10px;
          color: var(--secondary-text-color);
          max-width: 860px;
          line-height: 1.5;
        }
        .section {
          margin-top: 24px;
        }
        .section h2 {
          margin: 0 0 12px;
          font-size: 18px;
          line-height: 1.2;
          font-weight: 600;
        }
        .cards {
          display: grid;
          gap: 16px;
        }
        .cards.columns-2 {
          grid-template-columns: repeat(auto-fit, minmax(320px, 1fr));
        }
        .cards.columns-3 {
          grid-template-columns: repeat(auto-fit, minmax(300px, 1fr));
        }
        .overview-card,
        .job-card {
          padding: 16px;
        }
        ha-card.job-summary-card {
          cursor: pointer;
          transition: box-shadow 140ms ease, transform 140ms ease, border-color 140ms ease;
          border: 1px solid transparent;
        }
        ha-card.job-summary-card:hover,
        ha-card.job-summary-card:focus-visible {
          transform: translateY(-1px);
          box-shadow: var(--ha-card-box-shadow, 0 2px 4px rgba(0, 0, 0, 0.16));
        }
        ha-card.job-summary-card.selected {
          border-color: var(--primary-color);
          box-shadow: 0 0 0 1px var(--primary-color);
        }
        .card-title {
          font-size: 16px;
          font-weight: 600;
          line-height: 1.2;
        }
        .metric-grid {
          display: grid;
          gap: 12px;
          margin-top: 14px;
          grid-template-columns: repeat(auto-fit, minmax(140px, 1fr));
        }
        .metric-grid.compact {
          grid-template-columns: repeat(auto-fit, minmax(120px, 1fr));
        }
        .metric {
          padding: 12px;
          border-radius: 12px;
          background: var(--secondary-background-color);
        }
        .metric-label {
          color: var(--secondary-text-color);
          font-size: 12px;
          line-height: 1.3;
          margin-bottom: 6px;
        }
        .metric-value {
          font-size: 26px;
          font-weight: 700;
          line-height: 1.1;
        }
        .metric-value.small {
          font-size: 18px;
        }
        .job-top {
          display: flex;
          align-items: flex-start;
          justify-content: space-between;
          gap: 12px;
        }
        .job-subtitle {
          margin-top: 6px;
          color: var(--secondary-text-color);
          font-size: 13px;
        }
        .status-pill {
          padding: 6px 10px;
          border-radius: 999px;
          background: color-mix(in srgb, var(--status-color) 18%, transparent);
          color: var(--status-color);
          font-size: 12px;
          font-weight: 700;
          text-transform: uppercase;
          letter-spacing: 0.04em;
          white-space: nowrap;
        }
        .alert-card {
          padding: 16px;
        }
        .alert-top {
          display: flex;
          align-items: center;
          justify-content: space-between;
          gap: 12px;
          margin-bottom: 10px;
        }
        .alert-message {
          font-size: 15px;
          line-height: 1.45;
          margin-bottom: 12px;
        }
        .alert-meta {
          display: flex;
          flex-wrap: wrap;
          gap: 10px;
          color: var(--secondary-text-color);
          font-size: 13px;
          margin-bottom: 12px;
        }
        .empty-card {
          padding: 16px;
          color: var(--secondary-text-color);
        }
        @media (max-width: 720px) {
          .page {
            padding: 16px 12px 32px;
          }
          h1 {
            font-size: 26px;
          }
        }
      </style>
      <div class="page">
        <div class="hero">
          <div class="eyebrow">Home Assistant Panel</div>
          <h1>${title}</h1>
          <div class="lede">
            Live controller summary, job actions, host health, and job status using native Home Assistant cards and theming.
          </div>
        </div>
        <section class="section">
          <h2>Controller</h2>
          <div class="cards columns-2" id="controller-cards"></div>
        </section>
        <section class="section">
          <h2>Actions</h2>
          <div class="cards columns-2" id="action-cards"></div>
        </section>
        <section class="section">
          <h2>Hosts</h2>
          <div class="cards columns-3" id="host-cards"></div>
        </section>
        <section class="section">
          <h2>Jobs</h2>
          <div class="cards columns-3" id="job-cards"></div>
        </section>
        <section class="section">
          <h2>Selected Plan</h2>
          <div class="cards columns-3" id="selected-job-cards"></div>
        </section>
        <section class="section">
          <h2>Recent Alerts</h2>
          <div class="cards columns-3" id="selected-alert-cards"></div>
        </section>
      </div>
    `;

    if (!this._hass?.states) {
      return;
    }

    const states = this._allBixStates();
    const summaryEntities = this._summaryEntities(states);
    const hostGroups = this._groupEntities(states, "host", HOST_KEYS);
    const jobGroups = this._groupEntities(states, "job", JOB_KEYS);
    const selectedJob = this._syncSelectedJob(jobGroups);
    const jobButtons = this._jobButtons(states);
    const alertButtons = this._alertButtons(states);

    const controllerCards = [this._overviewCard(jobGroups)];

    const actionCards = [
      await this._buttonGrid("Run Backup", jobButtons, this._narrow ? 1 : 2),
      await this._buttonGrid("Alert Actions", alertButtons, this._narrow ? 1 : 2),
    ];

    const hostCards =
      hostGroups.length === 0
        ? [this._emptyCard("No BIX hosts detected.")]
        : await Promise.all(
            hostGroups.map((group) =>
              this._entitiesCard(
                group.label,
                HOST_KEYS.filter((key) => group.entities.has(key)).map((key) => group.entities.get(key))
              )
            )
          );

    const jobCards =
      jobGroups.length === 0
        ? [this._emptyCard("No BIX jobs detected.")]
        : jobGroups.map((group) => this._jobSummaryCard(group));
    const selectedJobCards = await this._selectedJobCards(selectedJob, jobButtons, hostGroups);
    const selectedAlertCards = await this._selectedJobAlertCards(selectedJob, alertButtons);

    if (token !== this._renderToken) {
      return;
    }

    const mount = (id, cards) => {
      const target = this.shadowRoot.getElementById(id);
      if (!target) {
        return;
      }
      target.replaceChildren(...cards);
      for (const card of cards) {
        if (card && typeof card === "object" && "hass" in card) {
          card.hass = this._hass;
        }
      }
    };

    mount("controller-cards", controllerCards);
    mount("action-cards", actionCards);
    mount("host-cards", hostCards);
    mount("job-cards", jobCards);
    mount("selected-job-cards", selectedJobCards);
    mount("selected-alert-cards", selectedAlertCards);

    for (const card of this.shadowRoot.querySelectorAll("ha-card.job-summary-card[data-job-id]")) {
      const activate = () => this._selectJob(card.dataset.jobId);
      card.addEventListener("click", activate);
      card.addEventListener("keydown", (event) => {
        if (event.key === "Enter" || event.key === " ") {
          event.preventDefault();
          activate();
        }
      });
    }
  }
}

customElements.define("bix-backup-panel", BixBackupPanel);
