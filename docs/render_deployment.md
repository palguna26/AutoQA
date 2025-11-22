# Render Deployment Guide

This guide walks you through deploying AutoQA to Render and configuring the webhook URL.

## Prerequisites

- A GitHub account with your AutoQA repository
- A Render account (sign up at [render.com](https://render.com))
- GitHub App credentials (App ID, Private Key, Webhook Secret)

## Step 1: Deploy to Render

### 1.1 Connect Repository

1. Go to [Render Dashboard](https://dashboard.render.com)
2. Click **New +** → **Blueprint**
3. Connect your GitHub account (if not already connected)
4. Select your AutoQA repository
5. Render will automatically detect `render.yaml` and configure the service

### 1.2 Review Service Configuration

Render will create:
- **Web Service:** `autoqa-backend` (from `render.yaml`)
- **PostgreSQL Database:** `autoqa-db` (from `render.yaml`)

The service will be configured with:
- Build command: `pip install -r requirements.txt`
- Start command: `uvicorn src.app.main:app --host 0.0.0.0 --port $PORT`
- Port: `10000`

### 1.3 Set Environment Variables

Before deploying, set these environment variables in Render:

1. Go to your `autoqa-backend` service
2. Click **Environment** tab
3. Add the following variables:

| Variable | Description | Example |
|----------|-------------|---------|
| `GITHUB_APP_ID` | Your GitHub App ID | `12345` |
| `GITHUB_PRIVATE_KEY` | Full private key (including BEGIN/END lines) | `-----BEGIN PRIVATE KEY-----\n...\n-----END PRIVATE KEY-----` |
| `GITHUB_WEBHOOK_SECRET` | Webhook secret (generate a secure random string) | `your-secret-here` |
| `LLM_PROVIDER` | LLM provider: `groq`, `openai`, or `none` | `groq` |
| `LLM_API_KEY` | Your LLM API key (if using LLM) | `your-api-key` |
| `AUTO_MERGE_ENABLED` | Enable auto-merge feature | `false` |

**Important Notes:**
- For `GITHUB_PRIVATE_KEY`: Paste the entire key including `-----BEGIN PRIVATE KEY-----` and `-----END PRIVATE KEY-----`
- Keep newlines as `\n` in the private key
- `GITHUB_WEBHOOK_SECRET` must match what you'll set in GitHub App settings
- `DATABASE_URL` is automatically set by Render from the database service

### 1.4 Deploy

1. Click **Save Changes** (if you added environment variables)
2. Render will automatically start building and deploying
3. Wait for deployment to complete (usually 2-5 minutes)
4. Check the **Logs** tab to verify successful deployment

## Step 2: Get Your Render URL

1. Once deployment is complete, go to your service dashboard
2. Your service URL is displayed at the top, for example:
   ```
   https://autoqa-backend.onrender.com
   ```
3. Your webhook URL will be:
   ```
   https://autoqa-backend.onrender.com/webhooks/github
   ```

**Note:** The URL format is `https://[service-name].onrender.com` where `service-name` matches the name in `render.yaml` (currently `autoqa-backend`).

## Step 3: Verify Deployment

### 3.1 Test Root Endpoint

Visit your service URL in a browser:
```
https://autoqa-backend.onrender.com
```

You should see:
```json
{
  "service": "AutoQA",
  "status": "running",
  "version": "1.0.0"
}
```

### 3.2 Test Health Endpoint

Visit:
```
https://autoqa-backend.onrender.com/health
```

You should see:
```json
{
  "status": "healthy",
  "service": "autoqa"
}
```

### 3.3 Test Webhook Endpoint (Optional)

Try accessing the webhook endpoint (without proper signature, it should return 401):
```
https://autoqa-backend.onrender.com/webhooks/github
```

Expected: `401 Unauthorized` (this is correct - it means the endpoint is working)

## Step 4: Configure GitHub App Webhook

Now that your app is deployed, configure the webhook in GitHub:

1. Go to [GitHub Settings](https://github.com/settings)
2. Click **Developer settings** → **GitHub Apps**
3. Click on your AutoQA app
4. In the **Webhook** section:
   - **Webhook URL:** Enter `https://autoqa-backend.onrender.com/webhooks/github`
     (Replace `autoqa-backend` with your actual service name if different)
   - **Webhook secret:** Enter the same value as `GITHUB_WEBHOOK_SECRET` in Render
5. Scroll to **Subscribe to events** and enable:
   - ✅ **Issues**
   - ✅ **Pull requests**
   - ✅ **Workflow runs**
6. Click **Save changes**

## Step 5: Test the Integration

1. **Create a test issue** in a repository where your app is installed
2. **Check Render logs** - You should see webhook events being received
3. **Check GitHub App deliveries** - Go to your GitHub App settings → **Recent Deliveries** to see webhook delivery status

## Troubleshooting

### Service Won't Start

**Check logs in Render dashboard:**
- Look for import errors
- Verify all dependencies are in `requirements.txt`
- Check database connection string

**Common issues:**
- Missing environment variables
- Database not ready (wait a few minutes after database creation)
- Port configuration issues

### Webhook Returns 401

- Verify `GITHUB_WEBHOOK_SECRET` in Render matches GitHub App settings
- Check that the secret doesn't have extra spaces
- Ensure the webhook URL is correct

### Webhook Returns 404

- Verify the webhook URL ends with `/webhooks/github`
- Check that your service is deployed and running
- Verify the service URL in Render dashboard

### Service Spins Down (Free Plan)

On Render's free plan, services spin down after 15 minutes of inactivity:
- First request after spin-down takes 30-60 seconds
- GitHub will retry failed webhooks
- Consider upgrading to paid plan for production use

### Database Connection Issues

- Verify `DATABASE_URL` is automatically set by Render
- Check database is running in Render dashboard
- Wait a few minutes after database creation for it to be ready

## Updating Your Deployment

### Update Code

1. Push changes to your GitHub repository
2. Render will automatically detect changes and redeploy
3. Monitor the **Logs** tab for deployment progress

### Update Environment Variables

1. Go to service → **Environment** tab
2. Add/update variables
3. Click **Save Changes**
4. Render will automatically redeploy

### Manual Redeploy

1. Go to service dashboard
2. Click **Manual Deploy** → **Deploy latest commit**

## Monitoring

### View Logs

1. Go to your service in Render dashboard
2. Click **Logs** tab
3. View real-time application logs

### Health Checks

Render automatically monitors your service. Check health endpoint:
```
https://autoqa-backend.onrender.com/health
```

### GitHub Webhook Deliveries

Monitor webhook deliveries in GitHub App settings:
1. Go to your GitHub App
2. Scroll to **Recent Deliveries**
3. View delivery status, payload, and responses

## Cost Considerations

### Free Plan

- **Web Service:** Free tier available (spins down after inactivity)
- **PostgreSQL:** Free tier available (limited to 90 days, then $7/month)
- **Limitations:** 
  - Service spins down after 15 min inactivity
  - Cold starts take 30-60 seconds
  - Limited database storage

### Paid Plans

For production use, consider:
- **Starter Plan ($7/month):** Keeps service always on
- **Standard Plan ($25/month):** Better performance, more resources

## Next Steps

After successful deployment:

1. ✅ Verify webhook is receiving events
2. ✅ Test by creating an issue (should generate checklist)
3. ✅ Test by opening a PR (should generate test manifest)
4. ✅ Review [Webhook Setup Guide](webhook_setup.md) for detailed webhook configuration
5. ✅ Review [GitHub Permissions Guide](github_permissions.md) to ensure permissions are correct

## Support

- Render Documentation: https://render.com/docs
- Render Support: https://render.com/support
- Check application logs in Render dashboard for debugging

