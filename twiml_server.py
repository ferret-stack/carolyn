"""Simple TwiML server to replace the rickroll demo."""

from flask import Flask, Response

app = Flask(__name__)


@app.route("/voice", methods=["POST"])
def voice():
    """Return TwiML for incoming calls."""
    twiml = """<?xml version="1.0" encoding="UTF-8"?>
<Response>
    <Say>Hello. Thank you for calling.</Say>
    <Hangup/>
</Response>
"""
    return Response(twiml, mimetype="application/xml")


if __name__ == "__main__":
    # Run on localhost:5000
    app.run(debug=False, port=5000)
