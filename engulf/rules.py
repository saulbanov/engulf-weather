"""The thresholds that turn numbers into a reading. Planning rules, set here, not Engulf policy.

The event's Fire Art Response Team and burn leads decide whether and when anything burns; nothing in
this repo is a fire-weather call. These lines say which numbers the readings flag, so anyone who
disagrees can change one and rerun. Each carries where it came from.
"""

# Wind, mph at 10 m (the height stations and models report). A burn crowd stands downwind of a
# large fire; sparks and embers travel with the wind. 15 mph sustained is where the National Weather
# Service's forecast wording starts to say "breezy"; 25 mph gusts is a round number chosen here.
# Neither is an Engulf rule, and no burn's own wind limit was checked.
WINDY_MPH = 15
GUSTY_MPH = 25

# Rain. 0.1 in in a few hours wets people and fuel; 0.5 in in a day on clay-loam site roads is
# where the event's own guide starts talking about mud and flooding. Planning levels only.
WET_IN = 0.1
SOAKING_IN = 0.5

# Cold, °F. 40°F is where a summer sleeping bag stops being enough for most people; 32°F is frost
# on tents and freezing water lines.
COLD_NIGHT_F = 40
FROST_F = 32

# Warm and chilly afternoons, °F: costume planning, not health bands.
WARM_DAY_F = 82
CHILLY_DAY_F = 58

# What-it-means lines (engulf/kit.py).
SWING_F = 25             # afternoon-to-morning drop at or above this is called "a big swing"
MUD_CHANCE = 0.3         # a day this likely to see 0.1 in of rain gets the mud line
DEWY_SHARE = 0.25        # share of calm predawn hours near the dew point that earns the dew line

# Dew and fog: when the air cools to within this many °F of its dew point on a calm night,
# tents and gear get wet without rain.
DEW_SPREAD_F = 3
CALM_MPH = 4
