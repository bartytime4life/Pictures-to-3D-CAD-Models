// Local CAD workspace export. Units mm. See parameters.csv for evidence.
// DIAMETRAL CLEARANCE COUPON (handbook section 15). Units: mm.
// A strip of through-holes, each larger than a nominal pin by a test clearance.
// Diametral clearance = hole diameter - pin diameter; radial clearance is half.
// These are EXAMPLE TEST SETTINGS, not recommended fits or claims about any printer.
// Print in the intended material, orientation, layer settings, and cooling;
// test with the real mating pin, in the finished (primed/painted) state.
//
// Override any value from the command line, for example:
//   openscad -o coupon.stl -D pin_diameter=3 -D 'label_mode="engrave"' clearance-coupon.scad
//
// The hole nearest the corner notch (x = 0 end) has the smallest clearance.

pin_diameter=5.0;          // measured diameter of the real mating pin
clearance_start=0.1;    // first diametral clearance
clearance_step=0.1;     // increment between holes
clearance_count=5.0;       // number of holes
thickness=4.0;             // coupon thickness (Z)
min_wall=2.0;              // minimum material between holes and to the long edges
end_wall=3.0;              // material from the outer holes to the ends (>= min_wall)
chord_error=0.02;        // maximum radial deviation of each polygonal hole
compensate_polygon=true; // place polygon flats (not vertices) on the hole diameter
label_mode="none";       // "none", "engrave", or "emboss" clearance labels
label_size = 3;            // text height
label_depth = 0.6;         // engrave depth or emboss height
index_notch=true;        // corner chamfer marking the smallest-clearance end
notch_size=2.0;            // chamfer leg length

function clearance(i) = clearance_start + i * clearance_step;
function hole_d(i) = pin_diameter + clearance(i);
// Segment count from the tessellation formula n >= pi / acos(1 - e / r)
// (OpenSCAD acos returns degrees, so pi becomes 180).
function segments(d) = max(16, ceil(180 / acos(1 - chord_error / (d / 2))));
// A polygon with vertices on radius R has flats at R cos(180 / n). Enlarging R
// by 1 / cos(180 / n) makes the largest pin that passes equal the hole diameter.
function poly_r(d) = (compensate_polygon ? 1 / cos(180 / segments(d)) : 1) * d / 2;

holes = [for (i = [0 : clearance_count - 1]) hole_d(i)];
max_r = max([for (d = holes) poly_r(d)]);
pitch = 2 * max_r + min_wall;
hole_band = 2 * (min_wall + max_r);
label_band = label_mode == "none" ? 0 : label_size + min_wall;
coupon_length = 2 * (end_wall + max_r) + (clearance_count - 1) * pitch;
coupon_width = hole_band + label_band;
hole_y = min_wall + max_r;
function hole_x(i) = end_wall + max_r + i * pitch;

assert(pin_diameter > 0 && thickness > 0 && min_wall > 0, "sizes must be positive");
assert(clearance_count >= 1 && clearance_count == floor(clearance_count), "clearance_count must be a positive integer");
assert(min(holes) > 0, "every hole diameter must be positive");
assert(end_wall >= min_wall, "end_wall must be at least min_wall");
assert(chord_error > 0 && chord_error < min(holes) / 2, "chord_error must be between 0 and the smallest hole radius");
assert(label_mode == "none" || label_mode == "engrave" || label_mode == "emboss", "label_mode must be none, engrave, or emboss");
assert(label_mode != "engrave" || label_depth < thickness, "engrave depth must be less than thickness");
// The notch edge (x + y = notch_size) must stay at least min_wall from hole 0.
assert(!index_notch || (hole_x(0) + hole_y - notch_size) / sqrt(2) - max_r >= min_wall,
       "notch_size is too large for the first hole");

module labels(height) {
    for (i = [0 : clearance_count - 1])
        translate([hole_x(i), hole_band + label_size / 2, 0])
            linear_extrude(height = height)
                text(str(clearance(i)), size = label_size, halign = "center", valign = "center");
}

module body() {
    difference() {
        cube([coupon_length, coupon_width, thickness]);
        for (i = [0 : clearance_count - 1])
            translate([hole_x(i), hole_y, -0.1])
                cylinder(h = thickness + 0.2, r = poly_r(holes[i]), $fn = segments(holes[i]));
        if (index_notch)
            translate([0, 0, -0.1])
                linear_extrude(height = thickness + 0.2)
                    polygon([[-0.1, -0.1], [notch_size + 0.1, -0.1], [-0.1, notch_size + 0.1]]);
        if (label_mode == "engrave")
            translate([0, 0, thickness - label_depth]) labels(label_depth + 0.1);
    }
}

if (label_mode == "emboss") {
    union() {
        body();
        translate([0, 0, thickness - 0.01]) labels(label_depth + 0.01);
    }
} else {
    body();
}

echo(str("COUPON length=", coupon_length, " width=", coupon_width, " pitch=", pitch,
         " holes=", holes, " segments=", [for (d = holes) segments(d)]));
