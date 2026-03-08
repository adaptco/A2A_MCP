# 🤖 Parker: The Base Model Agent Avatar

Parker is a personality-driven agent system designed for the **Jurassic Pixels** environment. Unlike traditional RL agents, Parker incorporates psychological traits, emotional states, and an internal monologue to make decisions and learn from experiences.

## 🏗️ Architecture

Parker's brain consists of several interlocking subsystems:

1.  **Personality Engine**: 8 evolving traits that define the "default" behavior (e.g., Cautious, Bold, Resourceful).
2.  **Emotional Sub-system**: 6 dynamic moods (e.g., Confident, Anxious) triggered by the environment and outcomes.
3.  **Goal Hierarchy**: 8 contextual goals that prioritize actions based on survival needs and personality.
4.  **Semantic Memory (RAG)**: A retrieval mechanism that pulls "memories" of past episodes to inform current logic.
5.  **Internal Monologue**: A logging system for "thoughts" that provides explainability for every action.

## 🧠 Personality Traits

| Trait | Description | Evolution Trigger |
| :--- | :--- | :--- |
| **Cautious** | Preference for safety and hazard avoidance. | Increases after health loss or death. |
| **Bold** | Willingness to take risks for high rewards. | Increases after successful high-risk actions. |
| **Resourceful** | Focus on gathering and efficiency. | Increases after gathering and crafting. |
| **Strategic** | Long-term planning and tool usage. | Increases after crafting complex items. |
| **Aggressive** | Predisposition towards hunting and combat. | Increases after successful hunts. |
| **Peaceful** | Avoidance of conflict and focus on building. | Increases after long survival periods without combat. |
| **Explorer** | Curiosity and movement into new areas. | Increases after discovering map segments. |
| **Builder** | Focus on creating structures and items. | Increases after crafting. |

## 🎮 Game Loop Integration

Parker connects to the Jurassic Pixels engine via a simple JSON interface:

1.  **Input**: The engine sends the `state` (Health, Threats, Resources).
2.  **Reasoning**:
    - **Step 1: Mood Shift**: Update mood based on health/threats.
    - **Step 2: Goal Selection**: Select goal based on state + personality.
    - **Step 3: RAG Retrieval**: Fetch memories related to the current goal.
    - **Step 4: Thought Generation**: Generate an internal monologue.
3.  **Action**: Parker returns the `action` and `reasoning`.
4.  **Learning**: After the episode, Parker updates traits based on the `reward` and `survived` status.

## 🚀 Getting Started

### Training
Run the orchestrator to train Parker for 10 episodes:
```bash
python parker_train.py --episodes 10 --export
```

### Interactive Mode
"Chat" with Parker to understand his reasoning:
```bash
python parker_train.py --interactive
```

### LoRA Export
Export Parker's thoughts and decisions for fine-tuning:
```bash
python parker_train.py --export
```

## 🛠️ State Persistence
Parker can be saved and loaded to maintain his personality across different runs of the simulation:
```python
parker.save_state("parker_v1.json")
parker_expert = Parker.load_state("parker_v1.json")
```
