import type { BridgeResponse } from '../types'
import { getBrowserFallback } from './fallback'
import type { BridgeJobResult, BridgeJobStart, BridgeSignal, BridgeSignalSlot, BridgeSlot } from './shared'
import { isObjectRecord } from './shared'

interface WebChannel {
  objects: {
    pyBridge?: Record<string, BridgeSlot | BridgeSignal | unknown>
  }
}

type QWebChannelConstructor = new (
  transport: unknown,
  callback: (channel: WebChannel) => void
) => unknown

declare global {
  interface Window {
    qt?: {
      webChannelTransport?: unknown
    }
    QWebChannel?: QWebChannelConstructor
  }
}

let bridgePromise: Promise<Record<string, BridgeSlot | unknown> | null> | null = null

export async function callQWebChannelBridge<T = unknown>(method: string, payload: unknown = {}): Promise<T> {
  const bridge = await getBridge()

  if (!bridge) {
    return getBrowserFallback<T>(method, payload)
  }

  const slot = bridge[method]
  if (typeof slot !== 'function') {
    if (method === 'getDataCenterSummary' || method === 'getDataCenterAnalytics') {
      return getBrowserFallback<T>(method, payload)
    }
    throw new Error(`Python bridge method not found: ${method}`)
  }

  const callSlot = slot as BridgeSlot

  return new Promise<T>((resolve, reject) => {
    const timer = window.setTimeout(() => {
      reject(new Error(`Python bridge call timed out: ${method}`))
    }, 30000)

    try {
      callSlot(encodePayload(payload), (response) => {
        window.clearTimeout(timer)
        try {
          resolve(unwrapBridgeResponse<T>(method, response))
        } catch (error) {
          reject(error)
        }
      })
    } catch (error) {
      window.clearTimeout(timer)
      reject(error)
    }
  })
}

export async function callQWebChannelJob<T = unknown>(
  method: string,
  payload: unknown = {},
  timeoutMs: number
): Promise<T> {
  const bridge = await getBridge()
  const signal = bridge?.jobFinished
  if (!isBridgeSignal(signal)) {
    const result = await callQWebChannelBridge<BridgeJobStart<T> | T>(method, payload)
    if (isBridgeJobStart<T>(result)) {
      throw new Error('Python bridge job signal is not available.')
    }
    return result as T
  }

  const jobSignal = signal
  return new Promise<T>((resolve, reject) => {
    let jobId = ''
    const pendingJobPayloads: BridgeJobResult<T>[] = []

    const timer = window.setTimeout(() => {
      cleanup()
      reject(new Error(`Python bridge job timed out: ${method}`))
    }, timeoutMs)

    const handler: BridgeSignalSlot = (rawPayload) => {
      let jobPayload: BridgeJobResult<T>
      try {
        jobPayload = unwrapBridgeJobResult<T>(rawPayload)
      } catch (error) {
        cleanup()
        reject(error)
        return
      }

      if (!jobId) {
        pendingJobPayloads.push(jobPayload)
        return
      }

      if (jobPayload.jobId !== jobId) {
        return
      }

      settleJob(jobPayload)
    }

    function cleanup(): void {
      window.clearTimeout(timer)
      jobSignal.disconnect?.(handler)
    }

    function settleJob(jobPayload: BridgeJobResult<T>): void {
      cleanup()
      if (jobPayload.ok) {
        resolve(jobPayload.result as T)
      } else {
        reject(new Error(jobPayload.error || `Python bridge job failed: ${jobId}`))
      }
    }

    jobSignal.connect(handler)

    callQWebChannelBridge<BridgeJobStart<T> | T>(method, payload)
      .then((start) => {
        if (!isBridgeJobStart<T>(start)) {
          cleanup()
          resolve(start as T)
          return
        }
        jobId = start.job_id
        const pendingPayload = pendingJobPayloads.find((jobPayload) => jobPayload.jobId === jobId)
        if (pendingPayload) {
          settleJob(pendingPayload)
        }
      })
      .catch((error) => {
        cleanup()
        reject(error)
      })
  })
}

async function getBridge(): Promise<Record<string, BridgeSlot | unknown> | null> {
  if (typeof window === 'undefined') {
    return null
  }

  if (bridgePromise) {
    return bridgePromise
  }

  const transport = window.qt?.webChannelTransport
  const QWebChannel = window.QWebChannel
  if (!transport || !QWebChannel) {
    bridgePromise = Promise.resolve(null)
    return bridgePromise
  }

  bridgePromise = new Promise((resolve) => {
    new QWebChannel(transport, (channel) => {
      resolve(channel.objects.pyBridge ?? null)
    })
  })

  return bridgePromise
}

function encodePayload(payload: unknown): string {
  return JSON.stringify(payload ?? {})
}

function unwrapBridgeResponse<T>(method: string, rawResponse: string): T {
  let response: unknown

  try {
    response = JSON.parse(rawResponse)
  } catch {
    throw new Error(`Invalid Python bridge response for ${method}: ${rawResponse}`)
  }

  if (!isBridgeResponse<T>(response)) {
    return response as T
  }

  if (!response.ok) {
    throw new Error(response.error || `Python bridge call failed: ${method}`)
  }

  return response.data as T
}

function isBridgeResponse<T>(value: unknown): value is BridgeResponse<T> {
  return (
    typeof value === 'object' &&
    value !== null &&
    'ok' in value &&
    typeof (value as BridgeResponse<T>).ok === 'boolean'
  )
}

function unwrapBridgeJobResult<T>(rawPayload: string): BridgeJobResult<T> {
  let response: unknown

  try {
    response = JSON.parse(rawPayload)
  } catch {
    throw new Error(`Invalid Python bridge job response: ${rawPayload}`)
  }

  if (!isObjectRecord(response)) {
    throw new Error('Invalid Python bridge job response shape.')
  }

  if (isBridgeResponse<T>(response)) {
    const data = isObjectRecord(response.data) ? response.data : undefined
    return {
      ok: response.ok,
      jobId: getJobId(data) || getJobId(response),
      result: (data?.result ?? response.data) as T,
      error: response.error
    }
  }

  return {
    ok: Boolean(response.ok),
    jobId: getJobId(response),
    result: response.result as T,
    error: typeof response.error === 'string' ? response.error : undefined
  }
}

function isBridgeJobStart<T>(value: BridgeJobStart<T> | T): value is BridgeJobStart<T> {
  return isObjectRecord(value) && typeof value.job_id === 'string' && value.job_id.length > 0
}

function isBridgeSignal(value: unknown): value is BridgeSignal {
  return isObjectRecord(value) && typeof value.connect === 'function'
}

function getJobId(value: unknown): string | undefined {
  if (!isObjectRecord(value)) {
    return undefined
  }
  return typeof value.job_id === 'string' ? value.job_id : undefined
}
