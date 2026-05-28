import sys
from src.adapters.ai import BedrockAI
from src.adapters.userstore import DynamoDBUserStore

class MockUserStore:
    def list_transactions(self, user_id, month=None):
        return [
            {"amount": -2000000, "category": "Food"},
            {"amount": -1000000, "category": "Transport"},
            {"amount": 10000000, "category": "Income"}
        ]

def test():
    ai_client = BedrockAI(region="us-east-1", model_id="us.anthropic.claude-haiku-4-5-20251001-v1:0")
    userstore = MockUserStore()
    
    try:
        from src.handlers import handle_coach
        import json
        
        # We need to hack handle_coach or just call ai_client.chat directly to see raw output
        from src.handlers import handle_coach
        prompt = "Analyze the user's financial data..." # let's just run handle_coach and see the raw text from the error
        res = handle_coach("test_user", ai_client, userstore)
        print("Final result:")
        print(json.dumps(res, indent=2))
    except Exception as e:
        print("Error:", e)

if __name__ == "__main__":
    test()
