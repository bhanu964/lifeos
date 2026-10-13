# LifeOS — Omi Integration & Webhook Guide

This guide describes how to configure the **Omi** mobile application or wearable device to automatically trigger LifeOS autonomous workflows.

---

## 1. What is Omi?

**Omi** is an open-source AI wearable and mobile application that continuously captures, transcribes, and summarizes real-world conversations. 

LifeOS uses Omi as its primary voice trigger. When a user finishes speaking, Omi dispatches an HTTPS webhook payload containing the conversation transcript to the LifeOS backend.

---

## 2. Setting Up the Webhook in the Omi App

### Step 1: Obtain Your Personal Webhook URL
1. Open your LifeOS web dashboard.
2. Sign in or register your account.
3. In the sidebar or **Integrations** tab, locate **Omi Wearable Integration**.
4. Copy your personalized webhook URL:
   ```text
   https://your-backend-domain.com/omi/conversation?uid=usr_12345&token=omi_sec_abcde
   ```
   *Note: Every user gets a unique tenant token ensuring voice input is routed strictly to their private workspace.*

### Step 2: Configure the Omi Mobile App
1. Open the **Omi** app on iOS or Android.
2. Navigate to **Settings** > **Developer Settings** (or **Integrations** / **Webhooks**).
3. Toggle **Real-time Webhook** or **Conversation Webhook** ON.
4. Paste your LifeOS Webhook URL into the **Webhook Endpoint URL** field.
5. Save the configuration.

---

## 3. Webhook Payload Specifications

LifeOS accepts both standard Omi conversation payloads and raw transcript objects:

### Request Example (`POST /omi/conversation`)
```json
{
  "id": "3c08f762-6c1b-4bbb-972c-eecc63182241",
  "created_at": "2026-10-13T16:49:48Z",
  "transcript_segments": [
    {
      "text": "Check my Google calendar for tomorrow. Tell me what meetings I have and how much free time is available.",
      "speaker": "SPEAKER_00",
      "start": 0.0,
      "end": 4.5
    }
  ],
  "structured": {
    "title": "Calendar and schedule inquiry",
    "overview": "User requested schedule check for tomorrow."
  }
}
```

---

## 4. Deduplication & Idempotency Engine

Omi frequently sends incremental chunks or retries failed HTTP requests. LifeOS prevents repeated execution using dual deduplication:

1. **UUID5 Segment Hashing**: Individual speech segments are keyed by `uuid5(NAMESPACE_DNS, f"{uid}:{session_id}:{text}")`.
2. **Workflow Idempotency Hash**: Full conversation transcripts generate a deterministic SHA-256 hash:
   ```python
   hashlib.sha256(f"{uid}:{conversation_id}:{normalized_transcript}".encode()).hexdigest()
   ```
If an identical conversation is received twice within a session window, LifeOS returns the existing workflow state without re-executing actions.

---

## 5. Local Testing via ngrok

When developing locally:
1. Expose your local port 8000:
   ```bash
   ngrok http 8000
   ```
2. Copy the resulting HTTPS forwarding URL (e.g. `https://abc-123.ngrok-free.app`).
3. Set your webhook URL in Omi:
   ```text
   https://abc-123.ngrok-free.app/omi/conversation?uid=usr_local&token=your_token
   ```
