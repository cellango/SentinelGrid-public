# Third-Party Dependency Strategy

> **Historical reference — superseded for release decisions.** This records an earlier design, operation, or validation attempt. It is not the current architecture, a supported quick start, or evidence that the source preview is production ready. Start with the repository README and current documentation index.


**Purpose:** Guidelines for handling issues with third-party dependencies (like Keycloak)

---

## Core Principles

### 1. Abstraction Over Coupling
**Always** build abstraction layers around third-party dependencies:
- ✅ **IAM Agent** - Abstracts Keycloak details
- ✅ **Service interfaces** - Allow swapping implementations
- ✅ **Configuration layers** - Centralize third-party config

### 2. Workarounds Over Forks
**Prefer** workarounds and contributions over forking:
- ✅ **Unblocks development** - Continue building features
- ✅ **Low maintenance** - No codebase to maintain
- ✅ **Community benefit** - Helps fix upstream
- ✅ **Upgrade path** - Easy to remove when fixed

### 3. Monitor and Plan
**Track** third-party issues and plan accordingly:
- ✅ **Issue tracking** - Monitor upstream issues
- ✅ **Version testing** - Test new versions in dev
- ✅ **Upgrade planning** - Schedule regular upgrades
- ✅ **Rollback plan** - Always have downgrade path

---

## Decision Framework

### When to Use a Workaround
✅ **Use workaround if:**
- Issue doesn't block core functionality
- Workaround is maintainable
- Upstream issue is filed and tracked
- Development can continue

### When to Consider Downgrade
✅ **Consider downgrade if:**
- Issue blocks production deployment
- Previous version is known stable
- No critical features lost in downgrade
- Temporary measure until upstream fix

### When to Consider Fork
⚠️ **Only consider fork if:**
- Issue is **critical** and **production-blocking**
- Upstream is **unresponsive** for 3+ months
- You have **dedicated team** for maintenance
- **Budget/resources** available long-term
- Fork is **temporary** (plan to merge upstream)

### When to Switch Providers
❌ **Avoid switching unless:**
- Provider is **abandoned** or **unsupported**
- Issues are **fundamental** and **ongoing**
- Provider doesn't meet **core requirements**
- Migration cost is **acceptable**

---

## Our Approach: Keycloak Example

### Current Situation
- **Issue:** Attribute persistence in v25.0
- **Impact:** Blocks multi-tenant isolation
- **Status:** Investigating

### Our Strategy

#### Phase 1: Workaround (Immediate)
```
✅ Implement database lookup for tenant_id
✅ Abstract behind IAM Agent
✅ Continue development
```

#### Phase 2: Contribution (Short-term)
```
✅ File detailed GitHub issue
✅ Provide reproduction test
✅ Engage with community
✅ Monitor upstream progress
```

#### Phase 3: Evaluation (Medium-term)
```
✅ Test Keycloak v24.x
✅ Evaluate if downgrade needed
✅ Assess upstream fix timeline
```

#### Phase 4: Resolution (Long-term)
```
✅ Upgrade when upstream fixed
✅ Remove workaround
✅ Document lessons learned
```

---

## Best Practices

### 1. Always Have a Workaround
- Design systems to be resilient
- Build fallback mechanisms
- Never rely on single path

### 2. Abstract Third-Party APIs
- Create service interfaces
- Hide implementation details
- Enable easy swapping

### 3. Test Early, Test Often
- Test new versions in dev
- Catch issues before production
- Have rollback plan ready

### 4. Monitor Upstream
- Track issue status
- Watch for fixes
- Plan upgrades

### 5. Document Decisions
- Record why choices made
- Document workarounds
- Share lessons learned

---

## Keycloak-Specific

### Why Keycloak is Good Choice
- ✅ Industry standard
- ✅ Active development
- ✅ Red Hat backing
- ✅ Large community
- ✅ Extensible

### Our IAM Agent Abstraction
- ✅ Hides Keycloak details
- ✅ Enables workarounds
- ✅ Allows future swapping
- ✅ Centralizes IAM logic

---

## Anti-Patterns to Avoid

❌ **Direct Coupling** - Don't call Keycloak directly from services  
❌ **No Abstraction** - Always build service layer  
❌ **No Workarounds** - Always have backup plan  
❌ **Forking Too Soon** - Exhaust other options first  
❌ **Ignoring Upstream** - Stay engaged with community  

---

## Success Metrics

### Workaround Success
- ✅ Development unblocked
- ✅ Production functionality works
- ✅ Maintenance burden low
- ✅ Easy to remove when fixed

### Upstream Engagement Success
- ✅ Issue filed and acknowledged
- ✅ Community responsive
- ✅ Fix timeline reasonable
- ✅ Contributing to solution

---

## Conclusion

**Strategy:** Workarounds + Abstraction + Upstream Contribution

**Implementation:**
1. ✅ Build abstraction layers (IAM Agent)
2. ✅ Implement workarounds (database lookup)
3. ✅ File detailed upstream issues
4. ✅ Monitor and plan upgrades
5. ✅ Document and learn

**Result:** Resilient system that can handle third-party issues gracefully.

---

**Related:**
- `KEYCLOAK_STRATEGY.md` - Keycloak-specific strategy
- `WORKAROUND_TENANT_ID.md` - Database workaround design

