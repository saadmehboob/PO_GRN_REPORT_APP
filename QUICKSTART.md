# Quick Deployment Reference

## ✅ Pre-Deployment Checklist

- [ ] `.env` file has correct credentials (local only)
- [ ] All test files removed (run `python cleanup.py`)
- [ ] Code tested locally
- [ ] Fly.io CLI installed

## 🚀 Deploy to Fly.io (First Time)

```bash
# 1. Login to Fly.io
flyctl auth login

# 2. Launch app (creates fly.toml if needed)
flyctl launch --no-deploy

# 3. Set secrets (IMPORTANT!)
flyctl secrets set ORACLE_USERNAME="your_oracle_username"
flyctl secrets set ORACLE_PASSWORD="your_oracle_password"
flyctl secrets set APP_PASSWORD="your_app_password"

# 4. Deploy
flyctl deploy

# 5. Open app
flyctl open
```

## 🔄 Update Existing Deployment

```bash
# Just deploy (secrets are already set)
flyctl deploy
```

## 🔐 Managing Secrets

```bash
# List secrets (names only)
flyctl secrets list

# Update a secret
flyctl secrets set APP_PASSWORD="new_password"

# Remove a secret
flyctl secrets unset SECRET_NAME
```

## 📊 Monitoring

```bash
# View logs
flyctl logs

# Check status
flyctl status

# SSH into container
flyctl ssh console
```

## 🛠️ Troubleshooting

```bash
# View recent logs
flyctl logs --tail

# Restart app
flyctl apps restart

# Check secrets are set
flyctl secrets list

# View app info
flyctl info
```

## 💰 Cost Management

```bash
# Scale down (save money)
flyctl scale count 0

# Scale up
flyctl scale count 1

# Auto-scaling is enabled by default:
# - Stops when idle
# - Starts on first request
```

## 🧪 Local Testing

```bash
# Test with uv
uv run streamlit run app.py

# Test with Docker
docker build -t po-report-fetcher .
docker run -p 8501:8501 \
  -e ORACLE_USERNAME="user" \
  -e ORACLE_PASSWORD="pass" \
  -e APP_PASSWORD="app_pass" \
  po-report-fetcher
```

## 📝 Important Notes

1. **Never commit `.env`** - It's in `.gitignore`
2. **Secrets are encrypted** on Fly.io
3. **HTTPS is automatic** on Fly.io
4. **Auto-scaling is enabled** - app stops when idle
5. **Free tier friendly** - Current config fits free tier

## 🆘 Getting Help

- Fly.io Docs: https://fly.io/docs/
- Fly.io Community: https://community.fly.io/
- Streamlit Docs: https://docs.streamlit.io/
