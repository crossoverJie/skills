export const AgentNotifierPlugin = async ({ $ }) => {
  return {
    event: async ({ event }) => {
      if (event.type === "session.idle") {
        const payload = JSON.stringify({
          platform: "opencode",
          event_type: "session.idle",
          message: "Session completed — waiting for your input"
        });
        await $`echo ${payload} | python3 ~/.claude/skills/agent-notifier/notify.py`;
      }
    }
  }
}
