from __future__ import annotations

import argparse
import json
from pathlib import Path

from ai_takehome.config import Settings
from ai_takehome.rag.cost import write_cost_artifacts
from ai_takehome.rag.evaluation import evaluate_rag
from ai_takehome.rag.service import RAGEngine


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Chroma-backed RAG utility")
    sub = parser.add_subparsers(dest="command", required=True)
    ingest = sub.add_parser("ingest")
    ingest.add_argument("path", type=Path)
    query = sub.add_parser("query")
    query.add_argument("question")
    query.add_argument("--k", type=int, default=None)
    query.add_argument(
        "--filter",
        action="append",
        default=[],
        help="Metadata equality filter in key=value form; repeatable.",
    )
    evaluate = sub.add_parser("evaluate")
    evaluate.add_argument("--questions", type=Path, required=True)
    evaluate.add_argument("--output", type=Path, required=True)
    evaluate.add_argument("--k", type=int, default=3)
    evaluate.add_argument("--latency-repeats", type=int, default=10)
    cost = sub.add_parser("cost")
    cost.add_argument("--json", type=Path, required=True)
    cost.add_argument("--csv", type=Path, required=True)
    return parser


def main() -> None:
    args = _parser().parse_args()
    settings = Settings.from_env()
    if args.command == "cost":
        result = write_cost_artifacts(args.json, args.csv)
    else:
        engine = RAGEngine(settings)
        if args.command == "ingest":
            items = engine.ingest(args.path)
            result = {
                "documents": len(items),
                "chunks_written": sum(item.chunks_written for item in items),
                "total_vectors": engine.store.count(),
                "results": [item.__dict__ for item in items],
            }
        elif args.command == "query":
            metadata_filter = {}
            for item in args.filter:
                if "=" not in item:
                    raise SystemExit("--filter must have key=value form")
                key, value = item.split("=", 1)
                metadata_filter[key] = value
            result = engine.ask(
                args.question,
                k=args.k,
                metadata_filter=metadata_filter or None,
            )
        else:
            result = evaluate_rag(
                engine,
                args.questions,
                args.output,
                k=args.k,
                latency_repeats=args.latency_repeats,
            )
    print(json.dumps(result, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()

