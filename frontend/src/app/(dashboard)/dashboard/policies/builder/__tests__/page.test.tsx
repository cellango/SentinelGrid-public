import { fireEvent, screen, waitFor } from '@testing-library/react';

import PolicyBuilderPage from '@/app/(dashboard)/dashboard/policies/builder/page';
import { renderWithProviders } from '@/test-utils/renderWithProviders';
import { policiesApi } from '@/lib/api/policies';
import { rolesApi } from '@/lib/api/roles';
import { listPolicyBundles } from '@/lib/api/iam-portal';

const { mockSearchParams, resetNavigationMocks } = require('@/test-utils/navigation');

const canvasPropsRef: { current: any } = { current: null };

jest.mock('next/dynamic', () => () => {
  return function MockDynamicComponent(props: any) {
    canvasPropsRef.current = props;
    return (
      <div data-testid="policy-builder-canvas">
        <div data-testid="policy-builder-canvas-readonly">{String(props.readonly)}</div>
        <div data-testid="policy-builder-canvas-roles">{props.roles?.length ?? 0}</div>
        <button type="button" onClick={() => props.onSave?.([], [])}>
          Save From Canvas
        </button>
      </div>
    );
  };
});

jest.mock('next/navigation', () => {
  const { getMockSearchParams } = require('@/test-utils/navigation');
  return {
    useSearchParams() {
      return getMockSearchParams();
    },
  };
});

jest.mock('@/lib/api/policies', () => ({
  policiesApi: {
    listTemplates: jest.fn(),
    get: jest.fn(),
    update: jest.fn(),
    create: jest.fn(),
    evaluate: jest.fn(),
  },
}));

jest.mock('@/lib/api/roles', () => ({
  rolesApi: {
    list: jest.fn(),
  },
}));

jest.mock('@/lib/api/iam-portal', () => ({
  listPolicyBundles: jest.fn(),
}));

jest.mock('react-hot-toast', () => ({
  toast: {
    success: jest.fn(),
    error: jest.fn(),
  },
}));

jest.mock('@/lib/policy/graph-to-json', () => ({
  graphToKeycloakJSON: jest.fn(() => ({
    id: 'generated-policy',
    type: 'access',
    scope: 'tenant',
    rules: [],
  })),
}));

jest.mock('@/lib/policy/json-to-graph', () => ({
  parseKeycloakPolicyJSON: jest.fn(() => ({ parsed: true })),
  keycloakJSONToGraph: jest.fn(() => ({ nodes: [{ id: 'node-1' }], edges: [] })),
}));

const mockedPoliciesApi = policiesApi as jest.Mocked<typeof policiesApi>;
const mockedRolesApi = rolesApi as jest.Mocked<typeof rolesApi>;
const mockedListPolicyBundles = listPolicyBundles as jest.MockedFunction<typeof listPolicyBundles>;

describe('PolicyBuilderPage', () => {
  beforeEach(() => {
    resetNavigationMocks();
    mockSearchParams({});
    canvasPropsRef.current = null;

    mockedRolesApi.list.mockReset();
    mockedPoliciesApi.listTemplates.mockReset();
    mockedPoliciesApi.get.mockReset();
    mockedPoliciesApi.update.mockReset();
    mockedPoliciesApi.create.mockReset();
    mockedPoliciesApi.evaluate.mockReset();
    mockedListPolicyBundles.mockReset();

    mockedRolesApi.list.mockResolvedValue([
      { id: 'role-1', name: 'SOC_MANAGER' },
      { id: 'role-2', name: 'SOC_ANALYST' },
    ] as any);
    mockedPoliciesApi.listTemplates.mockResolvedValue([]);
    mockedPoliciesApi.create.mockResolvedValue({ id: 'policy-1' } as any);
    mockedPoliciesApi.update.mockResolvedValue({ id: 'policy-1' } as any);
    mockedPoliciesApi.evaluate.mockResolvedValue({ result: 'allow', matched_rules: [] } as any);
    mockedListPolicyBundles.mockResolvedValue([]);
  });

  it('loads live tenant roles into the builder and uses tenant-policy copy', async () => {
    renderWithProviders(<PolicyBuilderPage />);

    expect(await screen.findByTestId('policy-builder-canvas')).toBeInTheDocument();
    await waitFor(() => {
      expect(mockedRolesApi.list).toHaveBeenCalled();
      expect(screen.getByTestId('policy-builder-canvas-roles')).toHaveTextContent('2');
    });

    expect(
      screen.getByText(/Compose tenant policy graphs for authorization, access, sign-on, and approval workflows/i)
    ).toBeInTheDocument();
    expect(screen.queryByText(/Keycloak authorization policies/i)).not.toBeInTheDocument();
  });

  it('locks metadata inputs and passes readonly mode through to the canvas for previews', async () => {
    mockSearchParams({ read_only: '1' });

    renderWithProviders(<PolicyBuilderPage />);

    expect(await screen.findByTestId('policy-builder-canvas-readonly')).toHaveTextContent('true');
    expect(screen.getByPlaceholderText('Policy name')).toBeDisabled();
    expect(screen.getByPlaceholderText('Display name')).toBeDisabled();
    expect(screen.getByRole('button', { name: /Clone Template/i })).toBeDisabled();
  });

  it('saves new tenant policies through the live create path', async () => {
    renderWithProviders(<PolicyBuilderPage />);

    fireEvent.change(await screen.findByPlaceholderText('Policy name'), {
      target: { value: 'approval-policy' },
    });
    fireEvent.change(screen.getByPlaceholderText('Display name'), {
      target: { value: 'Approval Policy' },
    });
    fireEvent.click(screen.getByRole('button', { name: /Save From Canvas/i }));

    await waitFor(() => {
      expect(mockedPoliciesApi.create).toHaveBeenCalledWith({
        name: 'approval-policy',
        display_name: 'Approval Policy',
        description: '',
        policy_type: 'access',
        scope: 'tenant',
        policy_data: {
          id: 'generated-policy',
          type: 'access',
          scope: 'tenant',
          rules: [],
        },
        is_active: true,
        priority: 100,
      });
    });
    expect(mockedPoliciesApi.update).not.toHaveBeenCalled();
  });
});
