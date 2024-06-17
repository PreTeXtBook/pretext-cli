# Creating a landing page for your project

**Note**: The following documentation is aspirational.  Not all features are currently implemented.

Often you will want to host multiple versions and formats of your project on your webpage for the book.  The following describes how you can accomplish this.

## Four Options for Deploying your Project

When running `pretext deploy`, you can get four different resutls.

1. Deploy a single target (the default `web` target) at the root of your github pages site.  This is the default behavior. 
1. Deploy one or more targets with a bare-bones landing page that is automatically generated for you.  To get this option, include a `@deploy-dir` attribute for each target you want hosted, with a value that is the relative path to where on the website the target should live.  You should not have a `site` folder in your project directory (if you do, rename it something like `_site` so it is ignored).
1. Deploy one or more targets with a static landing page (or multiple pages) that you create yourself and store in the `sites` directory.  Each project that should be deployed must have a `@deploy-dir` attribute.  You must have a `sites` directory, and it should **not** have a `pelicanconf.py` file present. 
1. Deploy one or more targets with a landing page (or multiple pages) that pretext will generate for you using [pelican](https://getpelican.com/). Set up your `sites` directory following the pelican documentation, which means it will include the main configuration file, `pelicanconf.py`.

