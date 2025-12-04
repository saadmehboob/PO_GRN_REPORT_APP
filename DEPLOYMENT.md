# Fly.io Deployment Guide for PO Report Fetcher

## Prerequisites

1. Install Fly.io CLI: https://fly.io/docs/hands-on/install-flyctl/
2. Sign up for Fly.io account: https://fly.io/app/sign-up

## Deployment Steps

### 1. Login to Fly.io
```bash
flyctl auth login
```

### 2. Create the app (first time only)
```bash
flyctl launch --no-deploy
```

### 3. Set Environment Secrets
Set your Oracle credentials and app password as secrets:

```bash
flyctl secrets set ORACLE_USERNAME="your_oracle_username"
flyctl secrets set ORACLE_PASSWORD="your_oracle_password"
flyctl secrets set APP_PASSWORD="your_app_password"
```

**Important:** These secrets are encrypted and stored securely on Fly.io. They will be available as environment variables to your app.

### 4. Deploy the Application
```bash
flyctl deploy
```

### 5. Open the Application
```bash
flyctl open
```

## Managing Secrets

### View current secrets (names only, not values)
```bash
flyctl secrets list
```

### Update a secret
```bash
flyctl secrets set ORACLE_PASSWORD="new_password"
```

### Remove a secret
```bash
flyctl secrets unset SECRET_NAME
```

## Monitoring

### View logs
```bash
flyctl logs
```

### Check app status
```bash
flyctl status
```

### SSH into the container
```bash
flyctl ssh console
```

## Scaling

### Scale vertically (more resources)
```bash
flyctl scale vm shared-cpu-1x --memory 2048
```

### Scale horizontally (more instances)
```bash
flyctl scale count 2
```

## Cost Optimization

The current configuration uses:
- 1 shared CPU
- 1GB RAM
- Auto-stop when idle
- Auto-start on request

This should fit within Fly.io's free tier for hobby projects.

## Troubleshooting

### App won't start
```bash
flyctl logs
```

### Check secrets are set
```bash
flyctl secrets list
```

### Restart the app
```bash
flyctl apps restart
```

## Local Testing

Before deploying, test the Docker container locally:

```bash
# Build the image
docker build -t po-report-fetcher .

# Run with environment variables
docker run -p 8501:8501 \
  -e ORACLE_USERNAME="your_username" \
  -e ORACLE_PASSWORD="your_password" \
  -e APP_PASSWORD="your_app_password" \
  po-report-fetcher
```

Then visit http://localhost:8501
