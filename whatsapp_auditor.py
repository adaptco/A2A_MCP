import os
import json
import hashlib
import pandas as pd
import requests
from datetime import datetime, timezone, timedelta

# --- Step 1: Securely Store Your WhatsApp API Key and Channel ID ---
# In a real environment, use environment variables or a secret manager.
# Example for local development:
# API_KEY = os.getenv('WHATSAPP_API_KEY')
# CHANNEL_ID = os.getenv('WHATSAPP_CHANNEL_ID')

# --- Step 2: Define Functions for WhatsApp Message Retrieval and Processing ---

def get_whatsapp_messages_paginated(api_key, phone_number_id, limit=100):
    """
    Retrieves messages from the WhatsApp Business API with pagination.

    Args:
        api_key (str): The Meta Cloud API access token.
        phone_number_id (str): The Phone Number ID.
        limit (int): Number of messages per page.

    Returns:
        list: A list of all retrieved message objects.
    """
    url = f"https://graph.facebook.com/v19.0/{phone_number_id}/messages"
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json"
    }
    params = {
        "limit": limit,
        "fields": "id,timestamp,type,text,reaction"
    }

    all_messages = []

    while url:
        try:
            response = requests.get(url, headers=headers, params=params)
            response.raise_for_status()
            data = response.json()

            messages = data.get('data', [])
            all_messages.extend(messages)

            # Check for pagination
            paging = data.get('paging', {})
            next_cursor = paging.get('next')

            if next_cursor:
                url = next_cursor
                params = {} # params are usually included in the next link
            else:
                url = None

        except requests.exceptions.RequestException as e:
            print(f"Error fetching messages: {e}")
            break

    return all_messages

def process_whatsapp_messages(raw_messages):
    """
    Processes raw WhatsApp message objects into a structured DataFrame.

    Args:
        raw_messages (list): List of message dictionaries from the API.

    Returns:
        pd.DataFrame: DataFrame containing processed message data.
    """
    processed_data = []

    for msg in raw_messages:
        msg_id = msg.get('id')
        timestamp = msg.get('timestamp')
        msg_type = msg.get('type')

        # Extract content based on type (simplifying for 'text' and 'reaction')
        content = None
        if msg_type == 'text':
            content = msg.get('text', {}).get('body')
        elif msg_type == 'reaction':
            content = msg.get('reaction', {}).get('emoji')

        # Convert timestamp to datetime
        try:
            # WhatsApp timestamps are usually unix timestamps (seconds)
            ts_dt = datetime.fromtimestamp(int(timestamp), tz=timezone.utc)
        except (ValueError, TypeError):
            ts_dt = None

        processed_data.append({
            'message_id': msg_id,
            'whatsapp_timestamp': ts_dt,
            'type': msg_type,
            'content': content,
            'raw_data': json.dumps(msg)
        })

    df = pd.DataFrame(processed_data)
    return df

# --- Step 3: Timestamp Verification Logic ---

def verify_timestamps(whatsapp_df, internal_df, tolerance_seconds=10):
    """
    Compares Meta-provided timestamps with internal event timestamps.

    Args:
        whatsapp_df (pd.DataFrame): DataFrame from process_whatsapp_messages.
        internal_df (pd.DataFrame): DataFrame containing internal event data.
                                    Must contain 'message_id' and 'internal_timestamp'.
        tolerance_seconds (int): Allowed difference in seconds.

    Returns:
        pd.DataFrame: DataFrame with verification results.
    """
    # Ensure message_id is the key for merging
    merged_df = pd.merge(
        whatsapp_df,
        internal_df[['message_id', 'internal_timestamp']],
        on='message_id',
        how='outer',
        indicator=True
    )

    results = []

    for index, row in merged_df.iterrows():
        wa_ts = row.get('whatsapp_timestamp')
        in_ts = row.get('internal_timestamp')
        status = 'UNKNOWN'
        delta = None

        if pd.notnull(wa_ts) and pd.notnull(in_ts):
            # Ensure both are offset-aware or both are offset-naive
            if wa_ts.tzinfo is None:
                wa_ts = wa_ts.replace(tzinfo=timezone.utc)
            if in_ts.tzinfo is None:
                in_ts = in_ts.replace(tzinfo=timezone.utc)

            delta = abs((wa_ts - in_ts).total_seconds())

            if delta <= tolerance_seconds:
                status = 'MATCH'
            else:
                status = 'DISCREPANCY'
        elif row['_merge'] == 'left_only':
            status = 'MISSING_INTERNAL'
        elif row['_merge'] == 'right_only':
            status = 'MISSING_WHATSAPP'

        results.append({
            'message_id': row['message_id'],
            'whatsapp_timestamp': wa_ts,
            'internal_timestamp': in_ts,
            'delta_seconds': delta,
            'status': status
        })

    return pd.DataFrame(results)

# --- Step 4: Local State Hashing & Step 5: Hash Cross-Referencing ---

def reconstruct_and_hash_local_state(event_record):
    """
    Standardizes critical fields and computes a SHA-256 hash.

    Args:
        event_record (dict): Dictionary representing a single internal event row.

    Returns:
        str: The SHA-256 hash hex string.
    """
    # standardized fields to include in hash (example)
    # In a real scenario, this must match exactly what was hashed previously
    fields_to_hash = [
        str(event_record.get('message_id', '')),
        str(event_record.get('content', '')),
        str(event_record.get('type', ''))
        # Add other fields as necessary (e.g., previous_hash)
    ]

    canonical_string = "|".join(fields_to_hash)
    return hashlib.sha256(canonical_string.encode('utf-8')).hexdigest()

def verify_hashes(whatsapp_df, internal_df):
    """
    Compares locally generated hashes with the 'hash_current' sent to WhatsApp (if available).
    Note: In this implementation, we assume the 'internal_df' contains the 'hash_current'
    that we *expect* to match the local state reconstruction.

    Args:
        whatsapp_df (pd.DataFrame): DataFrame from process_whatsapp_messages.
        internal_df (pd.DataFrame): DataFrame containing internal event data.
                                    Must contain 'message_id' and 'hash_current'.

    Returns:
        pd.DataFrame: DataFrame with hash verification results.
    """
    # Calculate fresh hashes from current local state
    internal_df = internal_df.copy()
    internal_df['calculated_hash'] = internal_df.apply(reconstruct_and_hash_local_state, axis=1)

    # Merge
    merged_df = pd.merge(
        whatsapp_df[['message_id']],
        internal_df[['message_id', 'hash_current', 'calculated_hash']],
        on='message_id',
        how='outer',
        indicator=True
    )

    results = []

    for index, row in merged_df.iterrows():
        stored_hash = row.get('hash_current')
        calc_hash = row.get('calculated_hash')
        status = 'UNKNOWN'

        if pd.notnull(stored_hash) and pd.notnull(calc_hash):
            # Compare prefixes (e.g., first 12 chars) or full hash
            # Assuming stored_hash might be a prefix or full
            if calc_hash == stored_hash:
            else:
                status = 'MISMATCH'
        elif row['_merge'] == 'left_only':
            status = 'MISSING_INTERNAL'
        elif row['_merge'] == 'right_only':
            status = 'MISSING_WHATSAPP'

        results.append({
            'message_id': row['message_id'],
            'stored_hash_current': stored_hash,
            'calculated_local_hash': calc_hash,
            'status': status
        })

    return pd.DataFrame(results)

# --- Step 6: Auditor CLI ---

def auditor_cli(api_key, phone_number_id, internal_events_df, limit=100):
    """
    Orchestrates the verification process.
    """
    print(f"--- Starting WhatsApp Audit for Phone ID: {phone_number_id} ---")

    # 1. Retrieve Messages
    print("Retrieving messages from WhatsApp...")
    # For demo purposes, if api_key is 'MOCK', we use mock data.
    if api_key == 'MOCK':
        print("Using MOCK mode.")
        raw_messages = [] # handled in main demo block usually, but let's handle here for CLI consistency if needed
    else:
        raw_messages = get_whatsapp_messages_paginated(api_key, phone_number_id, limit)

    if not raw_messages and api_key != 'MOCK':
        print("No messages found or error occurred.")
        return

    # 2. Process Messages
    if api_key != 'MOCK':
        whatsapp_df = process_whatsapp_messages(raw_messages)
    else:
        # If mock, we expect the caller to provide the DF or we skip (this function structure assumes real data usually)
        # To make this CLI robust for the example, we'll return early and let the demo block handle mock data generation.
        return

    print(f"Retrieved {len(whatsapp_df)} messages.")

    # 3. Verify Timestamps
    print("\nVerifying Timestamps...")
    ts_report = verify_timestamps(whatsapp_df, internal_events_df)
    print(ts_report[['message_id', 'status', 'delta_seconds']].to_string())

    # 4. Verify Hashes
    print("\nVerifying Hashes...")
    hash_report = verify_hashes(whatsapp_df, internal_events_df)
    print(hash_report[['message_id', 'status', 'stored_hash_current']].to_string())

    # Summary
    print("\n--- Audit Summary ---")
    print(f"Timestamp Matches: {len(ts_report[ts_report['status'] == 'MATCH'])}")
    print(f"Hash Matches: {len(hash_report[hash_report['status'] == 'MATCH'])}")


# --- Mock Data & Execution for Demonstration ---

def run_demo():
    print("\n--- Running Demo with Mock Data ---\n")

    # 1. Create Mock WhatsApp Messages (Data that would come from API)
    # We use timezone-aware datetimes for consistency
    base_time = datetime.now(timezone.utc)

    mock_raw_messages = [
        # Msg 1: Valid Match
        {
            'id': 'wamid.HBgLMjM0OTk3MDczMjYxFQIAERgSQA==_msg1',
            'timestamp': (base_time - timedelta(seconds=100)).timestamp(),
            'type': 'text',
            'text': {'body': 'Hello World'}
        },
        # Msg 2: Valid Match
        {
            'id': 'wamid.HBgLMjM0OTk3MDczMjYyFQIAERgSQA==_msg2',
            'timestamp': (base_time - timedelta(seconds=200)).timestamp(),
            'type': 'text',
            'text': {'body': 'Status Update'}
        },
        # Msg 3: Timestamp Discrepancy & Hash Mismatch
        {
            'id': 'wamid.HBgLMjM0OTk3MDczMjY3FQIAERgSQA==_msg3',
            'timestamp': (base_time - timedelta(seconds=300)).timestamp(), # WhatsApp time
            'type': 'text',
            'text': {'body': 'Mismatch Content'}
        },
        # Msg 4: Missing in Internal DB (No Match)
        {
            'id': 'wamid.HBgLMjM0OTk3MDczMjY4FQIAERgSQA==_msg4_no_internal_match',
            'timestamp': (base_time - timedelta(seconds=400)).timestamp(),
            'type': 'text',
            'text': {'body': 'Ghost Message'}
        }
    ]

    # Process them into DataFrame
    # Note: process_whatsapp_messages expects raw dicts, which we provided above
    whatsapp_df = process_whatsapp_messages(mock_raw_messages)

    # 2. Create Mock Internal Event Data
    # We need to construct this carefully to match the scenario

    # For Msg 1 & 2, we want Hash Match.
    # The 'reconstruct_and_hash_local_state' uses message_id|content|type
    # So we must pre-calculate what that hash will be to put it in 'hash_current'

    def calc_hash(mid, content, mtype):
        s = f"{mid}|{content}|{mtype}"
        return hashlib.sha256(s.encode('utf-8')).hexdigest()

    hash1 = calc_hash(mock_raw_messages[0]['id'], 'Hello World', 'text')
    hash2 = calc_hash(mock_raw_messages[1]['id'], 'Status Update', 'text')

    # For Msg 3, we want Hash Mismatch. We'll store a different hash.
    hash3_stored = "bad_hash_value_stored_in_db"

    internal_data = [
        {
            'message_id': mock_raw_messages[0]['id'],
            'internal_timestamp': datetime.fromtimestamp(mock_raw_messages[0]['timestamp'], tz=timezone.utc), # Exact match
            'content': 'Hello World',
            'type': 'text',
            'hash_current': hash1
        },
        {
            'message_id': mock_raw_messages[1]['id'],
            'internal_timestamp': datetime.fromtimestamp(mock_raw_messages[1]['timestamp'], tz=timezone.utc), # Exact match
            'content': 'Status Update',
            'type': 'text',
            'hash_current': hash2
        },
        {
            'message_id': mock_raw_messages[2]['id'],
            'internal_timestamp': datetime.fromtimestamp(mock_raw_messages[2]['timestamp'], tz=timezone.utc) + timedelta(seconds=15), # 15s discrepancy
            'content': 'Mismatch Content',
            'type': 'text',
            'hash_current': hash3_stored # Mismatch
        }
        # Msg 4 is missing from here
    ]

    internal_df = pd.DataFrame(internal_data)

    # 3. Run Verifications

    print("--- Timestamp Verification Report ---")
    ts_report = verify_timestamps(whatsapp_df, internal_df)
    print(ts_report[['message_id', 'status', 'delta_seconds']].to_string())

    print("\n--- Hash Verification Report ---")
    hash_report = verify_hashes(whatsapp_df, internal_df)
    # Merging 'hash_current' (stored) vs 'calculated_hash' (computed from local content)
    # We need to compute calculated hash for the report display if verify_hashes doesn't return it
    # verify_hashes returns 'stored_hash_current' and 'calculated_local_hash'
    print(hash_report[['message_id', 'status', 'stored_hash_current', 'calculated_local_hash']].to_string())

if __name__ == "__main__":
    api_key = os.getenv('WHATSAPP_API_KEY')
    phone_id = os.getenv('WHATSAPP_PHONE_ID')

    if api_key and phone_id:
        print(f"Environment variables found for Phone ID: {phone_id}")
        print("Running in live mode...")
        # TODO: In a real application, you would load 'internal_events_df' from your database here.
        # For this example, we'll use an empty DataFrame as a placeholder.
        internal_events_df = pd.DataFrame()
        auditor_cli(api_key, phone_id, internal_events_df)
    else:
        run_demo()
