'use client'

import { Cloud, Globe, FolderGit, Box } from 'lucide-react'
import type { Asset } from '@/lib/api-client'

interface AssetInventoryProps {
  assets: Asset[];
}

export function AssetInventory({ assets }: AssetInventoryProps) {
  const getAssetIcon = (type: string) => {
    switch (type.toLowerCase()) {
      case 'aws_account':
      case 'azure_subscription':
      case 'gcp_project':
        return Cloud;
      case 'web_application':
        return Globe;
      case 'git_repository':
        return FolderGit;
      case 'docker_image':
        return Box;
      default:
        return Box;
    }
  };

  const getAssetTypeLabel = (type: string) => {
    return type.split('_').map(word => 
      word.charAt(0).toUpperCase() + word.slice(1)
    ).join(' ');
  };

  // Group assets by type
  const groupedAssets = assets.reduce((acc, asset) => {
    if (!acc[asset.type]) {
      acc[asset.type] = [];
    }
    acc[asset.type].push(asset);
    return acc;
  }, {} as Record<string, Asset[]>);

  return (
    <div className="space-y-4">
      {Object.entries(groupedAssets).map(([type, assetList]) => {
        const Icon = getAssetIcon(type);
        
        return (
          <div key={type} className="border rounded-lg overflow-hidden">
            <div className="bg-muted p-4 flex items-center gap-2">
              <Icon className="h-5 w-5 text-primary" />
              <h3 className="font-semibold">{getAssetTypeLabel(type)}</h3>
              <span className="ml-auto text-sm text-muted-foreground">
                {assetList.length} {assetList.length === 1 ? 'asset' : 'assets'}
              </span>
            </div>

            <div className="divide-y">
              {assetList.map((asset) => (
                <div key={asset.id} className="p-4 hover:bg-muted/50 transition-colors">
                  <div className="flex items-center justify-between">
                    <div>
                      <div className="font-medium font-mono text-sm">
                        {asset.identifier}
                      </div>
                      {asset.metadata && (
                        <div className="text-xs text-muted-foreground mt-1">
                          {Object.entries(asset.metadata).slice(0, 2).map(([key, value]) => (
                            <span key={key} className="mr-3">
                              {key}: {String(value)}
                            </span>
                          ))}
                        </div>
                      )}
                    </div>

                    {asset.risk_score !== undefined && (
                      <div className="text-right">
                        <div className={`text-lg font-bold ${
                          asset.risk_score >= 70 ? 'text-red-600' :
                          asset.risk_score >= 40 ? 'text-yellow-600' :
                          'text-green-600'
                        }`}>
                          {asset.risk_score}
                        </div>
                        <div className="text-xs text-muted-foreground">
                          Risk Score
                        </div>
                      </div>
                    )}
                  </div>
                </div>
              ))}
            </div>
          </div>
        );
      })}

      {assets.length === 0 && (
        <div className="border rounded-lg p-12 text-center text-muted-foreground">
          <Box className="h-12 w-12 mx-auto mb-4 opacity-50" />
          <p>No assets discovered yet</p>
          <p className="text-sm mt-2">Run a scan to discover your infrastructure</p>
        </div>
      )}
    </div>
  );
}

