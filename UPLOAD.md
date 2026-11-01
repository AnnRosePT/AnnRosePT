# Uploading your profile README

GitHub shows a profile README from a public repository whose name exactly matches your username.

## 1. Create the profile repository
1. Go to https://github.com/new
2. Repository name: `AnnRosePT`
3. Set it to **Public**. Leave "Add a README" unticked.
4. Click **Create repository**.

## 2. Upload the files
**Option A: in the browser (easiest)**
1. Unzip `github-profile.zip` on your computer.
2. In the new repo, click **uploading an existing file**.
3. Open the unzipped `github-profile` folder, select everything inside it (`README.md`, `assets`, `scripts`, `.github`, `UPLOAD.md`) and drag it into the page.
   - `.github` is a hidden folder. On Windows, enable View → Hidden items; on macOS press Cmd+Shift+. in Finder.
   - If the browser skips the `.github` folder, create it afterwards: **Add file → Create new file**, name it `.github/workflows/stats.yml`, and paste the contents of that file.
4. Commit message: `Add profile README`. Click **Commit changes**.

**Option B: with Git**
```bash
cd github-profile
git init -b main
git add .
git commit -m "Add profile README"
git remote add origin https://github.com/AnnRosePT/AnnRosePT.git
git push -u origin main
```

## 3. Let the stats workflow save its cards
1. In the repo: **Settings → Actions → General → Workflow permissions**.
2. Select **Read and write permissions** and click **Save**.
3. Go to **Actions → Update profile stats → Run workflow**.
4. After about a minute, `assets/stats/overview.svg` and `assets/stats/languages.svg` are refreshed with your live numbers. They then update daily on their own.

The cards that ship in the zip are placeholders (some counts show 0) until that first run.

## 4. Check it
Open https://github.com/AnnRosePT and you should see the purple banner at the top.

## Editing later
- Text and sections: edit `README.md` directly on GitHub (pencil icon).
- Banner or project cards: replace the PNGs in `assets/` keeping the same file names.
