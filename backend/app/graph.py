"""A real LangGraph workflow. Session history lives in MySQL between calls."""
from typing import TypedDict
from langgraph.graph import END, START, StateGraph
from . import ai, rag

class InterviewState(TypedDict, total=False):
    role: str
    kind: str
    difficulty: str
    asked: list[str]
    resume: str
    answer: str
    question: str
    current_position: int
    question_limit: int
    reference: str
    evaluation: dict
    next_question: str
    done: bool
    last_score: float | None

def retrieve(state: InterviewState):
    topic = f"{state['role']} {state['kind']} {state.get('question', '')}"
    return {'reference': rag.search(topic)}

def generate(state: InterviewState):
    q = ai.generate_question(
        state['role'], state['kind'], state['difficulty'],
        state.get('asked', []), state.get('resume', ''),
        state.get('reference', ''), state.get('last_score'),
    )
    return {'next_question': q}

def evaluate(state: InterviewState):
    context = state.get('reference') or rag.search(f"{state['role']} {state['question']}")
    result = ai.evaluate_answer(state['question'], state['answer'],
                                state['kind'], context)
    return {'evaluation': result}

def decide(state: InterviewState):
    done = state['current_position'] >= state['question_limit']
    # Simple, explainable adaptive rule for a college prototype.
    grade = state['evaluation']['overall']
    if grade < 50:
        level = 'easy'
    elif grade >= 80:
        level = 'hard'
    else:
        level = 'medium'
    return {'done': done, 'difficulty': level, 'last_score': grade}

def entry(state: InterviewState):
    return 'grade' if state.get('answer') else 'get_context'

def after_decide(state: InterviewState):
    return 'end' if state['done'] else 'get_context'

builder = StateGraph(InterviewState)
builder.add_node('get_context', retrieve)
builder.add_node('ask_question', generate)
builder.add_node('grade', evaluate)
builder.add_node('decide', decide)
builder.add_conditional_edges(START, entry, {'grade': 'grade', 'get_context': 'get_context'})
builder.add_edge('get_context', 'ask_question')
builder.add_edge('ask_question', END)
builder.add_edge('grade', 'decide')
builder.add_conditional_edges('decide', after_decide, {'end': END, 'get_context': 'get_context'})
interview_graph = builder.compile()

def run_flow(state: InterviewState) -> InterviewState:
    return interview_graph.invoke(state)
