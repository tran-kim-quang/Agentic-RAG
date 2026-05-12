"""Ingest markdown files into the retrieval service."""
import sys, os, argparse, asyncio
sys.path.insert(0, "/home/meocon/work/sideprj")
from ingest_service.pipeline import ingest_documents


def parse_args():
    p = argparse.ArgumentParser(description="Ingest markdown documents into Qdrant")
    p.add_argument("--dir", required=True, help="Directory containing .md files")
    p.add_argument("--project", default="unknown", help="Project name metadata")
    return p.parse_args()


def load_markdown_files(directory: str, project: str):
    docs = []
    for root, _, files in os.walk(directory):
        for f in files:
            if f.endswith(".md"):
                path = os.path.join(root, f)
                with open(path, "r", encoding="utf-8") as fh:
                    text = fh.read()
                docs.append({
                    "source": os.path.relpath(path, directory),
                    "text": text,
                    "metadata": {"project": project, "type": "markdown"},
                })
    return docs


async def main():
    args = parse_args()
    docs = load_markdown_files(args.dir, args.project)
    if not docs:
        print("No .md files found.")
        return
    print(f"Ingesting {len(docs)} documents from {args.dir} ...")
    n = await ingest_documents(docs)
    print(f"Done. Upserted {n} chunks.")


if __name__ == "__main__":
    asyncio.run(main())
