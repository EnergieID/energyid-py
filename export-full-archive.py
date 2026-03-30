import requests
import os
from datetime import datetime
from dotenv import load_dotenv

# configuration
BASE_API_URL = "https://api.energyid.eu"
load_dotenv()
# The specific member ID for the export, member ID and API key must match the same user!
MEMBER_ID = "9d69301d-4cc5-49f7-bea6-4bd6daaec7d6"
API_KEY = os.getenv("API_KEY")


def generate_and_download_archive(member_id: str, api_key: str):
    """
    (SYNCHRONOUS METHOD)
    Connects to the EnergieID Web API to request and download a member's data archive in a single step.
    Authenticates using the custom "apiKey" authorization scheme.
    """
    endpoint_url = f"{BASE_API_URL}/api/v1/export/members/{member_id}/archive"
    headers = {"Authorization": f"apiKey {api_key}"}
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    output_filename = f"energieid_archive_{member_id}_{timestamp}.zip"

    print(f"▶️  (SYNC) Requesting archive for member: {member_id}")
    print(f"    Endpoint: GET {endpoint_url}")

    try:
        with requests.get(endpoint_url, headers=headers, stream=True) as response:
            response.raise_for_status()

            print(
                f"✅ (SYNC) SUCCESS: Status {response.status_code}. Downloading to '{output_filename}'..."
            )
            with open(output_filename, "wb") as f:
                for chunk in response.iter_content(chunk_size=8192):
                    f.write(chunk)
            print("✅ (SYNC) DONE: Archive saved successfully.")

    except requests.exceptions.Timeout:
        print(
            "❌ (SYNC) FAILURE: The request timed out from our end (after 300 seconds)."
        )
        print("     - This confirms the server is taking too long to respond.")
    except requests.exceptions.HTTPError as e:
        print("❌ (SYNC) FAILURE: An HTTP error occurred.")
        print(f"     - Status Code: {e.response.status_code}")
        if e.response.status_code == 500:
            print(
                "     - REASON: 500 Internal Server Error. This is a problem on the EnergieID server, likely a timeout on their end."
            )
        try:
            print(f"     - API Error Details: {e.response.json()}")
        except ValueError:
            print(f"     - Response Body: {e.response.text}")
    except requests.exceptions.RequestException as e:
        print(f"❌ (SYNC) FAILURE: A network or connection error occurred: {e}")


if __name__ == "__main__":
    generate_and_download_archive(MEMBER_ID, API_KEY)
