/**
 * Undo/Redo History Management for ESM Editor
 *
 * Provides undo/redo functionality with automatic change capture,
 * debounced updates, and keyboard shortcuts.
 */

import { createSignal, createEffect, onCleanup } from 'solid-js';
import type { EsmFile } from 'esm-format';

/**
 * Configuration for undo history behavior
 */
export interface UndoHistoryConfig {
  /** Maximum number of history entries to keep */
  maxEntries?: number;
  /** Debounce delay in milliseconds to avoid capturing every keystroke */
  debounceMs?: number;
  /** Whether to automatically register keyboard shortcuts */
  registerKeyboardShortcuts?: boolean;
}

/**
 * History entry representing a state snapshot
 */
export interface HistoryEntry {
  /** The ESM file state at this point */
  state: EsmFile;
  /** Timestamp when this entry was created */
  timestamp: number;
  /** Optional description of the change */
  description?: string;
}

/**
 * Undo/redo history management interface
 */
export interface UndoHistory {
  /** Undo the last change */
  undo: () => void;
  /** Redo the next change */
  redo: () => void;
  /** Whether undo is available */
  canUndo: () => boolean;
  /** Whether redo is available */
  canRedo: () => boolean;
  /** Clear all history */
  clear: () => void;
  /** Get current history length */
  historyLength: () => number;
  /** Manually capture current state */
  capture: (description?: string) => void;
}

/**
 * Deep clone an EsmFile to create an independent snapshot
 */
function cloneEsmFile(file: EsmFile): EsmFile {
  return JSON.parse(JSON.stringify(file));
}

/**
 * Create undo/redo history management for an ESM file
 *
 * @param file - Reactive signal containing the current ESM file
 * @param setFile - Function to update the ESM file
 * @param config - Optional configuration
 * @returns History management interface with undo/redo functions
 */
export function createUndoHistory(
  file: () => EsmFile,
  setFile: (newFile: EsmFile) => void,
  config: UndoHistoryConfig = {}
): UndoHistory {
  const {
    maxEntries = 100,
    debounceMs = 500,
    registerKeyboardShortcuts = true
  } = config;

  // History stacks
  const [undoStack, setUndoStack] = createSignal<HistoryEntry[]>([]);
  const [redoStack, setRedoStack] = createSignal<HistoryEntry[]>([]);

  // Track if we're currently applying a history change to avoid capturing it
  let isApplyingHistory = false;
  let debounceTimeout: number | null = null;
  let lastCapturedFile: EsmFile | null = null;

  /**
   * Add a new history entry, with debouncing
   */
  function captureState(description?: string) {
    if (isApplyingHistory) return;

    // Clear any existing timeout
    if (debounceTimeout !== null) {
      clearTimeout(debounceTimeout);
    }

    // Debounce the capture to avoid excessive history entries
    debounceTimeout = window.setTimeout(() => {
      const currentFile = file();
      if (!currentFile) return;

      // Don't capture if file hasn't actually changed
      if (lastCapturedFile && JSON.stringify(currentFile) === JSON.stringify(lastCapturedFile)) {
        return;
      }

      const entry: HistoryEntry = {
        state: cloneEsmFile(currentFile),
        timestamp: Date.now(),
        description
      };

      setUndoStack(prev => {
        const newStack = [...prev, entry];
        // Maintain maximum stack size
        if (newStack.length > maxEntries) {
          newStack.splice(0, newStack.length - maxEntries);
        }
        return newStack;
      });

      // Clear redo stack when new change is made
      setRedoStack([]);

      lastCapturedFile = cloneEsmFile(currentFile);
      debounceTimeout = null;
    }, debounceMs);
  }

  /**
   * Undo the last change
   */
  function undo() {
    const stack = undoStack();
    if (stack.length === 0) return;

    const currentFile = file();
    if (!currentFile) return;

    // Save current state to redo stack
    const currentEntry: HistoryEntry = {
      state: cloneEsmFile(currentFile),
      timestamp: Date.now(),
      description: 'Current state'
    };

    setRedoStack(prev => [...prev, currentEntry]);

    // Get the previous state
    const previousEntry = stack[stack.length - 1];

    // Remove from undo stack
    setUndoStack(prev => prev.slice(0, -1));

    // Apply the previous state
    isApplyingHistory = true;
    setFile(cloneEsmFile(previousEntry.state));
    isApplyingHistory = false;
  }

  /**
   * Redo the next change
   */
  function redo() {
    const stack = redoStack();
    if (stack.length === 0) return;

    const currentFile = file();
    if (!currentFile) return;

    // Save current state to undo stack
    const currentEntry: HistoryEntry = {
      state: cloneEsmFile(currentFile),
      timestamp: Date.now(),
      description: 'Redo checkpoint'
    };

    setUndoStack(prev => [...prev, currentEntry]);

    // Get the next state
    const nextEntry = stack[stack.length - 1];

    // Remove from redo stack
    setRedoStack(prev => prev.slice(0, -1));

    // Apply the next state
    isApplyingHistory = true;
    setFile(cloneEsmFile(nextEntry.state));
    isApplyingHistory = false;
  }

  /**
   * Check if undo is available
   */
  function canUndo(): boolean {
    return undoStack().length > 0;
  }

  /**
   * Check if redo is available
   */
  function canRedo(): boolean {
    return redoStack().length > 0;
  }

  /**
   * Clear all history
   */
  function clear() {
    // Cancel any pending debounced captures
    if (debounceTimeout !== null) {
      clearTimeout(debounceTimeout);
      debounceTimeout = null;
    }

    setUndoStack([]);
    setRedoStack([]);
  }

  /**
   * Get current history length
   */
  function historyLength(): number {
    return undoStack().length + redoStack().length;
  }

  // Watch for file changes and capture them
  createEffect(() => {
    const currentFile = file();
    if (currentFile && !isApplyingHistory) {
      captureState('File change');
    }
  });

  // Register keyboard shortcuts if enabled
  if (registerKeyboardShortcuts && typeof window !== 'undefined') {
    const handleKeydown = (event: KeyboardEvent) => {
      if ((event.ctrlKey || event.metaKey)) {
        if (event.key === 'z' && !event.shiftKey) {
          event.preventDefault();
          undo();
        } else if (
          (event.key === 'y') ||
          (event.key === 'z' && event.shiftKey)
        ) {
          event.preventDefault();
          redo();
        }
      }
    };

    document.addEventListener('keydown', handleKeydown);

    onCleanup(() => {
      document.removeEventListener('keydown', handleKeydown);
      if (debounceTimeout !== null) {
        clearTimeout(debounceTimeout);
      }
    });
  }

  return {
    undo,
    redo,
    canUndo,
    canRedo,
    clear,
    historyLength,
    capture: captureState
  };
}

/**
 * Default keyboard shortcut handler for undo/redo
 * Can be used independently of createUndoHistory if needed
 */
export function createUndoKeyboardHandler(
  undoFn: () => void,
  redoFn: () => void,
  canUndo: () => boolean,
  canRedo: () => boolean
) {
  const handleKeydown = (event: KeyboardEvent) => {
    if ((event.ctrlKey || event.metaKey)) {
      if (event.key === 'z' && !event.shiftKey && canUndo()) {
        event.preventDefault();
        undoFn();
      } else if (
        ((event.key === 'y') || (event.key === 'z' && event.shiftKey)) &&
        canRedo()
      ) {
        event.preventDefault();
        redoFn();
      }
    }
  };

  if (typeof window !== 'undefined') {
    document.addEventListener('keydown', handleKeydown);

    onCleanup(() => {
      document.removeEventListener('keydown', handleKeydown);
    });
  }

  return handleKeydown;
}