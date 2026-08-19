"""TwiML server that bridges the BDM to the prospect.

Two flows:

- Outbound: twilio_client.py calls the BDM's own phone first. When the BDM
  answers, Twilio requests /connect on this server, which dials the
  prospect's number and joins the two legs so they can talk live.
- Inbound: when someone calls the BDM's Twilio number directly, Twilio
  requests /incoming on this server, which rings the BDM's own phone.

Must be reachable by Twilio over HTTPS (e.g. via ngrok, or deployed
somewhere public). Set TWILIO_TWIML_URL in .env to this server's base URL,
and set /incoming as the Twilio number's "A call comes in" webhook in the
Twilio Console (Phone Numbers > Manage > Active Numbers > select the
number > Voice Configuration).
"""

import json
import os

from flask import Flask, Response, request
from twilio.twiml.voice_response import Dial, VoiceResponse

from twilio_client import is_valid_e164

app = Flask(__name__)


def _bdm_number_for(called_number: str) -> str:
    """Look up which BDM's personal phone rings for an inbound call.

    One Render deployment is shared by every BDM, but each BDM has their
    own Twilio number, so BDM_PHONE_NUMBER alone (a single value) can't
    tell us who to ring. INBOUND_ROUTING_MAP is a JSON object mapping each
    BDM's Twilio number to their personal phone, e.g.:
        {"+15551234567": "+15559876543", "+15551110000": "+15552223333"}
    Falls back to BDM_PHONE_NUMBER for simple single-BDM/local setups.
    """
    raw_map = os.getenv("INBOUND_ROUTING_MAP", "").strip()
    if raw_map:
        try:
            routing = json.loads(raw_map)
        except json.JSONDecodeError:
            routing = {}
        match = routing.get(called_number, "").strip() if isinstance(routing, dict) else ""
        if match:
            return match

    return os.getenv("BDM_PHONE_NUMBER", "").strip()


@app.route("/connect", methods=["GET", "POST"])
def connect():
    """TwiML for the BDM's leg: announce, then dial and bridge the prospect."""
    to_number = "".join(request.values.get("to", "").split())

    response = VoiceResponse()
    if not to_number or not is_valid_e164(to_number):
        response.say("Invalid destination number. Goodbye.")
        response.hangup()
        return Response(str(response), mimetype="application/xml")

    response.say("Connecting your call now.")
    caller_id = request.values.get("caller_id", "").strip() or os.getenv("TWILIO_FROM_NUMBER")
    dial = Dial(caller_id=caller_id) if caller_id else Dial()
    dial.number(to_number)
    response.append(dial)
    return Response(str(response), mimetype="application/xml")


@app.route("/incoming", methods=["GET", "POST"])
def incoming():
    """TwiML for an inbound call to the BDM's Twilio number: ring the BDM's own phone.

    Configure this as the number's "A call comes in" webhook in the Twilio
    Console so calls to the Twilio number (and WhatsApp verification calls)
    actually reach the BDM.
    """
    called_number = "".join(request.values.get("To", "").split())
    bdm_number = _bdm_number_for(called_number)

    response = VoiceResponse()
    if not bdm_number or not is_valid_e164(bdm_number):
        response.say("This number is not yet configured to receive calls. Goodbye.")
        response.hangup()
        return Response(str(response), mimetype="application/xml")

    response.say("Please hold while we connect your call.")
    dial = Dial()
    dial.number(bdm_number)
    response.append(dial)
    return Response(str(response), mimetype="application/xml")


if __name__ == "__main__":
    # Local dev only. In production (e.g. Render) gunicorn serves this app instead.
    app.run(debug=False, port=5000)
