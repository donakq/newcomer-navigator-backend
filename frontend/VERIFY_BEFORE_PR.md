# Copy and PR checklist

- This patch was generated from a previously shared frontend snapshot, **not** from the newly downloaded repository at `/Users/vicky/Desktop/Vicky/AI Project/Demo 1/frontend` (which is not accessible to this chat).
- The overlay replaces only listed app route files, adds `components/Shell.tsx`, `lib/demo.ts`, and ensures the campus illustration exists. It does **not** replace `package.json`, `tsconfig.json`, `app/layout.tsx` (so your Vercel Speed Insights stays intact), `.git`, or any backend files.
- Review `git status` and `git diff` before committing. Pay attention to any existing page changes not in the previous snapshot.
- The generated TS/TSX files passed TypeScript's **syntax parser**, but **a full `npm run build` was not possible** in the assistant environment because npm dependencies were not cached and internet installation was unavailable. Run build in your actual checkout.
- App routes use imports such as `@/lib/demo`; repo must have `@/*` alias set in tsconfig, as was present in previous Next.js frontend snapshot.
- Because backend design and PRD are not aligned, all backend integration is deferred. No API keys or secrets in the overlay.
