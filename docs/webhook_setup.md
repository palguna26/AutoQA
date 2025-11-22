# Webhook URL Configuration Guide

This guide explains how to configure the webhook URL in your GitHub App settings.

## Webhook Endpoint

Your AutoQA application exposes the webhook endpoint at:
```
/webhooks/github
```

## Determining Your Webhook URL

### For Local Development (using ngrok)

1. **Start your application:**
   ```bash
   uvicorn src.app.main:app --reload --port 8000
   ```

2. **Start ngrok in another terminal:**
   ```bash
   ngrok http 8000
   ```

3. **Copy the HTTPS URL from ngrok** (e.g., `https://abc123.ngrok.io`)

4. **Your webhook URL will be:**
   ```
   https://abc123.ngrok.io/webhooks/github
   ```

   ⚠️ **Note:** ngrok URLs change each time you restart ngrok (unless you have a paid plan with a fixed domain).

### For Production on Render

If you've deployed your application on Render, follow these steps:

#### Step 1: Deploy to Render

1. **Connect your repository to Render:**
   - Go to [Render Dashboard](https://dashboard.render.com)
   - Click **New +** → **Blueprint**
   - Connect your GitHub repository
   - Render will automatically detect `render.yaml` and configure the service

2. **Set environment variables in Render:**
   - Go to your service settings
   - Navigate to **Environment** tab
   - Add the following environment variables (matching your `.env` file):
     - `GITHUB_APP_ID` - Your GitHub App ID
     - `GITHUB_PRIVATE_KEY` - Your GitHub App private key (paste the full key including `-----BEGIN PRIVATE KEY-----` and `-----END PRIVATE KEY-----`)
     - `GITHUB_WEBHOOK_SECRET` - Your webhook secret (must match what you'll set in GitHub App)
     - `LLM_PROVIDER` - `groq`, `openai`, or `none`
     - `LLM_API_KEY` - Your LLM API key (if using LLM)
     - `AUTO_MERGE_ENABLED` - `true` or `false`

3. **Wait for deployment to complete:**
   - Render will build and deploy your application
   - The deployment URL will be shown in the dashboard (e.g., `https://autoqa-backend.onrender.com`)

#### Step 2: Get Your Render Webhook URL

Your Render service will have a URL like:
```
https://autoqa-backend.onrender.com
```

Your webhook URL will be:
```
https://autoqa-backend.onrender.com/webhooks/github
```

**Note:** 
- On Render's free plan, your service may spin down after inactivity. The first request after spin-down may take 30-60 seconds.
- For production, consider upgrading to a paid plan to avoid cold starts.
- You can also set a custom domain in Render settings if you prefer.

## Configuring GitHub App Webhook

### Step 1: Access GitHub App Settings

1. Go to [GitHub Settings](https://github.com/settings)
2. Click **Developer settings** (left sidebar)
3. Click **GitHub Apps**
4. Click on your AutoQA app

### Step 2: Configure Webhook URL

1. In the **General** section, find the **Webhook** settings
2. In the **Webhook URL** field, enter your webhook URL:
   - **For Render:** `https://your-service-name.onrender.com/webhooks/github`
   - Local: `https://your-ngrok-url.ngrok.io/webhooks/github`
   - Other production: `https://your-deployment-url.com/webhooks/github`

   **Example for Render:**
   ```
   https://autoqa-backend.onrender.com/webhooks/github
   ```

3. In the **Webhook secret** field, enter the same secret you have in your Render environment variables as `GITHUB_WEBHOOK_SECRET`

   ⚠️ **Important:** 
   - The webhook secret in GitHub must match exactly with `GITHUB_WEBHOOK_SECRET` in your Render environment variables
   - Make sure there are no extra spaces or newlines
   - The secret should be the same value in both places

### Step 3: Subscribe to Webhook Events

Scroll down to **Subscribe to events** and enable:

- ✅ **Issues** - For issue opened events (to generate checklists)
- ✅ **Pull requests** - For PR opened/synchronize events (to generate test manifests)
- ✅ **Workflow runs** - For CI completion events (to map test results)

### Step 4: Save Changes

1. Click **Save changes** at the bottom of the page
2. If your app is already installed, you may need to reinstall it for changes to take effect

## Verifying Webhook Configuration

### Test the Webhook

1. Make sure your application is running
2. Create a test issue in a repository where your app is installed
3. Check your application logs - you should see webhook events being received

### Check Webhook Deliveries

1. In your GitHub App settings, scroll to **Recent Deliveries**
2. You should see webhook delivery attempts
3. Click on a delivery to see:
   - Request payload
   - Response status
   - Response body

### Common Issues

**❌ 401 Unauthorized**
- Check that `GITHUB_WEBHOOK_SECRET` in your `.env` matches the webhook secret in GitHub App settings
- Verify the secret doesn't have extra spaces or newlines

**❌ 404 Not Found**
- Verify the webhook URL is correct (must end with `/webhooks/github`)
- Check that your application is running and accessible at that URL

**❌ Connection Refused**
- For local development: Make sure ngrok is running
- For production: Check that your deployment is live and accessible

**❌ Events Not Received**
- Verify you've subscribed to the correct events in GitHub App settings
- Check that the app is installed on the repository you're testing with
- Ensure the repository has the necessary permissions

## Updating Webhook URL

If you need to change your webhook URL:

1. Update the **Webhook URL** in GitHub App settings
2. Click **Save changes**
3. Test with a new event (create an issue, open a PR, etc.)

## Security Best Practices

1. **Always use HTTPS** - Never use HTTP for webhooks in production
2. **Use a strong webhook secret** - Generate a random, secure secret
3. **Keep secrets secure** - Never commit `.env` files or secrets to your repository
4. **Rotate secrets periodically** - Update webhook secrets regularly

## Quick Reference

| Environment | Webhook URL Format |
|------------|-------------------|
| Local (ngrok) | `https://[ngrok-id].ngrok.io/webhooks/github` |
| Render | `https://[service-name].onrender.com/webhooks/github` |
| Other Production | `https://[your-domain]/webhooks/github` |

## Render-Specific Notes

### Finding Your Render URL

1. Go to [Render Dashboard](https://dashboard.render.com)
2. Click on your `autoqa-backend` service
3. Your service URL is displayed at the top (e.g., `https://autoqa-backend.onrender.com`)
4. Your webhook URL is: `https://autoqa-backend.onrender.com/webhooks/github`

### Render Free Plan Considerations

⚠️ **Important for Free Plan:**
- Services on Render's free plan spin down after 15 minutes of inactivity
- The first webhook after spin-down may take 30-60 seconds to respond
- GitHub will retry failed webhooks, but there may be delays
- For production use, consider upgrading to a paid plan to avoid cold starts

### Setting Environment Variables in Render

1. Go to your service in Render Dashboard
2. Click **Environment** tab
3. Add each variable:
   - Click **Add Environment Variable**
   - Enter the key (e.g., `GITHUB_WEBHOOK_SECRET`)
   - Enter the value
   - Click **Save Changes**
4. **Important:** After adding/updating environment variables, Render will automatically redeploy your service

### Verifying Render Deployment

1. Check that your service is "Live" in Render dashboard
2. Visit your service URL: `https://your-service.onrender.com`
3. You should see: `{"service":"AutoQA","status":"running","version":"1.0.0"}`
4. Test the health endpoint: `https://your-service.onrender.com/health`
5. Test the webhook endpoint (should return 401 without proper signature): `https://your-service.onrender.com/webhooks/github`

## Next Steps

After configuring the webhook:
1. ✅ Verify webhook deliveries are successful
2. ✅ Test by creating an issue (should generate a checklist)
3. ✅ Test by opening a PR (should generate a test manifest)
4. ✅ Review [GitHub Permissions Guide](github_permissions.md) to ensure permissions are set correctly

