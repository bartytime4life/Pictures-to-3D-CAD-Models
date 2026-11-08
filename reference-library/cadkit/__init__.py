"""cadkit: standard-library helpers for the Pictures to printable CAD handbook.

The modules implement the handbook's worked arithmetic and checks so that the
examples, command line, tests, and the browser calculators agree:

- ``cadkit.calc``        scale, uncertainty, tessellation, depth, camera, labels,
                          coatings, gears, wind power, clearance series, units
- ``cadkit.homography``  normalized DLT homography fit, residuals, local scale
- ``cadkit.stl``         ASCII/binary STL reader and mesh checks
- ``cadkit.params``      design-parameter register (CSV) loader
- ``cadkit.scad``        OpenSCAD discovery and rendering with ``-D`` overrides
- ``cadkit.project``     project-folder scaffolding from the handbook templates
- ``cadkit.routes``      route finder shared with the HTML Toolkit (assets/data/routes.json)

Run ``python3 -m cadkit --help`` from the ``reference-library`` directory.
Every result is arithmetic on stated inputs; none of it is a measurement.
"""

__version__ = "1.0.0"

__all__ = ["calc", "homography", "stl", "params", "scad", "project", "routes", "__version__"]
