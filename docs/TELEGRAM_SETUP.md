# LifeOS — Telegram Bot Integration & Approval Guide

LifeOS uses Telegram as the mobile command center for human-in-the-loop oversight. Telegram is where you receive notifications of autonomous operations and authorize high-risk actions (creating calendar events, scheduling tasks, sending email drafts).

---

## 1. Creating Your Telegram Bot with BotFather

1. Open Telegram and search for [@BotFather](https://t.me/botfather).
2. Send `/newbot`.
3. Choose a display name (e.g. `My LifeOS Assistant`).
4. Choose a unique username ending in `bot` (e.g. `MyLifeOS_Operator_bot`).
5. BotFather will provide an HTTP API token:
   ```text
   7182938472:AAH9f23kL...9834kd
   ```
6. Add this token to your backend environment:
   ```ini
   TELEGRAM_BOT_TOKEN=7182938472:AAH9f23kL...9834kd
   TELEGRAM_BOT_USERNAME=MyLifeOS_Operator_bot
   ```

---

## 2. Pairing Your Telegram Account with Your LifeOS Profile

To receive notifications and approve actions, your Telegram account must be linked to your LifeOS user ID:

### Method A: Deep-Link Pairing (One-Click)
1. Open the LifeOS Web Dashboard and log in.
2. Navigate to **Integrations** > **Telegram**.
3. Click the **Pair with Telegram** button.
4. Telegram opens your bot with a pre-filled start parameter:
   ```text
   /start pair_9f8e2a
   ```
5. Press **Start**. Your `chat_id` is automatically linked to your tenant profile.

### Method B: Manual Chat ID Entry
1. Message your bot `/id` or message [@userinfobot](https://t.me/userinfobot) to find your numeric Chat ID (e.g. `123456789`).
2. In the LifeOS dashboard under Profile or Integrations, paste your Chat ID.

---

## 3. Human-in-the-Loop Approval Workflow

When a voice command triggers a high-risk action (such as creating a Gmail draft or deleting an item):

1. **Telegram Alert**: The bot sends an interactive message:
   ```text
   ⚠️ LifeOS Action Approval Required
   
   Action: Create Gmail Draft
   Recipient: sarah@company.com
   Subject: Project Alpha Update
   ```
2. **Inline Buttons**:
   - `[ Approve Action ]` (callback data: `approve_act-12345`)
   - `[ Reject Action ]` (callback data: `reject_act-12345`)
3. **Execution & Feedback**:
   - Tapping **Approve** immediately dispatches the task to Composio, verifies the result, updates persistent memory in Qdrant, and updates the Telegram message with:
     ```text
     ✅ Action Approved & Executed (Verified Live)
     ```

---

## 4. Webhook vs. Polling Configuration

- **Development / Local**: When running locally without a public IP, LifeOS automatically operates using asynchronous long-polling (`getUpdates`).
- **Production**: When `PUBLIC_BASE_URL` is set, LifeOS automatically registers an HTTPS webhook:
  ```text
  POST https://your-backend.com/api/telegram/webhook
  ```
