# SentinelGrid AWS Integration - Terraform Module Specification

> **Historical reference — superseded for release decisions.** This records an earlier design, operation, or validation attempt. It is not the current architecture, a supported quick start, or evidence that the source preview is production ready. Start with the repository README and current documentation index.


**Purpose:** Provide customers with a ready-to-use Terraform module to set up AWS integration for SentinelGrid.

---

## Module Overview

**Repository:** `terraform-aws-sentinelgrid-integration`  
**Provider:** AWS  
**Minimum Terraform Version:** 1.0+

---

## Inputs (Variables)

### Required Variables

| Variable | Type | Description |
|----------|------|-------------|
| `sentinelgrid_external_id` | `string` | Unique external ID for cross-account role trust (provided by SentinelGrid) |
| `sentinelgrid_aws_account_id` | `string` | SentinelGrid's AWS account ID (hardcoded in docs) |

### Optional Variables

| Variable | Type | Default | Description |
|----------|------|---------|-------------|
| `enable_cloudtrail` | `bool` | `false` | Create/configure CloudTrail trail |
| `enable_guardduty` | `bool` | `true` | Enable GuardDuty in the account |
| `enable_config` | `bool` | `false` | Enable AWS Config |
| `enable_security_hub` | `bool` | `false` | Enable Security Hub |
| `cloudtrail_s3_bucket_name` | `string` | `null` | Existing S3 bucket for CloudTrail (creates new if not provided) |
| `cloudtrail_s3_bucket_prefix` | `string` | `"cloudtrail-logs"` | S3 prefix for CloudTrail logs |
| `tags` | `map(string)` | `{}` | Additional tags for resources |

---

## Resources Created

### 1. IAM Role: `SentinelGridMonitorRole`

**Trust Policy:**
- Trusts SentinelGrid AWS account
- Requires `sts:ExternalId` matching provided external ID
- Allows `sts:AssumeRole` action

**Permissions Policy:**
- **CloudTrail:**
  - `cloudtrail:DescribeTrails`
  - `cloudtrail:GetTrailStatus`
  - `cloudtrail:GetEventSelectors`
  - `cloudtrail:LookupEvents`
  - `cloudtrail:GetTrail`
  - `cloudtrail:ListTrails`

- **S3 (CloudTrail buckets):**
  - `s3:GetObject`
  - `s3:ListBucket`
  - (Limited to CloudTrail log buckets only)

- **GuardDuty:**
  - `guardduty:GetFindings`
  - `guardduty:ListDetectors`
  - `guardduty:ListFindings`
  - `guardduty:GetDetector`
  - `guardduty:DescribeOrganizationConfiguration`

- **AWS Config:**
  - `config:Describe*`
  - `config:Get*`
  - `config:List*`
  - `config:SelectResourceConfig`

- **Security Hub:**
  - `securityhub:GetFindings`
  - `securityhub:GetEnabledStandards`
  - `securityhub:DescribeHub`
  - `securityhub:ListFindings`
  - `securityhub:BatchGetFindings`

- **IAM (read-only for context):**
  - `iam:GetRole`
  - `iam:ListRoles`
  - `iam:GetUser`
  - `iam:ListUsers`
  - `iam:ListAccountAliases`

**Note:** All permissions are read-only. No write/delete/modify permissions.

### 2. CloudTrail (Optional)

**If `enable_cloudtrail = true`:**

- Creates S3 bucket for CloudTrail logs (if not provided)
- Creates multi-region CloudTrail trail
- Enables log file validation
- Configures S3 bucket policy for CloudTrail
- Optionally sends to CloudWatch Logs

### 3. GuardDuty (Optional)

**If `enable_guardduty = true`:**

- Enables GuardDuty detector in the account
- Configures finding publishing (optional)
- Sets up S3 protection (optional)

### 4. AWS Config (Optional)

**If `enable_config = true`:**

- Enables AWS Config
- Creates delivery channel (S3)
- Sets up configuration recorder

### 5. Security Hub (Optional)

**If `enable_security_hub = true`:**

- Enables Security Hub
- Enables CIS AWS Foundations Benchmark
- Enables other security standards (optional)

---

## Outputs

| Output | Description |
|--------|-------------|
| `sentinelgrid_monitor_role_arn` | **REQUIRED** - IAM Role ARN to paste into SentinelGrid UI |
| `cloudtrail_trail_arn` | CloudTrail trail ARN (if enabled) |
| `cloudtrail_s3_bucket_arn` | CloudTrail S3 bucket ARN (if created) |
| `guardduty_detector_id` | GuardDuty detector ID (if enabled) |
| `config_recorder_name` | AWS Config recorder name (if enabled) |
| `security_hub_arn` | Security Hub ARN (if enabled) |

---

## Usage Example

### Basic (IAM Role Only)

```hcl
module "sentinelgrid_integration" {
  source = "github.com/sentinelgrid/terraform-aws-sentinelgrid-integration"

  sentinelgrid_external_id      = "550e8400-e29b-41d4-a716-446655440000"
  sentinelgrid_aws_account_id   = "987654321098"
}
```

### Full Setup (All Services)

```hcl
module "sentinelgrid_integration" {
  source = "github.com/sentinelgrid/terraform-aws-sentinelgrid-integration"

  sentinelgrid_external_id      = "550e8400-e29b-41d4-a716-446655440000"
  sentinelgrid_aws_account_id   = "987654321098"
  
  enable_cloudtrail    = true
  enable_guardduty     = true
  enable_config        = true
  enable_security_hub  = true
  
  tags = {
    Environment = "production"
    ManagedBy   = "sentinelgrid"
  }
}
```

---

## Module Structure

```
terraform-aws-sentinelgrid-integration/
├── README.md                    # Full documentation
├── LICENSE                      # Apache 2.0 or MIT
├── main.tf                      # IAM role and policies
├── cloudtrail.tf                # CloudTrail resources (optional)
├── guardduty.tf                 # GuardDuty resources (optional)
├── config.tf                    # AWS Config resources (optional)
├── security_hub.tf              # Security Hub resources (optional)
├── variables.tf                 # Input variables
├── outputs.tf                   # Output values
├── versions.tf                  # Provider version constraints
└── examples/
    ├── basic/
    │   └── main.tf              # Minimal example
    ├── full/
    │   └── main.tf              # All services enabled
    └── existing-cloudtrail/
        └── main.tf              # Use existing CloudTrail bucket
```

---

## Security Best Practices

1. **External ID:** Always required for cross-account role assumption
2. **Least Privilege:** Role has only read-only permissions
3. **Resource Scoping:** S3 permissions limited to CloudTrail buckets
4. **Encryption:** CloudTrail logs encrypted at rest
5. **MFA:** Consider requiring MFA for role assumption (future enhancement)

---

## Testing

### Manual Testing Checklist

- [ ] Module applies successfully
- [ ] IAM role created with correct trust policy
- [ ] External ID validation works
- [ ] SentinelGrid can assume role from our account
- [ ] CloudTrail logs are accessible (if enabled)
- [ ] GuardDuty findings are accessible (if enabled)
- [ ] All outputs are correct

### Automated Testing

- Terraform validation: `terraform validate`
- Security scanning: `tfsec` or `checkov`
- Policy validation: `terraform-compliance`

---

## Documentation Requirements

1. **README.md** with:
   - Quick start guide
   - All variables documented
   - All outputs documented
   - Usage examples
   - Security considerations
   - Troubleshooting

2. **Examples/** directory with:
   - Basic setup
   - Full setup
   - Edge cases (existing resources)

3. **CHANGELOG.md** for version tracking

---

## Versioning

Use semantic versioning:
- `v1.0.0` - Initial release
- `v1.1.0` - Add CloudTrail support
- `v1.2.0` - Add GuardDuty support
- etc.

Tag releases in GitHub for Terraform Registry compatibility.

---

## Next Steps

1. Create Terraform module repository
2. Implement IAM role and policies
3. Add CloudTrail support
4. Add GuardDuty support
5. Write comprehensive documentation
6. Create examples
7. Test with real AWS accounts
8. Publish to Terraform Registry (optional)

