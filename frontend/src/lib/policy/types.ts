/**
 * Policy Builder Types
 * Type definitions for Keycloak policy structure and React Flow nodes
 */

import { Node, Edge } from 'reactflow';

// Keycloak Policy Types
export type PolicyType =
  | 'role'
  | 'user'
  | 'group'
  | 'client'
  | 'time'
  | 'ip'
  | 'js'
  | 'aggregate';

export type PolicyLogic = 'POSITIVE' | 'NEGATIVE';

export type DecisionStrategy = 'AFFIRMATIVE' | 'UNANIMOUS' | 'CONSENSUS';

export type AggregateGateType = 'AND' | 'OR' | 'NOT';

// Policy Node Data Types
export interface RolePolicyData {
  type: 'role';
  roles: Array<{
    id: string;
    name: string;
    required: boolean;
  }>;
  logic: PolicyLogic;
}

export interface TimePolicyData {
  type: 'time';
  daysOfWeek: number[]; // 0-6 (Sunday-Saturday)
  hour: number;
  minute: number;
  hourEnd: number;
  minuteEnd: number;
  dayMonth?: string;
  dayMonthEnd?: string;
  notBefore?: string;
  notOnOrAfter?: string;
  timezone: string;
}

export interface IPPolicyData {
  type: 'ip';
  ipAddresses: string[]; // CIDR notation
  logic: PolicyLogic;
}

export interface AggregatePolicyData {
  type: 'aggregate';
  gateType: AggregateGateType;
  decisionStrategy?: DecisionStrategy;
  logic: PolicyLogic;
  policies: string[]; // IDs of child policies
}

export interface GroupPolicyData {
  type: 'group';
  groups: Array<{
    id: string;
    name: string;
    extendChildren: boolean;
  }>;
  logic: PolicyLogic;
}

export interface ClientPolicyData {
  type: 'client';
  clients: string[];
  logic: PolicyLogic;
}

export interface UserPolicyData {
  type: 'user';
  users: string[];
  logic: PolicyLogic;
}

export interface JavaScriptPolicyData {
  type: 'js';
  code: string;
  logic: PolicyLogic;
}

export type PolicyNodeData =
  | RolePolicyData
  | TimePolicyData
  | IPPolicyData
  | AggregatePolicyData
  | GroupPolicyData
  | ClientPolicyData
  | UserPolicyData
  | JavaScriptPolicyData;

// React Flow Node Types
export interface PolicyNode extends Node {
  type: 'policyNode';
  data: PolicyNodeData & {
    label: string;
    selected?: boolean;
  };
}

export interface AggregateNode extends Node {
  type: 'aggregateNode';
  data: AggregatePolicyData & {
    label: string;
    selected?: boolean;
  };
}

export type PolicyFlowNode = PolicyNode | AggregateNode;

export type PolicyFlowEdge = Edge;

// Keycloak Policy JSON Structure
export interface KeycloakPolicy {
  id?: string;
  name: string;
  type: PolicyType;
  logic: PolicyLogic;
  decisionStrategy?: DecisionStrategy;
  roles?: Array<{
    id: string;
    required: boolean;
  }>;
  users?: string[];
  groups?: Array<{
    id: string;
    extendChildren: boolean;
  }>;
  clients?: string[];
  ipAddress?: string;
  dayMonth?: string;
  dayMonthEnd?: string;
  hour?: string;
  minute?: string;
  hourEnd?: string;
  minuteEnd?: string;
  notBefore?: string;
  notOnOrAfter?: string;
  code?: string; // For JS policies
  policies?: Array<{
    id: string;
  }>;
}

// Node Palette Item
export interface NodePaletteItem {
  id: string;
  label: string;
  type: PolicyType | 'aggregate';
  icon: string;
  description: string;
  color: string;
  gateType?: AggregateGateType;
}

