// SYNTHETIC TEACHING EXAMPLE: not derived from a real photograph.
// Units: mm. No strength, machine fit, or physical print qualification.
// Preview/render in OpenSCAD; export after reviewing the dimensions.
// Values below are defaults. examples/build_plate.py overrides them with
// openscad -D from plate-parameters.csv, the single parameter source.
plate_length = 60;
plate_width = 30;
plate_thickness = 4;
hole_diameter = 5;
hole_spacing = 40;
chord_error = 0.02;
radius = hole_diameter / 2;
segments = max(16, ceil(180 / acos(1 - chord_error / radius)));
assert(plate_length > 0 && plate_width > 0 && plate_thickness > 0);
assert(hole_diameter > 0 && hole_spacing > 0);
assert(hole_spacing + hole_diameter < plate_length);
assert(hole_diameter < plate_width);
assert(chord_error > 0 && chord_error < radius);
difference() {
    translate([-plate_length/2, -plate_width/2, 0])
        cube([plate_length, plate_width, plate_thickness]);
    for (x = [-hole_spacing/2, hole_spacing/2])
        translate([x, 0, -0.1])
            cylinder(h=plate_thickness+0.2, d=hole_diameter, $fn=segments);
}
