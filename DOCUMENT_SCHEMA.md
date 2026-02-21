# Quiz Document Schema

This document describes the exact format your `.docx` file must follow to work with the quiz parser.

---

## Structure of Each Question Block

Each question must follow this structure **in order**:

```
Question 1: Your full question text goes here?
A. First option
B. Second option
C. Third option
D. Fourth option

The correct answer is: B. Second option

Explanation
Write your explanation paragraph here. Can be multiple sentences.

Why the other options are not the best answer
A. First option: Reason why A is wrong.
C. Third option: Reason why C is wrong.
D. Fourth option: Reason why D is wrong.
```

---

## Rules

| Element | Required Format |
|---|---|
| Question heading | Must start with `Question N:` — e.g. `Question 1:` |
| Options | Each on its own line, starting with `A.` `B.` `C.` `D.` |
| Correct answer line | Must start with `The correct answer is:` followed by letter and dot — e.g. `The correct answer is: B. Business objectives` |
| Explanation header | Exactly the single word `Explanation` on its own line |
| Wrong options header | Must start with `Why the other options` on its own line |
| Wrong option reasons | Format: `A. Option text: Reason why it is wrong` — one per line |
| Blank line between questions | Optional but recommended |

### What is ignored
- Any line starting with `Answer Key` (treated as a section header)
- Duplicate question numbers — only the **first** occurrence is kept
- Blank paragraphs

---

## Full Example (2 Questions)

```
Answer Key

Question 1: Which of the following is the MOST important input when developing risk scenarios?
A. Key performance indicators
B. Business objectives
C. The organization's risk framework
D. Risk appetite

The correct answer is: B. Business objectives

Explanation
Risk scenarios must be tied to what matters most to the enterprise—its business
objectives and value drivers. This ensures the scenarios are relevant, measurable,
and decision-useful.

Why the other options are not the best answer
A. Key performance indicators: KPIs track performance of ongoing activities; they do not define strategic aims or context for scenario building.
C. The organization's risk framework: The framework guides process and governance, but it is an enabler—not the primary input—when selecting and crafting scenarios.
D. Risk appetite: Appetite constrains risk-taking and helps with evaluation/response thresholds, but scenarios should first be derived from business objectives.

Question 2: Which of the following is the GREATEST concern associated with the transmission of healthcare data across the internet?
A. Unencrypted data
B. Lack of redundant circuits
C. Low bandwidth connections
D. Data integrity

The correct answer is: A. Unencrypted data

Explanation
Protected health information (PHI) requires strong confidentiality controls.
Transmitting data unencrypted over public networks creates the highest risk of
unauthorized disclosure and regulatory noncompliance.

Why the other options are not the best answer
B. Lack of redundant circuits: Affects availability and resilience, not the primary confidentiality concern for PHI in transit.
C. Low bandwidth connections: Impacts performance rather than the core security objective for PHI.
D. Data integrity: Important, but exposure from unencrypted transmission is typically the more critical and immediate risk for PHI.
```

---

## Notes

- Questions can have **any number of options** (A–D is typical, but more letters are supported).
- The wrong-options section does **not** need to include all options — only the ones that are not the correct answer.
- Option text in the `Why the other options` section does not need to match the original option text exactly; only the leading letter is used to identify the option.
- The document may contain an `Answer Key` heading at the top or between sections — it will be ignored automatically.
