import React from "react";

import EmptyState from "./EmptyState.jsx";

const formatTimestamp = (value) => {
  if (!value) {
    return "Unknown";
  }
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) {
    return value;
  }
  return date.toLocaleString();
};

const AlertsPanel = ({ alerts, onAck }) => (
  <div className="card">
    <div className="card-title">Active Alerts</div>
    {!alerts.length ? (
      <EmptyState title="No active alerts" subtitle="Everything looks good." />
    ) : (
      <div className="list">
        {alerts.map((alert) => (
          <div key={alert.id} className="list-row alert-row">
            <div className="list-main">
              <div className="list-title">{alert.message || "Alert"}</div>
              <div className="list-subtitle">
                Item: {alert.name || "Unassigned"} · Triggered{" "}
                {formatTimestamp(alert.created_at)}
              </div>
            </div>
            <div className="list-meta">
              <button
                type="button"
                className="button button-secondary"
                onClick={() => onAck(alert.id)}
              >
                Acknowledge
              </button>
            </div>
          </div>
        ))}
      </div>
    )}
  </div>
);

export default AlertsPanel;
