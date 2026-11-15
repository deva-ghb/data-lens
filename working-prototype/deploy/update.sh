#!/usr/bin/env bash
# Ships the current commit to the hosted demo: screens to S3 behind CloudFront, API to the EC2 instance.
# Usage: deploy/update.sh            (keeps the demo's data)
#        deploy/update.sh --reset    (also restores the story to Tuesday 28 July, 18:00)
set -euo pipefail
export AWS_PROFILE=${AWS_PROFILE:-deva-dev} AWS_REGION=${AWS_REGION:-us-east-1}
BUCKET=datalens-demo-378617177387
DIST=E1695MI4SV0NTY
HOST=ec2-user@3.91.202.48
KEY=${DATALENS_KEY:-$HOME/.ssh/datalens-demo.pem}
SSH=(ssh -i "$KEY" -o LogLevel=ERROR "$HOST")
root="$(cd "$(dirname "$0")/.." && pwd)"
tmp="$(mktemp -d)"
trap 'rm -rf "$tmp"' EXIT

echo "screens: build and upload"
(cd "$root/frontend" && npm run build >/dev/null)
aws s3 sync "$root/frontend/dist/assets" "s3://$BUCKET/assets" --cache-control "public,max-age=31536000,immutable" --only-show-errors
aws s3 cp "$root/frontend/dist/index.html" "s3://$BUCKET/index.html" --cache-control "no-cache" --only-show-errors
aws s3 cp "$root/frontend/dist/favicon.svg" "s3://$BUCKET/favicon.svg" --only-show-errors
aws cloudfront create-invalidation --distribution-id "$DIST" --paths /index.html >/dev/null

echo "api: copy code, keep the demo's database and settings"
git -C "$root" archive --format=tar.gz -o "$tmp/backend.tgz" HEAD:working-prototype backend
scp -q -i "$KEY" -o LogLevel=ERROR "$tmp/backend.tgz" "$HOST:/tmp/backend.tgz"
"${SSH[@]}" "set -e
  cd /opt/datalens
  tar xzf /tmp/backend.tgz --exclude=backend/data/datalens.db && rm /tmp/backend.tgz
  cd backend && ~/.local/bin/uv sync --no-dev -q
  if [ '${1:-}' = '--reset' ]; then sudo systemctl stop datalens; ~/.local/bin/uv run python scripts/reset.py; fi
  sudo systemctl restart datalens"
echo "done: https://d2v5b43xh6er8w.cloudfront.net"
