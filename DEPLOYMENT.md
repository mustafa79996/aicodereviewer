# 🌐 AI Code Reviewer - Deployment & 24/7 Always-Live Guide

This guide explains how to make your **AI Code Review & Bug Detection System** live permanently, both **locally on Windows (24/7 Background Service)** and **online on the Cloud (Free 24/7 Hosting)**.

---

## ⚡ Option 1: Always Live Locally on Windows (24/7 Background)

Keep the website running continuously without keeping a command prompt window open, and have it start automatically whenever your computer boots up.

### 1. Start Server Silently in Background
Double-click:
```
start_live.bat
```
- Starts the server completely hidden in the background (no black terminal window).
- Opens `http://localhost:8000` automatically in your browser.
- Keeps running silently even if you close all windows.

### 2. Auto-Start on Windows Boot (Always Live 24/7)
Double-click:
```
install_autostart.bat
```
- Adds a shortcut to your Windows Startup folder.
- Every time Windows boots or restarts, your AI Code Reviewer server starts automatically in the background.
- You can always access `http://localhost:8000` at any time without having to manually start anything!
- To remove auto-start later, double-click `uninstall_autostart.bat`.

### 3. Check Status
Double-click:
```
status.bat
```
- Displays whether the server is currently running, its Process ID (PID), and port.

### 4. Stop Server
Double-click:
```
stop_server.bat
```
- Gracefully terminates the background server process on port 8000.

---

## 🌍 Option 2: Free 24/7 Cloud Hosting on Render (Public Internet URL)

Deploy your GitHub repository (`mustafa79996/aicodereviewer`) so that anyone in the world can visit your website 24/7 from any phone or PC!

### Step-by-Step 2-Minute Setup:
1. **Push your code to GitHub**:
   ```bash
   git add .
   git commit -m "Configure 24/7 live deployment and bug fixes"
   git push origin main
   ```

2. **Go to [Render.com](https://render.com/)**:
   - Sign up or log in (free account with GitHub).
   - Click **New +** -> **Web Service**.
   - Select your GitHub repository: `mustafa79996/aicodereviewer`.

3. **Configure Settings**:
   - **Name**: `ai-code-reviewer`
   - **Region**: Choose the closest region (e.g., Singapore, Frankfurt, Oregon).
   - **Branch**: `main`
   - **Runtime**: `Python 3`
   - **Build Command**: `pip install -r requirements.txt`
   - **Start Command**: `uvicorn app.main:app --host 0.0.0.0 --port $PORT`
   - **Instance Type**: **Free** ($0/month)

4. **Click "Deploy Web Service"**:
   - Render will build and launch your application.
   - Within 1 minute, you will receive a free public live URL, like:
     `https://ai-code-reviewer.onrender.com`
   - Your website is now permanently live online 24/7!

---

## 🚀 Option 3: Instant Public HTTPS Link (Share with Friends / Team)

If your local server is running and you want an instant public HTTPS URL without deploying to the cloud:

Double-click:
```
share_live_online.bat
```
- Uses `localtunnel` to create an instant public HTTPS link (e.g., `https://ai-reviewer-abc.loca.lt`).
- Anyone on mobile, tablet, or another computer can access your live system!

---

## 💻 Option 4: Local Development Mode (Live Auto-Reload)

If you are modifying code, HTML, CSS, or JS and want instant live reload on every file save:

Double-click:
```
start_dev.bat
```
- Launches uvicorn with `--reload`.
- Automatically refreshes changes as soon as you save any file.
