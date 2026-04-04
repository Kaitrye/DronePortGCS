(function () {
  const app = window.WebUI;
  const trackingMapElement = document.getElementById("tracking_map");
  const controlDroneInput = document.getElementById("control_drone_id");
  if (!app || !trackingMapElement || !controlDroneInput) {
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
    trackingHint: document.getElementById("tracking_hint")
  };

  const trackingMap = L.map("tracking_map", { zoomControl: true }).setView([55.751244, 37.618423], 14);
  const trackingLayer = L.layerGroup().addTo(trackingMap);
  let telemetryPoll = null;
  let trackingMarker = null;
  let trackingTrail = null;
  let trackingPositions = [];

  L.tileLayer("https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png", {
    maxZoom: 19,
    attribution: "&copy; OpenStreetMap contributors"
  }).addTo(trackingMap);

  function syncDroneInputs() {
    const missionDroneId = document.getElementById("drone_id")?.value || "drone-demo-1";
    if (!controlDroneInput.value) {
      controlDroneInput.value = missionDroneId;
    }
    if (!trackingState.trackingDroneInput.dataset.userEdited) {
      trackingState.trackingDroneInput.value = controlDroneInput.value || missionDroneId;
    }
  }

  function stopTelemetryPolling() {
    if (telemetryPoll) {
      clearInterval(telemetryPoll);
      telemetryPoll = null;
    }
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
    trackingPositions = [];
    if (message) {
      trackingState.trackingHint.textContent = message;
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

  async function refreshTracking(options = {}) {
    const droneId = (trackingState.trackingDroneInput.value || "").trim();
    if (!droneId) {
      trackingState.trackingHint.textContent = "Укажите ID дрона для отслеживания.";
      updateTrackingPanel(null);
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

      if (options.center && drone.last_position) {
        trackingMap.setView(
          [drone.last_position.latitude, drone.last_position.longitude],
          Math.max(trackingMap.getZoom(), 15)
        );
      }
    } catch (error) {
      trackingState.trackingHint.textContent = String(error);
      updateTrackingPanel(null);
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

  function setDroneActionOutput(text) {
    const output = document.getElementById("drone_action_output");
    if (output) {
      output.textContent = text;
    }
  }

  async function runDroneAction(action, options = {}) {
    const button = options.button;
    const label = options.label || action;
    const body = options.body || {};
    const refreshPorts = options.refreshPorts || false;

    if (button) {
      button.disabled = true;
    }

    app.setStatus("", `Выполняется: ${label}`);
    setDroneActionOutput("Выполняю запрос...");

    try {
      const { response, data } = await app.requestJson(`/api/action/${action}`, {
        body
      });

      if (!response.ok || !data.ok) {
        const errorText = data.traceback || data.error || app.safeStringify(data);
        app.setStatus("err", `Ошибка: ${label}`);
        app.setOutputMessage(errorText);
        setDroneActionOutput(errorText);
        return;
      }

      const resultText = data.result_text || app.safeStringify(data.result);
      app.setStatus("ok", `Готово: ${label}`);
      app.setOutputMessage(resultText);
      setDroneActionOutput(resultText);

      if (refreshPorts) {
        app.emit("port-state:changed", { reason: action, droneId: body.drone_id || controlDroneInput.value });
      }

      if (action === "drone-state") {
        const drone = data?.result?.payload?.drone || data?.result?.drone;
        if (drone) {
          updateTrackingPanel(drone);
        }
      }
    } catch (error) {
      const text = String(error);
      app.setStatus("err", `Ошибка сети: ${label}`);
      app.setOutputMessage(text);
      setDroneActionOutput(text);
    } finally {
      if (button) {
        button.disabled = false;
      }
    }
  }

  trackingState.trackingDroneInput.addEventListener("input", () => {
    trackingState.trackingDroneInput.dataset.userEdited = "1";
  });

  controlDroneInput.addEventListener("input", () => {
    if (!trackingState.trackingDroneInput.dataset.userEdited) {
      trackingState.trackingDroneInput.value = controlDroneInput.value;
    }
  });

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

  document.getElementById("takeoff_btn").addEventListener("click", (event) => {
    runDroneAction("takeoff", {
      label: "Взлет",
      button: event.currentTarget,
      body: { drone_id: controlDroneInput.value || "drone-demo-1" },
      refreshPorts: true
    });
  });

  document.getElementById("landing_btn").addEventListener("click", (event) => {
    runDroneAction("landing", {
      label: "Посадка",
      button: event.currentTarget,
      body: {
        drone_id: controlDroneInput.value || "drone-demo-1",
        model: document.getElementById("control_drone_model").value || "DemoCopter-X"
      },
      refreshPorts: true
    });
  });

  document.getElementById("charging_btn").addEventListener("click", (event) => {
    runDroneAction("charging", {
      label: "Зарядка",
      button: event.currentTarget,
      body: {
        drone_id: controlDroneInput.value || "drone-demo-1",
        battery: Number(document.getElementById("control_battery").value || 30)
      }
    });
  });

  document.getElementById("drone_state_btn").addEventListener("click", (event) => {
    runDroneAction("drone-state", {
      label: "Состояние дрона",
      button: event.currentTarget,
      body: { drone_id: controlDroneInput.value || "drone-demo-1" }
    });
  });

  document.getElementById("drone_snapshot_btn").addEventListener("click", (event) => {
    runDroneAction("snapshot", {
      label: "Снимок состояния",
      button: event.currentTarget,
      body: { drone_id: controlDroneInput.value || "drone-demo-1" }
    });
  });

  document.getElementById("open_tracking_btn").addEventListener("click", () => {
    if (!trackingState.trackingDroneInput.dataset.userEdited) {
      trackingState.trackingDroneInput.value = controlDroneInput.value || "drone-demo-1";
    }
    app.openPage("tracking_page");
    refreshTracking({ center: true });
  });

  app.registerPageHandler("tracking_page", () => {
    setTimeout(() => {
      trackingMap.invalidateSize();
      syncDroneInputs();
      refreshTracking();
    }, 0);
    startTelemetryPolling();
  });

  ["flight_page", "schemes_page", "security_page", "dronoport_page", "status_page", "help_page", "drone_controls_page"].forEach(
    (pageId) => {
      app.registerPageHandler(pageId, stopTelemetryPolling);
    }
  );

  syncDroneInputs();
  setTimeout(() => trackingMap.invalidateSize(), 0);
})();
