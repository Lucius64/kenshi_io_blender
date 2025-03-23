# Kenshi Blender Plugin

:japan:[Japanese](README-ja.md)

This is a plugin to import and export Kenshi 3D assets to Blender.


## Requirements

- Windows
- Blender 2.79 or later


## Features
It has the following operators:

- Import mesh
- Export mesh
- Import skeleton
- Export skeleton
- Import collider (xml file)
- Export collider (xml file)


## Description

- [Installing/Uninstalling](Installation_extension.md)
    - [Legacy Add-ons](Installation.md)
- [Option description](Option_description.md)


## Improvements

### Performance

Performance has been improved and now runs faster.

For reference, the processing time of "human_male.mesh" and "male_skeleton.skeleton" in Blender 2.93 is as follows.

| conditions | import | export |
| --- | --------- | ----------- |
| mesh only | about 5.5s → 0.233s | about 7.2s → 0.074s |
| including skeleton | about 24.5s → 0.254s | about 7.3s → 0.075s |
| including animation| about 34.5s → 0.861s | about 50s → 0.925s |


### Bug fixes

Fixed the following bugs that exist in the official version.
- Memory leak when importing meshes and skeletons
- import operator undo not working
- Crash during UNDO on some versions due to the above
- Collider export has many bugs
- Unable to generate convex hull collision in game
- Missing some keyframes due to #INF and #IND when importing vanilla male animation
- Vertex colors for alpha channel cannot be imported correctly since official version 0.9.0
- Since the official version 0.9.0, importing meshes without UV maps and with vertex colors fails
- Smooth shading is not applied to imported meshes since official version 0.9.0
- When exporting multiple animations, bones without keyframes inherit poses from the previous animation
- Exporting a model with non-ASCII characters in object names or material names with Blender 2.92 or lower fails to import for users in different regions or Blender 2.93 or higher


## NOTICE

[NOTICE](NOTICE.md)
