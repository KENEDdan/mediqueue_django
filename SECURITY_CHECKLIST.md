# MediQueue Security Testing Checklist

## 1. AUTHENTICATION SECURITY (CIA - Confidentiality)

### Brute Force Protection
- [ ] Login blocked after 10 failed attempts in 5 minutes
- [ ] Reset endpoint blocked after 5 attempts in 10 minutes
- [ ] Registration blocked after 3 attempts in 10 minutes
- [ ] Test: POST /login/ 11 times with wrong password → should get 403

### Password Security
- [ ] Passwords hashed with bcrypt (check DB — no plaintext)
- [ ] Minimum 8 characters enforced on all registration forms
- [ ] Passwords never returned in any API response
- [ ] No password in URL parameters or logs

### Session Security
- [ ] Session cookie HttpOnly = True (can't be read by JS)
- [ ] Session cookie Secure = True (HTTPS only in production)
- [ ] Session invalidated on logout
- [ ] Session SameSite = Lax (CSRF protection)
- [ ] Test: Copy session cookie → use in different browser → should fail in prod

### 2FA (Clinic Admin)
- [ ] 2FA OTP expires after 5 minutes
- [ ] OTP is invalidated after 3 wrong attempts
- [ ] OTP stored in memory only (not database)
- [ ] Test: Enter correct OTP after 6 minutes → should be expired

---

## 2. AUTHORISATION SECURITY (CIA - Confidentiality)

### Role Enforcement
- [ ] Patient cannot access /superadmin/ → 403
- [ ] Patient cannot access /clinics/admin/ → 403
- [ ] Doctor cannot access /receptionist/ views → 403
- [ ] Receptionist cannot access superadmin finance → 403
- [ ] Clinic admin cannot see other clinic's data → 403
- [ ] Test each role with each restricted URL

### Object-Level Security
- [ ] Patient A cannot view Patient B's appointments
- [ ] Clinic A cannot view Clinic B's transactions
- [ ] Doctor from Clinic A cannot write report for Clinic B's patient
- [ ] Test: Change ID in URL to another clinic's ID → should 404 or 403

### CSRF Protection
- [ ] All POST forms have {% csrf_token %}
- [ ] API endpoints verify CSRF token
- [ ] Test: Submit form without CSRF token → should be rejected

---

## 3. INJECTION PREVENTION (CIA - Integrity)

### SQL Injection
- [ ] All queries use Django ORM (no raw SQL)
- [ ] Search inputs use .filter(field__icontains=value)
- [ ] Test: Enter ' OR '1'='1 in search → no SQL error, no data leak

### XSS Prevention
- [ ] All user input auto-escaped by Django templates
- [ ] No |safe filter on user-provided content
- [ ] Rich text areas (medical notes) are escaped on output
- [ ] Test: Enter <script>alert('xss')</script> in name field → should show as text

### File Upload Security
- [ ] File type validated by MIME type (not just extension)
- [ ] File size limited to 10MB
- [ ] Filename sanitized (no path traversal)
- [ ] Files stored outside web root or behind authentication
- [ ] Test: Upload a .php file renamed to .jpg → should be rejected

---

## 4. DATA SECURITY (CIA - Confidentiality)

### Sensitive Data Handling
- [ ] Credit card numbers: only last 4 digits stored
- [ ] Passwords: bcrypt hash only, never stored plaintext
- [ ] Security answers: stored lowercase (case-insensitive matching)
- [ ] Medical records: accessible only to authorized roles
- [ ] Audit log: records all access to medical reports

### API Security
- [ ] Stripe secret key NEVER in frontend code or templates
- [ ] API keys in environment variables only (.env)
- [ ] .env excluded from git (.gitignore)
- [ ] No secrets in Django templates

### HTTPS
- [ ] All traffic redirected to HTTPS in production
- [ ] HSTS header set (max-age=31536000)
- [ ] SSL certificate valid and not expired

---

## 5. AVAILABILITY (CIA - Availability)

### Rate Limiting
- [ ] Login: 10/5min per IP
- [ ] Password reset: 5/10min per IP
- [ ] Clinic registration: 3/10min per IP
- [ ] API endpoints: 60/min per IP

### Error Handling
- [ ] 500 errors show custom page (no stack traces to users)
- [ ] 404 errors show custom page
- [ ] Database errors don't expose schema
- [ ] Test: Visit non-existent URL → custom 404 page

### Resource Limits
- [ ] File upload max 10MB
- [ ] POST body max 10MB
- [ ] Long-running queries have timeouts

---

## 6. AUDIT & MONITORING

### Logging
- [ ] All login attempts logged (success and failure)
- [ ] All admin actions logged
- [ ] All payment actions logged
- [ ] All file uploads logged
- [ ] Security events logged to security.log
- [ ] Audit trail in audit.log

### Test Commands
```bash
# Check for common Django security issues
py manage.py check --deploy

# Verify no debug info leaked
curl -s http://localhost:8000/does-not-exist | grep -i traceback

# Check security headers
curl -I http://localhost:8000/ | grep -E "(X-|Content-Security|Strict)"

# Check CSRF on all forms (look for missing csrf_token)
grep -r "method=\"post\"" templates/ | grep -v csrf
```

---

## 7. PRE-LAUNCH SECURITY COMMANDS

```powershell
# Run Django security check
py manage.py check --deploy

# Check for missing migrations
py manage.py showmigrations

# Collect static (for production)
py manage.py collectstatic --no-input

# Run all tests
py manage.py test

# Verify environment
python -c "from decouple import config; print('SECRET_KEY set:', bool(config('SECRET_KEY')))"
```

---

## 8. PENETRATION TEST SCENARIOS TO RUN

1. **Horizontal privilege escalation**
   - Log in as Clinic A's admin
   - Manually change clinic_id in URL to Clinic B
   - Should return 403 or 404

2. **Vertical privilege escalation**
   - Log in as receptionist
   - Navigate to /superadmin/ directly
   - Should return 403

3. **IDOR on medical reports**
   - Log in as Patient A
   - Change report ID in URL to Patient B's report ID
   - Should return 403

4. **Brute force**
   - Script 20 rapid POST requests to /login/
   - Should start getting 429/403 after 10 attempts

5. **Session fixation**
   - Note session cookie before login
   - Login successfully
   - Session ID should have changed

6. **SQL injection in search**
   - Search for: `' OR 1=1; DROP TABLE users; --`
   - Should return no results, no error, tables intact

7. **XSS in profile name**
   - Register with name: `<script>alert(document.cookie)</script>`
   - View profile page
   - Should show literal text, no alert box