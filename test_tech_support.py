"""
Test Qwen tech support integration
"""
import asyncio
from tech_support import llm_client

async def test():
    print("Testing Qwen tech support...")
    
    # Test question
    question = "Как перевести деньги?"
    context = {'balance': 5000.0, 'has_pin': True}
    
    answer = await llm_client.ask(question, context)
    print(f"\nQuestion: {question}")
    print(f"Answer: {answer}")

if __name__ == '__main__':
    asyncio.run(test())
