(function () {
  const app = window.WebUI;
  const trackingMapElement = document.getElementById("tracking_map");
  if (!app || !trackingMapElement) {
    return;
  }

  const trackingState = {
    trackingDroneInput: document.getElementById("tracking_drone_id"),
    trackingStatusValue: document.getElementById("tracking_status_value"),
    trackingBatteryValue: document.getElementById("tracking_battery_value"),
    trackingLatValue: document.getElementById("tracking_lat_value"),
    trackingLonValue: document.getElementById("tracking_lon_value"),
    trackingAltValue: document.getElementById("tracking_alt_value"),
    trackingUpdatedValue: document.getElementById("tracking_updated_value"),
    trackingHint: document.getElementById("tracking_hint"),
    sitlMessageCount: document.getElementById("sitl_message_count"),
    sitlLastTopic: document.getElementById("sitl_last_topic"),
    sitlLastDrone: document.getElementById("sitl_last_drone"),
    sitlLastSeen: document.getElementById("sitl_last_seen"),
    sitlHint: document.getElementById("sitl_hint"),
    sitlMessagesBox: document.getElementById("sitl_messages_box")
  };

  const trackingMap = L.map("tracking_map", { zoomControl: true }).setView([55.751244, 37.618423], 14);
  const trackingLayer = L.layerGroup().addTo(trackingMap);
  const missionDroneInput = document.getElementById("drone_id");
  let telemetryPoll = null;
  let missionWatchPoll = null;
  let missionWatchDroneId = "";
  let trackingMarker = null;
  let trackingTrail = null;
  let trackingTrailSegments = [];
  const MAX_TRACK_SEGMENTS = 24;
  let trackingPositions = [];
  let lastAcceptedPositionTsMs = null;
  let missionFlightObserved = false;
  let landingRefreshSent = false;

  const MAX_TRACK_POINT_DISTANCE_M = 180;
  const MAX_TRACK_SPEED_MPS = 40;
  const DEFAULT_TRACK_DT_S = 2;
  const MIN_TRACK_POINT_DELTA_M = 0.8;

  L.tileLayer("https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png", {
    maxZoom: 19,
    attribution: "&copy; OpenStreetMap contributors"
  }).addTo(trackingMap);

  function syncDroneInputs() {
    const missionDroneId = (missionDroneInput?.value || "").trim();
    if (!trackingState.trackingDroneInput.dataset.userEdited) {
      trackingState.trackingDroneInput.value = missionDroneId;
    }
  }

  function stopTelemetryPolling() {
    if (telemetryPoll) {
      clearInterval(telemetryPoll);
      telemetryPoll = null;
    }
  }

  function stopMissionWatch() {
    if (missionWatchPoll) {
      clearInterval(missionWatchPoll);
      missionWatchPoll = null;
    }
    missionWatchDroneId = "";
  }

  function resetTrackingMap(message) {
    if (trackingMarker) {
      trackingLayer.removeLayer(trackingMarker);
      trackingMarker = null;
    }
    if (trackingTrail) {
      trackingLayer.removeLayer(trackingTrail);
      trackingTrail = null;
    }
    trackingTrailSegments.forEach((segment) => {
      trackingLayer.removeLayer(segment);
    });
    trackingTrailSegments = [];
    trackingPositions = [];
    lastAcceptedPositionTsMs = null;
    if (message) {
      trackingState.trackingHint.textContent = message;
    }
  }

  function parseTimestampMs(value) {
    if (!value) {
      return null;
    }
    const ts = Date.parse(value);
    return Number.isFinite(ts) ? ts : null;
  }

  function distanceMeters(a, b) {
    const toRad = (deg) => (deg * Math.PI) / 180;
    const lat1 = toRad(a[0]);
    const lat2 = toRad(b[0]);
    const dLat = lat2 - lat1;
    const dLon = toRad(b[1] - a[1]);
    const sinDLat = Math.sin(dLat / 2);
    const sinDLon = Math.sin(dLon / 2);
    const h = sinDLat * sinDLat + Math.cos(lat1) * Math.cos(lat2) * sinDLon * sinDLon;
    return 2 * 6371000 * Math.asin(Math.min(1, Math.sqrt(h)));
  }

  function evaluateTrackPoint(nextLatLng, nextTsMs) {
    const last = trackingPositions[trackingPositions.length - 1];
    if (!last) {
      return "accept";
    }

    const dist = distanceMeters(last, nextLatLng);
    if (dist < MIN_TRACK_POINT_DELTA_M) {
      return "skip";
    }

    if (dist > MAX_TRACK_POINT_DISTANCE_M) {
      return "reset";
    }

    if (lastAcceptedPositionTsMs != null && nextTsMs != null) {
      if (nextTsMs < lastAcceptedPositionTsMs) {
        return "skip";
      }
      const dtS = Math.max((nextTsMs - lastAcceptedPositionTsMs) / 1000, 0.2);
      if (dist / dtS > MAX_TRACK_SPEED_MPS) {
        return "skip";
      }
      return "accept";
    }

    if (dist / DEFAULT_TRACK_DT_S > MAX_TRACK_SPEED_MPS) {
      return "skip";
    }

    return "accept";
  }

  function archiveCurrentTrailSegment() {
    if (trackingPositions.length < 2) {
      return;
    }
    const segment = L.polyline(trackingPositions.slice(), {
      color: "#58a6ff",
      weight: 2,
      opacity: 0.35
    }).addTo(trackingLayer);
    trackingTrailSegments.push(segment);
    if (trackingTrailSegments.length > MAX_TRACK_SEGMENTS) {
      const oldest = trackingTrailSegments.shift();
      if (oldest) {
        trackingLayer.removeLayer(oldest);
      }
    }
  }

  function updateTrackingPanel(drone) {
    const position = drone?.last_position || {};
    trackingState.trackingStatusValue.textContent = drone?.status || "нет данных";
    trackingState.trackingBatteryValue.textContent = drone?.battery != null ? `${drone.battery}%` : "-";
    trackingState.trackingLatValue.textContent = position.latitude != null ? Number(position.latitude).toFixed(6) : "-";
    trackingState.trackingLonValue.textContent = position.longitude != null ? Number(position.longitude).toFixed(6) : "-";
    trackingState.trackingAltValue.textContent = position.altitude != null ? `${Number(position.altitude).toFixed(1)} м` : "-";
    trackingState.trackingUpdatedValue.textContent = drone?.updated_at || drone?.connected_at || "-";
  }

  function updateTrackingMap(drone) {
    const position = drone?.last_position;
    if (!position || position.latitude == null || position.longitude == null) {
      trackingState.trackingHint.textContent =
        "Телеметрия еще не содержит координат. Маркер появится после первого ответа от дрона.";
      return;
    }

    const latLng = [position.latitude, position.longitude];
    const tsMs =
      parseTimestampMs(drone?.source_timestamp) ||
      parseTimestampMs(drone?.updated_at) ||
      parseTimestampMs(drone?.connected_at);

    const trackDecision = evaluateTrackPoint(latLng, tsMs);
    if (trackDecision === "skip") {
      return;
    }

    if (trackDecision === "reset") {
      archiveCurrentTrailSegment();
      trackingPositions = [latLng];
      lastAcceptedPositionTsMs = tsMs || Date.now();
    }

    trackingState.trackingHint.textContent =
      "Карта показывает последнюю сохраненную позицию дрона и накопленный трек за текущую сессию.";

    if (!trackingMarker) {
      trackingMarker = L.marker(latLng).addTo(trackingLayer);
      trackingMarker.bindTooltip("Дрон", { direction: "top" });
    } else {
      trackingMarker.setLatLng(latLng);
    }

    const last = trackingPositions[trackingPositions.length - 1];
    if (!last || last[0] !== latLng[0] || last[1] !== latLng[1]) {
      trackingPositions.push(latLng);
      lastAcceptedPositionTsMs = tsMs || Date.now();
    }

    if (trackingTrail) {
      trackingLayer.removeLayer(trackingTrail);
    }
    trackingTrail = L.polyline(trackingPositions, {
      color: "#58a6ff",
      weight: 3,
      opacity: 0.88
    }).addTo(trackingLayer);
  }

  function summarizeSitlMessage(entry) {
    const payload = entry?.message?.payload || entry?.message || {};
    const droneId =
      payload?.drone_id ||
      payload?.data?.drone_id ||
      payload?.payload?.drone_id ||
      payload?.target?.drone_id ||
      "-";
    return {
      topic: entry?.topic || "-",
      droneId,
      receivedAt: entry?.received_at || "-",
      raw: entry?.message || {}
    };
  }

  function updateSitlPanel(snapshot) {
    const messages = Array.isArray(snapshot?.observed_sitl_messages) ? snapshot.observed_sitl_messages : [];
    const lastEntry = messages[messages.length - 1];
    const last = lastEntry ? summarizeSitlMessage(lastEntry) : null;

    trackingState.sitlMessageCount.textContent = String(messages.length);
    trackingState.sitlLastTopic.textContent = last?.topic || "-";
    trackingState.sitlLastDrone.textContent = last?.droneId || "-";
    trackingState.sitlLastSeen.textContent = last?.receivedAt || "-";

    if (!messages.length) {
      trackingState.sitlHint.textContent =
        "Пока ничего не замечено. После отправки HOME, команд или telemetry-запросов панель обновится.";
      trackingState.sitlMessagesBox.textContent = "Нет сообщений SITL";
      return;
    }

    trackingState.sitlHint.textContent =
      "Панель показывает последние сообщения по SITL-топикам, которые наблюдает demo-клиент.";
    const lines = messages.slice(-6).reverse().map((entry) => {
      const item = summarizeSitlMessage(entry);
      return `[${item.receivedAt}] ${item.topic} drone=${item.droneId}\n${JSON.stringify(item.raw, null, 2)}`;
    });
    trackingState.sitlMessagesBox.textContent = lines.join("\n\n");
  }

  async function refreshSitlPanel(droneId) {
    try {
      const { response, data } = await app.requestJson("/api/action/snapshot", {
        body: {
          drone_id:
            droneId ||
            (trackingState.trackingDroneInput.value || "").trim() ||
            window.defaultDemoDroneId ||
            "1"
        }
      });

      if (!response.ok || !data.ok) {
        trackingState.sitlHint.textContent = data.error || "Не удалось получить snapshot SITL.";
        return;
      }

      updateSitlPanel(data.result || {});
    } catch (error) {
      trackingState.sitlHint.textContent = String(error);
    }
  }

  function updatePortRefreshState(drone, droneId) {
    const position = drone?.last_position || {};
    const altitude = Number(position.altitude);
    const hasAltitude = Number.isFinite(altitude);
    const isAirborne = (hasAltitude && altitude > 1) || drone?.status === "busy";

    if (isAirborne) {
      missionFlightObserved = true;
      landingRefreshSent = false;
      return;
    }

    if (!missionFlightObserved || landingRefreshSent) {
      return;
    }

    const isLanded = !hasAltitude || altitude <= 1;
    if (!isLanded) {
      return;
    }

    landingRefreshSent = true;
    missionFlightObserved = false;
    app.emit("port-state:changed", {
      reason: "mission-landed",
      droneId: droneId || trackingState.trackingDroneInput.value
    });
    stopMissionWatch();
  }

  async function pollMissionWatchDrone() {
    if (!missionWatchDroneId) {
      stopMissionWatch();
      return;
    }

    try {
      const { response, data } = await app.requestJson("/api/action/drone-state", {
        body: { drone_id: missionWatchDroneId }
      });

      if (!response.ok || !data.ok) {
        return;
      }

      const drone = data?.result?.payload?.drone || data?.result?.drone;
      if (!drone) {
        return;
      }

      updatePortRefreshState(drone, missionWatchDroneId);
    } catch (error) {
      // Background watcher should stay silent; UI errors belong to explicit user actions.
    }
  }

  function startMissionWatch(droneId) {
    const normalizedDroneId = String(droneId || "").trim();
    if (!normalizedDroneId) {
      return;
    }

    stopMissionWatch();
    missionWatchDroneId = normalizedDroneId;
    missionFlightObserved = false;
    landingRefreshSent = false;
    pollMissionWatchDrone();
    missionWatchPoll = setInterval(pollMissionWatchDrone, 2000);
  }

  async function refreshTracking(options = {}) {
    const droneId = (trackingState.trackingDroneInput.value || "").trim();
    if (!droneId) {
      trackingState.trackingHint.textContent = "Укажите ID дрона для отслеживания.";
      updateTrackingPanel(null);
      updateSitlPanel({});
      return;
    }

    try {
      const { response, data } = await app.requestJson("/api/action/drone-state", {
        body: { drone_id: droneId }
      });

      if (!response.ok || !data.ok) {
        trackingState.trackingHint.textContent = data.error || "Не удалось получить состояние дрона.";
        updateTrackingPanel(null);
        return;
      }

      const drone = data?.result?.payload?.drone || data?.result?.drone;
      if (!drone) {
        resetTrackingMap(
          `DroneStore пока не знает дрон "${droneId}". Проверьте ID и убедитесь, что миссия уже назначена и запущена.`
        );
        updateTrackingPanel(null);
        return;
      }

      updateTrackingPanel(drone);
      updateTrackingMap(drone);
      updatePortRefreshState(drone, droneId);
      refreshSitlPanel(droneId);

      if (options.center && drone.last_position) {
        trackingMap.setView(
          [drone.last_position.latitude, drone.last_position.longitude],
          Math.max(trackingMap.getZoom(), 15)
        );
      }
    } catch (error) {
      trackingState.trackingHint.textContent = String(error);
      updateTrackingPanel(null);
      refreshSitlPanel(droneId);
    }
  }

  function startTelemetryPolling() {
    stopTelemetryPolling();
    telemetryPoll = setInterval(() => {
      if (app.isPageActive("tracking_page")) {
        refreshTracking();
      }
    }, 2000);
  }

  trackingState.trackingDroneInput.addEventListener("input", () => {
    trackingState.trackingDroneInput.dataset.userEdited = "1";
  });

  if (missionDroneInput) {
    missionDroneInput.addEventListener("input", syncDroneInputs);
  }

  document.getElementById("tracking_refresh_btn").addEventListener("click", () => {
    refreshTracking({ center: true });
  });

  document.getElementById("tracking_center_btn").addEventListener("click", () => {
    const last = trackingPositions[trackingPositions.length - 1];
    if (last) {
      trackingMap.setView(last, Math.max(trackingMap.getZoom(), 15));
    } else {
      refreshTracking({ center: true });
    }
  });

  app.registerPageHandler("tracking_page", () => {
    setTimeout(() => {
      trackingMap.invalidateSize();
      syncDroneInputs();
      refreshTracking();
    }, 0);
    startTelemetryPolling();
  });

  ["flight_page", "schemes_page", "security_page", "dronoport_page", "status_page", "help_page"].forEach(
    (pageId) => {
      app.registerPageHandler(pageId, stopTelemetryPolling);
    }
  );

  app.on("mission-flight-watch:start", (payload) => {
    startMissionWatch(payload?.droneId || missionDroneInput?.value || trackingState.trackingDroneInput.value);
  });

  syncDroneInputs();
  setTimeout(() => trackingMap.invalidateSize(), 0);
})();
