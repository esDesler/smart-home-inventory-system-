import React, { useCallback, useEffect, useMemo, useState } from "react";

import {
  ackAlert,
  fetchAlerts,
  fetchDevices,
  fetchHistory,
  fetchItem,
  fetchItems,
  getBaseUrl,
  hasUiToken,
} from "./api.js";
import AlertsPanel from "./components/AlertsPanel.jsx";
import DevicesPanel from "./components/DevicesPanel.jsx";
import HistoryTable from "./components/HistoryTable.jsx";
import ItemDetail from "./components/ItemDetail.jsx";
import ItemList from "./components/ItemList.jsx";

const POLL_INTERVAL_MS = Number(
  import.meta.env.VITE_POLL_INTERVAL_MS || 15000,
);

const cacheKey = (suffix) => `smart-inventory.${suffix}`;

const readCache = (key, fallback) => {
  try {
    const value = localStorage.getItem(key);
    if (!value) {
      return fallback;
    }
    return JSON.parse(value);
  } catch (error) {
    return fallback;
  }
};

const writeCache = (key, value) => {
  try {
    localStorage.setItem(key, JSON.stringify(value));
  } catch (error) {
    // Ignore cache write failures.
  }
};

const App = () => {
  const [view, setView] = useState("dashboard");
  const [items, setItems] = useState(() => readCache(cacheKey("items"), []));
  const [alerts, setAlerts] = useState(() =>
    readCache(cacheKey("alerts"), []),
  );
  const [devices, setDevices] = useState(() =>
    readCache(cacheKey("devices"), []),
  );
  const [selectedItemId, setSelectedItemId] = useState(
    items[0]?.id || null,
  );
  const [selectedItem, setSelectedItem] = useState(null);
  const [history, setHistory] = useState([]);
  const [error, setError] = useState(null);
  const [loading, setLoading] = useState(false);
  const [lastRefreshed, setLastRefreshed] = useState(
    readCache(cacheKey("lastRefreshed"), null),
  );

  const baseUrl = useMemo(() => getBaseUrl(), []);

  const refreshAll = useCallback(
    async (silent = false) => {
      if (!silent) {
        setLoading(true);
      }
      setError(null);
      try {
        const [itemsResp, alertsResp, devicesResp] = await Promise.all([
          fetchItems(),
          fetchAlerts(),
          fetchDevices(),
        ]);
        const newItems = itemsResp.items || [];
        const newAlerts = alertsResp.alerts || [];
        const newDevices = devicesResp.devices || [];
        setItems(newItems);
        setAlerts(newAlerts);
        setDevices(newDevices);
        writeCache(cacheKey("items"), newItems);
        writeCache(cacheKey("alerts"), newAlerts);
        writeCache(cacheKey("devices"), newDevices);
        const now = new Date().toISOString();
        setLastRefreshed(now);
        writeCache(cacheKey("lastRefreshed"), now);
        if (!selectedItemId && newItems.length) {
          setSelectedItemId(newItems[0].id);
        }
      } catch (err) {
        setError(err.message || "Failed to refresh data");
      } finally {
        if (!silent) {
          setLoading(false);
        }
      }
    },
    [selectedItemId],
  );

  const refreshItem = useCallback(async () => {
    if (!selectedItemId) {
      setSelectedItem(null);
      setHistory([]);
      return;
    }
    try {
      const [itemResp, historyResp] = await Promise.all([
        fetchItem(selectedItemId),
        fetchHistory(selectedItemId),
      ]);
      setSelectedItem(itemResp);
      setHistory(historyResp.readings || []);
    } catch (err) {
      setError(err.message || "Failed to load item details");
    }
  }, [selectedItemId]);

  const handleAck = useCallback(async (alertId) => {
    try {
      await ackAlert(alertId);
      await refreshAll(true);
    } catch (err) {
      setError(err.message || "Failed to acknowledge alert");
    }
  }, [refreshAll]);

  useEffect(() => {
    refreshAll();
    const interval = setInterval(() => refreshAll(true), POLL_INTERVAL_MS);
    return () => clearInterval(interval);
  }, [refreshAll]);

  useEffect(() => {
    refreshItem();
  }, [refreshItem]);

  const headerMeta = `${baseUrl} · ${
    hasUiToken() ? "auth enabled" : "auth disabled"
  }`;

  return (
    <div className="app">
      <header className="app-header">
        <div>
          <div className="app-title">Smart Inventory</div>
          <div className="app-subtitle">{headerMeta}</div>
        </div>
        <div className="header-actions">
          <div className="last-refresh">
            Last refresh: {lastRefreshed ? new Date(lastRefreshed).toLocaleTimeString() : "Never"}
          </div>
          <button type="button" className="button" onClick={() => refreshAll()}>
            Refresh
          </button>
        </div>
      </header>

      {error ? <div className="error-banner">{error}</div> : null}

      <nav className="nav">
        <button
          type="button"
          className={view === "dashboard" ? "nav-active" : ""}
          onClick={() => setView("dashboard")}
        >
          Dashboard
        </button>
        <button
          type="button"
          className={view === "alerts" ? "nav-active" : ""}
          onClick={() => setView("alerts")}
        >
          Alerts
        </button>
        <button
          type="button"
          className={view === "devices" ? "nav-active" : ""}
          onClick={() => setView("devices")}
        >
          Devices
        </button>
      </nav>

      <main className="content">
        {view === "dashboard" ? (
          <div className="grid">
            <ItemList
              items={items}
              selectedId={selectedItemId}
              onSelect={setSelectedItemId}
            />
            <div className="stack">
              <ItemDetail item={selectedItem} />
              <HistoryTable readings={history} />
            </div>
          </div>
        ) : null}
        {view === "alerts" ? (
          <AlertsPanel alerts={alerts} onAck={handleAck} />
        ) : null}
        {view === "devices" ? <DevicesPanel devices={devices} /> : null}
      </main>

      {loading ? <div className="loading-overlay">Loading...</div> : null}
    </div>
  );
};

export default App;
