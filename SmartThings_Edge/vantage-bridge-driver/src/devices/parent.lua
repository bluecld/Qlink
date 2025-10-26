local capabilities = require "st.capabilities"
local log = require "log"

local load_child = require "devices.load_child"
local scene_child = require "devices.scene_child"
local discovery = require "discovery"

local PARENT_DEVICE_FIELD = "is_parent_device"
local BRIDGE_CONFIG_FIELD = "bridge_config"
local LAST_DISCOVERY_HASH = "last_discovery_hash"
local REFRESH_TIMER = "refresh_timer"

local REFRESH_SECONDS = 120
local DISCOVERY_THROTTLE_SECONDS = 600

local parent = {}

local function is_parent(device)
  return device.parent_assigned_child_key == nil
end

local function ensure_parent_mark(device)
  if is_parent(device) then
    device:set_field(PARENT_DEVICE_FIELD, true, { persist = true })
  end
end

local function get_bridge_config(device)
  return device:get_field(BRIDGE_CONFIG_FIELD) or {
    host = device.preferences and device.preferences.bridgeIp or "",
    port = device.preferences and device.preferences.bridgePort or "8000",
    use_https = device.preferences and device.preferences.bridgeUseHttps,
  }
end

local function set_bridge_config(device, cfg)
  device:set_field(BRIDGE_CONFIG_FIELD, cfg, { persist = true })
end

local function calc_config_hash(cfg)
  if not cfg then return nil end
  return string.format("%s:%s:%s", cfg.host or "", cfg.port or "", tostring(cfg.use_https))
end

local function schedule_refresh(driver, device)
  if not is_parent(device) then return end
  local existing = device:get_field(REFRESH_TIMER)
  if existing then
    device.thread:cancel_timer(existing)
  end
  local timer = device.thread:call_on_schedule(REFRESH_SECONDS, function()
    parent.handle_refresh(driver, device)
  end)
  device:set_field(REFRESH_TIMER, timer)
end

local function run_discovery(driver, device, force)
  if not is_parent(device) then return end
  local cfg = get_bridge_config(device)
  if not cfg.host or cfg.host == "" then
    log.warn("Bridge host not configured; discovery skipped")
    return
  end

  local last_hash = device:get_field(LAST_DISCOVERY_HASH)
  local current_hash = calc_config_hash(cfg)
  local last_time = device:get_field(LAST_DISCOVERY_HASH .. "_ts") or 0
  local now = os.time()

  if not force then
    if last_hash == current_hash and (now - last_time) < DISCOVERY_THROTTLE_SECONDS then
      return
    end
  end

  discovery.run(driver, device, cfg)
  device:set_field(LAST_DISCOVERY_HASH, current_hash, { persist = true })
  device:set_field(LAST_DISCOVERY_HASH .. "_ts", now, { persist = false })
end

function parent.device_added(driver, device)
  if not is_parent(device) then
    return
  end

  ensure_parent_mark(device)
  device:online()
  log.info(string.format("Parent bridge device added (%s)", device.label))
  run_discovery(driver, device, true)
  schedule_refresh(driver, device)
end

function parent.device_init(driver, device)
  if not is_parent(device) then
    return
  end

  ensure_parent_mark(device)
  device:online()
  schedule_refresh(driver, device)
end

function parent.device_info_changed(driver, device, event, args)
  if not is_parent(device) then
    return
  end

  local old = args and args.old_stored_device or {}
  local old_prefs = old.preferences or {}
  local new_prefs = device.preferences or {}

  if old_prefs.bridgeIp ~= new_prefs.bridgeIp or
     old_prefs.bridgePort ~= new_prefs.bridgePort or
     old_prefs.bridgeUseHttps ~= new_prefs.bridgeUseHttps then
    local cfg = {
      host = new_prefs.bridgeIp,
      port = new_prefs.bridgePort,
      use_https = new_prefs.bridgeUseHttps,
    }
    set_bridge_config(device, cfg)
    device:set_field(LAST_DISCOVERY_HASH, nil, { persist = true })
    log.info(string.format("Updated bridge endpoint to %s:%s (https=%s)",
      cfg.host or "?", cfg.port or "?", tostring(cfg.use_https)))
    run_discovery(driver, device, true)
  end
end

function parent.device_removed(driver, device)
  if not is_parent(device) then
    return
  end

  log.info(string.format("Parent bridge device removed (%s)", device.label))
  local timer = device:get_field(REFRESH_TIMER)
  if timer then
    device.thread:cancel_timer(timer)
  end
end

local function sync_child_states(driver, device)
  local cfg = get_bridge_config(device)
  load_child.refresh_all(driver, device, cfg)
  scene_child.refresh_all(driver, device, cfg)
end

function parent.handle_refresh(driver, device, _command)
  if not is_parent(device) then
    return
  end

  log.debug("Parent refresh requested")
  device:online()
  run_discovery(driver, device, false)
  sync_child_states(driver, device)
end

return parent
