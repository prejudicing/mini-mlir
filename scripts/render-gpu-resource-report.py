#!/usr/bin/env python3
"""Refresh NVIDIA report tables/CSVs from JSON; --html also needs python-markdown.

Run after manually verifying and updating docs/reports/nvidia-gpu-resources.json.
This script formats data; it does not fetch or automatically validate vendor specs.
"""
import argparse
import csv
import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
FOLDER = ROOT / "docs/reports"
REPORT = FOLDER / "nvidia-gpu-architecture-resources.md"


def show(value):
    if value is None:
        return "—"
    if isinstance(value, int):
        return f"{value:,}"
    if isinstance(value, float):
        return f"{value:g}"
    return str(value)


def refs(row):
    return " ".join(f"[{key}]" for key in row["sources"])


def table(headers, rows):
    def line(row):
        return "| " + " | ".join(show(value).replace("|", "\\|").replace("\n", " ") for value in row) + " |"
    return "\n".join([line(headers), line(["---"] * len(headers)), *[line(row) for row in rows]])


def export_csv(path, rows):
    fields = list(rows[0])
    with path.open("w", encoding="utf-8-sig", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        for row in rows:
            writer.writerow({key: ";".join(value) if isinstance(value, list) else value for key, value in row.items()})


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--html", action="store_true")
    args = parser.parse_args()
    data = json.loads((FOLDER / "nvidia-gpu-resources.json").read_text())
    sm, gpu, sources = data["sm_resources"], data["gpu_resources"], data["sources"]
    for row in sm + gpu:
        assert all(key in sources for key in row["sources"])
    for row in sm:
        if row["max_resident_warps_per_sm"] is not None:
            assert row["max_resident_threads_per_sm"] == row["max_resident_warps_per_sm"] * 32
        if row["shared_kib_per_block"] is not None:
            assert row["shared_kib_per_block"] <= row["shared_kib_per_sm"]

    blocks = {}
    blocks["sm_compute"] = table(
        ["架构分支", "CC", "FP32 lane / SM", "Tensor Core / SM", "RT Core / SM", "依据"],
        [[r["branch"], r["cc"], r["fp32_lanes_per_sm"], r["tensor_cores_per_sm"], r["rt_cores_per_sm"], refs(r)] for r in sm])
    blocks["sm_memory"] = table(
        ["架构分支", "32 位寄存器数量 / SM", "寄存器容量（KiB）", "Shared / SM 上限（KiB）", "Shared / block 上限（KiB）", "L1/Shared 统一池或组织", "依据"],
        [[r["branch"], r["registers_32bit_per_sm"], None if r["registers_32bit_per_sm"] is None else r["registers_32bit_per_sm"] // 256,
          r["shared_kib_per_sm"], r["shared_kib_per_block"], r["l1_shared_pool"], refs(r)] for r in sm])
    blocks["sm_occupancy"] = table(
        ["架构分支", "最大驻留 warp / SM", "最大驻留线程 / SM", "最大驻留 block / SM", "依据"],
        [[r["branch"], r["max_resident_warps_per_sm"], r["max_resident_threads_per_sm"], r["max_resident_blocks_per_sm"], refs(r)] for r in sm])
    blocks["gpu_compute"] = table(
        ["架构 / 代表配置", "芯片", "启用或公开 SM", "FP32 lane 总数", "Tensor Core 总数", "RT Core 总数", "依据"],
        [[r["architecture"] + " / " + r["product"], r["chip"], r["sm_count"], r["fp32_lanes"], r["tensor_cores"], r["rt_cores"], refs(r)] for r in gpu])
    blocks["gpu_memory"] = table(
        ["代表配置", "显存容量（GB）", "显存类型", "标称带宽（GB/s）", "L2 官方标称", "配置口径", "依据"],
        [[r["product"], r["vram_gb"], r["vram_type"], r["vram_bandwidth_gbs"], r["l2_official_label"], r["scope"], refs(r)] for r in gpu])
    blocks["sources"] = table(["编号", "NVIDIA 官方资料", "主要核验内容"], [
        [key, f'[{value["title"]}]({value["url"]})',
         "见主表对应引用；核验日期 " + data["as_of"]] for key, value in sources.items()])
    blocks["source-definitions"] = "\n".join(f'[{key}]: {value["url"]}' for key, value in sources.items())
    content = REPORT.read_text()
    for key, value in blocks.items():
        pattern = rf"<!-- BEGIN:{re.escape(key)} -->.*?<!-- END:{re.escape(key)} -->"
        replacement = f"<!-- BEGIN:{key} -->\n\n{value}\n\n<!-- END:{key} -->"
        content, count = re.subn(pattern, lambda match: replacement, content, flags=re.S)
        assert count == 1, f"missing or repeated section: {key}"
    REPORT.write_text(content)
    export_csv(FOLDER / "nvidia-gpu-sm-resources.csv", sm)
    export_csv(FOLDER / "nvidia-gpu-device-resources.csv", gpu)

    if args.html:
        import markdown
        body = markdown.markdown(content, extensions=["tables", "fenced_code", "toc", "sane_lists"])
        # Numeric table data remains identical; wrappers allow horizontal scrolling.
        body = body.replace("<table>", '<div class="table-wrap"><table>').replace("</table>", "</table></div>")
        css = """
        :root { color-scheme: light; --blue: #1d4ed8; --ink: #172b4d; }
        * { box-sizing: border-box; } html { scroll-behavior: smooth; }
        body { margin: 0; background: #f2f6fc; color: var(--ink); font: 16px/1.85 system-ui, 'Noto Sans SC', 'Microsoft YaHei', sans-serif; }
        main { max-width: 1480px; margin: 30px auto; padding: 38px 44px; background: white; border-radius: 18px; }
        h1 { font-size: 30px; color: #12366d; border-bottom: 4px solid #3b82f6; padding-bottom: 16px; }
        h2 { margin-top: 42px; font-size: 24px; color: #12366d; }
        h3 { margin-top: 28px; font-size: 20px; } a { color: var(--blue); text-decoration: none; }
        a:hover { text-decoration: underline; } code { background: #eef3fc; padding: 2px 5px; border-radius: 4px; }
        pre { overflow: auto; padding: 18px; background: #edf3fb; border-left: 4px solid #93b7f5; font-size: 14px; line-height: 1.65; }
        pre code { background: none; padding: 0; } .table-wrap { overflow-x: auto; margin: 20px 0; }
        table { width: 100%; border-collapse: collapse; font-size: 14px; line-height: 1.6; }
        th { color: white; background: #244e8a; text-align: left; white-space: nowrap; }
        th, td { border: 1px solid #d6e0ee; padding: 10px 12px; vertical-align: top; }
        tr:nth-child(even) { background: #f3f7fd; } td a { white-space: nowrap; }
        li { margin: 7px 0; } .print-note { padding: 12px 18px; background: #eaf4ff; border: 1px solid #b9d8ff; border-radius: 10px; }
        @page { size: A4 landscape; margin: 15mm; }
        @media print { body { background: white; font-size: 10pt; } main { margin: 0; padding: 0; max-width: none; }
          h1 { font-size: 22pt; } h2 { font-size: 16pt; break-after: avoid; } h3 { break-after: avoid; }
          table { font-size: 8pt; } th, td { padding: 5px; } thead { display: table-header-group; }
          tr { break-inside: avoid; } .table-wrap { overflow: visible; } .print-note { display: none; }
          a { color: #12366d; } th { color: black; background: #e8eff9; } }
        """
        html = ('<!doctype html><html lang="zh-CN"><head><meta charset="utf-8">'
                '<meta name="viewport" content="width=device-width,initial-scale=1">'
                '<title>NVIDIA GPU 架构硬件资源报告</title><style>' + css + '</style></head><body><main>'
                '<p class="print-note">资料快照：2026-11-02。宽表可横向滚动；浏览器打印建议 A4 横向。CSV/JSON 与本文件放在同一目录。</p>'
                + body + '</main></body></html>')
        (FOLDER / "nvidia-gpu-architecture-resources.html").write_text(html)
    print(f"Updated report: {len(sm)} SM branches, {len(gpu)} GPU configurations, {len(sources)} sources")


if __name__ == "__main__":
    main()
