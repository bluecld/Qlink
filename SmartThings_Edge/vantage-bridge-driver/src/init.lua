local capabilities = require "st.capabilities"
local Driver = require "st.driver"
local log = require "log"

local parent_device = require "devices.parent"
local load_child = require "devices.load_child"
local scene_child = require "devices.scene_child"

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
