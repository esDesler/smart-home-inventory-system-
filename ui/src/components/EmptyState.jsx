import React from "react";

const EmptyState = ({ title, subtitle }) => (
  <div className="empty-state">
    <div className="empty-title">{title}</div>
    {subtitle ? <div className="empty-subtitle">{subtitle}</div> : null}
  </div>
);

export default EmptyState;
