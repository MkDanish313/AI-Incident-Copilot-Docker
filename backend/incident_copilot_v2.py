from langchain_ollama import OllamaLLM
llm = OllamaLLM(model="llama2:7b", base_url="http://localhost:11434")
print(llm.invoke("Give 3 steps to debug high CPU on Linux."))
