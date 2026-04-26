import os
from crewai import Agent, Task, Crew, Process, LLM
from textwrap import dedent

# Set your Groq API key here
os.environ["GROQ_API_KEY"] = ""

# Initialize the LLM explicitly using CrewAI's LLM class
groq_llm = LLM(
    model="groq/meta-llama/llama-4-scout-17b-16e-instruct",
    api_key=os.environ["GROQ_API_KEY"]
)

# --- 1. AGENTS ---

agent_a_sentinel = Agent(
    role='The Sentinel (News & Sentiment Analyst)',
    goal='Analyze football news and output a quantitative impact score (delta) between -15.0 and +15.0.',
    backstory=dedent("""\
        You are an elite football scouting data analyst. Your specialty is reading 
        qualitative news—injury reports, manager quotes, and social media trends—and 
        converting them into hard mathematical numbers to adjust a player's dynamic rating."""),
    verbose=True,
    allow_delegation=False,
    llm=groq_llm
)

agent_b_gm = Agent(
    role='The General Manager (Squad Deficit Analyst)',
    goal='Assess U Cluj team match performance and output a Positional Squad Deficit Map.',
    backstory=dedent("""\
        You are the General Manager of FC Universitatea Cluj. You constantly monitor your 
        team's overall match statistics. After a match, you identify which positions 
        are currently the weakest link and assign them an urgency score from 0.0 to 1.0."""),
    verbose=True,
    allow_delegation=False,
    llm=groq_llm
)

agent_c_tactician = Agent(
    role='The Tactician (Weakness Analyst)',
    goal='Analyze U Cluj match stats and update the boolean TEAM_WORST_STATS map.',
    backstory=dedent("""\
        You are the tactical analyst for U Cluj. You look at team performance data (e.g., aerials won, 
        possession lost, clean sheets) and determine which specific statistical categories 
        are currently failing. You output a JSON of boolean flags for these stats."""),
    verbose=True,
    allow_delegation=False,
    llm=groq_llm
)

agent_d_matchmaker = Agent(
    role='The Matchmaker (Synergy Multiplier)',
    goal='Evaluate a shortlisted prospect to determine their Complementary Factor multiplier.',
    backstory=dedent("""\
        You analyze a specific scouted player's strengths. If their best stats directly 
        solve the current TRUE boolean flags in U Cluj's TEAM_WORST_STATS map, you award 
        them a complementary_factor multiplier between 1.0 and 1.5."""),
    verbose=True,
    allow_delegation=False,
    llm=groq_llm
)