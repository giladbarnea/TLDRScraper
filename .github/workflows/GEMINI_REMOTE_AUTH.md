---
last_updated: 2026-01-02 11:51
---
These commands were used once locally in an authenticated session to set up the remote auth for the Gemini API:

```sh
# 1. Enable required APIs
gcloud services enable iamcredentials.googleapis.com --quiet
gcloud services enable sts.googleapis.com --quiet
gcloud services enable aiplatform.googleapis.com --quiet

# 2. Create Workload Identity Pool
gcloud iam workload-identity-pools create "github-pool" \
  --location="global" \
  --display-name="GitHub Actions Pool"

# 3. Create Workload Identity Provider (connects GitHub)
gcloud iam workload-identity-pools providers create-oidc "github-provider" \
  --location="global" \
  --workload-identity-pool="github-pool" \
  --issuer-uri="https://token.actions.githubusercontent.com" \
  --attribute-mapping="google.subject=assertion.sub,attribute.actor=assertion.actor,attribute.repository=assertion.repository" \
  --attribute-condition="assertion.repository_owner=='YOUR_GITHUB_USERNAME'"

# 4. Create service account (or reuse existing)
gcloud iam service-accounts create github-actions-sa \
  --display-name="GitHub Actions Service Account"

# 5. Grant Vertex AI User role to service account
gcloud projects add-iam-policy-binding YOUR_PROJECT_ID \
  --member="serviceAccount:github-actions-sa@YOUR_PROJECT_ID.iam.gserviceaccount.com" \
  --role="roles/aiplatform.user"

# 6. Allow Workload Identity Pool to impersonate the service account
gcloud iam service-accounts add-iam-policy-binding github-actions-sa@YOUR_PROJECT_ID.iam.gserviceaccount.com \
  --role="roles/iam.workloadIdentityUser" \
  --member="principalSet://iam.googleapis.com/projects/PROJECT_NUMBER/locations/global/workloadIdentityPools/github-pool/attribute.repository/YOUR_GITHUB_USERNAME/YOUR_REPO_NAME"

# 7. Get the Workload Identity Provider resource name (save this!)
gcloud iam workload-identity-pools providers describe "github-provider" \
  --location="global" \
  --workload-identity-pool="github-pool" \
  --format="value(name)"
  ```
---
Then `./test-gemini-wif.yml` was created and tested successfully in CI.
  
Resources:
- https://cloud.google.com/blog/products/identity-security/how-to-authenticate-service-accounts-to-help-keep-applications-secure?authuser=1
- https://google-gemini.github.io/gemini-cli/docs/get-started/authentication.html
- https://medium.com/google-cloud/goodbye-api-keys-gemini-cli-github-actions-with-workload-identity-federation-6d4fae9e936b - Excellent article specifically about your use case!
- https://medium.com/google-cloud/gemini-cli-tutorial-series-part-3-configuration-settings-via-settings-json-and-env-files-669c6ab6fd44
- https://github.com/google-gemini/gemini-cli/blob/main/docs/get-started/authentication.md
  