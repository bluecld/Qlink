local capabilities = require "st.capabilities"
local log = require "log"

local http_client = require "http_client"
local load_child = require "devices.load_child"

local scene_child = {}

local function parse_station(device)
  local stored = device:get_field("station_number")
  if stored then
    return stored
  end
  local key = device.parent_assigned_child_key or device.device_network_id or ""
  local station = key:match("^station:(%d+)$")
  return station or key
end

local function component_to_button(device, component, fallback_button)
  if component and component ~= "main" then
    local num = component:match("button(%d+)")
    if num then
      return tonumber(num)
    end
  end
  if fallback_button then
    local n = tonumber(fallback_button)
    if n then return n end
  end
  return 1
end

local function build_base_endpoint(cfg, path)
  if not cfg or not cfg.host or cfg.host == "" then
    return nil
  end
  local scheme = cfg.use_https and "https" or "http"
  local port = cfg.port and cfg.port ~= "" and (":" .. cfg.port) or ""
  return string.format("%s://%s%s%s", scheme, cfg.host, port, path)
end

local function build_button_endpoint(cfg, station, button)
  return build_base_endpoint(cfg, string.format("/button/%s/%s", station, button))
end

local function build_led_endpoint(cfg)
  return build_base_endpoint(cfg, "/api/leds")
end

local function set_switch_state(device, button, state)
  local component_id = string.format("button%d", button)
  local component = device.profile.components[component_id]
  if not component then return end
  if state == "on" or state == "blink" then
    device:emit_component_event(component, capabilities.switch.switch.on())
    device:set_field("button_blink_" .. button, state == "blink", { persist = false })
  else
    device:emit_component_event(component, capabilities.switch.switch.off())
    device:set_field("button_blink_" .. button, false, { persist = false })
  end
end

local function emit_button_event(device, button, event_name)
  local component_id = string.format("button%d", button)
  local component = device.profile.components[component_id] or device.profile.components["main"]
  local capability = capabilities.button.button[event_name]
  if capability then
    device:emit_component_event(component, capability())
  else
    log.warn(string.format("Unsupported button event %s", event_name))
  end
end

local function trigger_button(device, event_name, button_number)
  local parent = device:get_parent_device()
  local cfg = parent and parent:get_field("bridge_config")
  if not cfg then
    log.warn("Bridge configuration missing; cannot trigger button")
    return
  end

  local station = parse_station(device)
  local button = tonumber(button_number) or 1
  if button < 1 then button = 1 end
  if button > 8 then button = 8 end

  local endpoint = build_button_endpoint(cfg, station, button)
  if not endpoint then
    log.warn("Bridge endpoint missing; cannot trigger station button")
    return
  end

  local res, err = http_client.post(endpoint, "{}")
  if err then
    log.error(string.format("Failed to trigger station %s button %s: %s", station, button, err))
    return
  end
  log.debug(string.format("Station %s button %s response: %s", station, button, res or "<empty>"))
  emit_button_event(device, button, event_name)
end

local function handle_button_command(device, command, event_name)
  local args = command and command.args or {}
  local component = command and command.component
  local button = args.button or args.buttonNumber or args.button_id
  if not button then
    button = component_to_button(device, component, nil)
  end
  trigger_button(device, event_name, button)
end

function scene_child.handle_push(driver, device, command)
  handle_button_command(device, command, "pushed")
end

function scene_child.handle_hold(driver, device, command)
  handle_button_command(device, command, "held")
end

function scene_child.handle_switch_on(driver, device, command)
  handle_button_command(device, command, "pushed")
end

function scene_child.handle_switch_off(driver, device, command)
  handle_button_command(device, command, "pushed")
end

local function refresh_station_leds(device, station_payload)
  if type(station_payload) ~= "table" then return end
  local button_states = station_payload.button_states or station_payload.buttons or {}
  for btn = 1, 8 do
    local state = button_states[tostring(btn)] or button_states[btn] or "off"
    set_switch_state(device, btn, state)
  end
end

local function refresh_related_loads(driver, parent_device, cfg, loads)
  if type(loads) ~= "table" then return end
  for load_id, _ in pairs(loads) do
    local key = string.format("load:%s", load_id)
    local load_device = parent_device:get_child_by_parent_assigned_key(key)
    if load_device then
      load_child.refresh(driver, load_device, cfg)
    end
  end
end

function scene_child.refresh_all(driver, parent_device, cfg)
  local leds_endpoint = build_led_endpoint(cfg)
  if not leds_endpoint then return end
  local body, err = http_client.get(leds_endpoint)
  if err then
    log.debug(string.format("LED refresh failed: %s", err))
    return
  end
  local decoded = http_client.decode_json(body)
  if not decoded then return end
  local stations = decoded.stations or {}

  for _, child in ipairs(parent_device:get_child_list() or {}) do
    local key = child.parent_assigned_child_key
    if key and key:match("^station:") then
      local station_num = tostring(child:get_field("station_number") or key:match("^station:(%d+)$") or "")
      local payload = stations["V" .. station_num]
      refresh_station_leds(child, payload)
      if payload and payload.loads then
        refresh_related_loads(driver, parent_device, cfg, payload.loads)
      end
    end
  end
end

return scene_child
