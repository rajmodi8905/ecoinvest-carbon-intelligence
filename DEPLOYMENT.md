# EcoInvest Pathway - Deployment Guide

## 🚀 Quick Deployment

This guide covers deploying the **frontend** to Vercel and **backend** to a cloud platform.

---

## 📦 Frontend Deployment (Vercel)

### Step 1: Prepare Repository
```bash
git add .
git commit -m "Prepare for Vercel deployment"
git push origin main
```

### Step 2: Deploy to Vercel

#### Option A: Vercel CLI (Recommended)
```bash
# Install Vercel CLI
npm i -g vercel

# Deploy
vercel

# Follow the prompts:
# - Set up and deploy: Yes
# - Which scope: (your account)
# - Link to existing project: No
# - Project name: ecoinvest-pathway
# - Directory: ./
# - Build settings: Auto-detected (Vite)

# For production
vercel --prod
```

#### Option B: Vercel Dashboard
1. Go to [vercel.com/new](https://vercel.com/new)
2. Import your GitHub repository: `rajmodi8905/ecoinvest-carbon-intelligence`
3. Configure project:
   - **Framework Preset**: Vite
   - **Build Command**: `npm run build`
   - **Output Directory**: `dist`
   - **Install Command**: `npm install`

### Step 3: Configure Environment Variables

In Vercel Dashboard → Settings → Environment Variables, add:

```
VITE_API_URL=https://your-backend-url.com
VITE_WS_URL=https://your-backend-url.com
```

**Important**: Replace `your-backend-url.com` with your actual backend URL after deploying the backend (see below).

### Step 4: Redeploy
After adding environment variables, trigger a new deployment:
- Go to Deployments → Latest Deployment → Redeploy

---

## 🐳 Backend Deployment Options

The backend requires:
- Python 3.10+
- PostgreSQL database
- Redis cache
- Kafka (optional, for real-time features)
- Persistent WebSocket connections

### Option 1: Railway (Recommended) ⭐

**Pros**: Easy Docker support, PostgreSQL/Redis add-ons, WebSocket support

1. **Create Railway Account**: [railway.app](https://railway.app)

2. **Deploy Backend**:
```bash
# Install Railway CLI
npm i -g @railway/cli

# Login
railway login

# Link project
railway init

# Deploy
railway up
```

3. **Add Services**:
   - In Railway dashboard, add PostgreSQL
   - Add Redis
   - Copy connection URLs

4. **Set Environment Variables**:
```env
GOOGLE_API_KEY=your_gemini_key
TAVILY_API_KEY=your_tavily_key
DB_HOST=<from Railway PostgreSQL>
DB_PORT=5432
DB_NAME=railway
DB_USER=postgres
DB_PASSWORD=<from Railway>
REDIS_HOST=<from Railway Redis>
REDIS_PORT=6379
CORS_ORIGINS=https://your-vercel-app.vercel.app
```

5. **Get Backend URL**: Copy the generated Railway URL (e.g., `https://ecoinvest-backend-production.up.railway.app`)

6. **Update Vercel**: Add this URL to Vercel environment variables as `VITE_API_URL` and `VITE_WS_URL`

---

### Option 2: Render

**Pros**: Free tier available, managed PostgreSQL/Redis

1. **Create Render Account**: [render.com](https://render.com)

2. **Create Web Service**:
   - New → Web Service
   - Connect repository: `rajmodi8905/ecoinvest-carbon-intelligence`
   - Root Directory: `backend`
   - Build Command: `pip install -r requirements.txt`
   - Start Command: `gunicorn --worker-class eventlet -w 1 --bind 0.0.0.0:$PORT app:app`

3. **Add PostgreSQL**:
   - Dashboard → New → PostgreSQL
   - Copy Internal Database URL

4. **Add Redis**:
   - Dashboard → New → Redis
   - Copy Internal Redis URL

5. **Environment Variables**:
```env
GOOGLE_API_KEY=your_key
TAVILY_API_KEY=your_key
DATABASE_URL=<from Render PostgreSQL>
REDIS_URL=<from Render Redis>
CORS_ORIGINS=https://your-vercel-app.vercel.app
```

6. **Update requirements.txt**: Add `gunicorn` and `eventlet`
```bash
cd backend
echo "gunicorn==21.2.0" >> requirements.txt
echo "eventlet==0.33.3" >> requirements.txt
git add requirements.txt
git commit -m "Add production server dependencies"
git push
```

---

### Option 3: Heroku

**Pros**: Established platform, add-on marketplace

1. **Create Heroku Account**: [heroku.com](https://heroku.com)

2. **Create App**:
```bash
# Install Heroku CLI
npm i -g heroku

# Login
heroku login

# Create app
heroku create ecoinvest-backend

# Add buildpack
heroku buildpacks:set heroku/python

# Add PostgreSQL
heroku addons:create heroku-postgresql:mini

# Add Redis
heroku addons:create heroku-redis:mini
```

3. **Create Procfile** in `backend/`:
```
web: gunicorn --worker-class eventlet -w 1 --bind 0.0.0.0:$PORT app:app
```

4. **Set Environment Variables**:
```bash
heroku config:set GOOGLE_API_KEY=your_key
heroku config:set TAVILY_API_KEY=your_key
heroku config:set CORS_ORIGINS=https://your-vercel-app.vercel.app
```

5. **Deploy**:
```bash
git subtree push --prefix backend heroku main
```

---

### Option 4: DigitalOcean App Platform

**Pros**: Affordable, good Docker support

1. **Create Account**: [digitalocean.com](https://digitalocean.com)

2. **Create App**:
   - Apps → Create App
   - Connect GitHub: `rajmodi8905/ecoinvest-carbon-intelligence`
   - Select `backend` directory
   - Choose Docker or Python runtime

3. **Add Managed Database**:
   - Add Database Component → PostgreSQL
   - Add Database Component → Redis

4. **Configure Environment Variables** (same as above)

5. **Deploy**

---

## 🔄 Full Deployment Workflow

### 1. Deploy Backend First
Choose one of the backend options above and deploy. **Save the backend URL**.

### 2. Update Frontend Environment
Add backend URL to Vercel:
```
VITE_API_URL=https://your-backend-url.com
VITE_WS_URL=https://your-backend-url.com
```

### 3. Deploy/Redeploy Frontend
Redeploy on Vercel to pick up new environment variables.

### 4. Update Backend CORS
Update backend environment variable:
```
CORS_ORIGINS=https://your-frontend.vercel.app
```

### 5. Test Connection
Visit your Vercel URL and test:
- Dashboard loads
- Analytics data appears
- Chatbot responds
- News feed updates
- Company reports generate

---

## 🛠️ Troubleshooting

### Frontend Issues

**Problem**: API calls failing
- **Solution**: Check `VITE_API_URL` in Vercel environment variables
- Verify backend is running: visit `https://your-backend-url.com/health`

**Problem**: WebSocket not connecting
- **Solution**: Check `VITE_WS_URL` matches backend URL
- Ensure backend supports WebSocket (Railway, Render, Heroku all support it)

**Problem**: Build fails
- **Solution**: Check build logs in Vercel dashboard
- Verify `package.json` scripts are correct
- Run `npm run build` locally to test

### Backend Issues

**Problem**: Database connection fails
- **Solution**: Verify `DB_HOST`, `DB_PORT`, `DB_USER`, `DB_PASSWORD` are correct
- Check database is running and accessible

**Problem**: Redis connection fails
- **Solution**: Verify `REDIS_HOST` and `REDIS_PORT`
- Some platforms use `REDIS_URL` instead

**Problem**: CORS errors
- **Solution**: Update `CORS_ORIGINS` to include your Vercel domain
- Example: `https://ecoinvest.vercel.app,https://ecoinvest-git-main.vercel.app`

**Problem**: WebSocket not working
- **Solution**: Ensure using `eventlet` worker in Gunicorn
- Check firewall/security group allows WebSocket

---

## 📊 Monitoring

### Vercel Analytics
- Enable in Vercel Dashboard → Analytics
- Monitor page views, performance, errors

### Backend Monitoring
- **Railway**: Built-in metrics and logs
- **Render**: Metrics tab in dashboard
- **Heroku**: `heroku logs --tail`

### Custom Monitoring
Consider adding:
- Sentry for error tracking
- LogRocket for session replay
- New Relic for APM

---

## 🔐 Security Checklist

- [ ] All API keys in environment variables (never in code)
- [ ] CORS properly configured for production domain
- [ ] Database has strong password
- [ ] Redis password protected (if exposed)
- [ ] HTTPS enabled on both frontend and backend
- [ ] Rate limiting enabled on API endpoints
- [ ] Input validation on all user inputs
- [ ] SQL injection protection (using ORM)

---

## 💰 Cost Estimates

### Free Tier Option
- **Vercel**: Free (Hobby plan)
- **Railway**: $5/month credit (then pay-as-you-go ~$10-20/month)
- **Total**: ~$10-20/month

### Production Option
- **Vercel Pro**: $20/month
- **Railway**: ~$25-50/month (depending on usage)
- **Total**: ~$45-70/month

---

## 📞 Support

If you encounter issues:
1. Check deployment logs
2. Verify environment variables
3. Test backend health endpoint
4. Review CORS configuration
5. Open GitHub issue with details

---

**Ready to deploy?** Start with Railway for backend + Vercel for frontend - it's the easiest path! 🚀
