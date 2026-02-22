import os
import google.generativeai as genai

def generate_content_with_gemini(prompt_text, model_name='models/gemini-flash-latest'):
    """
    Generates content using the Google Gemini API.

    Args:
        prompt_text (str): The prompt to send to the model.
        model_name (str, optional): The name of the model to use. Defaults to 'models/gemini-flash-latest'.

    Returns:
        str: The generated text.
    """
    api_key = os.environ.get("GOOGLE_API_KEY")
    if not api_key:
        raise ValueError("GOOGLE_API_KEY environment variable is not set.")

    genai.configure(api_key=api_key)
    model = genai.GenerativeModel(model_name)
    response = model.generate_content(prompt_text)
    return response.text
