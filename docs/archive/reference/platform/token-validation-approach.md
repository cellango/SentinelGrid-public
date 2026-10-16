# Token Validation Approach Analysis

> **Historical reference — superseded for release decisions.** This records an earlier design, operation, or validation attempt. It is not the current architecture, a supported quick start, or evidence that the source preview is production ready. Start with the repository README and current documentation index.


## Current Approach: Manual Signature Verification

### What We're Doing
- Manual base64 decoding of token payload and header
- Direct signature verification using `cryptography` library
- Manual expiration checking
- Bypassing PyJWT's `jwt.decode()` to avoid issuer validation issues

### Cons / Trade-offs

#### 1. **Bypassing Library Security Checks**
- **Risk**: PyJWT includes additional security validations beyond signature and expiration (e.g., `nbf` (not before), algorithm validation, token format checks)
- **Impact**: We may miss some security edge cases that PyJWT handles automatically
- **Mitigation**: We manually verify critical claims (exp, signature, issuer pattern)

#### 2. **Maintenance Burden**
- **Risk**: Manual implementation means we maintain our own cryptography code
- **Impact**: More complex code, potential for bugs, requires deep understanding of JWT internals
- **Mitigation**: Code is well-documented, but any future changes need careful review

#### 3. **Future Compatibility**
- **Risk**: If PyJWT fixes issuer validation issues or adds new security features, we won't benefit automatically
- **Impact**: We may need to manually backport security fixes or enhancements
- **Mitigation**: We should periodically review PyJWT updates

#### 4. **Code Complexity**
- **Risk**: More complex code path with manual base64 decoding, signature verification, padding handling
- **Impact**: Harder to maintain, more places for bugs to hide
- **Mitigation**: Code is modular and well-logged

#### 5. **Testing Requirements**
- **Risk**: We need to thoroughly test our manual implementation for edge cases
- **Impact**: More comprehensive test coverage needed
- **Mitigation**: We have integration tests, but should expand unit test coverage

#### 6. **Security Review**
- **Risk**: Custom security code requires expert security review
- **Impact**: Potential for vulnerabilities if implementation has flaws
- **Mitigation**: Code follows standard JWT verification patterns, but should undergo security audit

#### 7. **Issuer URL Mismatch**
- **Root Cause**: Token issuer is `http://localhost:8081/realms/...` but internal Docker network uses `http://keycloak:8080`
- **Why We Work Around It**: PyJWT validates issuer even when `verify_iss=False` in some code paths
- **Better Solution**: Fix at the source - configure Keycloak to issue tokens with correct issuer URL for internal network

### Alternative Approaches to Consider

#### Option 1: Fix Issuer URL at Source (Recommended)
- **Approach**: Configure Keycloak to use correct issuer URL for tokens
- **Pros**: Clean, standard approach; PyJWT can handle it normally
- **Cons**: Requires Keycloak configuration changes
- **Effort**: Medium

#### Option 2: Normalize Issuer Before Validation
- **Approach**: Pre-process token to normalize issuer URL before PyJWT validation
- **Pros**: Use PyJWT normally, simpler code
- **Cons**: Token manipulation could be seen as security risk
- **Effort**: Low

#### Option 3: Fork/Patch PyJWT
- **Approach**: Modify PyJWT to properly respect `verify_iss=False`
- **Pros**: Fixes the root cause in the library
- **Cons**: Maintenance burden of maintaining fork
- **Effort**: High

#### Option 4: Different JWT Library
- **Approach**: Use a different JWT library (e.g., `pyjwt` fork or alternative)
- **Pros**: Might have better issuer validation controls
- **Cons**: New dependency, migration effort
- **Effort**: Medium

#### Option 5: Accept Current Approach (Keep as-is)
- **Approach**: Continue with manual verification
- **Pros**: Works now, gives us full control
- **Cons**: Maintenance burden, complexity
- **Effort**: Low (already done)

### Recommendation

**Short-term (Current)**: Keep the manual verification approach as it works and is secure.

**Medium-term (Q1 2025)**: Investigate Option 1 (Fix Issuer URL at Source):
- Configure Keycloak's `frontendUrl` or use proper hostname configuration
- This would allow us to use PyJWT normally
- Reduces complexity and maintenance burden

**Long-term**: Consider security audit of the manual verification code to ensure no edge cases are missed.

### Security Considerations

Our current implementation:
✅ Verifies signature using correct JWKS
✅ Checks expiration
✅ Validates issuer pattern manually
✅ Extracts realm correctly for multi-tenancy
✅ Uses cryptography library (industry standard)
✅ Properly handles base64url encoding

Potential gaps:
⚠️ Not checking `nbf` (not before) claim
⚠️ Not validating algorithm explicitly (relies on cryptography library)
⚠️ Manual base64 padding handling could have edge cases

### Action Items

1. **Add `nbf` validation** (Not Before claim) - Easy win for security
2. **Expand test coverage** for edge cases (malformed tokens, padding issues, etc.)
3. **Document security assumptions** clearly
4. **Schedule security review** of the manual verification code
5. **Investigate Keycloak issuer URL configuration** for long-term fix

