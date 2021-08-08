# Versioning

We use the following versioning design compatible with
<https://www.python.org/dev/peps/pep-0440/>.

- Always zero-index.
- Versions are tracked in `pretext/static/VERSION` (to be imported by both `setup.py` and the CLI
  itself for display)
- We use `[Major].[Minor].[BugFix]` versioning, whose history is 
  kept in the `main` branch, with features added via pull requests.
- Commits that aren't released on PyPI will have a `.devN` suffix.
- When `.devN` is deemed ready for release, a single commit chainging this version to `.rcN` is made,
  and this is built and released on PyPI. The next commit updates to `.dev(N+1)`.
- If the `rcN` release is deemed final, a new commit removes `.dev(N+1)` and this final release is
  released on PyPI.
- The final commit of a particular release candidate or public release is `git tag`'d as that version
  reflects what's on PyPI.
- The commit following each release bumps the version to `+0.0.1` the previous version with
  `.dev0` set.
- Whenever deemed appropriate, the development version may be upgraded to the next Minor release instead.
