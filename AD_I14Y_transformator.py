# AD_I14Y_transformator.py
# This script transforms CSV and XML files into a specific JSON format for interoperability with i14y.

import json
import sys
import csv
import os
import re
import xml.etree.ElementTree as ET
import enum
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

class Config:
    """Configuration class to handle all environment variables"""
    
    # Publisher information
    PUBLISHER_IDENTIFIER = os.getenv('PUBLISHER_IDENTIFIER', 'CH_eHealth')
    PUBLISHER_NAME = os.getenv('PUBLISHER_NAME', 'eHealth Suisse')
    
    # Default values
    DEFAULT_VERSION = os.getenv('DEFAULT_VERSION', '2.0.0')
    DEFAULT_PUBLICATION_LEVEL = os.getenv('DEFAULT_PUBLICATION_LEVEL', 'Internal')
    DEFAULT_CONCEPT_TYPE = os.getenv('DEFAULT_CONCEPT_TYPE', 'CodeList')
    DEFAULT_VALUE_TYPE = os.getenv('DEFAULT_VALUE_TYPE', 'String')
    DEFAULT_VALUE_MAX_LENGTH = int(os.getenv('DEFAULT_VALUE_MAX_LENGTH', '30'))
    
    # Period defaults
    DEFAULT_PERIOD_START = os.getenv('DEFAULT_PERIOD_START', '2024-06-01')
    DEFAULT_PERIOD_END = os.getenv('DEFAULT_PERIOD_END', '2100-06-01')
    
    # Person emails (fallback to original values if not in env)
    DEFAULT_RESPONSIBLE_EMAIL = os.getenv('DEFAULT_RESPONSIBLE_EMAIL', 'pero.grgic@e-health-suisse.ch')
    DEFAULT_DEPUTY_EMAIL = os.getenv('DEFAULT_DEPUTY_EMAIL', 'stefanie.neuenschwander@e-health-suisse.ch')


class PublisherPersons:
    """Handles publisher person information"""
    
    def __init__(self):
        self.persons = {
            "PGR": {
                "email": Config.DEFAULT_RESPONSIBLE_EMAIL
            },
            "SNE": {
                "email": Config.DEFAULT_DEPUTY_EMAIL
            }
        }

    def get_person(self, key):
        """Returns the person dictionary based on a given key (e.g., 'PGR' or 'SNE')."""
        return self.persons.get(key, {})
    
class AD_csv_to_i14y_json():
    """Main transformer class that handles CSV and XML to JSON conversion"""
    
    def __init__(self, file_path, output_file_path, file_name, responsible_key, deputy_key, validFrom, new_concept):
        self.file_path = file_path
        self.json_output_file_path = output_file_path
        self.codeListEntries = []
        self.fileExtension = None
        self.concept = concept()
        self.fileName = file_name
        self.publisher_persons = PublisherPersons()
        self.responsible_person = self.publisher_persons.get_person(key=responsible_key)
        self.deputy_person = self.publisher_persons.get_person(key=deputy_key)
        self.new_concept = new_concept
        self.validFrom = validFrom

    def process_csv(self):
        self.fileExtension ="csv"
        with open(self.file_path, 'r', encoding="utf-8") as csvfile:
            file = csv.reader(csvfile, quotechar='"', delimiter=';')
        
            # Read first row to get ValueSet info
            first_row = next(file)[0]  # Get first element of first row
        
            # Extract name and identifier using regex
            name_match = re.search(r'Value Set (.*?) -', first_row)
            identifier_match = re.search(r'- ([\d.]+)', first_row)
        
            # Create concept instance and set values
            concept_instance = concept()
            if name_match:
                concept_instance.set_name(name_match.group(1))
            if identifier_match:
                concept_instance.set_identifier(identifier_match.group(1))
            
            # Read second row to set indexes
            index_row = next(file)
            indexDEps = next((i for i, x in enumerate(index_row) if "de-CH" in x and "preferred" in x), None)
            indexENps = next((i for i, x in enumerate(index_row) if "en-US" in x and "preferred" in x), None)
            indexITps = next((i for i, x in enumerate(index_row) if "it-CH" in x and "preferred" in x), None)
            indexRMps = next((i for i, x in enumerate(index_row) if "rm-CH" in x and "preferred" in x), None)
            indexFRps = next((i for i, x in enumerate(index_row) if "fr-CH" in x and "preferred" in x), None)
            indexDEas = next((i for i, x in enumerate(index_row) if "de-CH" in x and "synonym" in x), None)
            indexENas = next((i for i, x in enumerate(index_row) if "en-US" in x and "synonym" in x), None)
            indexITas = next((i for i, x in enumerate(index_row) if "it-CH" in x and "synonym" in x), None)
            indexRMas = next((i for i, x in enumerate(index_row) if "rm-CH" in x and "synonym" in x), None)
            indexFRas = next((i for i, x in enumerate(index_row) if "fr-CH" in x and "synonym" in x), None)            
            # Process remaining rows
            for row in file:
                code = Code()
                code.set_code(row[2])
                code.set_DisplayNameEN(row[3]) #this is the DisplayName of the code
                if indexDEps is not None:
                    code.set_DisplayNameDE(row[indexDEps])
                if indexFRps is not None:
                    code.set_DisplayNameFR(row[indexFRps])
                if indexITps is not None:
                    code.set_DisplayNameIT(row[indexITps])
                if indexRMps is not None:
                    code.set_DisplayNameRM(row[indexRMps])

                codeSystem = CodeSystem()
                codeSystem.set_Title(row[5])
                codeSystem.set_Text_DE(row[5])
                codeSystem.set_Text_FR(row[5])
                codeSystem.set_Text_IT(row[5])
                codeSystem.set_Text_EN(row[5])
                codeSystem.set_Text_RM(row[5])
                codeSystem.set_Identifier(row[4])

                synonymPS = Synonym("Preferred")
                if indexENps is not None:
                    synonymPS.set_text_EN(row[indexENps])#this is the EN synonym of the code
                if indexDEps is not None:
                    synonymPS.set_text_DE(row[indexDEps])
                if indexFRps is not None:
                    synonymPS.set_text_FR(row[indexFRps])
                if indexITps is not None:
                    synonymPS.set_text_IT(row[indexITps])
                if indexRMps is not None:
                    synonymPS.set_text_RM(row[indexRMps])

                synonymAS = Synonym("Acceptable")
                if indexENas is not None:
                    synonymAS.set_text_EN(row[indexENas])#this is the EN synonym of the code
                if indexDEas is not None:
                    synonymAS.set_text_DE(row[indexDEas])
                if indexFRas is not None:
                    synonymAS.set_text_FR(row[indexFRas])
                if indexITas is not None:
                    synonymAS.set_text_IT(row[indexITas])
                if indexRMas is not None:
                    synonymAS.set_text_RM(row[indexRMas])

                periodStart = Period("start")
                periodStart.set_Date(Config.DEFAULT_PERIOD_START)
                periodEnd = Period("end")
                periodEnd.set_Date(Config.DEFAULT_PERIOD_END)

                self.codeListEntries.append([code, codeSystem, periodStart, periodEnd, synonymPS, synonymAS])

    def process_xml(self):
        self.fileExtension = "xml"
        tree = ET.parse(self.file_path)
        root = tree.getroot()

        value_set = root.find('.//valueSet')
        concept_instance = concept()
        concept_instance.set_name(value_set.get('name'))
        concept_instance.set_identifier(value_set.get('id'))
        concept_instance.set_id(self.get_codelist_id(self.fileName))
        concept_instance.set_validFrom(self.validFrom)


        # Create mapping of codeSystem ids to their names
        code_system_mapping = {}
        for source_code_system in value_set.findall('sourceCodeSystem'):
            code_system_mapping[source_code_system.get('id')] = source_code_system.get('identifierName')

        # Get descriptions for each language
        for desc in value_set.findall('desc'):
            lang = desc.get('language')
            # Check for div first, if not found use direct text
            div = desc.find('div')
            text = div.text.strip() if div is not None else desc.text.strip()
        
            if lang == 'de-CH':
                concept_instance.set_descriptionDE(text)
            elif lang == 'en-US':
                concept_instance.set_descriptionEN(text)
            elif lang == 'fr-CH':
                concept_instance.set_descriptionFR(text)
            elif lang == 'it-CH':
                concept_instance.set_descriptionIT(text)
        
        
        self.isParent = None
        for concept_elem in value_set.findall('.//concept'):
                code = Code()
                code.set_code(concept_elem.get('code'))
                code.set_DisplayNameDE(concept_elem.get('displayName'))
                code.set_DisplayNameEN(concept_elem.get('displayName'))
                code.set_DisplayNameFR(concept_elem.get('displayName'))
                code.set_DisplayNameIT(concept_elem.get('displayName'))
                code.set_DisplayNameRM(concept_elem.get('displayName'))

                if concept_elem.get('level') == '0':
                    self.isParent = concept_elem.get('code')
                else:
                    code.set_parentCode(self.isParent)
            
                # Create synonyms
                synonymPS = Synonym("Preferred")
                synonymAS = Synonym("Acceptable")
            
                # Process designations based on type
                for designation in concept_elem.findall('designation'):
                    lang = designation.get('language')
                    text = designation.get('displayName')
                    desig_type = designation.get('type')
                
                    if desig_type == 'preferred':
                        if lang == 'de-CH':
                            synonymPS.set_text_DE(text)
                            code.set_DisplayNameDE(text)
                        elif lang == 'en-US':
                            synonymPS.set_text_EN(text)
                        elif lang == 'fr-CH':
                            synonymPS.set_text_FR(text)
                            code.set_DisplayNameFR(text)
                        elif lang == 'it-CH':
                            synonymPS.set_text_IT(text)
                            code.set_DisplayNameIT(text)
                        elif lang == 'rm-CH':
                            synonymPS.set_text_RM(text)
                            code.set_DisplayNameRM(text)
                    elif desig_type == 'synonym':
                        if lang == 'de-CH':
                            synonymAS.set_text_DE(text)
                        elif lang == 'en-US':
                            synonymAS.set_text_EN(text)
                        elif lang == 'fr-CH':
                            synonymAS.set_text_FR(text)
                        elif lang == 'it-CH':
                            synonymAS.set_text_IT(text)
                        elif lang == 'rm-CH':
                            synonymAS.set_text_RM(text)
                        
                codeSystem = CodeSystem()
                code_system_id = concept_elem.get('codeSystem')
                codeSystem.set_Title(code_system_mapping.get(code_system_id))
                codeSystem.set_Text_EN(code_system_mapping.get(code_system_id))
                codeSystem.set_Text_DE(code_system_mapping.get(code_system_id))
                codeSystem.set_Text_FR(code_system_mapping.get(code_system_id))
                codeSystem.set_Text_IT(code_system_mapping.get(code_system_id))
                codeSystem.set_Text_RM(code_system_mapping.get(code_system_id))
                codeSystem.set_Identifier(code_system_id)
            
                periodStart = Period("start")
                periodStart.set_Date(Config.DEFAULT_PERIOD_START)
                periodEnd = Period("end")
                periodEnd.set_Date(Config.DEFAULT_PERIOD_END)

                self.codeListEntries.append([code, codeSystem, periodStart, periodEnd, synonymPS, synonymAS])
                self.concept = concept_instance

    def create_concept_output(self):
        output = {
            "data": {
                "codeListEntryValueMaxLength": Config.DEFAULT_VALUE_MAX_LENGTH, # Adjust the value as needed
                "codeListEntryValueType": Config.DEFAULT_VALUE_TYPE, # Adjust the value as needed
                "conceptType": Config.DEFAULT_CONCEPT_TYPE,
                "conformsTo": [],
                "description": {
                    "de": self.concept.get_descriptionDE(),
                    "en": self.concept.get_descriptionEN(),
                    "fr": self.concept.get_descriptionFR(),
                    "it": self.concept.get_descriptionIT()
                },
                "identifier": self.concept.get_identifier(),
                "keywords": [],
                "name": {
                    "de": self.concept.get_name(),
                    "en": self.concept.get_name(),
                    "fr": self.concept.get_name(),
                    "it": self.concept.get_name()
                },
                "publisher": {
                    "identifier": Config.PUBLISHER_IDENTIFIER,
                    "name": {
                        "de": Config.PUBLISHER_NAME,
                        "en": Config.PUBLISHER_NAME,
                        "fr": Config.PUBLISHER_NAME,
                        "it": Config.PUBLISHER_NAME,
                    }
                },
                "responsibleDeputy": self.deputy_person,
                "responsiblePerson": self.responsible_person,
                "themes": [],
                "validFrom": self.concept.get_validFrom(),
                "version": Config.DEFAULT_VERSION
            }
        }    
        return output
    
    def create_codeListEntries_output(self, codeListEntries):
        output = []
        
        for entry_list in codeListEntries:
            code = entry_list[0]  # Code object
            codeSystem = entry_list[1]  # CodeSystem object
            periodStart = entry_list[2]  # Period object
            periodEnd = entry_list[3]  # Period object
            synonymPS = entry_list[4]  # Synonym object
            synonymAS = entry_list[5] if len(entry_list) > 5 else None  # Synonym object (optional)
            
            # Create base annotations list
            annotations = [
                {
                    "identifier": codeSystem.Identifier,
                    "text": {
                        "de": codeSystem.Text_DE,
                        "en": codeSystem.Text_EN,
                        "fr": codeSystem.Text_FR,
                        "it": codeSystem.Text_IT,
                        "rm": codeSystem.Text_RM
                    },
                    "title": codeSystem.Title,
                    "type": "CodeSystem"
                },
                {
                    "identifier": periodEnd.Identifier,
                    "text": {
                        "en": periodEnd.Date
                    },
                    "title": periodEnd.Title,
                    "type": "Period"
                },
                {
                    "identifier": periodStart.Identifier,
                    "text": {
                        "en": periodStart.Date
                    },
                    "title": periodStart.Title,
                    "type": "Period"
                },
                {
                    "identifier": synonymPS.identifier,
                    "text": {
                        "de": synonymPS.Text_DE,
                        "en": synonymPS.Text_EN,
                        "fr": synonymPS.Text_FR,
                        "it": synonymPS.Text_IT,
                        "rm": synonymPS.Text_RM
                    },
                    "title": synonymPS.Title,
                    "type": "Designation"
                }
            ]
            # Add synonymAS to annotations if it exists
            if synonymAS is not None:
                text_dict = {}
                if synonymAS.Text_DE and synonymAS.Text_DE.strip():
                    text_dict["de"] = synonymAS.Text_DE
                if synonymAS.Text_EN and synonymAS.Text_EN.strip():
                    text_dict["en"] = synonymAS.Text_EN
                if synonymAS.Text_FR and synonymAS.Text_FR.strip():
                    text_dict["fr"] = synonymAS.Text_FR
                if synonymAS.Text_IT and synonymAS.Text_IT.strip():
                    text_dict["it"] = synonymAS.Text_IT
                if synonymAS.Text_RM and synonymAS.Text_RM.strip():
                    text_dict["rm"] = synonymAS.Text_RM
            
                if text_dict:  # Only add if there are non-empty text entries
                    annotations.append({
                        "identifier": synonymAS.identifier,
                        "text": text_dict,
                        "title": synonymAS.Title,
                        "type": "Designation"
                    })
            json_entry = {
                "annotations": annotations,
                "code": code.Code,
                "name": {
                    "de": code.DisplayNameDE,
                    "en": code.DisplayNameEN,
                    "fr": code.DisplayNameFR,
                    "it": code.DisplayNameIT,
                    "rm": code.DisplayNameRM
                }
            }
            if code.parentCode:
                json_entry["parentCode"] = code.parentCode
            
            output.append(json_entry)
        
        return {"data": output}

    def write_to_json(self):
        if self.fileExtension == "csv":
            output = self.create_codeListEntries_output(self.codeListEntries)
        elif self.fileExtension == "xml":
            if self.new_concept is True:
                output = self.create_concept_output()
            else:
                output = self.create_codeListEntries_output(self.codeListEntries)
            #output = self.create_codeListEntries_output(self.codeListEntries)
        
        with open(self.json_output_file_path, 'w', encoding="utf-8") as json_file:
            json.dump(output, json_file, indent=4, ensure_ascii=False)

    def get_codelist_id(self, filename):
        # Map filename patterns to enum values
        mapping = {
            'SubmissionSet.contentTypeCode': codeListsId.SubmissionSet_contentTypeCode.value,
            'EprRole': codeListsId.EprRole.value,
            'HCProfessional.hcProfession': codeListsId.HCProfessional_hcProfession.value,
            'DocumentEntry.classCode': codeListsId.DocumentEntry_classCode.value,
            'DocumentEntry.confidentialityCode': codeListsId.DocumentEntry_confidentialityCode.value,
            'DocumentEntry.eventCodeList': codeListsId.DocumentEntry_eventCodeList.value,
            'DocumentEntry.formatCode': codeListsId.DocumentEntry_formatCode.value,
            'DocumentEntry.healthcareFacilityTypeCode': codeListsId.DocumentEntry_healthcareFacilityTypeCode.value,
            'DocumentEntry.mimeType': codeListsId.DocumentEntry_mimeType.value,
            'DocumentEntry.practiceSettingCode': codeListsId.DocumentEntry_practiceSettingCode.value,
            'DocumentEntry.sourcePatientInfo.PID-8': codeListsId.DocumentEntry_sourcePatientInfo_PID_8.value,
            'DocumentEntry.typeCode': codeListsId.DocumentEntry_typeCode.value,
            'EprAuditTrailConsumptionEventType': codeListsId.EprAuditTrailConsumptionEventType.value,
            'EprDeletionStatus': codeListsId.EprDeletionStatus.value,
            'EprPurposeOfUse': codeListsId.EprPurposeOfUse.value,
            'DocumentEntry.languageCode': codeListsId.DocumentEntry_languageCode.value
        }
    
        # Remove file extension and path to get base filename
        # Return corresponding enum value or None if not found
        return mapping.get(filename)

class Code():
    def __init__(self):
        self.Code = ""
        self.DisplayNameEN = ""
        self.DisplayNameDE = ""
        self.DisplayNameFR = ""
        self.DisplayNameIT = ""
        self.DisplayNameRM = ""
        self.parentCode = None
    def set_code(self, code):
        self.Code = code
    def set_DisplayNameEN(self, displayNameEN):
        self.DisplayNameEN = displayNameEN
    def set_DisplayNameDE(self, displayNameDE):
        self.DisplayNameDE = displayNameDE
    def set_DisplayNameFR(self, displayNameFR):
        self.DisplayNameFR = displayNameFR
    def set_DisplayNameIT(self, displayNameIT):
        self.DisplayNameIT = displayNameIT
    def set_DisplayNameRM(self, displayNameRM):
        self.DisplayNameRM = displayNameRM
    def set_parentCode(self, parentCode):
        self.parentCode = parentCode
    def get_code(self):
        return self.Code
    def get_DisplayNameEN(self):
        return self.DisplayNameEN
    def get_DisplayNameDE(self):
        return self.DisplayNameDE
    def get_DisplayNameFR(self):
        return self.DisplayNameFR
    def get_DisplayNameIT(self):
        return self.DisplayNameIT
    def get_DisplayNameRM(self):
        return self.DisplayNameRM

class CodeSystem():
    def __init__(self):
        self.Title = None
        self.Text_DE = None
        self.Text_FR = None
        self.Text_IT = None
        self.Text_EN = None
        self.Text_RM = None
        self.Identifier = None
        self.URI = None
    def set_Title(self, title):
        self.Title = title
    def set_Text_DE(self, textDE):
        self.Text_DE = textDE
    def set_Text_FR(self, textFR):
        self.Text_FR = textFR
    def set_Text_IT(self, textIT):
        self.Text_IT = textIT
    def set_Text_EN(self, textEN):
        self.Text_EN = textEN
    def set_Text_RM(self, textRM):
        self.Text_RM = textRM
    def set_Identifier(self, identifier):
        self.Identifier = identifier
    def get_Title(self):
        return self.Title
    def get_Text_DE(self):
        return self.Text_DE
    def get_Text_FR(self):
        return self.Text_FR
    def get_Text_IT(self):
        return self.Text_IT
    def get_Text_EN(self):
        return self.Text_EN
    def get_Text_RM(self):
        return self.Text_RM
    def get_Identifier(self):
        return self.Identifier
    def get_URI(self):
        return self.URI   

class Period():
    def __init__(self, period_type):
        self.Title = period_type
        self.Date = None
        self.Identifier = period_type
        self.URI = None
    def set_Date(self, date):
        self.Date = date
    def get_Date(self):
        return self.Date

class Synonym():
    def __init__(self, title):
        self.Title = title
        self.Text_DE = ""
        self.Text_FR = ""
        self.Text_IT = ""
        self.Text_EN = ""
        self.Text_RM = ""
        if title == "Preferred":
            self.identifier = "900000000000548007"
        else :
            self.identifier = "900000000000549004"
        self.URI = None

    def set_text_DE(self, text_DE):
        self.Text_DE = text_DE
    def set_text_FR(self, text_FR):
        self.Text_FR = text_FR
    def set_text_IT(self, text_IT):
        self.Text_IT = text_IT
    def set_text_EN(self, text_EN):
        self.Text_EN = text_EN
    def set_text_RM(self, text_RM):
        self.Text_RM = text_RM
    def get_text_DE(self):
        return self.Text_DE
    def get_text_FR(self):
        return self.Text_FR
    def get_text_IT(self):
        return self.Text_IT
    def get_text_EN(self):
        return self.Text_EN
    def get_text_RM(self):
        return self.Text_RM
    def get_identifier(self):
        return self.identifier
    def get_URI(self):
        return self.URI

class concept():
     def __init__(self):
        self.codeListEntryValueMaxLength = Config.DEFAULT_VALUE_MAX_LENGTH
        self.codeListEntryValueType = Config.DEFAULT_VALUE_TYPE
        self.conceptType = Config.DEFAULT_CONCEPT_TYPE
        self.descriptionDE = None
        self.descriptionEN = None
        self.descriptionFR = None
        self.descriptionIT = None
        self.descriptionRM = None
        self.id = None
        self.identifier = None
        self.name = None
        self.publicationLevel = Config.DEFAULT_PUBLICATION_LEVEL
        self.publisher_identifier = Config.PUBLISHER_IDENTIFIER
        self.publisher_name = Config.PUBLISHER_NAME
        self.validFrom = None
        self.version = Config.DEFAULT_VERSION
    
     def set_descriptionDE(self, descriptionDE):
        self.descriptionDE = descriptionDE

     def set_descriptionEN(self, descriptionEN):
        self.descriptionEN = descriptionEN

     def set_descriptionFR(self, descriptionFR):
        self.descriptionFR = descriptionFR

     def set_descriptionIT(self, descriptionIT):
        self.descriptionIT = descriptionIT

     def set_descriptionRM(self, descriptionRM):
        self.descriptionRM = descriptionRM

     def set_id(self, id):
        self.id = id

     def set_identifier(self, identifier):
        self.identifier = identifier

     def set_name (self, name):
        self.name = name
     
     def set_validFrom(self, validFrom):
        self.validFrom = validFrom
     
     def set_version(self, version):
        self.version = version

     def get_descriptionDE(self):
        return self.descriptionDE

     def get_descriptionEN(self):
        return self.descriptionEN

     def get_descriptionFR(self):
        return self.descriptionFR

     def get_descriptionIT(self):
        return self.descriptionIT
     
     def get_name(self):
        return self.name
     
     def get_identifier(self):
        return self.identifier
     
     def get_id(self):
        return self.id
     
     def get_validFrom(self):
        return self.validFrom

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

def main():
    if len(sys.argv) < 5:
        print("Usage: python script_name.py <responsible_key> <deputy_key> <input_folder_path> <output_folder_path> <Date_Valid_From> [-n]")
        print("  <Date_Valid_From>   → date from which the concept is valid. needs to be in 'YYYY-MM-DD' format")
        print("  -n   → create new concept otherwise it will create a new version of existing concept")
        sys.exit(1)

    responsible_key = sys.argv[1]  # First argument (e.g., PGR)
    deputy_key = sys.argv[2]  # Second argument (e.g., SNE)
    input_folder = sys.argv[3]  # Third argument (pass your concept object)
    output_folder = sys.argv[4]  # Fourth argument (pass your codeListEntries object)
    date_valid_from = sys.argv[5]  # Fifth argument (date from which the concept is valid)
    new = len(sys.argv) > 6 and sys.argv[6] == "-n"  # Will be True if -n is present, False otherwise


    os.makedirs(output_folder, exist_ok=True)
    
    print("Starting transformation of files... \n ---------------------------------------------------------------")
    for filename in os.listdir(input_folder):
        if filename.endswith(('.csv', '.xml')):
            input_file = os.path.join(input_folder, filename)
            
            # Match both "VS_" and "VS " and handle space or underscore
            match = re.search(r'VS[ _](.*?)(?:\s*\(|\.)', filename)
            if match:
                concept_name = match.group(1).strip()
                new_filename = concept_name + '_transformed.json'
            else:
                print(f"⚠️ Could not parse concept name from filename: {filename}")
                concept_name = filename.replace('.csv', '').replace('.xml', '')
                new_filename = concept_name + '_transformed.json'

                
            output_file = os.path.join(output_folder, new_filename)
            
            file_name_match = re.search(r'VS[ _](.*?)(?:\s*\(|\.)', filename)
            file_name = file_name_match.group(1).strip() if file_name_match else filename.replace('.csv', '').replace('.xml', '')
            print(f"⏳ Parsing concept name: {file_name}")

            transformer = AD_csv_to_i14y_json(input_file, output_file, file_name, responsible_key, deputy_key, date_valid_from, new)
            
            if filename.endswith('.csv'):
                transformer.process_csv()
            else:
                transformer.process_xml()
                
            transformer.write_to_json()
            print(f"Transformed {filename} -> {new_filename} \n ---------------------------------------------------------------")
    
    print(f"All transformations complete. Output files written to: {output_folder}")

if __name__ == "__main__":
    main()

#TODO: ValidFrom auf Codeebene ist nicht dynamisch.