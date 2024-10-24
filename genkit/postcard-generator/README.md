# Postcard Demo

|           |                                           |
| --------- | ----------------------------------------- |
| Author(s) | [Matt Day](https://github.com/mattsday) |

**Looking to get started?** Check out [the docs](docs/README.md) for guides.

This demo showcases [Firebase Genkit](https://firebase.google.com/docs/genkit) running inside a [Next.js](https://nextjs.org) app that can be deployed onto [Firebase App Hosting](https://firebase.google.com/docs/app-hosting).

It was originally created for the 2024 London Summit, session [BO1.3 - Kick-start your AI journey with Google Cloud](https://cloudonair.withgoogle.com/events/london-summit-24?talk=b01-3)

![Example Postcard Image](images/example.jpg)

## Overview

This demo is built in two parts: a webapp and a Genkit development environment. Both use the same code, but have different aspects to demo. The most important thing is that it's the same codebase for both - just different tools to interact suitable for different personas and tasks.

See [the documentation](docs/README.md) for more information on how to deploy this and also for an example demo script.

## Using

See [the docs](docs/README.md) to get started!

### TL;DR

```sh
export PROJECT_ID="my-project-id"
cd terraform
terraform init && terraform apply -var="project_id=${PROJECT_ID}"
cd ..
npm install
npx firebase-tools@latest apphosting:backends:create --project="${PROJECT_ID}"
```
