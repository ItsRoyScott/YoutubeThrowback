# Google Cloud OAuth Setup Guide

This guide walks you through setting up Google Cloud OAuth 2.0 credentials for the YouTube Throwback CLI.

---

## Step 1: Create or Select a Google Cloud Project

1. Go to the [Google Cloud Console](https://console.cloud.google.com/).
2. Click the project dropdown near the top navigation bar.
3. Click **New Project**, enter a project name (such as `YoutubeThrowback`), and click **Create**.

---

## Step 2: Enable YouTube Data API v3

1. In the Google Cloud Console, open the left navigation menu.
2. Go to **APIs & Services** > **Library**.
3. Search for **YouTube Data API v3**.
4. Select the API from the results and click **Enable**.

---

## Step 3: Configure the OAuth Consent Screen

1. Navigate to **APIs & Services** > **OAuth consent screen**.
2. Select **External** as the User Type and click **Create**.
3. Fill in the required fields:
   * **App name:** `YouTube Throwback CLI`
   * **User support email:** Your email address
   * **Developer contact information:** Your email address
4. Click **Save and Continue**.
5. Skip the **Scopes** section by clicking **Save and Continue**.
6. Under **Test users**, click **Add Users** and enter the Google account email address you plan to use with the app.
7. Click **Save and Continue** to complete the consent screen setup.

---

## Step 4: Create OAuth Client Credentials

1. Navigate to **APIs & Services** > **Credentials**.
2. Click **Create Credentials** at the top and select **OAuth client ID**.
3. Set **Application type** to **Desktop app**.
4. Set **Name** to `YouTube Throwback Desktop Client`.
5. Click **Create**.

---

## Step 5: Download Client Secret File

1. In the confirmation dialog, click **Download JSON**.
2. Move the downloaded `.json` file into the `_credentials/` folder of this project directory.
3. Ensure the file sits directly in `_credentials/` alongside your configuration (for example `_credentials/client_secret_12345.json`).

---

## Step 6: Authenticate and Generate User Token

Run the verification script from your project root:

```bash
python test_auth.py
```

A browser window will open asking you to log into your Google account. Grant the requested permissions. Once completed, a `token.json` file will be generated inside `_credentials/`, completing the setup.