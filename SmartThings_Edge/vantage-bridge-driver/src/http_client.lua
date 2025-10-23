local cosock = require "cosock"
local http = cosock.asyncify "socket.http"
local ltn12 = require "ltn12"
local log = require "log"
local json = require "st.json"

local M = {}

local DEFAULT_TIMEOUT = 5

local function request(method, url, body, headers)
  local response_chunks = {}
  local req_headers = headers or {}
  req_headers["Content-Type"] = req_headers["Content-Type"] or "application/json"

  local result, status_code, response_headers, status_line = http.request({
    method = method,
    url = url,
    source = body and ltn12.source.string(body) or nil,
    sink = ltn12.sink.table(response_chunks),
    headers = req_headers,
    timeout = DEFAULT_TIMEOUT,
  })

  if not result then
    return nil, string.format("HTTP request failed (%s)", status_line or "unknown error")
  end

  local response_body = table.concat(response_chunks)
  if status_code and status_code >= 400 then
    return nil, string.format("HTTP %s: %s", status_code, response_body)
  end
  return response_body, nil, response_headers
end

function M.get(url, headers)
  return request("GET", url, nil, headers)
end

function M.post(url, body, headers)
  return request("POST", url, body, headers)
end

function M.decode_json(raw)
  if not raw or raw == "" then return nil end
  local ok, decoded = pcall(json.decode, raw)
  if not ok then
    log.warn(string.format("Failed to decode JSON response: %s", decoded))
    return nil
  end
  return decoded
end

function M.encode_json(tbl)
  local ok, encoded = pcall(json.encode, tbl)
  if not ok then
    log.warn(string.format("Failed to encode JSON payload: %s", encoded))
    return nil
  end
  return encoded
end

return M
