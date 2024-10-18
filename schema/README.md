This directory will contain the RelaxNG schema for the project manifest `project.ptx`.  

There are two versions, a compact syntax (`.rnc`) and XML (`.rng`).  Edits should be made to the `.rnc` file which can then be converted to the `.rng` version using [trang](https://github.com/relaxng/jing-trang) via
```
> trang project-ptx.rnc project-ptx.rng
```

You can then use [jing](https://github.com/relaxng/jing-trang) to test
whether a `project.ptx` file conforms to the schema.
```
> jing project-ptx.rng path/to/project.ptx
```

If you are running these commands directly from Java `.jar` files, you will
instead run
```
> java -jar path/to/jing.jar [...other arguments...]
```