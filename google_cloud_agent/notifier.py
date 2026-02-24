import os
from twilio.rest import Client

class WhatsAppNotifier:
    def __init__(self, account_sid: str = None, auth_token: str = None, from_number: str = None):
        self.account_sid = account_sid or os.getenv("TWILIO_ACCOUNT_SID")
        self.auth_token = auth_token or os.getenv("TWILIO_AUTH_TOKEN")
        self.from_number = from_number or os.getenv("TWILIO_FROM_NUMBER")
        
        if not all([self.account_sid, self.auth_token, self.from_number]):
            raise ValueError("Twilio credentials are required.")
            
        self.client = Client(self.account_sid, self.auth_token)

    def send_message(self, to_number: str, message_body: str) -> str:
        """Sends a WhatsApp message using Twilio."""
        try:
            message = self.client.messages.create(
                from_=f"whatsapp:{self.from_number}",
                body=message_body,
                to=f"whatsapp:{to_number}"
            )
            return message.sid
        except Exception as e:
            # Simple error handling for now
            print(f"Error sending message: {e}")
            raise