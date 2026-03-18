# GitHub Actions Deployment Setup

## Overview
This workflow automatically deploys NexusOS to your server whenever code is pushed to `main`.

## Required Secrets

Configure these in your GitHub repository settings:

1. **SSH_PRIVATE_KEY**
   - Private key that can SSH to your server
   - Generate with: `ssh-keygen -t ed25519 -C "github-deploy"`
   - Add the PUBLIC key to your server's `~/.ssh/authorized_keys`

2. **SERVER_HOST**
   - `187.124.150.225`

3. **SERVER_USER**
   - `root` (or `admin` depending on your setup)

## Setup Steps

### 1. Generate SSH Key (on your local machine)
```bash
ssh-keygen -t ed25519 -C "github-deploy"
# Save to ~/.ssh/github_deploy
```

### 2. Add Public Key to Server
Copy the contents of `~/.ssh/github_deploy.pub` and add to your server:
```bash
# In server console:
echo "PASTE_PUBLIC_KEY_HERE" >> ~/.ssh/authorized_keys
```

### 3. Add Secrets to GitHub
1. Go to: https://github.com/mikeandhank/nexus-ai/settings/secrets/actions
2. Add:
   - `SSH_PRIVATE_KEY`: Contents of `~/.ssh/github_deploy` (the PRIVATE key)
   - `SERVER_HOST`: `187.124.150.225`
   - `SERVER_USER`: `root`

### 4. Test
Push any change to `main` and watch the deploy happen automatically!

## Manual Deploy
You can also trigger manually from GitHub:
Actions → Deploy to Production → Run workflow
# trigger deploy
