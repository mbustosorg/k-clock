/*

A Lissajous curve tracer

https://en.wikipedia.org/wiki/Lissajous_curve

The A parameter and delta control the X, while
the B parameter controls the Y, allowing for a number of
Lissajous curves. A and B can be between 1 and 8.
Delta can be set in 1/4 pi increments.

The dot size, color, speed, and persistence on scree
can be adjusted.

2021 Ben Hencke

*/

//setting to eraase pixels when changing curve parameters
var clearOnChange = true 

//globals
var xl, y1
var pixels = array(pixelCount)
var hues = array(pixelCount)
var frameHue

//controls variables
var pixelDensity = 8
var t = timer(.1)
var a1 = 3
var b1 = 4
var d1 = PI/2
var fade = .9
var h = 0, s = 1, v = 1
var hueShift = .2
var hueShiftTimer = timer(.1)

//controls
//pick the dot starting color
export function hsvPickerColor(_h, _s, _v) {
  h = _h; v = _v; s = _s;
}

//shift hue by this much
export function sliderHueShift(v) {
  hueShift = v
}

export function sliderHueShiftSpeed(v) {
  v = 1-v
  timerSetInterval(hueShiftTimer, .001 + v*v*v)
}

//from tracers, to solid paints
export function sliderPersistence(v) {
  v = 1-v
  fade = 1-v*v
}

export function sliderSize(v) {
  v = 1-v
  pixelDensity = 1 + v*v*32
}

export function sliderSpeed(v) {
  v = 1-v
  timerSetInterval(t, .001 + v*v*v/5)
}

//Lissajous curve ratio A value
export function sliderA(v) {
  var newValue = 1 + floor(v*7)
  if (a1 != newValue)
    clearPixels()
  a1 = newValue
}
//Lissajous curve ratio B value
export function sliderB(v) {
  var newValue = 1 + floor(v*7)
  if (b1 != newValue)
    clearPixels()
  b1 = newValue
}
//Lissajous curve A delta
export function sliderDelta(v) {
  v = floor(v*7)/8
  var newValue = PI*2 * v
  if (d1 != newValue)
    clearPixels()
  d1 = newValue
}

function clearPixels() {
  if (clearOnChange) {
    pixels.mutate(() => 0)
  }
}

export function beforeRenderLissajou(delta) {
  var now = timerNow(t)
  //calc current Lissajous dot location
  xl = sin(now * a1 * PI2 + d1)
  y1 = sin(now * b1 * PI2)
  
  //start with the hue chosen, and shift +- by the hueShuft amount
  frameHue = h - hueShift/2 + triangle(timerNow(hueShiftTimer)) * hueShift
  
  resetTransform()
  //translate(-.5, -.5) //center
  //scale up, with a little extra room for larger dots
  scale(2 + 1.7/pixelDensity, 2 + 1.7/pixelDensity) 
}

export function render2DLissajou(index, x, y) {
  x = (x - 1) * 1.5
  y = (y - 1.2) * 1.5
  //this pixel's distance to the dot
  var distance = hypot(xl - x, y1 - y)
  //calc closeness, scaled by density
  var closeness = clamp(1 - distance * pixelDensity, 0, 1)
  //fade old pixel value, and draw the dot based on closeness
  var pixelValue = pixels[index] = max(pixels[index] * fade, closeness)
  //set the hue if we painted something here
  if (closeness > 0) {
    hues[index] = frameHue
  }
  
  hsv(hues[index],s,pixelValue * v)
}


//timer utility functions for smooth speed adjustment
function timer(interval) {
  return [0, interval]
}

function timerSetInterval(timer, interval) {
  var p1 = time(timer[1]) //measure the current interval's value
  var p2 = time(interval) //measure the new interval's value
  //calculate the phase difference between these
  timer[0] = mod(timer[0] + p1 - p2, 1)
  timer[1] = interval
}

function timerNow(timer) {
  return (time(timer[1]) + timer[0]) % 1
}

var beforeRenderBackground = (delta) => beforeRenderLissajou(delta)
var renderBackground = (index, x, y) => render2DLissajou(index, x * .5 + .5, y * .5 + .5)

var color = 0.0
export function sliderColor(v) { color = v }

var saturation = 0.0
export function sliderSaturation(v) { saturation = v }

var value = 1.0
export function sliderValue(v) { value = v }

var EDGE_INDICES_CLOCKWISE = [  3,   4,   5,
                                6,  29,
                               30,  63,  64, 105, 106, 155,
                              156, 212,
                              335, 336, 399, 400,
                              523, 579,
                              580, 629, 630, 671, 672, 705,
                              706, 729,
                              730, 731, 732, 733, 734, 735,
                              720, 719, 690, 689,
                              652, 651, 606, 605,
                              552, 494,
                              431, 368, 367, 304,
                              241, 183,
                              130, 129,  84,  83,  46,  45,
                               16,  15,   0,   1,  2,
];
var edgeLookup = array(736)
for (var ei = 0; ei < 60; ei++) { edgeLookup[EDGE_INDICES_CLOCKWISE[ei]] = 1 }

var zero  = [0, 0, 0b01110,0b10001,0b10001,0b10001,0b10001,0b10001,0b01110, 0]
var one   = [0, 0, 0b00100,0b01100,0b00100,0b00100,0b00100,0b00100,0b01110, 0]
var two   = [0, 0, 0b01110,0b10001,0b00001,0b00010,0b00100,0b01000,0b11111, 0]
var three = [0, 0, 0b11110,0b00001,0b00001,0b01110,0b00001,0b00001,0b11110, 0]
var four  = [0, 0, 0b00010,0b00110,0b01010,0b10010,0b11111,0b00010,0b00010, 0]
var five  = [0, 0, 0b11111,0b10000,0b10000,0b11110,0b00001,0b00001,0b11110, 0]
var six   = [0, 0, 0b00110,0b01000,0b10000,0b11110,0b10001,0b10001,0b01110, 0]
var seven = [0, 0, 0b11111,0b00001,0b00010,0b00100,0b01000,0b01000,0b01000, 0]
var eight = [0, 0, 0b01110,0b10001,0b10001,0b01110,0b10001,0b10001,0b01110, 0]
var nine  = [0, 0, 0b01110,0b10001,0b10001,0b01111,0b00001,0b00010,0b11100, 0]
var blank = [0, 0, 0, 0, 0, 0, 0, 0, 0, 0]

// Per-row glyph bitmap cache — computed once in beforeRender, read per-pixel in renderClock.
// row 0..9 → the bitmap value for each digit at that row given current offsets.
var cache1 = array(10)
var cache2 = array(10)
var cache3 = array(10)
var cache4 = array(10)
var cacheDirty = 1  // set to 1 whenever offsets or glyphs change; cleared after fillRowCache

ZERO_OFFSET  = -3
ONE_OFFSET   = 7
TWO_OFFSET   = 10
THREE_OFFSET = 6

var characters = [zero, one, two, three, four, five, six, seven, eight, nine]

var flat_characters = array(110)
for (i = 0; i < 11; i++) {
  for (j = 0; j < 10; j++) {
    if (i > 9) flat_characters[i * 10 + j] = characters[i - 10][j]
    else flat_characters[i * 10 + j] = characters[i][j]
  }
}

var flat_minute_characters = array(70)
for (i = 0; i < 7; i++) {
  for (j = 0; j < 10; j++) {
    if (i > 5) flat_minute_characters[i * 10 + j] = characters[i - 6][j]
    else flat_minute_characters[i * 10 + j] = characters[i][j]
  }
}


var digit_four = [
  242 - ZERO_OFFSET, 242 + ZERO_OFFSET,
  303 - ZERO_OFFSET, 305 + ZERO_OFFSET,
  367 - ZERO_OFFSET, 369 + ZERO_OFFSET,
  431 - ZERO_OFFSET, 433 + ZERO_OFFSET,
  494 - ZERO_OFFSET, 494 + ZERO_OFFSET
]

var digit_three = [
  digit_four[0] - ONE_OFFSET, digit_four[1] + ONE_OFFSET,
  digit_four[2] - ONE_OFFSET, digit_four[3] + ONE_OFFSET,
  digit_four[4] - ONE_OFFSET, digit_four[5] + ONE_OFFSET,
  digit_four[6] - ONE_OFFSET, digit_four[7] + ONE_OFFSET,
  digit_four[8] - ONE_OFFSET, digit_four[9] + ONE_OFFSET
]

var digit_two = [
  digit_three[0] - TWO_OFFSET, digit_three[1] + TWO_OFFSET,
  digit_three[2] - TWO_OFFSET, digit_three[3] + TWO_OFFSET,
  digit_three[4] - TWO_OFFSET, digit_three[5] + TWO_OFFSET,
  digit_three[6] - TWO_OFFSET, digit_three[7] + TWO_OFFSET,
  digit_three[8] - TWO_OFFSET, digit_three[9] + TWO_OFFSET
]

var digit_one = [
  digit_two[0] - THREE_OFFSET, digit_two[1] + THREE_OFFSET,
  digit_two[2] - THREE_OFFSET, digit_two[3] + THREE_OFFSET,
  digit_two[4] - THREE_OFFSET, digit_two[5] + THREE_OFFSET,
  digit_two[6] - THREE_OFFSET, digit_two[7] + THREE_OFFSET,
  digit_two[8] - THREE_OFFSET, digit_two[9] + THREE_OFFSET
]

var glyph1 = zero
var glyph2 = zero
var glyph3 = two
var glyph4 = one
export var glyph1_row = 0
export var glyph2_row = 0
var glyph3_row = 0

var cursor = false
export var row_offset_1 = 0
export var row_offset_2 = 0
var row_offset_3 = 0
var row_offset_4 = 0
var row_offset_1_start = 0
var row_offset_2_start = 0
var row_offset_3_start = 0
var row_offset_4_start = 0
var twelve_hour = 0
var cursor_twelve_hour_offset = 1
var cursor_dots = [0, 0]
var x1 = 0.77
var x2 = 0.5
var x3 = 0.2

// ── Scroll state machine ──────────────────────────────────────────────
// scrollState:
//   0 = normal clock
//   1 = scrolling OUT to blank  (triggerScrollToBlank fired)
//   2 = holding blank           (all digits reached blank, waiting)
//   3 = scrolling IN from blank (triggerScrollIn fired)

export var scrollState = 0
export function inputNumberState(v) { scrollState = clamp(floor(v), 0, 3) }
export var wakeMode = 0
export function triggerWakeMode(v) {
  wakeMode = wakeMode == 1 ? 0 : 1
}
var wakeEdgeTime = 0      // accumulator for fast edge index in wake mode

// Per-digit scroll speeds (ms per row step).  Randomised on trigger.
var scroll_speed_1 = 30
var scroll_speed_2 = 30
var scroll_speed_3 = 30
var scroll_speed_4 = 30

// Track which digits have finished their current scroll phase
var done_1 = 0
var done_2 = 0
var done_3 = 0
var done_4 = 0

// Snap all four offsets back to zero and mark them done so a fresh
// scroll can begin immediately from the top.
function resetAllOffsets() {
  row_offset_1 = 0; row_offset_1_start = 0; done_1 = 0
  row_offset_2 = 0; row_offset_2_start = 0; done_2 = 0
  row_offset_3 = 0; row_offset_3_start = 0; done_3 = 0
  row_offset_4 = 0; row_offset_4_start = 0; done_4 = 0
}

function randomSpeed() {
  return 10 + random(70)   // 10 – 80 ms per row, all four independent
}

export function triggerScrollOut(v) {
  if (scrollState == 1) return
  scrollState = 1
  cursor = false
  scroll_speed_1 = randomSpeed()
  scroll_speed_2 = randomSpeed()
  scroll_speed_3 = randomSpeed()
  scroll_speed_4 = randomSpeed()
  resetAllOffsets()
  row_offset_1_start = 0.001
  row_offset_2_start = 0.001
  row_offset_3_start = 0.001
  row_offset_4_start = 0.001
}

export function triggerScrollIn(v) {
  if (scrollState == 3) return
  scrollState = 3
  scroll_speed_1 = randomSpeed()
  scroll_speed_2 = randomSpeed()
  scroll_speed_3 = randomSpeed()
  scroll_speed_4 = randomSpeed()
  var t1 = minute % 10
  var t2 = trunc(minute / 10) % 10
  var t3 = twelve_hour % 10
  glyph1 = characters[t1]; glyph1_row = t1 * 10
  glyph2 = characters[t2]; glyph2_row = t2 * 10
  glyph3 = characters[t3]; glyph3_row = t3 * 10
  glyph4 = twelve_hour > 9 ? characters[1] : blank
  resetAllOffsets()
  row_offset_1 = 9; row_offset_2 = 9; row_offset_3 = 9; row_offset_4 = 9
}

export function resetDigitLocation(offset) {
  digit_four[0] = 242 - offset
  digit_four[1] = 242 + offset
  digit_four[2] = 303 - offset
  digit_four[3] = 305 + offset
  digit_four[4] = 367 - offset
  digit_four[5] = 369 + offset
  digit_four[6] = 431 - offset
  digit_four[7] = 433 + offset
  digit_four[8] = 494 - offset
  digit_four[9] = 494 + offset

  digit_three[0] = digit_four[0] - ONE_OFFSET
  digit_three[1] = digit_four[1] + ONE_OFFSET
  digit_three[2] = digit_four[2] - ONE_OFFSET
  digit_three[3] = digit_four[3] + ONE_OFFSET
  digit_three[4] = digit_four[4] - ONE_OFFSET
  digit_three[5] = digit_four[5] + ONE_OFFSET
  digit_three[6] = digit_four[6] - ONE_OFFSET
  digit_three[7] = digit_four[7] + ONE_OFFSET
  digit_three[8] = digit_four[8] - ONE_OFFSET
  digit_three[9] = digit_four[9] + ONE_OFFSET

  digit_two[0] = digit_three[0] - TWO_OFFSET
  digit_two[1] = digit_three[1] + TWO_OFFSET
  digit_two[2] = digit_three[2] - TWO_OFFSET
  digit_two[3] = digit_three[3] + TWO_OFFSET
  digit_two[4] = digit_three[4] - TWO_OFFSET
  digit_two[5] = digit_three[5] + TWO_OFFSET
  digit_two[6] = digit_three[6] - TWO_OFFSET
  digit_two[7] = digit_three[7] + TWO_OFFSET
  digit_two[8] = digit_three[8] - TWO_OFFSET
  digit_two[9] = digit_three[9] + TWO_OFFSET

  digit_one[0] = digit_two[0] - THREE_OFFSET
  digit_one[1] = digit_two[1] + THREE_OFFSET
  digit_one[2] = digit_two[2] - THREE_OFFSET
  digit_one[3] = digit_two[3] + THREE_OFFSET
  digit_one[4] = digit_two[4] - THREE_OFFSET
  digit_one[5] = digit_two[5] + THREE_OFFSET
  digit_one[6] = digit_two[6] - THREE_OFFSET
  digit_one[7] = digit_two[7] + THREE_OFFSET
  digit_one[8] = digit_two[8] - THREE_OFFSET
  digit_one[9] = digit_two[9] + THREE_OFFSET
}

minute      = clockMinute()
twelve_hour = clockHour()
if (twelve_hour > 12) twelve_hour -= 12
if (twelve_hour == 0) twelve_hour = 12
second       = clockSecond()
second_index = second
glyph1     = characters[minute % 10]
glyph1_row = minute % 10 * 10
glyph2     = characters[trunc(minute / 10) % 10]
glyph2_row = trunc(minute / 10) % 10 * 10
glyph3     = characters[twelve_hour % 10]
glyph3_row = twelve_hour % 10 * 10

export function beforeRender(delta) {
  beforeRenderBackground(delta)
  resetTransform()

  second       = clockSecond()
  if (wakeMode) {
    wakeEdgeTime = (wakeEdgeTime + delta) % 1000
    second_index = trunc(wakeEdgeTime / 1000 * 60)
  } else {
    wakeEdgeTime = 0
    second_index = second
  }
  if (scrollState == 0) cursor = (second & 1) == 0
  minute       = clockMinute()
  twelve_hour  = clockHour()
  if (twelve_hour > 12) twelve_hour -= 12
  if (twelve_hour == 0) twelve_hour = 12

  // ── Digit 4 / glyph4 (hour tens place) ───────────────────────────
  // Only recalculate layout when hour crosses 10 boundary (very rare).
  if (twelve_hour > 9) {
    if (ZERO_OFFSET != 1) {
      ZERO_OFFSET = 1
      ONE_OFFSET  = 5
      resetDigitLocation(ZERO_OFFSET)
      x1 = 0.77; x2 = 0.5; x3 = 0.2
      cursor_twelve_hour_offset = 0
      cursor_dots[0] = 352
      cursor_dots[1] = 447
    }
    if (scrollState == 0) glyph4 = characters[1]
  } else {
    if (ZERO_OFFSET != -2) {
      ZERO_OFFSET = -2
      resetDigitLocation(ZERO_OFFSET)
      x1 = 0.7; x2 = 0.5; x3 = 0.15
      cursor_twelve_hour_offset = -2
      cursor_dots[0] = 353
      cursor_dots[1] = 446
    }
    if (scrollState == 0) glyph4 = blank
  }

  // ── State machine ─────────────────────────────────────────────────
  if (scrollState == 0) {
    // Normal clock: only update cache when offsets or glyphs actually change.

    if ((minute % 10 != glyph1_row / 10) && row_offset_1 < 9) {
      row_offset_1_start += delta
      row_offset_1 = row_offset_1_start / scroll_speed_1
      cacheDirty = 1
    } else if (row_offset_1 != 0) {
      row_offset_1 = 0; row_offset_1_start = 0
      glyph1 = characters[minute % 10]
      glyph1_row = minute % 10 * 10
      cacheDirty = 1
    }

    if ((trunc(minute / 10) % 10 != glyph2_row / 10) && row_offset_2 < 9) {
      row_offset_2_start += delta
      row_offset_2 = row_offset_2_start / scroll_speed_2
      cacheDirty = 1
    } else if (row_offset_2 != 0) {
      row_offset_2 = 0; row_offset_2_start = 0
      glyph2 = characters[trunc(minute / 10) % 10]
      glyph2_row = trunc(minute / 10) % 10 * 10
      cacheDirty = 1
    }

    if ((twelve_hour % 10 != glyph3_row / 10) && row_offset_3 < 9) {
      row_offset_3_start += delta
      row_offset_3 = row_offset_3_start / scroll_speed_3
      cacheDirty = 1
    } else if (row_offset_3 != 0) {
      row_offset_3 = 0; row_offset_3_start = 0
      glyph3 = characters[twelve_hour % 10]
      glyph3_row = twelve_hour % 10 * 10
      cacheDirty = 1
    }

  } else if (scrollState == 1) {
    cacheDirty = 1
    // Scrolling OUT to blank — advance each digit independently.

    if (!done_1) {
      if (row_offset_1 < 9) {
        row_offset_1_start += delta
        row_offset_1 = row_offset_1_start / scroll_speed_1
      } else {
        row_offset_1 = 0; row_offset_1_start = 0
        glyph1 = blank; glyph1_row = 200
        done_1 = 1
      }
    }

    if (!done_2) {
      if (row_offset_2 < 9) {
        row_offset_2_start += delta
        row_offset_2 = row_offset_2_start / scroll_speed_2
      } else {
        row_offset_2 = 0; row_offset_2_start = 0
        glyph2 = blank; glyph2_row = 200
        done_2 = 1
      }
    }

    if (!done_3) {
      if (row_offset_3 < 9) {
        row_offset_3_start += delta
        row_offset_3 = row_offset_3_start / scroll_speed_3
      } else {
        row_offset_3 = 0; row_offset_3_start = 0
        glyph3 = blank; glyph3_row = 200
        done_3 = 1
      }
    }

    if (!done_4) {
      if (row_offset_4 < 9) {
        row_offset_4_start += delta
        row_offset_4 = row_offset_4_start / scroll_speed_4
      } else {
        row_offset_4 = 0; row_offset_4_start = 0
        glyph4 = blank
        done_4 = 1
      }
    }

    // All four done → enter holding state
    if (done_1 && done_2 && done_3 && done_4) {
      scrollState = 2
    }

  } else if (scrollState == 2) {
    // Holding blank — nothing to update; wait for triggerScrollIn.

  } else if (scrollState == 3) {
    cacheDirty = 1
    // Scrolling IN: starts blank, offsets count DOWN 9→0, target snaps in at 0.

    if (!done_1) {
      row_offset_1_start += delta
      row_offset_1 = 9 - (row_offset_1_start / scroll_speed_1)
      if (row_offset_1 <= 0) { row_offset_1 = 0; row_offset_1_start = 0; done_1 = 1 }
    }

    if (!done_2) {
      row_offset_2_start += delta
      row_offset_2 = 9 - (row_offset_2_start / scroll_speed_2)
      if (row_offset_2 <= 0) { row_offset_2 = 0; row_offset_2_start = 0; done_2 = 1 }
    }

    if (!done_3) {
      row_offset_3_start += delta
      row_offset_3 = 9 - (row_offset_3_start / scroll_speed_3)
      if (row_offset_3 <= 0) { row_offset_3 = 0; row_offset_3_start = 0; done_3 = 1 }
    }

    if (!done_4) {
      row_offset_4_start += delta
      row_offset_4 = 9 - (row_offset_4_start / scroll_speed_4)
      if (row_offset_4 <= 0) { row_offset_4 = 0; row_offset_4_start = 0; done_4 = 1 }
    }

    // All four landed → back to normal clock
    if (done_1 && done_2 && done_3 && done_4) {
      scrollState = 0
      cursor = (second & 1) == 0
      scroll_speed_1 = 30
      scroll_speed_2 = 30
      scroll_speed_3 = 30
      scroll_speed_4 = 30
    }
  }
  if (cacheDirty) { fillRowCache(); cacheDirty = 0 }
}

// Fills cache1..cache4 with the correct bitmap value for each row (0-9).
// Called once per frame from beforeRender after state machine runs.
function fillRowCache() {
  var ss = scrollState
  var d4offset = trunc(row_offset_4)
  for (var r = 0; r < 10; r++) {
    // Digit 1
    if (glyph1_row >= 200) {
      cache1[r] = 0
    } else {
      var fi1 = ss == 3 ? glyph1_row + r - trunc(row_offset_1)
                        : glyph1_row + r + trunc(row_offset_1)
      if      (ss == 3 && fi1 < glyph1_row)    cache1[r] = 0
      else if (ss == 1 && fi1 >= glyph1_row+10) cache1[r] = 0
      else { fi1 = fi1>109?109:(fi1<0?0:fi1); cache1[r] = flat_characters[fi1] }
    }
    // Digit 2
    if (glyph2_row >= 200) {
      cache2[r] = 0
    } else {
      var fi2 = ss == 3 ? glyph2_row + r - trunc(row_offset_2)
                        : glyph2_row + r + trunc(row_offset_2)
      if      (ss == 3 && fi2 < glyph2_row)    cache2[r] = 0
      else if (ss == 1 && fi2 >= glyph2_row+10) cache2[r] = 0
      else { fi2 = fi2>69?69:(fi2<0?0:fi2); cache2[r] = flat_minute_characters[fi2] }
    }
    // Digit 3
    if (glyph3_row >= 200) {
      cache3[r] = 0
    } else {
      var fi3 = ss == 3 ? glyph3_row + r - trunc(row_offset_3)
                        : glyph3_row + r + trunc(row_offset_3)
      if      (ss == 3 && fi3 < glyph3_row)    cache3[r] = 0
      else if (ss == 1 && fi3 >= glyph3_row+10) cache3[r] = 0
      else { fi3 = fi3>109?109:(fi3<0?0:fi3); cache3[r] = flat_characters[fi3] }
    }
    // Digit 4
    if (ss == 3) {
      var d4in = r - d4offset
      cache4[r] = d4in < 0 ? 0 : glyph4[d4in % 10]
    } else if (ss == 1 && d4offset >= 1) {
      cache4[r] = 0
    } else {
      cache4[r] = glyph4[(r + d4offset + 10) % 10]
    }
  }
}

export function renderClock(index, x, y) {
  if (index < 262 || index > 500) {renderBackground(index, x, y); return}
  if (cursor && (cursor_dots[0] == index || cursor_dots[1] == index)) {
    hsv(color, saturation, value); return
  }

  var row = 0
  if      (index <= 271) row = 0
  else if (index <= 493) row = ((index - 242) / 32 | 0) + 1
  else                   row = 9

  var forward = row & 1


  var anchor, bit, gv
  if (x > x1) {
    anchor = digit_one[row]
    bit = forward ? index - anchor : anchor - index - 1
    if ((cache1[row] << bit) & 32) { hsv(color, saturation, value) } else { renderBackground(index, x, y) }
    return
  }
  if (x > x2) {
    anchor = digit_two[row]
    bit = forward ? index - anchor : anchor - index - 1
    if ((cache2[row] << bit) & 32) { hsv(color, saturation, value) } else { renderBackground(index, x, y) }
    return
  }
  if (x > x3) {
    anchor = digit_three[row]
    bit = forward ? index - anchor : anchor - index - 1
    if ((cache3[row] << bit) & 32) { hsv(color, saturation, value) } else { renderBackground(index, x, y) }
    return
  }
  anchor = digit_four[row]
  bit = forward ? index - anchor : anchor - index - 1
  if ((cache4[row] << bit) & 32) { hsv(color, saturation, value) } else { renderBackground(index, x, y) }
}

export function render2D(index, x, y) {
  if (index == EDGE_INDICES_CLOCKWISE[second_index]) {
    hsv(color, saturation, value)
  } else {
    if (scrollState == 2) {renderBackground(index, x, y)} else renderClock(index, x, y)
  }
}