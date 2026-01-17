import React from "react";

const statusClass = (status) => {
  switch (status) {
    case "ok":
      return "status-pill status-ok";
    case "low":
      return "status-pill status-low";
    case "out":
      return "status-pill status-out";
    case "unknown":
    default:
      return "status-pill status-unknown";
  }
};

const formatStatus = (status) => {
  if (!status) {
    return "unknown";
  }
  return status;
};

const StatusPill = ({ status }) => (
  <span className={statusClass(status)}>{formatStatus(status)}</span>
);

export default StatusPill;
