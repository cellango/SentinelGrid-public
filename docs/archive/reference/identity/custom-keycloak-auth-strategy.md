# Custom Keycloak Authentication Strategy

> **Historical reference — superseded for release decisions.** This records an earlier design, operation, or validation attempt. It is not the current architecture, a supported quick start, or evidence that the source preview is production ready. Start with the repository README and current documentation index.


## Overview

Implement a custom authentication UI that matches SentinelGrid's design while using Keycloak as the backend authentication and authorization service. Users will see a branded login dialog instead of being redirected to Keycloak's login page.

## Goals

1. **Custom Login Dialog**: Branded login UI that matches SentinelGrid's design
2. **Keycloak Backend**: Use Keycloak for all authentication/authorization (no redirect)
3. **Sign Up Flow**: Create realms and users in Keycloak via API
4. **Seamless UX**: Users never see Keycloak UI

## Architecture

### Current Flow (Redirect-Based)
```
User clicks "Sign in"
  ↓
Redirect to Keycloak login page
  ↓
User enters credentials
  ↓
Keycloak redirects back with code
  ↓
Frontend exchanges code for tokens
```

### Proposed Flow (API-Based)
```
User clicks "Sign in"
  ↓
Show custom login dialog
  ↓
User enters credentials
  ↓
Frontend → IAM Agent API (POST /api/v1/auth/login)
  ↓
IAM Agent → Keycloak (Direct Access Grant / ROPC)
  ↓
IAM Agent returns tokens to frontend
  ↓
Frontend stores tokens and uses for API calls
```

## Components

### 1. Frontend Components

#### Login Dialog Component
- **Location**: `website/components/auth/LoginDialog.tsx`
- **Features**:
  - Modal/dialog that matches SentinelGrid UI
  - Email/password input fields
  - "Remember me" checkbox
  - "Forgot password?" link
  - Error message display
  - Loading state during authentication
  - Close button

#### Sign Up Form Component
- **Location**: `website/components/auth/SignUpForm.tsx` (enhance existing)
- **Features**:
  - Multi-step form (existing)
  - Company name, email, password fields
  - Terms acceptance
  - Error handling
  - Success state

#### Auth API Client
- **Location**: `website/lib/api/auth.ts` (new or enhance existing)
- **Endpoints**:
  - `login(email, password)` - Authenticate user
  - `signup(userData)` - Create new account
  - `logout()` - Invalidate session
  - `refreshToken()` - Refresh access token
  - `getUserInfo()` - Get current user info

### 2. Backend API Endpoints

#### IAM Agent - Authentication Endpoints

**POST /api/v1/auth/login**
- **Purpose**: Authenticate user with Keycloak
- **Request**:
  ```json
  {
    "email": "user@example.com",
    "password": "password123",
    "remember_me": true
  }
  ```
- **Response**:
  ```json
  {
    "access_token": "...",
    "refresh_token": "...",
    "expires_in": 3600,
    "token_type": "Bearer",
    "user": {
      "id": "user-id",
      "email": "user@example.com",
      "tenant_id": "tenant-id",
      "roles": ["TENANT_ADMIN"]
    }
  }
  ```
- **Implementation**:
  - Use Keycloak Direct Access Grants (ROPC flow)
  - Validate credentials with Keycloak
  - Return tokens and user info
  - Handle errors (invalid credentials, account locked, etc.)

**POST /api/v1/auth/signup**
- **Purpose**: Create new tenant and user in Keycloak
- **Request**:
  ```json
  {
    "company_name": "Acme Corp",
    "email": "admin@acme.com",
    "password": "SecurePass123!",
    "first_name": "John",
    "last_name": "Doe"
  }
  ```
- **Response**:
  ```json
  {
    "success": true,
    "tenant_id": "tenant-uuid",
    "realm": "acme-corp",
    "user_id": "user-uuid",
    "message": "Account created successfully"
  }
  ```
- **Implementation**:
  - Create new realm in Keycloak (or use shared realm with tenant isolation)
  - Create tenant in PostgreSQL
  - Create user in Keycloak realm
  - Assign default role (TENANT_ADMIN)
  - Send welcome email (optional)
  - Return success/error

**POST /api/v1/auth/logout**
- **Purpose**: Invalidate Keycloak session
- **Request**: `{ "refresh_token": "..." }`
- **Response**: `{ "success": true }`
- **Implementation**:
  - Call Keycloak logout endpoint
  - Invalidate refresh token

**POST /api/v1/auth/refresh**
- **Purpose**: Refresh access token
- **Request**: `{ "refresh_token": "..." }`
- **Response**: Same as login response
- **Implementation**:
  - Use Keycloak token refresh endpoint
  - Return new tokens

**GET /api/v1/auth/me**
- **Purpose**: Get current user info
- **Request**: Bearer token in Authorization header
- **Response**:
  ```json
  {
    "id": "user-id",
    "email": "user@example.com",
    "tenant_id": "tenant-id",
    "roles": ["TENANT_ADMIN"],
    "first_name": "John",
    "last_name": "Doe"
  }
  ```
- **Implementation**:
  - Validate token with Keycloak
  - Extract user info from token or Keycloak API
  - Return user details

### 3. Keycloak Configuration

#### Realm Strategy

**Option A: Multi-Realm (One Realm Per Tenant)**
- **Pros**: Complete isolation, easier to manage per-tenant settings
- **Cons**: More complex, requires realm creation API
- **Use Case**: Enterprise customers, strict isolation requirements

**Option B: Single Realm with Tenant Attribute (Recommended for MVP)**
- **Pros**: Simpler, faster signup, easier to manage
- **Cons**: Less isolation (but can be managed with policies)
- **Use Case**: SMB customers, faster onboarding
- **Implementation**:
  - Use single `sentinelgrid` realm
  - Store `tenant_id` as user attribute
  - Use protocol mapper to include `tenant_id` in tokens
  - Filter data by `tenant_id` in application layer

**Recommendation**: Start with **Option B** (single realm), migrate to Option A if needed.

#### Client Configuration

**Public Client for Website**
- **Client ID**: `sentinelgrid-web`
- **Type**: Public client
- **Direct Access Grants**: Enabled (for ROPC flow)
- **Valid Redirect URIs**: `http://localhost:3000/*`, `https://*.sentinelgrid.com/*`
- **Web Origins**: `+` (all)

**Confidential Client for IAM Agent**
- **Client ID**: `sentinelgrid-iam-agent`
- **Type**: Confidential client
- **Service Account**: Enabled
- **Direct Access Grants**: Enabled (for admin operations)

## Implementation Plan

### Phase 1: Backend API (IAM Agent)

#### Step 1.1: Login Endpoint
- [ ] Create `POST /api/v1/auth/login` endpoint
- [ ] Implement Keycloak Direct Access Grant (ROPC) flow
- [ ] Handle authentication errors gracefully
- [ ] Return tokens and user info
- [ ] Add rate limiting for security
- [ ] Add logging (without passwords)

#### Step 1.2: Signup Endpoint
- [ ] Create `POST /api/v1/auth/signup` endpoint
- [ ] Validate input (email format, password strength)
- [ ] Check if email already exists
- [ ] Create tenant in PostgreSQL
- [ ] Create user in Keycloak (single realm approach)
- [ ] Assign default role (TENANT_ADMIN)
- [ ] Set `tenant_id` user attribute
- [ ] Return success/error
- [ ] Send welcome email (optional)

#### Step 1.3: Logout Endpoint
- [ ] Create `POST /api/v1/auth/logout` endpoint
- [ ] Invalidate Keycloak session
- [ ] Return success

#### Step 1.4: Refresh Token Endpoint
- [ ] Create `POST /api/v1/auth/refresh` endpoint
- [ ] Validate refresh token
- [ ] Get new access token from Keycloak
- [ ] Return new tokens

#### Step 1.5: Get User Info Endpoint
- [ ] Create `GET /api/v1/auth/me` endpoint
- [ ] Validate access token
- [ ] Get user info from Keycloak or token
- [ ] Return user details

### Phase 2: Frontend Components

#### Step 2.1: Login Dialog Component
- [ ] Create `LoginDialog.tsx` component
- [ ] Match SentinelGrid UI design (dark theme, cyan accents)
- [ ] Add email/password input fields
- [ ] Add "Remember me" checkbox
- [ ] Add "Forgot password?" link (future)
- [ ] Add error message display
- [ ] Add loading state
- [ ] Add close button
- [ ] Handle form submission
- [ ] Call auth API

#### Step 2.2: Auth API Client
- [ ] Create `website/lib/api/auth.ts`
- [ ] Implement `login()` function
- [ ] Implement `signup()` function
- [ ] Implement `logout()` function
- [ ] Implement `refreshToken()` function
- [ ] Implement `getUserInfo()` function
- [ ] Handle errors
- [ ] Store tokens in localStorage/sessionStorage

#### Step 2.3: Update AuthProvider
- [ ] Update `AuthProvider.tsx` to use new API
- [ ] Remove Keycloak redirect logic
- [ ] Add login dialog trigger
- [ ] Handle token storage
- [ ] Handle token refresh
- [ ] Handle logout

#### Step 2.4: Update Login Page
- [ ] Update `website/app/login/page.tsx`
- [ ] Remove Keycloak redirect
- [ ] Show LoginDialog component
- [ ] Handle successful login (redirect to dashboard)

#### Step 2.5: Update Sign Up Flow
- [ ] Update `website/app/signup/page.tsx`
- [ ] Call signup API endpoint
- [ ] Handle success (auto-login or redirect to login)
- [ ] Handle errors (show in UI)

#### Step 2.6: Update Header
- [ ] Update `website/components/Header.tsx`
- [ ] Trigger login dialog instead of redirect
- [ ] Show user info when authenticated

### Phase 3: Security & Error Handling

#### Step 3.1: Security
- [ ] Add rate limiting to login endpoint (prevent brute force)
- [ ] Add CAPTCHA for signup (optional, future)
- [ ] Validate password strength on signup
- [ ] Sanitize inputs
- [ ] Use HTTPS in production
- [ ] Implement CSRF protection

#### Step 3.2: Error Handling
- [ ] Handle invalid credentials
- [ ] Handle account locked/disabled
- [ ] Handle network errors
- [ ] Handle token expiration
- [ ] Show user-friendly error messages

#### Step 3.3: Token Management
- [ ] Store tokens securely (httpOnly cookies in production)
- [ ] Implement automatic token refresh
- [ ] Handle token expiration gracefully
- [ ] Clear tokens on logout

### Phase 4: Testing

#### Step 4.1: Unit Tests
- [ ] Test login endpoint
- [ ] Test signup endpoint
- [ ] Test logout endpoint
- [ ] Test token refresh
- [ ] Test error cases

#### Step 4.2: Integration Tests
- [ ] Test full login flow
- [ ] Test full signup flow
- [ ] Test token refresh flow
- [ ] Test error scenarios

#### Step 4.3: E2E Tests
- [ ] Test login dialog UI
- [ ] Test signup form
- [ ] Test authentication state persistence
- [ ] Test logout

## Keycloak Flow Details

### Direct Access Grant (ROPC) Flow

```
1. Frontend sends credentials to IAM Agent
   POST /api/v1/auth/login
   {
     "email": "user@example.com",
     "password": "password123"
   }

2. IAM Agent calls Keycloak
   POST {KEYCLOAK_URL}/realms/{realm}/protocol/openid-connect/token
   {
     "grant_type": "password",
     "client_id": "sentinelgrid-web",
     "username": "user@example.com",
     "password": "password123"
   }

3. Keycloak validates and returns tokens
   {
     "access_token": "...",
     "refresh_token": "...",
     "expires_in": 3600
   }

4. IAM Agent returns tokens to frontend
   {
     "access_token": "...",
     "refresh_token": "...",
     "user": {...}
   }
```

### Signup Flow

```
1. Frontend sends signup data to IAM Agent
   POST /api/v1/auth/signup
   {
     "company_name": "Acme Corp",
     "email": "admin@acme.com",
     "password": "SecurePass123!",
     "first_name": "John",
     "last_name": "Doe"
   }

2. IAM Agent validates input
   - Check email format
   - Check password strength
   - Check if email exists

3. IAM Agent creates tenant in PostgreSQL
   INSERT INTO tenants (id, name, slug, ...)

4. IAM Agent creates user in Keycloak
   POST {KEYCLOAK_URL}/admin/realms/{realm}/users
   {
     "username": "admin@acme.com",
     "email": "admin@acme.com",
     "firstName": "John",
     "lastName": "Doe",
     "enabled": true,
     "attributes": {
       "tenant_id": ["tenant-uuid"]
     }
   }

5. IAM Agent sets password
   PUT {KEYCLOAK_URL}/admin/realms/{realm}/users/{user-id}/reset-password
   {
     "type": "password",
     "value": "SecurePass123!",
     "temporary": false
   }

6. IAM Agent assigns role
   POST {KEYCLOAK_URL}/admin/realms/{realm}/users/{user-id}/role-mappings/realm
   {
     "roles": [{"name": "TENANT_ADMIN"}]
   }

7. IAM Agent returns success
   {
     "success": true,
     "tenant_id": "tenant-uuid",
     "user_id": "user-uuid"
   }
```

## Security Considerations

### 1. Password Security
- **Never log passwords**
- **Use HTTPS in production**
- **Validate password strength** (min length, complexity)
- **Hash passwords** (Keycloak handles this)

### 2. Token Security
- **Store tokens securely** (httpOnly cookies in production, localStorage for dev)
- **Implement token refresh** (before expiration)
- **Validate tokens** on every API call
- **Clear tokens on logout**

### 3. Rate Limiting
- **Limit login attempts** (prevent brute force)
- **Limit signup attempts** (prevent abuse)
- **Use exponential backoff** for failed attempts

### 4. Input Validation
- **Sanitize all inputs**
- **Validate email format**
- **Validate password strength**
- **Prevent SQL injection** (use parameterized queries)
- **Prevent XSS** (sanitize outputs)

## Error Messages

### Login Errors
- `INVALID_CREDENTIALS` → "Invalid email or password"
- `ACCOUNT_DISABLED` → "Your account has been disabled. Please contact support."
- `ACCOUNT_LOCKED` → "Your account has been temporarily locked. Please try again later."
- `TOO_MANY_ATTEMPTS` → "Too many login attempts. Please try again in 15 minutes."

### Signup Errors
- `EMAIL_EXISTS` → "An account with this email already exists"
- `WEAK_PASSWORD` → "Password must be at least 8 characters with uppercase, lowercase, and numbers"
- `INVALID_EMAIL` → "Please enter a valid email address"
- `COMPANY_NAME_REQUIRED` → "Company name is required"

## UI/UX Considerations

### Login Dialog
- **Design**: Match SentinelGrid dark theme with cyan accents
- **Size**: Modal, centered, max-width 400px
- **Animation**: Smooth fade-in/out
- **Accessibility**: Keyboard navigation, focus management, ARIA labels
- **Mobile**: Responsive, full-screen on mobile

### Sign Up Form
- **Multi-step**: Keep existing multi-step design
- **Progress indicator**: Show current step
- **Validation**: Real-time validation feedback
- **Success state**: Clear success message, auto-redirect to dashboard

### Error Display
- **Inline errors**: Show below input fields
- **Toast notifications**: For general errors
- **Color coding**: Red for errors, green for success

## Migration Strategy

### From Current (Redirect-Based) to New (API-Based)

1. **Deploy backend endpoints first** (IAM Agent)
2. **Test endpoints independently** (using curl/Postman)
3. **Deploy frontend components** (behind feature flag)
4. **Test in staging** (full flow)
5. **Gradual rollout** (A/B test or feature flag)
6. **Monitor errors** (watch for issues)
7. **Full migration** (remove old redirect code)

## Future Enhancements

1. **Social Login**: Google, Microsoft, etc. (still via Keycloak)
2. **MFA/2FA**: TOTP, SMS, Email codes
3. **Password Reset**: Forgot password flow
4. **Email Verification**: Verify email before account activation
5. **SSO Integration**: For enterprise customers
6. **Session Management**: View/revoke active sessions

## Dependencies

### Backend
- ✅ `python-keycloak` (already installed)
- ✅ `httpx` (already installed)
- ✅ Keycloak admin access

### Frontend
- ✅ `axios` or `fetch` (for API calls)
- ✅ React hooks (for state management)
- ✅ Form validation library (optional)

## Testing Checklist

- [ ] Login with valid credentials
- [ ] Login with invalid credentials
- [ ] Login with disabled account
- [ ] Signup with new email
- [ ] Signup with existing email
- [ ] Signup with weak password
- [ ] Token refresh
- [ ] Logout
- [ ] Session persistence (refresh page)
- [ ] Token expiration handling
- [ ] Network error handling
- [ ] Rate limiting
- [ ] Mobile responsiveness

## Success Criteria

1. ✅ Users can log in via custom dialog (no Keycloak redirect)
2. ✅ Users can sign up and create account in Keycloak
3. ✅ Tokens are stored and used for API calls
4. ✅ UI matches SentinelGrid design
5. ✅ Error handling is user-friendly
6. ✅ Security best practices are followed
7. ✅ All tests pass

## Timeline Estimate

- **Phase 1 (Backend)**: 2-3 days
- **Phase 2 (Frontend)**: 2-3 days
- **Phase 3 (Security)**: 1-2 days
- **Phase 4 (Testing)**: 1-2 days
- **Total**: ~1-2 weeks

## Open Questions

1. **Realm Strategy**: Single realm vs multi-realm? (Recommendation: Single realm for MVP)
2. **Token Storage**: localStorage vs httpOnly cookies? (Recommendation: localStorage for dev, cookies for prod)
3. **Password Requirements**: What strength requirements? (Recommendation: Min 8 chars, complexity)
4. **Email Verification**: Required or optional? (Recommendation: Optional for MVP)
5. **Welcome Email**: Send on signup? (Recommendation: Yes, but can be async)

