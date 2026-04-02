# ============================================
# ANHA Trading - Deployment Guide
# ============================================

## Table of Contents
1. [Railway Deployment (Recommended)](#railway-deployment-recommended)
2. [Hostinger VPS Deployment](#hostinger-vps-deployment)
3. [Troubleshooting](#troubleshooting)

---

## Railway Deployment (Recommended)

### Why Railway?
- **One-Click Deploy**: Connect GitHub and deploy instantly
- **Auto SSL**: Free HTTPS automatically configured
- **Auto Deploy**: Every git push triggers deployment
- **Managed Database**: PostgreSQL included
- **Generous Free Tier**: $5 credit/month, pay-as-you-go
- **Simple Pricing**: Only pay for what you use

### Step-by-Step Deployment

#### 1. Prepare Your Repository

**Generate uv lock file (required):**
```bash
# Install uv if you haven't already
curl -LsSf https://astral.sh/uv/install.sh | sh

# Navigate to your project
cd anha-trading

# Generate lock file (ensures reproducible builds)
uv lock

# Commit all deployment files
git add railway.json nixpacks.toml .railwayignore .python-version uv.lock
git commit -m "Add Railway deployment configuration with uv"
git push origin main
```

**Note:** The `uv.lock` file ensures your production dependencies match exactly what you tested with.

#### 2. Create Railway Account
1. Go to [https://railway.app](https://railway.app)
2. Sign up with GitHub (recommended) for instant access
3. Complete the onboarding process

#### 3. Create New Project
1. Click **"New Project"**
2. Select **"Deploy from GitHub repo"**
3. Authorize Railway to access your GitHub
4. Select your `anha-trading` repository
5. Select the `main` branch

#### 4. Configure Service Settings

Railway will auto-detect Python and configure most settings. Verify:

**Build Settings:**
- **Build Command**: `curl -LsSf https://astral.sh/uv/install.sh | sh && $HOME/.local/bin/uv sync --frozen && npm install && npm run build`
- **Start Command**: `$HOME/.local/bin/uv run uvicorn app.main:app --host 0.0.0.0 --port $PORT --loop uvloop --http httptools --workers 2`

**Performance Optimizations:**
- ✅ **Python 3.13**: Latest Python with 10-40% performance improvements
- ✅ **uv**: Ultra-fast Python package manager (10-100x faster than pip)
- ✅ **uvloop**: Rust-based event loop (2-4x faster than asyncio)
- ✅ **httptools**: Rust-based HTTP parser (high-performance)
- ✅ **orjson**: Rust-based JSON serialization (3-4x faster than stdlib)
- ✅ **Multiple Workers**: 2 workers for parallel request handling
- ✅ **bcrypt**: Rust-based password hashing

**Why uv?**
- **10-100x faster** than pip and pip-tools
- Written in Rust (like uvloop, orjson)
- Compatible with pip requirements.txt
- Locks dependencies for reproducible builds
- Lower memory usage

**Healthcheck:**
- **Healthcheck Path**: `/health`
- **Port**: Railway auto-assigns via `$PORT` environment variable

#### 5. Add Environment Variables

In Railway dashboard, go to your service → **Variables** tab → **"Add Variable"**:

```bash
# Required Variables
APP_NAME=ANHA Trading
ENVIRONMENT=production
ACCESS_TOKEN_EXPIRE_MINUTES=720
RESET_TOKEN_EXPIRE_MINUTES=30
AUTO_CREATE_DB=true
LOG_LEVEL=INFO
SECRET_KEY=<generate-secure-random-key>

# Generate SECRET_KEY with:
# python -c "import secrets; print(secrets.token_urlsafe(32))"
```

**Click "Generate"** for SECRET_KEY or create your own secure value.

#### 6. Add PostgreSQL Database

1. In your Railway project, click **"New"** → **"Database"** → **"Add PostgreSQL"**
2. Railway will provision a PostgreSQL database automatically
3. Wait for database to be ready (~1-2 minutes)
4. Railway automatically creates `DATABASE_URL` variable in your service

**Verify Database Connection:**
- Go to your web service → **Variables** tab
- You should see `DATABASE_URL` automatically added
- Format: `postgresql://user:password@host:port/database`

#### 7. Add Persistent Volume (Optional - for file storage)

If you need persistent file storage:

1. In service dashboard, go to **"Volumes"** tab
2. Click **"Add Volume"**
3. Configure:
   - **Name**: `app-data`
   - **Mount Path**: `/app/data`
   - **Size**: 1 GB (minimum, expandable)

#### 8. Deploy

1. Railway automatically starts building after configuration
2. Watch the **Deployments** tab for build progress
3. Build completes in ~2-4 minutes
4. Once deployed, you'll see:
   - ✅ Build successful
   - ✅ Health check passing
   - 🌐 **Generate Domain** button

#### 9. Configure Custom Domain

1. In Railway dashboard, go to **"Settings"**
2. Scroll to **"Domains"**
3. Click **"Add Custom Domain"**
4. Enter your domain (e.g., `app.yourdomain.com` or `anha.yourdomain.com`)
5. Railway provides DNS records to configure:
   ```
   Type: CNAME
   Name: app (or @ for root)
   Value: <your-service>.up.railway.app
   ```
6. Update your domain's DNS records
7. Railway automatically provisions SSL certificate (takes 5-10 minutes)

**Free Railway Domain:**
- Click **"Generate Domain"** for a free `*.up.railway.app` domain
- Example: `anha-trading.up.railway.app`
- Includes free SSL certificate

#### 10. Create Admin User

After deployment, create the first admin user:

**Option A: Registration Page (Easiest)**
1. Visit your deployed URL
2. Go to registration page
3. Create an account
4. Manually update role in database (see below)

**Option B: Railway Shell**
1. In Railway dashboard, click **"Shell"** tab
2. Wait for shell to connect
3. Run Python script:

```python
python << EOF
import asyncio
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from app.models.user import User, Role
from app.core.security import hash_password
from app.db.session import Base

async def create_admin():
    import os
    database_url = os.getenv("DATABASE_URL")
    engine = create_async_engine(database_url)
    
    async with AsyncSession(engine) as session:
        admin = User(
            email='admin@yourdomain.com',
            full_name='Admin User',
            phone='+966500000000',
            hashed_password=hash_password('YourSecurePassword123!'),
            role=Role.admin,
            is_active=True
        )
        session.add(admin)
        await session.commit()
        print("Admin user created successfully!")

asyncio.run(create_admin())
EOF
```

**Option C: Direct Database Access**
1. In Railway dashboard, go to PostgreSQL service
2. Click **"Connect"** → **"Psql"**
3. Run SQL:
```sql
-- You'll need to generate the hash first
-- Use Railway Shell to run: python -c "from app.core.security import hash_password; print(hash_password('YourPassword'))"

-- Then insert:
INSERT INTO users (email, full_name, phone, hashed_password, role, is_active)
VALUES ('admin@yourdomain.com', 'Admin User', '+966500000000', '<hashed_password>', 'admin', true);
```

#### 11. Configure SMTP (Optional - for password reset emails)

In Railway **Variables** tab, add:

```bash
SMTP_HOST=smtp.hostinger.com
SMTP_PORT=587
SMTP_USER=your-email@your-domain.com
SMTP_PASSWORD=your-smtp-password
SMTP_FROM_EMAIL=your-email@your-domain.com
SMTP_TLS=true
```

#### 12. Monitor Deployment

- **Logs**: Dashboard → **Logs** tab (real-time streaming)
- **Metrics**: Dashboard → **Metrics** tab (CPU, Memory, Network)
- **Health**: Check `/health` endpoint
- **Deployments**: View deployment history and rollback if needed

---

## Railway Cost Estimation

### Free Tier
- **$5 credit/month** (enough for small apps)
- Pay-as-you-go after credit

### Typical Monthly Usage (Starter App)
| Resource | Usage | Cost |
|----------|-------|------|
| Compute | 720 hrs | ~$5 |
| PostgreSQL | 512 MB | ~$5 |
| Volume (1GB) | 1 GB | ~$1 |
| Bandwidth | 10 GB | Included |
| **Total** | | **~$11/month** |

**With $5 credit: ~$6/month out of pocket**

### Cost Optimization Tips
- Use free Railway domain initially
- Scale down during low-traffic periods
- Monitor usage in dashboard
- Set spending limits in **Settings → Billing**

---

## Railway vs Render Comparison

| Feature | Railway | Render |
|---------|---------|--------|
| Free Tier | $5 credit | Limited free tier |
| PostgreSQL | $5/month | $9/month |
| Ease of Use | ⭐⭐⭐⭐⭐ | ⭐⭐⭐⭐ |
| Auto Deploy | ✅ | ✅ |
| Custom Domain | ✅ Free SSL | ✅ Free SSL |
| Pricing | Pay-as-you-go | Fixed plans |
| **Best For** | **Flexibility & Cost** | Simplicity |

---

## Hostinger VPS Deployment

For detailed Docker deployment instructions on Hostinger VPS, see the original deployment guide in the repository history or use the Render deployment method above.

**Quick Summary:**
1. Set up Ubuntu VPS with Docker & Docker Compose
2. Clone repository and configure `.env.production.local`
3. Run `docker-compose -f docker-compose.prod.yml up -d`
4. Set up SSL with Let's Encrypt
5. Configure Nginx reverse proxy

---

## Troubleshooting
