local capabilities = require "st.capabilities"
local log = require "log"

local http_client = require "http_client"

local load_child = {}

local function get_load_id(device)
  return device:get_field("load_id")
    or (device.parent_assigned_child_key and device.parent_assigned_child_key:match("^load:(.+)$"))
    or device.parent_assigned_child_key
    or device.device_network_id
end

local function is_dimmer(device)
  return device:supports_capability(capabilities.switchLevel)
end

local function build_endpoint(cfg, suffix)
  if not cfg or not cfg.host or cfg.host == "" then
    return nil
  end
  local scheme = cfg.use_https and "https" or "http"
  local port = cfg.port and cfg.port ~= "" and (":" .. cfg.port) or ""
  return string.format("%s://%s%s%s", scheme, cfg.host, port, suffix)
end

local function post_json(cfg, path, payload)
  local endpoint = build_endpoint(cfg, path)
  if not endpoint then
    return nil, "bridge endpoint not configured"
  end
  local body = http_client.encode_json(payload)
  if not body then
    return nil, "failed to encode json"
  end
  return http_client.post(endpoint, body)
end

local function send_level(cfg, device, level)
  local load_id = get_load_id(device)
  if not load_id then return end
  local res, err = post_json(cfg, string.format("/device/%s/set", load_id), { level = level })
  if err then
    log.error(string.format("Failed to set level for %s (%s): %s", device.label, load_id, err))
  else
    log.debug(string.format("Level command response for %s: %s", device.label, res or "<empty>"))
  end
end

local function send_switch(cfg, device, state)
  local load_id = get_load_id(device)
  if not load_id then return end
  local res, err = post_json(cfg, string.format("/device/%s/set", load_id), { switch = state })
  if err then
    log.error(string.format("Failed to set switch for %s (%s): %s", device.label, load_id, err))
  else
    log.debug(string.format("Switch command response for %s: %s", device.label, res or "<empty>"))
  end
end

local function parse_level(value)
  if value == nil then return 0 end
  if type(value) == "number" then return math.floor(value) end
  if type(value) == "string" then
    local num = tonumber(value)
    if num then return math.floor(num) end
    local first = value:match("(%d+)")
    if first then
      return tonumber(first) or 0
    end
  elseif type(value) == "table" then
    return parse_level(value.level or value.value)
  end
  return 0
end

local function emit_level(device, level)
  level = math.max(0, math.min(100, math.floor(level or 0)))
  if is_dimmer(device) then
    device:emit_event(capabilities.switchLevel.level(level))
  end
  if level > 0 then
    device:emit_event(capabilities.switch.switch.on())
  else
    device:emit_event(capabilities.switch.switch.off())
  end
end

local function ensure_load(device)
  if not get_load_id(device) then
    log.warn(string.format("Skipping command for non-load child %s", device.label))
    return false
  end
  return true
end

function load_child.handle_on(driver, device, command)
  if not ensure_load(device) then return end
  local parent = device:get_parent_device()
  local cfg = parent and parent:get_field("bridge_config")
  if is_dimmer(device) then
    send_level(cfg, device, 100)
    emit_level(device, 100)
  else
    send_switch(cfg, device, "on")
    emit_level(device, 100)
  end
end

function load_child.handle_off(driver, device, command)
  if not ensure_load(device) then return end
  local parent = device:get_parent_device()
  local cfg = parent and parent:get_field("bridge_config")
  if is_dimmer(device) then
    send_level(cfg, device, 0)
  else
    send_switch(cfg, device, "off")
  end
  emit_level(device, 0)
end

function load_child.handle_set_level(driver, device, command)
  if not ensure_load(device) then return end
  local target = math.floor(command.args.level or 0)
  target = math.max(0, math.min(100, target))
  local parent = device:get_parent_device()
  local cfg = parent and parent:get_field("bridge_config")
  send_level(cfg, device, target)
  emit_level(device, target)
end

function load_child.refresh(driver, device, cfg)
  if not ensure_load(device) then return end
  local load_id = get_load_id(device)
  local endpoint = build_endpoint(cfg, string.format("/load/%s/status", load_id))
  if not endpoint then return end
  local body, err = http_client.get(endpoint)
  if err then
    log.warn(string.format("Failed to refresh load %s (%s): %s", device.label, load_id, err))
    return
  end
  local decoded = http_client.decode_json(body)
  if not decoded then return end

  local level
  if type(decoded) == "table" then
    level = parse_level(decoded.level or decoded.resp or decoded.value)
  end
  emit_level(device, level)
end

function load_child.refresh_all(driver, parent_device, cfg)
  for _, child in ipairs(parent_device:get_child_list() or {}) do
    local key = child.parent_assigned_child_key
    if key and key:match("^load:") then
      load_child.refresh(driver, child, cfg)
    end
  end
end

return load_child
