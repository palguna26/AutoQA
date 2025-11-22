# Runbook

## Overview

This runbook provides operational procedures for AutoQA production deployment.

## Monitoring

### Health Checks

The application provides a health check endpoint:

```
GET /health
```

Expected response:
```json
{
  "status": "healthy",
  "service": "autoqa"
}
```

### Logs

Logs are written to stdout and can be viewed via:
- Render dashboard (if deployed on Render)
- Container logs (if deployed via Docker)
- Application logs (if deployed on VM)

### Key Metrics to Monitor

- Webhook processing latency
- Database connection pool usage
- GitHub API rate limit usage
- LLM API call failures
- Error rates by event type

## Common Issues

### Webhook Verification Fails

**Symptoms:**
- 401 Unauthorized responses
- Logs show "Invalid signature"

**Resolution:**
1. Verify `GITHUB_WEBHOOK_SECRET` matches GitHub App settings
2. Check webhook URL is correct
3. Ensure request body is not modified by middleware/proxy

### Database Connection Errors

**Symptoms:**
- Connection timeout errors
- Pool exhaustion errors

**Resolution:**
1. Check database is running and accessible
2. Verify `DATABASE_URL` is correct
3. Check connection pool settings
4. Review database connection limits

### GitHub API Rate Limits

**Symptoms:**
- 403 Forbidden responses
- "rate limit exceeded" errors

**Resolution:**
1. Implement request queuing/backoff
2. Use installation token caching (already implemented)
3. Monitor rate limit usage via GitHub API headers
4. Consider requesting higher rate limits for GitHub App

### LLM API Failures

**Symptoms:**
- Checklist generation fails
- Timeout errors

**Resolution:**
1. Verify API key is valid
2. Check API quota/limits
3. Implement retry logic with exponential backoff
4. Fall back to heuristic parsing if LLM fails

## Deployment

### Render Deployment

1. Push code to repository
2. Render automatically builds and deploys
3. Verify environment variables are set:
   - `GITHUB_APP_ID`
   - `GITHUB_PRIVATE_KEY`
   - `GITHUB_WEBHOOK_SECRET`
   - `DATABASE_URL`
   - `LLM_API_KEY` (if using LLM)
4. Check health endpoint
5. Test webhook with sample payload

### Docker Deployment

1. Build image:
```bash
docker build -t autoqa .
```

2. Run container:
```bash
docker run -d \
  -p 8000:8000 \
  -e GITHUB_APP_ID=$GITHUB_APP_ID \
  -e GITHUB_PRIVATE_KEY="$GITHUB_PRIVATE_KEY" \
  -e GITHUB_WEBHOOK_SECRET=$GITHUB_WEBHOOK_SECRET \
  -e DATABASE_URL=$DATABASE_URL \
  autoqa
```

3. Run migrations:
```bash
docker exec -it <container_id> alembic upgrade head
```

## Backup and Recovery

### Database Backups

PostgreSQL backups should be configured:
- Daily backups
- Retention: 30 days minimum
- Test restore procedures regularly

### Configuration Backups

Backup critical configuration:
- GitHub App credentials
- Environment variables
- Database connection strings

## Scaling

### Horizontal Scaling

The application is stateless and can be scaled horizontally:
- Multiple instances behind load balancer
- Shared database
- Shared Redis (if using background tasks)

### Vertical Scaling

If experiencing resource constraints:
- Increase database connection pool
- Increase worker memory
- Optimize database queries

## Security

### Secret Rotation

Rotate secrets periodically:
1. Generate new GitHub App private key
2. Update `GITHUB_PRIVATE_KEY` environment variable
3. Update GitHub App settings
4. Restart application

### Access Control

- Restrict database access
- Use secure connection strings
- Enable SSL/TLS for database connections
- Monitor access logs

## Incident Response

### High Severity Issues

1. **Application Down:**
   - Check health endpoint
   - Review application logs
   - Check database connectivity
   - Restart application if needed

2. **Data Loss:**
   - Stop application immediately
   - Assess scope of data loss
   - Restore from backup if possible
   - Investigate root cause

3. **Security Breach:**
   - Rotate all secrets immediately
   - Review access logs
   - Audit database for unauthorized changes
   - Notify security team

### Low Severity Issues

1. **Single Webhook Failure:**
   - Check logs for error details
   - Retry manually if needed
   - Monitor for patterns

2. **LLM API Timeout:**
   - System falls back to heuristic parsing
   - Monitor LLM provider status
   - Retry if transient issue

## Maintenance

### Regular Tasks

- Weekly: Review error logs
- Monthly: Review and optimize database queries
- Quarterly: Rotate secrets
- Annually: Security audit

### Database Maintenance

- Regular VACUUM and ANALYZE
- Monitor table sizes
- Clean up old test results/reports (if needed)

## Support Contacts

- GitHub Issues: [Repository URL]
- Email: [Support Email]
- Documentation: [Docs URL]

