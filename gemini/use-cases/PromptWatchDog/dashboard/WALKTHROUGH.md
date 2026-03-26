# PromptWatchDog Dashboard Walkthrough

I have created a new Next.js application for the PromptWatchDog Dashboard. This generic UI allows you to list, create, edit, and "deploy" prompts (currently simulated).

## Prerequisities

- Node.js installed

## Getting Started

1. Navigate to the dashboard directory:
   ```bash
   cd dashboard
   ```

2. Install dependencies (if not already done):
   ```bash
   npm install
   ```

3. Run the development server:
   ```bash
   npm run dev
   ```

4. Open [http://localhost:3000](http://localhost:3000) in your browser.

## Features

- **Dashboard**: View all deployed prompts, their status, and service URLs.
- **New Prompt**: Create a new prompt. This simulates a deployment process.
- **Edit Prompt**: Update an existing prompt and "redeploy" it.
- **Mock API**: The backend interactions are currently mocked in `src/services/api.ts`. You can replace these with real API calls to your Python backend when ready.
- **Premium UI**: The interface uses a dark mode, glassmorphism design with responsive components.

## Directory Structure

- `src/app`: App Router pages (`page.tsx`, `new/page.tsx`, `edit/[id]/page.tsx`).
- `src/components`: Reusable UI components (`PromptCard`, `Navbar`, `PromptForm`).
- `src/services`: Mock API service.
- `src/types`: TypeScript definitions.
- `src/app/globals.css`: Global styles (Design System).

## Next Steps

- Integrate with the real Python Watchdog backend.
- Implement real Cloud Run deployment logic (likely in the backend).
- Add authentication if needed.
