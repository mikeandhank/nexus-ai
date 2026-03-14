# Deploy Instructions

## Option 1: Netlify (Recommended)
1. Go to https://app.netlify.com/drop
2. Drag & drop this folder onto the page
3. Done in ~10 seconds

## Option 2: Cloudflare Pages
1. Go to https://pages.dev
2. Connect GitHub or drag & drop folder
3. Instant deploy

## Option 3: GitHub Pages
1. Create new repo on GitHub
2. `git remote add origin <repo-url>`
3. `git push -u origin main`
4. Enable Pages in repo settings

## Option 4: Vercel
1. `npm i -g vercel`
2. `vercel --prod`

---

## Pre-Deploy Checklist
- [ ] Replace `YOUR_FORM_ID` in index.html with actual Google Form
- [ ] Test form submission works
- [ ] Verify pricing tiers
- [ ] Check mobile responsiveness