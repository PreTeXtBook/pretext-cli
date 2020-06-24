# Versioning

We use the following versioning design compatible with
<https://www.python.org/dev/peps/pep-0440/>.

- Always zero-index.
- Versions are tracked in `pretext/static/VERSION` (to be imported by both `setup.py` and the CLI itself for display)
- We use `[Major].[Minor]` versioning (with implied `.0` bugfix suffix), whose history is kept in the `master` branch.
  - If we discover we need to bugfix a minor release, we create a branch `[Major].[Minor].(N+1)` to fix things and publish the new version, and eventually merge these changes back into `master` for release in `[Major].[Minor+1]`.
- Each version always has at least one release candidate `rc0` for preview. If `rcN` reveals more work and a new preview is needed, `rc(N+1)` is developed. Otherwise a new commit removing the `rcN` is made (this should be the only change from `rcN` to the public release).
- The final commit of a particular release candidate or public release is `git tag`'d as that version and should reflect what's on PyPI.

An illustration of our version history looks something like this:

```
0.0rc0 (untagged) (several unpublished commits)
0.0rc0 (tagged) (one commit, published, further work needed)
0.0rc1 (untagged) (several unpublished commits)
0.0rc1 (tagged) (one commit, published, no further work needed)
0.0 (tagged) (one commit, published)
0.1rc0 (untagged) (several unpublished commits)
    0.0.1rc0 (untagged) (branch from 0.0)
    0.0.1rc0 (tagged)
    0.0.1 (tagged) (merged back into master as part of in-development 0.1rc0)
0.1rc0 (tagged)
```