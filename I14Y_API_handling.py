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

    if API_MODE == 'PROD':
        CLIENT_ID = PROD_CLIENT_ID
        CLIENT_SECRET = PROD_CLIENT_SECRET
        TOKEN_URL = PROD_TOKEN_URL
        BASE_API_URL = PROD_BASE_API_URL

    # Assign CONCEPT_POST_URL after BASE_API_URL is set correctly
    CONCEPT_POST_URL = f"{BASE_API_URL}concepts"


# Setting up logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

class i14y_api_calls():

    def __init__(self, directory_path):
        self.DIRECTORY_PATH = directory_path
        self.AUTH_TOKEN = None
        self.token_expiry = 0
        self.get_access_token()

    def get_access_token(self):
        if self.AUTH_TOKEN and time.time() < self.token_expiry:
            return self.AUTH_TOKEN
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
        self.AUTH_TOKEN = f"{token}"
        self.token_expiry = time.time() + expires_in - 60  # refresh 1 min early
        return self.AUTH_TOKEN
    
    def post_CodelistEntries(self, file_path, concept_id):
        headers = {
            'Authorization': f'{self.AUTH_TOKEN}',
            'accept': '*/*'
        }
        
        POST_URL = f"{Config.BASE_API_URL}/concepts/{concept_id}/codelist-entries/imports/json"

        # Check if the file exists before making the request
        if not os.path.isfile(file_path):
            logging.error(f"File not found: {file_path}")
            return

        # Prepare the file to be sent in the request
        files = {'file': (os.path.basename(file_path), open(file_path, 'rb'), 'application/json')}
        
        try:
            logging.info(f"Posting file to URL: {POST_URL}")
            response = requests.post(POST_URL, headers=headers, files=files, verify=certifi.where())
            response.raise_for_status()  # Raise an error for bad status codes
            logging.info("File posted successfully")
            return response.json()
        except requests.exceptions.HTTPError as http_err:
            logging.error(f"HTTP error occurred: {http_err}")
        except requests.exceptions.ConnectionError as conn_err:
            logging.error(f"Connection error occurred: {conn_err}")
        except requests.exceptions.Timeout as timeout_err:
            logging.error(f"Timeout error occurred: {timeout_err}")
        except Exception as err:
            logging.error(f"An error occurred: {err}")
        return None

    def get_CodelistEntry(self): #TODO: verbinden mit save_data_to_file, updaten so wie es jetzt ist, funktioniert nicht
        headers = {
            'accept': '*/*',
            'Authorization': f'Bearer {self.AUTH_TOKEN}'
        }
        
        logging.info(f"Fetching data from URL: {self.GET_URL}")
        
        try:
            response = requests.get(self.GET_URL, headers=headers)
            response.raise_for_status()  # Raise an error for bad status codes
            data = response.json()
            logging.info("Received response from the API")
            return data
        except requests.exceptions.HTTPError as http_err:
            logging.error(f"HTTP error occurred: {http_err}")
        except requests.exceptions.ConnectionError as conn_err:
            logging.error(f"Connection error occurred: {conn_err}")
        except requests.exceptions.Timeout as timeout_err:
            logging.error(f"Timeout error occurred: {timeout_err}")
        except Exception as err:
            logging.error(f"An error occurred: {err}")
        return None
    
    def delete_CodelistEntries(self, concept_id):
        headers = {
            'accept': '*/*',
            'Authorization': f'Bearer {self.AUTH_TOKEN}'
        }

        DELETE_URL = f"{Config.BASE_API_URL}/concepts/{concept_id}/codelist-entries"

        try:
            logging.info(f"Sending DELETE request to URL: {DELETE_URL}")
            response = requests.delete(DELETE_URL, headers=headers)
            response.raise_for_status()  # Raise an error for bad status codes
            logging.info("DELETE request successful")
            return response.json()
        except requests.exceptions.HTTPError as http_err:
            logging.error(f"HTTP error occurred: {http_err}")
        except requests.exceptions.ConnectionError as conn_err:
            logging.error(f"Connection error occurred: {conn_err}")
        except requests.exceptions.Timeout as timeout_err:
            logging.error(f"Timeout error occurred: {timeout_err}")
        except Exception as err:
            logging.error(f"An error occurred: {err}")
        return None
    
    def save_ResponseToFile(data, file_path):
        try:
            with open(file_path, 'w') as file:
                json.dump(data, file, indent=4)
            logging.info(f"Data has been written to {file_path}")
        except Exception as e:
            logging.error(f"Failed to write data to file: {e}")

    def update_CodelistEntries (self, file_path, concept_id):
        self.delete_CodelistEntries(concept_id)
        self.post_CodelistEntries(file_path, concept_id)
    
    def post_MultipleNewCodelists(self, directory_path):
        # Find all JSON files in the directory
        json_files = glob.glob(os.path.join(directory_path, "*_transformed.json"))
 
        print(f"Found {len(json_files)} files to process")

        for json_file in json_files:
            # Get the codelist ID based on filename
            print(f"Processing file: {json_file}")
            codelist_id = self.get_codelist_id(json_file)

            if codelist_id:
                print(f"Posting {json_file} with codelist ID: {codelist_id.value}")
                self.update_CodelistEntries(json_file, codelist_id.value)
            else:
                print(f"No matching codelist ID found for {json_file}")

    def get_codelist_id(self, filename):
        # Map filename patterns to enum values
        mapping = {
            'SubmissionSet.contentTypeCode_transformed': codeListsId.SubmissionSet_contentTypeCode,
            'EprRole_transformed': codeListsId.EprRole,
            'HCProfessional.hcProfession_transformed': codeListsId.HCProfessional_hcProfession,
            'DocumentEntry.classCode_transformed': codeListsId.DocumentEntry_classCode,
            'DocumentEntry.authorSpeciality_transformed': codeListsId.DocumentEntry_author_authorSpeciality,
            'DocumentEntry.confidentialityCode_transformed': codeListsId.DocumentEntry_confidentialityCode,
            'DocumentEntry.eventCodeList_transformed': codeListsId.DocumentEntry_eventCodeList,
            'DocumentEntry.formatCode_transformed': codeListsId.DocumentEntry_formatCode,
            'DocumentEntry.healthcareFacilityTypeCode_transformed': codeListsId.DocumentEntry_healthcareFacilityTypeCode,
            'DocumentEntry.mimeType_transformed': codeListsId.DocumentEntry_mimeType,
            'DocumentEntry.practiceSettingCode_transformed': codeListsId.DocumentEntry_practiceSettingCode,
            'DocumentEntry.sourcePatientInfo.PID-8_transformed': codeListsId.DocumentEntry_sourcePatientInfo_PID_8,
            'DocumentEntry.typeCode_transformed': codeListsId.DocumentEntry_typeCode,
            'EprAuditTrailConsumptionEventType_transformed': codeListsId.EprAuditTrailConsumptionEventType,
            'EprDeletionStatus_transformed': codeListsId.EprDeletionStatus,
            'DocumentEntry.languageCode_transformed': codeListsId.DocumentEntry_languageCode,
            'EprPurposeOfUse_transformed': codeListsId.EprPurposeOfUse,
            'EprAgentRole_transformed': codeListsId.EprAgentRole
        }
    
        # Remove file extension and path to get base filename
        base_filename = os.path.splitext(os.path.basename(filename))[0]
        # Return corresponding enum value or None if not found
        return mapping.get(base_filename)
    
    def post_NewConcept(self, file_path): #TODO: anpassen dass inhalte in das neu erstellte konzept geschrieben werden
        headers = {
            'Content-Type': 'application/json',
            'Authorization': f'Bearer {self.AUTH_TOKEN}',
            'Accept': 'application/json'
        }
        
        POST_URL = Config.CONCEPT_POST_URL
       
        # Check if the file exists before making the request
        if not os.path.isfile(file_path):
            logging.error(f"File not found: {file_path}")
            return

        # Prepare the file to be sent in the request
        files = {'file': (os.path.basename(file_path), open(file_path, 'rb'), 'application/json')}

        with open(file_path, 'r', encoding='utf-8') as file:
            payload = json.load(file)
            #print("Payload being sent:")
            #print(json.dumps(payload, indent=2))

        try:
            logging.info(f"Posting file to URL: {POST_URL}")
            response = requests.post(POST_URL, headers=headers, json=payload, verify=certifi.where())
            response.raise_for_status()  # Raise an error for bad status codes
            logging.info("File posted successfully")
      
        except requests.exceptions.RequestException as e:
            # Get basic info
            status_code = e.response.status_code if e.response else "No status code"
            error_text = e.response.text if e.response else "No response text"

            # Try to parse the JSON error response
            try:
                error_json = e.response.json()
                detail = error_json.get("detail", "No detail provided.")
                title = error_json.get("title", "")
            except Exception:
                detail = error_text
                title = ""

            # Check for known error cases
            user_hint = ""
            if "already exists" in detail:
                user_hint = (
                    "\nHint: The concept you're trying to post already exists on the server.\n"
                    "Consider using the '-dcl' (delete_CodelistEntries) method before re-posting.\n"
                )

            # Show clean error summary in terminal
            print(f"\n❌ Request failed with status code {status_code}: {title}")
            print(f"Reason: {detail.strip()}")
            print(user_hint)
            print("More technical details are written to 'api_errors_log.txt'\n")

            # Prepare full technical dump
            error_message = f"""
        Status Code: {status_code}
        Error Response: {error_text}
        Response Headers: {dict(e.response.headers) if e.response else 'No headers'}
        Request Exception: {str(e)}
        Request Details: {e.request.method if e.request else 'N/A'} {e.request.url if e.request else 'N/A'}
        Request Headers: {dict(e.request.headers) if e.request else 'N/A'}
        Request Body: {e.request.body if e.request else 'N/A'}
        """

            # Write to log
            log_path = os.path.join("AD_VS", "api_errors_log.txt")
            with open(log_path, 'a', encoding='utf-8') as f:
                f.write(f"\n--- Error occurred at {datetime.datetime.now()} ---\n")
                f.write(error_message)
                f.write("\n--------------------\n")



    
    def post_MultipleConcepts(self, directory_path):
        # Find all JSON files in the directory
        json_files = glob.glob(os.path.join(directory_path, "*.json"))

        print(f"Found {len(json_files)} files to process")

        for json_file in json_files:
            print(f"Posting file: {json_file}")
            self.post_NewConcept(json_file)

class codeListsId(enum.Enum):
    #Id of codelists version 2.0.0
    SubmissionSet_contentTypeCode = '08dd632d-b449-6c4f-bff5-38488abd5b6f'
    EprRole = '08dd632d-b378-e759-84d8-f04d0168890c' #The value sets SubmissionSet.Author.AuthorRole, DocumentEntry.author.authorRole and DocumentEntry.originalProviderRole are referencing this value set
    HCProfessional_hcSpecialisation = '' #import content from value set 
    HCProfessional_hcProfession = '08dd632d-b3c5-ed64-a995-369c44b38c06'
    DocumentEntry_classCode = '08dd632d-aa6b-ffb2-a78b-fbff93d4f167'
    DocumentEntry_author_authorSpeciality = '08dd632d-a98d-34ff-9252-123e46d6f053'
    DocumentEntry_confidentialityCode = '08dd632d-aada-98dd-bbc2-21ad33bd1565'
    DocumentEntry_eventCodeList = '08dd632d-ab2e-9938-8e31-4fb07a28b4a3'
    DocumentEntry_formatCode = '08dd632d-ab82-6614-a9a4-c9842737aa2f'
    DocumentEntry_healthcareFacilityTypeCode ='08dd632d-abd6-c1fd-9468-533a88e19499'
    DocumentEntry_mimeType = '08dd632d-aca1-b77d-80c2-3e6b677753f9'
    DocumentEntry_practiceSettingCode = '08dd632d-ad55-7a02-b041-ae0059ba8d79'
    DocumentEntry_sourcePatientInfo_PID_8 = '08dd632d-ada3-bda0-be32-f270bf291810'
    DocumentEntry_typeCode = '08dd632d-adf6-96f1-9850-7ef00f059f80'
    EprAuditTrailConsumptionEventType = '08dd632d-b23a-ec97-8812-886854f69afd'
    EprDeletionStatus = '08dd632d-b2a2-0ed2-941d-fffb2bea1af5'
    DocumentEntry_languageCode = '08dd632d-ac4d-977f-a53b-ec0b1af269f8'
    EprPurposeOfUse = '08dd632d-b2f7-197a-889f-18e7a917dd67'
    EprAgentRole = '08dd632d-aee2-333d-b1e4-505385fde8ff'

# Main execution
def main():
    logging.basicConfig(level=logging.INFO)

    if len(sys.argv) < 2:
        print("Usage: python I14Y_API_handling.py <method> [file_path] [concept_id]")
        print("Methods:")
        print("  -pc   → post_NewConcept(file_path)")
        print("  -pmc  → post_MultipleNewConcepts(directory_path)")
        print("  -pcl  → post_CodelistEntries(file_path, concept_id)")
        print("  -pmcl → post_MultipleNewCodelists(directory_path)")
        print("  -dcl  → delete_CodelistEntries(concept_id)")
        logging.error("Missing arguments.")
        sys.exit(1)

    # Extract arguments
    method = sys.argv[1]
    #i14y_user_token = sys.argv[1]  # Last argument is the auth_token
    

    # Initialize API handler (Only directory_path is required)
    if method == "-pmc":
        if len(sys.argv) < 3:
            logging.error("Missing argument: directory_path for -pmc.")
            sys.exit(1)
        
        directory_path = sys.argv[2]
        api_handler = i14y_api_calls(directory_path=directory_path)
        api_handler.post_MultipleConcepts(directory_path)

    elif method == "-pmcl":
        if len(sys.argv) < 3:
            logging.error("Missing argument: directory_path for -pmcl.")
            sys.exit(1)
        directory_path = sys.argv[2]
       
        api_handler = i14y_api_calls(directory_path=directory_path)
        api_handler.post_MultipleNewCodelists(directory_path)

    else:
        api_handler = i14y_api_calls()

        if method == "-pc":
            if len(sys.argv) < 3:
                logging.error("Missing argument: file_path for -pc.")
                sys.exit(1)
            file_path = sys.argv[2]
            api_handler.post_NewConcept(file_path)

        elif method == "-pcl":
            if len(sys.argv) < 4:
                logging.error("Missing argument: file_path und concept_id for -pcl.")
                sys.exit(1)
            file_path, concept_id = sys.argv[3:4]
            api_handler.post_CodelistEntries(file_path, concept_id)

        

        elif method == "-dcl":
            if len(sys.argv) < 3:
                logging.error("Missing argument: concept_id for -dcl.")
                sys.exit(1)
            concept_id = sys.argv[2]
            api_handler.delete_CodelistEntries(concept_id)

        else:
            logging.error(f"Invalid argument: {method}. Accepted arguments are: -pc, -pmc, -pcl, -pmcl, -dcl.")
            sys.exit(1)

    logging.info("Script execution completed.")

if __name__ == "__main__":
    main()
   
#TODO: Agrs anpassen um alles notwendige beim ausführen anzugeben. [1] dir path [2] auth token [3] welche operation ausgeführt werden soll (upload (new VS oder CodeListEntries), download, delete)