# 🐶 PromptWatchDog Dashboard

This is the local dashboard for managing prompts in PromptWatchDog.

> [!CAUTION]
> **DO NOT DEPLOY THIS DASHBOARD TO THE CLOUD.**
>
> The dashboard requires elevated permissions to create custom log-based metrics and perform administrative operations in GCP. Running this locally follows the **Principle of Least Privilege**, ensuring that these powerful permissions are restricted to your local authenticated session and not exposed via a specialized service account in a deployed environment.

![Dashboard](../static/dashboard.png)


## Getting Started

First, run the development server:

```bash
npm run dev
# or
yarn dev
# or
pnpm dev
# or
bun dev
```

Open [http://localhost:3000](http://localhost:3000) with your browser to see the result.

You can start editing the page by modifying `app/page.tsx`. The page auto-updates as you edit the file.

This project uses [`next/font`](https://nextjs.org/docs/app/building-your-application/optimizing/fonts) to automatically optimize and load [Geist](https://vercel.com/font), a new font family for Vercel.

## Learn More

To learn more about Next.js, take a look at the following resources:

- [Next.js Documentation](https://nextjs.org/docs) - learn about Next.js features and API.
- [Learn Next.js](https://nextjs.org/learn) - an interactive Next.js tutorial.

You can check out [the Next.js GitHub repository](https://github.com/vercel/next.js) - your feedback and contributions are welcome!


