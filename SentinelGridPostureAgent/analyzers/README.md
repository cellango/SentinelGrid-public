# Analyzers

> **Experimental component reference.** This monorepo publishes source for developer review. Commands and capability descriptions below are not a supported runtime or current release certification. Read [the root preview scope](../../RELEASE_SCOPE.md) first.


Observable-driven security analyzers for the posture platform.

## Architecture

The analyzer framework follows the **Observable-Analyzer Pattern** (similar to TheHive's Cortex):

1. **Observables**: Entities that can be analyzed (assets, repos, images, services)
2. **Analyzers**: Security tools that operate on specific observable types
3. **Dynamic Selection**: System automatically selects applicable analyzers based on observable type
4. **Parallel Execution**: Multiple analyzers run concurrently on the same observable

## Creating a New Analyzer

### 1. Create Analyzer Class

```python
from analyzers.base_analyzer import BaseAnalyzer
from analyzers.registry import registry

class MyToolAnalyzer(BaseAnalyzer):
    # Metadata
    name = "my-tool-scanner"
    description = "Scans for vulnerabilities using MyTool"
    version = "1.0.0"
    supported_observable_types = ["web_application", "api_endpoint"]
    tags = ["dast", "webapp", "critical"]
    
    # Optional: Execution constraints
    timeout_seconds = 300
    requires_credentials = True
    parallel_safe = True
    
    async def analyze(self, observable, config=None):
        """Run analysis."""
        url = observable["value"]
        
        # Run your tool
        results = await run_my_tool(url)
        
        # Parse findings
        findings = []
        for issue in results:
            findings.append({
                "source": "dast",
                "tool": "mytool",
                "title": issue["title"],
                "description": issue["description"],
                "severity": issue["severity"],
                "evidence": issue,
                "remediation": issue.get("fix")
            })
        
        return {
            "status": "success",
            "findings": findings,
            "metadata": {
                "duration": results["duration"],
                "urls_tested": len(results["urls"])
            }
        }
    
    def should_run(self, observable):
        """Custom logic for when to run."""
        # Only run if observable has certain metadata
        metadata = observable.get("metadata", {})
        return metadata.get("has_web_server", False)

# Register analyzer
registry.register(MyToolAnalyzer)
```

### 2. Observable Type Guidelines

| Type | Description | Example Value |
|------|-------------|---------------|
| `web_application` | Web application | `https://app.example.com` |
| `api_endpoint` | API endpoint | `https://api.example.com/v1` |
| `aws_s3_bucket` | AWS S3 bucket | `arn:aws:s3:::my-bucket` |
| `aws_account` | AWS account | `123456789012` |
| `docker_image` | Container image | `myregistry/app:v1.2.3` |
| `git_repository` | Git repository | `https://github.com/org/repo` |
| `k8s_cluster` | Kubernetes cluster | `arn:aws:eks:us-east-1:123456789012:cluster/my-cluster` |

### 3. Finding Format

All findings must follow this format:

```python
{
    "source": "cspm" | "iac" | "dast" | "sast" | "sca" | "secret_scan" | "image_scan" | "runtime",
    "tool": "prowler" | "zap" | "trivy" | "checkov" | "gitleaks" | etc.,
    "title": "Short finding title",
    "description": "Detailed description of the issue",
    "severity": "critical" | "high" | "medium" | "low" | "info",
    "evidence": {...},  # Tool-specific evidence (JSON)
    "remediation": "How to fix this issue",
    "check_id": "TOOL-SPECIFIC-CHECK-ID",  # Optional
    "framework_refs": {  # Optional
        "cis": ["1.1", "1.2"],
        "nist": ["AC-2", "SC-7"],
        "soc2": ["CC6.1"]
    }
}
```

### 4. Tags

Use tags to categorize analyzers:

- **By Category**: `cspm`, `iac`, `dast`, `sast`, `sca`, `secret_scan`
- **By Provider**: `aws`, `azure`, `gcp`, `kubernetes`
- **By Priority**: `critical`, `high-priority`, `low-priority`
- **By Speed**: `fast`, `slow`
- **By Cost**: `expensive`, `free`

### 5. Smart Execution

Implement `should_run()` for intelligent analyzer selection:

```python
def should_run(self, observable):
    """Only run if repo contains IaC files."""
    if observable["type"] != "git_repository":
        return False
    
    metadata = observable.get("metadata", {})
    return (
        metadata.get("has_terraform") or
        metadata.get("has_cloudformation") or
        metadata.get("has_kubernetes_manifests")
    )
```

## Existing Analyzers

### Cloud (CSPM)
- **prowler-aws-cspm**: AWS security posture scanning
- **prowler-azure-cspm**: Azure security posture scanning
- **prowler-gcp-cspm**: GCP security posture scanning

### IaC
- **checkov-iac**: Terraform, CloudFormation, K8s manifest scanning

### Secrets
- **gitleaks-secrets**: Git repository secret scanning

### Containers
- **trivy-vuln-scan**: Container image vulnerability scanning
- **grype-vuln-scan**: Alternative container scanning

### Web Applications
- **zap-dast**: OWASP ZAP dynamic scanning
- **nuclei-vuln**: Nuclei vulnerability scanning

## Testing Analyzers

```python
import asyncio
from analyzers.cloud.prowler_analyzer import ProwlerAnalyzer

async def test_analyzer():
    analyzer = ProwlerAnalyzer()
    
    observable = {
        "type": "aws_account",
        "value": "123456789012",
        "metadata": {"environment": "prod"}
    }
    
    result = await analyzer.analyze(observable)
    print(f"Status: {result['status']}")
    print(f"Findings: {len(result['findings'])}")

asyncio.run(test_analyzer())
```

## Registry Usage

```python
from analyzers.registry import registry

# List all analyzers
print(registry.list_analyzers())

# Get analyzers for a specific observable type
analyzers = registry.get_analyzers_for_observable("web_application")

# Filter by tags
critical_analyzers = registry.get_analyzers_for_observable(
    "web_application",
    tags=["critical"]
)

# Get statistics
print(registry.get_stats())
```

## Best Practices

1. **Timeout**: Set appropriate `timeout_seconds` based on tool performance
2. **Error Handling**: Catch tool errors and return `status: "failure"` with error message
3. **Credentials**: Use environment variables for sensitive data
4. **Parallel Safety**: Set `parallel_safe = False` if tool has concurrency issues
5. **Evidence**: Include enough evidence for humans to verify findings
6. **Remediation**: Provide actionable remediation steps

