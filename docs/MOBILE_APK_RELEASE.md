# TalentAI Enterprise Mobile APK — Release & Distribution Guide

## 📱 Release Artifact Summary

| Property | Value |
| :--- | :--- |
| **App Name** | `TalentAI Enterprise` |
| **Package ID** | `ai.talentai.app` |
| **Version Code** | `10001` |
| **Version Name** | `1.0.1` |
| **Target SDK** | Android 14 (`API 34`) |
| **Minimum SDK** | Android 7.0 (`API 24`) — Compatible with 95%+ of active devices |
| **APK File Path** | `D:\recruitment_platform\TalentAI-v1.0.1.apk` |
| **APK Size** | **4.4 MB** |
| **Signature** | Signed with RSA-2048 production keystore (`v2 APK Signature Scheme`) |
| **Debug APK** | `D:\recruitment_platform\TalentAI-v1.0.1-debug.apk` |

---

## 🚀 How to Ship & Share with People

You can immediately share `TalentAI-v1.0.1.apk` with anyone:
1. **Direct Sharing:** Send via WhatsApp, Telegram, Slack, or Email.
2. **Cloud Share:** Upload to Google Drive, Dropbox, or OneDrive and share the download link.
3. **Web Download:** Host directly on your Vercel or cloud web server (e.g., `https://talentai-recruiter.vercel.app/TalentAI-v1.0.1.apk`).

### Installation Instructions for Users:
1. Download `TalentAI-v1.0.1.apk` onto any Android phone.
2. Tap the downloaded file.
3. If prompted with *"Install unknown apps"*, tap **Settings** &rarr; toggle **Allow from this source**.
4. Tap **Install**. TalentAI will launch with the dark modern theme and connect directly to the 3,420 candidates database.

---

## 🔄 Built-In OTA (Over-The-Air) In-App Update Mechanism

The app includes native auto-update checking:
- **Automatic Check:** Every time the app opens, `UpdateManager.java` queries:
  `GET https://talentai-recruitment.onrender.com/api/v1/app/version`
- **Update Dialog:** If the server reports a newer `latest_version_code` than installed:
  - Displays a native dialog with the release notes and an **"Update Now"** button.
  - Downloads the APK directly using Android's `DownloadManager`.
  - Automatically triggers the Android Package Installer via `androidx.core.content.FileProvider`.
- **JavaScript Bridge:** Web pages inside the app can also trigger update checks or read version numbers via:
  ```javascript
  window.AndroidBridge.getAppVersion();     // returns "1.0.1"
  window.AndroidBridge.getAppVersionCode(); // returns 10001
  window.AndroidBridge.checkForUpdates();   // triggers OTA check popup
  ```

---

## 🛠️ How to Push Later Updates (Step-by-Step)

When you make changes and want all users to get the update:

### Step 1: Bump the Version in `android/app/build.gradle`
```groovy
defaultConfig {
    versionCode 10002       // Increment by 1
    versionName "1.0.2"     // Update version string
}
```

### Step 2: Build the New Signed APK
Run the 1-click build script:
```powershell
D:\recruitment_platform\android\build-apk.bat
```

### Step 3: Deploy New APK & Update Server Version
1. Place the new APK at your public download URL.
2. Update `backend/api/routes.py` in the `get_app_version()` endpoint:
```python
@router.get("/app/version")
def get_app_version():
    return {
        "status": "SUCCESS",
        "latest_version": "1.0.2",
        "latest_version_code": 10002,
        "download_url": "https://talentai-recruiter.vercel.app/download/talentai-latest.apk",
        "release_notes": "TalentAI Mobile v1.0.2:\n- What's new in this release...",
        "mandatory": False,
        "published_at": "2026-10-27T00:00:00Z"
    }
```
All users running v1.0.1 will automatically see the update prompt the next time they open the app!

---

## ⚡ Mobile Features Included

- **Offline + Cloud Hybrid Architecture:** Loads live cloud data with instant fallback to bundled local assets (`assets/www`) if offline.
- **Native File Picker (`WebChromeClient`):** Enables recruiters and applicants to upload CVs/Resumes directly from phone storage (`.pdf`, `.docx`).
- **Native Resume/Report Downloads:** Integrated with Android `DownloadManager` to save generated candidate profiles directly to phone downloads.
- **Swipe-to-Refresh:** Pull down anytime to re-sync search results.
- **Native Share Sheet:** Share candidate links and profiles directly to WhatsApp or email via `window.AndroidBridge.shareCandidate(...)`.
