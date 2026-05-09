"""Production orchestration for GameStates-first matrix sweep runs."""

from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor, as_completed, CancelledError
from datetime import datetime, timezone
import queue
import threading
import time

from sqlalchemy import func

from hopilot.gto.aof_hand_matrix import iter_canonical_matrix_cells
from hopilot.config import DEFAULT_CONFIG, load_config
from hopilot.gto.matrix_sweep_aggregation_service import MatrixSweepAggregationService
from hopilot.gto.matrix_sweep_contract import build_run_parameters, mark_raw_sweep_complete, mark_run_failed, validate_scenario_contract
from hopilot.hand_range import HandRange
from hopilot.logging_config import get_logger
from hopilot.models import HandMatrix, Simulation
from hopilot.database.persistence import QueuePersistenceStrategy

try:
    from tqdm import tqdm
except ImportError:  # pragma: no cover
    tqdm = None


logger = get_logger(__name__)

class MatrixSweepService:
    """Owns one full fixed-scenario matrix sweep run."""

    def __init__(self, repository, analyzer, persistence_factory):
        self.repository = repository
        self.analyzer = analyzer
        self.persistence_factory = persistence_factory

    def _capture_append_baseline(self):
        return {
            "max_simulation_id": self.repository.get_max_simulation_id(),
            "max_matrix_id": self.repository.get_max_matrix_id(),
        }

    def _validate_append_only_run(self, baseline, result):
        if result["simulation_id"] <= baseline["max_simulation_id"]:
            raise ValueError("Matrix sweep runs must append a new simulation record")
        if result["matrix_id"] <= baseline["max_matrix_id"]:
            raise ValueError("Matrix sweep runs must append a new hand matrix record")

    def _evaluate_combo(
        self,
        card_one: str,
        card_two: str,
        normalized_contract: dict[str, Any],
        write_queue: "queue.Queue[dict]",
        stop_event: threading.Event | None = None,
    ) -> bool:
        if stop_event is not None and stop_event.is_set():
            return False

        persistence = QueuePersistenceStrategy(write_queue)
        try:
            result = self.analyzer.calculate_odds_random_opponents(
                hero_hole_cards=[card_one, card_two],
                board_cards=[],
                num_opponents=normalized_contract["num_opponents"],
                num_simulations=normalized_contract["sims_per_combo"],
                persistence=persistence,
                cancel_check=stop_event.is_set if stop_event is not None else None,
                pot_size=normalized_contract["pot_size"],
                bet_amount=normalized_contract["bet_amount"],
            )
            return bool(result and result.get("valid_simulations", 0) > 0)
        except Exception:
            persistence.rollback_transaction()
            raise
        finally:
            persistence.close()

    def _apply_queue_payload(self, persistence, payload: dict[str, Any]) -> None:
        game_state = payload["game_state"]
        players = payload.get("players", [])
        bets = payload.get("bets", [])
        jackpots = payload.get("jackpots", [])

        game_state_id = persistence.store_game_state(
            timestamp=game_state["timestamp"],
            round_name=game_state["round"],
            pot_size=game_state["pot_size"],
            board_cards=game_state["board_cards"],
            outcome=game_state["outcome"],
        )

        for player in players:
            persistence.store_player(
                game_state_id=game_state_id,
                position=player["position"],
                hole_cards=player["hole_cards"],
                stack_size=player["stack_size"],
                is_hero=player["is_hero"],
                hand_class=player.get("hand_class"),
                final_strength=player.get("final_strength"),
            )

        for bet in bets:
            persistence.store_bet(
                game_state_id=game_state_id,
                player_id=bet["player_id"],
                amount=bet["amount"],
                action_type=bet["action_type"],
                round_name=bet.get("round", "preflop"),
            )

        for jackpot in jackpots:
            persistence.store_jackpot(
                game_state_id=game_state_id,
                player_id=jackpot["player_id"],
                jackpot_type=jackpot["jackpot_type"],
                payout_amount=jackpot["payout_amount"],
                cards_used=jackpot["cards_used"],
            )

    def _run_queue_writer(self, write_queue: "queue.Queue[dict]", normalized_contract: dict[str, Any]) -> None:
        session = self.repository.get_session()
        persistence = self.persistence_factory(session)
        try:
            while True:
                payload = write_queue.get()
                if payload is None:
                    break
                self._apply_queue_payload(persistence, payload)
                persistence.commit_transaction()
            persistence.close()
        finally:
            session.close()

    def run_raw_sweep(self, scenario_contract, queue_maxsize: int | None = None):
        normalized_contract = validate_scenario_contract(scenario_contract)
        if queue_maxsize is None:
            try:
                config = load_config()
            except FileNotFoundError:
                config = DEFAULT_CONFIG
            queue_maxsize = config.sweep.write_queue_maxsize
        raw_game_state_id_start = self.repository.get_latest_game_state_id() + 1
        parameters = build_run_parameters(
            normalized_contract,
            raw_game_state_id_start=raw_game_state_id_start,
        )
        simulation_id = self.repository.create_matrix_sweep_simulation(
            parameters,
            start_timestamp=datetime.now(timezone.utc),
        )

        failed_combinations = 0
        max_workers = max(1, int(normalized_contract.get("max_workers", 1)))
        stop_event = normalized_contract.get("stop_event")
        monitor_stop_event = threading.Event()

        write_queue: "queue.Queue[dict]" = queue.Queue(maxsize=queue_maxsize)
        writer_error: list[Exception] = []

        def _writer_target() -> None:
            try:
                self._run_queue_writer(write_queue, normalized_contract)
            except Exception as error:
                writer_error.append(error)
                raise

        writer_thread = threading.Thread(
            target=_writer_target,
            daemon=True,
        )
        writer_thread.start()

        def _queue_monitor() -> None:
            max_size = write_queue.maxsize if write_queue.maxsize > 0 else None
            progress_bar = None
            if tqdm is not None:
                progress_bar = tqdm(
                    total=max_size,
                    desc="Write queue",
                    unit="items",
                    dynamic_ncols=True,
                )
            warning_active = False
            while not monitor_stop_event.is_set():
                qsize = write_queue.qsize()
                if progress_bar is not None:
                    progress_bar.n = qsize
                    progress_bar.refresh()
                else:
                    effective_max = max_size if max_size is not None else max(qsize, 1)
                    fill_pct = qsize / effective_max * 100.0
                    if fill_pct > 75.0 and not warning_active:
                        logger.warning(
                            "Writer queue fill level is %.1f%% (%d/%s)",
                            fill_pct,
                            qsize,
                            effective_max,
                        )
                        warning_active = True
                    elif fill_pct <= 75.0 and warning_active:
                        warning_active = False
                time.sleep(0.05)
            if progress_bar is not None:
                progress_bar.close()

        monitor_thread = threading.Thread(target=_queue_monitor, daemon=True)
        monitor_thread.start()

        try:
            total_cells = 169
            cell_index = 0
            future_to_cell: dict = {}
            remaining_by_cell: dict[int, int] = {}
            hand_key_by_cell: dict[int, str] = {}
            stopped = False

            with ThreadPoolExecutor(max_workers=max_workers, thread_name_prefix="matrix-sweep") as executor:
                executor_shutdown = False
                for _, _, hand_key in iter_canonical_matrix_cells():
                    if stop_event is not None and stop_event.is_set():
                        stopped = True
                        executor.shutdown(wait=False, cancel_futures=True)
                        executor_shutdown = True
                        break

                    cell_index += 1
                    combos = HandRange.parse_shorthand(hand_key)
                    remaining_by_cell[cell_index] = len(combos)
                    hand_key_by_cell[cell_index] = hand_key
                    logger.info(
                        "Starting sweep cell %d/%d: %s (%d combos)",
                        cell_index,
                        total_cells,
                        hand_key,
                        len(combos),
                    )
                    for card_one, card_two in combos:
                        if stop_event is not None and stop_event.is_set():
                            stopped = True
                            executor.shutdown(wait=False, cancel_futures=True)
                            executor_shutdown = True
                            break
                        future = executor.submit(
                            self._evaluate_combo,
                            card_one,
                            card_two,
                            normalized_contract,
                            write_queue,
                            stop_event,
                        )
                        future_to_cell[future] = cell_index
                    if stopped:
                        break

                if stopped and not executor_shutdown:
                    executor.shutdown(wait=False, cancel_futures=True)

                for future in as_completed(future_to_cell):
                    cell_index = future_to_cell[future]
                    try:
                        success = future.result()
                    except CancelledError:
                        success = False
                    if not success:
                        failed_combinations += 1
                    remaining_by_cell[cell_index] -= 1
                    if remaining_by_cell[cell_index] == 0:
                        hand_key = hand_key_by_cell[cell_index]
                        logger.info(
                            "Finished sweep cell %d/%d: %s",
                            cell_index,
                            total_cells,
                            hand_key,
                        )

            write_queue.put(None)
            writer_thread.join()
            monitor_stop_event.set()
            monitor_thread.join()

            if writer_error:
                raise writer_error[0]

            if writer_thread.is_alive():
                logger.warning("Writer thread did not terminate cleanly")

            raw_game_state_id_end = self.repository.get_latest_game_state_id()
            raw_counts = self.repository.get_run_raw_counts(raw_game_state_id_start, raw_game_state_id_end)
            if stop_event is not None and stop_event.is_set():
                failed_parameters = mark_run_failed(parameters, "stopped by user")
                self.repository.update_matrix_sweep_simulation(
                    simulation_id,
                    parameters=failed_parameters,
                    end_timestamp=datetime.now(timezone.utc),
                )
                return {
                    "simulation_id": simulation_id,
                    "raw_game_states_written": raw_counts["raw_game_states"],
                    "raw_players_written": raw_counts["raw_players"],
                    "failed_combinations": failed_combinations,
                    "status": "raw_sweep_stopped",
                }

            completed_parameters = mark_raw_sweep_complete(
                parameters,
                raw_game_state_id_end=raw_game_state_id_end,
                raw_rows_written=raw_counts["raw_game_states"],
                raw_players_written=raw_counts["raw_players"],
                failed_combinations=failed_combinations,
            )
            self.repository.update_matrix_sweep_simulation(
                simulation_id,
                parameters=completed_parameters,
                end_timestamp=datetime.now(timezone.utc),
            )
            return {
                "simulation_id": simulation_id,
                "raw_game_states_written": raw_counts["raw_game_states"],
                "raw_players_written": raw_counts["raw_players"],
                "failed_combinations": failed_combinations,
                "status": "raw_sweep_complete",
            }
        except Exception as error:
            failed_parameters = mark_run_failed(parameters, str(error))
            self.repository.update_matrix_sweep_simulation(
                simulation_id,
                parameters=failed_parameters,
                end_timestamp=datetime.now(timezone.utc),
            )
            raise

    def run_sweep(self, scenario_contract):
        baseline = self._capture_append_baseline()
        raw_result = self.run_raw_sweep(scenario_contract)
        if raw_result.get("status") != "raw_sweep_complete":
            return raw_result

        # Trigger aggregation using the existing proven batch method first to ensure metrics are saved
        # This uses the original non-incremental logic that uses cell_stats dictionary
        aggregation_result = MatrixSweepAggregationService(self.repository).aggregate_run(
            raw_result["simulation_id"]
        )
        
        # Load convergence configuration from contract or defaults
        enable_tracking = scenario_contract.get("enable_convergence_tracking", True)
        if enable_tracking:
            emit_interval = scenario_contract.get("convergence_emit_interval", 100)
            logger.info("Triggering background convergence snapshot generation")
            # We call incremental mode second - it handles its own metric merging safely
            MatrixSweepAggregationService(self.repository).aggregate_run_incremental(
                raw_result["simulation_id"],
                enable_convergence_tracking=True,
                emit_interval=emit_interval
            )

        result = {
            "simulation_id": raw_result["simulation_id"],
            "matrix_id": aggregation_result["matrix_id"],
            "raw_game_states_written": raw_result["raw_game_states_written"],
            "raw_players_written": raw_result["raw_players_written"],
            "matrix_cells_written": aggregation_result["matrix_cells_written"],
            "aggregated_metrics_written": aggregation_result["aggregated_metrics_written"],
            "failed_combinations": raw_result["failed_combinations"],
            "unmapped_hero_records": aggregation_result["unmapped_hero_records"],
            "status": aggregation_result["status"],
        }
        self._validate_append_only_run(baseline, result)
        logger.info(
            "Completed append-only matrix sweep run simulation_id=%s matrix_id=%s",
            result["simulation_id"],
            result["matrix_id"],
        )
        return result

    def find_run_by_contract(self, scenario_contract):
        normalized_contract = validate_scenario_contract(scenario_contract)
        return self.repository.find_matrix_sweep_run_by_contract(normalized_contract)

    def get_run_summary(self, simulation_id):
        return self.repository.get_matrix_sweep_summary(simulation_id)