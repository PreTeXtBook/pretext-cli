# Roadmap

Here is a place for us to explore possible new features and prioritize our work.  All is subject to change.

## Initial release

Get basics working:

* `pretext new` to create basic skeleton of a new book project.  User supplies a title.  No customization beyond this.
* `pretext build html` and `pretext build latex` (or maybe `pretext build pdf`) to use included xsl to generate html or latex from `source/main.ptx`.  No string params, no publisher file, no custom xsl.  No images, no webwork.  Use lxml eliminating need for xsltproc.

## Next steps

Improve features of main functions:

### `pretext new`

* Allow user to provide `outline.xml` that is used to generate more complicated book projects (xi:include-ing chapters and sections).
* Generate publisher file.

### `pretext build`

* Add option to specify publisher file
* Add option to specify arbitrary string param.
* When passed option, build documents that use webwork.

### `pretext build html`

* When passed option, build images using the mbx script.

### Configuration

Save project-based options in a config file for that project.  The script reads global default options (are there any?) then options from local (project) config file, then options from command line.  One command line option is to save command line options to local config file.

Reasonable options to put in this file:

* location of pretext/xsl (for using dev version)
* name/location of publisher file
* custom xsl
* string params
* output location
* name of main ptx file

### Additional functionality

* Validation: `pretext validate` or `pretext check` or the like.  
* Additional build targets: 
  * `pretext build slides`
  * `pretext build epub`
  * `pretext build jupyter`
  * `pretext build worksheets`
  * `pretext build solution-manual`