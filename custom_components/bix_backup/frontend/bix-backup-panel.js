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

class BixBackupPanel extends HTMLElement {
  constructor() {
    super();
    this.attachShadow({ mode: "open" });
    this._hass = undefined;
    this._panel = undefined;
    this._route = undefined;
    this._narrow = false;
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

  _emptyCard(message) {
    const card = document.createElement("ha-card");
    const content = document.createElement("div");
    content.className = "empty-card";
    content.textContent = message;
    card.appendChild(content);
    return card;
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
      </div>
    `;

    if (!this._hass?.states) {
      return;
    }

    const states = this._allBixStates();
    const summaryEntities = this._summaryEntities(states);
    const hostGroups = this._groupEntities(states, "host", HOST_KEYS);
    const jobGroups = this._groupEntities(states, "job", JOB_KEYS);
    const jobButtons = this._jobButtons(states);
    const alertButtons = this._alertButtons(states);

    const controllerCards =
      summaryEntities.length === 0
        ? [this._emptyCard("No BIX summary sensors detected.")]
        : [
            await this._createCard({
              type: "glance",
              title: "Backup Overview",
              show_state: true,
              show_name: true,
              columns: this._narrow ? 2 : 4,
              entities: summaryEntities,
            }),
            await this._createCard({
              type: "entities",
              title: "Controller Signals",
              show_header_toggle: false,
              entities: summaryEntities,
            }),
          ];

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
        : await Promise.all(
            jobGroups.map((group) =>
              this._entitiesCard(
                group.label,
                JOB_KEYS.filter((key) => group.entities.has(key)).map((key) => group.entities.get(key))
              )
            )
          );

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
  }
}

customElements.define("bix-backup-panel", BixBackupPanel);
