# Change Log

All notable changes to the PreTeXt-CLI will be documented in this file (admittedly started rather late in the game).

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

Instructions: Add a subsection under `[UNRELEASED]` for additions, fixes, changes, and removals of features accompanying each PR.  When a release is made, the github action will automatically add the next version number above the unreleased changes with the date of release.

## [UNRELEASED]

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