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
   ```

   No `.env`, or one with values still missing? That's fine — the app runs
   in **dry-run mode**: you can try the screen, the number validation, and
   the confirmation popup end-to-end without placing a real call or being
   charged.

## Running the app

```
python app.py
```

Enter a phone number in international format (e.g. `+14155552671`), click
**Call**, and confirm in the popup that appears. A banner at the top of the
window always tells you whether the app is in dry-run mode or ready to
place live calls.

## Notes

- `.env` stays on your own computer and is never committed to git (it's
  listed in `.gitignore`).
- To force dry-run mode even with valid credentials in `.env` (e.g. while
  testing), add `TWILIO_DRY_RUN=true`.
