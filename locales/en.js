window.OEP_GUIDE_LOCALE = {
  "language": "en",
  "labels": {
    "AI input and output": "What the AI receives and returns",
    "Illustrative fixture notice": "Complete examples use a synthetic two-column, two-row dataset. Inputs come from real tool calls; the documented candidates follow the contract and passed acceptance checks. These are static examples, not live model responses.",
    "Injected error notice": "The combined workflow deliberately injects an incorrect title to show how independent review finds and repairs a semantic error. Program acceptance does not establish semantic correctness.",
    "Prompt assembly notice": "These complete examples were assembled for this guide: they show the host task, role instructions, current input and candidate output. Tools return data and checks; they do not assemble prompts or schedule roles.",
    "Full AI prompt": "Full AI prompt and input material",
    "Full AI output": "Full AI candidate output",
    "Example source": "Example: power.csv has two columns (year and power) and two rows. The background document declares installed capacity in GW.",
    "Re-review notice": "This is the task given to a fresh Reviewer after applying the repair patch. Its hashes, current title and input context have been updated.",
    "No AI execution notice": "This stage has no separate semantic candidate JSON example. The host AI still chooses the next action, calls tools and interprets results. The program performs only explicitly requested deterministic operations.",
    "Full localized prompt": "Full prompt · translated reading version",
    "Full original prompt": "Full prompt · English original",
    "Localized prompt notice": "The translated reading version describes the same task. Metadata, hashes, schema and original evidence remain in English. Follow the Skill and current tool contract when running the task.",
    "Command authorship": "Who writes commands and performs the work?",
    "Command authorship explanation": "The host AI or coordinator usually writes and calls commands based on your request and the current run state. You can also enter them manually. Once the terminal starts the Python tool, the program reads data, computes statistics, freezes snapshots and validates results. Role labels identify the main participant; they do not imply that a person must write every command.",
    "Command example prompt": "Request to the host AI: read examples/capacity.csv and examples/capacity-source.md, create generation run runs/draft-01 and collect evidence first. Do not upload. Write and call the corresponding tool command.",
    "Command example output": "A complete command the AI may write and call",
    "Characters": "characters",
    "Candidate file": "Candidate file",
    "Input material": "Input material",
    "Language": "Language"
  },
  "flows": []
};
