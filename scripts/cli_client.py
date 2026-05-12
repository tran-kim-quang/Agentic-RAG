"""Simple CLI client to chat with the orchestrator."""
import sys, httpx, argparse, uuid


def chat_loop(base_url: str):
    session = str(uuid.uuid4())
    print(f"Session: {session}")
    print("Nhập câu hỏi (hoặc 'exit' để thoát):\n")
    while True:
        text = input("Bạn: ").strip()
        if text.lower() in {"exit", "quit", "q"}:
            break
        resp = httpx.post(
            f"{base_url}/chat",
            json={"text": text, "session_id": session},
            timeout=30.0,
        )
        data = resp.json()
        print(f"AI: {data['answer']}")
        if data.get("follow_up"):
            print(f"   → {data['follow_up']}")
        print()


if __name__ == "__main__":
    p = argparse.ArgumentParser()
    p.add_argument("--url", default="http://localhost:8021", help="Orchestrator base URL")
    args = p.parse_args()
    chat_loop(args.url)
