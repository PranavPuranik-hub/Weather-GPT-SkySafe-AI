"""
SimClock: Thread-safe authoritative simulated clock for Lab scenario replay.
Drives all three views (Chat, Command, SMS) via a single SSE stream.
"""
import logging
import threading
import time
from typing import Callable, Optional

logger = logging.getLogger("app.eval.clock")

SCENARIOS = [
    "kerala_flood",
    "odisha_cyclone",
    "rajasthan_heatwave",
    "cyclone_t24",
    "cyclone_t12",
    "cyclone_t3",
    "flood",
    "heatwave",
]

SPEED_MULTIPLIERS = {1: 1.0, 10: 10.0, 60: 60.0}


class SimClock:
    """
    Single authoritative simulated clock. One instance (global singleton).
    Publishes tick events that the SSE stream forwards to all subscribers.
    """

    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._running = False
        self._paused = False
        self._scenario: Optional[str] = None
        self._speed: int = 1
        self._tick: int = 0
        self._thread: Optional[threading.Thread] = None
        self._callbacks: list[Callable] = []

    def register_callback(self, fn: Callable) -> None:
        """Register a function to call on each clock tick."""
        self._callbacks.append(fn)

    def unregister_callback(self, fn: Callable) -> None:
        if fn in self._callbacks:
            self._callbacks.remove(fn)

    def start(self, scenario: str, speed: int = 1) -> None:
        """Start the simulated clock for a given scenario."""
        with self._lock:
            if self._running:
                self._running = False
                if self._thread:
                    self._thread.join(timeout=2)
            self._scenario = scenario
            self._speed = speed if speed in SPEED_MULTIPLIERS else 1
            self._tick = 0
            self._paused = False
            self._running = True
            self._thread = threading.Thread(target=self._run, daemon=True)
            self._thread.start()
        logger.info(f"SimClock started: scenario={scenario} speed={speed}x")

    def pause(self) -> None:
        with self._lock:
            self._paused = True
        logger.info("SimClock paused")

    def resume(self) -> None:
        with self._lock:
            self._paused = False
        logger.info("SimClock resumed")

    def step(self) -> None:
        """Advance a single tick while paused."""
        self._fire_tick()

    def stop(self) -> None:
        with self._lock:
            self._running = False

    def current_state(self) -> dict:
        return {
            "running": self._running,
            "paused": self._paused,
            "scenario": self._scenario,
            "speed": self._speed,
            "tick": self._tick,
        }

    def _run(self) -> None:
        while True:
            with self._lock:
                if not self._running:
                    break
                if self._paused:
                    time.sleep(0.1)
                    continue
            self._fire_tick()
            # Wall-clock sleep inversely proportional to speed
            time.sleep(max(1.0 / SPEED_MULTIPLIERS[self._speed], 0.05))

    def _fire_tick(self) -> None:
        with self._lock:
            self._tick += 1
            tick = self._tick
            scenario = self._scenario
            speed = self._speed
        event_data = {"tick": tick, "scenario": scenario, "speed": speed}
        for cb in list(self._callbacks):
            try:
                cb(event_data)
            except Exception as e:
                logger.warning(f"SimClock callback error: {e}")


# Global singleton
sim_clock = SimClock()
