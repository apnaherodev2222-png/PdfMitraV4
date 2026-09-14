"""Rich transport metrics with no HTTP or event-loop dependency."""
import time
from collections import Counter

class RichMetrics:
    """FIX_PM_103: track rich-vs-fallback ratio and latency."""
    def __init__(self):
        self.sent = 0
        self.failed = 0
        self.fallback_used = 0
        self.circuit_skips = 0
        self.total_latency_ms = 0.0
        self.fail_reasons = Counter()
        self.block_type_counts = Counter()
        self.started_at = time.monotonic()

    def record_send(self, latency_ms: float):
        self.sent += 1
        self.total_latency_ms += latency_ms

    def record_fail(self, reason: str):
        self.failed += 1
        self.fail_reasons[str(reason)[:60]] += 1

    def record_fallback(self):
        self.fallback_used += 1

    def record_blocks(self, blocks):
        for b in blocks:
            if isinstance(b, dict):
                t = b.get("type")
                if isinstance(t, str):
                    self.block_type_counts[t] += 1

    def get_block_type_counts(self) -> Counter:
        return self.block_type_counts

    def record_circuit_skip(self):
        self.circuit_skips += 1

    def report(self) -> str:
        avg = (self.total_latency_ms / self.sent) if self.sent else 0.0
        uptime = time.monotonic() - self.started_at
        lines = [
            "📊 Rich Message Transport",
            f"Uptime: {uptime/60:.1f} min",
            f"Sent OK: {self.sent}",
            f"Failed: {self.failed}",
            f"Fallback used: {self.fallback_used}",
            f"Circuit skips: {self.circuit_skips}",
            f"Avg latency: {avg:.0f} ms",
        ]
        if self.fail_reasons:
            lines.append("Top fails:")
            for reason, count in self.fail_reasons.most_common(3):
                lines.append(f"  • {reason} ×{count}")
        return "\n".join(lines)

METRICS = RichMetrics()

def rich_metrics_report() -> str:
    return METRICS.report()

def get_block_type_counts() -> Counter:
    return METRICS.get_block_type_counts()

__all__ = ["RichMetrics", "METRICS", "rich_metrics_report", "get_block_type_counts"]
