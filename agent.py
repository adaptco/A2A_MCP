import os
import vertexai
from flask import Flask, request, jsonify
from langchain_core.tools import tool
from vertexai.preview.reasoning_engines import LangchainAgent

# --- Industry Data ---
INDUSTRY_DATA = {
    "Financial Services": {
        "description": "Solutions for banking, capital markets, and insurance to improve customer service, manage risk, and optimize operations.",
        "solutions": [
            {"name": "Retail Banking Solutions", "description": "Enhance customer experiences with personalized digital banking, fraud detection, and risk management."},
            {"name": "Capital Markets Solutions", "description": "Utilize high-performance computing for risk analysis, trade processing, and regulatory compliance."},
            {"name": "Insurance Solutions", "description": "Modernize policy administration, automate claims processing, and leverage data for underwriting."},
        ],
    },
    "Healthcare and Life Sciences": {
        "description": "Tools for healthcare providers, pharmaceutical companies, and researchers to accelerate research, improve patient care, and manage data.",
        "solutions": [
            {"name": "Clinical and Operational Tools", "description": "Improve patient outcomes with AI-powered diagnostics, data interoperability, and telehealth solutions."},
            {"name": "Drug Discovery and Development", "description": "Accelerate research with large-scale data analysis, genomics processing, and AI for drug discovery."},
            {"name": "Medical Imaging Solutions", "description": "Enhance diagnostic accuracy with AI-powered medical imaging analysis and storage solutions."},
        ],
    },
    "Retail": {
        "description": "Solutions to help retailers create personalized customer experiences, optimize supply chains, and improve e-commerce operations.",
        "solutions": [
            {"name": "E-commerce and Marketing", "description": "Increase sales with personalized recommendations, AI-powered search, and targeted marketing campaigns."},
            {"name": "Supply Chain and Logistics", "description": "Optimize inventory management, improve demand forecasting, and streamline logistics with data analytics."},
            {"name": "In-store Experience", "description": "Enhance the brick-and-mortar experience with smart shelves, contactless checkout, and personalized promotions."},
        ],
    },
    "Manufacturing": {
        "description": "Solutions for the manufacturing industry to improve operational efficiency, product quality, and supply chain visibility.",
        "solutions": [
            {"name": "Smart Factory and Operations", "description": "Optimize production with AI-powered quality control, predictive maintenance, and real-time monitoring."},
            {"name": "Supply Chain and Logistics", "description": "Increase visibility and resilience with supply chain twins, demand forecasting, and logistics optimization."},
            {"name": "Product Design and Engineering", "description": "Accelerate product development with collaborative design tools, simulation, and high-performance computing."},
        ]
    }
}

# --- Tool Definition ---
@tool
def get_industry_info(industry_name: str) -> dict:
    """
    Retrieves Google Cloud solutions for a given industry.

    Args:
        industry_name: The name of the industry to look up.
                       Must be one of: Financial Services, Healthcare and Life Sciences, Retail, Manufacturing.

    Returns:
        A dictionary containing the description and solutions for the industry,
        or an error message if the industry is not found.
    """
    return INDUSTRY_DATA.get(
        industry_name,
        {"error": f"Industry '{industry_name}' not found. Please choose from the available industries."}
    )

# --- Agent Definition ---
def create_agent():
    """Creates and returns the Google Cloud Solution Discovery Agent."""
    project_id = os.environ.get("GCP_PROJECT")
    location = os.environ.get("GCP_LOCATION", "us-central1")
    
    # Initialize Vertex AI
    vertexai.init(project=project_id, location=location)

    # Define the agent
    agent = LangchainAgent(
        model="gemini-1.0-pro",  # Or your preferred model
        tools=[get_industry_info],
        system_instructions=[
            "You are the Google Cloud Solution Discovery Agent.",
            "Your goal is to help users find the right Google Cloud solutions for their industry.",
            "Start by asking the user which industry they are interested in.",
            "Once the user specifies an industry, use the available tool to get information about it.",
            "Present the solutions to the user in a clear and helpful manner."
        ]
    )
    return agent

# --- Web Server for Render ---
app = Flask(__name__)
agent_instance = None

@app.route('/query', methods=['POST'])
def query():
    global agent_instance
    try:
        if not agent_instance:
            agent_instance = create_agent()

        data = request.get_json()
        user_input = data.get('input')
        
        if not user_input:
            return jsonify({"error": "Missing 'input' in request body"}), 400

        response = agent_instance.query(input=user_input)
        return jsonify({"response": response})

    except Exception as e:
        return jsonify({"error": str(e)}), 500

if __name__ == '__main__':
    # Run locally
    app.run(host='0.0.0.0', port=8080, debug=True)
