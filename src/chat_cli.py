from src.rag_chain import create_qa_chain


def main():
    qa_chain = create_qa_chain()

    print("Ask me anything about the CSS system (type 'exit' to quit):")
    while True:
        q = input("You: ").strip()
        if q.lower() == "exit":
            break

        result = qa_chain(q)

        print("\nCSS Bot:", result["result"])
        print()


if __name__ == "__main__":
    main()
