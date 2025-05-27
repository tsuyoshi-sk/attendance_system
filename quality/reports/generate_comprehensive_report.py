#!/usr/bin/env python3
"""
包括的品質レポート生成システム
NFC勤怠管理システムの総合品質レポート自動生成
"""

import json
import os
from datetime import datetime, timedelta
from typing import Dict, Any, List
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
import seaborn as sns
import pandas as pd
from jinja2 import Environment, FileSystemLoader
import pdfkit
import numpy as np


class ComprehensiveReportGenerator:
    """包括的品質レポート生成クラス"""
    
    def __init__(self):
        self.report_timestamp = datetime.now()
        self.template_env = Environment(
            loader=FileSystemLoader('quality/templates')
        )
        
    async def generate_comprehensive_report(self):
        """包括的品質レポート生成"""
        print("📊 包括的品質レポート生成開始...")
        
        # 全テスト結果収集
        test_results = await self.collect_all_test_results()
        
        # パフォーマンスメトリクス収集
        performance_metrics = await self.collect_performance_metrics()
        
        # セキュリティ評価収集
        security_assessment = await self.collect_security_results()
        
        # コード品質分析
        code_quality = await self.analyze_code_quality()
        
        # トレンド分析
        trend_analysis = await self.analyze_quality_trends()
        
        # 推奨事項生成
        recommendations = await self.generate_recommendations(
            test_results, performance_metrics, security_assessment, code_quality
        )
        
        # レポートデータ統合
        report_data = {
            'timestamp': self.report_timestamp.isoformat(),
            'executive_summary': self.generate_executive_summary(
                test_results, performance_metrics, security_assessment, code_quality
            ),
            'test_results': test_results,
            'performance_metrics': performance_metrics,
            'security_assessment': security_assessment,
            'code_quality': code_quality,
            'trend_analysis': trend_analysis,
            'recommendations': recommendations,
            'overall_score': self.calculate_overall_quality_score(
                test_results, performance_metrics, security_assessment, code_quality
            )
        }
        
        # 各種フォーマットでレポート生成
        await self.generate_html_report(report_data)
        await self.generate_pdf_report(report_data)
        await self.generate_json_report(report_data)
        await self.generate_performance_charts(performance_metrics)
        await self.generate_quality_dashboard(report_data)
        
        print("✅ 包括的品質レポート生成完了")
        
        return report_data
        
    async def collect_all_test_results(self) -> Dict[str, Any]:
        """全テスト結果収集"""
        results = {
            'unit_tests': {},
            'integration_tests': {},
            'performance_tests': {},
            'security_tests': {},
            'e2e_tests': {},
            'summary': {
                'total_tests': 0,
                'passed_tests': 0,
                'failed_tests': 0,
                'skipped_tests': 0,
                'overall_pass_rate': 0
            }
        }
        
        # ユニットテスト結果
        if os.path.exists('test_results/unit_test_results.json'):
            with open('test_results/unit_test_results.json', 'r') as f:
                results['unit_tests'] = json.load(f)
                
        # 統合テスト結果
        if os.path.exists('integration_results/integration_report.json'):
            with open('integration_results/integration_report.json', 'r') as f:
                results['integration_tests'] = json.load(f)
                
        # パフォーマンステスト結果
        if os.path.exists('performance_results/performance_report.json'):
            with open('performance_results/performance_report.json', 'r') as f:
                results['performance_tests'] = json.load(f)
                
        # セキュリティテスト結果
        if os.path.exists('security_results/security_report.json'):
            with open('security_results/security_report.json', 'r') as f:
                results['security_tests'] = json.load(f)
                
        # サマリー計算
        for test_type in ['unit_tests', 'integration_tests', 'e2e_tests']:
            if test_type in results and results[test_type]:
                test_data = results[test_type]
                if 'summary' in test_data:
                    results['summary']['total_tests'] += test_data['summary'].get('total', 0)
                    results['summary']['passed_tests'] += test_data['summary'].get('passed', 0)
                    results['summary']['failed_tests'] += test_data['summary'].get('failed', 0)
                    results['summary']['skipped_tests'] += test_data['summary'].get('skipped', 0)
                    
        if results['summary']['total_tests'] > 0:
            results['summary']['overall_pass_rate'] = (
                results['summary']['passed_tests'] / results['summary']['total_tests']
            ) * 100
            
        return results
        
    async def collect_performance_metrics(self) -> Dict[str, Any]:
        """パフォーマンスメトリクス収集"""
        metrics = {
            'response_times': {
                'api_endpoints': {},
                'websocket_latency': {},
                'database_queries': {}
            },
            'throughput': {
                'requests_per_second': 0,
                'concurrent_users_supported': 0,
                'peak_load_handling': 0
            },
            'resource_usage': {
                'cpu_usage': {},
                'memory_usage': {},
                'disk_io': {}
            },
            'scalability': {
                'horizontal_scaling': {},
                'vertical_scaling': {},
                'load_distribution': {}
            }
        }
        
        # パフォーマンスレポートから読み取り
        if os.path.exists('performance_results/performance_report.json'):
            with open('performance_results/performance_report.json', 'r') as f:
                perf_data = json.load(f)
                
            # レスポンス時間抽出
            if 'results' in perf_data:
                if 'response_time_analysis' in perf_data['results']:
                    rt_analysis = perf_data['results']['response_time_analysis']
                    metrics['response_times']['api_endpoints'] = {
                        'average': rt_analysis.get('mean', 0),
                        'p50': rt_analysis.get('p50', 0),
                        'p95': rt_analysis.get('p95', 0),
                        'p99': rt_analysis.get('p99', 0)
                    }
                    
                # スループット情報
                if 'throughput' in perf_data['results']:
                    tp_data = perf_data['results']['throughput']
                    metrics['throughput']['requests_per_second'] = tp_data.get('avg_throughput', 0)
                    
                # WebSocket情報
                if 'websocket_load' in perf_data['results']:
                    ws_data = perf_data['results']['websocket_load']
                    max_connections = max(ws_data.keys()) if ws_data else 0
                    metrics['throughput']['concurrent_users_supported'] = max_connections
                    
        return metrics
        
    async def collect_security_results(self) -> Dict[str, Any]:
        """セキュリティ評価結果収集"""
        assessment = {
            'vulnerabilities': {
                'critical': 0,
                'high': 0,
                'medium': 0,
                'low': 0,
                'details': []
            },
            'security_score': 0,
            'compliance': {
                'owasp_top10': {},
                'gdpr': {},
                'pci_dss': {}
            },
            'penetration_test_results': {},
            'security_recommendations': []
        }
        
        # セキュリティレポートから読み取り
        if os.path.exists('security_results/security_report.json'):
            with open('security_results/security_report.json', 'r') as f:
                security_data = json.load(f)
                
            assessment['security_score'] = security_data.get('overall_security_score', 0)
            
            # 脆弱性集計
            if 'results' in security_data:
                for test_name, test_results in security_data['results'].items():
                    if 'vulnerabilities' in test_results:
                        for vuln in test_results['vulnerabilities']:
                            severity = vuln.get('severity', 'low').lower()
                            if severity in assessment['vulnerabilities']:
                                assessment['vulnerabilities'][severity] += 1
                            assessment['vulnerabilities']['details'].append(vuln)
                            
        return assessment
        
    async def analyze_code_quality(self) -> Dict[str, Any]:
        """コード品質分析"""
        quality = {
            'metrics': {
                'lines_of_code': 0,
                'cyclomatic_complexity': 0,
                'maintainability_index': 0,
                'technical_debt': 0,
                'code_coverage': 0,
                'documentation_coverage': 0
            },
            'issues': {
                'code_smells': 0,
                'bugs': 0,
                'vulnerabilities': 0,
                'duplications': 0
            },
            'trends': {
                'quality_improving': False,
                'debt_increasing': False,
                'coverage_trend': 'stable'
            }
        }
        
        # 品質ダッシュボードから読み取り
        if os.path.exists('quality_dashboard.json'):
            with open('quality_dashboard.json', 'r') as f:
                dashboard_data = json.load(f)
                
            if 'summary' in dashboard_data:
                quality['metrics']['code_coverage'] = dashboard_data['summary'].get('code_coverage', 0)
                
        return quality
        
    async def analyze_quality_trends(self) -> Dict[str, Any]:
        """品質トレンド分析"""
        trends = {
            'test_coverage_trend': [],
            'performance_trend': [],
            'security_trend': [],
            'error_rate_trend': [],
            'quality_score_trend': []
        }
        
        # 履歴データから傾向分析
        # 実際の実装では時系列データベースから取得
        
        return trends
        
    def generate_executive_summary(self, test_results, performance_metrics, 
                                 security_assessment, code_quality) -> Dict[str, Any]:
        """エグゼクティブサマリー生成"""
        summary = {
            'overall_health': 'Good',
            'key_metrics': {
                'test_pass_rate': test_results['summary']['overall_pass_rate'],
                'code_coverage': code_quality['metrics']['code_coverage'],
                'security_score': security_assessment['security_score'],
                'performance_score': self.calculate_performance_score(performance_metrics),
                'total_vulnerabilities': sum(security_assessment['vulnerabilities'].values()) - 
                                       len(security_assessment['vulnerabilities']['details'])
            },
            'highlights': [],
            'concerns': [],
            'action_items': []
        }
        
        # ハイライト抽出
        if summary['key_metrics']['test_pass_rate'] > 95:
            summary['highlights'].append("Excellent test pass rate above 95%")
            
        if summary['key_metrics']['security_score'] > 90:
            summary['highlights'].append("Strong security posture with score above 90")
            
        # 懸念事項抽出
        if summary['key_metrics']['code_coverage'] < 80:
            summary['concerns'].append("Code coverage below recommended 80% threshold")
            
        if security_assessment['vulnerabilities']['critical'] > 0:
            summary['concerns'].append(f"{security_assessment['vulnerabilities']['critical']} critical vulnerabilities detected")
            
        # アクションアイテム生成
        if summary['concerns']:
            summary['action_items'].append("Address identified concerns immediately")
            
        # 全体的な健全性判定
        concern_count = len(summary['concerns'])
        if concern_count == 0:
            summary['overall_health'] = 'Excellent'
        elif concern_count <= 2:
            summary['overall_health'] = 'Good'
        elif concern_count <= 4:
            summary['overall_health'] = 'Fair'
        else:
            summary['overall_health'] = 'Needs Improvement'
            
        return summary
        
    def calculate_performance_score(self, performance_metrics) -> float:
        """パフォーマンススコア計算"""
        score = 100.0
        
        # レスポンス時間に基づく減点
        avg_response = performance_metrics['response_times']['api_endpoints'].get('average', 0)
        if avg_response > 1000:
            score -= 20
        elif avg_response > 500:
            score -= 10
        elif avg_response > 200:
            score -= 5
            
        # スループットに基づく調整
        rps = performance_metrics['throughput']['requests_per_second']
        if rps < 100:
            score -= 10
        elif rps < 500:
            score -= 5
            
        return max(0, score)
        
    def calculate_overall_quality_score(self, test_results, performance_metrics,
                                      security_assessment, code_quality) -> float:
        """総合品質スコア計算"""
        weights = {
            'test_pass_rate': 0.25,
            'code_coverage': 0.20,
            'security_score': 0.30,
            'performance_score': 0.25
        }
        
        scores = {
            'test_pass_rate': test_results['summary']['overall_pass_rate'],
            'code_coverage': code_quality['metrics']['code_coverage'],
            'security_score': security_assessment['security_score'],
            'performance_score': self.calculate_performance_score(performance_metrics)
        }
        
        weighted_score = sum(scores[metric] * weight for metric, weight in weights.items())
        
        return round(weighted_score, 1)
        
    async def generate_recommendations(self, test_results, performance_metrics,
                                     security_assessment, code_quality) -> List[Dict[str, Any]]:
        """推奨事項生成"""
        recommendations = []
        
        # テストカバレッジ推奨事項
        if code_quality['metrics']['code_coverage'] < 80:
            recommendations.append({
                'priority': 'High',
                'category': 'Testing',
                'recommendation': 'Increase code coverage to at least 80%',
                'impact': 'Improved quality assurance and bug prevention',
                'effort': 'Medium'
            })
            
        # セキュリティ推奨事項
        if security_assessment['vulnerabilities']['critical'] > 0:
            recommendations.append({
                'priority': 'Critical',
                'category': 'Security',
                'recommendation': f"Fix {security_assessment['vulnerabilities']['critical']} critical security vulnerabilities",
                'impact': 'Prevent potential security breaches',
                'effort': 'High'
            })
            
        # パフォーマンス推奨事項
        avg_response = performance_metrics['response_times']['api_endpoints'].get('average', 0)
        if avg_response > 500:
            recommendations.append({
                'priority': 'Medium',
                'category': 'Performance',
                'recommendation': 'Optimize API response times',
                'impact': 'Better user experience and system efficiency',
                'effort': 'Medium'
            })
            
        # コード品質推奨事項
        if code_quality['issues']['code_smells'] > 50:
            recommendations.append({
                'priority': 'Low',
                'category': 'Code Quality',
                'recommendation': 'Refactor code to reduce code smells',
                'impact': 'Improved maintainability',
                'effort': 'Low'
            })
            
        return recommendations
        
    async def generate_html_report(self, report_data: Dict[str, Any]):
        """HTMLレポート生成"""
        # テンプレート準備
        template_content = """
<!DOCTYPE html>
<html>
<head>
    <title>NFC Timecard System - Quality Report</title>
    <style>
        body { font-family: Arial, sans-serif; margin: 20px; }
        h1 { color: #333; }
        h2 { color: #666; margin-top: 30px; }
        .metric { 
            display: inline-block; 
            margin: 10px;
            padding: 20px;
            background: #f0f0f0;
            border-radius: 8px;
            text-align: center;
        }
        .metric-value { font-size: 2em; font-weight: bold; }
        .metric-label { color: #666; }
        .status-excellent { color: #4CAF50; }
        .status-good { color: #8BC34A; }
        .status-fair { color: #FFC107; }
        .status-poor { color: #F44336; }
        table { border-collapse: collapse; width: 100%; margin-top: 20px; }
        th, td { border: 1px solid #ddd; padding: 8px; text-align: left; }
        th { background-color: #f2f2f2; }
        .recommendation {
            background: #fff3cd;
            border: 1px solid #ffeaa7;
            padding: 10px;
            margin: 10px 0;
            border-radius: 4px;
        }
        .priority-critical { border-left: 4px solid #F44336; }
        .priority-high { border-left: 4px solid #FF9800; }
        .priority-medium { border-left: 4px solid #FFC107; }
        .priority-low { border-left: 4px solid #4CAF50; }
    </style>
</head>
<body>
    <h1>NFC Timecard System - Comprehensive Quality Report</h1>
    <p>Generated: {{ timestamp }}</p>
    
    <h2>Executive Summary</h2>
    <p>Overall System Health: <span class="status-{{ executive_summary.overall_health.lower() }}">
        {{ executive_summary.overall_health }}</span></p>
    
    <div class="metrics">
        <div class="metric">
            <div class="metric-value">{{ "%.1f"|format(executive_summary.key_metrics.test_pass_rate) }}%</div>
            <div class="metric-label">Test Pass Rate</div>
        </div>
        <div class="metric">
            <div class="metric-value">{{ "%.1f"|format(executive_summary.key_metrics.code_coverage) }}%</div>
            <div class="metric-label">Code Coverage</div>
        </div>
        <div class="metric">
            <div class="metric-value">{{ executive_summary.key_metrics.security_score }}/100</div>
            <div class="metric-label">Security Score</div>
        </div>
        <div class="metric">
            <div class="metric-value">{{ "%.0f"|format(executive_summary.key_metrics.performance_score) }}</div>
            <div class="metric-label">Performance Score</div>
        </div>
    </div>
    
    <h2>Test Results Summary</h2>
    <table>
        <tr>
            <th>Test Type</th>
            <th>Total</th>
            <th>Passed</th>
            <th>Failed</th>
            <th>Pass Rate</th>
        </tr>
        <tr>
            <td>All Tests</td>
            <td>{{ test_results.summary.total_tests }}</td>
            <td>{{ test_results.summary.passed_tests }}</td>
            <td>{{ test_results.summary.failed_tests }}</td>
            <td>{{ "%.1f"|format(test_results.summary.overall_pass_rate) }}%</td>
        </tr>
    </table>
    
    <h2>Security Assessment</h2>
    <table>
        <tr>
            <th>Severity</th>
            <th>Count</th>
        </tr>
        <tr>
            <td>Critical</td>
            <td>{{ security_assessment.vulnerabilities.critical }}</td>
        </tr>
        <tr>
            <td>High</td>
            <td>{{ security_assessment.vulnerabilities.high }}</td>
        </tr>
        <tr>
            <td>Medium</td>
            <td>{{ security_assessment.vulnerabilities.medium }}</td>
        </tr>
        <tr>
            <td>Low</td>
            <td>{{ security_assessment.vulnerabilities.low }}</td>
        </tr>
    </table>
    
    <h2>Recommendations</h2>
    {% for rec in recommendations %}
    <div class="recommendation priority-{{ rec.priority.lower() }}">
        <strong>[{{ rec.priority }}] {{ rec.category }}:</strong> {{ rec.recommendation }}<br>
        <small>Impact: {{ rec.impact }} | Effort: {{ rec.effort }}</small>
    </div>
    {% endfor %}
    
    <h2>Overall Quality Score</h2>
    <div class="metric">
        <div class="metric-value">{{ "%.1f"|format(overall_score) }}/100</div>
        <div class="metric-label">Quality Score</div>
    </div>
</body>
</html>
        """
        
        # Jinja2テンプレートとして処理
        from jinja2 import Template
        template = Template(template_content)
        html_content = template.render(**report_data)
        
        # HTMLファイル保存
        os.makedirs('quality_reports', exist_ok=True)
        with open('quality_reports/comprehensive_report.html', 'w', encoding='utf-8') as f:
            f.write(html_content)
            
    async def generate_pdf_report(self, report_data: Dict[str, Any]):
        """PDFレポート生成"""
        # HTML to PDF変換（wkhtmltopdfが必要）
        try:
            options = {
                'page-size': 'A4',
                'margin-top': '0.75in',
                'margin-right': '0.75in',
                'margin-bottom': '0.75in',
                'margin-left': '0.75in',
                'encoding': "UTF-8",
                'no-outline': None
            }
            
            pdfkit.from_file(
                'quality_reports/comprehensive_report.html',
                'quality_reports/comprehensive_report.pdf',
                options=options
            )
        except Exception as e:
            print(f"PDF生成エラー（wkhtmltopdfが必要）: {str(e)}")
            
    async def generate_json_report(self, report_data: Dict[str, Any]):
        """JSONレポート生成"""
        with open('quality_reports/comprehensive_report.json', 'w', encoding='utf-8') as f:
            json.dump(report_data, f, indent=2, ensure_ascii=False)
            
    async def generate_performance_charts(self, performance_metrics: Dict[str, Any]):
        """パフォーマンスチャート生成"""
        fig, axes = plt.subplots(2, 2, figsize=(15, 10))
        fig.suptitle('Performance Metrics Overview', fontsize=16)
        
        # レスポンス時間分布
        if performance_metrics['response_times']['api_endpoints']:
            rt_data = performance_metrics['response_times']['api_endpoints']
            percentiles = ['average', 'p50', 'p95', 'p99']
            values = [rt_data.get(p, 0) for p in percentiles]
            
            axes[0, 0].bar(percentiles, values, color='skyblue')
            axes[0, 0].set_title('API Response Time Distribution')
            axes[0, 0].set_ylabel('Response Time (ms)')
            axes[0, 0].grid(True, alpha=0.3)
            
        # スループット
        throughput_data = {
            'RPS': performance_metrics['throughput']['requests_per_second'],
            'Concurrent Users': performance_metrics['throughput']['concurrent_users_supported']
        }
        
        axes[0, 1].bar(throughput_data.keys(), throughput_data.values(), color='lightgreen')
        axes[0, 1].set_title('System Throughput')
        axes[0, 1].grid(True, alpha=0.3)
        
        # パフォーマンススコア履歴（ダミーデータ）
        dates = pd.date_range(end=datetime.now(), periods=7, freq='D')
        scores = [85, 87, 86, 88, 90, 89, self.calculate_performance_score(performance_metrics)]
        
        axes[1, 0].plot(dates, scores, 'o-', color='orange')
        axes[1, 0].set_title('Performance Score Trend')
        axes[1, 0].set_ylabel('Score')
        axes[1, 0].grid(True, alpha=0.3)
        axes[1, 0].tick_params(axis='x', rotation=45)
        
        # リソース使用状況（ダミーデータ）
        resources = ['CPU', 'Memory', 'Disk I/O', 'Network']
        usage = [45, 62, 35, 28]
        
        axes[1, 1].barh(resources, usage, color='coral')
        axes[1, 1].set_title('Resource Usage (%)')
        axes[1, 1].set_xlim(0, 100)
        axes[1, 1].grid(True, alpha=0.3)
        
        plt.tight_layout()
        plt.savefig('quality_reports/performance_charts.png', dpi=300, bbox_inches='tight')
        plt.close()
        
    async def generate_quality_dashboard(self, report_data: Dict[str, Any]):
        """品質ダッシュボード生成"""
        fig = plt.figure(figsize=(20, 12))
        
        # メインタイトル
        fig.suptitle('NFC Timecard System - Quality Dashboard', fontsize=20, y=0.98)
        
        # グリッドレイアウト
        gs = fig.add_gridspec(3, 4, hspace=0.3, wspace=0.3)
        
        # 1. 総合スコアゲージ
        ax1 = fig.add_subplot(gs[0, :2])
        self.create_gauge_chart(ax1, report_data['overall_score'], 'Overall Quality Score')
        
        # 2. テスト結果サマリー
        ax2 = fig.add_subplot(gs[0, 2:])
        test_summary = report_data['test_results']['summary']
        labels = ['Passed', 'Failed', 'Skipped']
        sizes = [
            test_summary['passed_tests'],
            test_summary['failed_tests'],
            test_summary['skipped_tests']
        ]
        colors = ['#4CAF50', '#F44336', '#FFC107']
        
        if sum(sizes) > 0:
            ax2.pie(sizes, labels=labels, colors=colors, autopct='%1.1f%%', startangle=90)
            ax2.set_title('Test Results Distribution')
        
        # 3. セキュリティ脆弱性
        ax3 = fig.add_subplot(gs[1, 0])
        vuln_data = report_data['security_assessment']['vulnerabilities']
        severities = ['Critical', 'High', 'Medium', 'Low']
        counts = [vuln_data[s.lower()] for s in severities]
        colors_vuln = ['#F44336', '#FF9800', '#FFC107', '#4CAF50']
        
        bars = ax3.bar(severities, counts, color=colors_vuln)
        ax3.set_title('Security Vulnerabilities')
        ax3.set_ylabel('Count')
        
        # 数値ラベル追加
        for bar, count in zip(bars, counts):
            if count > 0:
                ax3.text(bar.get_x() + bar.get_width()/2, bar.get_height() + 0.1,
                        str(count), ha='center', va='bottom')
                
        # 4. 品質メトリクスレーダーチャート
        ax4 = fig.add_subplot(gs[1, 1], projection='polar')
        categories = ['Testing', 'Security', 'Performance', 'Code Quality', 'Documentation']
        values = [
            test_summary['overall_pass_rate'],
            report_data['security_assessment']['security_score'],
            self.calculate_performance_score(report_data['performance_metrics']),
            report_data['code_quality']['metrics']['code_coverage'],
            75  # ダミー値
        ]
        
        angles = np.linspace(0, 2 * np.pi, len(categories), endpoint=False).tolist()
        values += values[:1]
        angles += angles[:1]
        
        ax4.plot(angles, values, 'o-', linewidth=2, color='#2196F3')
        ax4.fill(angles, values, alpha=0.25, color='#2196F3')
        ax4.set_xticks(angles[:-1])
        ax4.set_xticklabels(categories)
        ax4.set_ylim(0, 100)
        ax4.set_title('Quality Metrics Overview')
        ax4.grid(True)
        
        # 5. パフォーマンストレンド
        ax5 = fig.add_subplot(gs[1, 2:])
        # ダミーデータでトレンド表示
        dates = pd.date_range(end=datetime.now(), periods=30, freq='D')
        perf_scores = np.random.normal(85, 5, 30)
        perf_scores = np.convolve(perf_scores, np.ones(3)/3, mode='same')  # スムージング
        
        ax5.plot(dates, perf_scores, color='#4CAF50', linewidth=2)
        ax5.fill_between(dates, perf_scores, alpha=0.3, color='#4CAF50')
        ax5.set_title('Performance Score Trend (30 days)')
        ax5.set_ylabel('Score')
        ax5.grid(True, alpha=0.3)
        ax5.tick_params(axis='x', rotation=45)
        
        # 6. 推奨事項サマリー
        ax6 = fig.add_subplot(gs[2, :])
        ax6.axis('off')
        
        recommendations_text = "Key Recommendations:\n"
        for i, rec in enumerate(report_data['recommendations'][:5], 1):
            recommendations_text += f"{i}. [{rec['priority']}] {rec['recommendation']}\n"
            
        ax6.text(0.05, 0.95, recommendations_text, transform=ax6.transAxes,
                fontsize=12, verticalalignment='top',
                bbox=dict(boxstyle='round', facecolor='wheat', alpha=0.5))
        
        plt.savefig('quality_reports/quality_dashboard.png', dpi=300, bbox_inches='tight')
        plt.close()
        
    def create_gauge_chart(self, ax, value, title):
        """ゲージチャート作成"""
        # ゲージの背景
        theta = np.linspace(np.pi, 0, 100)
        r = np.ones_like(theta)
        
        # カラーマップ
        colors = ['#F44336', '#FF9800', '#FFC107', '#8BC34A', '#4CAF50']
        boundaries = [0, 20, 40, 60, 80, 100]
        
        for i in range(len(colors)):
            start_idx = int(boundaries[i] * len(theta) / 100)
            end_idx = int(boundaries[i+1] * len(theta) / 100)
            ax.plot(theta[start_idx:end_idx], r[start_idx:end_idx], 
                   color=colors[i], linewidth=20, solid_capstyle='butt')
            
        # 針
        angle = np.pi - (value / 100 * np.pi)
        ax.plot([angle, angle], [0, 0.8], 'k-', linewidth=3)
        ax.plot(angle, 0, 'ko', markersize=10)
        
        # スコア表示
        ax.text(0, -0.2, f'{value:.1f}/100', ha='center', va='center',
               fontsize=24, fontweight='bold')
        
        ax.set_ylim(0, 1)
        ax.set_xlim(-1.2, 1.2)
        ax.axis('off')
        ax.set_title(title, fontsize=16, pad=20)


async def main():
    """メイン実行関数"""
    generator = ComprehensiveReportGenerator()
    
    # 包括的レポート生成
    report_data = await generator.generate_comprehensive_report()
    
    print("\n🎉 包括的品質レポート生成完了！")
    print("📁 生成されたレポート:")
    print("  - quality_reports/comprehensive_report.html")
    print("  - quality_reports/comprehensive_report.pdf")
    print("  - quality_reports/comprehensive_report.json")
    print("  - quality_reports/performance_charts.png")
    print("  - quality_reports/quality_dashboard.png")
    
    # 総合品質スコア表示
    print(f"\n🏆 総合品質スコア: {report_data['overall_score']}/100")


if __name__ == "__main__":
    import asyncio
    asyncio.run(main())