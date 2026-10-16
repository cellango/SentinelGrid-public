/**
 * Hook for detecting user persona from roles
 */

import { useState, useEffect } from 'react';

export type Persona = 'executive' | 'operations' | 'analyst' | 'compliance' | 'technical' | 'iam' | 'default';

interface User {
  roles?: string[];
  email?: string;
}

/**
 * Detect persona from user roles
 */
export function usePersona(): Persona {
  const [persona, setPersona] = useState<Persona>('default');
  const [user, setUser] = useState<User | null>(null);

  useEffect(() => {
    // Get user info from localStorage or auth context
    // In production, this would come from AuthProvider
    if (typeof window !== 'undefined') {
      const userStr = localStorage.getItem('user');
      if (userStr) {
        try {
          const parsedUser = JSON.parse(userStr);
          setUser(parsedUser);
        } catch (e) {
          console.error('Failed to parse user from localStorage:', e);
        }
      }
    }
  }, []);

  useEffect(() => {
    if (!user || !user.roles || user.roles.length === 0) {
      setPersona('default');
      return;
    }

    const roles = user.roles.map((r) => r.toLowerCase());

    // Persona detection logic
    if (roles.includes('ciso') || roles.includes('executive') || roles.includes('tenant_admin')) {
      setPersona('executive');
    } else if (roles.includes('soc_manager')) {
      setPersona('operations');
    } else if (roles.includes('soc_analyst')) {
      setPersona('analyst');
    } else if (roles.includes('compliance_officer')) {
      setPersona('compliance');
    } else if (roles.includes('security_engineer')) {
      setPersona('technical');
    } else if (roles.includes('it_admin')) {
      setPersona('iam');
    } else {
      setPersona('analyst'); // Default to analyst view
    }
  }, [user]);

  return persona;
}

/**
 * Get persona display name
 */
export function getPersonaDisplayName(persona: Persona): string {
  const names: Record<Persona, string> = {
    executive: 'Executive Dashboard',
    operations: 'Operations Dashboard',
    analyst: 'Analyst Dashboard',
    compliance: 'Compliance Dashboard',
    technical: 'Technical Dashboard',
    iam: 'IAM Dashboard',
    default: 'Dashboard',
  };
  return names[persona];
}

