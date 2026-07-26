"""
YouTube Live Streaming Tool - Streamlit App
============================================
Fitur:
- Login Google (OAuth 2.0)
- Pilih Channel YouTube
- Buat Live Stream (Broadcast + Stream)
- Mulai / Hentikan Live Streaming
- Tampilkan Stream Key & RTMP URL
- Riwayat Broadcast
"""

import os
import json
import time
from datetime import datetime, timezone, timedelta

import streamlit as st
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow, Flow
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
from google.auth.transport.requests import Request

# ---------------------------------------------------------------------------
# Konfigurasi
# ---------------------------------------------------------------------------
st.set_page_config(
    page_title="YouTube Live Streaming Tool",
    page_icon="🔴",
    layout="wide",
    initial_sidebar_state="expanded",
)

SCOPES = [
    "https://www.googleapis.com/auth/youtube",
    "https://www.googleapis.com/auth/youtube.force-ssl",
]

# File penyimpanan credentials (local)
CLIENT_SECRETS_FILE = "client_secret.json"
TOKEN_FILE = "token.json"

# Timezone WIB (Jakarta)
WIB = timezone(timedelta(hours=7))


# ---------------------------------------------------------------------------
# Helper OAuth Google
# ---------------------------------------------------------------------------
def load_credentials():
    """Muat kredensial dari session_state atau file token."""
    if "creds" in st.session_state and st.session_state.creds:
        return st.session_state.creds

    if os.path.exists(TOKEN_FILE):
        creds = Credentials.from_authorized_user_file(TOKEN_FILE, SCOPES)
        if creds and creds.valid:
            st.session_state.creds = creds
            return creds
        if creds and creds.expired and creds.refresh_token:
            try:
                creds.refresh(Request())
                save_credentials(creds)
                st.session_state.creds = creds
                return creds
            except Exception:
                pass
    return None


def save_credentials(creds):
    """Simpan kredensial ke file."""
    with open(TOKEN_FILE, "w") as f:
        f.write(creds.to_json())
    st.session_state.creds = creds


def run_oauth_flow(client_config):
    """Jalankan OAuth flow via browser lokal, pakai redirect_uri localhost."""
    flow = Flow.from_client_config(
        client_config,
        scopes=SCOPES,
        redirect_uri="urn:ietf:wg:oauth:2.0:oob",
    )
    auth_url, _ = flow.authorization_url(
        access_type="offline",
        prompt="consent",
        include_granted_scopes="true",
    )
    return flow, auth_url


def run_local_oauth(client_config):
    """Jalankan OAuth lokal dengan server (lebih mudah dijalankan di komputer lokal)."""
    flow = InstalledAppFlow.from_client_config(
        client_config,
        scopes=SCOPES,
    )
    creds = flow.run_local_server(
        port=8501,
        access_type="offline",
        prompt="consent",
    )
    return creds


# ---------------------------------------------------------------------------
# Helper YouTube API
# ---------------------------------------------------------------------------
def get_youtube_service(creds):
    return build("youtube", "v3", credentials=creds)


def list_channels(youtube):
    """Ambil daftar channel yang dimiliki akun."""
    resp = youtube.channels().list(
        part="id,snippet,brandingSettings,statistics",
        mine=True,
    ).execute()
    return resp.get("items", [])


def list_broadcasts(youtube, broadcast_status="all"):
    """Ambil daftar broadcast."""
    results = []
    resp = youtube.liveBroadcasts().list(
        part="id,snippet,status,contentDetails",
        mine=True,
        broadcastStatus=broadcast_status,
        maxResults=50,
    ).execute()
    results.extend(resp.get("items", []))
    return results


def create_broadcast(youtube, title, description, start_time, privacy="unlisted"):
    """Buat broadcast baru."""
    resp = youtube.liveBroadcasts().insert(
        part="id,snippet,status,contentDetails",
        body={
            "snippet": {
                "title": title,
                "description": description,
                "scheduledStartTime": start_time.isoformat(),
            },
            "status": {
                "privacyStatus": privacy,
                "selfDeclaredMadeForKids": False,
            },
            "contentDetails": {
                "enableAutoStart": False,
                "enableAutoStop": True,
                "enableDvr": True,
                "enableContentEncryption": False,
                "latencyPreference": "low",
                "monitorStream": {
                    "enableMonitorStream": True,
                    "broadcastStreamDelayMs": 1,
                },
            },
        },
    ).execute()
    return resp


def create_stream(youtube, title):
    """Buat stream baru."""
    resp = youtube.liveStreams().insert(
        part="id,snippet,cdn,status",
        body={
            "snippet": {
                "title": title,
            },
            "cdn": {
                "ingestionType": "rtmp",
                "frameRate": "variable",
                "resolution": "variable",
                "format": "",
            },
            "contentDetails": {
                "isReusable": False,
            },
        },
    ).execute()
    return resp


def bind_broadcast(youtube, broadcast_id, stream_id):
    """Ikat broadcast ke stream."""
    return youtube.liveBroadcasts().bind(
        part="id,status,contentDetails",
        id=broadcast_id,
        streamId=stream_id,
    ).execute()


def transition_broadcast(youtube, broadcast_id, status):
    """Transisi status broadcast: testing, live, complete."""
    return youtube.liveBroadcasts().transition(
        broadcastStatus=status,
        id=broadcast_id,
        part="id,status",
    ).execute()


def get_broadcast_status(youtube, broadcast_id):
    resp = youtube.liveBroadcasts().list(
        part="id,status,contentDetails",
        id=broadcast_id,
    ).execute()
    items = resp.get("items", [])
    return items[0] if items else None


# ---------------------------------------------------------------------------
# Sidebar - Status Login
# ---------------------------------------------------------------------------
def sidebar_auth():
    st.sidebar.header("🔐 Autentikasi Google")

    creds = load_credentials()

    if creds:
        # Info user
        try:
            yt = get_youtube_service(creds)
            ch = yt.channels().list(part="snippet", mine=True).execute()
            if ch.get("items"):
                name = ch["items"][0]["snippet"]["title"]
                st.sidebar.success(f"✅ Login sebagai: **{name}**")
        except Exception:
            pass

        if st.sidebar.button("🚪 Logout", use_container_width=True):
            if os.path.exists(TOKEN_FILE):
                os.remove(TOKEN_FILE)
            if "creds" in st.session_state:
                del st.session_state["creds"]
            if "selected_channel" in st.session_state:
                del st.session_state["selected_channel"]
            st.rerun()
        return creds

    # Belum login
    st.sidebar.info("Silakan login dengan akun Google Anda.")

    # Cek apakah client_secret.json sudah ada
    if not os.path.exists(CLIENT_SECRETS_FILE):
        st.sidebar.warning(
            "⚠️ File `client_secret.json` belum ada.\n\n"
            "Ikuti langkah di halaman **Setup** untuk mengunduh OAuth Client ID "
            "dari Google Cloud Console."
        )

        # Upload file
        uploaded = st.sidebar.file_uploader(
            "Upload client_secret.json:",
            type=["json"],
        )
        if uploaded:
            data = json.loads(uploaded.read())
            with open(CLIENT_SECRETS_FILE, "w") as f:
                json.dump(data, f)
            st.sidebar.success("✅ File client_secret.json tersimpan!")
            st.rerun()
        return None
    else:
        st.sidebar.success("✅ client_secret.json siap!")
        if st.sidebar.button("🔑 Login dengan Google", use_container_width=True, type="primary"):
            st.session_state["oauth_start"] = True
            st.rerun()
        return None


# ---------------------------------------------------------------------------
# Halaman: Setup / Panduan
# ---------------------------------------------------------------------------
def page_setup():
    st.title("📘 Panduan Setup OAuth Google")
    st.markdown(
        """
        Untuk menggunakan tool ini, Anda perlu membuat **OAuth 2.0 Client ID** di
        Google Cloud Console.

        ### Langkah-langkah:

        1. **Buka Google Cloud Console** → https://console.cloud.google.com/
        2. **Buat Project Baru** atau pilih project yang sudah ada.
        3. **Aktifkan YouTube Data API v3:**
           - Buka menu **APIs & Services → Library**
           - Cari **YouTube Data API v3** → **Enable**
        4. **Buat OAuth Consent Screen:**
           - Menu **APIs & Services → OAuth Consent Screen**
           - Pilih **External** → Create
           - Isi App name, User support email, Developer contact
           - Save & Continue
           - Di tab **Scopes**, tambahkan scope:
             ```
             https://www.googleapis.com/auth/youtube
             ```
           - Save & Continue
           - Di tab **Test Users**, tambahkan email Anda (karena app dalam status Testing)
        5. **Buat OAuth Client ID:**
           - Menu **APIs & Services → Credentials**
           - **Create Credentials → OAuth client ID**
           - Application type: **Desktop app** (direkomendasikan) atau **Web application**
           - Jika Web app, tambahkan **Authorized redirect URIs**:
             - `http://localhost:8501/`
           - Klik **Create** → Download JSON
        6. **Upload file JSON** tersebut di sidebar (panel kiri).

        > ⚠️ **Catatan:** Aplikasi dalam status "Testing" hanya bisa digunakan oleh
        > email yang terdaftar sebagai Test User. Untuk publish ke publik perlu
        > proses verifikasi dari Google.
        """
    )

    if os.path.exists(CLIENT_SECRETS_FILE):
        st.success(f"✅ `{CLIENT_SECRETS_FILE}` sudah tersedia!")
        with open(CLIENT_SECRETS_FILE) as f:
            data = json.load(f)
        try:
            cid = (
                data.get("installed", data.get("web", {})).get("client_id", "?")
            )
            st.info(f"Client ID: `{cid[:30]}...`")
        except Exception:
            pass


# ---------------------------------------------------------------------------
# Halaman: OAuth Login Flow
# ---------------------------------------------------------------------------
def page_oauth_flow():
    st.title("🔑 Login Google")

    try:
        with open(CLIENT_SECRETS_FILE) as f:
            client_config = json.load(f)
    except Exception as e:
        st.error(f"Gagal membaca client_secret.json: {e}")
        return

    # Jika key sudah ada, sudah login
    creds = load_credentials()
    if creds:
        st.success("✅ Sudah login!")
        if st.button("Lanjut ke Dashboard →", type="primary"):
            st.session_state["page"] = "dashboard"
            st.rerun()
        return

    # Deteksi apakah ini web atau installed app
    app_type = "installed" if "installed" in client_config else "web"

    st.info(
        "Klik tombol di bawah, login dengan akun Google Anda, lalu "
        "otorisasi aplikasi ini untuk mengelola channel YouTube Anda."
    )

    if app_type == "installed":
        st.markdown("#### Mode: Installed App (Loopback)")
        if st.button("🚀 Mulai Login (Buka Browser)", type="primary"):
            with st.spinner("Menunggu autentikasi di browser..."):
                try:
                    creds = run_local_oauth(client_config)
                    save_credentials(creds)
                    st.success("✅ Login berhasil!")
                    st.rerun()
                except Exception as e:
                    st.error(f"Gagal login: {e}")
    else:
        st.markdown("#### Mode: Web App")
        flow, auth_url = run_oauth_flow(client_config)
        st.markdown(
            f"1. **Buka URL ini di browser:**\n\n👉 [{auth_url}]({auth_url})"
        )
        st.write("2. Login & otorisasi, lalu **copy authorization code** yang muncul.")
        code = st.text_input("3. Paste authorization code di sini:", type="password")
        if st.button("✅ Verifikasi Code", type="primary"):
            try:
                flow.fetch_token(code=code)
                creds = flow.credentials
                save_credentials(creds)
                st.success("✅ Login berhasil!")
                st.rerun()
            except Exception as e:
                st.error(f"Gagal: {e}")


# ---------------------------------------------------------------------------
# Halaman: Pilih Channel
# ---------------------------------------------------------------------------
def page_select_channel(youtube):
    st.title("📺 Pilih Channel YouTube")
    channels = list_channels(youtube)

    if not channels:
        st.error("Tidak ada channel YouTube yang ditemukan pada akun ini.")
        return

    st.write(f"Ditemukan **{len(channels)}** channel pada akun Anda:")

    for idx, ch in enumerate(channels):
        snippet = ch["snippet"]
        stats = ch.get("statistics", {})
        col1, col2 = st.columns([1, 5])
        with col1:
            thumb = snippet.get("thumbnails", {}).get("default", {}).get("url", "")
            if thumb:
                st.image(thumb, width=80)
        with col2:
            st.markdown(f"### {snippet['title']}")
            st.caption(f"ID: `{ch['id']}`")
            st.write(
                f"👥 {stats.get('subscriberCount', '0')} subscriber · "
                f"🎬 {stats.get('videoCount', '0')} video · "
                f"👁️ {stats.get('viewCount', '0')} views"
            )

        if st.button(
            f"✅ Gunakan Channel Ini",
            key=f"ch_{ch['id']}",
            type="primary",
        ):
            st.session_state.selected_channel = ch
            st.success(f"Channel **{snippet['title']}** dipilih!")
            time.sleep(0.8)
            st.session_state.page = "dashboard"
            st.rerun()
        st.divider()


# ---------------------------------------------------------------------------
# Halaman: Dashboard / Buat Live Stream
# ---------------------------------------------------------------------------
def page_dashboard(youtube):
    channel = st.session_state.get("selected_channel")
    if not channel:
        st.warning("Silakan pilih channel terlebih dahulu.")
        if st.button("Ke halaman Pilih Channel"):
            st.session_state.page = "select_channel"
            st.rerun()
        return

    ch_title = channel["snippet"]["title"]
    ch_id = channel["id"]

    st.title(f"🔴 YouTube Live Streaming Dashboard")
    st.caption(f"Channel: **{ch_title}** (`{ch_id}`)")

    tab1, tab2, tab3 = st.tabs(
        ["🎥 Buat Live Stream Baru", "📋 Kelola Broadcast Aktif", "📜 Riwayat Broadcast"]
    )

    # ---- TAB 1: Buat Live Baru ----
    with tab1:
        st.subheader("Buat Live Streaming Baru")

        with st.form("create_live_form"):
            title = st.text_input(
                "Judul Live Stream",
                value=f"Live Stream - {datetime.now(WIB).strftime('%d %b %Y %H:%M')} WIB",
            )
            description = st.text_area(
                "Deskripsi",
                value="Live streaming menggunakan tool YouTube Live Manager.\n\nJangan lupa like & subscribe!",
                height=120,
            )
            col_a, col_b = st.columns(2)
            with col_a:
                sched_date = st.date_input(
                    "Tanggal Mulai",
                    value=datetime.now(WIB).date(),
                )
                sched_time = st.time_input(
                    "Jam Mulai (WIB)",
                    value=(datetime.now(WIB) + timedelta(minutes=5)).time(),
                )
            with col_b:
                privacy = st.selectbox(
                    "Privasi",
                    ["private", "unlisted", "public"],
                    index=1,
                    help="public = siapa saja bisa menonton, unlisted = via link, private = hanya Anda",
                )
                latency = st.selectbox(
                    "Latency",
                    [("Normal", "normal"), ("Low", "low"), ("Ultra Low", "ultraLow")],
                    format_func=lambda x: x[0],
                    index=1,
                )

            submit = st.form_submit_button("🚀 Buat Live Stream", type="primary", use_container_width=True)

        if submit:
            if not title.strip():
                st.error("Judul tidak boleh kosong!")
            else:
                try:
                    start_dt = datetime.combine(sched_date, sched_time, tzinfo=WIB)
                    start_utc = start_dt.astimezone(timezone.utc)

                    with st.spinner("Membuat broadcast & stream..."):
                        broadcast = create_broadcast(
                            youtube, title, description, start_utc, privacy
                        )
                        stream = create_stream(youtube, title + " (Stream)")
                        bind_broadcast(youtube, broadcast["id"], stream["id"])

                    st.session_state["last_broadcast"] = broadcast
                    st.session_state["last_stream"] = stream

                    st.success(f"✅ Live stream **{title}** berhasil dibuat!")
                    st.balloons()
                except HttpError as e:
                    st.error(f"YouTube API Error: {e}")
                except Exception as e:
                    st.error(f"Error: {e}")

        # Tampilkan info stream terakhir dibuat
        if "last_broadcast" in st.session_state and "last_stream" in st.session_state:
            b = st.session_state.last_broadcast
            s = st.session_state.last_stream
            st.divider()
            st.subheader("📡 Detail Live Stream Terbaru")

            ingestion = s["cdn"]["ingestionInfo"]
            rtmp_url = ingestion["ingestionAddress"]
            stream_name = ingestion["streamName"]
            rtmp_full = f"{rtmp_url}/{stream_name}"
            watch_url = f"https://youtu.be/{b['id']}"

            col1, col2 = st.columns(2)
            with col1:
                st.markdown("**RTMP Ingestion URL:**")
                st.code(rtmp_url, language="bash")
                st.markdown("**Stream Key:**")
                st.code(stream_name, language="bash")
                st.markdown("**Full RTMP URL (copy ke OBS/vMix/Wirecast):**")
                st.code(rtmp_full, language="bash")

            with col2:
                st.markdown("**Link Video (setelah live):**")
                st.code(watch_url)
                st.markdown("**Status Broadcast:**")
                st.info(b["status"]["lifeCycleStatus"])
                st.markdown("**Status Stream:**")
                st.info(s.get("status", {}).get("streamStatus", "created"))

            st.warning(
                "⚠️ Masukkan RTMP URL & Stream Key di atas ke software encoder Anda "
                "(OBS Studio, vMix, Wirecast, dll), lalu mulai mengirim video."
            )

            col_x, col_y, col_z = st.columns(3)
            with col_x:
                if st.button("▶️ Mulai Testing", use_container_width=True):
                    try:
                        transition_broadcast(youtube, b["id"], "testing")
                        st.success("Mode testing aktif. Video mulai dikirim ke YouTube.")
                        time.sleep(1)
                        st.rerun()
                    except HttpError as e:
                        st.error(f"Error: {e}")
            with col_y:
                if st.button("🔴 GO LIVE!", use_container_width=True, type="primary"):
                    try:
                        transition_broadcast(youtube, b["id"], "live")
                        st.success("✅ SEDANG LIVE!")
                        st.rerun()
                    except HttpError as e:
                        st.error(f"Error: {e}")
            with col_z:
                if st.button("⏹️ Stop Live", use_container_width=True):
                    try:
                        transition_broadcast(youtube, b["id"], "complete")
                        st.success("Live dihentikan. Video akan diproses.")
                        st.rerun()
                    except HttpError as e:
                        st.error(f"Error: {e}")

    # ---- TAB 2: Kelola broadcast aktif ----
    with tab2:
        st.subheader("Broadcast Aktif / Siap Live")
        try:
            broadcasts = []
            for status in ["active", "upcoming"]:
                broadcasts.extend(list_broadcasts(youtube, status))

            if not broadcasts:
                st.info("Tidak ada broadcast aktif. Buat baru di tab **Buat Live Stream Baru**.")
            else:
                for b in broadcasts:
                    snip = b["snippet"]
                    stat = b["status"]
                    cid = b["id"]
                    with st.expander(
                        f"📹 {snip['title']} — Status: {stat['lifeCycleStatus']}"
                    ):
                        st.write(f"**ID:** `{cid}`")
                        st.write(f"**Privacy:** {stat['privacyStatus']}")
                        st.write(f"**Jadwal:** {snip.get('scheduledStartTime', '-')}")
                        st.write(f"**URL:** https://youtu.be/{cid}")

                        # Cari stream bound
                        bound_stream_id = b.get("contentDetails", {}).get("boundStreamId")
                        if bound_stream_id:
                            st.write(f"**Stream ID:** `{bound_stream_id}`")
                            try:
                                sresp = youtube.liveStreams().list(
                                    part="id,snippet,cdn,status", id=bound_stream_id
                                ).execute()
                                sitems = sresp.get("items", [])
                                if sitems:
                                    s = sitems[0]
                                    ing = s["cdn"]["ingestionInfo"]
                                    st.markdown("**RTMP:**")
                                    st.code(f"{ing['ingestionAddress']}/{ing['streamName']}")
                                    st.write(f"**Stream Status:** `{s.get('status', {}).get('streamStatus', '?')}`")
                            except Exception as ex:
                                st.warning(f"Gagal ambil info stream: {ex}")

                        cc1, cc2, cc3 = st.columns(3)
                        life = stat["lifeCycleStatus"]
                        with cc1:
                            if life in ("created", "ready", "testStarting"):
                                if st.button("▶️ Testing", key=f"t_{cid}"):
                                    transition_broadcast(youtube, cid, "testing")
                                    st.rerun()
                        with cc2:
                            if life in ("ready", "testing", "testStarting"):
                                if st.button("🔴 GO LIVE", key=f"l_{cid}", type="primary"):
                                    transition_broadcast(youtube, cid, "live")
                                    st.rerun()
                        with cc3:
                            if life in ("live", "liveStarting", "testing"):
                                if st.button("⏹️ Stop", key=f"s_{cid}"):
                                    transition_broadcast(youtube, cid, "complete")
                                    st.rerun()
        except HttpError as e:
            st.error(f"Error mengambil broadcast: {e}")

    # ---- TAB 3: Riwayat ----
    with tab3:
        st.subheader("Riwayat Broadcast (Completed)")
        try:
            completed = list_broadcasts(youtube, "completed")
            if not completed:
                st.info("Belum ada broadcast yang selesai.")
            else:
                rows = []
                for b in completed:
                    snip = b["snippet"]
                    stat = b["status"]
                    rows.append({
                        "Judul": snip["title"],
                        "ID": b["id"],
                        "Mulai": snip.get("actualStartTime", snip.get("scheduledStartTime", "-")),
                        "Selesai": snip.get("actualEndTime", "-"),
                        "Privasi": stat["privacyStatus"],
                        "URL": f"https://youtu.be/{b['id']}",
                    })
                import pandas as pd
                df = pd.DataFrame(rows)
                st.dataframe(df, use_container_width=True)
        except HttpError as e:
            st.error(f"Error: {e}")


# ---------------------------------------------------------------------------
# Navigasi Utama
# ---------------------------------------------------------------------------
def main():
    # Styling tambahan
    st.markdown(
        """
        <style>
        .block-container {padding-top: 2rem; padding-bottom: 2rem;}
        .stButton>button {font-weight: 600;}
        </style>
        """,
        unsafe_allow_html=True,
    )

    # Menu navigasi
    menu = st.sidebar.radio(
        "📂 Menu",
        ["🏠 Dashboard", "📺 Pilih Channel", "🔑 Login", "📘 Setup"],
        index=0,
    )

    creds = sidebar_auth()

    # Cek file client_secret
    if not os.path.exists(CLIENT_SECRETS_FILE) and menu != "📘 Setup":
        st.warning("⚠️ File `client_secret.json` belum ada. Silakan ke halaman **Setup** dulu.")
        page_setup()
        return

    # Logika tiap halaman
    if menu == "📘 Setup":
        page_setup()
        return

    if menu == "🔑 Login":
        page_oauth_flow()
        return

    # Halaman yang butuh login
    if not creds:
        st.warning("🔐 Anda belum login. Silakan login di halaman **Login**.")
        page_oauth_flow()
        return

    youtube = get_youtube_service(creds)

    if menu == "📺 Pilih Channel":
        page_select_channel(youtube)
        return

    if menu == "🏠 Dashboard":
        if "selected_channel" not in st.session_state:
            st.info("Belum pilih channel. Mengambil daftar channel Anda...")
            page_select_channel(youtube)
        else:
            page_dashboard(youtube)
        return


if __name__ == "__main__":
    main()
