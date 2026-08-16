import time
from typing import Any

from mods_base import SliderOption, build_mod, hook, get_pc
from unrealsdk.hooks import Type
from unrealsdk.unreal import BoundFunction, UObject, WrappedStruct

ffyl_recover_time = SliderOption(
    identifier="FFYL Recover Time",
    value=30,
    min_value=1,
    max_value=60,
    step=1,
    is_integer=True,
    description="Seconds without entering FFYL before recovering one FFYL state.",
)

ffyl_state_1 = SliderOption(
    identifier="FFYL State 1 Duration",
    value=12,
    min_value=1,
    max_value=30,
    step=1,
    is_integer=True,
    description="Base duration of the first FFYL state.",
)

ffyl_state_2 = SliderOption(
    identifier="FFYL State 2 Duration",
    value=8,
    min_value=1,
    max_value=30,
    step=1,
    is_integer=True,
    description="Base duration of the second FFYL state.",
)

ffyl_state_3 = SliderOption(
    identifier="FFYL State 3 Duration",
    value=4,
    min_value=1,
    max_value=30,
    step=1,
    is_integer=True,
    description="Base duration of the third FFYL state.",
)

ffyl_state_4 = SliderOption(
    identifier="FFYL State 4 Duration",
    value=1,
    min_value=1,
    max_value=30,
    step=1,
    is_integer=True,
    description="Base duration of the fourth FFYL state.",
)

ffyl_recovery_kills = SliderOption(
    identifier="FFYL Recovery Kills",
    value=10,
    min_value=1,
    max_value=20,
    step=1,
    is_integer=True,
    description="Kills required to move the next FFYL state back by one level.",
)

ffyl_state_index = 0
ffyl_recovery_kill_count = 0
last_ffyl_end_time: float | None = None
died = False

def reset_ffyl():
    global ffyl_state_index
    global ffyl_recovery_kill_count
    global last_ffyl_end_time

    ffyl_state_index = 0
    ffyl_recovery_kill_count = 0
    last_ffyl_end_time = None


def get_ffyl_base_duration() -> float:
    durations = (
        ffyl_state_1.value,
        ffyl_state_2.value,
        ffyl_state_3.value,
        ffyl_state_4.value,
    )

    return float(durations[ffyl_state_index])


def is_local_player(controller: UObject) -> bool:
    try:
        local_pc = get_pc()

        if not local_pc:
            return False

        return controller == local_pc

    except Exception as e:
        print(f"[FFYL] is_local_player exception: {e}")
        return False

def is_local_pawn(pawn: UObject) -> bool:
    try:
        local_pc = get_pc()

        if not local_pc:
            return False

        return pawn == local_pc.Pawn

    except Exception as e:
        print(f"[FFYL] is_local_pawn exception: {e}")
        return False

def set_ffyl_state(new_state: int):
    global ffyl_state_index
    global ffyl_recovery_kill_count
    global last_ffyl_end_time

    if new_state == ffyl_state_index:
        return

    ffyl_state_index = new_state
    
    # reset timer and kill count
    ffyl_recovery_kill_count = 0
    last_ffyl_end_time = time.monotonic()

@hook("WillowGame.BodyClassDeathDefinition:OnKilledBy", Type.PRE)
def killed_by(_obj: UObject, args: WrappedStruct, _ret: Any, _func: BoundFunction,) -> None:
    global ffyl_recovery_kill_count
    global ffyl_state_index

    killer = getattr(args, "Killer", None)

    if not killer:
        return

    try:
        if killer.Class.Name != "WillowPlayerController":
            return
    except Exception:
        return

    if not is_local_player(killer):
        return

    if not killer.Pawn:
        return

    ffyl_recovery_kill_count += 1

    if ffyl_recovery_kill_count < ffyl_recovery_kills.value:
        return

    ffyl_recovery_kill_count = 0

    if ffyl_state_index == 0:
        return

    set_ffyl_state(ffyl_state_index - 1)

@hook("WillowGame.WillowPawn:injured.BeginState", Type.POST)
def ffyl_start(obj: UObject, _args: WrappedStruct, _ret: object, _func: BoundFunction):
    if not is_local_pawn(obj):
        return
    now = time.monotonic()

    if last_ffyl_end_time is not None:
        elapsed = now - last_ffyl_end_time
        reset_time = float(ffyl_recover_time.value)

        recovery_steps = int(elapsed / reset_time)

        if recovery_steps > 0:
            old_state = ffyl_state_index
            new_state = max(0, ffyl_state_index - recovery_steps)

            if new_state != old_state:
                set_ffyl_state(new_state)

    base_duration = get_ffyl_base_duration()
    multiplier = float(obj.TimeToBeRevivedMultiplier)
    final_duration = base_duration * multiplier

    obj.TotalBleedoutTime = final_duration

@hook("WillowGame.WillowPawn:injured.EndState", Type.POST)
def ffyl_end(_obj: UObject, _args: WrappedStruct, _ret: object, _func: BoundFunction):
    if not is_local_pawn(obj):
        return
    
    global died
    global last_ffyl_end_time

    if died:
        died = False
        return

    if ffyl_state_index < 3:
        set_ffyl_state(ffyl_state_index + 1)
    else:
        last_ffyl_end_time = time.monotonic()

@hook("WillowGame.WillowPlayerPawn:StartInjuredDeathSequence", Type.POST)
def player_died(obj: UObject, args: WrappedStruct, ret: object, func: BoundFunction):
    global died
    
    if not is_local_pawn(obj):
        return
    
    died = True
    reset_ffyl()

build_mod(
    options=[
        ffyl_recover_time,
        ffyl_state_1,
        ffyl_state_2,
        ffyl_state_3,
        ffyl_state_4,
        ffyl_recovery_kills,
    ]
)