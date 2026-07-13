# BDM Outbound Dialer

A small desktop app for placing outbound calls through the company Twilio
number. It runs entirely on your own computer — no server, no login.

## First-time setup

1. Install Python 3.10 or later if you don't already have it:
   https://www.python.org/downloads/
2. Open a terminal in this folder and install the dependencies:

   ```
   pip install -r requirements.txt
   ```

3. Copy `.env.example` to a new file named `.env` in the same folder.
4. Fill in your Twilio values in `.env` (ask your admin for these):

   ```
   TWILIO_ACCOUNT_SID=
   TWILIO_API_KEY_SID=
   TWILIO_API_KEY_SECRET=
   TWILIO_FROM_NUMBER=
   BDM_PHONE_NUMBER=
   TWILIO_TWIML_URL=
   ```

   No `.env`, or one with values still missing? That's fine — the app runs
   in **dry-run mode**: you can try the screen, the number validation, and
   the confirmation popup end-to-end without placing a real call or being
   charged.

## How calls connect

This app doesn't stream audio through your computer. Instead, Twilio calls
the BDM's own phone (`BDM_PHONE_NUMBER`) first, and once they answer, it
dials the prospect and bridges the two calls together so they can talk live.

That bridging logic lives in `twiml_server.py`, a small Flask server Twilio
calls back into mid-call. It needs to be reachable over HTTPS at all times
— see **Deploying the bridge server** below for the permanent way to do
this. For local testing, you can instead run it on your own machine and
expose it with a tunnel:

```
python twiml_server.py
```

In another terminal:

```
ngrok http 5000
```

Copy the `https://...ngrok...` URL ngrok prints and set it as
`TWILIO_TWIML_URL` in `.env`. Free ngrok URLs change every restart, so
this is fine for testing but not for the BDM's day-to-day use.

## Deploying the bridge server (do this once, as the admin)

Rather than relying on your laptop and ngrok, deploy `twiml_server.py`
somewhere permanent so its URL never changes:

1. Push this repo to GitHub (already done) and sign up free at
   [render.com](https://render.com).
2. In the Render dashboard: **New > Blueprint**, connect this repo. Render
   reads `render.yaml` automatically and creates the service.
3. In the service's **Environment** tab, add `TWILIO_FROM_NUMBER` (same
   value as in your `.env`).
4. Once deployed, Render gives you a permanent URL like
   `https://carolyn-twiml-bridge.onrender.com`. Use that as
   `TWILIO_TWIML_URL` — for yourself and for the BDM (see below).

Free Render services sleep after inactivity and take a few seconds to wake
on the first call of the day — normal, not a bug.

## Installing the app on the BDM's Mac (no Python required)

1. On this repo's GitHub page: **Actions** tab > **Build macOS App** >
   **Run workflow**. Wait for it to finish (a couple of minutes).
2. Open the finished run, download the **BDM-Dialer-macOS** artifact, and
   unzip it. Send `BDM Dialer.app` to the BDM (AirDrop, Drive, email).
3. On the BDM's Mac, create a config file the app will read on launch:
   - Open **Terminal** (one-time only — no Python needed) and run:
     ```
     mkdir -p ~/.bdm_dialer && open -e ~/.bdm_dialer/.env
     ```
   - A text editor opens. Paste in, filling in the real values:
     ```
     TWILIO_ACCOUNT_SID=
     TWILIO_API_KEY_SID=
     TWILIO_API_KEY_SECRET=
     TWILIO_FROM_NUMBER=
     BDM_PHONE_NUMBER=      # the BDM's own phone number, e.g. +14155552671
     TWILIO_TWIML_URL=      # the permanent Render URL from above
     ```
   - Save and close.
4. Double-click `BDM Dialer.app`. macOS will likely block it with an
   *"Apple could not verify..."* warning since it isn't signed by a paid
   Apple Developer account — **right-click the app > Open > Open** to
   bypass this once. After that it opens normally.

## Running the app (from source)

```
python app.py
```

Enter a phone number in international format (e.g. `+14155552671`), click
**Call**, and confirm in the popup that appears. Your own phone
(`BDM_PHONE_NUMBER`) will ring first — answer it, and you'll be bridged to
the prospect. A banner at the top of the window always tells you whether
the app is in dry-run mode or ready to place live calls.

## Notes

- `.env` stays on your own computer and is never committed to git (it's
  listed in `.gitignore`).
- To force dry-run mode even with valid credentials in `.env` (e.g. while
  testing), add `TWILIO_DRY_RUN=true`.
