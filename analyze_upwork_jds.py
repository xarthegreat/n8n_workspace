#!/usr/bin/env python3
"""Analyze Upwork JD rows for marketing/sales-related n8n opportunities.

Input can be a local CSV export of your Google Sheet, or fetched directly via
Google Sheets CSV export if the sheet is shared publicly.
"""

from __future__ import annotations

import argparse
import itertools
import re
from collections import Counter, defaultdict
from pathlib import Path
from typing import Dict, List, Set, Tuple

import matplotlib.pyplot as plt
import pandas as pd
import seaborn as sns

REQUIRED_COLUMNS = ["Title", "URL", "Description", "Budget", "Skills Set"]

MARKETING_SALES_KEYWORDS = {
    "marketing",
    "sales",
    "lead",
    "lead gen",
    "lead generation",
    "crm",
    "email campaign",
    "cold email",
    "outreach",
    "funnel",
    "conversion",
    "ads",
    "facebook ads",
    "google ads",
    "seo",
    "content marketing",
    "pipeline",
    "prospect",
    "appointment setting",
    "b2b",
    "b2c",
    "webinar",
    "newsletter",
    "automation",
    "attribution",
}

# Canonical tool names + common aliases found in job descriptions.
TOOL_ALIASES: Dict[str, Set[str]] = {
    "n8n": {"n8n"},
    "Zapier": {"zapier"},
    "Make": {"make.com", "make", "integromat"},
    "HubSpot": {"hubspot"},
    "Salesforce": {"salesforce"},
    "Pipedrive": {"pipedrive"},
    "Airtable": {"airtable"},
    "Notion": {"notion"},
    "Google Sheets": {"google sheets", "gsheet", "g sheets"},
    "Google Ads": {"google ads", "adwords"},
    "Meta Ads": {"facebook ads", "meta ads", "instagram ads"},
    "LinkedIn": {"linkedin"},
    "Apollo": {"apollo", "apollo.io"},
    "Clay": {"clay", "clay.com"},
    "Lemlist": {"lemlist"},
    "Instantly": {"instantly", "instantly.ai"},
    "Mailchimp": {"mailchimp"},
    "Klaviyo": {"klaviyo"},
    "Brevo": {"brevo", "sendinblue"},
    "ActiveCampaign": {"activecampaign"},
    "GoHighLevel": {"gohighlevel", "highlevel"},
    "Twilio": {"twilio"},
    "Slack": {"slack"},
    "OpenAI": {"openai", "chatgpt", "gpt-4", "gpt"},
    "WhatsApp": {"whatsapp"},
    "Shopify": {"shopify"},
    "WooCommerce": {"woocommerce"},
    "Stripe": {"stripe"},
    "Calendly": {"calendly"},
}

PAIN_KEYWORDS = {
    "lead quality",
    "low conversion",
    "manual",
    "manual process",
    "time-consuming",
    "slow",
    "no visibility",
    "tracking",
    "attribution",
    "follow-up",
    "data sync",
    "duplicate",
    "messy",
    "inconsistent",
    "scaling",
    "missed leads",
    "response time",
    "integration",
    "reporting",
    "broken workflow",
    "handoff",
}

STOPWORDS = {
    "the", "and", "for", "with", "that", "this", "from", "you", "your", "our", "are", "need", "looking",
    "into", "have", "has", "will", "can", "not", "but", "all", "any", "job", "work", "build", "help", "using",
    "automation", "automate", "n8n", "workflow", "workflows", "make", "zapier", "client", "project", "description",
}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Analyze Upwork JD dataset for marketing/sales signals")
    parser.add_argument("--csv", type=str, help="Path to local CSV export", default=None)
    parser.add_argument("--sheet-id", type=str, help="Google Sheet ID (if public)", default=None)
    parser.add_argument("--gid", type=str, help="Sheet tab gid", default="0")
    parser.add_argument("--outdir", type=str, default="analysis_output")
    parser.add_argument("--min-cooccur", type=int, default=2, help="Minimum pair count to include in heatmap")
    return parser.parse_args()


def load_data(args: argparse.Namespace) -> pd.DataFrame:
    if args.csv:
        df = pd.read_csv(args.csv)
    elif args.sheet_id:
        csv_url = f"https://docs.google.com/spreadsheets/d/{args.sheet_id}/export?format=csv&gid={args.gid}"
        df = pd.read_csv(csv_url)
    else:
        raise ValueError("Provide either --csv or --sheet-id")

    missing = [c for c in REQUIRED_COLUMNS if c not in df.columns]
    if missing:
        raise ValueError(f"Missing required columns: {missing}")

    for col in ["Title", "Description", "Skills Set", "URL", "Budget"]:
        df[col] = df[col].fillna("").astype(str)

    return df


def is_marketing_sales_related(text: str) -> bool:
    t = text.lower()
    return any(k in t for k in MARKETING_SALES_KEYWORDS)


def filter_marketing_sales(df: pd.DataFrame) -> pd.DataFrame:
    combo = (df["Title"] + " " + df["Description"]).str.lower()
    mask = combo.apply(is_marketing_sales_related)
    return df[mask].copy()


def extract_tools(text: str) -> Counter:
    text_l = text.lower()
    counts = Counter()
    for canonical, aliases in TOOL_ALIASES.items():
        n = 0
        for alias in aliases:
            pattern = rf"(?<![\w-]){re.escape(alias)}(?![\w-])"
            n += len(re.findall(pattern, text_l))
        if n > 0:
            counts[canonical] += n
    return counts


def extract_pain_phrases(descriptions: List[str], top_n: int = 20) -> Counter:
    phrase_counter = Counter()
    token_counter = Counter()

    for d in descriptions:
        dl = d.lower()
        for kw in PAIN_KEYWORDS:
            if kw in dl:
                phrase_counter[kw] += 1

        tokens = re.findall(r"[a-zA-Z][a-zA-Z\-]{2,}", dl)
        filtered = [t for t in tokens if t not in STOPWORDS]
        token_counter.update(filtered)

    merged = Counter(phrase_counter)
    merged.update(dict(token_counter.most_common(top_n)))
    return Counter(dict(merged.most_common(top_n)))


def analyze(df: pd.DataFrame) -> Tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    tool_mentions_total = Counter()
    tool_mentions_by_jd = Counter()
    pair_counts = Counter()

    for _, row in df.iterrows():
        text = f"{row['Title']}\n{row['Description']}\n{row['Skills Set']}"
        tools = extract_tools(text)
        if not tools:
            continue

        for tool, n in tools.items():
            tool_mentions_total[tool] += n
            tool_mentions_by_jd[tool] += 1

        present_tools = sorted(tools.keys())
        for a, b in itertools.combinations(present_tools, 2):
            pair_counts[(a, b)] += 1

    tools_df = pd.DataFrame(
        [
            {"Tool": t, "Total Mentions": tool_mentions_total[t], "Job Descriptions Mentioning Tool": tool_mentions_by_jd[t]}
            for t in tool_mentions_total
        ]
    ).sort_values(["Job Descriptions Mentioning Tool", "Total Mentions"], ascending=False)

    cooc_df = pd.DataFrame(
        [{"Tool A": a, "Tool B": b, "Co-mentioned JDs": n} for (a, b), n in pair_counts.items()]
    ).sort_values("Co-mentioned JDs", ascending=False)

    pains = extract_pain_phrases(df["Description"].tolist())
    pain_df = pd.DataFrame([{"Pain / Phrase": k, "Count": v} for k, v in pains.items()]).sort_values("Count", ascending=False)

    return tools_df, cooc_df, pain_df


def save_visuals(tools_df: pd.DataFrame, cooc_df: pd.DataFrame, pain_df: pd.DataFrame, outdir: Path, min_cooccur: int) -> None:
    sns.set_theme(style="whitegrid")

    plt.figure(figsize=(10, 6))
    top_tools = tools_df.head(15)
    sns.barplot(data=top_tools, y="Tool", x="Job Descriptions Mentioning Tool", color="#4C78A8")
    plt.title("Top tools/platforms mentioned in marketing/sales JDs")
    plt.tight_layout()
    plt.savefig(outdir / "top_tools.png", dpi=150)
    plt.close()

    if not cooc_df.empty:
        filtered = cooc_df[cooc_df["Co-mentioned JDs"] >= min_cooccur]
        if not filtered.empty:
            tools = sorted(set(filtered["Tool A"]).union(filtered["Tool B"]))
            matrix = pd.DataFrame(0, index=tools, columns=tools)
            for _, row in filtered.iterrows():
                a, b, n = row["Tool A"], row["Tool B"], int(row["Co-mentioned JDs"])
                matrix.loc[a, b] = n
                matrix.loc[b, a] = n

            plt.figure(figsize=(12, 10))
            sns.heatmap(matrix, cmap="Blues", linewidths=0.5)
            plt.title(f"Tool co-mentions (>= {min_cooccur} shared JDs)")
            plt.tight_layout()
            plt.savefig(outdir / "tool_cooccurrence_heatmap.png", dpi=150)
            plt.close()

    plt.figure(figsize=(10, 6))
    top_pains = pain_df.head(15)
    sns.barplot(data=top_pains, y="Pain / Phrase", x="Count", color="#F58518")
    plt.title("Top client pains / recurring description phrases")
    plt.tight_layout()
    plt.savefig(outdir / "pain_points.png", dpi=150)
    plt.close()


def main() -> None:
    args = parse_args()
    outdir = Path(args.outdir)
    outdir.mkdir(parents=True, exist_ok=True)

    df = load_data(args)
    filtered_df = filter_marketing_sales(df)
    tools_df, cooc_df, pain_df = analyze(filtered_df)

    filtered_df.to_csv(outdir / "filtered_marketing_sales_jds.csv", index=False)
    tools_df.to_csv(outdir / "tool_counts.csv", index=False)
    cooc_df.to_csv(outdir / "tool_cooccurrence.csv", index=False)
    pain_df.to_csv(outdir / "pain_points.csv", index=False)
    save_visuals(tools_df, cooc_df, pain_df, outdir, args.min_cooccur)

    print(f"Rows total: {len(df)}")
    print(f"Rows marketing/sales-related: {len(filtered_df)}")
    print(f"Outputs saved to: {outdir.resolve()}")


if __name__ == "__main__":
    main()
