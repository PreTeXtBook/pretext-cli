# Change Log

All notable changes to the PreTeXt-CLI will be documented in this file (admittedly started rather late in the game).

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

Instructions: Add a subsection under `[UNRELEASED]` for additions, fixes, changes, and removals of features accompanying each PR.  When a release is made, the github action will automatically add the next version number above the unreleased changes with the date of release.

## [UNRELEASED]

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