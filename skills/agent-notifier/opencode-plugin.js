export const AgentNotifierPlugin = async ({ $ }) => {
  const NOTIFY_SCRIPT = `${process.env.HOME}/.agents/skills/agent-notifier/notify.py`
  return {
    event: async ({ event }) => {
      if (event.type === "session.idle") {
        const payload = JSON.stringify({
          platform: "opencode",
          event_type: "session.idle",
          message: "Session completed — waiting for your input",
        })
        await $`echo ${payload} | python3 ${NOTIFY_SCRIPT}`.nothrow().quiet()
      }
      if (event.type === "session.error") {
        const payload = JSON.stringify({
          platform: "opencode",
          event_type: "session.error",
          message: "Session error occurred",
        })
        await $`echo ${payload} | python3 ${NOTIFY_SCRIPT}`.nothrow().quiet()
      }
    },
  }
}