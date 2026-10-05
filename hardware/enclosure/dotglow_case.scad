// DotGlow case "Lean": ESP32-S3 DevKitC-1 + MAX7219 4-in-1 (8x32), smoked acrylic front, leaning face,
// built-in pedestal, open back with a removable plate (screws or snap) carrying a DC jack.
// Parametric OpenSCAD 2021+. Render one part at a time:
//   openscad -o dotglow-shell.stl   -D 'part="shell"'   dotglow_case.scad   (print front face down)
//   openscad -o dotglow-back.stl    -D 'part="back"'    dotglow_case.scad   (print outside face down)
//   openscad -o dotglow-testfit.stl -D 'part="testfit"' dotglow_case.scad   (quick fit check of acrylic + display)
// part="assembly" shows the finished clock on the desk (preview).
//
// Face coordinates (all parts are built in them): u = across the face (+u is the LEFT side seen from the front),
// v = up along the face, w = depth into the case (0 = front face). The shell STL comes out front-face-down.

part = "assembly";      // shell | back | testfit | assembly

/* [Look] */
lean      = 15;         // face leans back (degrees). 10-20 for a desk; 30 for a low shelf (taller pedestal)
ped_inset = 16;         // pedestal is this much narrower than the case on each side ("floating" look)
show_acrylic = false;   // preview only

/* [Options] */
usb_c     = true;       // slot in the right side for the ESP32's USB-C ports (flashing / USB power)
dc_jack   = "pcb";      // "pcb" (DC-005: glued into a cradle, wires soldered) | "panel" (threaded jack + nut) | "none"
board_mount = "cradle"; // ESP32 on the back plate: "cradle" (guides + snap hook, tape optional) | "tape" (ridge + foam tape)
back_fix  = "screw";    // "screw" (4 x M3) | "snap" (push-fit clips, no screws)
button    = "tactile12";// "tactile12" (12x12 switch + its round cap, on a small perfboard) | "panel" | "none"
ldr       = true;       // 5 mm LDR hole, front left (auto brightness)

/* [Parts: measure these] */
modules   = 4;
disp_w    = 32 * modules;
disp_h    = 32;
matrix_h  = 8.2;        // front of the LEDs to the front of the display PCB
disp_pcb  = 1.6;
disp_back = 3.5;        // parts on the back of the display PCB
hdr_side  = 16;         // room at each end for the pin headers + Dupont plugs

board_l   = 70;         // ESP32-S3 DevKitC-1
board_w   = 25.6;
board_pcb = 1.6;
board_top = 3.5;
dupont    = 16;         // pins + Dupont plugs under the board (8 if you solder wires)
usb_w     = 24;
usb_h     = 5;

acr_t      = 2.0;       // smoked acrylic. 0 = printed 0.6 mm front skin instead
acr_margin = 2;

dc_body   = [9.0, 11.0, 14.2]; // DC-005 body: width, height (pin side down), length (plug direction)
dc_axis   = 6.5;        // DC-005: plug axis height above the body's pin side
dc_fit    = 0.2;        // gap around the body for super glue
dc_plug_d = 6.6;        // hole for the 5.5 mm plug barrel
dc_boss_d = 11.5;       // counterbore for the plug's insulator, so the barrel goes fully in
dc_panel_d = 8.2;       // threaded panel jack hole

tact_cap_d   = 12.6;    // round cap of the 12x12 switch
tact_stack   = 12.5;    // perfboard top to top of the cap
tact_proud   = 1.5;     // cap sticks out this much
perf         = [24, 20];// perfboard: across x along the depth
panel_btn_d  = 7.2;     // panel push button

/* [Case] */
wall    = 2.4;
front   = 1.6;
back_t  = 2.4;
tol     = 0.3;
skin    = 0.6;
screw_d = 2.6;          // M3 thread-forming. 4.0 for M3 heat-set inserts
radius  = 4;
chamfer = 1.2;

$fn = 48;

// ---------- derived (face coordinates) ----------
inner_w = disp_w + 2 * hdr_side;
inner_h = max(disp_h + 2 * acr_margin, board_w) + 2 * tol;
outer_w = inner_w + 2 * wall;
outer_h = inner_h + 2 * wall;

z_matrix   = front + acr_t;
z_disp_pcb = z_matrix + matrix_h;
z_disp_bk  = z_disp_pcb + disp_pcb;
z_board_tp = z_disp_bk + disp_back + 1.5 + board_top;
z_board_bt = z_board_tp + board_pcb;
depth_in   = z_board_bt + dupont;                 // open back of the shell
depth      = depth_in + back_t;

RIGHT = -1; LEFT = 1;                             // sides seen from the front
board_end = RIGHT * (inner_w / 2 - 0.5);          // USB-C end against the right wall
board_mid = board_end - RIGHT * board_l / 2;
board_far = board_end - RIGHT * board_l;

boss_r = 3.2;
boss_u = inner_w / 2 - 3;
boss_v = inner_h / 2 - 1.8;
boss_w0 = z_board_bt + 2;

ldr_u  = LEFT * (disp_w / 2 + hdr_side / 2);
btn_u  = LEFT * (disp_w / 2 - 14);
perf_top = outer_h / 2 - (tact_stack - tact_proud);   // perfboard top surface (v)
perf_w0  = depth_in - perf[1] - 0.5;
btn_w    = button == "tactile12" ? perf_w0 + perf[1] / 2 + 0.5 : z_board_tp + 8;
rail_end = depth_in - 5;

posts_u  = [RIGHT * (disp_w / 2 - 2), RIGHT * 25, LEFT * 10, LEFT * 32];
post_v   = disp_h / 2 - 1.4;
dc_pos   = [LEFT * 45, -4];
snap_w   = 2.5;          // snap bump distance from the back edge

// placement on the desk: face bottom edge at y = 0, pedestal raises it to ped_h
s = sin(lean); c = cos(lean);
ped_h = max(10, depth * s + 4);
ty = outer_h / 2 * s;
tz = ped_h + outer_h / 2 * c;
R = [[-1, 0, 0, 0], [0, s, c, 0], [0, c, -s, 0], [0, 0, 0, 1]];   // face -> world rotation (its own inverse)
module to_world()   translate([0, ty, tz]) multmatrix(R) children();
module from_world() multmatrix(R) translate([0, -ty, -tz]) children();

module rrect(w, h, r) { offset(r) square([w - 2 * r, h - 2 * r], center = true); }
module cbox(w, h, d, r, ch) hull() {               // rounded box with a chamfered front edge
    linear_extrude(0.01) rrect(w - 2 * ch, h - 2 * ch, max(0.5, r - ch));
    translate([0, 0, ch]) linear_extrude(d - ch) rrect(w, h, r);
}

// ---------- shell ----------
module pedestal() {
    v_low = -tz / c - 4;                         // reaches below the desk, cut flat later
    v_top = -outer_h / 2 + wall / 2;
    translate([0, (v_low + v_top) / 2, 0]) cbox(outer_w - 2 * ped_inset, v_top - v_low, depth_in, radius, chamfer);
}

module shell_body() {
    difference() {
        union() {
            difference() {
                cbox(outer_w, outer_h, depth_in, radius, chamfer);
                translate([0, 0, front]) linear_extrude(depth_in) rrect(inner_w, inner_h, 1);
            }
            if (acr_t > 0)
                for (sx = [-1, 1]) translate([sx * (disp_w / 2 + acr_margin + tol + 0.8), 0, front + acr_t / 2])
                    cube([1.6, inner_h, acr_t], center = true);
            translate([0, 0, z_matrix]) linear_extrude(matrix_h - 1.5) difference() {
                rrect(disp_w + 2 * tol + 3.2, inner_h, 0.5);
                square([disp_w + 2 * tol, disp_h + 2 * tol], center = true);
            }
            if (back_fix == "screw")
                for (su = [-1, 1], sv = [-1, 1]) hull() {
                    translate([su * boss_u, sv * boss_v, boss_w0]) cylinder(r = boss_r, h = depth_in - boss_w0);
                    translate([su * boss_u - boss_r, sv > 0 ? inner_h / 2 - 0.1 : -inner_h / 2 - 0.1, boss_w0 - 4])
                        cube([2 * boss_r, 0.2, depth_in - boss_w0 + 4]);
                }
            if (ldr) translate([ldr_u, 0, front]) cylinder(d = 5.2 + 2.4, h = 3);
            if (button == "tactile12")                                  // rails: the perfboard slides in from the back
                for (su = [-1, 1]) translate([btn_u + su * (perf[0] / 2 + 1), 0, perf_w0 - 1.5]) difference() {
                    translate([-1.5, perf_top - 4.5, 0]) cube([3, inner_h / 2 - perf_top + 4.6, rail_end - perf_w0 + 1.5]);
                    translate([su > 0 ? -1.5 - 0.1 : 0.3, perf_top - 1.6 - 0.25, 1.5]) cube([1.3, 1.6 + 0.5, 100]);
                }
        }
        // window with an outward bevel, or the thin printed skin
        if (acr_t > 0)
            translate([0, 0, -0.01]) hull() {
                linear_extrude(0.01) square([disp_w - 2 + 2 * front, disp_h - 2 + 2 * front], center = true);
                translate([0, 0, front + 0.02]) linear_extrude(0.01) square([disp_w - 2, disp_h - 2], center = true);
            }
        else translate([0, 0, skin]) linear_extrude(front) square([disp_w + 2 * tol, disp_h + 2 * tol], center = true);
        if (back_fix == "screw")
            for (su = [-1, 1], sv = [-1, 1]) translate([su * boss_u, sv * boss_v, boss_w0 + 1]) cylinder(d = screw_d, h = depth_in);
        if (back_fix == "snap")                                          // grooves for the back plate's bumps
            for (sv = [-1, 1]) translate([0, sv * inner_h / 2, depth_in - snap_w]) rotate([0, 90, 0])
                cylinder(r = 0.8, h = inner_w - 20, center = true, $fn = 12);
        if (ldr) translate([ldr_u, 0, -1]) cylinder(d = 5.2, h = front + 5);
        if (usb_c) translate([RIGHT * (outer_w / 2 - wall / 2), 0, z_board_tp - board_top / 2]) rotate([0, 90, 0])
            linear_extrude(wall + 2, center = true) rrect(usb_h, usb_w, 1.5);
        if (button != "none") translate([btn_u, outer_h / 2 - wall / 2, btn_w]) rotate([90, 0, 0])
            cylinder(d = button == "tactile12" ? tact_cap_d : panel_btn_d, h = wall + 2, center = true);
        for (i = [-2 : 2]) translate([i * 12 + RIGHT * 10, outer_h / 2, depth_in - 10]) cube([7, wall * 3, 2.2], center = true);
    }
}

module desk_cut() from_world() translate([-500, -500, -1000]) cube([1000, 1000, 1000]);

module shell() difference() { union() { shell_body(); pedestal(); } desk_cut(); }

// ---------- back plate ----------
// back_u() is laid out in face coordinates (x = u); back() mirrors it into the real, printable part
// (z = 0 is the outside face, printed face down). On the clock: rotate([0, 180, 0]) at w = depth.
module back() mirror([1, 0, 0]) back_u();
module back_u() {
    lip_h = back_fix == "snap" ? 4 : 1.6;
    difference() {
        union() {
            linear_extrude(back_t) rrect(outer_w, outer_h, radius);
            translate([0, 0, back_t]) linear_extrude(lip_h) difference() {
                rrect(inner_w - 2 * tol, inner_h - 2 * tol, 0.8);
                rrect(inner_w - 2 * tol - 3, inner_h - 2 * tol - 3, 0.5);
                if (back_fix == "screw") for (su = [-1, 1], sv = [-1, 1]) translate([su * boss_u, sv * boss_v]) circle(r = boss_r + tol + 0.2);
                if (usb_c) translate([RIGHT * (inner_w / 2 - 6), 0]) square([12, usb_w + 4], center = true);
                if (button == "tactile12") translate([btn_u, inner_h / 2]) square([perf[0] + 8, 8], center = true);
            }
            if (back_fix == "snap")
                for (sv = [-1, 1]) translate([0, sv * (inner_h / 2 - tol), back_t + snap_w]) rotate([0, 90, 0])
                    cylinder(r = 0.6, h = inner_w - 24, center = true, $fn = 12);
            translate([board_mid + LEFT * 2, 0, back_t]) linear_extrude(dupont) square([board_l - 16, 8], center = true);   // board ridge
            if (board_mount == "cradle") board_cradle();
            else translate([board_far + LEFT * 1.2, 0, back_t]) linear_extrude(dupont + board_pcb + 1) square([2.4, 8], center = true);
            for (u = posts_u, sv = [-1, 1]) translate([u, sv * post_v, back_t])
                linear_extrude(depth_in - z_disp_bk + 0.3) square([3, 2.4], center = true);
            if (dc_jack == "pcb") dc005_cradle();
        }
        if (back_fix == "screw") for (su = [-1, 1], sv = [-1, 1]) translate([su * boss_u, sv * boss_v, -1]) {
            cylinder(d = 3.4, h = back_t + 2);
            cylinder(d1 = 6.4, d2 = 3.4, h = 2.5);
        }
        if (back_fix == "snap") translate([0, -outer_h / 2, -0.01]) linear_extrude(back_t * 0.6) rrect(16, 6, 1.5);   // finger notch
        if (dc_jack == "pcb") translate([dc_pos[0], dc_pos[1], -1]) {
            cylinder(d = dc_plug_d, h = back_t + 2);
            cylinder(d = dc_boss_d, h = back_t - 0.8 + 1);
        }
        if (dc_jack == "panel") translate([dc_pos[0], dc_pos[1], -1]) cylinder(d = dc_panel_d, h = back_t + 2);
        for (i = [0 : 5]) for (sv = [-1, 1]) translate([board_far + RIGHT * (12 + i * 10), sv * (outer_h / 2 - 9), -1])
            linear_extrude(back_t + 2) rrect(3, 7, 1.4);
        translate([LEFT * 12, -outer_h / 2 + 6, -0.01]) linear_extrude(0.6)
            text("DotGlow", size = 5, halign = "center", font = "Liberation Sans:style=Bold");
        if (dc_jack != "none") translate([dc_pos[0], dc_pos[1] - 10, -0.01]) linear_extrude(0.6)
            text("5V", size = 4, halign = "center", font = "Liberation Sans:style=Bold");
    }
}

// DC-005 cradle: the jack's front face sits on the plate, plug hole in line with its barrel. Four walls hold it
// straight; glue windows in the side walls take a drop of super glue; the rear end and the pins stay free for soldering.
// The pins point down (-v).
module dc005_cradle() {
    bw = dc_body[0] + 2 * dc_fit; bh = dc_body[1] + 2 * dc_fit;
    cy = dc_pos[1] - (dc_axis - dc_body[1] / 2);          // body centre (the barrel sits above it)
    hgt = dc_body[2] - 4;                                 // last 4 mm + rear pin uncovered
    translate([dc_pos[0], cy, back_t]) difference() {
        linear_extrude(hgt) square([bw + 3.2, bh + 3.2], center = true);
        translate([0, 0, -1]) linear_extrude(hgt + 2) square([bw, bh], center = true);
        translate([0, -bh / 2 - 1, 5 + 50]) cube([bw + 4, 3, 100], center = true);    // pin side: low wall, pins free
        for (sx = [-1, 1]) translate([sx * (bw / 2 + 0.8), 0, 3 + 50]) cube([3, 4, 100], center = true);   // glue windows
    }
}

// ESP32 cradle on the ridge: side guides stop it sliding, a snap hook clicks over the antenna end of the PCB,
// the USB-C end rests against the right wall. Optional strip of foam tape on the ridge.
module board_cradle() {
    top = back_t + dupont + board_pcb;                    // PCB top surface
    for (u = [board_end - RIGHT * 8, board_far + RIGHT * 8], sv = [-1, 1])
        translate([u, sv * (board_w / 2 + tol + 0.8), back_t]) linear_extrude(top - back_t + 1) square([6, 1.6], center = true);
    // snap hook: thin arm just past the antenna end, lip over the PCB edge, sloped top so the board pushes it aside
    au = board_far - RIGHT * tol;                         // arm inner face
    translate([0, -4, 0]) rotate([90, 0, 0]) mirror([0, 0, 1]) linear_extrude(8) polygon([
        [au, back_t], [au - RIGHT * 1.4, back_t], [au - RIGHT * 1.4, top + 3], [au, top + 3],
        [au + RIGHT * 1.0, top + 0.1], [au, top + 0.1]]);
}

// ---------- test fit ----------
module testfit() intersection() {
    shell_body();
    translate([0, 0, -1]) linear_extrude(z_matrix + matrix_h) square([outer_w + 2, outer_h + 2], center = true);
}

// ---------- preview stand-ins ----------
digits = [[4,12,4,4,4,4,14], [14,17,1,2,4,8,31], [2,6,10,18,31,2,2], [31,16,30,1,1,17,14]];   // 1 2 4 5
function lit(cn, r) =
    (r == 0) ? false :
    (cn == 15 || cn == 16) ? (r == 2 || r == 3 || r == 5 || r == 6) :
    let(st = [1, 7, 19, 25], k = [for (i = [0 : 3]) if (cn >= st[i] && cn < st[i] + 5) i])
    len(k) == 0 ? false : floor(digits[k[0]][r - 1] / pow(2, 4 - (cn - st[k[0]]))) % 2 == 1;
module display_model() {
    color("#111") translate([0, 0, z_matrix + matrix_h / 2]) cube([disp_w, disp_h, matrix_h], center = true);
    for (i = [0 : modules * 8 - 1], j = [0 : 7])        // column 0 on the viewer's left (+u)
        color(lit(i, j) ? "#ff2020" : "#3a0d0d")
            translate([disp_w / 2 - 2 - i * 4, disp_h / 2 - 2 - j * 4, z_matrix - 0.4]) cylinder(d = 3, h = 0.4, $fn = 12);
}

if (part == "shell") shell();
else if (part == "back") back();
else if (part == "testfit") testfit();
else {
    color("#2b2f38") to_world() shell_body();
    color("#2b2f38") difference() { to_world() pedestal(); translate([-500, -500, -1000]) cube([1000, 1000, 1000]); }
    to_world() display_model();
    if (acr_t > 0 && show_acrylic) color("#140000", 0.25) to_world() translate([0, 0, front + acr_t / 2])
        cube([disp_w + 2 * acr_margin, disp_h + 2 * acr_margin, acr_t], center = true);
    color("#3a3f4a") to_world() translate([0, 0, depth]) rotate([0, 180, 0]) back();
    color("#555") translate([0, 60, -0.5]) cube([320, 200, 1], center = true);   // desk
}

echo(str("Outer case (mm): ", outer_w, " x ", outer_h, " x ", depth, ", pedestal ", ped_h, " mm, lean ", lean, " deg"));
echo(str("Acrylic (mm): ", disp_w + 2 * acr_margin, " x ", disp_h + 2 * acr_margin, " x ", acr_t));
