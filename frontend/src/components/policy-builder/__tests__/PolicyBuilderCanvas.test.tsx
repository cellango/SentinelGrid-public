import { fireEvent, render, screen, waitFor } from '@testing-library/react';

import { PolicyBuilderCanvasWrapper } from '@/components/policy-builder/PolicyBuilderCanvas';

jest.mock('reactflow', () => {
  const React = require('react');

  return {
    __esModule: true,
    default: ({ children }: { children?: React.ReactNode }) => (
      <div data-testid="reactflow-mock">{children}</div>
    ),
    Background: () => null,
    Controls: () => null,
    MiniMap: () => null,
    ReactFlowProvider: ({ children }: { children?: React.ReactNode }) => <>{children}</>,
    addEdge: (edge: unknown, edges: unknown[]) => [...edges, edge],
    useNodesState: (initialNodes: unknown[] = []) => {
      const [nodes, setNodes] = React.useState(initialNodes);
      return [nodes, setNodes, jest.fn()];
    },
    useEdgesState: (initialEdges: unknown[] = []) => {
      const [edges, setEdges] = React.useState(initialEdges);
      return [edges, setEdges, jest.fn()];
    },
  };
});

jest.mock('@/components/policy-builder/NodePalette', () => ({
  NodePalette: ({ readonly }: { readonly?: boolean }) => (
    <div data-testid="node-palette">readonly:{String(readonly)}</div>
  ),
}));

jest.mock('@/components/policy-builder/PropertiesPanel', () => ({
  PropertiesPanel: () => <div data-testid="properties-panel">Properties</div>,
}));

jest.mock('@/components/policy-builder/PolicyTemplates', () => ({
  PolicyTemplates: () => <div data-testid="policy-templates">Templates</div>,
}));

jest.mock('react-hot-toast', () => ({
  toast: {
    success: jest.fn(),
    error: jest.fn(),
  },
}));

jest.mock('@/lib/policy/graph-to-json', () => ({
  graphToKeycloakJSON: jest.fn(() => ({
    name: 'Policy Graph',
    type: 'authorization',
    scope: 'tenant',
    rules: [],
  })),
  exportPolicyAsJSON: jest.fn(() => '{}'),
  validateKeycloakPolicy: jest.fn(() => ({ valid: true, errors: [] })),
}));

jest.mock('@/lib/policy/json-to-graph', () => ({
  keycloakJSONToGraph: jest.fn(() => ({ nodes: [], edges: [] })),
  parseKeycloakPolicyJSON: jest.fn(() => ({})),
}));

describe('PolicyBuilderCanvas', () => {
  it('locks the canvas in readonly preview mode', () => {
    render(
      <PolicyBuilderCanvasWrapper
        readonly
        initialNodes={[]}
        initialEdges={[]}
      />
    );

    expect(screen.getByTestId('node-palette')).toHaveTextContent('readonly:true');
    expect(screen.getByRole('button', { name: /Preview Only/i })).toBeDisabled();
  });

  it('uses the provided save handler for tenant policy saves', async () => {
    const onSave = jest.fn().mockResolvedValue(undefined);

    render(
      <PolicyBuilderCanvasWrapper
        onSave={onSave}
        initialNodes={[]}
        initialEdges={[]}
      />
    );

    fireEvent.click(screen.getByRole('button', { name: /Save Tenant Policy/i }));

    await waitFor(() => {
      expect(onSave).toHaveBeenCalledWith([], []);
    });
  });
});
