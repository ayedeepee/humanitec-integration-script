## Import the needed libraries
import requests
from requests.auth import HTTPBasicAuth
from decouple import config
from loguru import logger
from typing import Any
import time
from datetime import datetime
import re


# Get environment variables using the config object or os.environ["KEY"]

PORT_CLIENT_ID = "Ex3GeM9hXjiYowHNkoWUxsMnP0ZXsMNm" #config("PORT_CLIENT_ID")
PORT_CLIENT_SECRET = "CZhDeIwEEvQhqiDD7r4DZ0ze2MlQ4jFT6QwzTnCSVaubYbcbRe18HnFwRIdVxOlZ" #config("PORT_CLIENT_SECRET")
PORT_API_URL = "https://api.getport.io/v1"

print("PORT_CLIENT_ID",PORT_CLIENT_ID)
print("PORT_CLIENT_SECRET",PORT_CLIENT_SECRET)
# Define your API token and base URL
HUMANITEC_API_TOKEN = "WLnM3EJm1bGMScqvuu2HH4YBB5FaNRlYUqkuc2C-RrDM"
BASE_URL = "https://api.humanitec.io"
HUMANITEC_ORG_ID = "port-testing"

## According to https://support.atlassian.com/bitbucket-cloud/docs/api-request-limits/
RATE_LIMIT = 1000  # Maximum number of requests allowed per hour
RATE_PERIOD = 3600  # Rate limit reset period in seconds (1 hour)

# Initialize rate limiting variables
request_count = 0
rate_limit_start = time.time()

## Get Port Access Token
credentials = {"clientId": PORT_CLIENT_ID, "clientSecret": PORT_CLIENT_SECRET}
token_response = requests.post(f"{PORT_API_URL}/auth/access_token", json=credentials)
access_token = token_response.json() #["accessToken"]
print(access_token)
access_token = access_token["accessToken"]

# You can now use the value in access_token when making further requests
port_headers = {"Authorization": f"Bearer {access_token}"}

# Define the headers including the Authorization token
headers = {"Authorization": f"Bearer {HUMANITEC_API_TOKEN}", "Content-Type": "application/json"}


def add_entity_to_port(blueprint_id, entity_object):
    response = requests.post(
        f"{PORT_API_URL}/blueprints/{blueprint_id}/entities?upsert=true&merge=true",
        json=entity_object,
        headers=port_headers,
    )
    logger.info(response.json())


def get_paginated_resource(
    path: str, params: dict[str, Any] = None, page_size: int = 25
):
    logger.info(f"Requesting data for {path}")

    global request_count, rate_limit_start

    # Check if we've exceeded the rate limit, and if so, wait until the reset period is over
    if request_count >= RATE_LIMIT:
        elapsed_time = time.time() - rate_limit_start
        if elapsed_time < RATE_PERIOD:
            sleep_time = RATE_PERIOD - elapsed_time
            time.sleep(sleep_time)

        # Reset the rate limiting variables
        request_count = 0
        rate_limit_start = time.time()

    params = params or {}
    """
    params["limit"] = page_size
    """
    next_page_start = None

    while True:
        try:
            """
            if next_page_start:
                params["start"] = next_page_start
            """
            # Define the endpoint for applications
            endpoint = f"{BASE_URL}/orgs/{HUMANITEC_ORG_ID}/{path}"
            # Make the GET request to the Humanitec API
            response = requests.get(endpoint, headers=headers, params=params)

            response.raise_for_status()
            page_json = response.json()
            request_count += 1
            """
            print(json.dumps(page_json, indent=2))
            batch_data = page_json["values"]
            """
            batch_data = page_json
            yield batch_data

            # Check for next page start in response
            """
            next_page_start = page_json.get("nextPageStart")
            """
            # Break the loop if there is no more data
            if not next_page_start:
                break
        except requests.exceptions.HTTPError as e:
            logger.error(
                f"HTTP error with code {e.response.status_code}, content: {e.response.text}"
            )
            raise
    logger.info(f"Successfully fetched paginated data for {path}")


def convert_to_datetime(timestamp: int):
    converted_datetime = datetime.utcfromtimestamp(timestamp / 1000.0)
    return converted_datetime.strftime("%Y-%m-%dT%H:%M:%SZ")

def remove_symbols_and_title_case(input_string: str) -> str:
    cleaned_string = re.sub(r'[^A-Za-z0-9\s]', '', input_string)
    title_case_string = cleaned_string.title()
    return title_case_string

def process_app_entities(apps_data: list[dict[str, Any]]):
    blueprint_id = "humanitecApplication"

    for app in apps_data:
        entity = {
            "identifier": app["id"],
            "title": remove_symbols_and_title_case(app["name"]),
            "properties": {
                "createdAt": app["created_at"]
            },
            "relations": {},
        }

        add_entity_to_port(blueprint_id=blueprint_id, entity_object=entity)


def process_environment_entities(environment_data: list[dict[str, Any]], app_id:str):
    blueprint_id = "humanitecEnvironment"

    for environment in environment_data:
        entity = {
            "identifier": environment["id"],
            "title": environment["name"],
            "properties": {
                "type": environment["type"],
                "createdAt": environment["created_at"],
                "lastDeploymentStatus": environment.get("last_deploy",{}).get("status"),
                "lastDeploymentDate": environment.get("last_deploy",{}).get("created_at"),
                "lastDeploymentComment": environment.get("last_deploy",{}).get("comment")
            },
            "relations": {
                "application": app_id
            },
        }
        add_entity_to_port(blueprint_id=blueprint_id, entity_object=entity)


def process_workload_profile_entities(workload_profile_data: list[dict[str, Any]]):
    blueprint_id = "humanitecWorkload"
    for workload_profile in workload_profile_data:
        print(workload_profile)
        entity = {
            "identifier": workload_profile["id"],
            "title": remove_symbols_and_title_case(workload_profile["id"]),
            "properties": {
                "description": workload_profile['description'],
                "workloadProfileVersion": workload_profile["version"],
                "createdAt": workload_profile["created_at"],
                "updatedAt": workload_profile["updated_at"],
                "version": workload_profile["version"],
            },
            "relations": {
                "application": []
            },
        }
        add_entity_to_port(blueprint_id=blueprint_id, entity_object=entity)


def process_workload_profile_version_entities(workload_profile_version_data: list[dict[str, Any]]):
    blueprint_id = "humanitecWorkloadVersion"
    # print("Workload Profile Data",workload_profile_version_data)

    for workload_profile_version in workload_profile_version_data:
        entity = {
            "identifier": workload_profile_version["id"],
            "title": workload_profile_version["name"],
            "properties": {},
            "relations": {
                "environment": "",
                "workload": workload_profile_version["workload_profile_id"]
            },
        }
        add_entity_to_port(blueprint_id=blueprint_id, entity_object=entity)


def get_workload_profiles():
    workfload_path = "workload-profiles"
    for workload_batch in get_paginated_resource(path=workfload_path):
        logger.info(f"received workload profiles batch with size {len(workload_batch)}")
        process_workload_profile_entities(workload_data=workload_batch)


def get_workload_profile_versions(workload_profile_id):
    workload_profile_version_path = f"workload-profiles/{workload_profile_id}/versions"
    for workload_profile_version_batch in get_paginated_resource(
        path=workload_profile_version_path
    ):
        logger.info(
            f"received workload profile versions batch with size len{workload_profile_version_batch} from {workload_profile_id}"
        )
        process_workload_profile_version_entities(
            workload_profile_version_data=workload_profile_version_batch
        )


def get_environments(app: dict[str, Any]):
    environments_path = f"apps/{app['id']}/envs"
    for environments_batch in get_paginated_resource(path=environments_path):
        logger.info(
            f"received environments batch with size {len(environments_batch)} from app: {app['name']}"
        )
        process_environment_entities(environment_data=environments_batch, app_id= app['id'])


if __name__ == "__main__":
    app_path = "apps"
    for apps_batch in get_paginated_resource(path=app_path):
        logger.info(f"received apps batch with size {len(apps_batch)}")
        process_app_entities(apps_data=apps_batch)

        for app in apps_batch:
            get_environments(app=app)

    workfload_path = "workload-profiles"
    for workload_batch in get_paginated_resource(path=workfload_path):
        logger.info(f"received workload profiles batch with size {len(workload_batch)}")
        process_workload_profile_entities(workload_profile_data = workload_batch)

        for workload_profile in workload_batch:
            get_workload_profile_versions(workload_profile_id=workload_profile["id"])
