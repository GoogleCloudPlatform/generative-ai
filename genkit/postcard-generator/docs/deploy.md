# Deploy to Firebase App Hosting

**Note:** By default this app has authentication disabled. This means anyone with the URL can use it. If you intend to leave it running, you should [enable authentication](#authentication).

## Step 1: Push this to GitHub

As of 2024-09-27 App Hosting only supports GitHub, so you will need to create a repository on GitHub and push this code there.

## Step 2: Configure your backend

You can do this from the CLI:

```sh
export PROJECT_ID="my-project-id"
npx firebase-tools@latest apphosting:backends:create --project="${PROJECT_ID}"
```

Run through the wizard - but don't run a deployment just yet as it will fail without appropriate IAM configuration. Remember the backend ID you created earlier

## Step 3: Grant Secret Access

App Hosting allows granular secret access and has a nifty way to manage this. Use the CLI to grant it access to our Maps API secret:

```sh
export BACKEND_ID="my-backend-id"
npx firebase-tools@latest apphosting:secrets:grantaccess NEXT_PUBLIC_GOOGLE_MAPS_PUBLIC_API_KEY --project "${PROJECT_ID}" --backend "${BACKEND_ID}"
npx firebase-tools@latest apphosting:secrets:grantaccess GOOGLE_MAPS_API_SERVER_KEY --project "${PROJECT_ID}" --backend "${BACKEND_ID}"
```

## Step 4: Configure IAM

The Firebase App Hosting service account requires the following additional roles to work with this app:

1. `roles/aiplatform.user` - to access Vertex AI

This cannot be done at setup as this service account is not created until a Firebase App Hosting backend is created. It is not possible to automate App Hosting with Terraform today.

You can either do this manually or with terraform. To do so with terraform:

In the `terraform/` directory, edit your `terraform.tfvars` to add:

```tf
firebase_app_hosting=true
```

Now redeploy:

```sh
terraform apply
```

## Step 5: Rollout

You can now create a new rollout in the console. Navigate to [console.firebase.google.com](https://console.firebase.google.com) and then create a new rollout in App Hosting.

This should deploy your app ready for production!

## Authentication

### Step 1: Deploy Blocking Functions (Optional / Recommended)

[Blocking functions](https://cloud.google.com/identity-platform/docs/blocking-functions) allow you to control who can login. In general, you only want people in your org to use this app. Deploying a blocking function makes this easy and simple.

### Step 2: Configure Firebase Auth

In [the Firebase Console](https://console.firebase.google.com) head to "Authentication" and create a Google sign-in.

Under Settings, selected Authorized Domains and add your deployed App's URLs - e.g. `postcards--postcards-demo.europe-west4.hosted.app`

### Step 3: Add Firebase App Config

In the Project Settings area of [the Firebase Console](https://console.firebase.google.com), select your Web App, and copy the firebase config section. It should look something like this:

```js
const firebaseConfig = {
  apiKey: "xx",
  authDomain: "postcards-demo.firebaseapp.com",
  projectId: "postcards-demo",
  storageBucket: "postcards-demo.appspot.com",
  messagingSenderId: "1022638455307",
  appId: "1:1022638455307:web:bc560683c150393541650e",
};
```

Open [libs/firebase/config.ts](../libs/firebase/config.ts) and replace it with your config **ensuring** you prefix it with `export`. For example:

```ts
export const firebaseConfig = {
  apiKey: "xx",
  authDomain: "postcards-demo.firebaseapp.com",
  projectId: "postcards-demo",
  storageBucket: "postcards-demo.appspot.com",
  messagingSenderId: "1022638455307",
  appId: "1:1022638455307:web:bc560683c150393541650e",
};
```

### Step 4: Configure Deployment

Edit `apphosting.yaml` and change the `AUTH_ENABLED` section to look like this:

```yaml
- variable: AUTH_ENABLED
  value: "true"
  availability:
    - RUNTIME
    - BUILD
```

### Step 5: Push your changes

## Maps Public API Key Security

You should further lock your public API key down so it can only be accessed from your demo. You can modify its configuration to restrict use specifically to your deployed domain.
