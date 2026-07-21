#!/usr/bin/env bash
# One-time GCP setup for the screener jobs (Cloud Build + Cloud Scheduler).
# Mirrors the Ahoya daily-ci pattern. Run section by section, not blindly.
#
# Prereqs done in the console first (one-time OAuth):
#   Cloud Build > Repositories > connect the GitHub repo (2nd gen connection).
#
# Usage: PROJECT=<gcp-project-id> REPO_OWNER=<gh-user> REPO_NAME=stocks-analyzer bash scripts/setup-gcp.sh
set -euo pipefail

PROJECT="${PROJECT:?set PROJECT=<gcp-project-id>}"
REPO_OWNER="${REPO_OWNER:?set REPO_OWNER=<github user/org>}"
REPO_NAME="${REPO_NAME:-stocks-analyzer}"
REGION="us-central1"
CONNECTION="${CONNECTION:-github}"   # name of the Cloud Build 2nd-gen connection

gcloud services enable cloudbuild.googleapis.com cloudscheduler.googleapis.com \
  secretmanager.googleapis.com --project "$PROJECT"

# 1. Secret: single .env blob (edit a local file first, then pipe it in)
#    cat > /tmp/stocks-analyzer.env <<'EOF'
#    SUPABASE_URL=https://xxxx.supabase.co
#    SUPABASE_SERVICE_KEY=eyJ...
#    RESEND_API_KEY=re_...
#    ALERT_FROM=stocks-analyzer <alerts@yourdomain.com>
#    ALERT_TO=kunalganglani@gmail.com
#    EOF
if ! gcloud secrets describe stocks-analyzer-env --project "$PROJECT" >/dev/null 2>&1; then
  gcloud secrets create stocks-analyzer-env --project "$PROJECT" \
    --replication-policy automatic --data-file /tmp/stocks-analyzer.env
else
  gcloud secrets versions add stocks-analyzer-env --project "$PROJECT" \
    --data-file /tmp/stocks-analyzer.env
fi

PROJECT_NUMBER=$(gcloud projects describe "$PROJECT" --format 'value(projectNumber)')
CB_SA="${PROJECT_NUMBER}-compute@developer.gserviceaccount.com"

gcloud secrets add-iam-policy-binding stocks-analyzer-env --project "$PROJECT" \
  --member "serviceAccount:${CB_SA}" --role roles/secretmanager.secretAccessor

# 2. Build triggers (manual; scheduler/dashboard invoke them)
gcloud builds triggers create github --project "$PROJECT" --region "$REGION" \
  --name stocks-daily \
  --repository "projects/$PROJECT/locations/$REGION/connections/$CONNECTION/repositories/$REPO_OWNER-$REPO_NAME" \
  --branch-pattern '^main$' --build-config cloudbuild.yaml \
  --substitutions _MODE=daily --include-logs-with-status

gcloud builds triggers create github --project "$PROJECT" --region "$REGION" \
  --name stocks-weekly \
  --repository "projects/$PROJECT/locations/$REGION/connections/$CONNECTION/repositories/$REPO_OWNER-$REPO_NAME" \
  --branch-pattern '^main$' --build-config cloudbuild.yaml \
  --substitutions _MODE=weekly --include-logs-with-status

# 3. Scheduler service account allowed to run triggers
SCHED_SA="stocks-scheduler@${PROJECT}.iam.gserviceaccount.com"
gcloud iam service-accounts create stocks-scheduler --project "$PROJECT" \
  --display-name "stocks-analyzer scheduler" || true
gcloud projects add-iam-policy-binding "$PROJECT" \
  --member "serviceAccount:${SCHED_SA}" --role roles/cloudbuild.builds.editor

DAILY_ID=$(gcloud builds triggers describe stocks-daily --project "$PROJECT" --region "$REGION" --format 'value(id)')
WEEKLY_ID=$(gcloud builds triggers describe stocks-weekly --project "$PROJECT" --region "$REGION" --format 'value(id)')

# 4. Scheduler jobs (22:30 UTC weekdays after US close; Sunday 08:00 UTC)
gcloud scheduler jobs create http stocks-daily-screen --project "$PROJECT" \
  --location "$REGION" --schedule "30 22 * * 1-5" --time-zone "Etc/UTC" \
  --uri "https://cloudbuild.googleapis.com/v1/projects/$PROJECT/locations/$REGION/triggers/$DAILY_ID:run" \
  --http-method POST --message-body '{"source":{"branchName":"main"}}' \
  --oauth-service-account-email "$SCHED_SA"

gcloud scheduler jobs create http stocks-weekly-fundamentals --project "$PROJECT" \
  --location "$REGION" --schedule "0 8 * * 0" --time-zone "Etc/UTC" \
  --uri "https://cloudbuild.googleapis.com/v1/projects/$PROJECT/locations/$REGION/triggers/$WEEKLY_ID:run" \
  --http-method POST --message-body '{"source":{"branchName":"main"}}' \
  --oauth-service-account-email "$SCHED_SA"

# 5. Dashboard "Run now": create a key for a minimal SA and put it in Vercel env
#    GCP_SA_KEY (JSON), GCP_PROJECT, CLOUD_BUILD_TRIGGER_ID=$DAILY_ID
echo "daily trigger id:  $DAILY_ID"
echo "weekly trigger id: $WEEKLY_ID"
