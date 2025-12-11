# I14Y_API_handling.py
# This script handles API calls to the i14y service for managing codelists and concepts

import requests
import logging
import os
import json
import enum
import sys
import glob
import certifi
import datetime
import time
import re
from pathlib import Path
from typing import Optional, Dict, Any, Union
from dotenv import load_dotenv
from urllib.parse import urlencode

# Load environment variables: CAVE override is important for PROD / ABN switch via .env file
load_dotenv(override=True)

class Config:
    """Configuration class to handle all environment variables with enhanced debugging"""
    
    # Debug: Check what's actually in the environment
    #print("🔍 Environment variable debug:")
    #print(f"API_MODE from os.getenv(): '{os.getenv('API_MODE')}'")
    #print(f"API_MODE from os.environ: '{os.environ.get('API_MODE', 'NOT_SET')}'")
    
    # Check if there are any shell environment variables overriding .env
    shell_api_mode = os.environ.get('API_MODE')
    dotenv_api_mode = None
    
    # Try to read .env file directly to compare
    try:
        with open('.env', 'r') as f:
            for line in f:
                if line.strip().startswith('API_MODE=') and not line.strip().startswith('#'):
                    dotenv_api_mode = line.split('=', 1)[1].strip()
                    break
        #print(f".env file contains: API_MODE={dotenv_api_mode}")
        #print(f"Shell environment: API_MODE={shell_api_mode}")
        
        if shell_api_mode and shell_api_mode != dotenv_api_mode:
            print("⚠️  WARNING: Shell environment variable is overriding .env file!")
            print(f"   Shell: {shell_api_mode}")
            print(f"   .env:  {dotenv_api_mode}")
    except FileNotFoundError:
        print("❌ .env file not found in current directory")
    except Exception as e:
        print(f"❌ Error reading .env file: {e}")
    
    API_MODE = os.getenv("API_MODE", "ABN")  # Default to ABN if not set
    
    #print(f"🎯 Final API_MODE value: '{API_MODE}'")

    # Production credentials
    PROD_CLIENT_ID = os.getenv("PROD_CLIENT_ID")
    PROD_CLIENT_SECRET = os.getenv("PROD_CLIENT_SECRET")
    PROD_TOKEN_URL = os.getenv("PROD_TOKEN_URL")
    PROD_BASE_API_URL = os.getenv("PROD_BASE_API_URL")

    # ABN credentials  
    ABN_CLIENT_ID = os.getenv("ABN_CLIENT_ID")
    ABN_CLIENT_SECRET = os.getenv("ABN_CLIENT_SECRET")
    ABN_TOKEN_URL = os.getenv("ABN_TOKEN_URL")
    ABN_BASE_API_URL = os.getenv("ABN_BASE_API_URL")
    
    # Publisher information
    PUBLISHER_IDENTIFIER = os.getenv('PUBLISHER_IDENTIFIER', 'CH_eHealth')
    PUBLISHER_NAME = os.getenv('PUBLISHER_NAME', 'eHealth Suisse')

    # Set the active configuration based on API_MODE
    if API_MODE == 'PROD':
        CLIENT_ID = PROD_CLIENT_ID
        CLIENT_SECRET = PROD_CLIENT_SECRET
        TOKEN_URL = PROD_TOKEN_URL
        BASE_API_URL = PROD_BASE_API_URL
        print(f"🔴 USING PRODUCTION ENVIRONMENT")
        #print(f"   Client ID: {CLIENT_ID}")
        print(f"   Base URL: {BASE_API_URL}")
    else:  # Default to ABN
        CLIENT_ID = ABN_CLIENT_ID
        CLIENT_SECRET = ABN_CLIENT_SECRET
        TOKEN_URL = ABN_TOKEN_URL
        BASE_API_URL = ABN_BASE_API_URL
        print(f"🟡 USING ABN ENVIRONMENT")
        #print(f"   Client ID: {CLIENT_ID}")
        print(f"   Base URL: {BASE_API_URL}")

    # Validate that we have the required credentials
    if not all([CLIENT_ID, CLIENT_SECRET, TOKEN_URL, BASE_API_URL]):
        missing = []
        if not CLIENT_ID: missing.append("CLIENT_ID")
        if not CLIENT_SECRET: missing.append("CLIENT_SECRET") 
        if not TOKEN_URL: missing.append("TOKEN_URL")
        if not BASE_API_URL: missing.append("BASE_API_URL")
        
        print(f"❌ Missing environment variables: {missing}")
        raise ValueError(f"Missing required environment variables for {API_MODE} mode: {missing}")
    #else:
        #print("✅ All required environment variables are set")

    # Set CONCEPT_POST_URL after BASE_API_URL is properly set
    CONCEPT_POST_URL = f"{BASE_API_URL}/concepts"
    
    @classmethod
    def print_config(cls):
        """Print current configuration (without secrets)"""
        print("")
        print("="*50)
        print("CURRENT CONFIGURATION:")
        print(f"API Mode: {cls.API_MODE}")
        print(f"Base URL: {cls.BASE_API_URL}")
        print(f"Token URL: {cls.TOKEN_URL}")
        print(f"Publisher: {cls.PUBLISHER_IDENTIFIER}")
        print(f"Client ID: {cls.CLIENT_ID}")
        print("="*50)
        print("")
        
# Setting up logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

class I14yApiError(Exception):
    """Custom exception for I14Y API errors"""
    def __init__(self, message: str, status_code: Optional[int] = None, response_text: Optional[str] = None):
        self.message = message
        self.status_code = status_code
        self.response_text = response_text
        super().__init__(self.message)

'''
ToDo: Implemented PROD / ABN switch
def set_env(prod_or_abn_env: Optional[str] = None):

    if prod_or_abn_env == 'ABN':    
        Config.CLIENT_ID = os.getenv("ABN_CLIENT_ID")
        Config.CLIENT_SECRET = os.getenv("ABN_CLIENT_SECRET")
        Config.TOKEN_URL = os.getenv("ABN_TOKEN_URL")
        Config.BASE_API_URL = os.getenv("ABN_BASE_API_URL")
    elif prod_or_abn_env == 'PROD':            
        Config.CLIENT_ID = os.getenv("PROD_CLIENT_ID")
        Config.CLIENT_SECRET = os.getenv("PROD_CLIENT_SECRET")
        Config.TOKEN_URL = os.getenv("PROD_TOKEN_URL")
        Config.BASE_API_URL = os.getenv("PROD_BASE_API_URL")
    else:
        logging.error("prod_or_abn_env must be either 'PROD' or 'ABN'")
        sys.exit(1)

    logging.info(f"Using environment: {prod_or_abn_env}")
'''

class CodelistManager:
    def __init__(self, mapping_file: str = None):

        self.api_client = I14yApiClient()
        self.mapping_file = Path(mapping_file)
        self.mapping = self._load_mapping()
        self.cache: Dict[str, str] = {}
        
    def _load_mapping(self) -> Dict[str, Any]:
        """Load the filename to API identifier mapping, create file if missing"""
        if not self.mapping_file.exists():
            # Create file with empty dict
            self.mapping_file.parent.mkdir(parents=True, exist_ok=True)
            with open(self.mapping_file, 'w', encoding='utf-8') as f:
                json.dump({}, f, indent=2)

        """Load the filename to API identifier mapping"""
        with open(self.mapping_file, 'r', encoding='utf-8') as f:
            return json.load(f)
    
    def get_codelist_id(self, filename: str) -> Optional[str]:
        """Get codelist ID from filename, either from cache or API"""
        base_filename = os.path.splitext(os.path.basename(filename))[0]
        
        # Remove '_transformed' suffix if present
        if base_filename.endswith('_transformed'):
            base_filename = base_filename[:-len('_transformed')]
            
        # Check if we have a mapping for this filename
        if base_filename not in self.mapping['concepts']:
            return None
        
        mapping_info = self.mapping['concepts'][base_filename]

        # Try to get from API first
        #api_id = self._get_from_api(mapping_info.get('api_identifier'))
        #if api_id:
        #    return api_id

        #print(mapping_info.get('api_identifier'))
        #sys.exit(0)
        
        # Fall back to hardcoded ID if API fails
        return mapping_info.get('api_identifier')
    
    def _get_from_api(self, identifier: Optional[str]) -> Optional[str]:
        """Get codelist ID from API using the identifier"""
        if not identifier:
            return None
            
        # Check cache first
        if identifier in self.cache:
            return self.cache[identifier]
            
        # Call your existing API method
        api_client = I14yApiClient()

        concepts = api_client.get_concepts(
            publisher_identifier=Config.PUBLISHER_IDENTIFIER,
            save_to_file=None  # Don't save to file for this lookup
        )

        if concepts and concepts.get('data'):
            # Assuming the first result is what we want
            concepts = concepts['data'][0]
            return concepts
            
        return None
    
    def refresh_cache(self):
        """Clear the cache to force fresh API lookups"""
        self.cache.clear()
    
    def update_mapping_from_api(self) -> bool:
        """Update the mapping file with current data from API, handling Unicode properly"""
        try:
            # Get all EPD concepts from API
            concepts = self.api_client.get_epd_concepts()

            if not concepts or 'data' not in concepts:
                logging.warning("No concepts data received from API")
                return False
            
            # Build new mapping with proper Unicode handling
            new_mapping = {
                "concepts": {}, 
                "last_updated": datetime.datetime.now().isoformat(),
                "metadata": {
                    "source": "I14Y API",
                    "version": "1.0"
                }
            }
            
            for concept in concepts['data']:

                try:
                    # Use German name as key, fallback to English if German not available
                    name = concept['name'].get('de') or concept['name'].get('en')

                    if not name:
                        logging.warning(f"Concept {concept.get('id')} has no name in DE or EN")
                        continue

                    # Create entry with all relevant information
                    new_mapping['concepts'][name] = {
                        'oid': concept['identifier'],
                        'api_identifier': concept['id'],
                        'concept_type': concept.get('conceptType'),
                        'version': concept.get('version'),
                        'status': concept.get('registrationStatus'),
                        'validFrom': concept.get('validFrom'),
                    }

                except KeyError as ke:
                    logging.warning(f"Missing expected field in concept: {ke}")
                    continue
            
            # Save with ensure_ascii=False to preserve Unicode characters
            with open(self.mapping_file, 'w', encoding='utf-8') as f:
                json.dump(new_mapping, f, indent=2)
            
            self.mapping = new_mapping
            logging.info(f"Successfully updated mapping with {len(new_mapping['concepts'])} concepts: {self.mapping_file}")
            return True
            
        except json.JSONDecodeError as je:
            logging.error(f"JSON processing error: {str(je)}")
            return False
        except IOError as ioe:
            logging.error(f"File operation error: {str(ioe)}")
            return False
        except Exception as e:
            logging.error(f"Unexpected error updating mapping: {str(e)}", exc_info=True)
            return False


class I14yApiClient:
    """Main API client for i14y service"""

    def __init__(self, directory_path: Optional[str] = None):
        self.directory_path = directory_path
        self.auth_token = None
        self.token_expiry = 0
        self._get_access_token()

    def _get_access_token(self) -> str:
        """Get or refresh access token"""
        if self.auth_token and time.time() < self.token_expiry:
            return self.auth_token

        try:
            logging.info(f"🔐 Attempting authentication to: {Config.TOKEN_URL}")
            logging.info(f"🔐 Using CLIENT_ID: {Config.CLIENT_ID}")
            logging.info(f"🔐 CLIENT_SECRET length: {len(Config.CLIENT_SECRET) if Config.CLIENT_SECRET else 0} characters")
            
            response = requests.post(
                Config.TOKEN_URL,
                data={'grant_type': 'client_credentials'},
                auth=(Config.CLIENT_ID, Config.CLIENT_SECRET),
                headers={'Content-Type': 'application/x-www-form-urlencoded'},
                verify=certifi.where()
            )
            response.raise_for_status()
            
            data = response.json()
            token = data.get("access_token")
            expires_in = data.get("expires_in", 3600)
            
            self.auth_token = f"Bearer {token}"
            logging.info(f"<token_start>Bearer {token}<token_end>")
            self.token_expiry = time.time() + expires_in - 60  # refresh 1 min early
            
            logging.info("✅ Access token obtained successfully")
            return self.auth_token
            
        except requests.exceptions.HTTPError as e:
            error_msg = f"Authentication failed with status {e.response.status_code}"
            if e.response.status_code == 401:
                error_msg += "\n❌ 401 Unauthorized: Check your CLIENT_ID and CLIENT_SECRET in .env file"
                error_msg += f"\n   Current CLIENT_ID: {Config.CLIENT_ID}"
                error_msg += f"\n   CLIENT_SECRET length: {len(Config.CLIENT_SECRET) if Config.CLIENT_SECRET else 0}"
                error_msg += "\n   Make sure .env file is in the project root and properly formatted"
            logging.error(error_msg)
            raise I14yApiError(error_msg)
        except Exception as e:
            logging.error(f"Failed to obtain access token: {e}")
            raise I14yApiError(f"Authentication failed: {e}")

    def _make_request(self, 
                     method: str, 
                     url: str, 
                     headers: Optional[Dict[str, str]] = None,
                     json_data: Optional[Dict[str, Any]] = None,
                     files: Optional[Dict[str, Any]] = None,
                     operation_name: str = "API request") -> Optional[Dict[str, Any]]:
        """
        Unified method for making HTTP requests with consistent error handling
        
        Args:
            method: HTTP method (GET, POST, DELETE, etc.)
            url: Request URL
            headers: Request headers
            json_data: JSON payload for POST requests
            files: Files for multipart requests
            operation_name: Description of the operation for logging
            
        Returns:
            Response JSON data or None if request failed
        """
        # Ensure we have a valid token
        self._get_access_token()
        
        # Set default headers
        default_headers = {
            'Authorization': self.auth_token,
            'accept': '*/*'
        }
        
        if headers:
            default_headers.update(headers)

        try:
            logging.info(f"{operation_name}: {method} {url}")
            
            # Make the request
            response = requests.request(
                method=method,
                url=url,
                headers=default_headers,
                json=json_data,
                files=files,
                verify=certifi.where()
            )
            
            response.raise_for_status()
            logging.info(f"{operation_name} completed successfully")
            
            # Return JSON response if available
            try:
                return response.json()
            except ValueError:
                # Response might not be JSON
                return {"status": "success", "message": f"{operation_name} completed"}
                
        except requests.exceptions.RequestException as e:
            self._handle_request_error(e, operation_name)
            return None

    def _handle_request_error(self, exception: requests.exceptions.RequestException, operation_name: str):
        """
        Unified error handling for all API requests
        
        Args:
            exception: The request exception that occurred
            operation_name: Description of the failed operation
        """
        status_code = exception.response.status_code if exception.response else "No status code"
        error_text = exception.response.text if exception.response else "No response text"

        # Try to parse JSON error response
        try:
            error_json = exception.response.json()
            detail = error_json.get("detail", "No detail provided.")
            title = error_json.get("title", "")
        except Exception:
            detail = error_text
            title = ""

        # Provide user-friendly hints for common errors
        user_hint = self._get_error_hint(detail)

        print("")
        print("-"*50)
        print("START ERROR")
        print("-"*50)
        # Display clean error summary
        print(f"\n❌ {operation_name} failed with status code '{status_code}': {title}\n")
        print(f"Reason: {detail.strip()}")
        if user_hint:
            print(user_hint)
        print("More technical details are written to 'api_errors_log.txt'\n")
        print("-"*50)
        print("END ERROR")
        print("-"*50)
        print("")

        # Log detailed error information
        self._log_detailed_error(exception, operation_name)

    def _get_error_hint(self, detail: str) -> str:
        """Get user-friendly hints based on error details"""
        if "already exists" in detail.lower():
            return ("\nHint: The concept you're trying to post already exists on the server.\n"
                   "Consider using the '-dcl' (delete_CodelistEntries) method before re-posting or delete the concept using '-dc' .\n")
        elif "not found" in detail.lower():
            return "\nHint: The requested resource was not found. Please check the concept ID.\n"
        elif "unauthorized" in detail.lower():
            return "\nHint: Authentication failed. Please check your credentials.\n"
        elif "forbidden" in detail.lower():
            return "\nHint: Access denied. You may not have permission for this operation.\n"
        elif "internal server error" in detail.lower():
            return ("\nHint: The server encountered an error processing your request.\n"
                   "Common causes:\n"
                   "  - Invalid data format (e.g., sending concept metadata instead of codelist entries)\n"
                   "  - The concept doesn't exist yet (create it first with -pc)\n"
                   "  - Data validation failed on the server side\n")
        return ""

    def _log_detailed_error(self, exception: requests.exceptions.RequestException, operation_name: str):
        """Log detailed error information to file with improved formatting"""
        
        # Format request body nicely
        request_body = "N/A"
        if exception.request and exception.request.body:
            try:
                if isinstance(exception.request.body, bytes):
                    # Try to decode bytes to string first
                    body_str = exception.request.body.decode('utf-8')
                    # Try to parse as JSON and format it nicely
                    body_json = json.loads(body_str)
                    request_body = json.dumps(body_json, indent=2, ensure_ascii=False)
                elif isinstance(exception.request.body, str):
                    # Try to parse string as JSON and format it
                    body_json = json.loads(exception.request.body)
                    request_body = json.dumps(body_json, indent=2, ensure_ascii=False)
                else:
                    request_body = str(exception.request.body)
            except (json.JSONDecodeError, UnicodeDecodeError, AttributeError):
                # If JSON parsing fails, just convert to string
                request_body = str(exception.request.body)
                # Truncate if too long for readability
                if len(request_body) > 5000:
                    request_body = request_body[:5000] + "\n... [TRUNCATED - body too long]"
        
        # Format response body nicely too
        response_body = "No response text"
        if exception.response and exception.response.text:
            try:
                response_json = json.loads(exception.response.text)
                response_body = json.dumps(response_json, indent=2, ensure_ascii=False)
            except json.JSONDecodeError:
                response_body = exception.response.text

        error_message = f"""
    {'='*80}
    {operation_name.upper()} ERROR - {datetime.datetime.now()}
    {'='*80}

    STATUS CODE: {exception.response.status_code if exception.response else 'No status code'}

    REQUEST DETAILS:
    - Method: {exception.request.method if exception.request else 'N/A'}
    - URL: {exception.request.url if exception.request else 'N/A'}

    REQUEST HEADERS:
    {json.dumps(dict(exception.request.headers), indent=2) if exception.request else 'N/A'}

    REQUEST BODY:
    {request_body}

    RESPONSE HEADERS:
    {json.dumps(dict(exception.response.headers), indent=2) if exception.response else 'No headers'}

    RESPONSE BODY:
    {response_body}

    EXCEPTION DETAILS:
    {str(exception)}

    {'='*80}

    """

        log_path = "api_errors_log.txt"
        # No need to create directories for root level file
        
        with open(log_path, 'a', encoding='utf-8') as f:
            f.write(error_message)

    def _validate_file_exists(self, file_path: str) -> bool:
        """Validate that a file exists"""
        if not os.path.isfile(file_path):
            logging.error(f"File not found: {file_path}")
            return False
        return True

    def post_codelist_entries(self, file_path: str, concept_id: str) -> Optional[Dict[str, Any]]:
        """
        Post codelist entries from a JSON file
        
        IMPORTANT: This endpoint expects ONLY codelist entries, not concept metadata.
        The file should contain an array of entries like:
        {
          "data": [
            {
              "code": "1051",
              "name": {
                "de": "Name in German",
                "en": "Name in English",
                ...
              }
            },
            ...
          ]
        }
        
        Do NOT send the full concept definition (with identifier, publisher, etc.)
        """
        if not self._validate_file_exists(file_path):
            return None

        url = f"{Config.BASE_API_URL}/concepts/{concept_id}/codelist-entries/imports/json"
        
        with open(file_path, 'rb') as file:
            files = {'file': (os.path.basename(file_path), file, 'application/json')}
            return self._make_request(
                method='POST',
                url=url,
                files=files,
                operation_name=f"Posting codelist entries for concept {concept_id}"
            )

    def get_codelist_entry(self, concept_id: str, save_to_file: str) -> Optional[Dict[str, Any]]:
        """Get codelist entry (needs to be connected with save_data_to_file)"""

        url = f"{Config.BASE_API_URL}/concepts/{concept_id}/codelist-entries/exports/json"

        result = self._make_request(
            method='GET',
            url=url,
            operation_name="Fetching codelist entry"
        )

        logging.info(f"Found {len(result.get('data', []))} codelists")
    
        return self.save_response_to_file(result, save_to_file)
    
    def delete_concept(self, concept_id: str) -> Optional[Dict[str, Any]]:
        """CAVE: Deletes a concept"""
        url = f"{Config.BASE_API_URL}/concepts/{concept_id}/"
        return self._make_request(
            method='DELETE',
            url=url,
            operation_name=f"Deleting a concept {concept_id}"
        )

    def delete_codelist_entries(self, concept_id: str) -> Optional[Dict[str, Any]]:
        """Delete all codelist entries for a concept"""
        url = f"{Config.BASE_API_URL}/concepts/{concept_id}/codelist-entries"
        return self._make_request(
            method='DELETE',
            url=url,
            operation_name=f"Deleting codelist entries for concept {concept_id}"
        )
    
    def set_publication_level(self, publication_level: str, concept_id: str) -> Optional[Dict[str, Any]]:
        """Set the publication level of a concept"""
        url = f"{Config.BASE_API_URL}/concepts/{concept_id}/publication-level-proposal?proposal={publication_level}"
        return self._make_request(
            method="PUT",
            url=url,
            operation_name=f"Set publication level for concept {concept_id}"
        )

    
    def set_registration_status(self, registration_status: str, concept_id: str) -> Optional[Dict[str, Any]]:
            """Delete all codelist entries for a concept"""
            
            url = f"{Config.BASE_API_URL}/concepts/{concept_id}/registration-status-proposal?proposal={registration_status}"
            return self._make_request(
                method='PUT',
                url=url,
                operation_name=f"Set registration status for concept {concept_id}"
            )

    def update_codelist_entries(self, file_path: str, concept_id: str) -> bool:
        """Update codelist entries by deleting existing ones and posting new ones"""
        logging.info(f"Updating codelist entries for concept {concept_id}")
        
        # Delete existing entries
        delete_result = self.delete_codelist_entries(concept_id)

        if delete_result is None:
            logging.error("Failed to delete existing entries")
            return False
        
        # Post new entries
        post_result = self.post_codelist_entries(file_path, concept_id)

        return post_result is not None

    def post_new_concept(self, file_path: str) -> Optional[Dict[str, Any]]:
        """Post a new concept from a JSON file"""
        if not self._validate_file_exists(file_path):
            return None

        try:
            with open(file_path, 'r', encoding='utf-8') as file:
                payload = json.load(file)
        except json.JSONDecodeError as e:
            logging.error(f"Invalid JSON in file {file_path}: {e}")
            return None

        headers = {'Content-Type': 'application/json', 'Accept': 'application/json'}
        
        response = self._make_request(
            method='POST',
            url=Config.CONCEPT_POST_URL,  # Changed: removed the UUID suffix
            headers=headers,
            json_data=payload,
            operation_name=f"Posting new concept from {file_path}"
        )
        
        # If successful, rename the corresponding codelist file with the new UUID
        # The API returns the new UUID directly as a string (e.g., "bdc10a38-45d3-46c4-92d0-4ba1f6a16018")
        if response:
            new_uuid = None
            
            # Handle different response formats
            if isinstance(response, str):
                new_uuid = response.strip('"')  # Remove quotes if present
            elif isinstance(response, dict):
                # Try to find UUID in nested structure
                if 'data' in response and 'id' in response['data']:
                    new_uuid = response['data']['id']
                elif 'id' in response:
                    new_uuid = response['id']
            
            if new_uuid:
                self._rename_codelist_with_new_uuid(file_path, new_uuid)
        
        return response
    
    def _rename_codelist_with_new_uuid(self, concept_file_path: str, new_uuid: str):
        """
        Rename the corresponding codelist file with the new UUID returned from the API.
        
        Args:
            concept_file_path: Path to the concept file that was just posted
            new_uuid: The new UUID returned by the API
        """
        # Extract the old UUID from the concept filename
        old_uuid = self.extract_identifier_from_filename(os.path.basename(concept_file_path))
        if not old_uuid:
            logging.warning(f"Could not extract UUID from concept filename: {concept_file_path}")
            return
        
        # Extract the concept name (everything before the first UUID)
        concept_filename = os.path.basename(concept_file_path)
        concept_name_match = re.match(r'^(.+?)_[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}', concept_filename, re.IGNORECASE)
        if not concept_name_match:
            logging.warning(f"Could not extract concept name from filename: {concept_file_path}")
            return
        
        concept_name = concept_name_match.group(1)
        
        # Determine the codelist directory
        # Check if concept is in AD_VS/Transformed/Concepts structure
        concept_dir = os.path.dirname(concept_file_path)
        
        # Try to find the Codelists directory in several locations
        possible_codelist_dirs = []
        
        # 1. Sibling to Concepts directory (AD_VS/Transformed/Codelists)
        if 'Concepts' in concept_dir:
            possible_codelist_dirs.append(os.path.join(os.path.dirname(concept_dir), 'Codelists'))
        
        # 2. Same directory as concept (for uploads/ or other locations)
        possible_codelist_dirs.append(os.path.join(concept_dir, '../AD_VS/Transformed/Codelists'))
        
        # 3. Relative to project root
        project_root = os.path.dirname(os.path.abspath(__file__))
        possible_codelist_dirs.append(os.path.join(project_root, 'AD_VS/Transformed/Codelists'))
        
        # Find the first existing directory
        codelist_dir = None
        for dir_path in possible_codelist_dirs:
            normalized_path = os.path.normpath(os.path.abspath(dir_path))
            if os.path.exists(normalized_path):
                codelist_dir = normalized_path
                break
        
        if not codelist_dir:
            logging.info(f"Codelist directory not found. Searched in: {[os.path.normpath(os.path.abspath(d)) for d in possible_codelist_dirs]}")
            return
        
        # Find the codelist file with the old UUID
        for filename in os.listdir(codelist_dir):
            if filename.startswith(concept_name) and old_uuid in filename:
                old_codelist_path = os.path.join(codelist_dir, filename)
                new_codelist_filename = filename.replace(old_uuid, new_uuid)
                new_codelist_path = os.path.join(codelist_dir, new_codelist_filename)
                
                try:
                    os.rename(old_codelist_path, new_codelist_path)
                    logging.info(f"✅ Renamed codelist file:")
                    logging.info(f"   Old: {filename}")
                    logging.info(f"   New: {new_codelist_filename}")
                    print(f"\n✅ Codelist file renamed with new UUID:")
                    print(f"   {new_codelist_filename}\n")
                except Exception as e:
                    logging.error(f"Failed to rename codelist file: {e}")
                
                break
    
    @staticmethod
    def extract_identifier_from_filename(filename):
        """
        Extract identifier from filename.
        
        Expected format: ConceptName_identifier_transformed.json
        Example: HCProfessional.hcProfession_08dd632d-b3c5-ed64-a995-369c44b38c06_transformed.json
        
        Returns the UUID if found, None otherwise.
        """
        # Pattern to match UUID format: 8-4-4-4-12 hexadecimal characters
        uuid_pattern = r'([0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12})'
        
        match = re.search(uuid_pattern, filename, re.IGNORECASE)
        if match:
            return match.group(1)
        return None

    def post_multiple_new_codelists(self, directory_path: str):
        """Post multiple codelist files from a directory"""
        json_files = glob.glob(os.path.join(directory_path, "*_transformed.json"))
        
        if not json_files:
            logging.warning(f"No *_transformed.json files found in {directory_path}")
            return
        
        logging.info(f"Found {len(json_files)} files to process")
        
        for json_file in json_files:
            logging.info(f"Processing file: {json_file}")
            
            # Extract identifier from filename
            filename = os.path.basename(json_file)
            identifier = self.extract_identifier_from_filename(filename)

            if identifier:
                logging.info(f"Posting {json_file} with identifier: {identifier}")
                self.update_codelist_entries(json_file, identifier)
            else:
                logging.info(f"No matching identifier found for {json_file}")

    def post_multiple_concepts(self, directory_path: str):
        """Post multiple concept files from a directory"""
        json_files = glob.glob(os.path.join(directory_path, "*.json"))
        
        if not json_files:
            logging.warning(f"No JSON files found in {directory_path}")
            return

        logging.info(f"Found {len(json_files)} concept files to process")

        for json_file in json_files:
            logging.info(f"Posting concept file: {json_file}")
            self.post_new_concept(json_file)

    @staticmethod
    def save_response_to_file(data: Dict[str, Any], file_path: str):
        """Save API response data to a JSON file"""
        try:
            dir_path = os.path.dirname(file_path)
            if dir_path:  # Only create if not empty
                os.makedirs(dir_path, exist_ok=True)

            with open(file_path, 'w', encoding='utf-8') as file:
                json.dump(data, file, indent=4, ensure_ascii=False)
            logging.info(f"Data has been written to {file_path}")
        except Exception as e:
            logging.error(f"Failed to write data to file: {e}")

    def get_concepts(self, 
                    concept_identifier: Optional[str] = None,
                    publisher_identifier: Optional[str] = None,
                    version: Optional[str] = None,
                    publication_level: Optional[str] = None,
                    registration_status: Optional[str] = None,
                    page: Optional[int] = None,
                    page_size: Optional[int] = 9999,
                    save_to_file: Optional[str] = None) -> Optional[Dict[str, Any]]:
        """
        Get concepts matching the given filters
        
        Args:
            concept_identifier: Filter by specific concept identifier
            publisher_identifier: Filter by publisher
            version: Filter by version
            publication_level: Filter by publication level ("Internal" or "Public")
            registration_status: Filter by status ("Incomplete", "Candidate", "Recorded", 
                            "Qualified", "Standard", "Preferred", "Standard", "Superseded", "Retired")
            page: Page number for pagination
            page_size: Maximum number of results per page
            save_to_file: Optional file path to save the response JSON
            
        Returns:
            Response JSON data or None if request failed
        """

        # Build query parameters
        params = {}

        if concept_identifier:
            params['conceptIdentifier'] = concept_identifier
        if publisher_identifier:
            params['publisherIdentifier'] = publisher_identifier
        if version:
            params['version'] = version
        if publication_level:
            params['publicationLevel'] = publication_level
        if registration_status:
            params['registrationStatus'] = registration_status
        if page is not None:
            params['page'] = page
        if page_size is not None:
            params['pageSize'] = page_size

        # Build URL with query parameters
        query_string = urlencode(params)
        url = f"{Config.BASE_API_URL}/concepts"
        if query_string:
            url += f"?{query_string}"

        # Make the request
        result = self._make_request(
            method='GET',
            url=url,
            operation_name=f"Getting concepts with filters: {params}"
        )

        # Save to file if requested
        if result and save_to_file:
            self.save_response_to_file(result, save_to_file)
        
        logging.info(f"Found {len(result.get('data', []))} concepts")

        return result

    def get_epd_concepts(self, save_to_file: Optional[str] = None) -> Optional[Dict[str, Any]]:
        """
        Get all EPD (Electronic Patient Record) concepts from eHealth Suisse (" + Config.PUBLISHER_IDENTIFIER + ")
        
        Args:
            save_to_file: Optional file path to save the response JSON
            
        Returns:
            Response JSON data or None if request failed
        """

        logging.info("Fetching EPD concepts from eHealth Suisse...")
        
        return self.get_concepts(
            publisher_identifier=Config.PUBLISHER_IDENTIFIER,
            save_to_file=save_to_file
        )

    def get_concept_by_identifier(self, concept_identifier: str, save_to_file: Optional[str] = None) -> Optional[Dict[str, Any]]:
        """
        Get a specific concept by its identifier (OID)
        
        Args:
            concept_identifier: The concept identifier to retrieve: Usually the OID (2.16.756.5.30.1.127.3.10.1.11)
            save_to_file: Optional file path to save the response JSON
            
        Returns:
            Response JSON data or None if request failed
        """

        logging.info(f"Fetching concept with ID: {concept_identifier}")

        return self.get_concepts(
            concept_identifier=concept_identifier,
            publisher_identifier=None,
            save_to_file=save_to_file
        )


def main():
    # Force all logging to stdout
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(levelname)s - %(message)s",
        datefmt="%H:%M:%S",
        stream=sys.stdout,
        force=True
    )
    
    # Add this line to see which environment you're using (Debug Stuff)
    #Config.print_config()

    if len(sys.argv) < 2:
        print("Usage: python I14Y_API_handling.py <method> [file_path] [concept_id]")
        print("Methods:")
        print("  -pc   → post_new_concept(file_path)")
        print("  -pmc  → post_multiple_concepts(directory_path)")
        print("  -pcl  → post_codelist_entries(file_path, concept_id)")
        print("  -pmcl → post_multiple_new_codelists(directory_path)")
        print("  -gce  → get_codelist_entry(concept_id)")
        print("  -dc   → delete_concept(concept_id)")
        print("  -dcl  → delete_codelist_entries(concept_id)")
        print("  -ucl  → update_codelist_entries(file_path, concept_id)")
        print("\nGet Methods:")
        print("  -gc   → get_concepts([filters...]) [output_file]")
        print("  -gec  → get_epd_concepts([output_file])")
        print("  -gci  → get_concept_by_identifier(OID) [output_file]")
        print("  -ucm  → update_mapping_from_api()")  # New method
        print("\nStatus & Publication level Methods:")
        print("  -spl   → set_publication_level(publication_level, concept_id)")
        print("  -srs   → set_registration_status(registration_status, concept_id)")
        print("\nGet Examples:")
        print("  python3 I14Y_API_handling.py -gec epd_concepts.json")
        print("  python3 I14Y_API_handling.py -gci 08dd632d-aca1-b77d-80c2-3e6b677753f9")
        print("  python3 I14Y_API_handling.py -gc --publisher='eHealth Suisse' --status=Standard")
        sys.exit(1)

    method = sys.argv[1]

    try:
        if method == "-pmc":
            if len(sys.argv) < 3:
                logging.error("Missing argument: directory_path for -pmc.")
                sys.exit(1)
            
            directory_path = sys.argv[2]
            api_client = I14yApiClient(directory_path=directory_path)
            api_client.post_multiple_concepts(directory_path)

        elif method == "-pmcl":
            if len(sys.argv) < 3:
                logging.error("Missing argument: directory_path for -pmcl.")
                sys.exit(1)
            directory_path = sys.argv[2]
            
            api_client = I14yApiClient(directory_path=directory_path)
            api_client.post_multiple_new_codelists(directory_path)

        elif method == "-gce":
            if len(sys.argv) < 3:
                logging.error("Missing argument: concept_id for -gce.")
                sys.exit(1)
            concept_id = sys.argv[2]
            api_client = I14yApiClient()
            api_client.get_codelist_entry(concept_id, "epd_codelist_entry.json")

        else:
            api_client = I14yApiClient()

            if method == "-pc":
                if len(sys.argv) < 3:
                    logging.error("Missing argument: file_path for -pc.")
                    sys.exit(1)
                file_path = sys.argv[2]
                api_client.post_new_concept(file_path)

            elif method == "-pcl":
                if len(sys.argv) < 4:
                    logging.error("Missing arguments: file_path and concept_id for -pcl.")
                    sys.exit(1)
                file_path, concept_id = sys.argv[2], sys.argv[3]
                #print(file_path)
                api_client.post_codelist_entries(file_path, concept_id)

            elif method == "-spl":
                if len(sys.argv) < 4:
                    logging.error("Missing arguments: publication_level and concept_id for -spl.")
                    sys.exit(1)
                print(sys.argv[1])
                publication_level, concept_id = sys.argv[2], sys.argv[3]
                api_client.set_publication_level(publication_level, concept_id)

            elif method == "-srs":
                if len(sys.argv) < 4:
                    logging.error("Missing arguments: registration_status and concept_id for -srs.")
                    sys.exit(1)
                registration_status, concept_id = sys.argv[2], sys.argv[3]
                api_client.set_registration_status(registration_status, concept_id)

            elif method == "-ucl":
                if len(sys.argv) < 4:
                    logging.error("Missing arguments: file_path and concept_id for -ucl.")
                    sys.exit(1)
                file_path, concept_id = sys.argv[2], sys.argv[3]
                api_client.update_codelist_entries(file_path, concept_id)

            elif method == "-dcl":
                if len(sys.argv) < 3:
                    logging.error("Missing argument: concept_id for -dcl.")
                    sys.exit(1)
                concept_id = sys.argv[2]
                api_client.delete_codelist_entries(concept_id)

            elif method == "-dc":
                if len(sys.argv) < 3:
                    logging.error("Missing argument: concept_id for -dc.")
                    sys.exit(1)
                concept_id = sys.argv[2]
                api_client.delete_concept(concept_id)

            elif method == "-gec":
                # Get all EPD concepts
                save_file = sys.argv[2] if len(sys.argv) > 2 else None

                result = api_client.get_epd_concepts(save_to_file=save_file)

                if result:
                    if not save_file:
                        print(json.dumps(result, indent=2, ensure_ascii=False))

            elif method == "-gci":
                # Get concept by identifier
                if len(sys.argv) < 3:
                    logging.error("Missing argument: concept_identifier for -gci.")
                    sys.exit(1)
                concept_identifier = sys.argv[2]
                save_file = sys.argv[3] if len(sys.argv) > 3 else None
                result = api_client.get_concept_by_identifier(concept_identifier, save_to_file=save_file)
                if result and not save_file:
                    print(json.dumps(result, indent=2, ensure_ascii=False))

            elif method == "-gc":
                # Advanced get concepts with filters
                save_file = None
                filters = {}
                
                # Parse additional arguments
                for arg in sys.argv[2:]:
                    if arg.endswith('.json'):
                        save_file = arg
                    elif arg.startswith('--publisher='):
                        filters['publisher_identifier'] = arg.split('=', 1)[1]
                    elif arg.startswith('--status='):
                        filters['registration_status'] = arg.split('=', 1)[1]
                    elif arg.startswith('--level='):
                        filters['publication_level'] = arg.split('=', 1)[1]
                    elif arg.startswith('--version='):
                        filters['version'] = arg.split('=', 1)[1]
                    elif arg.startswith('--id='):
                        filters['concept_identifier'] = arg.split('=', 1)[1]
                    elif arg.startswith('--page='):
                        filters['page'] = int(arg.split('=', 1)[1])
                    elif arg.startswith('--pagesize='):
                        filters['page_size'] = int(arg.split('=', 1)[1])
                
                result = api_client.get_concepts(save_to_file=save_file, **filters)
                if result:
                    if not save_file:
                        print(json.dumps(result, indent=2, ensure_ascii=False))
            
            elif method == "-ucm":
                logging.info("Updating codelist mapping from API...")
                codelist_manager = CodelistManager("codelist_mapping.json")

                updated = codelist_manager.update_mapping_from_api()
                if updated:
                    logging.info("Codelist mapping updated successfully")
                else:
                    logging.warning("No updates were made to codelist mapping")

            else:
                logging.error(f"Invalid method: {method}. "
                            f"Accepted methods are: -pc, -pmc, -pcl, -pmcl, -dcl, -ucl, -gec, -gci, -gc, -spl, -srs.")
                sys.exit(1)

    except I14yApiError as e:
        logging.error(f"API Error: {e.message}")
        sys.exit(1)
    except Exception as e:
        logging.error(f"Unexpected error: {e}")
        sys.exit(1)

    logging.info("🎉 Script execution completed successfully.")


if __name__ == "__main__":
    main()