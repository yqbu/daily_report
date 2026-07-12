import { callHttpBridge } from './http'

export async function callTauriBridge<T>(method: string, payload: unknown): Promise<T> {
  return callHttpBridge<T>(method, payload)
}
