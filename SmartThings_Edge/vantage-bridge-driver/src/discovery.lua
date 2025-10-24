local capabilities = require "st.capabilities"
local log = require "log"

local http_client = require "http_client"

local discovery = {}

local function build_endpoint(cfg, path)
  if not cfg or not cfg.host or cfg.host == "" then
    return nil
  end
  local scheme = cfg.use_https and "https" or "http"
  local port = (cfg.port and cfg.port ~= "" and cfg.port ~= 80) and (":" .. cfg.port) or ""
  return string.format("%s://%s%s%s", scheme, cfg.host, port, path)
end

local function fetch_config(cfg)
  local endpoint = build_endpoint(cfg, "/config")
  if not endpoint then
    return nil, "Bridge IP/port not configured"
  end
  local body, err = http_client.get(endpoint)
  if err then
    return nil, err
  end
  local decoded = http_client.decode_json(body)
  if not decoded then
    return nil, "Failed to decode /config response"
  end
  return decoded, nil
end

local function ensure_child(driver, parent_device, key, metadata)
  local existing = parent_device:get_child_by_parent_assigned_key(key)
  if existing then
    if metadata.label and existing.label ~= metadata.label then
      existing:try_update_metadata({ label = metadata.label })
    end
    return existing, false
  end

  metadata.parent_device_id = parent_device.id
  metadata.parent_assigned_child_key = key
  metadata.vendor_provided_label = metadata.label

  local success, err = driver:try_create_device(metadata)
  if not success then
    log.error(string.format("Failed to create child %s: %s", key, err or "unknown error"))
    return nil, false
  end
  log.info(string.format("Created child device '%s' (%s)", metadata.label, key))
  return parent_device:get_child_by_parent_assigned_key(key), true
end

local function discover_loads(driver, parent_device, cfg, parsed_config)
  local loads_by_id = {}

  for _, room in ipairs(parsed_config.rooms or {}) do
    local room_name = room.name or "Room"
    for _, load in ipairs(room.loads or {}) do
      local load_id = load.id
      if load_id then
        loads_by_id[load_id] = loads_by_id[load_id] or {
          id = load_id,
          name = load.name or ("Load " .. load_id),
          type = load.type or "dimmer",
          room = room_name,
        }
      end
    end
  end

  local seen = {}
  for _, load in pairs(loads_by_id) do
    local profile = load.type == "dimmer" and "vantageBridge.loadDimmer" or "vantageBridge.loadSwitch"
    local label = string.format("%s - %s", load.room, load.name)
    local key = string.format("load:%s", load.id)
    seen[key] = true

    local child = ensure_child(driver, parent_device, key, {
      type = "EDGE_CHILD",
      label = label,
      profile = profile,
      manufacturer = "Vantage",
      model = load.type == "dimmer" and "LoadDimmer" or "LoadSwitch",
    })

    if child then
      child:set_field("load_id", load.id, { persist = true })
      child:set_field("load_type", load.type or "dimmer", { persist = true })
      child:set_field("room_name", load.room, { persist = true })
    end
  end

  for _, child in ipairs(parent_device:get_child_list() or {}) do
    local key = child.parent_assigned_child_key
    if key and key:match("^load:") and not seen[key] then
      log.info(string.format("Removing orphan load child %s (%s)", child.label, key))
      driver:try_delete_device(child.id)
    end
  end
end

local function merge_station_buttons(accum, station_entry, default_room)
  local station_num = tonumber(station_entry.station)
  if not station_num then return accum end

  local existing = accum[station_num]
  if not existing then
    existing = {
      station = station_num,
      buttons = {},
      room = default_room,
    }
    accum[station_num] = existing
  end

  for _, btn in ipairs(station_entry.buttons or {}) do
    local num = tonumber(btn.number)
    if num and num >= 1 and num <= 8 then
      existing.buttons[num] = btn.name or ("Button " .. num)
    end
  end

  if default_room then
    existing.room = default_room
  end

  return accum
end

local function discover_station_buttons(driver, parent_device, cfg, parsed_config)
  local stations = {}

  for _, room in ipairs(parsed_config.rooms or {}) do
    if room.station then
      stations = merge_station_buttons(stations, room, room.name)
    end
    for _, station in ipairs(room.stations or {}) do
      stations = merge_station_buttons(stations, station, room.name)
    end
  end

  local seen = {}
  for station_num, info in pairs(stations) do
    local key = string.format("station:%s", station_num)
    seen[key] = true
    local label = string.format("%s - Station V%s", info.room or "Station", station_num)
    local child = ensure_child(driver, parent_device, key, {
      type = "EDGE_CHILD",
      label = label,
      profile = "vantageBridge.stationButtons",
      manufacturer = "Vantage",
      model = "StationButtons",
    })

    if child then
      local buttons = info.buttons
      local count = 0
      for btn_num = 1, 8 do
        if buttons[btn_num] then
          count = count + 1
        end
      end
      if count == 0 then count = 8 end

      child:set_field("station_number", station_num, { persist = true })
      child:set_field("button_labels", buttons, { persist = true })

      child:emit_event(capabilities.button.numberOfButtons(count))

      for btn_num = 1, 8 do
        local component_id = string.format("button%d", btn_num)
        local component = child.profile.components[component_id]
        if component then
          child:emit_component_event(component, capabilities.button.supportedButtonValues({ "pushed", "held" }, { visibility = { displayed = false } }))
          child:emit_component_event(component, capabilities.switch.switch.off())
        end
      end
    end
  end

  for _, child in ipairs(parent_device:get_child_list() or {}) do
    local key = child.parent_assigned_child_key
    if key and key:match("^station:") and not seen[key] then
      log.info(string.format("Removing orphan station child %s (%s)", child.label, key))
      driver:try_delete_device(child.id)
    end
  end
end

function discovery.run(driver, parent_device, cfg)
  local config, err = fetch_config(cfg)
  if err then
    log.warn(string.format("Bridge discovery failed: %s", err))
    return
  end

  discover_loads(driver, parent_device, cfg, config)
  discover_station_buttons(driver, parent_device, cfg, config)
end

return discovery
