# Change Log

All notable changes to the PreTeXt-CLI will be documented in this file (admittedly started rather late in the game).

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

Instructions: Add a subsection under `[Unreleased]` for additions, fixes, changes, and removals of features accompanying each PR.  When a release is made, the github action will automatically add the next version number above the unreleased changes with the date of release.

## [Unreleased]

### Fixed

- Bug causing poor math output inside a sidebyside/stack.

## [2.28.0] - 2025-08-16

Includes updates to core through commit: [bec45fb](https://github.com/PreTeXtBook/pretext/commit/bec45fb595aa6d758e50e7e9eb7185405ada9f0d)

### Added

- New "handout" division, similar to worksheets, but intended for pages you print without exercises.
- `@workspace` can go on most paragraph-level elements in worksheets and handouts.
- Experimental support for improve bibliographies using citeproc.  `pretext generate references` will generate the required xml file in generated assets.
- Experimental support for generating STACK static assets.  `pretext generate stack` will generate the required assets.

### Fixed

- Footnotes inside detached `proof` works better in print conversion.
- Improve autoscroll of table of contents for HTML.

## [2.27.0] - 2025-08-12

Includes updates to core through commit: [132ca23](https://github.com/PreTeXtBook/pretext/commit/132ca234495d16ffbb8ad75fc06375f991000db4)

### Changed

- Legacy themes for HTML will now be automatically replaced with their new equivalents.

### Added

- Codelense trace improvements.

### Fixed

- Bug preventing authored webwork problems in projects from being generated.
- Runestone profile menu now works in mobile view.

## [2.26.0] - 2025-08-11

Includes updates to core through commit: [8b25e5f](https://github.com/PreTeXtBook/pretext/commit/8b25e5f6b8c1b0c8e0a9b2488cdb83cddd6e6ffd)

### Changed

- HTML links no longer produce footnotes with url; LaTeX puts url in parentheses (core).

### Added

- WeBWorK problems can be authored in bare PG (core).

### Fixed

- Bug preventing braille building to work.
- Bug preventing workspace in HTML worksheets when no special worksheet formatting is requested (core).
- Variety of HTML theme improvements (core).


## [2.25.1] - 2025-08-01

Includes updates to core through commit: [f15f9b9](https://github.com/PreTeXtBook/pretext/commit/f15f9b9fee75331d64d0fff4d757c479ef85fcb7)

### Fixed

- Bug in which qrcodes don't generate for video/audio if no interactive or youtube elements exist.

### Changed

- qrcodes for pdf are now generated based on a hash of the elements they point to in addition to the baseurl for the publication file.

## [2.25.0] - 2025-07-26

Includes updates to core through commit: [45be2cf](https://github.com/PreTeXtBook/pretext/commit/45be2cfe85fd54a3e5c03743226919eb1a6b2085)

### Changed

- NEW BEHAVIOR: the `pretext build -g` command will not use cached versions of assets when regenerating.  You can still generate assets and use the cache with `pretext generate`.
- Improve default settings in codespace settings.

## [2.24.0] - 2025-07-21

Includes updates to core through commit: [32262dd](https://github.com/PreTeXtBook/pretext/commit/32262dda4922a4535bcfb10fe1c66b50c51337ac)

### Changed

- Template devcontainer will now use versioned docker image.
- The `pretext upgrade` command will include prefigure and pelican if they are already installed.

### Fixed

- Bug that sometimes stopped `pretext view` from working in a codespace.

## [2.23.1] - 2025-07-14

Includes updates to core through commit: [c750a05](https://github.com/PreTeXtBook/pretext/commit/c750a05a2c35cad67dd269682e1618e3c1eb63dc)

### Fixed

- Better error messages when node version is too low for FITB generation step.
- Github actions now install the correct version of node for FITB generation step.
- Worksheet printing bug cause by top page margin has been fixed.

### Changed

- Better messages when build/generate completes with errors.

## [2.23.0] - 2025-07-11

Includes updates to core through commit: [899648f](https://github.com/PreTeXtBook/pretext/commit/899648f16a2f78760b5d309c98c623d9c63f09e3)

### Added

- Print preview for worksheets now has option to highlight workspace and compare the rendered workspace to the authored height.
- WeBWorK exercises can be generated using a local copy of PG (with the proper setup).

### Changed

- Generating dynamic substitutions now uses node instead of playwright.  Node 22.10 or greater is required.

## [2.22.0] - 2025-07-05

Includes updates to core through commit: [e6f9288](https://github.com/PreTeXtBook/pretext/commit/e6f92889e1e4978f71d7417be410ca379d6e9eff)

### Changed

- Printing worksheets from HTML should work a lot better now.  The "Print preview" page now matches the printed output, and you can toggle between letter and a4.  Worksheets can be authored with or without `<page>` elements and still get good results.

### Fixed

- Publication file in templates had incorrect element for latex cover setting.

## [2.21.0] - 2025-06-27

Includes updates to core through commit: [2bcef90](https://github.com/PreTeXtBook/pretext/commit/2bcef902b5938d357cb72c34a0999fdf922f46d2)

### Changed

- Python version 3.10 or higher is now required (removed support for python 3.8 and 3.9).

### Fixed

- Bug that caused MyOpenMath problems to be downloaded on every build, regardless of whether they were needed.
- Bug which caused error in `pretext view` when the `running_servers` file contained a blank line.

## [2.20.0] - 2025-06-20

Includes updates to core through commit: [1ef97c0](https://github.com/PreTeXtBook/pretext/commit/1ef97c03fda832b25d60d78edfbc729ee3a75683)


### Changed

- Default devcontainer setup now uses a simplified, versioned `pretext-full` docker image.

### Fixed

- Fill-in-the-blank questions do not need dynamic-subs assets for HTML-format builds; now they will no longer be generated.
- Sometimes the `pretext view` command did not work in Codespaces.  Now inactive server instances are removed immediately which should fix this issue.

### Added

- Sometimes something goes wrong with the pretext resources in `~/.ptx`.  You can now run `pretext init --system` to reinstall these resources for the current version.  This will also try to run `npm install` for the css themes.


## [2.19.3] - 2025-06-14

Includes updates to core through commit: [1b65b63](https://github.com/PreTeXtBook/pretext/commit/1b65b63c3a83292c22b46cf1e12795c4dd519cc0)

## [2.19.2] - 2025-06-04

Includes updates to core through commit: [b31d10b](https://github.com/PreTeXtBook/pretext/commit/b31d10bd04eebc7387bb1d55b1e64a603533c3e0)

## [2.19.1] - 2025-05-24

Includes updates to core through commit: [6a4f8ff](https://github.com/PreTeXtBook/pretext/commit/6a4f8ff46a481e01f583f796f6ea7701906a3dc3)

## [2.19.0] - 2025-05-23

Includes updates to core through commit: [2a9f32a](https://github.com/PreTeXtBook/pretext/commit/2a9f32ab41c6329d09961f0b9cd5e05424e61155)

## Added

- You can now build standalone targets as PDF, HTML, or a SCORM archive using `pretext build html -i path/to/ptx/file`.  Output will be placed adjacent to source.
- You can now build standalone targets from within a project (in case you want to build arbitrary files without creating targets for them).  Just add a target with `standalone="yes"` in the manifest.

## [2.18.3] - 2025-05-19

Includes updates to core through commit: [638c52a](https://github.com/PreTeXtBook/pretext/commit/638c52a4f65df4371f9b7f907ff709bf4fe8b076)

## Changed

- Update course template.

## [2.18.2] - 2025-05-16

Includes updates to core through commit: [11011fb](https://github.com/PreTeXtBook/pretext/commit/11011fbbd7e35d3e66063bc421cc86386ff6d748)

## Changed

- Update devcontainer for codespaces with more custom settings and suggested extensions.

## [2.18.1] - 2025-05-13

Includes updates to core through commit: [9be1596](https://github.com/PreTeXtBook/pretext/commit/9be1596d6ecab588c8a7c1a5c437c7785b895f23)

## [2.18.0] - 2025-05-06

Includes updates to core through commit: [1024036](https://github.com/PreTeXtBook/pretext/commit/1024036febe76e48c5f2a997a021cec5c68c97f2)

### Added

- Support for more journals.
- HTML build can now create a SCORM archive for uploading to an LMS.
- Further improvements for portable html builds (fewer auxilary files created).
- New "boulder" theme for minimal single-page HTML builds.
- Optional embed button (for getting `<iframe>` code to put in an LMS).
- Improvements to `program` element.

## Changed

- Improvements to wide elements in CSS themes
- Deprecated "matches" in exercises in favor of "cardsort"
- `Listing`s now use `title`s instead of `caption`s

## [2.17.1] - 2025-04-10

Includes updates to core through commit: [7936f3f](https://github.com/PreTeXtBook/pretext/commit/7936f3fd1595439fe86adc44ea9a4f8045372801)

### Fixed

- Bug preventing some repositories from using `pretext deploy`.

## [2.17.0] - 2025-04-09

Includes updates to core through commit: [2c3fda7](https://github.com/PreTeXtBook/pretext/commit/2c3fda724738cabba04c28378f91a64a72a0e7c2)

### Changed

- The CLI now uses your assembled source in case you use "versions" for checking for some source errors and deciding whether assets must be regenerated.  For example, if you change an asset in a component that is not part of a version, it will not trigger rebuilding all assets.

### Fixed

- Fixed a bug with the denver theme that displayed some tasks with their headings not inline.

## [2.16.1] - 2025-04-08

Includes updates to core through commit: [7017d8f](https://github.com/PreTeXtBook/pretext/commit/7017d8fcc7005984ffc7fad81d0a37062a529a9d)

## [2.16.0] - 2025-04-07

Includes updates to core through commit: [7017d8f](https://github.com/PreTeXtBook/pretext/commit/7017d8fcc7005984ffc7fad81d0a37062a529a9d)

### Addded

- New option for `pretext deploy`.  If you pass `--no-push` then deploy will commit your output to the `gh-pages` branch but not push.  This can be useful for CI/CD workflows or in case deploy encounters an authentication error.

### Changed

- The default devcontainer no longer includes a full LaTeX install.  If you run into trouble generating latex-images or building pdfs, see the README.md file for assistance.
- The default devcontainer no longer includes sagemath.  If you want to build sageplot assets, see the README.md file for assistance.


## [2.15.2] - 2025-03-31

Includes updates to core through commit: [7017d8f](https://github.com/PreTeXtBook/pretext/commit/7017d8fcc7005984ffc7fad81d0a37062a529a9d)

### Fixed

- Bug preventing github actions from completing deploy (internal).


## [2.15.1] - 2025-03-24

Includes updates to core through commit: [7017d8f](https://github.com/PreTeXtBook/pretext/commit/7017d8fcc7005984ffc7fad81d0a37062a529a9d)

### Added

- Portable html builds now embed SVGs directly into the html (so you no longer need to upload them separately).
- Coloraide package added as a dependency (for building custom themes).

## [2.15.0] - 2025-03-15

Includes updates to core through commit: [bd0998c](https://github.com/PreTeXtBook/pretext/commit/bd0998c5663b25a9d2272ebc0e97bea80b66dc05)

### Added

- Portable html: setting `/publication/html/platform/@portable="yes"` will create html output that doesn't rely on local css or js.  Useful when chunking level is set to 0 to get a single html file to upload to an LMS.
- Improved support for journals in the latex conversion.

### Fixed

- Dynamic substitution xml file was not generated on html build correctly; it is now.
- Bug where permalinks sometimes fail to be added if there is a webwork problem on the page.
- Miscellaneous HTML theme improvements.

### Changed

- Improved success feedback message.

## [2.14.0] - 2025-02-26

Includes updates to core through commit: [8f8858c](https://github.com/PreTeXtBook/pretext/commit/8f8858c9deaeeb1057c365aeaca52652abb496bd)

### Changed

- We now package the latest runestone services with the CLI and use the packaged versions in case there is no internet access to download them directly.  This allows builds to go through even if offline.

## [2.13.5] - 2025-02-16

Includes updates to core through commit: [2f6bfae](https://github.com/PreTeXtBook/pretext/commit/2f6bfaedec237e0024772dd1a7486b5559ec53df)

### Fixed

- Improve robustness of `pretext view` command.

## [2.13.4] - 2025-02-15

Includes updates to core through commit: [2f6bfae](https://github.com/PreTeXtBook/pretext/commit/2f6bfaedec237e0024772dd1a7486b5559ec53df)

### Fixed

- Update psutil requirement to 7.0 for consistent server checking with `pretext view`.

## [2.13.3] - 2025-02-14

Includes updates to core through commit: [2f6bfae](https://github.com/PreTeXtBook/pretext/commit/2f6bfaedec237e0024772dd1a7486b5559ec53df)

### Changed

- Allow deployment even if there are un-committed changes to the project folder; issue warning.

### Fixed

- Addressed another bug causing errors on `pretext update`.

## [2.13.2] - 2025-02-11

Includes updates to core through commit: [2f6bfae](https://github.com/PreTeXtBook/pretext/commit/2f6bfaedec237e0024772dd1a7486b5559ec53df)

### Changed

- Added a temporary hack to avoid build failures when not connected to the internet.  This will be reverted in 2.14 in favor of a more robust solution.

## [2.13.1] - 2025-02-11

Includes updates to core through commit: [2f6bfae](https://github.com/PreTeXtBook/pretext/commit/2f6bfaedec237e0024772dd1a7486b5559ec53df)

### Fixed

- Resolved bug with `pretext update`.
- Better warning messages if unable to build css with node.


## [2.13.0] - 2025-02-05

Includes updates to core through commit: [2f6bfae](https://github.com/PreTeXtBook/pretext/commit/2f6bfaedec237e0024772dd1a7486b5559ec53df)

### Added

- Logging is now available when the CLI is used programmatically (as a library).  See [docs/api.md](docs/api.md).

### Changed

- Asset generation of asymptote, latex-image, and sageplot now utilize a *generated-cache* of images (stored in `.cache` in the root of a project, but customizable in `project.ptx`).  This should speed up building and generating assets.

## [2.12.0] - 2025-01-16

Includes updates to core through commit: [3ce0b18](https://github.com/PreTeXtBook/pretext/commit/3ce0b18284473f5adf52cea46374688299b6d643)

### Added

- `pretext update` command will update managed files and the `requirements.txt` file to match current installed version of PreTeXt.

### Changed

- Improved help when deploy fails.
- Managed files (`project.ptx`, `requirements.txt`, etc) are now managed by comparing to stock versions, not by a magic comment at top.
- Only manage git-related files (`.gitignore`, `.devcontainer.json`, `.github/workflows/pretext-cli.yml`) when project is tracked by git.
- Only updates managed files when `pretext update` is run, instead on every run.
- Only check for new pretext version once a day.

### Fixed

- Removed unneeded warnings about pretext projects existing or not when running `pretext upgrade` and `pretext new`.

## [2.11.4] - 2025-01-11

Includes updates to core through commit: [42236bf](https://github.com/PreTeXtBook/pretext/commit/42236bf454d9e3f98bc25f0bb5186029710f17f7)

### Fixed

- Bug with `pretext view`.

## [2.11.3] - 2025-01-06

Includes updates to core through commit: [42236bf](https://github.com/PreTeXtBook/pretext/commit/42236bf454d9e3f98bc25f0bb5186029710f17f7)

## [2.11.2] - 2024-12-28

Includes updates to core through commit: [3c662c9](https://github.com/PreTeXtBook/pretext/commit/3c662c9fc70c6fa49c031c44ffaebcfbf61ce2f1)

### Fixed

- Improved codespace view command (now respects already running servers).
- CSS fixes for logo and references from core.

## [2.11.1] - 2024-12-25

Includes updates to core through commit: [e4edfd0](https://github.com/PreTeXtBook/pretext/commit/e4edfd0fe052d9dd91404667a42ff1c0932d114b)

### Fixed

- `pretext view` bug where a process is terminated abnormally

## [2.11.0] - 2024-12-24

Includes updates to core through commit: [e4edfd0](https://github.com/PreTeXtBook/pretext/commit/e4edfd0fe052d9dd91404667a42ff1c0932d114b)

### Added

- New and improved css style options.  See PreTeXt documentation.
- `pretext upgrade` command will run `pip install --upgrade pretext` using the same python you are running pretext from, for smoother upgrades.

### Changed

- `pretext view` now reuses the current local server correctly, and starts different local servers for different projects.  This allows you to correctly view multiple projects at the same time.

## [2.10.1] - 2024-12-10

Includes updates to core through commit: [e532f63](https://github.com/PreTeXtBook/pretext/commit/e532f6357afb849df2b54d10aef504ac88e4b271)


## [2.10.0] - 2024-12-06

### Added

- Support for building stand-alone documents without adding the source to the manifest.
- Support for upcoming html themes, including `pretext build --theme` to refresh theme without rebuilding entire project.

## [2.9.2] - 2024-11-22

### Fixed

- prefigure graphics were not not being recognized.

## [2.9.1] - 2024-11-09

### Changed

- prefigure dependency is now an optional install.  To get it, install pretext with `pip install pretext[prefigure]`.

## [2.9.0] - 2024-11-07

### Added

- Support for generating prefigure graphics.
- Always checks whether there is a new version of the CLI available.

## [2.8.2] - 2024-11-05

### Fixed

- Further video id bug.

## [2.8.1] - 2024-10-31

### Fixed

- Bug: could not use custom XSL on windows without special permissions
- Bug: Runestone issue "Failed to evaluate the AVT of attribute 'data-video-divid'"

## [2.8.0] - 2024-10-18

### Added

- From core: publication option to control latex style file.
- From core: default programming language can be set in `<docinfo>`

### Changed

- From core: `<bibinfo>` container for bibliographic information previous held in `<titlepage>` and `<colophon>`.
- Improved publication file template.

## [2.7.1] - 2024-10-03

### Fixed

- Bug: temporary directories from core not deleted on builds.

## [2.7.0] - 2024-09-24

### Added

- Support for reveal.js slides via `format="revealjs"`.
- Support for custom xsl that imports core xsl via `../xsl/pretext-[type].xsl`

### Fixed

- Bug preventing the extraction of webwork sets.

### Updated

- Github action will test build on older versions listed in requirements.
- Bumped `lxml` to at least 5.3 and `psutils` to at least 6.0.

## [2.6.2] - 2024-08-21

### Updated

- Newest version of core pretext.

## [2.6.1] - 2024-08-10

### Fixed

- `pretext view` should now work even if a previous view process did not exit properly.

## [2.6.0] - 2024-07-18

### Changed

- Updated the process for generating latex-image to use pyMuPDF instead of pdf2svg

### Fixed

- Only generate myopenmath problems when actually needed.

## [2.5.2] - 2024-07-17

### Fixed

- Bug with html build for source with version controlled components with duplicate ids.

## [2.5.1] - 2024-07-16

### Fixed

- For compatibility with Runestone you must install pretext with pip install pretext[homepage] in order to get the landing page features.

## [2.5.0] - 2024-07-15

### Added

- Automatically build a landing page for a project when deploying multiple targets.
- New (optional) github action workflows for publishing/deploying sites.
- Static versions of problems for MyOpenMath can now be downloaded using the CLI.  Build/generate for print as usual to get these.
- Support of mermaid diagrams.

### Fixed

- Improved `pretext import` command to handle modular latex files better.
- Turned off image conversions for `pretext import`.
- Always stage to a clean stage directory for `pretext deploy`.
- Improved output messages for info and error messages.

### Incorporated improvements from 'core' PreTeXt

- Parsons problems can have partially ordered solutions.
- Fill In The Blank problems improvements
- Improved MyOpenMath support
- Support "circular" cases for proofs (TFAE, eg)

## [2.4.1] - 2024-05-18

### Fixed

- Improved `pretext view` for inside codespaces.

## [2.4.0] - 2024-05-02

### Added

- `pretext import` command.  Pass a path to a `.tex` file and it will use PlasTeX to do its best to convert the latex to pretext.

## [2.3.10] - 2024-04-10

## [2.3.9] - 2024-03-02

### Fixed

- Temporary hack fixes `pretext view` issues in codespaces.

### Changed

- `pretext view` now opens browser sooner when you are not using codespaces.

## [2.3.8] - 2024-02-25

### Added

- Added this CHANGELOG.md file to track future changes to the PreTeXt-CLI.

### Changed

- Generating webwork will now continue in most cases where a single exercise is invalid, still creating a representations file.
- Improve error message when webwork-representations file fails to build.
