local capabilities = require "st.capabilities"
local Driver = require "st.driver"
local log = require "log"

local parent_device = require "devices.parent"
local load_child = require "devices.load_child"
local scene_child = require "devices.scene_child"

local function parent_exists(driver)
  for _, device in ipairs(driver:get_devices() or {}) do
    if device.parent_assigned_child_key == nil then
      return true
    end
  end
  return false
end

local function discovery_handler(driver, _, should_continue)
  log.info_with({ hub_logs = true }, "Starting Vantage bridge discovery")

  if parent_exists(driver) then
    log.info_with({ hub_logs = true }, "Parent device already present; skipping discovery")
    return
  end

  local env = driver.environment_info or {}
  local dni_source = env.hub_ipv4 or env.hub_zigbee_id or tostring(os.time())
  local sanitized = string.upper((tostring(dni_source)):gsub("[^%w]", ""))
  if sanitized == "" then
    sanitized = string.upper(string.format("%X", os.time()))
  end
  local device_network_id = string.format("VANTAGEQBRIDGE-%s", sanitized)

  local create_device_msg = {
    type = "LAN",
    device_network_id = device_network_id,
    label = "Vantage QLink Bridge",
    profile = "vantageBridge.parent",
    manufacturer = "Vantage",
    model = "QLinkBridge",
    vendor_provided_label = "Vantage QLink Bridge",
  }

  local success, err = driver:try_create_device(create_device_msg)
  if success then
    log.info_with({ hub_logs = true }, string.format("Created parent bridge device (dni=%s)", device_network_id))
  else
    log.error_with({ hub_logs = true }, string.format("Failed to create parent bridge device: %s", err or "unknown error"))
  end

  if should_continue and should_continue() then
    -- This driver only creates a single parent device, so no need to loop further.
    return
  end
end

local function is_load_device(device)
  return device:get_field("load_id") ~= nil or (device.parent_assigned_child_key and device.parent_assigned_child_key:match("^load:"))
end

local driver_template = {
  supported_capabilities = {
    capabilities.refresh,
    capabilities.healthCheck,
    capabilities.switch,
    capabilities.switchLevel,
    capabilities.button,
  },
  lifecycle_handlers = {
    init = parent_device.device_init,
    added = parent_device.device_added,
    infoChanged = parent_device.device_info_changed,
    removed = parent_device.device_removed,
  },
  discovery = discovery_handler,
  capability_handlers = {
    [capabilities.refresh.ID] = {
      [capabilities.refresh.commands.refresh.NAME] = parent_device.handle_refresh,
    },
    [capabilities.switch.ID] = {
      [capabilities.switch.commands.on.NAME] = function(driver, device, command)
        if is_load_device(device) then
          load_child.handle_on(driver, device, command)
        else
          scene_child.handle_switch_on(driver, device, command)
        end
      end,
      [capabilities.switch.commands.off.NAME] = function(driver, device, command)
        if is_load_device(device) then
          load_child.handle_off(driver, device, command)
        else
          scene_child.handle_switch_off(driver, device, command)
        end
      end,
    },
    [capabilities.switchLevel.ID] = {
      [capabilities.switchLevel.commands.setLevel.NAME] = function(driver, device, command)
        if is_load_device(device) then
          load_child.handle_set_level(driver, device, command)
        else
          log.warn(string.format("Ignoring setLevel on non-load child %s", device.label))
        end
      end,
    },
    [capabilities.button.ID] = {
      [capabilities.button.commands.push.NAME] = scene_child.handle_push,
      [capabilities.button.commands.hold.NAME] = scene_child.handle_hold,
    },
  },
}

local driver = Driver("vantage-bridge", driver_template)

log.info_with({ hub_logs = true }, "Vantage QLink Bridge SmartThings Edge driver initialised")

driver:run()
