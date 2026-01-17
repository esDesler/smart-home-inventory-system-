import React from "react";

import StatusPill from "./StatusPill.jsx";

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

const ItemDetail = ({ item }) => {
  if (!item) {
    return (
      <div className="card">
        <div className="card-title">Item Details</div>
        <div className="card-body muted">Select an item to view details.</div>
      </div>
    );
  }

  return (
    <div className="card">
      <div className="card-title">Item Details</div>
      <div className="detail-grid">
        <div>
          <div className="detail-label">Name</div>
          <div className="detail-value">{item.name}</div>
        </div>
        <div>
          <div className="detail-label">Status</div>
          <StatusPill status={item.latest_reading?.state || "unknown"} />
        </div>
        <div>
          <div className="detail-label">Sensor</div>
          <div className="detail-value">{item.sensor_id || "Unassigned"}</div>
        </div>
        <div>
          <div className="detail-label">Last Update</div>
          <div className="detail-value">
            {formatTimestamp(item.latest_reading?.ts)}
          </div>
        </div>
        <div>
          <div className="detail-label">Normalized Value</div>
          <div className="detail-value">
            {item.latest_reading?.normalized_value ?? "-"}
          </div>
        </div>
        <div>
          <div className="detail-label">Raw Value</div>
          <div className="detail-value">
            {item.latest_reading?.raw_value ?? "-"}
          </div>
        </div>
      </div>
    </div>
  );
};

export default ItemDetail;
