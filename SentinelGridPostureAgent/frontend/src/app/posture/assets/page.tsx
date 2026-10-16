'use client'

import { useEffect, useState } from 'react'
import { AssetInventory } from '@/components/posture/AssetInventory'
import { apiClient, type Asset } from '@/lib/api-client'

export default function AssetsPage() {
  const [assets, setAssets] = useState<Asset[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    loadAssets();
  }, []);

  const loadAssets = async () => {
    try {
      setLoading(true);
      const tenantId = 'default-tenant';

      const data = await apiClient.listAssets(tenantId);
      setAssets(data);
    } catch (error) {
      console.error('Error loading assets:', error);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="container mx-auto p-8">
      <div className="mb-8">
        <h1 className="text-4xl font-bold mb-2">Asset Inventory</h1>
        <p className="text-muted-foreground">
          All discovered cloud resources and infrastructure
        </p>
      </div>

      {loading ? (
        <div className="text-center py-12">
          <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-primary mx-auto mb-4"></div>
          <p className="text-muted-foreground">Loading assets...</p>
        </div>
      ) : (
        <>
          <div className="mb-4 text-sm text-muted-foreground">
            Total: {assets.length} assets
          </div>
          <AssetInventory assets={assets} />
        </>
      )}
    </div>
  );
}

