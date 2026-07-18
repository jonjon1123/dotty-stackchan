# AGENTS.md

## Repo Structure

This repo (`jonjon1123/dotty-stackchan`) is a fork of `BrettKinny/dotty-stackchan`. It
contains a single git submodule at `firmware/` pointing to `jonjon1123/dotty-firmware`.

> **Note:** This is a fork. The primary reference docs are in `README-UPDATED.md`,
> not the original `README.md` from upstream.

### Fork Chain

```
m5stack/StackChan          (original upstream)
       │
BrettKinny/StackChan       (dotty fork — firmware customizations)
       │
jonjon1123/dotty-firmware   (your firmware fork — submodule source)
```

```
BrettKinny/dotty-stackchan  (server-side stack fork)
       │
jonjon1123/dotty-stackchan  (this repo)
```

### Remote Layout

**This repo** (`jonjon1123/dotty-stackchan`):

| Remote   | URL                                                   | Purpose                        |
|----------|-------------------------------------------------------|--------------------------------|
| `origin` | `https://github.com/jonjon1123/dotty-stackchan.git`   | Your fork (push target)        |
| `upstream` | `https://github.com/BrettKinny/dotty-stackchan.git` | Pulls from the dotty stack fork |

**Submodule** (`firmware/` — `jonjon1123/dotty-firmware`):

| Remote     | URL                                                 | Purpose                              |
|------------|-----------------------------------------------------|--------------------------------------|
| `origin`   | `https://github.com/jonjon1123/dotty-firmware.git`  | Your firmware fork (push target)     |
| `fork`     | `https://github.com/BrettKinny/StackChan.git`       | Pulls from the BrettKinny fork       |
| `upstream` | `https://github.com/m5stack/StackChan.git`          | Pulls from the original m5stack repo |

### Submodule Configuration

`.gitmodules` in the parent repo pins the submodule to:
- **URL:** `https://github.com/jonjon1123/dotty-firmware.git`
- **Branch:** `dotty`

The local `.git/config` must match `.gitmodules`. If they drift (e.g. after cloning),
run:

```bash
git submodule sync
```

## Workflow: Pulling Updates Into the Submodule

All commands below are run from the `firmware/` directory.

### Pull from BrettKinny/StackChan (fork updates)

```bash
cd firmware
git fetch fork
git merge fork/dotty
```

### Pull from m5stack/StackChan (upstream updates)

```bash
cd firmware
git fetch upstream
git merge upstream/main
```

### Push updated submodule to your fork

```bash
cd firmware
git push origin dotty
```

### Update the submodule pointer in the parent repo

After pushing the submodule, update the parent repo to point at the new commit:

```bash
cd ..
git add firmware
git commit -m "chore: update firmware submodule"
git push origin main
```

## Workflow: Pulling Updates Into the Parent Repo

```bash
git fetch upstream
git merge upstream/main
git push origin main
```

## Quick Reference

| Task                              | Command                                                  |
|-----------------------------------|----------------------------------------------------------|
| Sync submodule URL after clone    | `git submodule sync`                                     |
| Init submodule after fresh clone  | `git submodule update --init`                            |
| Update submodule to latest remote | `cd firmware && git pull origin dotty`                   |
| Check submodule status            | `git submodule status`                                   |
| List submodule remotes            | `git -C firmware remote -v`                              |
