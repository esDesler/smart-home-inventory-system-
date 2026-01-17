import React from "react";

import EmptyState from "./EmptyState.jsx";

const formatTimestamp = (value) => {
  if (!value) {
    return "Never";
  }
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) {
    return value;
  }
  return date.toLocaleString();
};

const DevicesPanel = ({ devices }) => (
  <div className="card">
    <div className="card-title">Devices</div>
    {!devices.length ? (
      <EmptyState
        title="No devices registered"
        subtitle="Send readings from a device to populate this list."
      />
    ) : (
      <div className="table">
        <div className="table-row table-header">
          <div>Device ID</div>
          <div>Firmware</div>
          <div>Last Seen</div>
        </div>
        {devices.map((device) => (
          <div key={device.id} className="table-row">
            <div>{device.id}</div>
            <div>{device.firmware || "-"}</div>
            <div>{formatTimestamp(device.last_seen)}</div>
          </div>
        ))}
      </div>
    )}
  </div>
);

export default DevicesPanel;
