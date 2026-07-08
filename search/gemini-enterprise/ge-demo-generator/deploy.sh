#!/bin/bash
# Copyright 2026 Google LLC
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     https://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
# deploy.sh — Push to Apps Script and update the production deployment.
# Usage: bash deploy.sh
#
# Prerequisites:
#   - clasp authenticated (npx @google/clasp login)
#   - .clasp.json pointing to the correct Script ID
#
# This script:
#   1. Extracts APP_VERSION from Code.gs
#   2. Runs clasp push --force
#   3. Creates a new version with APP_VERSION as description
#   4. Updates the production deployment to the new version

set -euo pipefail

DEPLOYMENT_ID="${DEPLOYMENT_ID:-AKfycbxL84crJM36plCKcHsz5d0sp_h4Sk21lgTD6chIFk9t42ABggzodjaTIrV5ovWOlpMShA}"
CLASP="npx --registry https://registry.npmjs.org @google/clasp@latest"

# 1. Extract APP_VERSION from Code.gs
APP_VERSION=$(grep "APP_VERSION:" app/Code.gs | head -1 | sed "s/.*'\(.*\)'.*/\1/")
if [ -z "$APP_VERSION" ]; then
  echo "❌ Could not extract APP_VERSION from app/Code.gs"
  exit 1
fi
echo "📦 Version: $APP_VERSION"

# 2. Push to Apps Script
echo "🚀 Pushing to Apps Script..."
$CLASP push --force
echo ""

# 3. Create a new version
echo "📋 Creating version with description: $APP_VERSION"
VERSION_OUTPUT=$($CLASP version "$APP_VERSION" 2>&1)
VERSION_NUM=$(echo "$VERSION_OUTPUT" | grep -oE 'Created version [0-9]+' | grep -oE '[0-9]+')
if [ -z "$VERSION_NUM" ]; then
  echo "❌ Failed to create version. Output: $VERSION_OUTPUT"
  exit 1
fi
echo "✅ Created version $VERSION_NUM"

# 4. Update the production deployment
echo "🔄 Updating deployment $DEPLOYMENT_ID to version $VERSION_NUM..."
$CLASP deploy -i "$DEPLOYMENT_ID" -V "$VERSION_NUM" -d "$APP_VERSION"

echo ""
echo "========================================="
echo "✅ Deployment complete!"
echo "   Version:       $VERSION_NUM"
echo "   Description:   $APP_VERSION"
echo "   Deployment ID: $DEPLOYMENT_ID"
echo "========================================="
