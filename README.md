# GoRelay

GoFile → SourceForge relay, fully automated via GitHub Actions.

## Use it

1. Fork this repo.
2. Add secrets. In your fork: **Settings → Secrets and variables → Actions →
   New repository secret**:
   - `SF_SSH_KEY` (required) — passphrase-less SourceForge SSH **private** key
     (whole key, multiline, with BEGIN/END lines). Public half goes to your
     SourceForge account (Account Services → SSH Keys).
     **Note:** It must be an SSH private key, not SourceForge password.
   - `GF_TOKEN` (optional) — only if you hit GoFile download limits
     (recommended for files 4GB+).
3. **Actions → GoFile to SourceForge relay → Run workflow** with:

| Input | Default |
|---|---|
| `gofile_url` | — |
| `gofile_password` | empty |
| `sf_username` | `topexguy` |
| `sf_project` | `skyroms` |
| `sf_remote_path` | project root |

Flow: install `uv` → download from GoFile → verify md5 vs GoFile API →
`scp` to `/home/frs/project/<sf_project>/<sf_remote_path>`.

## Local use

```sh
uv run gofile-downloader.py https://gofile.io/d/contentid [password]
uv run verify-gofile.py https://gofile.io/d/contentid [password]
```

Env vars (`GF_TOKEN`, `GF_DOWNLOAD_DIR`, `GF_INTERACTIVE`, ...) can go in a `.env` file.

---

Fork of [ltsdw/gofile-downloader](https://github.com/ltsdw/gofile-downloader).
