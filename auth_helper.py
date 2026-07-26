"""
Helper autentikasi Google OAuth 2.0 untuk YouTube Data API v3.
Modul ini menyediakan fungsi-fungsi untuk:
- Memulai flow OAuth (loopback / web)
- Menyimpan & memuat kredensial
- Membuat service YouTube
"""

import os
import json
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow, Flow
from google.auth.transport.requests import Request
from googleapiclient.discovery import build

SCOPES = [
    "https://www.googleapis.com/auth/youtube",
    "https://www.googleapis.com/auth/youtube.force-ssl",
]


def get_credentials(client_secrets_file="client_secret.json", token_file="token.json"):
    """Dapatkan kredensial valid. Gunakan refresh token jika ada,
    jika tidak jalankan flow OAuth interaktif."""
    creds = None
    if os.path.exists(token_file):
        creds = Credentials.from_authorized_user_file(token_file, SCOPES)

    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            if not os.path.exists(client_secrets_file):
                raise FileNotFoundError(
                    f"File {client_secrets_file} tidak ditemukan. "
                    "Download OAuth Client ID dari Google Cloud Console dulu."
                )
            flow = InstalledAppFlow.from_client_secrets_file(client_secrets_file, SCOPES)
            creds = flow.run_local_server(port=0, access_type="offline", prompt="consent")

        with open(token_file, "w") as f:
            f.write(creds.to_json())

    return creds


def create_auth_url(client_secrets_file="client_secret.json", redirect_uri=None):
    """Buat URL otorisasi untuk mode web. Mengembalikan (flow, auth_url)."""
    with open(client_secrets_file) as f:
        client_config = json.load(f)

    if redirect_uri is None:
        redirect_uri = "urn:ietf:wg:oauth:2.0:oob"

    flow = Flow.from_client_config(client_config, scopes=SCOPES, redirect_uri=redirect_uri)
    auth_url, state = flow.authorization_url(
        access_type="offline",
        prompt="consent",
        include_granted_scopes="true",
    )
    return flow, auth_url, state


def exchange_code(flow, code, token_file="token.json"):
    """Tukar authorization code menjadi kredensial, simpan ke file."""
    flow.fetch_token(code=code)
    creds = flow.credentials
    with open(token_file, "w") as f:
        f.write(creds.to_json())
    return creds


def get_youtube_service(creds):
    """Buat service YouTube Data API v3."""
    return build("youtube", "v3", credentials=creds)


def logout(token_file="token.json"):
    """Hapus token file (logout)."""
    if os.path.exists(token_file):
        os.remove(token_file)
