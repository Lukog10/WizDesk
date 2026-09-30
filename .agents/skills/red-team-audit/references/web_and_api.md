# Web and API Attack Surfaces

This reference defines deep-dive inspection vectors for Web applications, APIs, single page applications (SPAs), server-side rendering (SSR), and serverless edge functions.

## 1. Secrets and Client Bundles
- Search client-side directories (`/pages`, `/app`, `/src`, `/public`, `/components`) for leaked admin keys or service role secrets.
- Verify environment variable naming: ensure private keys never use client prefixes like `NEXT_PUBLIC_`, `VITE_`, `REACT_APP_`, or `EXPO_PUBLIC_`.
- Inspect git commits and PR history for credentials, tokens, and connection strings committed in previous revisions.

## 2. Databases, BaaS, and Supabase
- Audit migration scripts for tables missing Row Level Security (`ENABLE ROW LEVEL SECURITY`).
- Scan for `service_role` keys invoked in client-reachable routes, Edge Functions without authorization checks, or browser code.
- Check RLS policies: verify that `auth.uid()` calls wrap queries properly: `(select auth.uid())` to avoid per-row re-evaluation and bypasses.
- Verify storage bucket access levels: confirm private buckets are not set to public read.
- Audit query builders and raw SQL for interpolation: replace string concatenation with parameterized prepared statements.

## 3. Authentication, Authorization, and Session Management
- Inspect all endpoints and server actions: confirm every mutating route enforces server-side authentication.
- Verify role checks: ensure admin capabilities verify user roles in database records or secure JWT claims, never trust client headers.
- Inspect CORS headers: flag `Access-Control-Allow-Origin: *` on routes that mutate state, handle sessions, or process credentials.
- Verify CSRF protection on cookie-authenticated forms and mutations.
- Check JWT verification routines: confirm signature verification, expiration check (`exp`), issuer check (`iss`), and rejection of `alg: none`.

## 4. Input Handling and Injection
- Cross-Site Scripting (XSS): audit usages of `innerHTML`, `dangerouslySetInnerHTML`, `v-html`, and unescaped templates.
- Server-Side Request Forgery (SSRF): check URL fetchers, webhook dispatchers, and avatar importers for unvalidated user URLs targeting internal networks (`127.0.0.1`, `169.254.169.254`, `10.0.0.0/8`).
- Path traversal: ensure file download and upload handlers validate filenames against directory traversal (`../`).

## 5. Webhook Endpoints
- Confirm signature verification on incoming webhooks (Stripe, Clerk, GitHub, Resend, Twilio).
- Ensure HMAC computation uses the raw request payload buffer, not parsed or re-serialized JSON.
- Verify timestamp replay tolerance checks (reject webhooks with timestamps older than 5 minutes).
- Confirm webhook secret tokens are never logged or echoed in HTTP error responses.
