import pandas as pd
from google.oauth2.service_account import Credentials
from googleapiclient.discovery import build
import streamlit as st

def get_google_sheets_credentials():
    """Get Google Sheets credentials from Streamlit secrets"""
    try:
        # Debug: Print available secrets keys
        # st.write("Available secrets keys:", list(st.secrets.keys()))
         
        # Get the service account info from secrets
        service_account_info = {
            "type": st.secrets["gcp_service_account"]["type"],
            "project_id": st.secrets["gcp_service_account"]["project_id"],
            "private_key_id": st.secrets["gcp_service_account"]["private_key_id"],
            "private_key": st.secrets["gcp_service_account"]["private_key"].replace("\\n", "\n"),
            "client_email": st.secrets["gcp_service_account"]["client_email"],
            "client_id": st.secrets["gcp_service_account"]["client_id"],
            "auth_uri": st.secrets["gcp_service_account"]["auth_uri"],
            "token_uri": st.secrets["gcp_service_account"]["token_uri"],
            "auth_provider_x509_cert_url": st.secrets["gcp_service_account"]["auth_provider_x509_cert_url"],
            "client_x509_cert_url": st.secrets["gcp_service_account"]["client_x509_cert_url"]
        }
        
        # Debug: Print service account email
        # st.write("Service Account Email:", service_account_info["client_email"])
        
        return Credentials.from_service_account_info(
            service_account_info,
            scopes=["https://www.googleapis.com/auth/spreadsheets"]
        )
    except Exception as e:
        st.error(f"Error loading Google Sheets credentials: {str(e)}")
        st.error("Full error details:", str(e.__class__.__name__))
        return None

def get_sheet_data(spreadsheet_id, range_name):
    """Read data from Google Sheet"""
    try:
        creds = get_google_sheets_credentials()
        if not creds:
            return None
            
        service = build('sheets', 'v4', credentials=creds)
        sheet = service.spreadsheets()
        
        result = sheet.values().get(
            spreadsheetId=spreadsheet_id,
            range=range_name
        ).execute()
        
        values = result.get('values', [])
        if not values:
            return pd.DataFrame()
            
        # Get the number of columns from the header row
        num_columns = len(values[0])
        
        # Debug information
        # st.write(f"Number of columns in header: {num_columns}")
        # st.write(f"Number of rows in data: {len(values)}")
        
        # Find the maximum number of columns in any row
        max_columns = max(len(row) for row in values)
        if max_columns > num_columns:
            st.warning(f"Some rows have more columns ({max_columns}) than the header ({num_columns}). Truncating extra columns.")
            # Truncate rows that are too long
            values = [row[:num_columns] for row in values]
        
        # Pad shorter rows with empty strings
        padded_values = []
        for i, row in enumerate(values):
            if len(row) < num_columns:
                # st.warning(f"Row {i+1} has fewer columns ({len(row)}) than the header ({num_columns}). Padding with empty strings.")
                row = row + [''] * (num_columns - len(row))
            padded_values.append(row)
            
        # Convert to DataFrame
        df = pd.DataFrame(padded_values[1:], columns=padded_values[0])
        
        # Debug information about the final DataFrame
        # st.write(f"Final DataFrame shape: {df.shape}")
        
        return df
        
    except Exception as e:
        st.error(f"Error reading from Google Sheet: {str(e)}")
        st.error("Full error details:", str(e.__class__.__name__))
        return None

def update_sheet_data(spreadsheet_id, range_name, df):
    """Update data in Google Sheet"""
    try:
        creds = get_google_sheets_credentials()
        if not creds:
            return False
            
        service = build('sheets', 'v4', credentials=creds)
        sheet = service.spreadsheets()
        
        # First, clear the existing data in the range
        sheet.values().clear(
            spreadsheetId=spreadsheet_id,
            range=range_name
        ).execute()
        
        # Convert DataFrame to list of lists
        values = [df.columns.tolist()] + df.values.tolist()
        
        # Debug output
        # st.write("[update_sheet_data] Values to be sent:", values[:3])  # Show only first 2 rows for brevity
        # st.write("[update_sheet_data] Number of rows to send (including header):", len(values))
        # st.write("[update_sheet_data] Number of columns:", len(df.columns))
        
        body = {
            'values': values
        }
        
        # Update with new data
        result = sheet.values().update(
            spreadsheetId=spreadsheet_id,
            range=range_name,
            valueInputOption='USER_ENTERED',  # Changed from 'RAW' to 'USER_ENTERED'
            body=body
        ).execute()
        
        # st.write("[update_sheet_data] Google API response:", result)
        
        return True
        
    except Exception as e:
        st.error(f"Error updating Google Sheet: {str(e)}")
        st.error("Full error details:", str(e.__class__.__name__))
        return False

def append_sheet_data(spreadsheet_id, range_name, df):
    """Append data to Google Sheet"""
    try:
        creds = get_google_sheets_credentials()
        if not creds:
            return False
            
        service = build('sheets', 'v4', credentials=creds)
        sheet = service.spreadsheets()
        
        # Convert DataFrame to list of lists
        values = df.values.tolist()
        
        body = {
            'values': values
        }
        
        result = sheet.values().append(
            spreadsheetId=spreadsheet_id,
            range=range_name,
            valueInputOption='RAW',
            body=body
        ).execute()
        
        return True
        
    except Exception as e:
        st.error(f"Error appending to Google Sheet: {str(e)}")
        return False 
