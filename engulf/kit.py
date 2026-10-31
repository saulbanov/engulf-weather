"""What to wear, what to pack and what to eat, from the numbers. Planning advice, in plain words.

Clothing follows how cold it feels, not just the thermometer: below 50°F with wind over 3 mph the
National Weather Service's wind-chill formula applies. Packing plans for the cold end of the runs
(the 10th percentile), because a jacket you didn't need costs less than one you didn't bring. Meals
follow the event's own rules (Engulf Survival Guide 2026): personal fires and fire pits are not
allowed, ice is sold noon to 4 pm Thursday to Saturday for cash, nothing else is sold, bring 1.5
gallons of water a person a day, and generators are off from 10 pm to 10 am. The guide does not
mention camp stoves, so the advice says to clear one with your camp before relying on it.
"""
from __future__ import annotations
from . import rules


def feels(temp_f: float, wind_mph: float) -> float:
    """NWS wind chill (2001 formula) where it applies; otherwise the air temperature."""
    if temp_f > 50 or wind_mph <= 3:
        return temp_f
    v = wind_mph ** 0.16
    return 35.74 + 0.6215 * temp_f - 35.75 * v + 0.4275 * temp_f * v


def dress(f: float | None) -> str:
    """The layer for a temperature, from rules.LAYERS (warmest first)."""
    if f is None:
        return "unknown"
    for floor, words in rules.LAYERS:
        if f >= floor:
            return words
    return rules.LAYERS[-1][1]


def sleepwear(f: float | None) -> str:
    """What to sleep in, from the overnight low; the bag and pad do most of the work."""
    if f is None:
        return "unknown"
    for floor, words in rules.SLEEPWEAR:
        if f >= floor:
            return words
    return rules.SLEEPWEAR[-1][1]


def sleep_rating(coldest_low: float) -> int:
    """The sleeping-bag rating to bring: the coldest likely low less a margin, rounded down to 5°F."""
    r = coldest_low - rules.SLEEP_MARGIN_F
    return int(r // 5 * 5)


def meals(day: dict, is_burn_day: bool, is_last_day: bool, is_first_day: bool = False, sunset: str = "") -> list[str]:
    """A few lines of meal planning for one day, from its morning low, high and evening feel."""
    out = []
    low, high, eve = day.get("morning_f"), day.get("high_f"), day.get("evening_feels_f")
    if is_first_day:
        out.append("Before you come: eat on the road. Gates open at 10 am and setup eats the afternoon.")
        out.append(f"Dinner: something easy and pre-made. It's dark by {sunset}, so get camp up first.")
    elif low is not None and low <= rules.HOT_BREAKFAST_F:
        out.append(f"Breakfast: something hot. Mornings near {low}°F make coffee and oats worth it "
                   "(a stove cleared with your camp; personal fires are not allowed).")
    if is_first_day:
        pass
    elif high is not None and high >= rules.COOLER_WARM_F:
        out.append(f"Lunch: no-cook and cold. Near {high}°F a shaded cooler still loses ice; ice is sold noon to 4 pm, cash.")
    if is_burn_day:
        out.append("Dinner: a real meal by 6:30 pm. You'll be standing out from the temple burn at 8 through the effigy at 10.")
    elif is_last_day:
        out.append("Eat the cooler down; you have to be off the land by 5 pm.")
    if eve is not None and eve <= rules.WARM_DRINK_F and not is_last_day:
        out.append(f"Evening: a thermos of something hot. It will feel like {eve}°F after dark.")
    return out


def checklist(days: list[dict], any_wet: float | None, dewy: float | None, sunset: str, dark_hours: int) -> list[tuple[str, str]]:
    """The packing list as (item, why) pairs, in the order a camper loads the car. Same data, same list."""
    lows = [d["overnight_p10_f"] for d in days if d.get("overnight_p10_f") is not None]
    eves = [d["evening_p10_f"] for d in days if d.get("evening_p10_f") is not None]
    highs = [d["high_p90_f"] for d in days if d.get("high_p90_f") is not None]
    out = []
    if lows:
        c = min(lows)
        out.append((f"Sleeping bag rated {sleep_rating(c)}°F or warmer, and a sleeping pad",
                    f"Nights could drop to about {round(c)}°F. Generators are off 10 pm to 10 am, so no plug-in heaters."))
    out.append(("Headlamp, plus lights for your camp, tent lines and bike",
                f"It's dark by {sunset}: about {dark_hours} hours of darkness a night."))
    if eves:
        e = min(eves)
        out.append((dress(e)[0].upper() + dress(e)[1:], f"For evenings and the burns. With the wind it could feel like {round(e)}°F."))
    out.append(("Rain jacket and mud boots", "The event asks for both whatever the forecast"
                + (f"; there's about a {round(any_wet * 10)} in 10 chance of rain on at least one day." if any_wet and round(any_wet * 10) else ".")))
    if highs and max(highs) >= rules.COOLER_WARM_F:
        out.append(("Sun hat and sunscreen", f"Afternoons could reach {round(max(highs))}°F, and there isn't much shade."))
    if dewy:
        out.append(("Dry bags or a plastic bin", "Heavy dew on calm nights soaks anything left out, even without rain."))
    if eves and min(eves) <= rules.WARM_DRINK_F:
        out.append(("Thermos", "Something hot for standing out at the burns."))
    out.append(("4½ gallons of water per person", "The event's figure: 1.5 gallons a day for three days. Nothing is sold on site."))
    out.append(("Cash for ice", "Ice is the only thing sold: noon to 4 pm, Thursday to Saturday."))
    return out


def packing(days: list[dict], any_wet: float | None, dewy: float | None, past_cold: float | None = None,
            past_cold_evening: float | None = None) -> list[str]:
    """The list for the whole weekend, planned for the cold end of the forecast (or of a normal year, for days it doesn't reach)."""
    lows = [d["overnight_p10_f"] for d in days if d.get("overnight_p10_f") is not None]
    eves = [d["evening_p10_f"] for d in days if d.get("evening_p10_f") is not None]
    highs = [d["high_p90_f"] for d in days if d.get("high_p90_f") is not None]
    out = []
    if lows or past_cold is not None:
        c = min(lows) if lows else past_cold          # a day no forecast reaches already carries the normal year's cold end
        out.append(f"Sleep: a bag rated {sleep_rating(c)}°F or warmer, plus a sleeping pad (cold comes up from the ground). "
                   f"Nights could drop to about {round(c)}°F. Generators are off 10 pm to 10 am, so no plug-in heaters.")
    if eves:
        cold_eve = min(eves)
        out.append(f"Burn night and evenings: {dress(cold_eve)}. With the wind, evenings could feel as cold as {round(cold_eve)}°F.")
    if highs:
        out.append(f"Afternoons: {dress(max(highs))}. It could reach {round(max(highs))}°F, and there isn't much shade.")
    out.append("Rain: a rain jacket and mud boots, whatever the forecast says. The event asks for both"
               + (f", and there's about a {round(any_wet * 10)} in 10 chance of rain on at least one day." if any_wet and round(any_wet * 10)
                  else ", even though rain looks unlikely for now."))
    if dewy:
        out.append("Dew: dry bags or a plastic bin for clothes and electronics. On calm nights here, heavy dew soaks anything left out, "
                   "even when it doesn't rain.")
    out.append("Water: 1.5 gallons per person per day (the event's figure), more if it's warm.")
    return out
