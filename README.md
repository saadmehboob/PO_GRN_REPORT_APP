# PO Report Fetcher & Processor

A Streamlit web application for scheduling, downloading, and processing Purchase Order reports from Oracle BI Publisher.

## Features

- 🔄 **Schedule & Download**: Schedule new PO reports with custom date ranges
- 📥 **Download from Job ID**: Download previously scheduled reports using their Job ID
- 📊 **Report Processing**: Automatically process reports into 3 formats:
  - Combined Report (all sheets merged)
  - Processed Report (aggregated summary with calculations)
  - ProcessedDetailed Report (detailed line-level calculations)
- 🔐 **Password Protection**: Secure access with password authentication
- 💾 **CSV Export**: Download all processed reports as CSV files

## Quick Start

### Local Development

1. **Clone the repository**
   ```bash
   git clone <repository-url>
   cd PO_report_v2
   ```

2. **Set up environment variables**
   ```bash
   cp .env.example .env
   # Edit .env with your credentials
   ```

3. **Install dependencies**
   ```bash
   uv sync
   ```

4. **Run the application**
   ```bash
   uv run streamlit run app.py
   ```

5. **Access the app**
   - Open http://localhost:8501
   - Enter the APP_PASSWORD you set in .env

## Environment Variables

Required environment variables (set in `.env` for local, or as secrets in Fly.io):

- `ORACLE_USERNAME`: Your Oracle BI Publisher username
- `ORACLE_PASSWORD`: Your Oracle BI Publisher password  
- `APP_PASSWORD`: Password to access the Streamlit application

## Deployment to Fly.io

See [DEPLOYMENT.md](DEPLOYMENT.md) for detailed deployment instructions.

### Quick Deploy

```bash
# Install Fly.io CLI
curl -L https://fly.io/install.sh | sh

# Login
flyctl auth login

# Launch app
flyctl launch --no-deploy

# Set secrets
flyctl secrets set ORACLE_USERNAME="your_username"
flyctl secrets set ORACLE_PASSWORD="your_password"
flyctl secrets set APP_PASSWORD="your_app_password"

# Deploy
flyctl deploy
```

## Project Structure

```
PO_report_v2/
├── app.py                      # Main Streamlit application
├── PO_report_fetcher.py        # Oracle BIP integration module
├── PO_report_processor.py      # Report processing logic
├── Dockerfile                  # Docker container configuration
├── fly.toml                    # Fly.io deployment configuration
├── pyproject.toml              # Python dependencies
├── uv.lock                     # Dependency lock file
├── .env.example                # Environment variables template
├── .gitignore                  # Git ignore rules
├── DEPLOYMENT.md               # Deployment guide
└── README.md                   # This file
```

## Usage

### Tab 1: Schedule & Download

1. Select the "To Date" for your report
2. Choose whether to process the report (recommended)
3. Click "Schedule & Download Report"
4. Wait for the report to complete (15-20 minutes)
5. Download the processed CSV files

### Tab 2: Download from Job ID

1. Enter a previously scheduled Job ID
2. Choose whether to process the report
3. Click "Download Report"
4. Download the files

## Report Processing

The application generates three types of reports:

1. **Combined Report**: Merges all Excel sheets into a single dataset
2. **Processed Report**: Aggregates data by PO, Invoice, and Line Number with:
   - Automatic conversion rate calculation
   - Duplicate invoice line handling
   - Difference calculations (Line Amount - Amount Received)
3. **ProcessedDetailed Report**: Line-level details with:
   - Duplicate indicators
   - Adjusted line amounts
   - SAR conversions
   - GRN amount calculations

## Cleanup

Before deploying or committing, clean up test files:

```bash
python cleanup.py
```

This removes:
- Test and debug scripts
- Jupyter notebooks
- Large data files (CSV, XLS, XLSX)

## Security Notes

- ⚠️ Never commit `.env` file to version control
- 🔐 Use strong passwords for `APP_PASSWORD`
- 🔒 Oracle credentials are encrypted when stored as Fly.io secrets
- 🛡️ The app uses HTTPS when deployed to Fly.io

## Troubleshooting

### Job ID Resolution Issues

The app automatically handles Oracle BIP's job ID vs instance ID discrepancy:
- Tries to resolve using `getAllJobInstanceIDs`
- Falls back to `job_id + 1` if resolution fails

### Large Reports

For very large reports (>100MB):
- Increase timeout in `PO_report_fetcher.py`
- Consider increasing Fly.io VM memory

### Authentication Errors

- Verify `ORACLE_USERNAME` and `ORACLE_PASSWORD` are correct
- Check Oracle BIP service is accessible
- Ensure credentials have proper permissions

## License

Internal use only - Aspire

## Support

For issues or questions, contact the development team.
