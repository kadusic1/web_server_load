"""SimPy-based simulation engine for web server request lifecycle.

Encapsulates the resource model (multi-server queue) and collects
per-request statistics.  The engine is agnostic to the generator
implementation — theoretical vs empirical is a configuration choice.
"""

from __future__ import annotations

from collections.abc import Generator

import numpy as np
import simpy
from loguru import logger

from src.simulation._config import SimulationConfig
from src.simulation._types import SimulationResult
from src.simulation.generators import ArrivalGenerator, ServiceGenerator


def _rate_from_gen(gen: ArrivalGenerator | ServiceGenerator) -> float:
    """Read the ``rate`` property from a generator.

    Args:
        gen: An arrival or service generator.

    Returns:
        Rate in requests per second.
    """
    return float(gen.rate)


class _StatsCollector:
    """Collect per-request stats and aggregate into SimulationResult.

    Args:
        warmup: Discard statistics before this time.
    """

    def __init__(self, warmup: float = 0.0) -> None:
        self._cutoff: float = warmup
        self._waits: list[float] = []
        self._queue_samples: list[tuple[float, int]] = []
        self._busy_samples: list[tuple[float, int]] = []
        self._total_requests: int = 0

    @staticmethod
    def _safe_mean(
        samples: list[tuple[float, int]],
        duration: float,
    ) -> float:
        """Mean of the second element of each sample pair."""
        return (
            float(np.mean([s[1] for s in samples])) if samples and duration > 0 else 0.0
        )

    def sample(self, resource: simpy.Resource, now: float) -> None:
        """Record a snapshot of queue length and busy servers.

        Args:
            resource: The SimPy resource to sample.
            now: Current simulation time.
        """
        if now < self._cutoff:
            return
        self._queue_samples.append((now, len(resource.queue)))
        self._busy_samples.append((now, resource.count))

    def record_wait(self, wait: float, arrival: float) -> None:
        """Record a request's waiting time.

        Only records requests that *arrived* after the warmup cutoff.

        Args:
            wait: Time spent in the queue (seconds).
            arrival: Simulation time when the request arrived.
        """
        if arrival >= self._cutoff:
            self._waits.append(wait)

    def record_departure(self, now: float) -> None:
        """Record a request departure.

        Args:
            now: Current simulation time.
        """
        if now >= self._cutoff:
            self._total_requests += 1

    def result(
        self,
        lambda_: float,
        mu: float,
        cfg: SimulationConfig,
    ) -> SimulationResult:
        """Aggregate recorded stats into a SimulationResult.

        Args:
            lambda_: Arrival rate used for the run.
            mu: Service rate used for the run.
            cfg: The simulation config (for servers, seed, sim_time,
                warmup).

        Returns:
            SimulationResult with computed metrics.
        """
        n = len(self._waits)
        avg_wait = float(np.mean(self._waits)) if n > 0 else 0.0

        duration = cfg.sim_time - cfg.warmup
        avg_queue = self._safe_mean(self._queue_samples, duration)
        avg_busy = self._safe_mean(self._busy_samples, duration)
        utilization = avg_busy / cfg.servers if cfg.servers > 0 else 0.0

        return SimulationResult(
            lambda_=lambda_,
            mu=mu,
            servers=cfg.servers,
            seed=cfg.seed,
            avg_wait=avg_wait,
            avg_queue_length=avg_queue,
            server_utilization=min(utilization, 1.0),
            total_requests=self._total_requests,
        )


class SimulationEngine:
    """Discrete-event simulation of a multi-server queue.

    Args:
        arrival_gen: Source of inter-arrival times.
        service_gen: Source of service times.
        config: Simulation parameters. If ``None``, uses defaults.
    """

    def __init__(
        self,
        arrival_gen: ArrivalGenerator,
        service_gen: ServiceGenerator,
        config: SimulationConfig | None = None,
    ) -> None:
        self._arrival_gen = arrival_gen
        self._service_gen = service_gen
        self._config = config or SimulationConfig()

    def run(self) -> SimulationResult:
        """Run the simulation and collect statistics.

        Returns:
            SimulationResult with aggregated metrics.
        """
        cfg = self._config
        env = simpy.Environment()
        resource = simpy.Resource(env, capacity=cfg.servers)

        collector = _StatsCollector(cfg.warmup)

        lam = _rate_from_gen(self._arrival_gen)
        mu = _rate_from_gen(self._service_gen)

        self._assign_rngs()

        env.process(self._arrival_process(env, resource, collector))
        env.process(self._monitor_process(env, resource, collector))
        env.run(until=cfg.sim_time)

        result = collector.result(lam, mu, cfg)
        logger.info(
            f"Simulation done: λ={result.lambda_:.3f}, μ={result.mu:.3f}, "
            f"wait={result.avg_wait:.4f}s, util={result.server_utilization:.3f}"
        )
        return result

    def _arrival_process(
        self,
        env: simpy.Environment,
        resource: simpy.Resource,
        collector: _StatsCollector,
    ) -> Generator[simpy.events.Event, None, None]:
        """Generate requests according to the arrival process.

        Args:
            env: SimPy environment.
            resource: Shared server resource.
            collector: Statistics collector.

        Yields:
            SimPy timeout events between request arrivals.
        """
        while True:
            interarrival = self._arrival_gen.next_interarrival()
            yield env.timeout(interarrival)

            service_time = self._service_gen.next_service_time()
            env.process(
                self._request_lifecycle(
                    env,
                    resource,
                    service_time,
                    collector,
                )
            )

    def _monitor_process(
        self,
        env: simpy.Environment,
        resource: simpy.Resource,
        collector: _StatsCollector,
    ) -> Generator[simpy.events.Event, None, None]:
        """Periodically sample queue length and server busy count.

        Args:
            env: SimPy environment.
            resource: Shared server resource.
            collector: Statistics collector.

        Yields:
            SimPy timeout events at each monitoring tick.
        """
        while True:
            yield env.timeout(self._config.monitor_interval)
            collector.sample(resource, env.now)

    def _assign_rngs(self) -> None:
        """Assign independent RNG streams to each generator."""
        base_rng = np.random.default_rng(self._config.seed)
        arrival_rng, service_rng = base_rng.spawn(2)
        self._arrival_gen.rng = arrival_rng
        self._service_gen.rng = service_rng

    @staticmethod
    def _request_lifecycle(
        env: simpy.Environment,
        resource: simpy.Resource,
        service_time: float,
        collector: _StatsCollector,
    ) -> Generator[simpy.events.Event, None, None]:
        """Simulate one request: queue, serve, depart.

        Args:
            env: SimPy environment.
            resource: Shared server resource.
            service_time: Service duration for this request.
            collector: Statistics collector.

        Yields:
            SimPy events for resource request and service timeout.
        """
        arrival = env.now
        with resource.request() as req:
            yield req
            service_start = env.now
            collector.record_wait(service_start - arrival, arrival)
            yield env.timeout(service_time)
            collector.record_departure(env.now)
