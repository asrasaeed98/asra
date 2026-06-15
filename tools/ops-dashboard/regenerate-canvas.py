#!/usr/bin/env python3
"""Regenerate findings-ops-dashboard.canvas.tsx from build-partial-ops-data.py output."""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
CANVAS_REPO = ROOT / "tools/ops-dashboard/findings-ops-dashboard.canvas.tsx"
CANVAS_CURSOR = (
    Path.home() / ".cursor/projects/Users-asrasaeed-asra/canvases/findings-ops-dashboard.canvas.tsx"
)
BUILD = ROOT / "scripts/build-partial-ops-data.py"
PY = ROOT / "apps/api/.venv/bin/python"
TZ = "America/New_York"


def main() -> int:
    raw = subprocess.check_output([str(PY), str(BUILD)], cwd=ROOT, text=True)
    data = json.loads(raw)

    sessions_js = json.dumps(data["all_sessions"], indent=2)
    api_usage_js = json.dumps(data["api_usage"], indent=2)
    visitors_js = json.dumps(data.get("visitors", {}), indent=2)
    fetched = data["fetched_at"]
    catalog_total = data["catalog"]["total"]
    date_min = data["date_bounds"]["min"]
    date_max = data["date_bounds"]["max"]
    total_sessions = len(data["all_sessions"])

    canvas_src = CANVAS_TEMPLATE.format(
        fetched=fetched,
        catalog_total=catalog_total,
        date_min=date_min,
        date_max=date_max,
        total_sessions=total_sessions,
        sessions_js=sessions_js,
        api_usage_js=api_usage_js,
        visitors_js=visitors_js,
        tz=TZ,
    )
    CANVAS_REPO.parent.mkdir(parents=True, exist_ok=True)
    CANVAS_REPO.write_text(canvas_src)
    CANVAS_CURSOR.parent.mkdir(parents=True, exist_ok=True)
    CANVAS_CURSOR.write_text(canvas_src)
    print(f"Wrote {CANVAS_REPO}")
    print(f"Wrote {CANVAS_CURSOR}")
    return 0


CANVAS_TEMPLATE = '''import {{
  BarChart,
  Button,
  Callout,
  Card,
  CardBody,
  CardHeader,
  Grid,
  H1,
  PieChart,
  Row,
  Select,
  Spacer,
  Stack,
  Stat,
  Table,
  Text,
  TextInput,
  useCanvasAction,
  useCanvasState,
}} from "cursor/canvas";

type SessionRecord = {{
  id: string;
  status: string;
  resource_count: number;
  duration_sec: number | null;
  day: string;
  created_at: string;
  error: string | null;
}};

type DurationStats = {{
  count: number;
  mean_sec: number;
  median_sec: number;
  p90_sec: number;
  max_sec: number;
  min_sec: number;
}};

const TIMEZONE = "{tz}";
const FETCHED_AT = "{fetched}";
const CATALOG_TOTAL = {catalog_total};
const DATE_MIN = "{date_min}";
const DATE_MAX = "{date_max}";
const ALL_SESSIONS: SessionRecord[] = {sessions_js};
const API_USAGE = {api_usage_js};
const VISITORS = {visitors_js};

const LIMITATIONS = {{
  users: "Unique visitors use an anonymous browser UUID (localStorage), not accounts.",
  time_on_app: "Time on site is approximated by page views — not dwell time per page.",
  window_note: "Based on last {total_sessions} analysis runs. Use the date filter below.",
}};

function formatSec(sec: number | null | undefined): string {{
  if (sec == null) return "—";
  if (sec < 60) return `${{Math.round(sec)}}s`;
  const m = Math.floor(sec / 60);
  const s = Math.round(sec % 60);
  return s > 0 ? `${{m}}m ${{s}}s` : `${{m}}m`;
}}

function formatEt(iso: string, withDate = true): string {{
  const d = new Date(iso);
  if (withDate) {{
    return `${{d.toLocaleString("en-US", {{
      dateStyle: "medium",
      timeStyle: "short",
      timeZone: TIMEZONE,
    }})}} ET`;
  }}
  return `${{d.toLocaleTimeString("en-US", {{
    hour: "numeric",
    minute: "2-digit",
    timeZone: TIMEZONE,
  }})}} ET`;
}}

function shortReason(reason: string): string {{
  if (reason.startsWith("World Bank")) return "World Bank unavailable";
  if (reason.startsWith("Load was interrupted")) return "Load interrupted / timeout";
  if (reason.startsWith("Analysis took longer")) return "Analysis stale timeout";
  if (reason.startsWith("Invalid Input")) return "JSON ingest error";
  return reason.length > 42 ? `${{reason.slice(0, 42)}}…` : reason;
}}

function statusTone(
  status: string,
): "success" | "danger" | "warning" | "info" | "neutral" {{
  if (status === "complete") return "success";
  if (status === "failed") return "danger";
  if (status === "ingesting" || status === "analyzing") return "info";
  return "neutral";
}}

function percentile(sorted: number[], p: number): number {{
  if (sorted.length === 0) return 0;
  if (sorted.length === 1) return sorted[0];
  const k = (sorted.length - 1) * (p / 100);
  const f = Math.floor(k);
  const c = Math.min(f + 1, sorted.length - 1);
  if (f === c) return sorted[f];
  return sorted[f] + (sorted[c] - sorted[f]) * (k - f);
}}

function durationStats(durations: number[]): DurationStats | null {{
  if (durations.length === 0) return null;
  const s = [...durations].sort((a, b) => a - b);
  const sum = s.reduce((a, b) => a + b, 0);
  const mid = Math.floor(s.length / 2);
  const median = s.length % 2 === 0 ? (s[mid - 1] + s[mid]) / 2 : s[mid];
  return {{
    count: s.length,
    mean_sec: Math.round((sum / s.length) * 10) / 10,
    median_sec: Math.round(median * 10) / 10,
    p90_sec: Math.round(percentile(s, 90) * 10) / 10,
    max_sec: Math.round(s[s.length - 1] * 10) / 10,
    min_sec: Math.round(s[0] * 10) / 10,
  }};
}}

function addDays(isoDay: string, delta: number): string {{
  const [y, m, d] = isoDay.split("-").map(Number);
  const dt = new Date(Date.UTC(y, m - 1, d));
  dt.setUTCDate(dt.getUTCDate() + delta);
  return dt.toISOString().slice(0, 10);
}}

function resolveRange(
  preset: string,
  from: string,
  to: string,
): {{ from: string; to: string; label: string }} {{
  if (preset === "7d") {{
    const start = addDays(DATE_MAX, -6);
    return {{ from: start < DATE_MIN ? DATE_MIN : start, to: DATE_MAX, label: "Last 7 days" }};
  }}
  if (preset === "30d") {{
    const start = addDays(DATE_MAX, -29);
    return {{ from: start < DATE_MIN ? DATE_MIN : start, to: DATE_MAX, label: "Last 30 days" }};
  }}
  if (preset === "custom" && from && to) {{
    return {{ from: from < to ? from : to, to: from < to ? to : from, label: `${{from}} → ${{to}}` }};
  }}
  return {{ from: DATE_MIN, to: DATE_MAX, label: "All loaded runs" }};
}}

function filterSessions(sessions: SessionRecord[], from: string, to: string): SessionRecord[] {{
  return sessions.filter((s) => s.day && s.day >= from && s.day <= to);
}}

function aggregate(sessions: SessionRecord[]) {{
  const byStatus: Record<string, number> = {{}};
  const failures: Record<string, number> = {{}};
  const daily: Record<string, number> = {{}};
  const completeDurations: number[] = [];
  const allDurations: number[] = [];
  let twoDataset = 0;

  for (const s of sessions) {{
    byStatus[s.status] = (byStatus[s.status] ?? 0) + 1;
    if (s.day) daily[s.day] = (daily[s.day] ?? 0) + 1;
    if (s.duration_sec != null) {{
      allDurations.push(s.duration_sec);
      if (s.status === "complete") completeDurations.push(s.duration_sec);
    }}
    if (s.status === "failed" && s.error) {{
      failures[s.error] = (failures[s.error] ?? 0) + 1;
    }}
    if (s.resource_count >= 2) twoDataset += 1;
  }}

  const failureReasons = Object.entries(failures)
    .sort((a, b) => b[1] - a[1])
    .slice(0, 6)
    .map(([reason, count]) => ({{ reason, count }}));

  const dailyRuns = Object.entries(daily)
    .sort((a, b) => a[0].localeCompare(b[0]))
    .map(([day, runs]) => ({{ day, runs }}));

  return {{
    count: sessions.length,
    byStatus,
    twoDataset,
    durationComplete: durationStats(completeDurations),
    durationAll: durationStats(allDurations),
    dailyRuns,
    failureReasons,
    tableSessions: sessions.slice(0, 25),
  }};
}}

export default function FindingsOpsDashboard() {{
  const dispatch = useCanvasAction();
  const [preset, setPreset] = useCanvasState("datePreset", "all");
  const [dateFrom, setDateFrom] = useCanvasState("dateFrom", DATE_MIN);
  const [dateTo, setDateTo] = useCanvasState("dateTo", DATE_MAX);

  const range = resolveRange(preset, dateFrom, dateTo);
  const filtered = filterSessions(ALL_SESSIONS, range.from, range.to);
  const agg = aggregate(filtered);

  const complete = agg.byStatus.complete ?? 0;
  const failed = agg.byStatus.failed ?? 0;
  const sampled = agg.count;
  const successRate = sampled > 0 ? Math.round((complete / sampled) * 100) : 0;
  const currentAi = API_USAGE[0];
  const dur = agg.durationComplete;

  const statusPie = Object.entries(agg.byStatus).map(([label, value]) => ({{
    label,
    value,
    tone: statusTone(label),
  }}));

  const failureChart = agg.failureReasons.slice(0, 5).map((f) => ({{
    label: shortReason(f.reason),
    value: f.count,
  }}));

  return (
    <Stack gap={{20}}>
      <Row align="center" wrap>
        <Stack gap={{4}}>
          <H1>Findings ops dashboard</H1>
          <Text tone="secondary" size="small">
            Source: production API · fetched {{formatEt(FETCHED_AT)}} (Eastern)
          </Text>
        </Stack>
        <Spacer />
        <Button
          variant="primary"
          onClick={{() =>
            dispatch({{
              type: "newComposerChat",
              userPrompt:
                "Refresh the Findings ops dashboard canvas with latest production metrics.",
            }})
          }}
        >
          Refresh in chat
        </Button>
      </Row>

      <Card>
        <CardHeader label="Date filter (Eastern)" />
        <CardBody>
          <Row gap={{12}} align="end" wrap>
            <Stack gap={{4}} style={{{{ minWidth: 180 }}}}>
              <Text size="small" tone="secondary">
                Range
              </Text>
              <Select
                value={{preset}}
                onChange={{setPreset}}
                options={{[
                  {{ value: "all", label: "All loaded runs" }},
                  {{ value: "7d", label: "Last 7 days" }},
                  {{ value: "30d", label: "Last 30 days" }},
                  {{ value: "custom", label: "Custom range" }},
                ]}}
              />
            </Stack>
            {{preset === "custom" ? (
              <>
                <Stack gap={{4}} style={{{{ minWidth: 140 }}}}>
                  <Text size="small" tone="secondary">
                    From (ET date)
                  </Text>
                  <TextInput
                    value={{dateFrom}}
                    onChange={{setDateFrom}}
                    placeholder="YYYY-MM-DD"
                  />
                </Stack>
                <Stack gap={{4}} style={{{{ minWidth: 140 }}}}>
                  <Text size="small" tone="secondary">
                    To (ET date)
                  </Text>
                  <TextInput
                    value={{dateTo}}
                    onChange={{setDateTo}}
                    placeholder="YYYY-MM-DD"
                  />
                </Stack>
              </>
            ) : null}}
            <Stack gap={{4}}>
              <Text size="small" tone="secondary">
                Showing
              </Text>
              <Text weight="semibold">
                {{range.label}} · {{sampled}} run{{sampled === 1 ? "" : "s"}}
              </Text>
              <Text size="small" tone="tertiary">
                Data spans {{DATE_MIN}} to {{DATE_MAX}} (Eastern dates)
              </Text>
            </Stack>
          </Row>
        </CardBody>
      </Card>

      <Callout tone="info">
        <Stack gap={{6}}>
          <Text weight="semibold">What this measures</Text>
          <Text size="small">{{LIMITATIONS.users}}</Text>
          <Text size="small">{{LIMITATIONS.time_on_app}}</Text>
          <Text size="small" tone="secondary">
            {{LIMITATIONS.window_note}} Times and dates use US Eastern (ET). AI usage table is monthly.
          </Text>
          <Text size="small" tone="secondary">{{VISITORS.note}}</Text>
        </Stack>
      </Callout>

      {{VISITORS.total_page_views > 0 ? (
        <Card>
          <CardHeader label="Unique visitors (anonymous)" />
          <CardBody>
            <Grid columns={{4}} gap={{12}}>
              <Stat
                label="Unique visitors (30d)"
                value={{String(VISITORS.unique_visitors_in_window)}}
                tone="info"
              />
              <Stat
                label="Page views (30d)"
                value={{String(VISITORS.page_views_in_window)}}
                tone="neutral"
              />
              <Stat
                label="Visitors who ran analysis"
                value={{String(VISITORS.unique_visitors_with_analysis)}}
                tone="success"
              />
              <Stat
                label="Unique visitors (all time)"
                value={{String(VISITORS.unique_visitors_all_time)}}
                tone="neutral"
              />
            </Grid>
            {{VISITORS.daily_unique_visitors.length > 0 ? (
              <Stack gap={{8}} style={{{{ marginTop: 16 }}}}>
                <Text size="small" weight="semibold">Daily unique visitors (ET)</Text>
                <BarChart
                  categories={{VISITORS.daily_unique_visitors.map((d) => String(d.day).slice(5))}}
                  series={{[{{
                    name: "Unique visitors",
                    data: VISITORS.daily_unique_visitors.map((d) => d.visitors),
                    tone: "info",
                  }}]}}
                  height={{180}}
                />
              </Stack>
            ) : null}}
            {{VISITORS.top_paths.length > 0 ? (
              <Stack gap={{8}} style={{{{ marginTop: 16 }}}}>
                <Text size="small" weight="semibold">Top pages (30d)</Text>
                <Table
                  headers={{["Path", "Views", "Unique visitors"]}}
                  rows={{VISITORS.top_paths.map((p) => [
                    p.path,
                    String(p.views),
                    String(p.visitors),
                  ])}}
                />
              </Stack>
            ) : null}}
          </CardBody>
        </Card>
      ) : null}}

      {{sampled === 0 ? (
        <Callout tone="warning" title="No runs in this date range">
          <Text size="small">Adjust the filter — loaded data only covers {{DATE_MIN}} through {{DATE_MAX}} (ET).</Text>
        </Callout>
      ) : (
        <>
          <Grid columns={{4}} gap={{12}}>
            <Stat label="Analysis runs" value={{String(sampled)}} tone="info" />
            <Stat label="Completed" value={{`${{complete}} (${{successRate}}%)`}} tone="success" />
            <Stat label="Failed" value={{String(failed)}} tone="danger" />
            <Stat label="Catalog resources" value={{String(CATALOG_TOTAL)}} tone="neutral" />
          </Grid>

          <Grid columns={{4}} gap={{12}}>
            <Stat
              label="Median analysis time (complete)"
              value={{formatSec(dur?.median_sec)}}
              tone="info"
            />
            <Stat label="P90 analysis time" value={{formatSec(dur?.p90_sec)}} tone="info" />
            <Stat
              label="Two-dataset runs"
              value={{`${{agg.twoDataset}} (${{sampled > 0 ? Math.round((agg.twoDataset / sampled) * 100) : 0}}%)`}}
              tone="neutral"
            />
            <Stat
              label="AI spend (current month)"
              value={{`$${{currentAi.cost_usd.toFixed(2)}} · ${{currentAi.calls}} calls`}}
              tone="warning"
            />
          </Grid>

          {{agg.dailyRuns.length > 0 ? (
            <Grid columns={{2}} gap={{16}}>
              <Card>
                <CardHeader label="Analysis runs per day (ET)" />
                <CardBody>
                  <BarChart
                    categories={{agg.dailyRuns.map((d) => d.day.slice(5))}}
                    series={{[{{ name: "Runs", data: agg.dailyRuns.map((d) => d.runs), tone: "info" }}]}}
                    height={{200}}
                  />
                  <Text size="small" tone="secondary" style={{{{ marginTop: 8 }}}}>
                    Eastern dates · {{range.from}} to {{range.to}}
                  </Text>
                </CardBody>
              </Card>

              {{statusPie.length > 0 ? (
                <Card>
                  <CardHeader label="Run status mix" />
                  <CardBody>
                    <Row align="center" gap={{24}}>
                      <PieChart data={{statusPie}} size={{160}} donut />
                      <Stack gap={{6}}>
                        {{statusPie.map((s) => (
                          <Text key={{s.label}} size="small">
                            {{s.label}}: {{s.value}}
                          </Text>
                        ))}}
                      </Stack>
                    </Row>
                    <Text size="small" tone="secondary" style={{{{ marginTop: 8 }}}}>
                      Source: {{sampled}} sessions in selected range
                    </Text>
                  </CardBody>
                </Card>
              ) : null}}
            </Grid>
          ) : null}}

          {{dur ? (
            <Card>
              <CardHeader label="Completed analysis duration" />
              <CardBody>
                <Grid columns={{5}} gap={{12}}>
                  <Stat label="Runs" value={{String(dur.count)}} tone="neutral" />
                  <Stat label="Median" value={{formatSec(dur.median_sec)}} tone="info" />
                  <Stat label="Mean" value={{formatSec(dur.mean_sec)}} tone="info" />
                  <Stat label="P90" value={{formatSec(dur.p90_sec)}} tone="info" />
                  <Stat label="Max" value={{formatSec(dur.max_sec)}} tone="warning" />
                </Grid>
                {{agg.durationAll ? (
                  <Text size="small" tone="secondary" style={{{{ marginTop: 12 }}}}>
                    All statuses mean: {{formatSec(agg.durationAll.mean_sec)}} (includes failed/stuck runs).
                  </Text>
                ) : null}}
              </CardBody>
            </Card>
          ) : null}}

          <Grid columns={{2}} gap={{16}}>
            {{failureChart.length > 0 ? (
              <Card>
                <CardHeader label="Top failure reasons" />
                <CardBody>
                  <BarChart
                    categories={{failureChart.map((f) => f.label)}}
                    series={{[
                      {{ name: "Failures", data: failureChart.map((f) => f.value), tone: "danger" }},
                    ]}}
                    horizontal
                    height={{220}}
                  />
                  <Text size="small" tone="secondary" style={{{{ marginTop: 8 }}}}>
                    Source: failed runs in selected range
                  </Text>
                </CardBody>
              </Card>
            ) : null}}

            <Card>
              <CardHeader label="Anthropic API usage" />
              <CardBody>
                <Table
                  headers={{["Month", "Calls", "Tokens in", "Tokens out", "Est. cost"]}}
                  rows={{API_USAGE.map((u) => [
                    u.month,
                    String(u.calls),
                    u.tokens_in.toLocaleString(),
                    u.tokens_out.toLocaleString(),
                    `$${{u.cost_usd.toFixed(2)}}`,
                  ])}}
                />
                <Text size="small" tone="secondary" style={{{{ marginTop: 8 }}}}>
                  Monthly ledger — not filtered by date range above
                </Text>
              </CardBody>
            </Card>
          </Grid>

          <Card>
            <CardHeader label="Analysis runs in range" />
            <CardBody>
              <Table
                headers={{["When (ET)", "Session", "Status", "Datasets", "Duration", "Error"]}}
                rows={{agg.tableSessions.map((s) => [
                  s.created_at,
                  s.id,
                  s.status,
                  String(s.resource_count),
                  formatSec(s.duration_sec),
                  s.error ? shortReason(s.error) : "—",
                ])}}
                rowTone={{agg.tableSessions.map((s) => statusTone(s.status))}}
              />
              {{sampled > 25 ? (
                <Text size="small" tone="secondary" style={{{{ marginTop: 8 }}}}>
                  Showing 25 of {{sampled}} runs
                </Text>
              ) : null}}
            </CardBody>
          </Card>
        </>
      )}}

      <Text size="small" tone="tertiary">
        Filter state is saved with the canvas. Ask in chat to refresh underlying data.
      </Text>
    </Stack>
  );
}}
'''


if __name__ == "__main__":
    raise SystemExit(main())
