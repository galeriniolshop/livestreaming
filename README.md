# 🔴 YouTube Live Streaming Tool (Streamlit)

Tool berbasis web (Streamlit) untuk **membuat dan mengelola live streaming YouTube**
lengkap dengan **Login Google OAuth 2.0**, **pemilihan channel**, dan
**pembuatan live stream baru** beserta kontrol Start/Stop.

![Python](https://img.shields.io/badge/Python-3.9+-blue)
![Streamlit](https://img.shields.io/badge/Streamlit-1.32+-red)
![YouTube API](https://img.shields.io/badge/YouTube%20Data%20API-v3-orange)

---

## ✨ Fitur

| Fitur | Status |
|---|---|
| 🔐 Login dengan akun Google (OAuth 2.0) | ✅ |
| 📺 Pilih channel YouTube | ✅ |
| 🎥 Buat live broadcast baru | ✅ |
| 📡 Buat streaming endpoint (RTMP) | ✅ |
| 🔗 Bind broadcast & stream otomatis | ✅ |
| ▶️ Kontrol Testing / Go Live / Stop | ✅ |
| 🔑 Tampilkan Stream Key & RTMP URL | ✅ |
| 📊 Daftar broadcast aktif & riwayat | ✅ |
| ⚙️ Setting latency (normal/low/ultra-low) | ✅ |
| 🔒 Pilihan privasi (public/unlisted/private) | ✅ |

---

## 🚀 Cara Menjalankan (Lokal)

### 1. Clone & install dependensi

```bash
git clone <repo-url> livestreaming
cd livestreaming
pip install -r requirements.txt
```

### 2. Setup Google OAuth 2.0

1. Buka [Google Cloud Console](https://console.cloud.google.com/)
2. Buat project baru
3. **Enable API:** `APIs & Services → Library` → cari **YouTube Data API v3** → **Enable**
4. **OAuth Consent Screen:**
   - Pilih **External** → Create
   - Isi App name, email support, email developer
   - Di tab **Scopes**, tambahkan:
     ```
     https://www.googleapis.com/auth/youtube
     ```
   - Di tab **Test Users**, tambahkan email Google Anda sendiri
5. **Buat Credentials:**
   - `APIs & Services → Credentials → Create Credentials → OAuth client ID`
   - Pilih **Desktop app** (paling mudah untuk lokal)
   - Klik **Create**, lalu **Download JSON**
6. Simpan file tersebut sebagai `client_secret.json` di folder project
   (atau upload lewat UI sidebar aplikasi nanti)

### 3. Jalankan aplikasi

```bash
streamlit run app.py
```

Buka browser di **http://localhost:8501**

4. Klik tombol **🔑 Login dengan Google** di sidebar → login & otorisasi.
5. Pilih channel YouTube yang ingin digunakan.
6. Buat live stream baru → masukkan RTMP URL & Stream Key ke OBS / vMix / encoder lain.
7. Klik **▶️ Testing**, setelah video terkirim klik **🔴 GO LIVE!**

---

## ☁️ Deploy ke Streamlit Cloud

> ⚠️ **Catatan penting:** OAuth tipe "Desktop app" tidak cocok untuk Streamlit Cloud
> karena di cloud tidak bisa membuka browser lokal. Untuk deploy ke Streamlit Cloud:

1. Di Google Cloud Console, buat OAuth Client ID tipe **Web application**.
2. Tambahkan **Authorized redirect URIs**:
   - `https://<your-app>.streamlit.app/` (ganti dengan URL app Anda)
   - Untuk lokal: `http://localhost:8501/`
3. Di aplikasi, gunakan mode **Web App** (copy-paste auth code).
4. Deploy ke Streamlit Cloud dari repo GitHub ini.
5. Upload `client_secret.json` melalui UI sidebar (atau simpan di private repo).

> 🔒 **Keamanan:** Jangan commit `client_secret.json` dan `token.json` ke repo publik.
> File-file ini sudah ada di `.gitignore`.

---

## 📁 Struktur File

```
livestreaming/
├── app.py                 # Aplikasi utama Streamlit
├── auth_helper.py         # Helper fungsi OAuth
├── requirements.txt       # Dependensi Python
├── README.md              # Dokumentasi (file ini)
├── .gitignore             # Ignore file sensitif
└── .streamlit/
    └── config.toml        # Konfigurasi Streamlit
```

File yang di-generate saat runtime (**jangan commit**):
- `client_secret.json`  — OAuth client secret dari Google
- `token.json`          — Token akses/refresh setelah login

---

## 🎬 Alur Kerja Live Streaming di YouTube API

YouTube memisahkan **Broadcast** (halaman video live) dan **Stream** (endpoint RTMP
tempat mengirim video):

```
Buat Broadcast ──► Buat Stream ──► Bind keduanya
                                       │
                                       ▼
                          Mulai kirim video via RTMP (OBS)
                                       │
                                       ▼
                         Transisi: testing → live → complete
```

Aplikasi ini mengotomatiskan seluruh langkah di atas.

---

## 🔧 Troubleshooting

- **Error "accessNotConfigured"** → YouTube Data API v3 belum di-enable di project Anda.
- **Error "insufficientPermissions"** → Scope `youtube` belum ditambahkan di consent screen,
  atau Anda perlu login ulang (hapus `token.json` lalu login lagi).
- **Stream tidak muncul sebagai "Good"** → Pastikan encoder sudah mengirim video
  ke RTMP URL + Stream Key yang benar.
- **Tidak bisa Go Live** → Broadcast harus dalam status `ready` (stream terhubung)
  atau `testing` sebelum bisa transisi ke `live`.

---

## 📜 Lisensi

MIT - silakan gunakan & modifikasi.
