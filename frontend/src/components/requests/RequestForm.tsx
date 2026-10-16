/**
 * Request Form Component
 * Form for creating new access requests
 */

'use client';

import { useEffect } from 'react';
import { useForm } from 'react-hook-form';
import { zodResolver } from '@hookform/resolvers/zod';
import { z } from 'zod';
import { useCreateAccessRequest } from '@/lib/hooks/useAccessRequests';
import { useRouter } from 'next/navigation';

const requestSchema = z.object({
  resource_type: z.string().min(1, 'Resource type is required'),
  resource_id: z.string().min(1, 'Resource ID is required'),
  action: z.string().min(1, 'Action is required'),
  justification: z.string().min(10, 'Justification must be at least 10 characters'),
  expires_at: z.string().optional(),
});

type RequestFormData = z.infer<typeof requestSchema>;

interface RequestFormProps {
  tenantId: string; // TODO: Get from context
  onSuccess?: () => void;
  initialValues?: Partial<RequestFormData>;
}

export function RequestForm({ tenantId, onSuccess, initialValues }: RequestFormProps) {
  const router = useRouter();
  const createRequest = useCreateAccessRequest();

  const {
    register,
    handleSubmit,
    formState: { errors, isSubmitting },
    reset,
  } = useForm<RequestFormData>({
    resolver: zodResolver(requestSchema),
    defaultValues: initialValues,
  });

  useEffect(() => {
    reset({
      resource_type: initialValues?.resource_type || '',
      resource_id: initialValues?.resource_id || '',
      action: initialValues?.action || '',
      justification: initialValues?.justification || '',
      expires_at: initialValues?.expires_at,
    });
  }, [initialValues, reset]);

  const onSubmit = async (data: RequestFormData) => {
    try {
      const request = await createRequest.mutateAsync({
        tenant_id: tenantId,
        resource_type: data.resource_type,
        resource_id: data.resource_id,
        action: data.action,
        justification: data.justification,
        expires_at: data.expires_at ? new Date(data.expires_at).toISOString() : undefined,
      });
      reset();
      onSuccess?.();
      router.push(`/dashboard/requests/${request.id}`);
    } catch (error) {
      // Error handled by mutation hook
    }
  };

  return (
    <form onSubmit={handleSubmit(onSubmit)} className="bg-surface-card rounded-lg shadow-sm border border-surface-card-border p-6 space-y-6">
      <div>
        <h2 className="text-xl font-semibold text-text-main mb-4">Request Access</h2>
        <p className="text-sm text-text-muted">
          Submit a request for access to a resource. Your request will be reviewed by a manager or administrator.
        </p>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
        <div>
          <label htmlFor="resource_type" className="block text-sm font-medium text-text-muted mb-1">
            Resource Type <span className="text-red-500">*</span>
          </label>
          <input
            {...register('resource_type')}
            type="text"
            id="resource_type"
            placeholder="e.g., incident, alert"
            className="w-full px-3 py-2 border border-border rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
          />
          {errors.resource_type && (
            <p className="mt-1 text-sm text-red-600">{errors.resource_type.message}</p>
          )}
        </div>

        <div>
          <label htmlFor="resource_id" className="block text-sm font-medium text-text-muted mb-1">
            Resource ID <span className="text-red-500">*</span>
          </label>
          <input
            {...register('resource_id')}
            type="text"
            id="resource_id"
            placeholder="* or specific ID"
            className="w-full px-3 py-2 border border-border rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
          />
          {errors.resource_id && (
            <p className="mt-1 text-sm text-red-600">{errors.resource_id.message}</p>
          )}
          <p className="mt-1 text-xs text-text-muted">Use * for all resources of this type</p>
        </div>

        <div>
          <label htmlFor="action" className="block text-sm font-medium text-text-muted mb-1">
            Action <span className="text-red-500">*</span>
          </label>
          <select
            {...register('action')}
            id="action"
            className="w-full px-3 py-2 border border-border rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
          >
            <option value="">Select action</option>
            <option value="read">Read</option>
            <option value="write">Write</option>
            <option value="delete">Delete</option>
            <option value="execute">Execute</option>
            <option value="triage">Triage</option>
            <option value="revoke">Revoke</option>
          </select>
          {errors.action && <p className="mt-1 text-sm text-red-600">{errors.action.message}</p>}
        </div>
      </div>

      <div>
        <label htmlFor="justification" className="block text-sm font-medium text-text-muted mb-1">
          Justification <span className="text-red-500">*</span>
        </label>
        <textarea
          {...register('justification')}
          id="justification"
          rows={4}
          placeholder="Explain why you need this access..."
          className="w-full px-3 py-2 border border-border rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
        />
        {errors.justification && (
          <p className="mt-1 text-sm text-red-600">{errors.justification.message}</p>
        )}
        <p className="mt-1 text-xs text-text-muted">Minimum 10 characters required</p>
      </div>

      <div>
        <label htmlFor="expires_at" className="block text-sm font-medium text-text-muted mb-1">
          Expiration Date (Optional)
        </label>
        <input
          {...register('expires_at')}
          type="datetime-local"
          id="expires_at"
          className="w-full px-3 py-2 border border-border rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
        />
        <p className="mt-1 text-xs text-text-muted">Leave empty for permanent access</p>
      </div>

      <div className="flex justify-end gap-3 pt-4 border-t border-surface-card-border">
        <button
          type="button"
          onClick={() => reset()}
          className="px-4 py-2 border border-border rounded-md text-sm font-medium text-text-muted hover:bg-surface-hover"
        >
          Clear
        </button>
        <button
          type="submit"
          disabled={isSubmitting || createRequest.isPending}
          className="px-4 py-2 bg-blue-600 text-white rounded-md text-sm font-medium hover:bg-blue-700 disabled:opacity-50 disabled:cursor-not-allowed"
        >
          {createRequest.isPending ? 'Submitting...' : 'Submit Request'}
        </button>
      </div>
    </form>
  );
}
