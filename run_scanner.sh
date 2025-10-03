#!/bin/bash
cd /Volumes/ORICO/SignalScan/SignalScan
source .venv/bin/activate
export SSL_CERT_FILE=$(python3 -c "import certifi; print(certifi.where())")
export REQUESTS_CA_BUNDLE=$SSL_CERT_FILE
python3 live_scanner.py
