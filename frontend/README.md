# Autonomous Code Reviewer AI - Next.js Frontend Foundation

This is the Next.js 15 (App Router) frontend application foundation for the **Autonomous Code Reviewer AI** dashboard, designed under Clean Architecture and Domain-Driven Design (DDD) principles.

---

## Technical Stack
- **Framework**: Next.js 15 (App Router, Turbopack) & React 19
- **Language**: TypeScript (Strict Mode)
- **Styling**: Tailwind CSS v4 & shadcn/ui custom primitives
- **Theming**: next-themes (Light/Dark/System theme synchronization)
- **State Management**: TanStack Query v5 (Server state) & Zustand v5 (Client state)
- **Validation**: Zod
- **API Client**: Axios (isolated inside the Infrastructure layer)
- **Editor Workspace**: Monaco Editor (`@monaco-editor/react`)
- **Testing**: Vitest, Playwright, and Mock Service Worker (MSW)

---

## Folder Architecture

The codebase enforces strict horizontal layer boundaries to isolate core business rules:

```text
src/
├── app/                        # Next.js App Router Pages and BFF Route Handlers
│   ├── api/                    # Backend-for-Frontend (BFF) endpoint proxies
│   └── dashboard/              # Workspace panels and dynamic report pages
├── contracts/                  # Type-safe API Request/Response contracts (Zod)
├── domain/                     # Pure Enterprise Business Rules
│   ├── entities/               # Core domain entities (Repository, Analysis, User)
│   ├── value_objects/          # Immutable domain properties (CostMetric)
│   ├── ports/                  # Abstract service port interfaces
│   ├── exceptions/             # Domain validation and runtime exceptions
│   └── validation/             # Framework-agnostic validators
├── services/                   # Infrastructure Adapters (implementing Domain Ports)
│   ├── api/                    # Axios API Client setup & DTO-to-Entity Mappers
│   └── events/                 # Real-time message adapters (WS/SSE/Polling)
├── features/                   # Self-contained business features
│   ├── dashboard/              # Upload selectors and widgets
│   ├── reports/                # Code viewports and issue navigation
│   └── auth/                   # Route protection guards and login views
├── widgets/                    # Reusable compound dashboard blocks
├── components/                 # Shared visual primitives (Radix/shadcn UI)
├── providers/                  # Application wrappers injecting contexts
├── stores/                     # Zustand global UI state stores
├── hooks/                      # Shared utility hooks
├── styles/                     # Tailwind index.css and design tokens
├── types/                      # Shared TypeScript definitions
├── config/                     # Environment configuration loader and validator
└── lib/                        # Third-party utilities (cn)
```

---

## How It Works

### 1. Backend-for-Frontend (BFF)
Browser clients communicate strictly with the Next.js Route Handlers (`src/app/api/`), which proxy requests to the FastAPI engine. This layer handles security constraints:
- Storing JWT access tokens in memory and refresh tokens in secure, HttpOnly cookies.
- Injecting CSRF tokens and correlation tracing headers (`X-Request-ID`).
- Normalizing API responses before sending them to the browser client.

### 2. Providers Layer
Root-level providers are registered inside `src/app/layout.tsx` to wrap children components:
- `ThemeProvider`: Implements system-preferred themes (Dark mode by default).
- `QueryProvider`: Configures the TanStack Query client for fetching and caching server data.
- `SessionProvider`: Manages memory sessions, permission checks, and RBAC hooks (`useCurrentUser()`, `usePermissions()`).
- `ShortcutProvider`: Standardizes global hotkey keybindings (e.g. `Ctrl+K`).
- `PaletteProvider`: Coordinates overlay transitions for the Command Palette.
- `NotificationProvider`: Handles visual toast alert stacks.

### 3. Styling & Theming
Theme HSL color tokens are configured in `src/styles/globals.css` inside Tailwind's `@theme` directive. Colors align with dark-first visual requirements:
- Dark background HSL: `hsl(240 10% 3.9%)` (Obsidian)
- Accent HSL: `hsl(200 100% 50%)` (Neon Cyan)
Use the `useTheme` hook from `next-themes` to toggle visual modes.

---

## Development Operations

### Environment Configurations
1. Copy the example configuration template:
   ```bash
   cp .env.example .env.local
   ```
2. The environment schema is validated dynamically using Zod under `src/config/index.ts`. Missing configurations will trigger compiler warnings.

### Starting Local Server
Runs the Next.js development server in Turbopack mode:
```bash
npm run dev
```
Open [http://localhost:3000](http://localhost:3000) to view the workspace interface.

---

## Testing Infrastructure

### 1. Unit & Integration Testing (Vitest + MSW)
- Excludes Playwright end-to-end tests from unit runs.
- MSW server hooks (`src/tests/mocks/server.ts`) intercept fetching requests automatically.
- Execute unit tests:
  ```bash
  npm run test:unit
  ```

### 2. End-to-End Testing (Playwright)
- Spins up the Next.js development server automatically before starting browser tests.
- Execute e2e test suite:
  ```bash
  npm run test:e2e
  ```
