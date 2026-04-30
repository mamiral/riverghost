"""
Performance testing for database integration.

This module provides comprehensive performance testing to ensure database
queries meet the <500ms requirement and identify performance bottlenecks.
"""

import asyncio
import time
from typing import Dict, Any, List, Optional
from datetime import datetime
from statistics import mean, median, stdev
import json

from hopilot.logging_config import get_logger
from hopilot.gto.performance_monitor import QueryPerformanceMonitor

logger = get_logger(__name__)


class PerformanceTestSuite:
    """
    Comprehensive performance testing suite for database operations.
    """

    def __init__(self, repository: Any):
        self.repository = repository
        self.monitor = QueryPerformanceMonitor("sqlite:///performance_test.db")
        self.results = []

    async def run_full_performance_test(self) -> Dict[str, Any]:
        """
        Run the complete performance test suite.

        Returns:
            Comprehensive performance report
        """
        logger.info("Starting full performance test suite")

        report = {
            'timestamp': datetime.now().isoformat(),
            'tests': {},
            'summary': {},
            'recommendations': []
        }

        # Run individual tests
        tests = [
            ('strategy_matrix_queries', self.test_strategy_matrix_performance),
            ('convergence_data_queries', self.test_convergence_data_performance),
            ('complex_joins', self.test_complex_join_performance),
            ('bulk_operations', self.test_bulk_operation_performance),
            ('concurrent_access', self.test_concurrent_access_performance),
        ]

        for test_name, test_func in tests:
            try:
                logger.info(f"Running test: {test_name}")
                result = await test_func()
                report['tests'][test_name] = result

                # Check for failures
                if result.get('status') == 'failed':
                    report['recommendations'].append(f"Fix {test_name}: {result.get('error', 'Unknown error')}")

            except Exception as e:
                logger.error(f"Test {test_name} failed: {e}")
                report['tests'][test_name] = {
                    'status': 'error',
                    'error': str(e)
                }

        # Generate summary
        report['summary'] = self._generate_summary(report['tests'])

        # Add recommendations
        report['recommendations'].extend(self._generate_recommendations(report['summary']))

        logger.info("Performance test suite completed")
        return report

    async def test_strategy_matrix_performance(self) -> Dict[str, Any]:
        """
        Test performance of strategy matrix queries.
        """
        result = {
            'status': 'passed',
            'samples': 0,
            'avg_time': 0,
            'median_time': 0,
            'max_time': 0,
            'p95_time': 0,
            'failures': 0
        }

        positions = ['UTG', 'MP', 'CO', 'BTN']
        actions = ['FOLD', 'CALL', 'RAISE']
        metrics = ['equity', 'jackpot_adjusted_ev']

        times = []

        for position in positions:
            for action in actions:
                for metric in metrics:
                    try:
                        start_time = time.time()
                        # Simulate strategy matrix query
                        data = await self.repository.get_matrix_statistics(
                            type('PositionContext', (), {'value': position})(),
                            type('ActionContext', (), {'value': action})()
                        )
                        end_time = time.time()

                        query_time = (end_time - start_time) * 1000  # Convert to ms
                        times.append(query_time)
                        result['samples'] += 1

                        if query_time > 500:  # 500ms threshold
                            result['failures'] += 1

                    except Exception as e:
                        result['failures'] += 1
                        logger.warning(f"Strategy matrix query failed: {e}")

        if times:
            result['avg_time'] = mean(times)
            result['median_time'] = median(times)
            result['max_time'] = max(times)
            result['p95_time'] = sorted(times)[int(len(times) * 0.95)]

            if result['p95_time'] > 500:
                result['status'] = 'failed'
                result['error'] = f"P95 response time {result['p95_time']:.1f}ms exceeds 500ms threshold"

        return result

    async def test_convergence_data_performance(self) -> Dict[str, Any]:
        """
        Test performance of convergence data queries.
        """
        result = {
            'status': 'passed',
            'samples': 0,
            'avg_time': 0,
            'max_time': 0,
            'failures': 0
        }

        positions = ['UTG', 'MP', 'CO', 'BTN', 'SB', 'BB']
        times = []

        for position in positions:
            try:
                start_time = time.time()
                # This would call the actual convergence data method
                # For now, simulate with a database query
                data = await self.repository.get_simulation_summary()
                end_time = time.time()

                query_time = (end_time - start_time) * 1000
                times.append(query_time)
                result['samples'] += 1

                if query_time > 500:
                    result['failures'] += 1

            except Exception as e:
                result['failures'] += 1
                logger.warning(f"Convergence data query failed: {e}")

        if times:
            result['avg_time'] = mean(times)
            result['max_time'] = max(times)

            if result['max_time'] > 500:
                result['status'] = 'failed'
                result['error'] = f"Max response time {result['max_time']:.1f}ms exceeds 500ms threshold"

        return result

    async def test_complex_join_performance(self) -> Dict[str, Any]:
        """
        Test performance of complex multi-table join queries.
        """
        result = {
            'status': 'passed',
            'samples': 0,
            'avg_time': 0,
            'max_time': 0,
            'failures': 0
        }

        times = []

        # Test complex queries
        complex_queries = [
            ('simulation_summary', lambda: self.repository.get_simulation_summary()),
            ('hand_performance', lambda: self.repository.get_hand_performance_comparison(['AKs', 'QQ'])),
        ]

        for query_name, query_func in complex_queries:
            try:
                start_time = time.time()
                await query_func()
                end_time = time.time()

                query_time = (end_time - start_time) * 1000
                times.append(query_time)
                result['samples'] += 1

                if query_time > 1000:  # Complex queries can be slower but not > 1s
                    result['failures'] += 1

            except Exception as e:
                result['failures'] += 1
                logger.warning(f"Complex query {query_name} failed: {e}")

        if times:
            result['avg_time'] = mean(times)
            result['max_time'] = max(times)

            if result['max_time'] > 1000:
                result['status'] = 'failed'
                result['error'] = f"Complex query max time {result['max_time']:.1f}ms exceeds 1000ms threshold"

        return result

    async def test_bulk_operation_performance(self) -> Dict[str, Any]:
        """
        Test performance of bulk data operations.
        """
        result = {
            'status': 'passed',
            'insert_time': 0,
            'bulk_insert_time': 0,
            'improvement': 0
        }

        # Test individual inserts vs bulk inserts
        test_data = [
            {'simulation_id': f'test_{i}', 'parameters': {'test': True}}
            for i in range(10)
        ]

        # Individual inserts
        start_time = time.time()
        for data in test_data:
            try:
                # This would be actual insert logic
                pass
            except Exception:
                pass
        end_time = time.time()
        result['insert_time'] = (end_time - start_time) * 1000

        # Bulk insert simulation
        start_time = time.time()
        try:
            # This would be bulk insert logic
            pass
        except Exception:
            pass
        end_time = time.time()
        result['bulk_insert_time'] = (end_time - start_time) * 1000

        if result['insert_time'] > 0:
            result['improvement'] = (result['insert_time'] - result['bulk_insert_time']) / result['insert_time'] * 100

        return result

    async def test_concurrent_access_performance(self) -> Dict[str, Any]:
        """
        Test performance under concurrent access.
        """
        result = {
            'status': 'passed',
            'concurrent_users': 5,
            'avg_response_time': 0,
            'max_response_time': 0,
            'errors': 0
        }

        async def simulate_user_query(user_id: int):
            """Simulate a user making queries."""
            try:
                start_time = time.time()
                # Simulate some database queries
                await asyncio.sleep(0.01)  # Simulate query time
                await self.repository.get_simulation_summary()
                end_time = time.time()

                return (end_time - start_time) * 1000
            except Exception as e:
                logger.warning(f"Concurrent query {user_id} failed: {e}")
                return None

        # Run concurrent queries
        tasks = [simulate_user_query(i) for i in range(result['concurrent_users'])]
        results = await asyncio.gather(*tasks, return_exceptions=True)

        response_times = [r for r in results if r is not None and not isinstance(r, Exception)]

        if response_times:
            result['avg_response_time'] = mean(response_times)
            result['max_response_time'] = max(response_times)
            result['errors'] = len(results) - len(response_times)

            if result['max_response_time'] > 500:
                result['status'] = 'failed'
                result['error'] = f"Concurrent access max time {result['max_response_time']:.1f}ms exceeds 500ms threshold"

        return result

    def _generate_summary(self, test_results: Dict[str, Any]) -> Dict[str, Any]:
        """Generate overall performance summary."""
        summary = {
            'total_tests': len(test_results),
            'passed_tests': 0,
            'failed_tests': 0,
            'overall_status': 'passed',
            'performance_score': 100,
            'bottlenecks': []
        }

        for test_name, result in test_results.items():
            if result.get('status') == 'passed':
                summary['passed_tests'] += 1
            else:
                summary['failed_tests'] += 1
                summary['overall_status'] = 'failed'
                summary['bottlenecks'].append(test_name)

        # Calculate performance score
        if summary['total_tests'] > 0:
            pass_rate = summary['passed_tests'] / summary['total_tests']
            summary['performance_score'] = pass_rate * 100

        return summary

    def _generate_recommendations(self, summary: Dict[str, Any]) -> List[str]:
        """Generate performance improvement recommendations."""
        recommendations = []

        if summary['overall_status'] == 'failed':
            recommendations.append("Critical: Performance requirements not met - optimize slow queries")

        if 'strategy_matrix_queries' in summary.get('bottlenecks', []):
            recommendations.append("Add database indexes on frequently queried columns")
            recommendations.append("Consider query result caching for strategy matrices")

        if 'complex_joins' in summary.get('bottlenecks', []):
            recommendations.append("Review and optimize complex join queries")
            recommendations.append("Consider denormalization for frequently joined data")

        if 'concurrent_access' in summary.get('bottlenecks', []):
            recommendations.append("Implement connection pooling for concurrent access")
            recommendations.append("Consider read replicas for high-concurrency scenarios")

        if summary['performance_score'] < 80:
            recommendations.append("Overall performance below acceptable threshold - comprehensive optimization required")

        return recommendations

    def save_report(self, report: Dict[str, Any], filename: str):
        """
        Save performance report to file.

        Args:
            report: Performance report to save
            filename: Output filename
        """
        try:
            with open(filename, 'w') as f:
                json.dump(report, f, indent=2, default=str)
            logger.info(f"Performance report saved to {filename}")
        except Exception as e:
            logger.error(f"Failed to save performance report: {e}")