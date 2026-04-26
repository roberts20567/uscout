import time
from agent_workflows import agent_a_inject_news, agent_b_process_match_file

def trigger_agent_a():
    print("\n======================================================")
    print("🚀 TRIGGERING AGENT A (The Sentinel)")
    print("======================================================")
    # NOTE: Replace '143839' with a valid Player ID that currently exists in your 'u_dynamic_shadow_prospects' Firestore collection!
    test_player_id = "10399" 
    test_news = "The player suffered a minor calf strain during training today and will miss the next match, but the coach is optimistic."
    agent_a_inject_news(test_player_id, test_news)

def trigger_agents_b_and_c():
    print("\n======================================================")
    print("🚀 TRIGGERING AGENTS B & C (The GM & The Tactician)")
    print("======================================================")
    agent_b_process_match_file("mock_match_test.json")

if __name__ == "__main__":
    trigger_agent_a()
    time.sleep(2) # Brief pause between tests
    trigger_agents_b_and_c()
    print("\n✅ Test triggers sent! Check your Firestore database to see the live updates.")