# Issue 1: Platform Mismatch in Poridhi Cloud

**Problem:**  
The requested image's platform (`linux/arm64/v8`) does not match the detected host platform (`linux/amd64/v3`), and no specific platform was requested.

**Symptom:**  
`socket hang up`

**Solution:**  
Build a multi-platform Docker image on macOS using BuildKit, so the image works on both `linux/arm64` and `linux/amd64`.

### Steps (on macOS):

1. **Enable BuildKit:**

   ```bash
   export DOCKER_BUILDKIT=1
   ```

2. **Build and Push a Multi-Platform Image:**
   ```bash
   docker buildx create --use
   docker buildx build --platform linux/amd64,linux/arm64 -t fahadkabir123/flask-jwt-auth:latest --push .
   ```
   This creates a multi-architecture image and pushes it to Docker Hub.
