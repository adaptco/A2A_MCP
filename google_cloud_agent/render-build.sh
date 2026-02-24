#!/usr/bin/env bash
# Exit on error
set -o errexit

# Install Python dependencies
pip install -r requirements.txt

# Setup Google Cloud Credentials
# Expects GOOGLE_CREDENTIALS_JSON env var containing the full JSON key content
if [ ! -z "$GOOGLE_CREDENTIALS_JSON" ]; then
    echo "$GOOGLE_CREDENTIALS_JSON" > google-credentials.json
    export GOOGLE_APPLICATION_CREDENTIALS=$(pwd)/google-credentials.json
fi