# Demo Course

This is an example of how you could set up a "course" in PreTeXt.

## Instructions

Build the entire course with:

```bash
pretext build web
```

and then view it with 

```bash
pretext view
```

If you want to build just a single activity, say the "Magic Beans" activity, run:

```bash
pretext build ./source/activities/magic-beans.ptx
```

This will create a pdf inside the `source/activities` directory.

Another thing to try:

```bash
pretext build web -i ./source/main-no-syllabus.ptx
```

Note that there is a `web` target in `project.ptx` but it builds from `main.ptx` not `main-no-syllabus.ptx`.  So using the `-i` flag, you can override the input file but still use the settings for an existing target.

### How this is done

Look at the source files, in particular `source/acitivies.ptx` and `source/activities/magic-beans.ptx` to see how the activities are included in the main document and can also build on their own.

The use of `xpointer="/1/1/1"` is a little mysterious; we could have also used `xpoint="Activity-magic-beans"` to refer to the activity by its `xml:id`, although this would require us changing that for each included activity.

