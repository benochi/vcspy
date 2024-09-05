import os
import json
import hashlib
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload

# Constants
PROJECT_DIR = 'C:/path_to_your_project/eq'  # Path to your Unreal Engine project folder
METADATA_FILE = 'file_metadata.json'        # Local file to track changes
FOLDER_ID = 'your_google_drive_folder_id'   # Replace with your Google Drive folder ID where you want to upload

# Google Drive API setup
SCOPES = ['https://www.googleapis.com/auth/drive.file']

def authenticate_gdrive():
    creds = None
    if os.path.exists('token.json'):
        creds = Credentials.from_authorized_user_file('token.json', SCOPES)
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            flow = InstalledAppFlow.from_client_secrets_file('credentials.json', SCOPES)
            creds = flow.run_local_server(port=0)
        with open('token.json', 'w') as token:
            token.write(creds.to_json())
    return build('drive', 'v3', credentials=creds)

def get_file_hash(filepath):
    """Generate SHA-256 hash of the file."""
    sha256_hash = hashlib.sha256()
    with open(filepath, "rb") as f:
        for byte_block in iter(lambda: f.read(4096), b""):
            sha256_hash.update(byte_block)
    return sha256_hash.hexdigest()

def load_metadata():
    """Load or create metadata for tracking file changes."""
    if os.path.exists(METADATA_FILE):
        with open(METADATA_FILE, 'r') as f:
            return json.load(f)
    return {}

def save_metadata(metadata):
    """Save the updated metadata to file."""
    with open(METADATA_FILE, 'w') as f:
        json.dump(metadata, f, indent=4)

def upload_to_gdrive(service, file_path, folder_id):
    """Upload a file to Google Drive."""
    file_name = os.path.basename(file_path)
    media = MediaFileUpload(file_path, resumable=True)
    request = service.files().create(
        media_body=media,
        body={'name': file_name, 'parents': [folder_id]},
        fields='id'
    ).execute()
    print(f"Uploaded {file_name} to Google Drive (ID: {request.get('id')})")

def main():
    # Authenticate Google Drive API
    service = authenticate_gdrive()

    # Load previous file metadata
    file_metadata = load_metadata()

    # Iterate through project files
    for root, _, files in os.walk(PROJECT_DIR):
        for file in files:
            file_path = os.path.join(root, file)
            file_hash = get_file_hash(file_path)
            relative_path = os.path.relpath(file_path, PROJECT_DIR)

            # Compare with previous hash
            if relative_path not in file_metadata or file_metadata[relative_path] != file_hash:
                print(f"Detected changes in: {relative_path}")
                upload_to_gdrive(service, file_path, FOLDER_ID)
                file_metadata[relative_path] = file_hash

    # Save the updated metadata
    save_metadata(file_metadata)
    print("Sync completed.")

if __name__ == '__main__':
    main()
