# Free code signing for the Windows flasher (SignPath Foundation)

Unsigned `.exe` files are blocked by Windows Smart App Control and warned about by SmartScreen. SignPath Foundation signs
open-source projects for free with a certificate issued to "SignPath Foundation" (so that is the publisher name Windows
shows). Conditions (signpath.org/terms): OSI-approved licence, no proprietary code, actively maintained, already released,
documented, and you only sign your own project's binaries, built by CI.

## One-time setup

1. Make the repository **public** (after the Play Store launch).
2. Fill in `desktop-flasher/NOTICE.md` / README so the project's purpose is documented, and publish a first (unsigned)
   release: run the **Desktop flasher** workflow (Actions tab) or push a tag `flasher-v1.0.0`, attach the files to a GitHub release.
3. Apply at https://signpath.org/apply (project name DotGlow Flasher, repository URL, licence GPL-2.0-or-later, download page).
   Turn on two-factor login for everyone who can release.
4. After approval, in SignPath create the project `dotglow-flasher` and the signing policy `release-signing`, and use
   `.signpath/artifact-configuration.xml` as the artifact configuration. Create an API token (CI user).
5. In the GitHub repository: secret `SIGNPATH_API_TOKEN`, variables `SIGNPATH_ORGANIZATION_ID` and `SIGNPATH_ENABLED=true`.
6. Run the workflow again: the artifact `DotGlowFlasher-signed` has the signed files. Attach them to the release.

## Good to know

- A new signature may still show a SmartScreen notice until enough people have downloaded the file; Smart App Control
  accepts files signed by a trusted certificate.
- Sign only builds from this repository's CI; never sign files built on a personal PC.
