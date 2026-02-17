/**
 * TypeScript Integration for ESM Format Package Analytics
 *
 * Provides decorators, functions, and utilities for integrating performance monitoring
 * and analytics into TypeScript/JavaScript ESM format packages.
 */

import { performance } from 'perf_hooks';

// Environment-specific imports
let fs: any;
let path: any;
let os: any;
let crypto: any;

try {
  // Node.js environment
  fs = require('fs');
  path = require('path');
  os = require('os');
  crypto = require('crypto');
} catch (e) {
  // Browser environment - these will be null
  fs = null;
  path = null;
  os = null;
  crypto = null;
}

export interface PerformanceMetric {
  operation: string;
  duration_ms: number;
  memory_mb?: number;
  timestamp: string;
  package: string;
  version: string;
  platform_info: Record<string, string>;
  file_size_bytes?: number;
  success: boolean;
  error_message?: string;
  metadata?: Record<string, any>;
}

export interface UsageEvent {
  event_type: string;
  package: string;
  version: string;
  timestamp: string;
  user_id: string;
  session_id: string;
  file_type?: string;
  file_size_category?: string;
  success: boolean;
  error_type?: string;
  metadata?: Record<string, any>;
}

export interface FeedbackEntry {
  feedback_id: string;
  package: string;
  version: string;
  timestamp: string;
  user_id: string;
  feedback_type: string;
  severity: number;
  title: string;
  description: string;
  platform_info: Record<string, string>;
  reproduction_steps?: string;
  expected_behavior?: string;
  actual_behavior?: string;
  metadata?: Record<string, any>;
}

export interface AnalyticsConfig {
  package_name: string;
  version: string;
  enabled?: boolean;
  storage_backend?: 'localStorage' | 'indexedDB' | 'memory' | 'file';
  api_endpoint?: string; // For server-side analytics
}

/**
 * Main analytics class for TypeScript/JavaScript packages.
 */
export class ESMAnalytics {
  private config: AnalyticsConfig;
  private userId: string;
  private sessionId: string;
  private platformInfo: Record<string, string>;
  private performanceMetrics: PerformanceMetric[] = [];
  private usageEvents: UsageEvent[] = [];
  private feedbackEntries: FeedbackEntry[] = [];
  private isEnabled: boolean;

  private static instance: ESMAnalytics | null = null;

  constructor(config: AnalyticsConfig) {
    this.config = config;
    this.isEnabled = config.enabled ?? this.checkEnvironmentEnabled();

    if (!this.isEnabled) {
      return;
    }

    this.userId = this.getOrCreateUserId();
    this.sessionId = this.generateId();
    this.platformInfo = this.collectPlatformInfo();

    // Load existing data
    this.loadStoredData();

    // Auto-save periodically
    if (typeof window !== 'undefined') {
      setInterval(() => this.saveData(), 30000); // Every 30 seconds

      // Save on page unload
      window.addEventListener('beforeunload', () => this.saveData());
    }
  }

  /**
   * Initialize analytics singleton.
   */
  static initialize(config: AnalyticsConfig): ESMAnalytics {
    if (ESMAnalytics.instance) {
      return ESMAnalytics.instance;
    }

    ESMAnalytics.instance = new ESMAnalytics(config);
    return ESMAnalytics.instance;
  }

  /**
   * Get the current analytics instance.
   */
  static getInstance(): ESMAnalytics | null {
    return ESMAnalytics.instance;
  }

  private checkEnvironmentEnabled(): boolean {
    if (typeof process !== 'undefined' && process.env) {
      return process.env.ESM_ANALYTICS_ENABLED !== 'false';
    }
    if (typeof window !== 'undefined') {
      return localStorage.getItem('esm_analytics_enabled') !== 'false';
    }
    return true;
  }

  private getOrCreateUserId(): string {
    const storageKey = 'esm_analytics_user_id';

    // Try localStorage first (browser)
    if (typeof window !== 'undefined' && window.localStorage) {
      let userId = localStorage.getItem(storageKey);
      if (!userId) {
        userId = this.generateAnonymousUserId();
        localStorage.setItem(storageKey, userId);
      }
      return userId;
    }

    // Try file system (Node.js)
    if (fs && os) {
      try {
        const userFile = path.join(os.homedir(), '.esm_analytics', '.user_id');

        // Try to read existing ID
        if (fs.existsSync(userFile)) {
          return fs.readFileSync(userFile, 'utf8').trim();
        }

        // Create new ID
        const userId = this.generateAnonymousUserId();
        fs.mkdirSync(path.dirname(userFile), { recursive: true });
        fs.writeFileSync(userFile, userId);
        return userId;
      } catch (e) {
        // Fallback to session-only ID
        return this.generateId();
      }
    }

    // Fallback for other environments
    return this.generateId();
  }

  private generateAnonymousUserId(): string {
    // Create anonymous ID based on available system info
    let systemInfo = '';

    if (typeof navigator !== 'undefined') {
      systemInfo = navigator.userAgent + navigator.language;
    } else if (os) {
      systemInfo = os.hostname() + os.arch() + os.platform();
    }

    if (crypto) {
      return crypto.createHash('sha256').update(systemInfo).digest('hex').substring(0, 16);
    } else {
      // Fallback hash function
      let hash = 0;
      for (let i = 0; i < systemInfo.length; i++) {
        const char = systemInfo.charCodeAt(i);
        hash = ((hash << 5) - hash) + char;
        hash = hash & hash; // Convert to 32-bit integer
      }
      return Math.abs(hash).toString(16);
    }
  }

  private generateId(): string {
    if (crypto) {
      return crypto.randomUUID();
    } else {
      // Fallback UUID v4 implementation
      return 'xxxxxxxx-xxxx-4xxx-yxxx-xxxxxxxxxxxx'.replace(/[xy]/g, (c) => {
        const r = Math.random() * 16 | 0;
        const v = c === 'x' ? r : (r & 0x3 | 0x8);
        return v.toString(16);
      });
    }
  }

  private collectPlatformInfo(): Record<string, string> {
    const info: Record<string, string> = {};

    if (typeof navigator !== 'undefined') {
      info.user_agent = navigator.userAgent;
      info.language = navigator.language;
      info.platform = navigator.platform;
      info.cookieEnabled = navigator.cookieEnabled.toString();

      if ('connection' in navigator) {
        const connection = (navigator as any).connection;
        if (connection) {
          info.connection_type = connection.effectiveType || 'unknown';
        }
      }

      if ('deviceMemory' in navigator) {
        info.device_memory = (navigator as any).deviceMemory?.toString() || 'unknown';
      }

      if ('hardwareConcurrency' in navigator) {
        info.cpu_cores = navigator.hardwareConcurrency?.toString() || 'unknown';
      }
    } else if (os) {
      info.os = os.type();
      info.arch = os.arch();
      info.platform = os.platform();
      info.node_version = process.version;
      info.cpu_cores = os.cpus().length.toString();
      info.memory_gb = (os.totalmem() / (1024 ** 3)).toFixed(1);
    }

    return info;
  }

  /**
   * Start tracking a performance operation.
   */
  startOperation(operation: string, fileSizeBytes?: number, metadata?: Record<string, any>): string {
    if (!this.isEnabled) return '';

    const operationId = this.generateId();
    const startTime = performance.now();
    const startMemory = this.getMemoryUsage();

    // Store operation data for later completion
    (this as any)[`_op_${operationId}`] = {
      operation,
      startTime,
      startMemory,
      fileSizeBytes,
      metadata
    };

    return operationId;
  }

  /**
   * End tracking and record performance metric.
   */
  endOperation(operationId: string, success: boolean = true, errorMessage?: string): PerformanceMetric | null {
    if (!this.isEnabled || !operationId) return null;

    const opData = (this as any)[`_op_${operationId}`];
    if (!opData) return null;

    const endTime = performance.now();
    const endMemory = this.getMemoryUsage();

    const metric: PerformanceMetric = {
      operation: opData.operation,
      duration_ms: endTime - opData.startTime,
      memory_mb: Math.max(0, endMemory - opData.startMemory),
      timestamp: new Date().toISOString(),
      package: this.config.package_name,
      version: this.config.version,
      platform_info: this.platformInfo,
      file_size_bytes: opData.fileSizeBytes,
      success,
      error_message: errorMessage,
      metadata: opData.metadata
    };

    this.performanceMetrics.push(metric);

    // Also record usage event
    this.recordUsageEvent(
      opData.operation,
      undefined,
      opData.fileSizeBytes,
      success,
      errorMessage ? 'Error' : undefined,
      opData.metadata
    );

    // Clean up operation data
    delete (this as any)[`_op_${operationId}`];

    this.saveData();
    return metric;
  }

  private getMemoryUsage(): number {
    if (typeof performance !== 'undefined' && 'memory' in performance) {
      return (performance as any).memory?.usedJSHeapSize / (1024 * 1024) || 0;
    }
    if (typeof process !== 'undefined' && process.memoryUsage) {
      return process.memoryUsage().heapUsed / (1024 * 1024);
    }
    return 0;
  }

  private determineFileSizeCategory(sizeBytes?: number): string | undefined {
    if (!sizeBytes) return undefined;

    if (sizeBytes < 1000) return 'tiny';
    if (sizeBytes < 100_000) return 'small';
    if (sizeBytes < 10_000_000) return 'medium';
    if (sizeBytes < 100_000_000) return 'large';
    return 'massive';
  }

  /**
   * Record a usage event.
   */
  recordUsageEvent(
    eventType: string,
    fileType?: string,
    fileSizeBytes?: number,
    success: boolean = true,
    errorType?: string,
    metadata?: Record<string, any>
  ): void {
    if (!this.isEnabled) return;

    const event: UsageEvent = {
      event_type: eventType,
      package: this.config.package_name,
      version: this.config.version,
      timestamp: new Date().toISOString(),
      user_id: this.userId,
      session_id: this.sessionId,
      file_type: fileType,
      file_size_category: this.determineFileSizeCategory(fileSizeBytes),
      success,
      error_type: errorType,
      metadata
    };

    this.usageEvents.push(event);
    this.saveData();
  }

  /**
   * Submit user feedback.
   */
  submitFeedback(
    feedbackType: string,
    severity: number,
    title: string,
    description: string,
    options: {
      reproductionSteps?: string;
      expectedBehavior?: string;
      actualBehavior?: string;
      metadata?: Record<string, any>;
    } = {}
  ): string {
    if (!this.isEnabled) return '';

    const feedbackId = this.generateId();

    const feedback: FeedbackEntry = {
      feedback_id: feedbackId,
      package: this.config.package_name,
      version: this.config.version,
      timestamp: new Date().toISOString(),
      user_id: this.userId,
      feedback_type: feedbackType,
      severity,
      title,
      description,
      platform_info: this.platformInfo,
      reproduction_steps: options.reproductionSteps,
      expected_behavior: options.expectedBehavior,
      actual_behavior: options.actualBehavior,
      metadata: options.metadata
    };

    this.feedbackEntries.push(feedback);
    this.saveData();

    return feedbackId;
  }

  private loadStoredData(): void {
    if (typeof window !== 'undefined' && window.localStorage) {
      try {
        const data = localStorage.getItem('esm_analytics_data');
        if (data) {
          const parsed = JSON.parse(data);
          this.performanceMetrics = parsed.performanceMetrics || [];
          this.usageEvents = parsed.usageEvents || [];
          this.feedbackEntries = parsed.feedbackEntries || [];
        }
      } catch (e) {
        console.warn('Failed to load analytics data from localStorage:', e);
      }
    }
    // TODO: Add file-based storage for Node.js
  }

  private saveData(): void {
    if (typeof window !== 'undefined' && window.localStorage) {
      try {
        const data = {
          performanceMetrics: this.performanceMetrics,
          usageEvents: this.usageEvents,
          feedbackEntries: this.feedbackEntries,
          lastSaved: new Date().toISOString()
        };
        localStorage.setItem('esm_analytics_data', JSON.stringify(data));
      } catch (e) {
        console.warn('Failed to save analytics data to localStorage:', e);
      }
    }
    // TODO: Add file-based storage for Node.js
    // TODO: Add API endpoint submission if configured
  }

  /**
   * Get performance summary.
   */
  getPerformanceSummary(days: number = 30): Record<string, any> {
    if (!this.isEnabled) return {};

    const cutoffDate = new Date();
    cutoffDate.setDate(cutoffDate.getDate() - days);

    const recentMetrics = this.performanceMetrics.filter(
      m => new Date(m.timestamp) > cutoffDate
    );

    const operations: Record<string, any> = {};

    recentMetrics.forEach(metric => {
      if (!operations[metric.operation]) {
        operations[metric.operation] = {
          count: 0,
          total_duration: 0,
          total_memory: 0,
          successful: 0
        };
      }

      const op = operations[metric.operation];
      op.count += 1;
      op.total_duration += metric.duration_ms;
      op.total_memory += metric.memory_mb || 0;
      if (metric.success) op.successful += 1;
    });

    // Calculate averages
    Object.keys(operations).forEach(op => {
      const data = operations[op];
      data.avg_duration_ms = data.total_duration / data.count;
      data.avg_memory_mb = data.total_memory / data.count;
      data.success_rate = (data.successful / data.count) * 100;
      delete data.total_duration;
      delete data.total_memory;
    });

    return {
      package: this.config.package_name,
      version: this.config.version,
      period_days: days,
      operations,
      platform_info: this.platformInfo
    };
  }

  /**
   * Get usage summary.
   */
  getUsageSummary(days: number = 30): Record<string, any> {
    if (!this.isEnabled) return {};

    const cutoffDate = new Date();
    cutoffDate.setDate(cutoffDate.getDate() - days);

    const recentEvents = this.usageEvents.filter(
      e => new Date(e.timestamp) > cutoffDate
    );

    const events: Record<string, any> = {};

    recentEvents.forEach(event => {
      if (!events[event.event_type]) {
        events[event.event_type] = {
          total_events: 0,
          successful_events: 0,
          unique_users: new Set()
        };
      }

      const eventData = events[event.event_type];
      eventData.total_events += 1;
      if (event.success) eventData.successful_events += 1;
      eventData.unique_users.add(event.user_id);
    });

    // Convert sets to counts
    Object.keys(events).forEach(eventType => {
      const eventData = events[eventType];
      eventData.unique_users = eventData.unique_users.size;
      eventData.success_rate = (eventData.successful_events / eventData.total_events) * 100;
    });

    return {
      package: this.config.package_name,
      version: this.config.version,
      period_days: days,
      events
    };
  }
}

/**
 * Decorator for tracking performance.
 */
export function trackPerformance(operationName?: string, trackFileSize: boolean = false) {
  return function (target: any, propertyName: string, descriptor: PropertyDescriptor) {
    const method = descriptor.value;

    descriptor.value = async function (...args: any[]) {
      const analytics = ESMAnalytics.getInstance();
      if (!analytics) {
        return method.apply(this, args);
      }

      const opName = operationName || `${target.constructor.name}.${propertyName}`;
      const fileSize = trackFileSize ? extractFileSize(args) : undefined;

      const operationId = analytics.startOperation(opName, fileSize);

      try {
        const result = await method.apply(this, args);
        analytics.endOperation(operationId, true);
        return result;
      } catch (error) {
        analytics.endOperation(operationId, false, error.toString());
        throw error;
      }
    };

    return descriptor;
  };
}

/**
 * Decorator for recording usage events.
 */
export function recordEvent(eventType?: string, trackFileInfo: boolean = false) {
  return function (target: any, propertyName: string, descriptor: PropertyDescriptor) {
    const method = descriptor.value;

    descriptor.value = async function (...args: any[]) {
      const analytics = ESMAnalytics.getInstance();
      if (!analytics) {
        return method.apply(this, args);
      }

      const eventName = eventType || `${target.constructor.name}.${propertyName}`;
      const { fileType, fileSize } = trackFileInfo ? extractFileInfo(args) : { fileType: undefined, fileSize: undefined };

      try {
        const result = await method.apply(this, args);
        analytics.recordUsageEvent(eventName, fileType, fileSize, true);
        return result;
      } catch (error) {
        analytics.recordUsageEvent(eventName, fileType, fileSize, false, error.constructor.name);
        throw error;
      }
    };

    return descriptor;
  };
}

/**
 * Context manager for manual operation tracking.
 */
export class OperationTracker {
  private analytics: ESMAnalytics | null;
  private operationId: string = '';

  constructor(
    private operation: string,
    private fileSizeBytes?: number,
    private metadata?: Record<string, any>
  ) {
    this.analytics = ESMAnalytics.getInstance();
  }

  start(): void {
    if (this.analytics) {
      this.operationId = this.analytics.startOperation(
        this.operation,
        this.fileSizeBytes,
        this.metadata
      );
    }
  }

  end(success: boolean = true, errorMessage?: string): void {
    if (this.analytics) {
      this.analytics.endOperation(this.operationId, success, errorMessage);
    }
  }
}

/**
 * Utility function to create an operation tracker.
 */
export function trackOperation(
  operation: string,
  fileSizeBytes?: number,
  metadata?: Record<string, any>
): OperationTracker {
  return new OperationTracker(operation, fileSizeBytes, metadata);
}

// Helper functions
function extractFileSize(args: any[]): number | undefined {
  // Try to find file size in arguments
  for (const arg of args) {
    if (typeof arg === 'string' && fs) {
      try {
        const stats = fs.statSync(arg);
        return stats.size;
      } catch (e) {
        // Not a valid file path
      }
    } else if (typeof arg === 'string' || arg instanceof ArrayBuffer) {
      return arg.length;
    }
  }
  return undefined;
}

function extractFileInfo(args: any[]): { fileType?: string; fileSize?: number } {
  for (const arg of args) {
    if (typeof arg === 'string') {
      // Try as file path
      if (path && arg.includes('.')) {
        const ext = path.extname(arg).toLowerCase().replace('.', '');
        let size: number | undefined;

        if (fs) {
          try {
            const stats = fs.statSync(arg);
            size = stats.size;
          } catch (e) {
            // Not a valid file path, might be content
            size = arg.length;
          }
        } else {
          size = arg.length;
        }

        return { fileType: ext, fileSize: size };
      } else {
        // Treat as content
        return { fileSize: arg.length };
      }
    } else if (arg instanceof ArrayBuffer) {
      return { fileSize: arg.byteLength };
    }
  }

  return {};
}

// Convenience functions
export function submitFeedback(
  feedbackType: string,
  severity: number,
  title: string,
  description: string,
  options?: {
    reproductionSteps?: string;
    expectedBehavior?: string;
    actualBehavior?: string;
    metadata?: Record<string, any>;
  }
): string | null {
  const analytics = ESMAnalytics.getInstance();
  if (!analytics) return null;

  return analytics.submitFeedback(feedbackType, severity, title, description, options);
}

export function getPerformanceSummary(days: number = 30): Record<string, any> | null {
  const analytics = ESMAnalytics.getInstance();
  if (!analytics) return null;

  return analytics.getPerformanceSummary(days);
}

export function getUsageSummary(days: number = 30): Record<string, any> | null {
  const analytics = ESMAnalytics.getInstance();
  if (!analytics) return null;

  return analytics.getUsageSummary(days);
}