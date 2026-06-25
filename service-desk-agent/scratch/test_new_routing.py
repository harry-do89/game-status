import os
import json
import sys

# Add scripts directory to path
sys.path.append(os.path.join(os.getcwd(), "scripts"))

import gemini
import utils

def test_triage_routing(summary, description, ticket_type="DevOps Support"):
    print(f"\n--- Testing: {summary} ---")
    prompt = utils.load_prompt("triage",
        ticket_type=ticket_type,
        game_name="N/A",
        environment="N/A",
        summary=summary,
        description=description,
        reporter="Test User"
    )
    
    response = gemini.ask(prompt)
    result = utils.parse_gemini_json(response)
    print(json.dumps(result, indent=2))
    return result

if __name__ == "__main__":
    # Test cases from user request
    test_triage_routing("Build staging for game A", "Please build staging environment.")
    test_triage_routing("build ex-staging", "Need build ex-staging for testing.")
    test_triage_routing("build server loadtest", "Loadtest build request.")
    
    # Test cases for DevOps keywords
    test_triage_routing("Jenkin pipeline issue", "Pipeline is failing.")
    test_triage_routing("Deployment request to UAT", "Deploy version 1.2.3 to UAT.")
    test_triage_routing("Preprod environment setup", "Need preprod env for final check.")
