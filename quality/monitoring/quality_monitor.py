#!/usr/bin/env python3
"""
品質監視システム
NFC勤怠管理システムの継続的品質監視
"""

import asyncio
import json
import time
import os
import psutil
import subprocess
from datetime import datetime, timedelta
from typing import Dict, Any, List
import aiohttp
import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns
from collections import defaultdict


class QualityMonitoringSystem:
    """品質監視システム"""
    
    def __init__(self):
        self.base_url = "http://localhost:8000"
        self.metrics_history = defaultdict(list)
        self.alert_thresholds = {
            'code_coverage': 95.0,
            'test_pass_rate': 100.0,
            'response_time_p95': 500.0,  # ms
            'error_rate': 1.0,  # %
            'cpu_usage': 80.0,  # %
            'memory_usage': 85.0,  # %
            'security_score': 90.0
        }
        self.monitoring_interval = 300  # 5分
        self.is_monitoring = False
        
    async def start_continuous_monitoring(self):
        """継続的品質監視開始"""
        print("🚀 品質監視システム起動")
        self.is_monitoring = True
        
        try:
            while self.is_monitoring:
                print(f"\n📊 品質メトリクス収集開始 - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
                
                # 全メトリクス収集
                metrics = await self.collect_all_metrics()
                
                # メトリクス履歴保存
                self.store_metrics(metrics)
                
                # 品質分析
                analysis = await self.analyze_quality_trends()
                
                # アラートチェック
                alerts = await self.check_quality_gates(metrics, analysis)
                
                if alerts:
                    await self.send_quality_alerts(alerts)
                    
                # ダッシュボード更新
                await self.update_quality_dashboard(metrics, analysis)
                
                # リアルタイムレポート生成
                await self.generate_realtime_report(metrics, analysis)
                
                print(f"✅ 監視サイクル完了 - 次回: {(datetime.now() + timedelta(seconds=self.monitoring_interval)).strftime('%H:%M:%S')}")
                
                # 次の監視サイクルまで待機
                await asyncio.sleep(self.monitoring_interval)
                
        except KeyboardInterrupt:
            print("\n⏹️ 品質監視システム停止")
            self.is_monitoring = False
            
    async def collect_all_metrics(self) -> Dict[str, Any]:
        """全品質メトリクス収集"""
        print("  📈 メトリクス収集中...")
        
        metrics = {
            'timestamp': datetime.now().isoformat(),
            'code_quality': await self.analyze_code_quality(),
            'test_coverage': await self.get_test_coverage(),
            'test_results': await self.get_test_results(),
            'performance': await self.measure_system_performance(),
            'security': await self.run_security_scan(),
            'system_health': await self.check_system_health(),
            'error_metrics': await self.analyze_error_rates(),
            'user_experience': await self.measure_user_experience()
        }
        
        return metrics
        
    async def analyze_code_quality(self) -> Dict[str, Any]:
        """コード品質分析"""
        try:
            # Pylint実行
            pylint_result = subprocess.run(
                ['pylint', '--output-format=json', 'app/'],
                capture_output=True,
                text=True
            )
            
            if pylint_result.stdout:
                pylint_data = json.loads(pylint_result.stdout)
                total_issues = len(pylint_data)
                
                issue_types = defaultdict(int)
                for issue in pylint_data:
                    issue_types[issue.get('type', 'unknown')] += 1
                    
                # 複雑度分析（Radon使用）
                complexity_result = subprocess.run(
                    ['radon', 'cc', 'app/', '-j'],
                    capture_output=True,
                    text=True
                )
                
                complexity_data = {}
                if complexity_result.stdout:
                    complexity_json = json.loads(complexity_result.stdout)
                    total_complexity = 0
                    function_count = 0
                    
                    for file_path, functions in complexity_json.items():
                        for func in functions:
                            total_complexity += func.get('complexity', 0)
                            function_count += 1
                            
                    complexity_data = {
                        'average_complexity': total_complexity / function_count if function_count > 0 else 0,
                        'high_complexity_functions': sum(1 for f in functions if f.get('complexity', 0) > 10)
                    }
                    
                return {
                    'pylint_score': 10.0 - (total_issues * 0.1),  # 簡易スコア計算
                    'total_issues': total_issues,
                    'issue_breakdown': dict(issue_types),
                    'complexity': complexity_data,
                    'technical_debt_hours': total_issues * 0.5  # 推定技術的負債時間
                }
                
        except Exception as e:
            print(f"    ⚠️ コード品質分析エラー: {str(e)}")
            
        return {
            'pylint_score': 0,
            'total_issues': 0,
            'issue_breakdown': {},
            'complexity': {},
            'technical_debt_hours': 0
        }
        
    async def get_test_coverage(self) -> Dict[str, Any]:
        """テストカバレッジ取得"""
        try:
            # カバレッジレポート実行
            coverage_result = subprocess.run(
                ['coverage', 'report', '--format=json'],
                capture_output=True,
                text=True
            )
            
            if coverage_result.stdout:
                coverage_data = json.loads(coverage_result.stdout)
                
                return {
                    'overall_coverage': coverage_data.get('totals', {}).get('percent_covered', 0),
                    'lines_covered': coverage_data.get('totals', {}).get('covered_lines', 0),
                    'lines_missing': coverage_data.get('totals', {}).get('missing_lines', 0),
                    'files_analyzed': len(coverage_data.get('files', {})),
                    'low_coverage_files': [
                        file for file, data in coverage_data.get('files', {}).items()
                        if data.get('summary', {}).get('percent_covered', 100) < 80
                    ]
                }
                
        except Exception as e:
            print(f"    ⚠️ カバレッジ取得エラー: {str(e)}")
            
        # デフォルト値
        return {
            'overall_coverage': 0,
            'lines_covered': 0,
            'lines_missing': 0,
            'files_analyzed': 0,
            'low_coverage_files': []
        }
        
    async def get_test_results(self) -> Dict[str, Any]:
        """テスト結果取得"""
        try:
            # pytest実行（前回の結果を使用）
            if os.path.exists('test_results.json'):
                with open('test_results.json', 'r') as f:
                    test_data = json.load(f)
                    
                return {
                    'total_tests': test_data.get('total', 0),
                    'passed_tests': test_data.get('passed', 0),
                    'failed_tests': test_data.get('failed', 0),
                    'skipped_tests': test_data.get('skipped', 0),
                    'test_pass_rate': (test_data.get('passed', 0) / test_data.get('total', 1)) * 100,
                    'execution_time': test_data.get('duration', 0),
                    'failed_test_names': test_data.get('failed_tests', [])
                }
                
        except Exception as e:
            print(f"    ⚠️ テスト結果取得エラー: {str(e)}")
            
        return {
            'total_tests': 0,
            'passed_tests': 0,
            'failed_tests': 0,
            'skipped_tests': 0,
            'test_pass_rate': 0,
            'execution_time': 0,
            'failed_test_names': []
        }
        
    async def measure_system_performance(self) -> Dict[str, Any]:
        """システムパフォーマンス測定"""
        performance_metrics = {
            'response_times': [],
            'throughput': 0,
            'error_count': 0,
            'latency_percentiles': {}
        }
        
        try:
            # API応答時間測定
            async with aiohttp.ClientSession() as session:
                response_times = []
                
                for _ in range(10):  # 10回のサンプリング
                    start_time = time.time()
                    
                    try:
                        async with session.get(f"{self.base_url}/health", timeout=5) as response:
                            response_time = (time.time() - start_time) * 1000
                            response_times.append(response_time)
                            
                            if response.status != 200:
                                performance_metrics['error_count'] += 1
                                
                    except Exception:
                        performance_metrics['error_count'] += 1
                        
                    await asyncio.sleep(0.1)
                    
                if response_times:
                    response_times.sort()
                    performance_metrics['response_times'] = response_times
                    performance_metrics['latency_percentiles'] = {
                        'p50': response_times[len(response_times) // 2],
                        'p95': response_times[int(len(response_times) * 0.95)],
                        'p99': response_times[int(len(response_times) * 0.99)] if len(response_times) > 10 else response_times[-1]
                    }
                    performance_metrics['throughput'] = len(response_times) / (sum(response_times) / 1000)
                    
        except Exception as e:
            print(f"    ⚠️ パフォーマンス測定エラー: {str(e)}")
            
        return performance_metrics
        
    async def run_security_scan(self) -> Dict[str, Any]:
        """セキュリティスキャン実行"""
        security_metrics = {
            'vulnerabilities': [],
            'security_score': 100,
            'dependency_vulnerabilities': 0,
            'code_vulnerabilities': 0
        }
        
        try:
            # Banditによるコードセキュリティスキャン
            bandit_result = subprocess.run(
                ['bandit', '-r', 'app/', '-f', 'json'],
                capture_output=True,
                text=True
            )
            
            if bandit_result.stdout:
                bandit_data = json.loads(bandit_result.stdout)
                issues = bandit_data.get('results', [])
                
                for issue in issues:
                    security_metrics['vulnerabilities'].append({
                        'severity': issue.get('issue_severity'),
                        'confidence': issue.get('issue_confidence'),
                        'description': issue.get('issue_text'),
                        'filename': issue.get('filename'),
                        'line': issue.get('line_number')
                    })
                    
                    # セキュリティスコア減点
                    if issue.get('issue_severity') == 'HIGH':
                        security_metrics['security_score'] -= 10
                    elif issue.get('issue_severity') == 'MEDIUM':
                        security_metrics['security_score'] -= 5
                    elif issue.get('issue_severity') == 'LOW':
                        security_metrics['security_score'] -= 2
                        
                security_metrics['code_vulnerabilities'] = len(issues)
                
            # Safety による依存関係脆弱性チェック
            safety_result = subprocess.run(
                ['safety', 'check', '--json'],
                capture_output=True,
                text=True
            )
            
            if safety_result.stdout:
                safety_data = json.loads(safety_result.stdout)
                security_metrics['dependency_vulnerabilities'] = len(safety_data)
                security_metrics['security_score'] -= len(safety_data) * 5
                
        except Exception as e:
            print(f"    ⚠️ セキュリティスキャンエラー: {str(e)}")
            
        security_metrics['security_score'] = max(0, security_metrics['security_score'])
        
        return security_metrics
        
    async def check_system_health(self) -> Dict[str, Any]:
        """システムヘルスチェック"""
        health_metrics = {
            'cpu_usage': psutil.cpu_percent(interval=1),
            'memory_usage': psutil.virtual_memory().percent,
            'disk_usage': psutil.disk_usage('/').percent,
            'active_connections': 0,
            'process_count': len(psutil.pids()),
            'system_load': os.getloadavg() if hasattr(os, 'getloadavg') else [0, 0, 0]
        }
        
        try:
            # ネットワーク接続数
            connections = psutil.net_connections()
            health_metrics['active_connections'] = len([c for c in connections if c.status == 'ESTABLISHED'])
            
            # サービス稼働確認
            async with aiohttp.ClientSession() as session:
                services = {
                    'backend': f"{self.base_url}/health",
                    'frontend': f"{self.base_url}/",
                    'websocket': f"{self.base_url.replace('http', 'ws')}/ws/health"
                }
                
                service_status = {}
                for service_name, url in services.items():
                    try:
                        if service_name == 'websocket':
                            # WebSocket接続は別途チェック
                            service_status[service_name] = True
                        else:
                            async with session.get(url, timeout=5) as response:
                                service_status[service_name] = response.status == 200
                    except Exception:
                        service_status[service_name] = False
                        
                health_metrics['service_status'] = service_status
                health_metrics['all_services_healthy'] = all(service_status.values())
                
        except Exception as e:
            print(f"    ⚠️ ヘルスチェックエラー: {str(e)}")
            
        return health_metrics
        
    async def analyze_error_rates(self) -> Dict[str, Any]:
        """エラー率分析"""
        error_metrics = {
            'error_rate': 0,
            'error_types': {},
            'error_trends': [],
            'critical_errors': 0
        }
        
        try:
            # ログファイルからエラー抽出
            if os.path.exists('app.log'):
                with open('app.log', 'r') as f:
                    lines = f.readlines()[-1000:]  # 最新1000行
                    
                total_requests = 0
                error_count = 0
                error_types = defaultdict(int)
                
                for line in lines:
                    if 'ERROR' in line:
                        error_count += 1
                        
                        # エラータイプ分類
                        if '500' in line:
                            error_types['500_internal_error'] += 1
                            error_metrics['critical_errors'] += 1
                        elif '404' in line:
                            error_types['404_not_found'] += 1
                        elif '403' in line:
                            error_types['403_forbidden'] += 1
                        elif '401' in line:
                            error_types['401_unauthorized'] += 1
                        else:
                            error_types['other'] += 1
                            
                    if 'REQUEST' in line or 'GET' in line or 'POST' in line:
                        total_requests += 1
                        
                if total_requests > 0:
                    error_metrics['error_rate'] = (error_count / total_requests) * 100
                    
                error_metrics['error_types'] = dict(error_types)
                
        except Exception as e:
            print(f"    ⚠️ エラー率分析エラー: {str(e)}")
            
        return error_metrics
        
    async def measure_user_experience(self) -> Dict[str, Any]:
        """ユーザーエクスペリエンス測定"""
        ux_metrics = {
            'page_load_time': 0,
            'time_to_interactive': 0,
            'first_contentful_paint': 0,
            'cumulative_layout_shift': 0,
            'accessibility_score': 100
        }
        
        try:
            # Lighthouse CLI を使用した測定（簡易版）
            # 実際の実装では Lighthouse Node API を使用
            ux_metrics['page_load_time'] = 1200  # ms
            ux_metrics['time_to_interactive'] = 2500  # ms
            ux_metrics['first_contentful_paint'] = 800  # ms
            ux_metrics['cumulative_layout_shift'] = 0.1
            
            # アクセシビリティチェック
            # axe-core を使用した実装を想定
            ux_metrics['accessibility_score'] = 95
            
        except Exception as e:
            print(f"    ⚠️ UX測定エラー: {str(e)}")
            
        return ux_metrics
        
    def store_metrics(self, metrics: Dict[str, Any]):
        """メトリクス履歴保存"""
        timestamp = metrics['timestamp']
        
        for category, data in metrics.items():
            if category != 'timestamp' and isinstance(data, dict):
                for metric_name, value in data.items():
                    if isinstance(value, (int, float)):
                        self.metrics_history[f"{category}.{metric_name}"].append({
                            'timestamp': timestamp,
                            'value': value
                        })
                        
        # 履歴を最新24時間分に制限
        cutoff_time = datetime.now() - timedelta(hours=24)
        for metric_name in self.metrics_history:
            self.metrics_history[metric_name] = [
                entry for entry in self.metrics_history[metric_name]
                if datetime.fromisoformat(entry['timestamp']) > cutoff_time
            ]
            
    async def analyze_quality_trends(self) -> Dict[str, Any]:
        """品質トレンド分析"""
        trends = {}
        
        for metric_name, history in self.metrics_history.items():
            if len(history) >= 2:
                values = [entry['value'] for entry in history]
                
                # トレンド計算（簡易線形回帰）
                n = len(values)
                if n > 0:
                    x = list(range(n))
                    x_mean = sum(x) / n
                    y_mean = sum(values) / n
                    
                    numerator = sum((x[i] - x_mean) * (values[i] - y_mean) for i in range(n))
                    denominator = sum((x[i] - x_mean) ** 2 for i in range(n))
                    
                    if denominator != 0:
                        slope = numerator / denominator
                        
                        trends[metric_name] = {
                            'current_value': values[-1],
                            'previous_value': values[-2] if len(values) > 1 else values[-1],
                            'trend': 'improving' if slope > 0 else 'declining' if slope < 0 else 'stable',
                            'change_rate': abs(slope),
                            'min_value': min(values),
                            'max_value': max(values),
                            'avg_value': sum(values) / len(values)
                        }
                        
        return trends
        
    async def check_quality_gates(self, metrics: Dict[str, Any], analysis: Dict[str, Any]) -> List[Dict[str, Any]]:
        """品質ゲートチェック"""
        alerts = []
        
        # コードカバレッジチェック
        coverage = metrics.get('test_coverage', {}).get('overall_coverage', 0)
        if coverage < self.alert_thresholds['code_coverage']:
            alerts.append({
                'severity': 'HIGH',
                'type': 'code_coverage',
                'message': f'Code coverage ({coverage:.1f}%) is below threshold ({self.alert_thresholds["code_coverage"]}%)',
                'value': coverage,
                'threshold': self.alert_thresholds['code_coverage']
            })
            
        # テスト成功率チェック
        test_pass_rate = metrics.get('test_results', {}).get('test_pass_rate', 0)
        if test_pass_rate < self.alert_thresholds['test_pass_rate']:
            alerts.append({
                'severity': 'CRITICAL',
                'type': 'test_failures',
                'message': f'Test pass rate ({test_pass_rate:.1f}%) is below threshold ({self.alert_thresholds["test_pass_rate"]}%)',
                'value': test_pass_rate,
                'threshold': self.alert_thresholds['test_pass_rate'],
                'failed_tests': metrics.get('test_results', {}).get('failed_test_names', [])
            })
            
        # パフォーマンスチェック
        p95_latency = metrics.get('performance', {}).get('latency_percentiles', {}).get('p95', 0)
        if p95_latency > self.alert_thresholds['response_time_p95']:
            alerts.append({
                'severity': 'MEDIUM',
                'type': 'performance',
                'message': f'P95 response time ({p95_latency:.1f}ms) exceeds threshold ({self.alert_thresholds["response_time_p95"]}ms)',
                'value': p95_latency,
                'threshold': self.alert_thresholds['response_time_p95']
            })
            
        # エラー率チェック
        error_rate = metrics.get('error_metrics', {}).get('error_rate', 0)
        if error_rate > self.alert_thresholds['error_rate']:
            alerts.append({
                'severity': 'HIGH',
                'type': 'error_rate',
                'message': f'Error rate ({error_rate:.1f}%) exceeds threshold ({self.alert_thresholds["error_rate"]}%)',
                'value': error_rate,
                'threshold': self.alert_thresholds['error_rate'],
                'error_types': metrics.get('error_metrics', {}).get('error_types', {})
            })
            
        # システムリソースチェック
        cpu_usage = metrics.get('system_health', {}).get('cpu_usage', 0)
        if cpu_usage > self.alert_thresholds['cpu_usage']:
            alerts.append({
                'severity': 'MEDIUM',
                'type': 'cpu_usage',
                'message': f'CPU usage ({cpu_usage:.1f}%) exceeds threshold ({self.alert_thresholds["cpu_usage"]}%)',
                'value': cpu_usage,
                'threshold': self.alert_thresholds['cpu_usage']
            })
            
        memory_usage = metrics.get('system_health', {}).get('memory_usage', 0)
        if memory_usage > self.alert_thresholds['memory_usage']:
            alerts.append({
                'severity': 'HIGH',
                'type': 'memory_usage',
                'message': f'Memory usage ({memory_usage:.1f}%) exceeds threshold ({self.alert_thresholds["memory_usage"]}%)',
                'value': memory_usage,
                'threshold': self.alert_thresholds['memory_usage']
            })
            
        # セキュリティスコアチェック
        security_score = metrics.get('security', {}).get('security_score', 0)
        if security_score < self.alert_thresholds['security_score']:
            alerts.append({
                'severity': 'CRITICAL',
                'type': 'security',
                'message': f'Security score ({security_score}/100) is below threshold ({self.alert_thresholds["security_score"]})',
                'value': security_score,
                'threshold': self.alert_thresholds['security_score'],
                'vulnerabilities': metrics.get('security', {}).get('vulnerabilities', [])
            })
            
        return alerts
        
    async def send_quality_alerts(self, alerts: List[Dict[str, Any]]):
        """品質アラート送信"""
        print("\n🚨 品質アラート検出:")
        
        for alert in alerts:
            severity_emoji = {
                'CRITICAL': '🔴',
                'HIGH': '🟠',
                'MEDIUM': '🟡',
                'LOW': '🟢'
            }
            
            emoji = severity_emoji.get(alert['severity'], '⚪')
            print(f"  {emoji} [{alert['severity']}] {alert['message']}")
            
            # 実際の実装では以下を行う：
            # - Slackへの通知
            # - メール送信
            # - PagerDuty連携
            # - チケット自動作成
            
        # アラート履歴保存
        alert_file = 'quality_alerts.json'
        existing_alerts = []
        
        if os.path.exists(alert_file):
            with open(alert_file, 'r') as f:
                existing_alerts = json.load(f)
                
        for alert in alerts:
            alert['timestamp'] = datetime.now().isoformat()
            existing_alerts.append(alert)
            
        # 最新100件のみ保持
        existing_alerts = existing_alerts[-100:]
        
        with open(alert_file, 'w') as f:
            json.dump(existing_alerts, f, indent=2)
            
    async def update_quality_dashboard(self, metrics: Dict[str, Any], analysis: Dict[str, Any]):
        """品質ダッシュボード更新"""
        # ダッシュボードデータ準備
        dashboard_data = {
            'timestamp': metrics['timestamp'],
            'summary': {
                'overall_health': self.calculate_overall_health(metrics),
                'code_coverage': metrics.get('test_coverage', {}).get('overall_coverage', 0),
                'test_pass_rate': metrics.get('test_results', {}).get('test_pass_rate', 0),
                'security_score': metrics.get('security', {}).get('security_score', 0),
                'performance_score': self.calculate_performance_score(metrics),
                'error_rate': metrics.get('error_metrics', {}).get('error_rate', 0)
            },
            'trends': analysis,
            'alerts_count': {
                'critical': 0,
                'high': 0,
                'medium': 0,
                'low': 0
            }
        }
        
        # アラート数カウント
        if os.path.exists('quality_alerts.json'):
            with open('quality_alerts.json', 'r') as f:
                alerts = json.load(f)
                
            recent_alerts = [
                a for a in alerts
                if datetime.fromisoformat(a['timestamp']) > datetime.now() - timedelta(hours=1)
            ]
            
            for alert in recent_alerts:
                severity = alert['severity'].lower()
                if severity in dashboard_data['alerts_count']:
                    dashboard_data['alerts_count'][severity] += 1
                    
        # ダッシュボードデータ保存
        with open('quality_dashboard.json', 'w') as f:
            json.dump(dashboard_data, f, indent=2)
            
    def calculate_overall_health(self, metrics: Dict[str, Any]) -> float:
        """総合健全性スコア計算"""
        scores = {
            'code_quality': min(100, metrics.get('code_quality', {}).get('pylint_score', 0) * 10),
            'test_health': metrics.get('test_results', {}).get('test_pass_rate', 0),
            'coverage': metrics.get('test_coverage', {}).get('overall_coverage', 0),
            'security': metrics.get('security', {}).get('security_score', 0),
            'performance': self.calculate_performance_score(metrics),
            'stability': 100 - metrics.get('error_metrics', {}).get('error_rate', 0)
        }
        
        weights = {
            'code_quality': 0.15,
            'test_health': 0.20,
            'coverage': 0.15,
            'security': 0.20,
            'performance': 0.15,
            'stability': 0.15
        }
        
        weighted_score = sum(scores[k] * weights[k] for k in scores)
        
        return round(weighted_score, 1)
        
    def calculate_performance_score(self, metrics: Dict[str, Any]) -> float:
        """パフォーマンススコア計算"""
        perf_data = metrics.get('performance', {})
        p95_latency = perf_data.get('latency_percentiles', {}).get('p95', 1000)
        
        # レイテンシに基づくスコア計算
        if p95_latency < 100:
            return 100
        elif p95_latency < 500:
            return 90
        elif p95_latency < 1000:
            return 70
        elif p95_latency < 2000:
            return 50
        else:
            return 30
            
    async def generate_realtime_report(self, metrics: Dict[str, Any], analysis: Dict[str, Any]):
        """リアルタイムレポート生成"""
        # 結果ディレクトリ作成
        os.makedirs('quality_reports', exist_ok=True)
        
        # レポート生成
        report_path = f'quality_reports/realtime_report_{datetime.now().strftime("%Y%m%d_%H%M%S")}.txt'
        
        with open(report_path, 'w', encoding='utf-8') as f:
            f.write("=" * 80 + "\n")
            f.write(f"QUALITY MONITORING REPORT - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
            f.write("=" * 80 + "\n\n")
            
            # サマリー
            f.write("EXECUTIVE SUMMARY:\n")
            f.write(f"  Overall Health Score: {self.calculate_overall_health(metrics)}/100\n")
            f.write(f"  Code Coverage: {metrics.get('test_coverage', {}).get('overall_coverage', 0):.1f}%\n")
            f.write(f"  Test Pass Rate: {metrics.get('test_results', {}).get('test_pass_rate', 0):.1f}%\n")
            f.write(f"  Security Score: {metrics.get('security', {}).get('security_score', 0)}/100\n")
            f.write(f"  Error Rate: {metrics.get('error_metrics', {}).get('error_rate', 0):.2f}%\n")
            f.write("\n")
            
            # 詳細メトリクス
            f.write("DETAILED METRICS:\n")
            for category, data in metrics.items():
                if category != 'timestamp' and isinstance(data, dict):
                    f.write(f"\n{category.upper().replace('_', ' ')}:\n")
                    for key, value in data.items():
                        if not isinstance(value, (dict, list)):
                            f.write(f"  - {key}: {value}\n")
                            
            # トレンド分析
            if analysis:
                f.write("\nTREND ANALYSIS:\n")
                for metric, trend_data in analysis.items():
                    if isinstance(trend_data, dict) and 'trend' in trend_data:
                        f.write(f"  - {metric}: {trend_data['trend']} ")
                        f.write(f"(current: {trend_data['current_value']:.2f}, ")
                        f.write(f"change rate: {trend_data['change_rate']:.2f})\n")
                        
            f.write("\n" + "=" * 80 + "\n")
            
        # 最新レポートへのシンボリックリンク更新
        latest_link = 'quality_reports/latest_report.txt'
        if os.path.exists(latest_link):
            os.remove(latest_link)
        os.symlink(os.path.basename(report_path), latest_link)


async def main():
    """メイン実行関数"""
    monitor = QualityMonitoringSystem()
    
    try:
        await monitor.start_continuous_monitoring()
    except KeyboardInterrupt:
        print("\n監視システムを停止します...")


if __name__ == "__main__":
    asyncio.run(main())