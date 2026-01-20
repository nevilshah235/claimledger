# Vercel & Cloud Run Deployment Guide

Complete step-by-step guide for deploying ClaimLedger frontend to Vercel and backend to Google Cloud Run.

## Overview

This guide covers:
- **Frontend**: Next.js app deployed to Vercel
- **Backend**: FastAPI app deployed to Google Cloud Run
- **Prerequisites**: Setting up required tools and accounts
- **Configuration**: Environment variables and settings
- **Deployment**: Step-by-step deployment process

## Architecture

```
┌─────────────────┐         ┌──────────────────┐         ┌─────────────────┐
│   Vercel/CDN    │ ──────▶ │   Cloud Run      │ ──────▶ │   PostgreSQL    │
│   (Frontend)    │  HTTPS  │   (Backend API)  │         │   (Database)    │
└─────────────────┘         └──────────────────┘         └─────────────────┘
         │                           │
         │                           │
         ▼                           ▼
┌─────────────────┐         ┌──────────────────┐
│  Next.js App    │         │  FastAPI App     │
│  - React        │         │  - Python 3.11+  │
│  - TypeScript   │         │  - Uvicorn       │
└─────────────────┘         └──────────────────┘
```

## Prerequisites

### 1. Required Accounts

- **Vercel Account**: Sign up at [vercel.com](https://vercel.com)
- **Google Cloud Account**: Sign up at [cloud.google.com](https://cloud.google.com)
  - Enable billing (Cloud Run requires billing)
  - Create or select a project

### 2. Required Tools

#### Node.js (for frontend)
```bash
# Check if installed
node --version  # Should be v18+ or v20+

# Install if needed
# macOS: brew install node
# Or download from: https://nodejs.org/
```

#### Google Cloud SDK (gcloud CLI)
```bash
# Check if installed
gcloud --version

# Install if needed (macOS)
brew install --cask google-cloud-sdk

# Or follow: https://cloud.google.com/sdk/docs/install

# Authenticate
gcloud auth login
gcloud config set project claimly-484803
```

#### Docker (for building Cloud Run images)
```bash
# Check if installed
docker --version

# Install if needed
# macOS: brew install --cask docker
# Or download from: https://www.docker.com/products/docker-desktop
```

## Backend Deployment (Google Cloud Run)

### Step 1: Prepare Backend Environment

1. **Navigate to backend directory:**
   ```bash
   cd backend
   ```

2. **Verify Dockerfile exists:**
   ```bash
   ls -la Dockerfile .dockerignore
   ```
   Should see both files.

3. **Set environment variables in Google Cloud:**
   ```bash
   # Set project
   gcloud config set project claimly-484803
   ```

### Step 1.5: Set Up Cloud SQL PostgreSQL (Recommended for Production)

**Option A: Create Cloud SQL Instance via gcloud CLI**

1. **Create a PostgreSQL instance:**
   ```bash
   # NOTE: db-f1-micro is NOT supported with ENTERPRISE or ENTERPRISE_PLUS editions.
   # If you need low-cost development/testing, use "db-f1-micro" with the 'Cloud SQL Enterprise' (non-PLUS) edition:
   gcloud sql instances create claimledger-db \
     --database-version=POSTGRES_18 \
     --tier=db-f1-micro \
     --region=us-central1 \
     --root-password="" \
     --storage-type=SSD \
     --storage-size=10GB \
     --storage-auto-increase \
     --edition=ENTERPRISE
   ```
   
   **Parameters explained:**
   - `--tier=db-f1-micro`: Smallest/cheapest tier (~$7/month). Use `db-g1-small` for more resources (~$25/month)
   - `--region=us-central1`: Should match your Cloud Run region
   - `--root-password`: Set a strong password (you'll need this)
   - `--storage-size=10GB`: Starting storage (auto-increases as needed)
   - `--backup`: Enables automated backups
   - `--enable-bin-log`: Enables point-in-time recovery

2. **Create a database:**
   ```bash
   gcloud sql databases create claimledger \
     --instance=claimledger-db
   ```

3. **Create a database user:**
   ```bash
   gcloud sql users create claimledger-user \
     --instance=claimledger-db \
     --password=YOUR_DB_USER_PASSWORD
   ```

4. **Get the connection name:**
   ```bash
   gcloud sql instances describe claimledger-db \
     --format="value(connectionName)"
   ```
   
   Output example: `claimly-484803:us-central1:claimledger-db`
   
   **Save this connection name** - you'll need it for Cloud Run!

5. **Get the public IP address:**
   ```bash
   gcloud sql instances describe claimledger-db \
     --format="value(ipAddresses[0].ipAddress)"
   ```

**Option B: Create via Google Cloud Console (Easier)**

1. Go to [Google Cloud Console → SQL](https://console.cloud.google.com/sql/instances)
2. Click **"Create Instance"**
3. Choose **PostgreSQL**
4. Configure:
   - **Instance ID**: `claimledger-db`
   - **Password**: Set root password
   - **Region**: `us-central1` (match Cloud Run region)
   - **Database version**: PostgreSQL 15
   - **Machine type**: `db-f1-micro` (for cost savings) or `db-g1-small` (recommended)
   - **Storage**: 10GB, enable auto-increase
   - **Enable backups**: Yes
5. Click **"Create"**
6. After creation:
   - Go to **Databases** tab → **Create database**: `claimledger`
   - Go to **Users** tab → **Add user account**: `claimledger-user` with password

**Get Connection Details:**

After creating the instance, get the connection name:
```bash
# Get connection name (format: PROJECT:REGION:INSTANCE)
gcloud sql instances describe claimledger-db \
  --format="value(connectionName)"
```

**Update .env.production:**

Add the PostgreSQL connection string to your `.env.production`:
```bash
# Format: postgresql://USER:PASSWORD@/DATABASE?host=/cloudsql/CONNECTION_NAME
# Or use public IP: postgresql://USER:PASSWORD@PUBLIC_IP:5432/DATABASE

DATABASE_URL=postgresql://claimledger-user:YOUR_PASSWORD@/claimledger?host=/cloudsql/claimly-484803:us-central1:claimledger-db
```

**For local testing (using public IP):**
```bash
# First, authorize your IP
gcloud sql instances patch claimledger-db \
  --authorized-networks=YOUR_IP_ADDRESS/32

# Then use public IP connection
DATABASE_URL=postgresql://claimledger-user:YOUR_PASSWORD@PUBLIC_IP:5432/claimledger
```

**Cost Notes:**
- `db-f1-micro`: ~$7-10/month (shared CPU, 0.6GB RAM) - Good for development
- `db-g1-small`: ~$25/month (1 vCPU, 1.7GB RAM) - Recommended for production
- Storage: $0.17/GB/month (10GB = ~$1.70/month)
- Backups: Included in storage cost
- **Total estimate**: ~$10-30/month depending on tier

**Alternative: Use SQLite for Development**

If you want to start with SQLite (free, but not recommended for production):
```bash
DATABASE_URL=sqlite:///./claimledger.db
```

### Step 2: Build and Push Docker Image

You have two options for building and pushing your Docker image:

**Option A: Build Locally and Push to GCR**

**Important:** Cloud Run requires `linux/amd64` architecture. If you're on Apple Silicon (M1/M2/M3) or ARM, you must build for the correct platform.

1. **Build Docker image locally for linux/amd64:**
   ```bash
   cd backend
   docker build --platform linux/amd64 -t claimledger-backend:latest .
   ```
   
   **Note:** The `--platform linux/amd64` flag ensures the image works on Cloud Run, even if you're building on ARM (Apple Silicon).

2. **Tag the image for Google Container Registry:**
   ```bash
   docker tag claimledger-backend:latest gcr.io/claimly-484803/claimledger-backend:latest
   ```

3. **Configure Docker to authenticate with GCR:**
   ```bash
   gcloud auth configure-docker
   ```

4. **Push the image to GCR:**
   ```bash
   docker push gcr.io/claimly-484803/claimledger-backend:latest
   ```

**Option B: Build Directly on Cloud Build (Recommended)**

This builds the image in the cloud and automatically pushes it to GCR:
   ```bash
   cd backend
   gcloud builds submit --tag gcr.io/claimly-484803/claimledger-backend:latest
   ```

**Verify image:**
   ```bash
   # List local images
   docker images | grep claimledger-backend
   
   # Or verify in GCR
   gcloud container images list --repository=gcr.io/claimly-484803
   ```

### Step 3: Deploy to Cloud Run

1. **Create a `.env.production` file (recommended):**
   
   Create `backend/.env.production` with all your environment variables:
   ```bash
   cd backend
   cat > .env.production << EOF
   DATABASE_URL=sqlite:///./claimledger.db
   JWT_SECRET_KEY=your-secret-key-change-in-production
   GOOGLE_API_KEY=your_google_api_key_here
   CIRCLE_WALLETS_API_KEY=your_api_key_here
   CIRCLE_ENTITY_SECRET=your_entity_secret_here
   CIRCLE_GATEWAY_API_KEY=your_gateway_api_key_here
   ARC_RPC_URL=https://rpc.testnet.arc.network
   CLAIM_ESCROW_ADDRESS=0x80794995149E5d26F22c36eD56B817CBd8E5d4Fa
   USDC_ADDRESS=0x3600000000000000000000000000000000
   EOF
   ```
   
   **Important:** Add `.env.production` to `.gitignore` to avoid committing secrets!

2. **Deploy using the .env file:**

   **If using Cloud SQL PostgreSQL:**
   ```bash
   # Get your Cloud SQL connection name first
   CONNECTION_NAME=$(gcloud sql instances describe claimledger-db \
     --format="value(connectionName)")
   
   gcloud run deploy claimledger-backend \
     --image gcr.io/claimly-484803/claimledger-backend:latest \
     --platform managed \
     --region us-central1 \
     --allow-unauthenticated \
     --port 8080 \
     --memory 1Gi \
     --cpu 1 \
     --timeout 300 \
     --max-instances 1 \
     --add-cloudsql-instances $CONNECTION_NAME \
     --env-vars-file .env.production.yaml
   ```
   
   **If using SQLite (development only):**
   ```bash
   gcloud run deploy claimledger-backend \
     --image gcr.io/claimly-484803/claimledger-backend:latest \
     --platform managed \
     --region us-central1 \
     --allow-unauthenticated \
     --port 8080 \
     --memory 1Gi \
     --cpu 1 \
     --timeout 300 \
     --max-instances 1 \
     --env-vars-file .env.production
   ```
   
   **Key difference:** The `--add-cloudsql-instances` flag connects Cloud Run to your Cloud SQL instance.

   **Alternative: Using individual environment variables (if you prefer):**
   ```bash
   gcloud run deploy claimledger-backend \
     --image gcr.io/claimly-484803/claimledger-backend:latest \
     --platform managed \
     --region us-central1 \
     --allow-unauthenticated \
     --port 8080 \
     --memory 1Gi \
     --cpu 1 \
     --timeout 300 \
     --max-instances 10 \
     --set-env-vars "DATABASE_URL=sqlite:///./claimledger.db,JWT_SECRET_KEY=your-secret-key,GOOGLE_API_KEY=your_key"
   ```

#### Understanding `gcloud run deploy` Parameters

Here's what each parameter does:

| Parameter | Description | Example/Notes |
|-----------|-------------|---------------|
| `claimledger-backend` | Service name in Cloud Run | Must be unique in your project |
| `--image` | Docker image to deploy | Full path: `gcr.io/PROJECT_ID/image:tag` |
| `--platform managed` | Use fully managed Cloud Run | Alternative: `--platform gke` for GKE |
| `--region` | Geographic region for deployment | `us-central1`, `us-east1`, `europe-west1`, etc. |
| `--allow-unauthenticated` | Allow public access (no auth required) | Remove for private services |
| `--port` | Container port to listen on | Must match your app (default: 8080) |
| `--memory` | Memory allocation per instance | `256Mi`, `512Mi`, `1Gi`, `2Gi`, `4Gi`, `8Gi` |
| `--cpu` | CPU allocation | `1`, `2`, `4`, `6`, `8` (or `0.5` for minimal) |
| `--timeout` | Request timeout in seconds | Max: 3600 (1 hour), default: 300 (5 min) |
| `--max-instances` | Maximum concurrent instances | `1` to `1000` (0 = unlimited) |
| `--min-instances` | Minimum instances to keep warm | `0` (default, scales to zero) or `1+` |
| `--env-vars-file` | Load env vars from file | File format: `KEY=VALUE` (one per line) |
| `--set-env-vars` | Set env vars inline | Format: `"KEY1=value1,KEY2=value2"` |

**Important Notes:**
- **Memory & CPU**: Higher values = faster but more expensive. Start with `1Gi` memory and `1` CPU.
- **Timeout**: For long-running AI evaluations, increase to `600` (10 min) or `1800` (30 min).
- **Max Instances**: Prevents runaway costs. Set based on expected traffic.
- **Min Instances**: Set to `1` to avoid cold starts, but costs more (always running).
- **Port**: Cloud Run sets `PORT` env var automatically. Your app should read `os.getenv("PORT", "8080")`.

2. **Get service URL:**
   ```bash
   gcloud run services describe claimledger-backend \
     --platform managed \
     --region us-central1 \
     --format 'value(status.url)'
   ```
   
   Output example: `https://claimledger-backend-xxxxx-uc.a.run.app`

3. **Test deployment:**
   ```bash
   # Test health endpoint
   curl https://YOUR_SERVICE_URL/health
   # Expected: {"status":"healthy"}
   ```

### Step 4: Update CORS Settings

The backend automatically supports Vercel URLs via environment variables:

1. **Set FRONTEND_URL in Cloud Run:**
   
   **Option A: Update using .env file (recommended):**
   ```bash
   # Add FRONTEND_URL to your .env.production file
   echo "FRONTEND_URL=https://your-app.vercel.app" >> backend/.env.production
   
   # Update the service
   gcloud run services update claimledger-backend \
     --platform managed \
     --region us-central1 \
     --env-vars-file backend/.env.production
   ```
   
   **Option B: Update individual variable:**
   ```bash
   gcloud run services update claimledger-backend \
     --platform managed \
     --region us-central1 \
     --update-env-vars "FRONTEND_URL=https://your-app.vercel.app"
   ```

   Or the backend will automatically detect `VERCEL_URL` from Vercel's deployment environment.

## Frontend Deployment (Vercel)

### Step 1: Prepare Frontend

1. **Navigate to frontend directory:**
   ```bash
   cd frontend
   ```

2. **Verify configuration files:**
   ```bash
   ls -la next.config.js vercel.json
   ```
   Should see both files.

3. **Build locally (optional, for testing):**
   ```bash
   npm install
   npm run build
   ```

### Step 2: Deploy to Vercel

#### Option A: Vercel CLI (Recommended)

1. **Install Vercel CLI:**
   ```bash
   npm install -g vercel
   ```

2. **Login to Vercel:**
   ```bash
   vercel login
   ```

3. **Deploy:**
   ```bash
   cd frontend
   vercel
   
   # Follow prompts:
   # - Link to existing project? (or create new)
   # - Set up and deploy? Yes
   ```

4. **Set environment variables:**
   ```bash
   vercel env add NEXT_PUBLIC_API_URL production
   # Enter: https://YOUR_CLOUD_RUN_SERVICE_URL
   
   # Or add via Vercel dashboard:
   # Settings → Environment Variables → Add
   ```

5. **Deploy to production:**
   ```bash
   vercel --prod
   ```

#### Option B: Vercel Dashboard (Alternative)

1. **Connect GitHub repository:**
   - Go to [vercel.com/new](https://vercel.com/new)
   - Import your Git repository
   - Select `frontend` as root directory (if monorepo)

2. **Configure project:**
   - Framework Preset: Next.js
   - Root Directory: `frontend`
   - Build Command: `npm run build`
   - Output Directory: `.next`

3. **Set environment variables:**
   - Go to Project Settings → Environment Variables
   - Add: `NEXT_PUBLIC_API_URL` = `https://YOUR_CLOUD_RUN_SERVICE_URL`
   - Apply to: Production, Preview, Development

4. **Deploy:**
   - Click "Deploy"
   - Wait for deployment to complete

### Step 3: Update Backend CORS

After getting your Vercel URL:

1. **Get Vercel deployment URL:**
   - From Vercel dashboard: `https://your-app.vercel.app`

2. **Update backend CORS:**
   
   **Using .env file:**
   ```bash
   # Update .env.production with your Vercel URL
   # Then redeploy or update
   gcloud run services update claimledger-backend \
     --platform managed \
     --region us-central1 \
     --env-vars-file backend/.env.production
   ```
   
   **Or update individual variable:**
   ```bash
   gcloud run services update claimledger-backend \
     --platform managed \
     --region us-central1 \
     --update-env-vars "FRONTEND_URL=https://your-app.vercel.app"
   ```

## Post-Deployment

### 1. Verify Frontend → Backend Connection

1. **Open frontend in browser:**
   ```
   https://your-app.vercel.app
   ```

2. **Check browser console for errors:**
   - Open DevTools (F12)
   - Look for API connection errors

3. **Test API endpoint:**
   ```bash
   curl https://your-app.vercel.app/api/health
   # Should proxy or redirect to backend
   ```

### 2. Test Authentication Flow

1. **Register a test user:**
   - Go to frontend
   - Click "Register" or "Connect Wallet"
   - Create test account

2. **Verify backend logs:**
   ```bash
   gcloud run services logs read claimledger-backend \
     --platform managed \
     --region us-central1 \
     --limit 50
   ```

### 3. Monitor Performance

1. **Vercel Analytics:**
   - Check deployment status in Vercel dashboard
   - View performance metrics

2. **Cloud Run Metrics:**
   ```bash
   # View service metrics
   gcloud run services describe claimledger-backend \
     --platform managed \
     --region us-central1
   ```

## Environment Variables Reference

### Backend (Cloud Run)

| Variable | Description | Example |
|----------|-------------|---------|
| `DATABASE_URL` | Database connection string | `sqlite:///./claimledger.db` |
| `JWT_SECRET_KEY` | JWT token secret | `your-secret-key` |
| `GOOGLE_API_KEY` | Google AI API key | `AIza...` |
| `CIRCLE_WALLETS_API_KEY` | Circle Wallets API key | `TEST_API_KEY:...` |
| `CIRCLE_ENTITY_SECRET` | Circle entity secret (64 hex chars) | `abc123...` |
| `CIRCLE_GATEWAY_API_KEY` | Circle Gateway API key | `TEST_API_KEY:...` |
| `ARC_RPC_URL` | Arc blockchain RPC URL | `https://rpc.testnet.arc.network` |
| `CLAIM_ESCROW_ADDRESS` | ClaimEscrow contract address | `0x...` |
| `USDC_ADDRESS` | USDC token address | `0x...` |
| `FRONTEND_URL` | Frontend URL for CORS | `https://your-app.vercel.app` |
| `PORT` | Port (auto-set by Cloud Run) | `8080` |

### Frontend (Vercel)

| Variable | Description | Example |
|----------|-------------|---------|
| `NEXT_PUBLIC_API_URL` | Backend API URL | `https://claimledger-backend-xxxxx-uc.a.run.app` |

## Troubleshooting

### Backend Issues

**"Container failed to start"**
- Check Dockerfile syntax
- Verify `PORT` environment variable handling
- Check logs: `gcloud run services logs read claimledger-backend`

**"Container manifest type must support amd64/linux"**
- **Cause:** Image was built for wrong architecture (e.g., ARM64 on Apple Silicon)
- **Fix:** Rebuild with `--platform linux/amd64` flag:
  ```bash
  cd backend
  docker build --platform linux/amd64 -t claimledger-backend:latest .
  docker tag claimledger-backend:latest gcr.io/claimly-484803/claimledger-backend:latest
  docker push gcr.io/claimly-484803/claimledger-backend:latest
  ```
- **Alternative:** Use Cloud Build (automatically builds for correct platform):
  ```bash
  cd backend
  gcloud builds submit --tag gcr.io/claimly-484803/claimledger-backend:latest
  ```

**"CORS errors"**
- Verify `FRONTEND_URL` is set in Cloud Run
- Check `main.py` CORS configuration
- Ensure Vercel URL matches exactly (including `https://`)

**"Database connection failed"**
- Verify `DATABASE_URL` format
- Check Cloud SQL instance (if using PostgreSQL)
- Ensure database is accessible from Cloud Run

### Frontend Issues

**"API connection failed"**
- Verify `NEXT_PUBLIC_API_URL` is set in Vercel
- Check backend service URL is correct
- Test backend health endpoint directly

**"Build failed"**
- Check `next.config.js` syntax
- Verify all dependencies in `package.json`
- Check build logs in Vercel dashboard

**"Environment variables not working"**
- Ensure variables start with `NEXT_PUBLIC_` for client-side access
- Redeploy after adding new variables
- Clear browser cache

## Continuous Deployment

### GitHub Actions (Recommended)

1. **Backend CI/CD:**
   - On push to `main`, build and deploy to Cloud Run
   - Use Google Cloud Build or GitHub Actions

2. **Frontend CI/CD:**
   - Vercel automatically deploys on Git push (if connected)
   - Or configure GitHub Actions for manual control

### Manual Deployment

1. **Backend:**
   ```bash
   # Rebuild and redeploy
   gcloud builds submit --tag gcr.io/claimly-484803/claimledger-backend:latest
   gcloud run deploy claimledger-backend --image gcr.io/claimly-484803/claimledger-backend:latest
   ```

2. **Frontend:**
   ```bash
   # Deploy via CLI
   cd frontend
   vercel --prod
   ```

## Security Best Practices

1. **Never commit secrets to Git:**
   - Use `.gitignore` for `.env` files
   - Use environment variables in Cloud Run/Vercel

2. **Use production keys:**
   - Replace testnet keys with production keys
   - Rotate secrets regularly

3. **Enable Cloud Run authentication (optional):**
   ```bash
   # For production, remove --allow-unauthenticated
   gcloud run services update claimledger-backend \
     --no-allow-unauthenticated
   ```

4. **Monitor logs:**
   - Set up Cloud Logging alerts
   - Monitor Vercel deployment status

## Cost Estimates

### Vercel (Frontend)
- **Free tier**: 100GB bandwidth, unlimited builds
- **Pro**: $20/month (additional bandwidth)

### Cloud Run (Backend) - Detailed Cost Breakdown

Based on your configuration (`1 vCPU`, `1Gi memory`, `us-central1`, `max-instances: 1`) and [Cloud Run pricing](https://cloud.google.com/run/pricing#regions):

#### Free Tier (Monthly)
- **CPU**: 240,000 vCPU-seconds free (Instance-based) or 180,000 vCPU-seconds (Request-based)
- **Memory**: 450,000 GiB-seconds free (Instance-based) or 360,000 GiB-seconds (Request-based)
- **Requests**: 2 million requests free (Request-based billing only)

#### Pricing (us-central1 - Tier 1)
**Request-based billing** (recommended for most apps):
- **CPU (active)**: $0.000024 per vCPU-second
- **Memory (active)**: $0.0000025 per GiB-second
- **Requests**: $0.40 per 1,000,000 requests

**Instance-based billing**:
- **CPU**: $0.000018 per vCPU-second
- **Memory**: $0.000002 per GiB-second

#### Cost Scenarios

**Scenario 1: Light Usage (Development/Testing)**
- 10,000 requests/month
- Average request duration: 500ms
- **Calculation**:
  - CPU time: 10,000 × 0.5s × 1 vCPU = 5,000 vCPU-seconds
  - Memory time: 10,000 × 0.5s × 1 GiB = 5,000 GiB-seconds
  - Requests: 10,000
- **Cost**: $0.00 (all within free tier)

**Scenario 2: Moderate Usage (Small Production)**
- 100,000 requests/month
- Average request duration: 1 second
- **Calculation**:
  - CPU time: 100,000 × 1s × 1 vCPU = 100,000 vCPU-seconds (free)
  - Memory time: 100,000 × 1s × 1 GiB = 100,000 GiB-seconds (free)
  - Requests: 100,000 (free)
- **Cost**: $0.00 (all within free tier)

**Scenario 3: Heavy Usage (Active Production)**
- 1,000,000 requests/month
- Average request duration: 2 seconds
- **Calculation**:
  - CPU time: 1,000,000 × 2s × 1 vCPU = 2,000,000 vCPU-seconds
  - Memory time: 1,000,000 × 2s × 1 GiB = 2,000,000 GiB-seconds
  - Requests: 1,000,000 (free)
  - **Billed CPU**: (2,000,000 - 180,000) × $0.000024 = $43.68
  - **Billed Memory**: (2,000,000 - 360,000) × $0.0000025 = $4.10
- **Total**: ~$47.78/month

**Scenario 4: AI Evaluation Heavy (Your Use Case)**
- 10,000 claims/month
- Average evaluation time: 30 seconds (AI processing)
- **Calculation**:
  - CPU time: 10,000 × 30s × 1 vCPU = 300,000 vCPU-seconds
  - Memory time: 10,000 × 30s × 1 GiB = 300,000 GiB-seconds
  - Requests: 10,000 (free)
  - **Billed CPU**: (300,000 - 180,000) × $0.000024 = $2.88
  - **Billed Memory**: (300,000 - 360,000) = $0.00 (within free tier)
- **Total**: ~$2.88/month

**Scenario 5: High Traffic (Scale)**
- 10,000,000 requests/month
- Average request duration: 500ms
- **Calculation**:
  - CPU time: 10,000,000 × 0.5s × 1 vCPU = 5,000,000 vCPU-seconds
  - Memory time: 10,000,000 × 0.5s × 1 GiB = 5,000,000 GiB-seconds
  - Requests: 10,000,000
  - **Billed CPU**: (5,000,000 - 180,000) × $0.000024 = $115.68
  - **Billed Memory**: (5,000,000 - 360,000) × $0.0000025 = $11.60
  - **Billed Requests**: (10,000,000 - 2,000,000) / 1,000,000 × $0.40 = $3.20
- **Total**: ~$130.48/month

#### Cost Optimization Tips

1. **Use Request-based billing** for most workloads (better free tier)
2. **Optimize request duration**: Faster responses = lower costs
3. **Set `--max-instances 1`** (as you have) to prevent runaway costs
4. **Use `--min-instances 0`** (default) to scale to zero when idle
5. **Consider increasing timeout** for AI evaluations: `--timeout 1800` (30 min) if needed
6. **Monitor usage**: Check Cloud Console → Cloud Run → Metrics

#### Real-World Estimate for ClaimLedger

For a typical insurance claims platform:
- **Low traffic** (100 claims/day): ~$0-5/month
- **Medium traffic** (1,000 claims/day): ~$10-30/month
- **High traffic** (10,000 claims/day): ~$50-150/month

**Note**: These estimates don't include:
- Cloud SQL (if using PostgreSQL instead of SQLite): ~$10-50/month
- Cloud Storage (for file uploads): ~$0.02/GB/month
- Network egress: First 1GB free, then ~$0.12/GB

#### Cost Calculator

Use Google's [Cloud Run Pricing Calculator](https://cloud.google.com/products/calculator) for precise estimates based on your specific usage patterns.

## Next Steps

1. **Set up monitoring:**
   - Google Cloud Monitoring
   - Vercel Analytics
   - Error tracking (Sentry, etc.)

2. **Configure custom domains:**
   - Vercel: Add custom domain in dashboard
   - Cloud Run: Use Cloud Load Balancer

3. **Set up database:**
   - ✅ Cloud SQL PostgreSQL setup (see Step 1.5 above)
   - ✅ Automated backups enabled (if configured during creation)
   - **Optional:** Set up scheduled backups or point-in-time recovery

4. **Enable HTTPS:**
   - Vercel: Automatic (included)
   - Cloud Run: Automatic (included)

## References

- [Vercel Documentation](https://vercel.com/docs)
- [Google Cloud Run Documentation](https://cloud.google.com/run/docs)
- [Next.js Deployment](https://nextjs.org/docs/deployment)
- [FastAPI Deployment](https://fastapi.tiangolo.com/deployment/)

## Support

For issues or questions:
1. Check deployment logs
2. Review this guide
3. Check documentation links above
4. Create an issue in the repository
