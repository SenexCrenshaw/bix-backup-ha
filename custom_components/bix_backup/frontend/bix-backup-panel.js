class BixBackupPanel extends HTMLElement {
  constructor() {
    super();
    this.attachShadow({ mode: "open" });
    this._hass = undefined;
    this._panel = undefined;
    this._route = undefined;
    this._narrow = false;
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

  _bixStates() {
    if (!this._hass || !this._hass.states) {
      return [];
    }
    return Object.entries(this._hass.states)
      .map(([entityId, stateObj]) => ({ entityId, stateObj }))
      .filter(({ stateObj }) => {
        const name = String(stateObj?.attributes?.friendly_name || "").trim();
        return name.startsWith("BIX ");
      })
      .sort((left, right) => {
        const leftName = String(left.stateObj?.attributes?.friendly_name || left.entityId);
        const rightName = String(right.stateObj?.attributes?.friendly_name || right.entityId);
        return leftName.localeCompare(rightName);
      });
  }

  _summaryStates(states) {
    return states.filter(({ entityId, stateObj }) => {
      const name = String(stateObj?.attributes?.friendly_name || "");
      return entityId.startsWith("sensor.") && !name.startsWith("BIX Host ") && !name.startsWith("BIX Job ");
    });
  }

  _hostStates(states) {
    return states.filter(({ stateObj }) => String(stateObj?.attributes?.friendly_name || "").startsWith("BIX Host "));
  }

  _jobStates(states) {
    return states.filter(({ stateObj }) => String(stateObj?.attributes?.friendly_name || "").startsWith("BIX Job "));
  }

  _alertButtons(states) {
    return states.filter(({ entityId, stateObj }) => {
      const name = String(stateObj?.attributes?.friendly_name || "");
      return entityId.startsWith("button.") && name.startsWith("BIX Alert ");
    });
  }

  _jobButtons(states) {
    return states.filter(({ entityId, stateObj }) => {
      const name = String(stateObj?.attributes?.friendly_name || "");
      return entityId.startsWith("button.") && name.startsWith("BIX Job ");
    });
  }

  async _press(entityId) {
    if (!this._hass) {
      return;
    }
    await this._hass.callService("button", "press", { entity_id: entityId });
  }

  _renderRows(states, options = {}) {
    const asButtons = Boolean(options.buttons);
    if (!states.length) {
      return `<div class="empty">No items</div>`;
    }
    return states
      .map(({ entityId, stateObj }) => {
        const friendlyName = String(stateObj?.attributes?.friendly_name || entityId);
        const value = String(stateObj?.state || "unknown");
        if (asButtons) {
          const disabled = value === "unavailable" ? "disabled" : "";
          return `
            <button class="action" data-entity-id="${entityId}" ${disabled}>
              <span class="label">${friendlyName}</span>
              <span class="meta">${entityId}</span>
            </button>
          `;
        }
        return `
          <div class="row">
            <div>
              <div class="label">${friendlyName}</div>
              <div class="meta">${entityId}</div>
            </div>
            <div class="value">${value}</div>
          </div>
        `;
      })
      .join("");
  }

  _render() {
    if (!this.shadowRoot) {
      return;
    }

    const states = this._bixStates();
    const summary = this._summaryStates(states);
    const hosts = this._hostStates(states);
    const jobs = this._jobStates(states);
    const jobButtons = this._jobButtons(states);
    const alertButtons = this._alertButtons(states);

    this.shadowRoot.innerHTML = `
      <style>
        :host {
          display: block;
          min-height: 100%;
          background:
            radial-gradient(circle at top left, rgba(64, 145, 108, 0.18), transparent 30%),
            linear-gradient(180deg, #f6f7f3 0%, #eef2ea 100%);
          color: #132018;
        }
        .wrap {
          max-width: 1200px;
          margin: 0 auto;
          padding: 24px 16px 40px;
        }
        .hero {
          display: grid;
          gap: 12px;
          padding: 20px;
          border-radius: 20px;
          background: rgba(255, 255, 255, 0.82);
          border: 1px solid rgba(19, 32, 24, 0.08);
          box-shadow: 0 20px 40px rgba(19, 32, 24, 0.08);
        }
        h1, h2 {
          margin: 0;
        }
        h1 {
          font-size: 28px;
          line-height: 1.1;
        }
        .sub {
          color: #466052;
          font-size: 14px;
        }
        .grid {
          display: grid;
          gap: 16px;
          margin-top: 20px;
          grid-template-columns: repeat(auto-fit, minmax(280px, 1fr));
        }
        .card {
          background: rgba(255, 255, 255, 0.9);
          border: 1px solid rgba(19, 32, 24, 0.08);
          border-radius: 18px;
          padding: 16px;
          box-shadow: 0 16px 30px rgba(19, 32, 24, 0.06);
        }
        .section-title {
          font-size: 15px;
          text-transform: uppercase;
          letter-spacing: 0.08em;
          color: #5a6f62;
          margin-bottom: 12px;
        }
        .row {
          display: flex;
          align-items: center;
          justify-content: space-between;
          gap: 16px;
          padding: 10px 0;
          border-top: 1px solid rgba(19, 32, 24, 0.08);
        }
        .row:first-of-type {
          border-top: 0;
          padding-top: 0;
        }
        .label {
          font-weight: 600;
          line-height: 1.3;
        }
        .meta {
          color: #688071;
          font-size: 12px;
          line-height: 1.3;
        }
        .value {
          font: 600 13px/1.2 ui-monospace, SFMono-Regular, Menlo, monospace;
          padding: 6px 10px;
          border-radius: 999px;
          background: #e6efe8;
          color: #193425;
        }
        .action {
          width: 100%;
          display: grid;
          gap: 4px;
          text-align: left;
          margin: 0 0 10px;
          padding: 14px;
          border: 0;
          border-radius: 14px;
          background: linear-gradient(135deg, #224f3a 0%, #3c7a58 100%);
          color: white;
          cursor: pointer;
        }
        .action:last-of-type {
          margin-bottom: 0;
        }
        .action .meta {
          color: rgba(255, 255, 255, 0.75);
        }
        .action:disabled {
          background: #a6b8ae;
          cursor: not-allowed;
        }
        .empty {
          color: #688071;
          font-size: 14px;
        }
      </style>
      <div class="wrap">
        <div class="hero">
          <h1>${this._panel?.config?.title || "BIX Backup"}</h1>
          <div class="sub">
            Dynamic Home Assistant view for BIX entities and actions.
            ${this._narrow ? "Narrow mode enabled." : "Wide layout active."}
          </div>
        </div>
        <div class="grid">
          <section class="card">
            <div class="section-title">Summary</div>
            ${this._renderRows(summary)}
          </section>
          <section class="card">
            <div class="section-title">Job Actions</div>
            ${this._renderRows(jobButtons, { buttons: true })}
          </section>
          <section class="card">
            <div class="section-title">Alert Actions</div>
            ${this._renderRows(alertButtons, { buttons: true })}
          </section>
          <section class="card">
            <div class="section-title">Hosts</div>
            ${this._renderRows(hosts)}
          </section>
          <section class="card">
            <div class="section-title">Jobs</div>
            ${this._renderRows(jobs)}
          </section>
        </div>
      </div>
    `;

    for (const button of this.shadowRoot.querySelectorAll("button[data-entity-id]")) {
      button.addEventListener("click", () => this._press(button.dataset.entityId));
    }
  }
}

customElements.define("bix-backup-panel", BixBackupPanel);
