"""TwiML server that bridges the BDM to the prospect.

Flow: twilio_client.py calls the BDM's own phone first. When the BDM
answers, Twilio requests /connect on this server, which dials the
prospect's number and joins the two legs so they can talk live.

Must be reachable by Twilio over HTTPS (e.g. via ngrok, or deployed
somewhere public). Set TWILIO_TWIML_URL in .env to this server's base URL.
"""

import os

from flask import Flask, Response, request
from twilio.twiml.voice_response import Dial, VoiceResponse

from twilio_client import is_valid_e164

app = Flask(__name__)


@app.route("/connect", methods=["GET", "POST"])
def connect():
    """TwiML for the BDM's leg: announce, then dial and bridge the prospect."""
    to_number = request.values.get("to", "").strip()

    response = VoiceResponse()
    if not to_number or not is_valid_e164(to_number):
        response.say("Invalid destination number. Goodbye.")
        response.hangup()
        return Response(str(response), mimetype="application/xml")

    response.say("Connecting your call now.")
    from_number = os.getenv("TWILIO_FROM_NUMBER")
    dial = Dial(caller_id=from_number) if from_number else Dial()
    dial.number(to_number)
    response.append(dial)
    return Response(str(response), mimetype="application/xml")


if __name__ == "__main__":
    # Local dev only. In production (e.g. Render) gunicorn serves this app instead.
    app.run(debug=False, port=5000)
