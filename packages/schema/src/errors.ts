// Adapted from Azimlearning/Arcana-v2, packages/schema/src/errors.ts @ 21c6dcf5.
// The one error shape. Every failure the client can see arrives as an ErrorEnvelope, never a stack trace.

export type ErrorCode =
  | "validation_failed"
  | "bad_request"
  | "not_found"
  | "spend_cap_exceeded"
  | "provider_unavailable"
  | "verification_refused"
  | "internal";

/**
 * One violation, located by a dotted path into the offending payload. Two sentinels exist:
 * "(block)" and "(body)" mean the problem is the whole block or body, not one field.
 */
export interface FieldIssue {
  path: string;
  message: string;
}

export interface ErrorEnvelope {
  code: ErrorCode;
  message: string;
  issues: FieldIssue[];
  retryable: boolean;
}
