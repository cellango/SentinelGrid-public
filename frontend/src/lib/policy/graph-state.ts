/**
 * Graph State Management
 * Handles undo/redo functionality for policy builder
 */

import { Node, Edge } from 'reactflow';

interface GraphState {
  nodes: Node[];
  edges: Edge[];
}

export class GraphStateManager {
  private history: GraphState[] = [];
  private currentIndex: number = -1;
  private maxHistorySize: number = 50;

  constructor(initialNodes: Node[] = [], initialEdges: Edge[] = []) {
    this.pushState({ nodes: initialNodes, edges: initialEdges });
  }

  /**
   * Push a new state to history
   */
  pushState(state: GraphState): void {
    // Remove any states after current index (when undoing and then making changes)
    this.history = this.history.slice(0, this.currentIndex + 1);

    // Add new state
    this.history.push({
      nodes: JSON.parse(JSON.stringify(state.nodes)),
      edges: JSON.parse(JSON.stringify(state.edges)),
    });

    // Limit history size
    if (this.history.length > this.maxHistorySize) {
      this.history.shift();
    } else {
      this.currentIndex++;
    }
  }

  /**
   * Get current state
   */
  getCurrentState(): GraphState | null {
    if (this.currentIndex < 0 || this.currentIndex >= this.history.length) {
      return null;
    }
    return {
      nodes: JSON.parse(JSON.stringify(this.history[this.currentIndex].nodes)),
      edges: JSON.parse(JSON.stringify(this.history[this.currentIndex].edges)),
    };
  }

  /**
   * Undo to previous state
   */
  undo(): GraphState | null {
    if (this.canUndo()) {
      this.currentIndex--;
      return this.getCurrentState();
    }
    return null;
  }

  /**
   * Redo to next state
   */
  redo(): GraphState | null {
    if (this.canRedo()) {
      this.currentIndex++;
      return this.getCurrentState();
    }
    return null;
  }

  /**
   * Check if undo is possible
   */
  canUndo(): boolean {
    return this.currentIndex > 0;
  }

  /**
   * Check if redo is possible
   */
  canRedo(): boolean {
    return this.currentIndex < this.history.length - 1;
  }

  /**
   * Clear history
   */
  clear(): void {
    this.history = [];
    this.currentIndex = -1;
  }
}

