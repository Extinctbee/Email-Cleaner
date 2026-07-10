import pytest
from unittest.mock import MagicMock, patch
# Assuming your function is in src/GmailScript.py
from src.GmailScript import get_gmail_service 

@patch('src.GmailScript.os.path.exists')
@patch('src.GmailScript.pickle.load')
@patch('src.GmailScript.build')
def test_get_gmail_service_with_valid_db_token(mock_build, mock_pickle_load, mock_os_exists, monkeypatch):
    """
    Test case: The database contains a token path, and the file exists.
    The function should load the token and return the built service without logging in again.
    """
    # 1. ARRANGE: Set up our fake database cursor
    mock_cursor = MagicMock()
    # Simulate cur.fetchone() returning a tuple with a fake file path
    mock_cursor.fetchone.return_value = ("C:/fake/path/token.pickle",) 
    
    # Inject our fake cursor into your database module namespace
    import src.database
    monkeypatch.setattr(src.database, "cur", mock_cursor)

    # Simulate that the token file actually exists on disk
    mock_os_exists.return_value = True
    # Simulate pickle successfully loading a valid credentials object
    mock_creds = MagicMock()
    mock_creds.valid = True
    mock_pickle_load.return_value = mock_creds

    # 2. ACT: Call the actual function with a test email
    service = get_gmail_service("test@gmail.com")

    # 3. ASSERT: Verify the function did exactly what it was supposed to do
    mock_cursor.execute.assert_called_once_with(
        "SELECT refresh_token FROM User_Emails WHERE email = %s", ("test@gmail.com",)
    )
    mock_os_exists.assert_any_call("C:/fake/path/token.pickle")
    mock_build.assert_called_once_with('gmail', 'v1', credentials=mock_creds)