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

# Layers, by how cold it feels (°F, wind chill applied), warmest first. Common outdoor-clothing
# practice, written here as planning advice; adjust to taste and rerun.
LAYERS = [
    (78, "a t-shirt, sun hat and sunscreen"),
    (68, "a t-shirt, with a long-sleeve shirt handy"),
    (58, "long sleeves and a light layer"),
    (48, "a fleece or sweater under a light jacket"),
    (38, "a warm jacket, hat and something for your hands"),
    (28, "winter layers: insulated jacket, thermal base layer, hat, gloves"),
    (-99, "full winter kit: base layers, insulated jacket, warm hat, gloves, wool socks"),
]
SLEEPWEAR = [
    (55, "light, dry layers"),
    (45, "a dry base layer and socks"),
    (35, "a dry base layer, wool socks and a hat"),
    (-99, "thermals, wool socks and a hat; a hot-water bottle in the bag helps"),
]
SLEEP_MARGIN_F = 10      # bring a bag rated this much below the coldest likely night
HOT_BREAKFAST_F = 50     # mornings at or below this make a hot breakfast worth planning
COOLER_WARM_F = 75       # afternoons at or above this melt cooler ice noticeably faster
WARM_DRINK_F = 50        # evenings that feel this cold or colder: bring a thermos

# Dew and fog: when the air cools to within this many °F of its dew point on a calm night,
# tents, bags and playa wear get wet without rain.
DEW_SPREAD_F = 3
CALM_MPH = 4
