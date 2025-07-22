#!/usr/bin/env python3
"""
Analyst Bee Class - 分析専門エージェント
Issue #4: 基本的な自律実行システム

コードベース分析・品質評価・パフォーマンス分析を専門とするAnalyst Bee
"""

import json
import os
from datetime import datetime
from pathlib import Path
from typing import Any

from .config import BeehiveConfig, get_config
from .exceptions import (
    TaskExecutionError,
    error_handler,
)
from .worker_bee import WorkerBee


class AnalystBee(WorkerBee):
    """分析専門のWorker Beeクラス

    コードベース分析、品質メトリクス、パフォーマンス評価を専門とする
    """

    def __init__(self, config: BeehiveConfig | None = None) -> None:
        """Analyst Beeを初期化

        Args:
            config: 設定オブジェクト
        """
        self.config = config or get_config()
        super().__init__("analyst", "analysis", self.config)

        # 分析結果の保存ディレクトリ
        self.analysis_output_dir = Path("analysis_reports")
        self.analysis_output_dir.mkdir(exist_ok=True)

        self.logger.log_event(
            "analyst_initialization",
            "Analyst Bee initialized - Ready for code analysis and quality assessment",
            "INFO",
            specialty="analysis",
            capabilities=self.capabilities,
        )

    def _define_capabilities(self) -> list[str]:
        """Analyst Bee固有の能力を定義

        Returns:
            分析能力のリスト
        """
        return [
            "performance_analysis",
            "code_metrics",
            "quality_assessment",
            "report_generation",
            "dependency_analysis",
            "security_scan",
            "test_coverage",
            "complexity_analysis",
            "architecture_review",
        ]

    @error_handler
    def performance_analysis(self, target_path: str, task_id: int | None = None) -> dict[str, Any]:
        """パフォーマンス分析を実行

        Args:
            target_path: 分析対象のパス
            task_id: 関連タスクID

        Returns:
            パフォーマンス分析結果

        Raises:
            TaskExecutionError: 分析実行に失敗した場合
        """
        try:
            self.logger.log_event(
                "performance_analysis_started",
                f"Starting performance analysis: {target_path}",
                "INFO",
                target_path=target_path,
                task_id=task_id,
            )

            analysis_result = {
                "analysis_type": "performance",
                "target_path": target_path,
                "timestamp": datetime.now().isoformat(),
                "metrics": {},
                "recommendations": [],
                "summary": "",
            }

            # ファイルサイズと行数の基本メトリクス
            if os.path.isfile(target_path):
                file_stats = self._analyze_file_performance(target_path)
                analysis_result["metrics"].update(file_stats)
            elif os.path.isdir(target_path):
                dir_stats = self._analyze_directory_performance(target_path)
                analysis_result["metrics"].update(dir_stats)

            # パフォーマンス推奨事項
            analysis_result["recommendations"] = self._generate_performance_recommendations(
                analysis_result["metrics"]
            )

            # サマリー生成
            analysis_result["summary"] = self._generate_performance_summary(analysis_result)

            # 結果をファイルに保存
            self._save_analysis_report(analysis_result, "performance")

            self.logger.log_event(
                "performance_analysis_completed",
                f"Performance analysis completed: {target_path}",
                "INFO",
                metrics_count=len(analysis_result["metrics"]),
                recommendations_count=len(analysis_result["recommendations"]),
            )

            return analysis_result

        except Exception as e:
            self.logger.error(f"Performance analysis failed: {e}", error=e)
            raise TaskExecutionError(
                task_id=task_id or 0,
                bee_name=self.bee_name,
                stage="performance_analysis",
                original_error=e,
            )

    @error_handler
    def code_metrics(self, target_path: str, task_id: int | None = None) -> dict[str, Any]:
        """コード品質メトリクスを計算

        Args:
            target_path: 分析対象のパス
            task_id: 関連タスクID

        Returns:
            コードメトリクス結果

        Raises:
            TaskExecutionError: メトリクス計算に失敗した場合
        """
        try:
            self.logger.log_event(
                "code_metrics_started",
                f"Starting code metrics analysis: {target_path}",
                "INFO",
                target_path=target_path,
                task_id=task_id,
            )

            metrics_result = {
                "analysis_type": "code_metrics",
                "target_path": target_path,
                "timestamp": datetime.now().isoformat(),
                "metrics": {},
                "quality_score": 0.0,
                "issues": [],
                "summary": "",
            }

            # 基本的なコードメトリクス
            if os.path.isfile(target_path):
                file_metrics = self._calculate_file_metrics(target_path)
                metrics_result["metrics"].update(file_metrics)
            elif os.path.isdir(target_path):
                dir_metrics = self._calculate_directory_metrics(target_path)
                metrics_result["metrics"].update(dir_metrics)

            # 品質スコア計算
            metrics_result["quality_score"] = self._calculate_quality_score(
                metrics_result["metrics"]
            )

            # 品質問題の検出
            metrics_result["issues"] = self._detect_quality_issues(metrics_result["metrics"])

            # サマリー生成
            metrics_result["summary"] = self._generate_metrics_summary(metrics_result)

            # 結果をファイルに保存
            self._save_analysis_report(metrics_result, "code_metrics")

            self.logger.log_event(
                "code_metrics_completed",
                f"Code metrics analysis completed: {target_path}",
                "INFO",
                quality_score=metrics_result["quality_score"],
                issues_count=len(metrics_result["issues"]),
            )

            return metrics_result

        except Exception as e:
            self.logger.error(f"Code metrics analysis failed: {e}", error=e)
            raise TaskExecutionError(
                task_id=task_id or 0, bee_name=self.bee_name, stage="code_metrics", original_error=e
            )

    @error_handler
    def quality_assessment(self, target_path: str, task_id: int | None = None) -> dict[str, Any]:
        """品質評価を実行

        Args:
            target_path: 評価対象のパス
            task_id: 関連タスクID

        Returns:
            品質評価結果

        Raises:
            TaskExecutionError: 品質評価に失敗した場合
        """
        try:
            self.logger.log_event(
                "quality_assessment_started",
                f"Starting quality assessment: {target_path}",
                "INFO",
                target_path=target_path,
                task_id=task_id,
            )

            # パフォーマンス分析とコードメトリクスを実行
            performance_result = self.performance_analysis(target_path, task_id)
            metrics_result = self.code_metrics(target_path, task_id)

            # 総合品質評価
            assessment_result = {
                "analysis_type": "quality_assessment",
                "target_path": target_path,
                "timestamp": datetime.now().isoformat(),
                "overall_score": 0.0,
                "performance_score": 0.0,
                "metrics_score": 0.0,
                "assessment_details": {
                    "performance": performance_result,
                    "metrics": metrics_result,
                },
                "recommendations": [],
                "priority_issues": [],
                "summary": "",
            }

            # 各スコアの計算
            assessment_result["performance_score"] = self._calculate_performance_score(
                performance_result
            )
            assessment_result["metrics_score"] = metrics_result["quality_score"]

            # 総合スコア（重み付き平均）
            assessment_result["overall_score"] = (
                assessment_result["performance_score"] * 0.4
                + assessment_result["metrics_score"] * 0.6
            )

            # 優先的な問題の特定
            assessment_result["priority_issues"] = self._identify_priority_issues(
                performance_result, metrics_result
            )

            # 改善提案
            assessment_result["recommendations"] = self._generate_quality_recommendations(
                assessment_result
            )

            # 総合サマリー
            assessment_result["summary"] = self._generate_assessment_summary(assessment_result)

            # 結果をファイルに保存
            self._save_analysis_report(assessment_result, "quality_assessment")

            self.logger.log_event(
                "quality_assessment_completed",
                f"Quality assessment completed: {target_path}",
                "INFO",
                overall_score=assessment_result["overall_score"],
                priority_issues_count=len(assessment_result["priority_issues"]),
            )

            return assessment_result

        except Exception as e:
            self.logger.error(f"Quality assessment failed: {e}", error=e)
            raise TaskExecutionError(
                task_id=task_id or 0,
                bee_name=self.bee_name,
                stage="quality_assessment",
                original_error=e,
            )

    @error_handler
    def report_generation(
        self, analysis_results: list[dict[str, Any]], task_id: int | None = None
    ) -> str:
        """分析結果からレポートを生成

        Args:
            analysis_results: 分析結果のリスト
            task_id: 関連タスクID

        Returns:
            生成されたレポートファイルのパス

        Raises:
            TaskExecutionError: レポート生成に失敗した場合
        """
        try:
            self.logger.log_event(
                "report_generation_started",
                f"Starting report generation for {len(analysis_results)} results",
                "INFO",
                results_count=len(analysis_results),
                task_id=task_id,
            )

            report_timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            report_filename = f"analysis_report_{report_timestamp}.md"
            report_path = self.analysis_output_dir / report_filename

            # Markdownレポート生成
            report_content = self._generate_markdown_report(analysis_results)

            # レポートをファイルに書き込み
            with open(report_path, "w", encoding="utf-8") as f:
                f.write(report_content)

            self.logger.log_event(
                "report_generation_completed",
                f"Report generated: {report_path}",
                "INFO",
                report_path=str(report_path),
                content_length=len(report_content),
            )

            return str(report_path)

        except Exception as e:
            self.logger.error(f"Report generation failed: {e}", error=e)
            raise TaskExecutionError(
                task_id=task_id or 0,
                bee_name=self.bee_name,
                stage="report_generation",
                original_error=e,
            )

    def _analyze_file_performance(self, file_path: str) -> dict[str, Any]:
        """ファイルのパフォーマンス分析"""
        try:
            file_stats = os.stat(file_path)
            with open(file_path, encoding="utf-8", errors="ignore") as f:
                content = f.read()
                lines = content.split("\n")

            return {
                "file_size_bytes": file_stats.st_size,
                "file_size_kb": round(file_stats.st_size / 1024, 2),
                "line_count": len(lines),
                "character_count": len(content),
                "average_line_length": len(content) / max(len(lines), 1),
                "last_modified": datetime.fromtimestamp(file_stats.st_mtime).isoformat(),
            }
        except Exception:
            return {"error": f"Failed to analyze file: {file_path}"}

    def _analyze_directory_performance(self, dir_path: str) -> dict[str, Any]:
        """ディレクトリのパフォーマンス分析"""
        try:
            total_size = 0
            total_files = 0
            file_types = {}

            for root, _dirs, files in os.walk(dir_path):
                for file in files:
                    file_path = os.path.join(root, file)
                    try:
                        file_stats = os.stat(file_path)
                        total_size += file_stats.st_size
                        total_files += 1

                        # ファイルタイプ別集計
                        ext = os.path.splitext(file)[1].lower()
                        file_types[ext] = file_types.get(ext, 0) + 1
                    except OSError:
                        continue

            return {
                "total_size_bytes": total_size,
                "total_size_mb": round(total_size / (1024 * 1024), 2),
                "total_files": total_files,
                "file_types": file_types,
                "average_file_size": total_size / max(total_files, 1),
            }
        except Exception:
            return {"error": f"Failed to analyze directory: {dir_path}"}

    def _calculate_file_metrics(self, file_path: str) -> dict[str, Any]:
        """ファイルのコードメトリクス計算"""
        try:
            with open(file_path, encoding="utf-8", errors="ignore") as f:
                lines = f.readlines()

            # 基本メトリクス
            total_lines = len(lines)
            blank_lines = sum(1 for line in lines if not line.strip())
            comment_lines = sum(
                1 for line in lines if line.strip().startswith(("#", "//", "/*", "*", "--"))
            )
            code_lines = total_lines - blank_lines - comment_lines

            # 複雑度の簡易計算（制御構造をカウント）
            complexity_keywords = [
                "if",
                "elif",
                "else",
                "for",
                "while",
                "try",
                "except",
                "finally",
                "with",
            ]
            complexity_count = 0
            for line in lines:
                line_stripped = line.strip().lower()
                for keyword in complexity_keywords:
                    if keyword in line_stripped:
                        complexity_count += 1

            return {
                "total_lines": total_lines,
                "code_lines": code_lines,
                "blank_lines": blank_lines,
                "comment_lines": comment_lines,
                "comment_ratio": comment_lines / max(total_lines, 1),
                "cyclomatic_complexity": complexity_count,
                "maintainability_index": min(100, max(0, 100 - complexity_count * 2)),
            }
        except Exception:
            return {"error": f"Failed to calculate metrics for file: {file_path}"}

    def _calculate_directory_metrics(self, dir_path: str) -> dict[str, Any]:
        """ディレクトリのコードメトリクス計算"""
        try:
            total_metrics = {
                "total_lines": 0,
                "code_lines": 0,
                "blank_lines": 0,
                "comment_lines": 0,
                "cyclomatic_complexity": 0,
                "file_count": 0,
            }

            code_extensions = {
                ".py",
                ".js",
                ".ts",
                ".java",
                ".cpp",
                ".c",
                ".h",
                ".go",
                ".rs",
                ".rb",
            }

            for root, _dirs, files in os.walk(dir_path):
                for file in files:
                    if any(file.endswith(ext) for ext in code_extensions):
                        file_path = os.path.join(root, file)
                        file_metrics = self._calculate_file_metrics(file_path)

                        if "error" not in file_metrics:
                            for key in total_metrics:
                                if key != "file_count":
                                    total_metrics[key] += file_metrics.get(key, 0)
                            total_metrics["file_count"] += 1

            # 平均値を計算
            if total_metrics["file_count"] > 0:
                total_metrics["average_complexity"] = (
                    total_metrics["cyclomatic_complexity"] / total_metrics["file_count"]
                )
                total_metrics["average_lines_per_file"] = (
                    total_metrics["total_lines"] / total_metrics["file_count"]
                )
                total_metrics["comment_ratio"] = total_metrics["comment_lines"] / max(
                    total_metrics["total_lines"], 1
                )

            return total_metrics
        except Exception:
            return {"error": f"Failed to calculate metrics for directory: {dir_path}"}

    def _calculate_quality_score(self, metrics: dict[str, Any]) -> float:
        """品質スコアを計算（0-100）"""
        if "error" in metrics:
            return 0.0

        score = 100.0

        # コメント率による減点/加点
        comment_ratio = metrics.get("comment_ratio", 0)
        if comment_ratio < 0.1:  # 10%未満
            score -= 20
        elif comment_ratio > 0.3:  # 30%以上
            score += 10

        # 複雑度による減点
        complexity = metrics.get("cyclomatic_complexity", 0)
        if complexity > 20:
            score -= min(30, (complexity - 20) * 2)

        # 保守性指数
        maintainability = metrics.get("maintainability_index", 100)
        score = (score + maintainability) / 2

        return max(0.0, min(100.0, score))

    def _calculate_performance_score(self, performance_result: dict[str, Any]) -> float:
        """パフォーマンススコアを計算（0-100）"""
        metrics = performance_result.get("metrics", {})
        if "error" in metrics:
            return 0.0

        score = 100.0

        # ファイルサイズによる減点
        if "file_size_kb" in metrics:
            size_kb = metrics["file_size_kb"]
            if size_kb > 100:  # 100KB以上
                score -= min(30, (size_kb - 100) / 10)

        # 行数による減点
        if "line_count" in metrics:
            lines = metrics["line_count"]
            if lines > 500:  # 500行以上
                score -= min(25, (lines - 500) / 50)

        return max(0.0, min(100.0, score))

    def _detect_quality_issues(self, metrics: dict[str, Any]) -> list[dict[str, str]]:
        """品質問題を検出"""
        issues = []

        if "error" in metrics:
            issues.append(
                {
                    "type": "analysis_error",
                    "severity": "high",
                    "message": "Failed to analyze code metrics",
                }
            )
            return issues

        # コメント不足
        comment_ratio = metrics.get("comment_ratio", 0)
        if comment_ratio < 0.1:
            issues.append(
                {
                    "type": "documentation",
                    "severity": "medium",
                    "message": f"Low comment ratio: {comment_ratio:.2%}. Consider adding more documentation.",
                }
            )

        # 高い複雑度
        complexity = metrics.get("cyclomatic_complexity", 0)
        if complexity > 15:
            issues.append(
                {
                    "type": "complexity",
                    "severity": "high" if complexity > 25 else "medium",
                    "message": f"High cyclomatic complexity: {complexity}. Consider refactoring.",
                }
            )

        # 低い保守性
        maintainability = metrics.get("maintainability_index", 100)
        if maintainability < 50:
            issues.append(
                {
                    "type": "maintainability",
                    "severity": "high" if maintainability < 25 else "medium",
                    "message": f"Low maintainability index: {maintainability:.1f}. Code may be difficult to maintain.",
                }
            )

        return issues

    def _generate_performance_recommendations(self, metrics: dict[str, Any]) -> list[str]:
        """パフォーマンス改善提案を生成"""
        recommendations = []

        if "error" in metrics:
            return ["Fix analysis errors before proceeding with performance optimization"]

        # ファイルサイズに基づく推奨事項
        if "file_size_kb" in metrics and metrics["file_size_kb"] > 50:
            recommendations.append(
                "Consider splitting large files into smaller, more focused modules"
            )

        # 行数に基づく推奨事項
        if "line_count" in metrics and metrics["line_count"] > 300:
            recommendations.append(
                "Large files detected - consider refactoring into smaller components"
            )

        # ファイルタイプに基づく推奨事項
        if "file_types" in metrics:
            file_types = metrics["file_types"]
            if file_types.get(".py", 0) > 20:
                recommendations.append(
                    "Many Python files detected - consider using __init__.py for package organization"
                )

        if not recommendations:
            recommendations.append(
                "Performance metrics look good - no immediate optimizations needed"
            )

        return recommendations

    def _generate_quality_recommendations(self, assessment: dict[str, Any]) -> list[str]:
        """品質改善提案を生成"""
        recommendations = []

        overall_score = assessment.get("overall_score", 0)
        priority_issues = assessment.get("priority_issues", [])

        if overall_score < 70:
            recommendations.append(
                "Overall code quality needs improvement - focus on addressing high-priority issues"
            )

        for issue in priority_issues:
            if issue["type"] == "complexity":
                recommendations.append(
                    "Reduce cyclomatic complexity by extracting methods and simplifying logic"
                )
            elif issue["type"] == "documentation":
                recommendations.append(
                    "Add comprehensive documentation and comments to improve code readability"
                )
            elif issue["type"] == "maintainability":
                recommendations.append(
                    "Improve code maintainability by refactoring and following best practices"
                )

        if not recommendations:
            recommendations.append("Code quality is good - focus on maintaining current standards")

        return recommendations

    def _identify_priority_issues(
        self, performance_result: dict[str, Any], metrics_result: dict[str, Any]
    ) -> list[dict[str, str]]:
        """優先的な問題を特定"""
        priority_issues = []

        # メトリクスからの高優先度問題
        for issue in metrics_result.get("issues", []):
            if issue["severity"] == "high":
                priority_issues.append(issue)

        # パフォーマンスの問題
        perf_metrics = performance_result.get("metrics", {})
        if "file_size_kb" in perf_metrics and perf_metrics["file_size_kb"] > 100:
            priority_issues.append(
                {
                    "type": "performance",
                    "severity": "high",
                    "message": f"Large file size: {perf_metrics['file_size_kb']}KB. Consider splitting.",
                }
            )

        return priority_issues

    def _generate_performance_summary(self, result: dict[str, Any]) -> str:
        """パフォーマンス分析サマリー生成"""
        metrics = result.get("metrics", {})
        if "error" in metrics:
            return "Performance analysis failed due to errors"

        summary_parts = []

        if "file_size_kb" in metrics:
            summary_parts.append(f"File size: {metrics['file_size_kb']}KB")
        if "line_count" in metrics:
            summary_parts.append(f"Lines: {metrics['line_count']}")
        if "total_files" in metrics:
            summary_parts.append(f"Files: {metrics['total_files']}")

        rec_count = len(result.get("recommendations", []))
        summary_parts.append(f"Recommendations: {rec_count}")

        return " | ".join(summary_parts)

    def _generate_metrics_summary(self, result: dict[str, Any]) -> str:
        """コードメトリクスサマリー生成"""
        quality_score = result.get("quality_score", 0)
        issues_count = len(result.get("issues", []))

        return f"Quality Score: {quality_score:.1f}/100 | Issues: {issues_count}"

    def _generate_assessment_summary(self, result: dict[str, Any]) -> str:
        """品質評価サマリー生成"""
        overall_score = result.get("overall_score", 0)
        priority_issues = len(result.get("priority_issues", []))

        score_level = (
            "Excellent"
            if overall_score >= 90
            else "Good"
            if overall_score >= 70
            else "Fair"
            if overall_score >= 50
            else "Poor"
        )

        return f"Overall Quality: {score_level} ({overall_score:.1f}/100) | Priority Issues: {priority_issues}"

    def _save_analysis_report(self, result: dict[str, Any], analysis_type: str) -> None:
        """分析結果をファイルに保存"""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"{analysis_type}_{timestamp}.json"
        filepath = self.analysis_output_dir / filename

        try:
            with open(filepath, "w", encoding="utf-8") as f:
                json.dump(result, f, indent=2, ensure_ascii=False)
            self.logger.debug(f"Analysis result saved: {filepath}")
        except Exception as e:
            self.logger.warning(f"Failed to save analysis result: {e}")

    def _generate_markdown_report(self, analysis_results: list[dict[str, Any]]) -> str:
        """Markdownフォーマットのレポート生成"""
        report_lines = [
            "# 分析レポート",
            "",
            f"**生成日時:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
            f"**分析結果数:** {len(analysis_results)}",
            "",
            "## 分析結果サマリー",
            "",
        ]

        # 各分析結果のサマリー
        for i, result in enumerate(analysis_results, 1):
            analysis_type = result.get("analysis_type", "unknown")
            target_path = result.get("target_path", "N/A")
            summary = result.get("summary", "No summary available")

            report_lines.extend(
                [
                    f"### {i}. {analysis_type.title()} - {target_path}",
                    f"**サマリー:** {summary}",
                    "",
                ]
            )

            # 詳細情報の追加
            if "overall_score" in result:
                report_lines.append(f"**総合スコア:** {result['overall_score']:.1f}/100")
            if "quality_score" in result:
                report_lines.append(f"**品質スコア:** {result['quality_score']:.1f}/100")

            # 推奨事項
            recommendations = result.get("recommendations", [])
            if recommendations:
                report_lines.append("**推奨事項:**")
                for rec in recommendations[:3]:  # 最大3つまで
                    report_lines.append(f"- {rec}")

            report_lines.append("")

        # フッター
        report_lines.extend(["---", f"*Generated by Analyst Bee - {self.bee_name}*"])

        return "\n".join(report_lines)

    def _process_message(self, message: dict[str, Any]):
        """Analyst Bee固有のメッセージ処理"""
        # 分析関連のメッセージを処理
        if "analysis" in message.get("content", "").lower():
            self._handle_analysis_request(message)
        elif "report" in message.get("content", "").lower():
            self._handle_report_request(message)
        else:
            # 基底クラスの処理を呼び出し
            super()._process_message(message)

    def _handle_analysis_request(self, message: dict[str, Any]):
        """分析要請を処理"""
        from_bee = message.get("from_bee")
        task_id = message.get("task_id")

        # 分析対象の抽出（簡易実装）
        target_path = "."  # デフォルトは現在のディレクトリ

        try:
            # 総合品質評価を実行
            assessment_result = self.quality_assessment(target_path, task_id)

            response = (
                f"分析を完了しました。品質スコア: {assessment_result['overall_score']:.1f}/100"
            )

            self.send_message(from_bee, "response", "分析結果", response, task_id)

        except Exception as e:
            error_response = f"分析中にエラーが発生しました: {str(e)}"
            self.send_message(from_bee, "response", "分析エラー", error_response, task_id)

        self.mark_message_processed(message.get("message_id"))

    def _handle_report_request(self, message: dict[str, Any]):
        """レポート要請を処理"""
        from_bee = message.get("from_bee")

        try:
            # 既存の分析結果を収集
            analysis_files = list(self.analysis_output_dir.glob("*.json"))
            analysis_results = []

            for file_path in analysis_files[-5:]:  # 最新5件
                try:
                    with open(file_path, encoding="utf-8") as f:
                        analysis_results.append(json.load(f))
                except Exception:
                    continue

            if analysis_results:
                report_path = self.report_generation(analysis_results)
                response = f"レポートを生成しました: {report_path}"
            else:
                response = "レポート生成用の分析結果がありません"

            self.send_message(from_bee, "response", "レポート生成完了", response)

        except Exception as e:
            error_response = f"レポート生成中にエラーが発生しました: {str(e)}"
            self.send_message(from_bee, "response", "レポート生成エラー", error_response)

        self.mark_message_processed(message.get("message_id"))
