# Deploying to Hostinger VPS

This guide walks you through deploying the AI Article Generator to your Hostinger VPS server using Docker.

## Prerequisites

- Hostinger VPS with Docker installed
- SSH access to your server
- Anthropic API key
- Google Cloud OAuth credentials

## Step 1: Connect to Your Server

```bash
ssh root@your-server-ip
# Or use the Hostinger web terminal
```

## Step 2: Clone the Repository

```bash
cd /opt
git clone https://github.com/yourusername/ai-article-generator.git
cd ai-article-generator
```

Or transfer files using SCP/SFTP if not using git.

## Step 3: Set Up Credentials Directory

```bash
mkdir -p credentials
```

## Step 4: Add Google OAuth Credentials

You need to upload your `credentials.json` file from Google Cloud Console:

### Option A: Using SCP (from your local machine)
```bash
scp /path/to/your/credentials.json root@your-server-ip:/opt/ai-article-generator/credentials/
```

### Option B: Using Hostinger File Manager
1. Go to Hostinger hPanel
2. Open File Manager
3. Navigate to `/opt/ai-article-generator/credentials/`
4. Upload your `credentials.json` file

## Step 5: Create Environment File

```bash
cat > .env << 'EOF'
# Your Anthropic API Key
ANTHROPIC_API_KEY=sk-ant-xxxxxxxxxxxxx

# Optional: Google Drive folder ID to save articles
GOOGLE_DRIVE_FOLDER_ID=

# Optional: Customize article settings
ARTICLE_MIN_WORDS=800
ARTICLE_MAX_WORDS=2000
EOF
```

Replace `sk-ant-xxxxxxxxxxxxx` with your actual Anthropic API key.

## Step 6: Authenticate with Google (First Time Only)

This is the tricky part - Google OAuth requires a browser redirect. Here are your options:

### Option A: Authenticate Locally First (Recommended)

1. On your local machine, run the app and authenticate:
   ```bash
   pip install -e .
   article-gen auth
   ```

2. After authenticating, copy the generated `token.json` to your server:
   ```bash
   scp token.json root@your-server-ip:/opt/ai-article-generator/credentials/
   ```

### Option B: Use SSH Port Forwarding

1. Start the container:
   ```bash
   docker compose up -d
   ```

2. From your local machine, create an SSH tunnel:
   ```bash
   ssh -L 8000:localhost:8000 root@your-server-ip
   ```

3. Open `http://localhost:8000` in your browser

4. If prompted for Google auth, complete it (the redirect will work through the tunnel)

### Option C: Expose Port Temporarily

1. Temporarily allow port 8000 in your firewall
2. Navigate to `http://your-server-ip:8000`
3. Complete Google authentication
4. Close the firewall port afterward

## Step 7: Build and Start the Application

```bash
docker compose up -d --build
```

Check if it's running:
```bash
docker compose ps
docker compose logs -f
```

## Step 8: Set Up Reverse Proxy (Recommended)

For HTTPS and proper domain access, set up a reverse proxy:

### Using Nginx

```bash
apt install nginx -y
```

Create nginx config:
```bash
cat > /etc/nginx/sites-available/article-generator << 'EOF'
server {
    listen 80;
    server_name yourdomain.com;

    location / {
        proxy_pass http://127.0.0.1:8000;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection 'upgrade';
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        proxy_cache_bypass $http_upgrade;
    }
}
EOF

ln -s /etc/nginx/sites-available/article-generator /etc/nginx/sites-enabled/
nginx -t
systemctl reload nginx
```

### Add SSL with Let's Encrypt

```bash
apt install certbot python3-certbot-nginx -y
certbot --nginx -d yourdomain.com
```

## Step 9: Verify Deployment

1. Open your browser and navigate to:
   - `http://your-server-ip:8000` (direct)
   - `https://yourdomain.com` (if using reverse proxy)

2. Check the health endpoint:
   ```bash
   curl http://localhost:8000/health
   ```

3. Try generating an article!

## Common Commands

### View Logs
```bash
docker compose logs -f
```

### Restart the Application
```bash
docker compose restart
```

### Stop the Application
```bash
docker compose down
```

### Update the Application
```bash
git pull
docker compose up -d --build
```

### Check Container Status
```bash
docker compose ps
```

## Troubleshooting

### "Google credentials not found"
- Make sure `credentials.json` is in the `/opt/ai-article-generator/credentials/` directory
- Check file permissions: `chmod 644 credentials/credentials.json`

### "Not authenticated with Google"
- Run authentication locally and copy `token.json` to the server
- Token files are in the `credentials/` directory

### Container keeps restarting
```bash
docker compose logs --tail=50
```
Check for error messages.

### Port 8000 not accessible
- Check firewall: `ufw allow 8000` or `firewall-cmd --add-port=8000/tcp`
- Verify the container is running: `docker compose ps`

### API errors
- Verify your `ANTHROPIC_API_KEY` is correct in `.env`
- Check API limits on your Anthropic account

## Security Recommendations

1. **Use HTTPS** - Always use a reverse proxy with SSL in production
2. **Firewall** - Only expose ports 80/443, keep 8000 internal
3. **API Keys** - Keep `.env` file secure, never commit to git
4. **Updates** - Keep Docker and the application updated

## Architecture

```
Internet
    │
    ▼
┌─────────────┐
│   Nginx     │ ← Port 80/443 (HTTPS)
│  (Reverse   │
│   Proxy)    │
└──────┬──────┘
       │
       ▼
┌─────────────┐
│   Docker    │ ← Port 8000 (internal)
│  Container  │
│  (FastAPI)  │
└──────┬──────┘
       │
       ▼
┌─────────────┐     ┌─────────────┐
│  Claude AI  │     │ Google Docs │
│    API      │     │    API      │
└─────────────┘     └─────────────┘
```
