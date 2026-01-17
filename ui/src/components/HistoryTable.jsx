import React from "react";

const formatTimestamp = (value) => {
  if (!value) {
    return "";
  }
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) {
    return value;
  }
  return date.toLocaleString();
};

const HistoryTable = ({ readings }) => (
  <div className="card">
    <div className="card-title">History</div>
    <div className="table">
      <div className="table-row table-header">
        <div>Time</div>
        <div>State</div>
        <div>Value</div>
      </div>
      {readings.map((reading) => (
        <div key={`${reading.seq_id}-${reading.ts}`} className="table-row">
          <div>{formatTimestamp(reading.ts)}</div>
          <div>{reading.state}</div>
          <div>{reading.normalized_value ?? "-"}</div>
        </div>
      ))}
      {!readings.length ? (
        <div className="table-row table-empty">No readings</div>
      ) : null}
    </div>
  </div>
);

export default HistoryTable;
