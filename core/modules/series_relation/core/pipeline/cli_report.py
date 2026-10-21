"""CLI 人读短报告（无图时用文字交代核心结论）。"""

from __future__ import annotations

from typing import Any, List, Mapping


def format_cli_report(meta: Mapping[str, Any], summary: Mapping[str, Any]) -> str:
    key = str(meta.get("key") or "series_relation")
    lines: List[str] = [
        f"=== series_relation report: {key} ===",
        f"normalize={meta.get('normalize')}  fill={meta.get('fill')}  "
        f"series={summary.get('series_count')}  calendar={summary.get('calendar_len')}",
        "",
        "[系列]",
    ]
    for item in meta.get("series") or []:
        extra = ""
        if item.get("source") == "strategy_sim":
            sk = item.get("strategy_key") or item.get("strategy")
            extra = (
                f"  [sim {sk}@"
                f"{item.get('resolved_version') or item.get('version')} "
                f"{item.get('layer')}.{item.get('metric')}"
            )
            if item.get("entity_id"):
                extra += f" {item.get('entity_id')}"
            if item.get("transform"):
                extra += f" transform={item.get('transform')}"
            extra += "]"
        elif item.get("transform") and item.get("transform") != "none":
            extra = f"  [transform={item.get('transform')}]"
        lines.append(
            f"  {item.get('id')}  {item.get('label')}: "
            f"n={item.get('point_count')}  "
            f"[{item.get('date_min')} .. {item.get('date_max')}]{extra}"
        )

    pairwise = list(summary.get("pairwise") or [])
    if not pairwise:
        lines.extend(["", "[结论] 未做两两分析（analyze=false 或系列不足）。", ""])
        return "\n".join(lines)

    by_id = {
        str(item.get("id") or ""): item
        for item in (meta.get("series") or [])
        if isinstance(item, Mapping)
    }
    lines.extend(["", "[参与者] 下面找关系的都是谁", ""])
    for item in meta.get("series") or []:
        if not isinstance(item, Mapping):
            continue
        who = _participant_who(item)
        lines.append(
            f"  {item.get('id')}  {item.get('label')}"
            + (f"  ← {who}" if who else "")
        )

    lines.extend(
        [
            "",
            "[读法] 三问：是不是一起动？谁更早动？谁波动更大？",
            "      括号里是专业指标；结论是统计描述，不是因果。",
            "",
            "[核心结论]",
            "",
        ]
    )
    for index, row in enumerate(pairwise, start=1):
        core = row.get("core") if isinstance(row.get("core"), Mapping) else {}
        left = _pair_title(row.get("label_a"), by_id.get(str(row.get("a") or "")))
        right = _pair_title(row.get("label_b"), by_id.get(str(row.get("b") or "")))
        lines.append(f"  ({index}) {left}  vs  {right}")
        rel = str(core.get("relation_text") or "").strip()
        if rel:
            lines.append(f"      同向还是反向: {rel}")
        lead = str(core.get("lead_text") or "").strip()
        if lead:
            lines.append(f"      谁先谁后: {lead}")
        scale = str(core.get("scale_text") or "").strip()
        if scale:
            lines.append(f"      波动差多少: {scale}")
        flags = []
        if row.get("reliable") is False:
            flags.append("共同样本偏少，结论仅供参考")
        if row.get("shape_ok") is False:
            flags.append("走势不太像 →「谁先谁后 / 波动差多少」请谨慎看")
        if flags:
            lines.append(f"      注意: {'；'.join(flags)}")
        lines.append("")

    extras: List[str] = []
    has_rolling = False
    for row in pairwise:
        label = f"{row.get('label_a')} vs {row.get('label_b')}"
        for warn in row.get("warnings") or []:
            extras.append(f"  - {label}: {warn}")
        supplement = row.get("supplement")
        rolling = (
            supplement.get("rolling")
            if isinstance(supplement, Mapping)
            else None
        )
        if isinstance(rolling, Mapping):
            has_rolling = True
            extras.append(f"  - {label}: {format_rolling_stability(rolling)}")
    notes = [
        str(n).strip()
        for n in (summary.get("notes") or [])
        if str(n).strip() and ("事件" in str(n) or "cum_exit_roi" in str(n))
    ]
    if extras or notes:
        if has_rolling:
            lines.extend(
                [
                    "[补充] 关系稳不稳",
                    "      用连续重叠的滚动窗看相关是否老变；",
                    "      「翻转」=相邻两窗从正相关变成负相关（或反过来）；",
                    "      分母=最多可能翻转的次数（窗数−1）。",
                    "",
                ]
            )
        else:
            lines.append("[补充]")
        for note in notes:
            lines.append(f"  - {note}")
        lines.extend(extras)
        lines.append("")

    lines.append("产物含 series.json（供日后画图）与 findings.md。")
    lines.append("")
    return "\n".join(lines)


def _participant_who(item: Mapping[str, Any]) -> str:
    """一句话说明这条序列是谁（策略 key / 数据键等）。"""
    if item.get("source") == "strategy_sim":
        sk = item.get("strategy_key") or item.get("strategy") or "?"
        ver = item.get("resolved_version") or item.get("version") or "latest"
        layer = item.get("layer") or "?"
        metric = item.get("metric") or "?"
        who = f"策略 {sk}@{ver} · {layer}.{metric}"
        if item.get("entity_id"):
            who += f" · {item.get('entity_id')}"
        return who
    data_key = str(item.get("data_key") or "").strip()
    field = str(item.get("field") or "").strip()
    entity_id = str(item.get("entity_id") or "").strip()
    if data_key and entity_id and field:
        return f"{data_key} · {entity_id}.{field}"
    if data_key and field:
        return f"{data_key} · {field}"
    return data_key or field or ""


def _pair_title(label: Any, item: Mapping[str, Any] | None) -> str:
    name = str(label or "").strip() or "?"
    if not item:
        return name
    who = _participant_who(item)
    if not who:
        return name
    # 身份已写进 label 时不再重复
    sk = str(item.get("strategy_key") or "").strip()
    if who in name or (sk and sk in name):
        return name
    return f"{name}（{who}）"


def format_rolling_stability(rolling: Mapping[str, Any]) -> str:
    """白话回答「稳不稳」，专业数放括号。"""
    window = int(rolling.get("window") or 0)
    mean = rolling.get("mean")
    recent = rolling.get("recent")
    flips = int(rolling.get("sign_flips") or 0)
    n_windows = int(rolling.get("n_windows") or 0)
    max_flips = rolling.get("max_sign_flips")
    if max_flips is None:
        max_flips = max(0, n_windows - 1)
    max_flips = int(max_flips)
    rate = (flips / max_flips) if max_flips > 0 else 0.0
    tag = str(rolling.get("stability") or "")
    if not tag and mean is not None and recent is not None:
        from core.modules.series_relation.core.pipeline.analyze import (
            _stability_tag,
        )

        tag = _stability_tag(float(mean), float(recent), flips, max_flips)

    from core.modules.series_relation.core.pipeline.format_num import (
        fmt_corr,
        fmt_pct,
    )

    verdict, nuance = _stability_plain(tag, mean, recent)
    stats = (
        f"{window} 日滚动 Spearman：平均≈{fmt_corr(mean)}，最近≈{fmt_corr(recent)}；"
        f"方向翻转 {flips}/{max_flips} 次"
        f"（翻转率≈{fmt_pct(rate)}，窗数={n_windows}）"
    )
    return f"{verdict}——{nuance}（{stats}）"


def _stability_plain(
    tag: str,
    mean: Any,
    recent: Any,
) -> tuple[str, str]:
    try:
        m = float(mean)
        r = float(recent)
    except (TypeError, ValueError):
        return "说不清稳不稳", "滚动相关算不出来"

    weaker = abs(r) + 0.08 < abs(m)
    stronger = abs(r) > abs(m) + 0.08
    if tag == "stable":
        verdict = "比较稳"
        if weaker:
            nuance = "方向大体一直没对调，但最近相关比全程平均弱一些"
        elif stronger:
            nuance = "方向大体一直没对调，最近相关还略强一些"
        else:
            nuance = "方向大体一直没对调，相关力度也还算连贯"
        return verdict, nuance
    if tag == "mostly_stable":
        verdict = "还算稳"
        nuance = "偶尔会正负对调，但多数时候方向还能对上"
        if weaker:
            nuance += "；最近比平均弱一些"
        return verdict, nuance
    # unstable
    mean_sign = 0 if abs(m) < 0.05 else (1 if m > 0 else -1)
    recent_sign = 0 if abs(r) < 0.05 else (1 if r > 0 else -1)
    if mean_sign and recent_sign and mean_sign != recent_sign:
        return (
            "不太稳",
            "全程平均与最近窗口的方向已经对不上（有时同向、有时反向）",
        )
    if abs(m) < 0.12 and abs(r) < 0.15:
        return "不太稳", "相关本身偏弱，时有时无，谈不上稳定的同向/反向"
    return "不太稳", "相邻窗口里正负对调偏多，关系方向不牢靠"


__all__ = ["format_cli_report", "format_rolling_stability"]
