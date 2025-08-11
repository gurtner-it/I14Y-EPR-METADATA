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
from pathlib import Path
from typing import Optional, Dict, Any, Union
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

class Config:
    """Configuration class to handle all environment variables"""
    API_MODE = os.getenv("API_MODE")

    PROD_CLIENT_ID = os.getenv("PROD_CLIENT_ID")
    PROD_CLIENT_SECRET = os.getenv("PROD_CLIENT_SECRET")
    PROD_TOKEN_URL = os.getenv("PROD_TOKEN_URL")
    PROD_BASE_API_URL = os.getenv("PROD_BASE_API_URL")

    CLIENT_ID = os.getenv("ABN_CLIENT_ID")
    CLIENT_SECRET = os.getenv("ABN_CLIENT_SECRET")
    TOKEN_URL = os.getenv("ABN_TOKEN_URL")
    BASE_API_URL = os.getenv("ABN_BASE_API_URL")
    
    # Publisher information
    PUBLISHER_IDENTIFIER = os.getenv('PUBLISHER_IDENTIFIER', 'CH_eHealth')
    PUBLISHER_NAME = os.getenv('PUBLISHER_NAME', 'eHealth Suisse')

    if API_MODE == 'PROD':
        CLIENT_ID = PROD_CLIENT_ID
        CLIENT_SECRET = PROD_CLIENT_SECRET
        TOKEN_URL = PROD_TOKEN_URL
        BASE_API_URL = PROD_BASE_API_URL

    # Assign CONCEPT_POST_URL after BASE_API_URL is set correctly
    CONCEPT_POST_URL = f"{BASE_API_URL}concepts"


# Setting up logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')


class I14yApiError(Exception):
    """Custom exception for I14Y API errors"""
    def __init__(self, message: str, status_code: Optional[int] = None, response_text: Optional[str] = None):
        self.message = message
        self.status_code = status_code
        self.response_text = response_text
        super().__init__(self.message)


class CodeListsId(enum.Enum):
    """Enum for codelist IDs version 2.0.0"""
    SubmissionSet_contentTypeCode = '08dd632d-b449-6c4f-bff5-38488abd5b6f'
    EprRole = '08dd632d-b378-e759-84d8-f04d0168890c'
    HCProfessional_hcSpecialisation = ''  # import content from value set 
    HCProfessional_hcProfession = '08dd632d-b3c5-ed64-a995-369c44b38c06'
    DocumentEntry_classCode = '08dd632d-aa6b-ffb2-a78b-fbff93d4f167'
    DocumentEntry_author_authorSpeciality = '08dd632d-a98d-34ff-9252-123e46d6f053'
    DocumentEntry_confidentialityCode = '08dd632d-aada-98dd-bbc2-21ad33bd1565'
    DocumentEntry_eventCodeList = '08dd632d-ab2e-9938-8e31-4fb07a28b4a3'
    DocumentEntry_formatCode = '08dd632d-ab82-6614-a9a4-c9842737aa2f'
    DocumentEntry_healthcareFacilityTypeCode = '08dd632d-abd6-c1fd-9468-533a88e19499'
    DocumentEntry_mimeType = '08dd632d-aca1-b77d-80c2-3e6b677753f9'
    DocumentEntry_practiceSettingCode = '08dd632d-ad55-7a02-b041-ae0059ba8d79'
    DocumentEntry_sourcePatientInfo_PID_8 = '08dd632d-ada3-bda0-be32-f270bf291810'
    DocumentEntry_typeCode = '08dd632d-adf6-96f1-9850-7ef00f059f80'
    EprAuditTrailConsumptionEventType = '08dd632d-b23a-ec97-8812-886854f69afd'
    EprDeletionStatus = '08dd632d-b2a2-0ed2-941d-fffb2bea1af5'
    DocumentEntry_languageCode = '08dd632d-ac4d-977f-a53b-ec0b1af269f8'
    EprPurposeOfUse = '08dd632d-b2f7-197a-889f-18e7a917dd67'
    EprAgentRole = '08dd632d-aee2-333d-b1e4-505385fde8ff'


class CodelistManager:
    def __init__(self, mapping_file: str = None):
        self.api_client = I14yApiClient()
        self.mapping_file = Path(mapping_file)
        self.mapping = self._load_mapping()
        self.cache: Dict[str, str] = {}
        
    def _load_mapping(self) -> Dict[str, Any]:
        """Load the filename to API identifier mapping"""
        with open(self.mapping_file, 'r', encoding='utf-8') as f:
            return json.load(f)
    
    def get_codelist_id(self, filename: str) -> Optional[str]:
        """Get codelist ID from filename, either from cache or API"""
        base_filename = os.path.splitext(os.path.basename(filename))[0]
        
        # Check if we have a mapping for this filename
        if base_filename not in self.mapping['concepts']:
            return None
            
        mapping_info = self.mapping['concepts'][base_filename]
        
        # Try to get from API first
        api_id = self._get_from_api(mapping_info.get('api_identifier'))
        if api_id:
            return api_id
            
        # Fall back to hardcoded ID if API fails
        return mapping_info.get('fallback_id')
    
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
            logging.info(f"Successfully updated mapping with {len(new_mapping['concepts'])} concepts")
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
            #logging.info(token)
            self.token_expiry = time.time() + expires_in - 60  # refresh 1 min early
            
            logging.info("Access token obtained successfully")
            return self.auth_token
            
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

        # Display clean error summary
        print(f"\n❌ {operation_name} failed with status code {status_code}: {title}")
        print(f"Reason: {detail.strip()}")
        if user_hint:
            print(user_hint)
        print("More technical details are written to 'api_errors_log.txt'\n")

        # Log detailed error information
        self._log_detailed_error(exception, operation_name)

    def _get_error_hint(self, detail: str) -> str:
        """Get user-friendly hints based on error details"""
        if "already exists" in detail.lower():
            return ("\nHint: The concept you're trying to post already exists on the server.\n"
                   "Consider using the '-dcl' (delete_CodelistEntries) method before re-posting.\n")
        elif "not found" in detail.lower():
            return "\nHint: The requested resource was not found. Please check the concept ID.\n"
        elif "unauthorized" in detail.lower():
            return "\nHint: Authentication failed. Please check your credentials.\n"
        elif "forbidden" in detail.lower():
            return "\nHint: Access denied. You may not have permission for this operation.\n"
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

        log_path = os.path.join("AD_VS", "api_errors_log.txt")
        os.makedirs(os.path.dirname(log_path), exist_ok=True)
        
        with open(log_path, 'a', encoding='utf-8') as f:
            f.write(error_message)

    def _validate_file_exists(self, file_path: str) -> bool:
        """Validate that a file exists"""
        if not os.path.isfile(file_path):
            logging.error(f"File not found: {file_path}")
            return False
        return True

    def post_codelist_entries(self, file_path: str, concept_id: str) -> Optional[Dict[str, Any]]:
        """Post codelist entries from a JSON file"""
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

    def get_codelist_entry(self, get_url: str) -> Optional[Dict[str, Any]]:
        """Get codelist entry (needs to be connected with save_data_to_file)"""
        return self._make_request(
            method='GET',
            url=get_url,
            operation_name="Fetching codelist entry"
        )

    def delete_codelist_entries(self, concept_id: str) -> Optional[Dict[str, Any]]:
        """Delete all codelist entries for a concept"""
        url = f"{Config.BASE_API_URL}/concepts/{concept_id}/codelist-entries"
        return self._make_request(
            method='DELETE',
            url=url,
            operation_name=f"Deleting codelist entries for concept {concept_id}"
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
        
        return self._make_request(
            method='POST',
            url=Config.CONCEPT_POST_URL,
            headers=headers,
            json_data=payload,
            operation_name=f"Posting new concept from {file_path}"
        )

    def post_multiple_new_codelists(self, directory_path: str):
        """Post multiple codelist files from a directory"""
        json_files = glob.glob(os.path.join(directory_path, "*_transformed.json"))
        
        if not json_files:
            logging.warning(f"No *_transformed.json files found in {directory_path}")
            return

        print(f"Found {len(json_files)} files to process")

        for json_file in json_files:
            print(f"Processing file: {json_file}")
            codelist_id = self._get_codelist_id(json_file)

            if codelist_id:
                print(f"Posting {json_file} with codelist ID: {codelist_id.value}")
                self.update_codelist_entries(json_file, codelist_id.value)
            else:
                print(f"No matching codelist ID found for {json_file}")

    def _get_codelist_id(self, filename: str) -> Optional[CodeListsId]:
        """Map filename patterns to enum values"""
        mapping = {
            'SubmissionSet.contentTypeCode_transformed': CodeListsId.SubmissionSet_contentTypeCode,
            'EprRole_transformed': CodeListsId.EprRole,
            'HCProfessional.hcProfession_transformed': CodeListsId.HCProfessional_hcProfession,
            'DocumentEntry.classCode_transformed': CodeListsId.DocumentEntry_classCode,
            'DocumentEntry.authorSpeciality_transformed': CodeListsId.DocumentEntry_author_authorSpeciality,
            'DocumentEntry.confidentialityCode_transformed': CodeListsId.DocumentEntry_confidentialityCode,
            'DocumentEntry.eventCodeList_transformed': CodeListsId.DocumentEntry_eventCodeList,
            'DocumentEntry.formatCode_transformed': CodeListsId.DocumentEntry_formatCode,
            'DocumentEntry.healthcareFacilityTypeCode_transformed': CodeListsId.DocumentEntry_healthcareFacilityTypeCode,
            'DocumentEntry.mimeType_transformed': CodeListsId.DocumentEntry_mimeType,
            'DocumentEntry.practiceSettingCode_transformed': CodeListsId.DocumentEntry_practiceSettingCode,
            'DocumentEntry.sourcePatientInfo.PID-8_transformed': CodeListsId.DocumentEntry_sourcePatientInfo_PID_8,
            'DocumentEntry.typeCode_transformed': CodeListsId.DocumentEntry_typeCode,
            'EprAuditTrailConsumptionEventType_transformed': CodeListsId.EprAuditTrailConsumptionEventType,
            'EprDeletionStatus_transformed': CodeListsId.EprDeletionStatus,
            'DocumentEntry.languageCode_transformed': CodeListsId.DocumentEntry_languageCode,
            'EprPurposeOfUse_transformed': CodeListsId.EprPurposeOfUse,
            'EprAgentRole_transformed': CodeListsId.EprAgentRole
        }

        base_filename = os.path.splitext(os.path.basename(filename))[0]
        return mapping.get(base_filename)

    def post_multiple_concepts(self, directory_path: str):
        """Post multiple concept files from a directory"""
        json_files = glob.glob(os.path.join(directory_path, "*.json"))
        
        if not json_files:
            logging.warning(f"No JSON files found in {directory_path}")
            return

        print(f"Found {len(json_files)} concept files to process")

        for json_file in json_files:
            print(f"Posting concept file: {json_file}")
            self.post_new_concept(json_file)

    @staticmethod
    def save_response_to_file(data: Dict[str, Any], file_path: str):
        """Save API response data to a JSON file"""
        try:
            os.makedirs(os.path.dirname(file_path), exist_ok=True)
            with open(file_path, 'w', encoding='utf-8') as file:
                json.dump(data, file, indent=4, ensure_ascii=False)
            logging.info(f"Data has been written to {file_path}")
        except Exception as e:
            logging.error(f"Failed to write data to file: {e}")

    def get_concepts(self, 
                    concept_identifier: Optional[str] = None,
                    publisher_identifier: Optional[str] = Config.PUBLISHER_IDENTIFIER,
                    version: Optional[str] = None,
                    publication_level: Optional[str] = None,
                    registration_status: Optional[str] = None,
                    page: Optional[int] = None,
                    page_size: Optional[int] = None,
                    save_to_file: Optional[str] = "AD_VS/epr_concepts.txt") -> Optional[Dict[str, Any]]:
        """
        Get concepts matching the given filters
        
        Args:
            concept_identifier: Filter by specific concept identifier
            publisher_identifier: Filter by publisher (defaults to " + Config.PUBLISHER_IDENTIFIER +")
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

        save_to_file = save_to_file or "AD_VS/epr_concepts.txt" 


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
        url = f"{Config.BASE_API_URL}/concepts"
        
        # Make the request
        result = self._make_request(
            method='GET',
            url=url,
            json_data=params,
            operation_name=f"Getting concepts with filters: {params}"
        )
        
        # Save to file if requested
        if result and save_to_file:
            self.save_response_to_file(result, save_to_file)
        
        return result

    def get_epd_concepts(self, save_to_file: Optional[str] = "AD_VS/epr_concepts.txt") -> Optional[Dict[str, Any]]:
        """
        Get all EPD (Electronic Patient Record) concepts from eHealth Suisse (" + Config.PUBLISHER_IDENTIFIER + ")
        
        Args:
            save_to_file: Optional file path to save the response JSON
            
        Returns:
            Response JSON data or None if request failed
        """

        print("Fetching EPD concepts from eHealth Suisse...")

        return self.get_concepts(
            publisher_identifier=Config.PUBLISHER_IDENTIFIER,
            save_to_file=save_to_file
        )

    def get_concept_by_id(self, concept_id: str, save_to_file: Optional[str] = None) -> Optional[Dict[str, Any]]:
        """
        Get a specific concept by its identifier
        
        Args:
            concept_id: The concept identifier to retrieve
            save_to_file: Optional file path to save the response JSON
            
        Returns:
            Response JSON data or None if request failed
        """

        print(f"Fetching concept with ID: {concept_id}")

        return self.get_concepts(
            concept_identifier=concept_id,
            save_to_file=save_to_file
        )


def main():
    """Main execution function"""
    logging.basicConfig(level=logging.INFO)

    if len(sys.argv) < 2:
        print("Usage: python I14Y_API_handling.py <method> [file_path] [concept_id]")
        print("Methods:")
        print("  -pc   → post_new_concept(file_path)")
        print("  -pmc  → post_multiple_concepts(directory_path)")
        print("  -pcl  → post_codelist_entries(file_path, concept_id)")
        print("  -pmcl → post_multiple_new_codelists(directory_path)")
        print("  -dcl  → delete_codelist_entries(concept_id)")
        print("  -ucl  → update_codelist_entries(file_path, concept_id)")
        print("\nGet Methods:")
        print("  -gc   → get_concepts([filters...]) [output_file]")
        print("  -gepd → get_epd_concepts([output_file])")
        print("  -gci  → get_concept_by_id(concept_id) [output_file]")
        print("  -ucm  → update_codelist_mapping()")  # New method
        print("\nGet Examples:")
        print("  python3 I14Y_API_handling.py -gepd epd_concepts.json")
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
                api_client.post_codelist_entries(file_path, concept_id)

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

            # New GET methods
            elif method == "-gepd":
                # Get all EPD concepts
                save_file = sys.argv[2] if len(sys.argv) > 2 else None

                result = api_client.get_epd_concepts(save_to_file=save_file)

                if result:
                    print(f"Found {len(result.get('data', []))} EPD concepts")
                    if not save_file:
                        print(json.dumps(result, indent=2, ensure_ascii=False))

            elif method == "-gci":
                # Get concept by ID
                if len(sys.argv) < 3:
                    logging.error("Missing argument: concept_id for -gci.")
                    sys.exit(1)
                concept_id = sys.argv[2]
                save_file = sys.argv[3] if len(sys.argv) > 3 else None
                result = api_client.get_concept_by_id(concept_id, save_to_file=save_file)
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
                    print(f"Found {len(result.get('data', []))} concepts")
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
                            f"Accepted methods are: -pc, -pmc, -pcl, -pmcl, -dcl, -ucl, -gepd, -gci, -gc.")
                sys.exit(1)

    except I14yApiError as e:
        logging.error(f"API Error: {e.message}")
        sys.exit(1)
    except Exception as e:
        logging.error(f"Unexpected error: {e}")
        sys.exit(1)

    logging.info("Script execution completed successfully.")


if __name__ == "__main__":
    main()