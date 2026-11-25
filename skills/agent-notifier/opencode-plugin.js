import { spawn } from "node:child_process"
import { existsSync } from "node:fs"
import { homedir } from "node:os"
import { join } from "node:path"

function resolveNotifyScript() {
  const home = process.env.HOME || homedir()
  const candidates = [
    process.env.AGENT_NOTIFIER_SCRIPT,
    join(home, ".claude", "skills", "agent-notifier", "notify.py"),
    join(home, ".agents", "skills", "agent-notifier", "notify.py"),
  ].filter(Boolean)
  for (const candidate of candidates) {
    if (existsSync(candidate)) return candidate
  }
  return join(home, ".agents", "skills", "agent-notifier", "notify.py")
}

function dispatchNotification(payload) {
  const script = resolveNotifyScript()
  try {
    const child = spawn("python3", [script, "--platform", "opencode"], {
      stdio: ["pipe", "ignore", "ignore"],
      detached: true,
    })
    child.on("error", () => {})
    if (child.stdin) {
      child.stdin.on("error", () => {})
      child.stdin.end(JSON.stringify(payload))
    }
    child.unref()
  } catch {
    // Notification errors must never disrupt OpenCode execution.
  }
}

async function lookupSessionInfo(ctx, sessionID, signal) {
  if (!sessionID || !ctx?.session?.get) return null
  const attempts =
    ctx.session.get.length >= 2
      ? [
          [{ sessionID }, { signal }],
          [{ path: { id: sessionID }, signal }],
        ]
      : [[{ sessionID, signal }], [{ path: { id: sessionID }, signal }]]
  for (const args of attempts) {
    try {
      const res = await ctx.session.get(...args)
      const info = res?.data ?? res
      if (info && typeof info === "object") return info
    } catch {
      if (signal?.aborted) return null
    }
  }
  return null
}

function extractErrorDetail(data) {
  const err = data?.error ?? data?.reason ?? data?.message ?? ""
  if (typeof err === "string") return err.slice(0, 120)
  if (err && typeof err === "object") {
    const msg = err.message || err.name || err.type || err.code || ""
    if (typeof msg === "string") return msg.slice(0, 120)
  }
  return ""
}

async function setupOpenCode2Notifier(ctx) {
  if (!ctx?.event?.subscribe) return async () => {}

  const controller = new AbortController()
  const sessionMetaById = new Map() // sessionID -> { isChild: boolean, directory: string }
  const dedupeTimestamps = new Map()
  const DEDUPE_MS = 1500

  function rememberSession(id, isChild, directory = "") {
    if (!id) return
    if (sessionMetaById.size >= 256 && !sessionMetaById.has(id)) {
      const oldest = sessionMetaById.keys().next().value
      if (oldest !== undefined) sessionMetaById.delete(oldest)
    }
    sessionMetaById.set(id, { isChild: Boolean(isChild), directory: directory || "" })
  }

  async function resolveSessionMeta(sessionID) {
    if (!sessionID) return { isChild: false, directory: "" }
    if (sessionMetaById.has(sessionID)) return sessionMetaById.get(sessionID)
    const info = await lookupSessionInfo(ctx, sessionID, controller.signal)
    if (!info) return { isChild: false, directory: "" }
    const meta = {
      isChild: Boolean(info.parentID),
      directory: info.directory || "",
    }
    rememberSession(sessionID, meta.isChild, meta.directory)
    return meta
  }

  function shouldDedupe(key) {
    const now = Date.now()
    const prev = dedupeTimestamps.get(key)
    if (prev !== undefined && now - prev < DEDUPE_MS) return true
    if (dedupeTimestamps.size >= 256) {
      const oldest = dedupeTimestamps.keys().next().value
      if (oldest !== undefined) dedupeTimestamps.delete(oldest)
    }
    dedupeTimestamps.set(key, now)
    return false
  }

  const consume = async () => {
    for await (const input of ctx.event.subscribe({ signal: controller.signal })) {
      if (controller.signal.aborted) break
      const type = input?.type
      const data = input?.data || input?.properties || {}
      const sessionID = data?.sessionID || data?.info?.id || ""

      if (type === "session.created") {
        const info = data?.info || data
        const id = info?.sessionID || info?.id || ""
        rememberSession(id, Boolean(info?.parentID), info?.directory || "")
        continue
      }

      if (type === "session.execution.succeeded") {
        const meta = await resolveSessionMeta(sessionID)
        if (meta.isChild) continue
        if (shouldDedupe(`done:${sessionID}`)) continue
        dispatchNotification({
          platform: "opencode",
          event_type: "session.execution.succeeded",
          message: "Task completed — waiting for your input",
          cwd: data?.directory || meta.directory || "",
        })
        continue
      }

      if (type === "session.execution.failed" || type === "session.error") {
        const meta = await resolveSessionMeta(sessionID)
        if (meta.isChild) continue
        if (shouldDedupe(`err:${sessionID}:${type}`)) continue
        const detail = extractErrorDetail(data)
        dispatchNotification({
          platform: "opencode",
          event_type: type,
          message: detail || "",
          cwd: data?.directory || meta.directory || "",
        })
        continue
      }

      if (type === "permission.asked") {
        const meta = await resolveSessionMeta(sessionID)
        const action = data?.action || data?.permission || data?.title || ""
        const reqId = data?.id || action || sessionID
        if (shouldDedupe(`perm:${reqId}`)) continue
        dispatchNotification({
          platform: "opencode",
          event_type: "permission.asked",
          message: action ? `Permission required (${action})` : "Permission required",
          cwd: data?.directory || meta.directory || "",
        })
        continue
      }

      if (type === "form.created" || type === "question.asked") {
        const meta = await resolveSessionMeta(sessionID)
        const form = data?.form || data
        const title =
          form?.title ||
          form?.fields?.[0]?.title ||
          data?.questions?.[0]?.question ||
          ""
        const reqId = form?.id || data?.id || title || sessionID
        if (shouldDedupe(`form:${reqId}`)) continue
        dispatchNotification({
          platform: "opencode",
          event_type: "form.created",
          message: title ? `Waiting for your answer: ${title}` : "Waiting for your answer",
          cwd: data?.directory || meta.directory || "",
        })
      }
    }
  }

  const consuming = consume().catch(() => {})

  return async () => {
    controller.abort()
    await consuming
  }
}

export default {
  id: "agent-notifier",
  server: async () => ({}),
  setup: setupOpenCode2Notifier,
}
