import type { BridgeMethodPayloadMap, BridgeMethodResultMap } from './types'
import { apiMode } from './client'
import { callHttpBridge } from './bridgeAdapters/http'
import { callMockBridge } from './bridgeAdapters/mock'
import { callQWebChannelBridge, callQWebChannelJob } from './bridgeAdapters/qwebchannel'
import { callTauriBridge } from './bridgeAdapters/tauri'
import { DEFAULT_BRIDGE_TIMEOUT_MS } from './bridgeAdapters/shared'

export async function callBridge<T = unknown>(method: string, payload: unknown = {}): Promise<T> {
  const mode = apiMode()
  if (mode === 'mock') {
    return callMockBridge<T>(method, payload)
  }
  if (mode === 'qwebchannel') {
    return callQWebChannelBridge<T>(method, payload)
  }
  if (mode === 'tauri') {
    return callTauriBridge<T>(method, payload)
  }
  return callHttpBridge<T>(method, payload)
}

export function callTypedBridge<Method extends keyof BridgeMethodPayloadMap>(
  method: Method,
  payload: BridgeMethodPayloadMap[Method]
): Promise<BridgeMethodResultMap[Method]> {
  return callBridge<BridgeMethodResultMap[Method]>(method, payload)
}

export async function callBridgeJob<T = unknown>(
  method: string,
  payload: unknown = {},
  timeoutMs = DEFAULT_BRIDGE_TIMEOUT_MS
): Promise<T> {
  if (apiMode() === 'qwebchannel') {
    return callQWebChannelJob<T>(method, payload, timeoutMs)
  }
  return callBridge<T>(method, payload)
}
