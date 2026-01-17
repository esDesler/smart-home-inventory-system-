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

const ItemList = ({ items, selectedId, onSelect }) => (
  <div className="card">
    <div className="card-title">Items</div>
    <div className="list">
      {items.map((item) => (
        <button
          type="button"
          key={item.id}
          className={`list-row ${selectedId === item.id ? "selected" : ""}`}
          onClick={() => onSelect(item.id)}
        >
          <div className="list-main">
            <div className="list-title">{item.name}</div>
            <div className="list-subtitle">
              Last update: {formatTimestamp(item.last_update)}
            </div>
          </div>
          <div className="list-meta">
            <StatusPill status={item.status} />
          </div>
        </button>
      ))}
    </div>
  </div>
);

export default ItemList;
