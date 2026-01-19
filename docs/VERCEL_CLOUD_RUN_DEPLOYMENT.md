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
gcloud config set project YOUR_PROJECT_ID
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
   gcloud config set project YOUR_PROJECT_ID
   
   # Create a Cloud SQL instance (if using PostgreSQL)
   # Or use SQLite for development (not recommended for production)
   
   # Set environment variables (we'll use Cloud Run's env var feature)
   # These will be set during deployment
   ```

### Step 2: Build and Push Docker Image

1. **Build Docker image:**
   ```bash
   # Build locally (optional, for testing)
   docker build -t claimledger-backend:latest .
   
   # Or use Cloud Build directly
   gcloud builds submit --tag gcr.io/YOUR_PROJECT_ID/claimledger-backend:latest
   ```

2. **Verify image:**
   ```bash
   docker images | grep claimledger-backend
   ```

### Step 3: Deploy to Cloud Run

1. **Deploy with environment variables:**
   ```bash
   gcloud run deploy claimledger-backend \
     --image gcr.io/YOUR_PROJECT_ID/claimledger-backend:latest \
     --platform managed \
     --region us-central1 \
     --allow-unauthenticated \
     --port 8080 \
     --memory 1Gi \
     --cpu 1 \
     --timeout 300 \
     --max-instances 10 \
     --set-env-vars "DATABASE_URL=sqlite:///./claimledger.db" \
     --set-env-vars "JWT_SECRET_KEY=your-secret-key-change-in-production" \
     --set-env-vars "GOOGLE_API_KEY=your_google_api_key_here" \
     --set-env-vars "CIRCLE_WALLETS_API_KEY=your_api_key_here" \
     --set-env-vars "CIRCLE_ENTITY_SECRET=your_entity_secret_here" \
     --set-env-vars "CIRCLE_GATEWAY_API_KEY=your_gateway_api_key_here" \
     --set-env-vars "ARC_RPC_URL=https://rpc.testnet.arc.network" \
     --set-env-vars "CLAIM_ESCROW_ADDRESS=0x80794995149E5d26F22c36eD56B817CBd8E5d4Fa" \
     --set-env-vars "USDC_ADDRESS=0x3600000000000000000000000000000000"
   ```

   **Or use a .env file (recommended for production):**
   ```bash
   # Create a .env.production file with all variables
   # Then deploy using --set-env-vars-file
   gcloud run deploy claimledger-backend \
     --image gcr.io/YOUR_PROJECT_ID/claimledger-backend:latest \
     --platform managed \
     --region us-central1 \
     --allow-unauthenticated \
     --port 8080 \
     --set-env-vars-file .env.production
   ```

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
   gcloud builds submit --tag gcr.io/YOUR_PROJECT_ID/claimledger-backend:latest
   gcloud run deploy claimledger-backend --image gcr.io/YOUR_PROJECT_ID/claimledger-backend:latest
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

### Cloud Run (Backend)
- **Free tier**: 2 million requests/month
- **Pricing**: Pay per request + CPU/memory time
- **Estimate**: ~$10-50/month for moderate traffic

## Next Steps

1. **Set up monitoring:**
   - Google Cloud Monitoring
   - Vercel Analytics
   - Error tracking (Sentry, etc.)

2. **Configure custom domains:**
   - Vercel: Add custom domain in dashboard
   - Cloud Run: Use Cloud Load Balancer

3. **Set up database:**
   - Migrate from SQLite to Cloud SQL (PostgreSQL)
   - Set up backups

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
