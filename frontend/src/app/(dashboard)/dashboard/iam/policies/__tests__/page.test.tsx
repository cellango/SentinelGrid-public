import { fireEvent, screen, waitFor } from '@testing-library/react';

import PoliciesPage from '@/app/(dashboard)/dashboard/iam/policies/page';
import { renderWithProviders } from '@/test-utils/renderWithProviders';
import {
  clonePolicyBundle,
  createPolicyFromTemplate,
  deletePolicy,
  getPolicies,
  getPolicyTemplates,
  listPolicyBundles,
  updatePolicy,
} from '@/lib/api/iam-portal';

const { getMockRouter, resetNavigationMocks } = require('@/test-utils/navigation');

jest.mock('next/navigation', () => {
  const { getMockRouter } = require('@/test-utils/navigation');
  return {
    useRouter() {
      return getMockRouter();
    },
  };
});

jest.mock('@/lib/api/iam-portal', () => ({
  getPolicies: jest.fn(),
  getPolicyTemplates: jest.fn(),
  createPolicyFromTemplate: jest.fn(),
  deletePolicy: jest.fn(),
  listPolicyBundles: jest.fn(),
  clonePolicyBundle: jest.fn(),
  updatePolicy: jest.fn(),
}));

const mockedGetPolicies = getPolicies as jest.MockedFunction<typeof getPolicies>;
const mockedGetPolicyTemplates = getPolicyTemplates as jest.MockedFunction<
  typeof getPolicyTemplates
>;
const mockedCreatePolicyFromTemplate = createPolicyFromTemplate as jest.MockedFunction<
  typeof createPolicyFromTemplate
>;
const mockedDeletePolicy = deletePolicy as jest.MockedFunction<typeof deletePolicy>;
const mockedListPolicyBundles = listPolicyBundles as jest.MockedFunction<
  typeof listPolicyBundles
>;
const mockedClonePolicyBundle = clonePolicyBundle as jest.MockedFunction<
  typeof clonePolicyBundle
>;
const mockedUpdatePolicy = updatePolicy as jest.MockedFunction<typeof updatePolicy>;

const signonPolicy = {
  id: 'policy-1',
  tenant_id: 'tenant-1',
  name: 'admin-signon',
  display_name: 'Admin Sign-on Policy',
  description: 'Require MFA for privileged logins',
  policy_type: 'signon',
  scope: 'tenant',
  policy_data: {
    rules: [
      {
        id: 'rule-1',
        name: 'Require MFA',
        conditions: [],
        actions: [{ type: 'require_mfa' }],
      },
    ],
  },
  is_active: true,
  priority: 100,
  created_at: '2026-04-15T12:00:00.000Z',
  updated_at: '2026-04-15T12:00:00.000Z',
};

const authorizationPolicy = {
  id: 'policy-auth-1',
  tenant_id: 'tenant-1',
  name: 'sensitive-data-access',
  display_name: 'Sensitive Data Access',
  description: 'Constrain high-risk access paths',
  policy_type: 'authorization',
  scope: 'tenant',
  policy_data: {
    rules: [],
  },
  is_active: true,
  priority: 50,
  created_at: '2026-04-15T12:00:00.000Z',
  updated_at: '2026-04-15T12:00:00.000Z',
};

const authorizationBundle = {
  ...authorizationPolicy,
  id: 'bundle-auth-1',
  tenant_id: 'sg_admin',
  name: 'starter-authorization-bundle',
  display_name: 'Starter Authorization Bundle',
};

describe('PoliciesPage', () => {
  beforeEach(() => {
    resetNavigationMocks();
    window.history.replaceState({}, '', '/dashboard/iam/policies');

    mockedGetPolicies.mockReset();
    mockedGetPolicyTemplates.mockReset();
    mockedCreatePolicyFromTemplate.mockReset();
    mockedDeletePolicy.mockReset();
    mockedListPolicyBundles.mockReset();
    mockedClonePolicyBundle.mockReset();
    mockedUpdatePolicy.mockReset();

    mockedGetPolicies.mockImplementation(async (policyType) => {
      if (policyType === 'authorization') {
        return [authorizationPolicy as any];
      }
      return [signonPolicy as any];
    });
    mockedGetPolicyTemplates.mockResolvedValue([]);
    mockedCreatePolicyFromTemplate.mockResolvedValue(signonPolicy as any);
    mockedDeletePolicy.mockResolvedValue(undefined);
    mockedListPolicyBundles.mockResolvedValue([authorizationBundle as any]);
    mockedClonePolicyBundle.mockResolvedValue(authorizationBundle as any);
    mockedUpdatePolicy.mockResolvedValue(signonPolicy as any);
  });

  it('shows honest authorization copy instead of a demo label', async () => {
    window.history.replaceState({}, '', '/dashboard/iam/policies?tab=authorization');

    renderWithProviders(<PoliciesPage />);

    expect(await screen.findByRole('heading', { name: /authorization policy builder/i })).toBeInTheDocument();
    expect(screen.getByText('Tenant policies')).toBeInTheDocument();
    expect(screen.getByText(/persisted to your tenant/i)).toBeInTheDocument();
    expect(screen.queryByText(/tenant policies \(demo\)/i)).not.toBeInTheDocument();
  });

  it('saves inline policy edits through the update API', async () => {
    renderWithProviders(<PoliciesPage />);

    fireEvent.click(await screen.findByRole('button', { name: 'Edit' }));
    expect(await screen.findByRole('heading', { name: /edit policy/i })).toBeInTheDocument();
    fireEvent.change(screen.getByLabelText(/policy name/i), {
      target: { value: 'Admin Sign-on Policy Updated' },
    });
    fireEvent.click(screen.getByRole('button', { name: /save policy/i }));

    await waitFor(() => {
      expect(mockedUpdatePolicy).toHaveBeenCalledWith('policy-1', {
        display_name: 'Admin Sign-on Policy Updated',
        description: 'Require MFA for privileged logins',
        policy_data: signonPolicy.policy_data,
        is_active: true,
        priority: 100,
      });
    });
  });

  it('routes inline editing to the visual builder for advanced changes', async () => {
    renderWithProviders(<PoliciesPage />);

    fireEvent.click(await screen.findByRole('button', { name: 'Edit' }));
    expect(await screen.findByRole('heading', { name: /edit policy/i })).toBeInTheDocument();
    fireEvent.click(screen.getByRole('button', { name: /open visual builder/i }));

    expect(getMockRouter().push).toHaveBeenCalledWith('/dashboard/policies/builder?policy_id=policy-1');
  });
});
