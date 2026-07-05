# No workflow file needed in monitored repos

Unlike tools that require you to add a step to every workflow, this project
uses a **repository-level webhook**, so it works for every existing workflow
with zero changes to your CI YAML.

## Setup

1. Go to the repo you want monitored → **Settings → Webhooks → Add webhook**
2. Payload URL: `https://<your-deployed-backend>/webhook`
3. Content type: `application/json`
4. Secret: same value as `GITHUB_WEBHOOK_SECRET` in your backend's `.env`
5. "Which events would you like to trigger this webhook?" → select
   **"Let me select individual events"** → check **"Workflow runs"**
6. Save.

That's it — any failed workflow run in that repo will now trigger a
diagnosis automatically.
