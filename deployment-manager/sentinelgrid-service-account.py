"""Deployment Manager type provider for creating GCP service account."""

def GenerateConfig(context):
    """Generate Deployment Manager configuration for service account."""
    
    service_account_id = context.properties.get('serviceAccountId', 'sentinelgrid-monitor')
    display_name = context.properties.get('displayName', 'SentinelGrid Monitoring')
    description = context.properties.get('description', 'Service account for SentinelGrid monitoring')
    
    resources = [{
        'name': service_account_id,
        'type': 'iam.v1.serviceAccount',
        'properties': {
            'accountId': service_account_id,
            'displayName': display_name,
            'description': description
        }
    }]
    
    return {
        'resources': resources,
        'outputs': [{
            'name': 'email',
            'value': '$(ref.' + service_account_id + '.email)'
        }]
    }

