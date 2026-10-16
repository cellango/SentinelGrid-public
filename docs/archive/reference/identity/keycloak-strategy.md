# Keycloak Strategy - Handling Third-Party Dependencies

> **Historical reference — superseded for release decisions.** This records an earlier design, operation, or validation attempt. It is not the current architecture, a supported quick start, or evidence that the source preview is production ready. Start with the repository README and current documentation index.


**Date:** 2025-11-28  
**Status:** Strategic Planning

---

## Current Issue

Keycloak v25.0 user attribute persistence failure via `kcadm.sh` and Admin REST API.

---

## Is This a Known Issue?

**Research Findings:**

### ✅ Related Known Issues in Keycloak v25.0

1. **Issue #28220 (Keycloak 25.0.0):** Updating user attributes via Admin API can clear `firstname`, `lastname`, and `email` fields. This is documented in the Keycloak 25.0.0 release notes.

2. **Session Persistence Issues:** Multiple reports of session persistence challenges in v25.0, especially during upgrades.

3. **Attribute Handling:** Related attribute persistence problems have been reported in the community.

### 🔍 Our Issue

**Not exactly the same as #28220**, but **likely related**:
- Issue #28220: Clears specific fields during update
- Our Issue: Attributes don't persist at all (returns empty `{ }`)

**Likely Causes:**
1. **Regression Bug** - Related to issue #28220, attribute handling bug in v25.0
2. **API Change** - Breaking change in how attributes are handled
3. **Dev Mode Behavior** - Possible dev mode specific issue
4. **Database/Transaction Issue** - Attributes not being committed to DB

### ✅ Resolution Path

**Keycloak 26.0.6+** includes fixes for v25.0 issues. Recommended to:
1. Test v26.0.x to verify if issue is fixed
2. Upgrade when ready (after thorough testing)

---

## Strategic Options for Handling Third-Party Issues

### Option 1: Fork and Maintain Custom Build ⭐ **NOT RECOMMENDED**

**Pros:**
- ✅ Full control over fixes
- ✅ Can patch immediately
- ✅ No waiting for upstream

**Cons:**
- ❌ **Massive maintenance burden** - Must merge upstream changes
- ❌ **Security risk** - Responsible for security patches
- ❌ **Team expertise** - Requires deep Keycloak knowledge
- ❌ **Testing burden** - Must test all changes
- ❌ **Divergence** - Codebase diverges from upstream
- ❌ **Upgrade complexity** - Harder to upgrade later

**Verdict:** ❌ **Not recommended** - Only consider if:
- Issue is critical and blocks production
- Upstream is unresponsive for months
- You have dedicated Keycloak expertise
- You're willing to maintain long-term fork

---

### Option 2: Upgrade to Keycloak v26.0.6+ ⭐ **RECOMMENDED**

**Pros:**
- ✅ **Fixes known v25.0 issues** - Issue #28220 and related fixes
- ✅ **Latest security patches** - Most secure option
- ✅ **Forward path** - No downgrade needed
- ✅ **Community support** - Latest version gets most support

**Cons:**
- ⚠️ **Testing required** - Must test thoroughly before production
- ⚠️ **Potential new issues** - Newer version may have new bugs
- ⚠️ **Migration effort** - Need to test all functionality

**Research Findings:**
- Keycloak 26.0.6+ includes fixes for v25.0 attribute handling issues
- Recommended by Keycloak community for production
- Migration guides available

**Verdict:** ✅✅ **Best long-term solution** - Upgrade after testing

### Option 2b: Downgrade to Keycloak v24.x

**Pros:**
- ✅ Known stable version
- ✅ Community-tested
- ✅ Likely no attribute persistence issue
- ✅ Quick to implement

**Cons:**
- ❌ **Missing v25.0+ features** - Security improvements, performance
- ❌ **Technical debt** - Will need to upgrade eventually
- ❌ **Security concerns** - Older version may have vulnerabilities
- ❌ **Migration path** - Will need to migrate to v26.x later anyway

**Verdict:** ⚠️ **Short-term option** - Only if upgrade not feasible

---

### Option 3: Implement Workaround + File Upstream Issue ⭐ **RECOMMENDED**

**Pros:**
- ✅ **Unblocks development** - Continue building features
- ✅ **Contributes to community** - Helps fix upstream
- ✅ **Maintainable** - No fork maintenance
- ✅ **Future-proof** - Can remove workaround when fixed
- ✅ **Production-ready** - Workaround can be production-grade

**Cons:**
- ⚠️ Temporary complexity (until upstream fix)
- ⚠️ Need to track upstream issue status

**Implementation:**
1. Implement database lookup workaround
2. File detailed GitHub issue with reproduction steps
3. Monitor upstream issue status
4. Remove workaround when upstream fixes

**Verdict:** ✅✅✅ **Best long-term approach**

---

### Option 4: Use Alternative Identity Provider

**Pros:**
- ✅ Avoid Keycloak issues entirely
- ✅ Might be better fit

**Cons:**
- ❌ **Massive migration effort** - Rewrite authentication
- ❌ **Unknown issues** - New provider may have different issues
- ❌ **Loss of investment** - Time spent on Keycloak wasted

**Verdict:** ❌ **Not recommended** - Too much sunk cost

---

### Option 5: Hybrid: Workaround + Test v24.x + Monitor Upstream

**Implementation:**
1. ✅ **Implement database workaround** (immediate, unblocks dev)
2. ✅ **Test Keycloak v24.x** (verify if issue exists)
3. ✅ **File upstream issue** (contribute to fix)
4. ✅ **Monitor upstream** (upgrade when fixed)
5. ✅ **Document decision** (for team reference)

**Verdict:** ✅✅ **Most pragmatic approach**

---

## Recommended Strategy

### Phase 1: Immediate (This Week)
1. ✅ **Implement database workaround** - Unblock development
2. ✅ **Create comprehensive GitHub issue** - Include:
   - Detailed reproduction steps
   - Test script we created
   - Environment details
   - Expected vs actual behavior
3. ✅ **Test Keycloak v24.x** - Verify if issue exists

### Phase 2: Short-term (Next 2 Weeks)
1. ✅ **Monitor upstream issue** - Track progress
2. ✅ **Engage with Keycloak community** - Ask questions
3. ✅ **Evaluate v24.x** - Test if it meets our needs
4. ✅ **Productionize workaround** - Add caching, monitoring

### Phase 3: Decision Point (After 2-4 Weeks)
Based on upstream response:
- **If fixed upstream** → Upgrade and remove workaround
- **If fix in progress** → Continue with workaround, plan upgrade
- **If no response** → Consider v24.x or alternative approach
- **If critical for production** → Consider fork (last resort)

---

## Best Practices for Third-Party Dependencies

### 1. Dependency Selection Criteria
- ✅ **Active maintenance** - Regular releases
- ✅ **Community support** - Active community
- ✅ **Issue responsiveness** - Maintainers respond to issues
- ✅ **Stability** - Mature, widely used
- ✅ **Extensibility** - Can work around issues

### 2. Risk Mitigation
- ✅ **Abstraction layers** - Don't couple directly to third-party
- ✅ **Workarounds ready** - Always have backup plan
- ✅ **Version pinning** - Lock versions in production
- ✅ **Gradual upgrades** - Test in dev/staging first
- ✅ **Issue tracking** - Monitor upstream issues

### 3. When to Fork
**Only consider forking if:**
- ✅ Issue is **critical** and **blocks production**
- ✅ Upstream is **unresponsive** for months
- ✅ You have **dedicated expertise** to maintain
- ✅ Fork will be **temporary** (merge upstream when fixed)
- ✅ **Budget/resources** available for maintenance

---

## Keycloak-Specific Recommendations

### Why Keycloak is a Good Choice
- ✅ **Industry standard** - Widely adopted
- ✅ **Active development** - Regular releases
- ✅ **Red Hat backing** - Enterprise support available
- ✅ **Extensible** - Many integration options
- ✅ **Feature-rich** - Comprehensive IAM solution

### Our Approach
1. ✅ **Use abstraction** - IAM Agent layer isolates us from Keycloak specifics
2. ✅ **Implement workarounds** - Database lookup as fallback
3. ✅ **Contribute upstream** - File detailed issues
4. ✅ **Monitor releases** - Stay informed about fixes
5. ✅ **Test thoroughly** - Always test in dev first

---

## Action Plan

### Immediate Actions
1. ✅ **Implement database workaround** (unblocks development)
2. ✅ **File Keycloak GitHub issue** with:
   - Our test script
   - Detailed reproduction steps
   - Environment configuration
3. ✅ **Test Keycloak v24.x** to verify if issue exists there

### Short-term Actions
1. ✅ **Monitor upstream issue** - Set up notifications
2. ✅ **Engage community** - Ask in Keycloak forums/Discord
3. ✅ **Productionize workaround** - Add caching, monitoring
4. ✅ **Document lessons learned** - Update our practices

### Long-term Strategy
1. ✅ **Establish abstraction** - IAM Agent already provides this
2. ✅ **Build test suite** - Catch issues early
3. ✅ **Plan upgrades** - Regular upgrade schedule
4. ✅ **Consider support** - Red Hat support if critical

---

## Decision Matrix

| Option | Time to Implement | Maintenance Burden | Risk | Recommendation |
|--------|-------------------|-------------------|------|----------------|
| Fork Keycloak | High (days/weeks) | Very High | High | ❌ Last resort |
| Downgrade to v24.x | Medium (hours) | Low | Medium | ✅ Short-term option |
| Workaround + Upstream | Low (hours) | Low | Low | ✅✅ **Recommended** |
| Alternative Provider | Very High (weeks) | Medium | High | ❌ Not recommended |

---

## Conclusion

**Best Approach:** Implement database workaround + file upstream issue + test v24.x

**Why:**
- ✅ Unblocks development immediately
- ✅ Low maintenance burden
- ✅ Contributes to community
- ✅ Maintains upgrade path
- ✅ No fork complexity

**Next Steps:**
1. Implement database workaround (today)
2. File detailed GitHub issue (this week)
3. Test v24.x compatibility (this week)
4. Monitor upstream (ongoing)

---

**Related Documents:**
- `WORKAROUND_TENANT_ID.md` - Database workaround design
- `TENANT_ID_FIX_IN_PROGRESS.md` - Investigation notes
- `test_keycloak_attribute_persistence.py` - Reproduction test

