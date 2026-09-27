```markdown
# Google OAuth Setup Instructions

Follow these steps to obtain your Google OAuth credentials for this application.

---

## 1. Install Dependencies

Ensure Python 3.9 or higher is installed, then run:

```bash
pip install google-auth-oauthlib google-api-python-client

```

---

## 2. Obtain Credentials

1. Go to the [Google Cloud Console](https://console.cloud.google.com/?utm_source=gemini).
2. Create a new project (for example, `YouTube Throwback`).
3. Navigate to **APIs & Services > Library**, search for **YouTube Data API v3**, and click **Enable**.
4. Configure the **OAuth Consent Screen**:
* Go to **APIs & Services > OAuth consent screen** (or **Google Auth Platform**).
* Select **External** and click **Create**.
* Fill in an application name (for example, `YoutubeThrowbackApp`) and your support email.
* Save and navigate to the **Audience** / **Test users** section.
* Click **+ ADD USERS** and add your Google account email address.


5. Create **OAuth 2.0 Credentials**:
* Go to **APIs & Services > Credentials**.
* Click **+ CREATE CREDENTIALS** at the top and select **OAuth client ID**.
* Set **Application type** to **Web application**.
* Under **Authorized redirect URIs**, click **ADD URI** and add:
* `http://localhost:8000/`
* `http://127.0.0.1:8000/`


* Click **Create**.


6. Download the JSON credential file and save it directly into this `_credentials` folder.

---

## 3. Verify Authentication

Run the test script from the project root to complete your initial login:

```bash
python test_auth.py

```

1. Your default browser will open automatically to the Google sign in page.
2. Sign in with the Google account you added as a test user.
3. On the consent screen, click **Continue** and grant the requested YouTube permissions.
4. Return to your terminal to confirm that your YouTube channel details are printed.

```

```